import logging
import os
import sys
import threading
import time
from pathlib import Path

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

    # Frozen GUI builds have sys.stderr = None — fix it early
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    logger.handlers[0].setStream(sys.stderr)

    # Patch uvicorn's DefaultFormatter to never call isatty on None
    import uvicorn.logging as _uvlog
    _orig_init = _uvlog.DefaultFormatter.__init__
    def _patched_init(self, fmt=None, datefmt=None, style="%", use_colors=None, validate=True):
        try:
            _orig_init(self, fmt, datefmt, style, use_colors, validate)
        except AttributeError:
            _orig_init(self, fmt, datefmt, style, False, validate)
    _uvlog.DefaultFormatter.__init__ = _patched_init

    logger.info("Mnemo starting...")
    logger.info("Database: %s", DB_PATH)

    conn = db_module.get_connection()
    db_module.run_migrations(conn)
    conn.commit()

    config = load_config()

    check_ocr()

    for folder in config.get("watched_folders", []):
        db_module.add_watched_folder(conn, folder)
    conn.commit()

    db_module.reset_stale_indexing(conn)
    conn.commit()

    watcher = FileWatcher()
    watcher.start()
    logger.info("File watcher started")

    # Start API server in background thread (uvicorn blocks)
    def _run_api():
        try:
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=8765,
                log_config=None,
                access_log=False,
            )
        except Exception as e:
            logger.error("API server error: %s", e)
    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()

    model_name = config["embedding_model"]

    # Defer model loading and background workers to after UI starts
    def _start_background():
        load_model(model_name)
        threading.Thread(target=run_ocr_worker, daemon=True).start()
        threading.Thread(target=run_initial_index, daemon=True).start()
    threading.Thread(target=_start_background, daemon=True).start()

    # Qt UI must run on the MAIN thread — show it immediately
    try:
        from .ui import run_ui
        run_ui()
    except Exception as e:
        logger.error("UI error: %s", e)

    watcher.stop()
    conn.close()


if __name__ == "__main__":
    main()
