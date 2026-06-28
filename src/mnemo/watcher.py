import logging
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from . import db as db_module
from . import indexer
from .embedder import get_model_name
from .config import load_config

logger = logging.getLogger(__name__)

SUPPORTED_EXT = (".pdf", ".txt")


class MnemoFileHandler(FileSystemEventHandler):
    def __init__(self):
        self.model_name = get_model_name() or load_config()["embedding_model"]
        self._local = threading.local()

    def _get_conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = db_module.get_connection()
        return self._local.conn

    def is_supported(self, path):
        return path.lower().endswith(SUPPORTED_EXT)

    def on_created(self, event):
        if event.is_directory or not self.is_supported(event.src_path):
            return
        logger.info("File created: %s", event.src_path)
        conn = self._get_conn()
        try:
            indexer.index_file(conn, event.src_path, self.model_name)
        except Exception as e:
            logger.error("Error indexing %s: %s", event.src_path, e)

    def on_modified(self, event):
        if event.is_directory or not self.is_supported(event.src_path):
            return
        logger.info("File modified: %s", event.src_path)
        conn = self._get_conn()
        try:
            indexer.index_file(conn, event.src_path, self.model_name)
        except Exception as e:
            logger.error("Error reindexing %s: %s", event.src_path, e)

    def on_deleted(self, event):
        if event.is_directory or not self.is_supported(event.src_path):
            return
        logger.info("File deleted: %s", event.src_path)
        conn = self._get_conn()
        try:
            existing = db_module.file_exists_by_path(conn, event.src_path)
            if existing:
                db_module.delete_file(conn, existing["id"])
                conn.commit()
        except Exception as e:
            logger.error("Error deleting %s: %s", event.src_path, e)

    def on_moved(self, event):
        if event.is_directory or not self.is_supported(event.dest_path):
            return
        logger.info("File moved: %s -> %s", event.src_path, event.dest_path)
        conn = self._get_conn()
        try:
            db_module.update_file_path(conn, event.src_path, event.dest_path)
            conn.commit()
        except Exception as e:
            logger.error("Error moving %s: %s", event.src_path, e)


class FileWatcher:
    def __init__(self):
        self.observer = Observer()
        self.handler = MnemoFileHandler()

    def start(self):
        conn = db_module.get_connection()
        folders = db_module.get_watched_folders(conn)
        conn.close()
        for row in folders:
            path = row["path"]
            logger.info("Watching folder: %s", path)
            self.observer.schedule(self.handler, path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def add_folder(self, path):
        self.observer.schedule(self.handler, path, recursive=True)
