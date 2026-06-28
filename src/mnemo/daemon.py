import logging
import threading
import time

import uvicorn

from . import db as db_module
from . import indexer
from .api import app
from .config import DB_PATH, ensure_config_dir, load_config, save_config
from .embedder import load_model
from .parser import check_ocr
from .watcher import FileWatcher

logger = logging.getLogger("mnemo")
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def first_run_setup(conn):
    config = load_config()
    if config.get("watched_folders"):
        return

    print("=== Mnemo - First Run ===")
    print("No folders are being watched yet.")
    print(
        "Enter paths to folders you want Mnemo to index (one per line)."
    )
    print("Press Enter on an empty line when done.")

    folders = []
    while True:
        line = input("Folder path: ").strip()
        if not line:
            break
        folders.append(line)

    if folders:
        for folder in folders:
            db_module.add_watched_folder(conn, folder)
        conn.commit()
        config["watched_folders"] = folders
        save_config(config)
        print(f"Added {len(folders)} folder(s). Starting index...")
    else:
        print("No folders added. Use POST /index later to add folders.")


def run_search_worker():
    try:
        from .ui import run_ui
        run_ui()
    except Exception as e:
        logger.error("UI worker failed: %s", e)


def report_status(conn):
    total = conn.execute("SELECT COUNT(*) as c FROM files WHERE index_status='complete'").fetchone()["c"]
    pages = conn.execute("SELECT COUNT(*) as c FROM pages").fetchone()["c"]
    ocr_pending = conn.execute("SELECT COUNT(*) as c FROM pages WHERE extract_status='needs_ocr'").fetchone()["c"]
    ocr_done = conn.execute("SELECT COUNT(*) as c FROM pages WHERE extract_status='ocr_done'").fetchone()["c"]
    return total, pages, ocr_pending, ocr_done


def run_ocr_worker():
    conn = db_module.get_connection()
    db_module.run_migrations(conn)
    pages_this_minute = 0
    cycle_start = time.time()
    MAX_PAGES_PER_CYCLE = 5
    CYCLE_INTERVAL = 60
    last_reported_pending = -1
    while True:
        try:
            now = time.time()
            if now - cycle_start > CYCLE_INTERVAL:
                pages_this_minute = 0
                cycle_start = now
            if pages_this_minute < MAX_PAGES_PER_CYCLE:
                indexer.process_ocr_queue(conn)
                pages_this_minute += 1
        except Exception as e:
            logger.error("OCR worker error: %s", e)

        _, _, ocr_pending, ocr_done = report_status(conn)
        if ocr_pending != last_reported_pending:
            if ocr_pending == 0:
                logger.info("All OCR complete! Search has %d OCR-processed pages available.", ocr_done)
            elif ocr_pending > 0 and last_reported_pending == 0:
                pass
            last_reported_pending = ocr_pending

        time.sleep(12)


def run_initial_index():
    conn = db_module.get_connection()
    db_module.run_migrations(conn)
    logger.info("Starting initial index of watched folders...")
    indexer.initial_index(conn)
    total, pages, ocr_pending, ocr_done = report_status(conn)
    logger.info(
        "Initial index complete: %d files, %d pages indexed. "
        "%d pages need OCR (background worker will process them). "
        "Search is ready.",
        total, pages - ocr_pending - ocr_done, ocr_pending,
    )


def main():
    ensure_config_dir()
    logger.info("Mnemo starting...")
    logger.info("Database: %s", DB_PATH)

    conn = db_module.get_connection()
    db_module.run_migrations(conn)
    conn.commit()

    config = load_config()
    model_name = config["embedding_model"]
    load_model(model_name)

    check_ocr()

    first_run_setup(conn)

    for folder in config.get("watched_folders", []):
        db_module.add_watched_folder(conn, folder)
    conn.commit()

    db_module.reset_stale_indexing(conn)
    conn.commit()

    watcher = FileWatcher()
    watcher.start()
    logger.info("File watcher started")

    threading.Thread(target=run_ocr_worker, daemon=True).start()
    threading.Thread(target=run_initial_index, daemon=True).start()
    threading.Thread(target=run_search_worker, daemon=True).start()

    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8765,
            log_level="info",
            access_log=False,
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        watcher.stop()
        conn.close()


if __name__ == "__main__":
    main()
