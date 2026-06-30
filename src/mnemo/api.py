import threading

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from . import db as db_module
from . import indexer
from .config import load_config
from .embedder import get_model_name, is_model_ready
from .search import search

app = FastAPI(title="Mnemo", version="0.1.0")

_local = threading.local()
_index_lock = threading.Lock()


def _get_conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = db_module.get_connection()
    return _local.conn


class OpenLogRequest(BaseModel):
    query: str
    file_path: str
    file_id: int


@app.get("/search")
def search_endpoint(q: str = Query(...), limit: int = Query(8, le=50)):
    conn = _get_conn()
    results, cached, latency_ms, reason = search(conn, q, limit=limit)
    return {
        "query": q,
        "results": results,
        "cached": cached,
        "latency_ms": latency_ms,
        "reason": reason,
    }


@app.post("/index")
def add_folder(path: str = Query(...)):
    # Wait for model to finish loading — indexing needs embeddings
    while not is_model_ready():
        import time as _t
        _t.sleep(0.5)
    with _index_lock:
        conn = _get_conn()
        db_module.add_watched_folder(conn, path)
        conn.commit()
        model_name = get_model_name() or load_config()["embedding_model"]
        indexer.index_folder(conn, path, model_name)
    return {"status": "ok", "path": path}


@app.get("/status")
def daemon_status():
    conn = _get_conn()
    total = conn.execute(
        "SELECT COUNT(*) as c FROM files"
    ).fetchone()["c"]
    indexed = conn.execute(
        "SELECT COUNT(*) as c FROM files WHERE index_status = 'complete'"
    ).fetchone()["c"]
    stats = db_module.get_page_stats(conn)
    return {
        "status": "running",
        "model_ready": is_model_ready(),
        "files_total": total,
        "files_indexed": indexed,
        "pages_total": stats["total"],
        "pages_extracted": stats["extracted"],
        "pages_needing_ocr": stats["needs_ocr"],
        "pages_ocr_done": stats["ocr_done"],
        "pages_duplicate": stats["duplicate"],
    }


@app.get("/files")
def list_files():
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, path, filename, mtime, index_status, chunk_count FROM files ORDER BY mtime DESC"
    ).fetchall()
    return {"files": [dict(r) for r in rows]}


@app.delete("/files")
def remove_file(path: str = Query(...)):
    conn = _get_conn()
    existing = db_module.file_exists_by_path(conn, path)
    if not existing:
        raise HTTPException(status_code=404, detail="File not found")
    db_module.delete_file(conn, existing["id"])
    conn.commit()
    return {"status": "deleted", "path": path}


@app.post("/log-open")
def log_open(req: OpenLogRequest):
    conn = _get_conn()
    db_module.log_access(conn, req.query, req.file_path, req.file_id)
    conn.commit()
    return {"status": "logged"}
