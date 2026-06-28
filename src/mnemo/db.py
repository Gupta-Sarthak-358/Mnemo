import json
import re
import sqlite3
import sqlite_vec
import struct
import time
from pathlib import Path

from .config import DB_PATH

CURRENT_SCHEMA_VERSION = 11

FTS_STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","by","with",
    "is","are","was","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","shall","can","need",
    "this","that","these","those","it","its","not","no","nor","so","just",
    "all","each","every","both","few","more","most","some","such","only",
    "own","same","here","there","when","where","why","how","about","into",
    "over","after","before","between","under","then","also","if","as",
}


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def run_migrations(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at REAL
        )
    """)
    version = conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_version"
    ).fetchone()[0]

    if version < 1:
        run_migration_1(conn)
    if version < 2:
        run_migration_2(conn)
    if version < 3:
        run_migration_3(conn)
    if version < 4:
        run_migration_4(conn)
    if version < 5:
        run_migration_5(conn)
    if version < 6:
        run_migration_6(conn)
    if version < 7:
        run_migration_7(conn)
    if version < 8:
        run_migration_8(conn)
    if version < 9:
        run_migration_9(conn)
    if version < 10:
        run_migration_10(conn)
    if version < 11:
        run_migration_11(conn)
    _backfill_chunk_metadata(conn)


def run_migration_8(conn):
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            text,
            tokenize='porter unicode61',
        );
    """)
    conn.execute(
        "INSERT OR IGNORE INTO chunks_fts(rowid, text) SELECT id, text FROM chunks"
    )
    conn.execute(
        "INSERT INTO schema_version VALUES (?, ?)", (8, time.time())
    )


def run_migration_9(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chunk_metadata (
            chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
            heading TEXT,
            concepts TEXT,
            enriched_at REAL
        );
    """)
    conn.execute(
        "INSERT INTO schema_version VALUES (?, ?)", (9, time.time())
    )
    _backfill_chunk_metadata(conn)


def run_migration_10(conn):
    conn.executescript("""
        ALTER TABLE files ADD COLUMN author TEXT DEFAULT '';
    """)
    conn.execute(
        "INSERT INTO schema_version VALUES (?, ?)", (10, time.time())
    )


def run_migration_11(conn):
    from .enrich import extract_concepts as extract_concepts_fn
    rows = conn.execute(
        "SELECT cm.chunk_id, c.text FROM chunk_metadata cm JOIN chunks c ON cm.chunk_id = c.id"
    ).fetchall()
    print(f"[migration 11] Re-enriching {len(rows)} chunks with improved concepts...")
    for i, row in enumerate(rows):
        new_concepts = extract_concepts_fn(row["text"])
        conn.execute(
            "UPDATE chunk_metadata SET concepts = ?, enriched_at = ? WHERE chunk_id = ?",
            (json.dumps(new_concepts), time.time(), row["chunk_id"]),
        )
        if i > 0 and i % 200 == 0:
            conn.commit()
    conn.execute("INSERT INTO schema_version VALUES (?, ?)", (11, time.time()))
    conn.commit()
    print(f"[migration 11] Done.")


def _backfill_chunk_metadata(conn):
    from .enrich import extract_heading, extract_concepts
    rows = conn.execute(
        "SELECT id, text FROM chunks WHERE id NOT IN (SELECT chunk_id FROM chunk_metadata)"
    ).fetchall()
    for row in rows:
        heading = extract_heading(row["text"])
        concepts = extract_concepts(row["text"])
        conn.execute(
            "INSERT OR IGNORE INTO chunk_metadata (chunk_id, heading, concepts, enriched_at) VALUES (?, ?, ?, ?)",
            (row["id"], heading, json.dumps(concepts), time.time()),
        )


def insert_chunk_metadata(conn, chunk_id, heading=None, concepts=None):
    conn.execute(
        """INSERT OR REPLACE INTO chunk_metadata (chunk_id, heading, concepts, enriched_at)
           VALUES (?, ?, ?, ?)""",
        (chunk_id, heading, json.dumps(concepts or []), time.time()),
    )


def get_chunk_metadata_batch(conn, chunk_ids):
    if not chunk_ids:
        return {}
    placeholders = ",".join("?" * len(chunk_ids))
    rows = conn.execute(
        f"SELECT chunk_id, heading, concepts FROM chunk_metadata WHERE chunk_id IN ({placeholders})",
        chunk_ids,
    ).fetchall()
    result = {}
    for r in rows:
        concepts = json.loads(r["concepts"]) if r["concepts"] else []
        result[r["chunk_id"]] = {
            "heading": r["heading"],
            "concepts": concepts,
        }
    return result


def run_migration_1(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at REAL
        );

        CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE,
            filename TEXT,
            mtime REAL,
            date_indexed REAL,
            ocr_used INTEGER DEFAULT 0,
            file_type TEXT,
            hash TEXT,
            index_status TEXT DEFAULT 'pending',
            embedding_model TEXT
        );

        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
            page_num INTEGER,
            chunk_index INTEGER,
            text TEXT
        );

        CREATE VIRTUAL TABLE chunk_embeddings USING vec0(
            chunk_id INTEGER PRIMARY KEY,
            embedding FLOAT[384]
        );

        CREATE TABLE access_log (
            id INTEGER PRIMARY KEY,
            query TEXT,
            file_path TEXT,
            file_id INTEGER REFERENCES files(id),
            opened_at REAL
        );

        CREATE TABLE search_events (
            id INTEGER PRIMARY KEY,
            query TEXT,
            result_count INTEGER,
            clicked_rank INTEGER,
            timestamp REAL
        );

        CREATE TABLE watched_folders (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE,
            added_at REAL,
            active INTEGER DEFAULT 1
        );
    """)
    conn.execute(
        "INSERT INTO schema_version VALUES (?, ?)", (1, time.time())
    )


def run_migration_2(conn):
    conn.executescript("""
        ALTER TABLE files ADD COLUMN total_pages INTEGER DEFAULT 0;
    """)
    conn.execute(
        "INSERT INTO schema_version VALUES (?, ?)", (2, time.time())
    )


def run_migration_3(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ocr_queue (
            id INTEGER PRIMARY KEY,
            file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
            path TEXT,
            page_num INTEGER,
            priority INTEGER DEFAULT 1,
            status TEXT DEFAULT 'pending'
        );
    """)
    conn.execute(
        "INSERT INTO schema_version VALUES (?, ?)", (3, time.time())
    )


def run_migration_4(conn):
    conn.executescript("""
        CREATE TABLE query_cache (
            query_hash TEXT PRIMARY KEY,
            results TEXT,
            cached_at REAL
        );
    """)
    conn.execute(
        "INSERT INTO schema_version VALUES (?, ?)", (4, time.time())
    )


def run_migration_5(conn):
    conn.executescript("""
        ALTER TABLE files ADD COLUMN chunk_count INTEGER DEFAULT 0;
    """)
    conn.execute(
        "INSERT INTO schema_version VALUES (?, ?)", (5, time.time())
    )


def run_migration_6(conn):
    conn.executescript("""
        CREATE TABLE page_quality (
            id INTEGER PRIMARY KEY,
            file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
            page_num INTEGER,
            quality_score REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            UNIQUE(file_id, page_num)
        );
    """)
    conn.execute(
        "INSERT INTO schema_version VALUES (?, ?)", (6, time.time())
    )


def run_migration_7(conn):
    conn.executescript("""
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY,
            file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
            page_num INTEGER,
            page_hash TEXT,
            quality_score REAL DEFAULT 0.0,
            extract_status TEXT DEFAULT 'pending',
            extraction_method TEXT DEFAULT 'unknown',
            ocr_attempts INTEGER DEFAULT 0,
            UNIQUE(file_id, page_num)
        );
        CREATE INDEX idx_pages_file ON pages(file_id);
        CREATE INDEX idx_pages_hash ON pages(page_hash);
    """)
    conn.execute(
        "INSERT INTO schema_version VALUES (?, ?)", (7, time.time())
    )


def insert_file(conn, path, mtime, file_type, hash_val, model_name, author=""):
    filename = Path(path).name
    cur = conn.execute(
        """INSERT INTO files (path, filename, mtime, date_indexed, file_type, hash, index_status, embedding_model, author)
           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (path, filename, mtime, time.time(), file_type, hash_val, model_name, author),
    )
    return cur.lastrowid


def update_file_status(conn, file_id, status, chunk_count=None):
    if chunk_count is not None:
        conn.execute(
            "UPDATE files SET index_status = ?, chunk_count = ? WHERE id = ?",
            (status, chunk_count, file_id),
        )
    else:
        conn.execute(
            "UPDATE files SET index_status = ? WHERE id = ?",
            (status, file_id),
        )


def set_file_indexing(conn, file_id):
    conn.execute(
        "UPDATE files SET index_status = 'indexing' WHERE id = ?",
        (file_id,),
    )


def file_exists_by_hash(conn, hash_val):
    row = conn.execute(
        "SELECT id FROM files WHERE hash = ?", (hash_val,)
    ).fetchone()
    return row is not None


def file_exists_by_path(conn, path):
    row = conn.execute(
        "SELECT id, hash, index_status FROM files WHERE path = ?", (path,)
    ).fetchone()
    return row


def get_file_by_id(conn, file_id):
    return conn.execute(
        "SELECT * FROM files WHERE id = ?", (file_id,)
    ).fetchone()


def insert_chunk(conn, file_id, page_num, chunk_index, text):
    cur = conn.execute(
        "INSERT INTO chunks (file_id, page_num, chunk_index, text) VALUES (?, ?, ?, ?)",
        (file_id, page_num, chunk_index, text),
    )
    return cur.lastrowid


def insert_embedding(conn, chunk_id, embedding):
    vec_bytes = struct.pack(f"{len(embedding)}f", *embedding)
    conn.execute(
        "INSERT INTO chunk_embeddings (chunk_id, embedding) VALUES (?, ?)",
        (chunk_id, vec_bytes),
    )


def delete_file_chunks(conn, file_id):
    conn.execute(
        "DELETE FROM chunks_fts WHERE rowid IN (SELECT id FROM chunks WHERE file_id = ?)",
        (file_id,),
    )
    conn.execute(
        "DELETE FROM chunk_embeddings WHERE chunk_id IN (SELECT id FROM chunks WHERE file_id = ?)",
        (file_id,),
    )
    conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))


def delete_file(conn, file_id):
    delete_file_chunks(conn, file_id)
    conn.execute("DELETE FROM access_log WHERE file_id = ?", (file_id,))
    conn.execute("DELETE FROM pages WHERE file_id = ?", (file_id,))
    conn.execute("DELETE FROM ocr_queue WHERE file_id = ?", (file_id,))
    conn.execute("DELETE FROM files WHERE id = ?", (file_id,))


def update_file_path(conn, old_path, new_path):
    filename = Path(new_path).name
    conn.execute(
        "UPDATE files SET path = ?, filename = ? WHERE path = ?",
        (new_path, filename, old_path),
    )


def vector_search(conn, query_embedding, limit=24):
    vec_bytes = struct.pack(f"{len(query_embedding)}f", *query_embedding)
    rows = conn.execute(
        """
        SELECT
            ce.chunk_id,
            distance,
            c.file_id,
            c.page_num,
            c.chunk_index,
            c.text,
            f.path,
            f.filename,
            f.mtime,
            f.author
        FROM chunk_embeddings ce
        JOIN chunks c ON c.id = ce.chunk_id
        JOIN files f ON f.id = c.file_id
        WHERE ce.embedding MATCH ? AND k = ?
        ORDER BY distance
        """,
        (vec_bytes, limit),
    ).fetchall()
    return rows


def insert_fts(conn, chunk_id, text):
    conn.execute(
        "INSERT INTO chunks_fts(rowid, text) VALUES (?, ?)",
        (chunk_id, text),
    )


def delete_fts(conn, chunk_id):
    conn.execute("DELETE FROM chunks_fts WHERE rowid = ?", (chunk_id,))


def _to_fts_query(user_query):
    terms = [
        t for t in re.split(r"\W+", user_query.strip().lower())
        if len(t) > 1 and t not in FTS_STOPWORDS
    ]
    if not terms:
        return None
    escaped = [re.sub(r"[^\w]", "", t) for t in terms if re.sub(r"[^\w]", "", t)]
    if not escaped:
        return None
    if len(escaped) >= 2:
        exact = '"' + " ".join(escaped) + '"'
        and_part = " AND ".join(t + "*" for t in escaped)
        return f"({exact}) OR ({and_part})"
    return escaped[0] + "*"


def fts_search_detailed(conn, query, limit=24):
    fts_q = _to_fts_query(query)
    if not fts_q:
        return []
    rows = conn.execute(
        """
        SELECT
            fts.rowid AS chunk_id,
            fts.rank AS bm25_rank,
            c.file_id,
            c.page_num,
            c.chunk_index,
            c.text,
            f.path,
            f.filename,
            f.mtime,
            f.author
        FROM chunks_fts fts
        JOIN chunks c ON c.id = fts.rowid
        JOIN files f ON f.id = c.file_id
        WHERE chunks_fts MATCH ?
        ORDER BY fts.rank
        LIMIT ?
        """,
        (fts_q, limit),
    ).fetchall()
    return rows


def log_access(conn, query, file_path, file_id):
    conn.execute(
        "INSERT INTO access_log (query, file_path, file_id, opened_at) VALUES (?, ?, ?, ?)",
        (query, file_path, file_id, time.time()),
    )


def log_search_event(conn, query, result_count, clicked_rank, latency_ms=None):
    conn.execute(
        "INSERT INTO search_events (query, result_count, clicked_rank, timestamp) VALUES (?, ?, ?, ?)",
        (query, result_count, clicked_rank, time.time()),
    )


def get_access_count(conn, file_id):
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM access_log WHERE file_id = ?",
        (file_id,),
    ).fetchone()
    return row["cnt"] if row else 0


def get_watched_folders(conn):
    return conn.execute(
        "SELECT path FROM watched_folders WHERE active = 1"
    ).fetchall()


def add_watched_folder(conn, path):
    conn.execute(
        "INSERT OR IGNORE INTO watched_folders (path, added_at) VALUES (?, ?)",
        (path, time.time()),
    )


def reset_stale_indexing(conn):
    conn.execute(
        "UPDATE files SET index_status = 'pending' WHERE index_status = 'indexing'"
    )


def get_pending_files(conn):
    return conn.execute(
        "SELECT * FROM files WHERE index_status = 'pending' ORDER BY mtime DESC"
    ).fetchall()


def get_reindex_candidates(conn, model_name):
    return conn.execute(
        "SELECT * FROM files WHERE COALESCE(embedding_model, '') != ?",
        (model_name,),
    ).fetchall()


def get_cache(conn, query_hash):
    row = conn.execute(
        "SELECT results FROM query_cache WHERE query_hash = ? AND cached_at > ?",
        (query_hash, time.time() - 300),
    ).fetchone()
    return row["results"] if row else None


def set_cache(conn, query_hash, results_json):
    conn.execute(
        """INSERT INTO query_cache (query_hash, results, cached_at)
           VALUES (?, ?, ?)
           ON CONFLICT(query_hash) DO UPDATE SET results = ?, cached_at = ?""",
        (query_hash, results_json, time.time(), results_json, time.time()),
    )


def page_hash_exists(conn, page_hash, file_id):
    row = conn.execute(
        "SELECT id FROM pages WHERE page_hash = ? AND file_id != ?",
        (page_hash, file_id),
    ).fetchone()
    return row is not None


def upsert_page(conn, file_id, page_num, page_hash, quality_score, status, method):
    conn.execute(
        """INSERT INTO pages (file_id, page_num, page_hash, quality_score, extract_status, extraction_method)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(file_id, page_num) DO UPDATE SET
               page_hash = excluded.page_hash,
               quality_score = excluded.quality_score,
               extract_status = excluded.extract_status,
               extraction_method = excluded.extraction_method""",
        (file_id, page_num, page_hash, quality_score, status, method),
    )


def get_pages_needing_ocr(conn, limit=5):
    return conn.execute(
        """SELECT p.*, f.path as file_path
           FROM pages p
           JOIN files f ON f.id = p.file_id
           WHERE p.extract_status = 'needs_ocr'
           ORDER BY p.quality_score ASC
           LIMIT ?""",
        (limit,),
    ).fetchall()


def mark_page_ocr_done(conn, file_id, page_num):
    conn.execute(
        "UPDATE pages SET extract_status = 'ocr_done', extraction_method = 'ocr', ocr_attempts = ocr_attempts + 1 WHERE file_id = ? AND page_num = ?",
        (file_id, page_num),
    )


def mark_page_extracted(conn, file_id, page_num):
    conn.execute(
        "UPDATE pages SET extract_status = 'extracted', extraction_method = 'text' WHERE file_id = ? AND page_num = ?",
        (file_id, page_num),
    )


def get_page_stats(conn):
    total = conn.execute("SELECT COUNT(*) as c FROM pages").fetchone()["c"]
    rows = conn.execute(
        "SELECT extract_status, COUNT(*) as c FROM pages GROUP BY extract_status"
    ).fetchall()
    stats = {"total": total, "extracted": 0, "needs_ocr": 0, "ocr_done": 0, "duplicate": 0}
    for r in rows:
        status = r["extract_status"]
        if status in stats:
            stats[status] = r["c"]
    return stats
