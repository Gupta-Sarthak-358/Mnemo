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

_debug_log = None
def _debug(msg):
    global _debug_log
    try:
        if _debug_log is None:
            _debug_log = open(Path.home() / "mnemo_daemon_debug.log", "w")
        _debug_log.write(f"{msg}\n")
        _debug_log.flush()
    except Exception:
        pass





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
    import time as _time
    _t0 = _time.time()
    _debug("main() started")
    ensure_config_dir()
    _debug(f"ensure_config_dir OK ({round((_time.time()-_t0)*1000)}ms)")

    # Frozen GUI builds have sys.stderr = None — fix it early
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    # Re-point the module-level handler to whatever stderr is now
    logger.handlers[0].setStream(sys.stderr)
    _debug(f"stderr fixed, is None: {sys.stderr is None}")

    # Patch uvicorn's DefaultFormatter to never call isatty on None
    import uvicorn.logging as _uvlog
    _orig_init = _uvlog.DefaultFormatter.__init__
    def _patched_init(self, fmt=None, datefmt=None, style="%", use_colors=None, validate=True):
        try:
            _orig_init(self, fmt, datefmt, style, use_colors, validate)
        except AttributeError:
            _orig_init(self, fmt, datefmt, style, False, validate)
    _uvlog.DefaultFormatter.__init__ = _patched_init
    _debug(f"uvicorn formatter patched ({round((_time.time()-_t0)*1000)}ms)")

    logger.info("Mnemo starting...")
    logger.info("Database: %s", DB_PATH)
    _debug(f"logger OK ({round((_time.time()-_t0)*1000)}ms)")

    conn = db_module.get_connection()
    _debug(f"get_connection OK ({round((_time.time()-_t0)*1000)}ms)")
    db_module.run_migrations(conn)
    conn.commit()
    _debug(f"migrations OK ({round((_time.time()-_t0)*1000)}ms)")

    config = load_config()
    _debug(f"config loaded ({round((_time.time()-_t0)*1000)}ms)")

    _debug(f"check_ocr... ({round((_time.time()-_t0)*1000)}ms)")
    check_ocr()
    _debug(f"check_ocr OK ({round((_time.time()-_t0)*1000)}ms)")

    # First-run handled by UI dialog (run_search_worker)

    for folder in config.get("watched_folders", []):
        db_module.add_watched_folder(conn, folder)
    conn.commit()

    db_module.reset_stale_indexing(conn)
    conn.commit()
    _debug(f"DB setup done ({round((_time.time()-_t0)*1000)}ms)")

    watcher = FileWatcher()
    watcher.start()
    logger.info("File watcher started")
    _debug(f"watcher started ({round((_time.time()-_t0)*1000)}ms)")

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
    _debug(f"API thread started ({round((_time.time()-_t0)*1000)}ms)")

    model_name = config["embedding_model"]
    _debug(f"will load model {model_name} in background... ({round((_time.time()-_t0)*1000)}ms)")

    # Defer model loading and background workers to after UI starts
    # model loading (SentenceTransformer) takes 5-15s and must not block the UI
    def _start_background():
        _bt = _time.time()
        load_model(model_name)
        _debug(f"model loaded in background ({round((_time.time()-_bt)*1000)}ms)")
        threading.Thread(target=run_ocr_worker, daemon=True).start()
        threading.Thread(target=run_initial_index, daemon=True).start()
        _debug(f"background workers started ({round((_time.time()-_t0)*1000)}ms)")
    threading.Thread(target=_start_background, daemon=True).start()

    # Qt UI must run on the MAIN thread — show it immediately
    _debug(f"starting Qt UI on main thread... ({round((_time.time()-_t0)*1000)}ms)")
    try:
        from .ui import run_ui
        run_ui()
    except Exception as e:
        logger.error("UI error: %s", e)
        _debug(f"UI error: {e}")
    _debug("UI returned, shutting down...")

    watcher.stop()
    conn.close()
    _debug("shutdown complete")


if __name__ == "__main__":
    main()
