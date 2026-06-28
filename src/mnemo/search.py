import json
import time
import hashlib
import re
from pathlib import Path

from . import db as db_module
from .embedder import safe_embed, get_model

SEMANTIC_WEIGHT = 0.80
RECENCY_WEIGHT = 0.10
ACCESS_WEIGHT = 0.10

HYBRID_SEMANTIC_WEIGHT = 0.70
HYBRID_FTS_WEIGHT = 0.30
HEADING_BOOST = 0.15
FILENAME_BOOST_PER_TERM = 0.10
FILENAME_BOOST_MAX = 0.25


def normalize_recency(mtime, now=None):
    if now is None:
        now = time.time()
    age_days = (now - mtime) / 86400
    score = 1.0 / (1.0 + age_days * 0.1)
    return max(0.0, min(1.0, score))


def normalize_access(access_count):
    if access_count <= 0:
        return 0.0
    return min(1.0, access_count / 20.0)


def is_index_page(snippet):
    lines = snippet.split("\n")
    index_lines = 0
    for line in lines:
        clean = line.strip()
        if re.match(r"^[\w\s\-]+,?\s+\d{1,4}", clean):
            index_lines += 1
    if len(lines) > 2 and index_lines / len(lines) > 0.5:
        return True
    if re.search(r"(?:index|contents|glossary)", snippet[:200].lower()):
        return True
    return False


def _heading_boost(query, snippet):
    q = query.lower().strip()
    s = snippet[:200].lower()
    if q in s:
        return HEADING_BOOST
    terms = [t for t in re.split(r"\W+", q) if len(t) > 1]
    if len(terms) >= 2:
        idx = -1
        for t in terms:
            idx = s.find(t, idx + 1)
            if idx == -1:
                break
        else:
            return HEADING_BOOST * 0.7
    return 0.0


def _filename_boost(query, filename):
    stem = Path(filename).stem.lower().replace("_", " ").replace("-", " ")
    terms = [t for t in re.split(r"\W+", query.lower().strip()) if len(t) > 1]
    if not terms:
        return 0.0
    boost = 0.0
    for t in terms:
        if t in stem:
            boost += FILENAME_BOOST_PER_TERM
    return min(boost, FILENAME_BOOST_MAX)


def search(conn, query, limit=8):
    start = time.time()
    query_hash = hashlib.sha256(query.encode()).hexdigest()
    cached = db_module.get_cache(conn, query_hash)
    if cached:
        elapsed = round((time.time() - start) * 1000, 1)
        return json.loads(cached), True, elapsed

    model = get_model()
    if model is None:
        return [], False, 0

    embedding, _ = safe_embed(query)

    # 1. Vector semantic search
    vec_raw = db_module.vector_search(conn, embedding, limit=limit * 3)

    # 2. FTS5 keyword search
    fts_raw = db_module.fts_search_detailed(conn, query, limit=limit * 3)

    # Normalize FTS BM25 ranks (more negative = better match)
    fts_norm = {}
    if fts_raw:
        ranks = [abs(r["bm25_rank"]) for r in fts_raw]
        max_rank = max(ranks) if ranks else 1
        for r in fts_raw:
            fts_norm[r["chunk_id"]] = 1.0 - (abs(r["bm25_rank"]) / max_rank) if max_rank > 0 else 0.0

    # Build chunk map from vector results
    chunks = {}
    for row in vec_raw:
        cid = row["chunk_id"]
        semantic_sim = max(0.0, 1.0 - row["distance"])
        chunks[cid] = {
            "file_id": row["file_id"],
            "filename": row["filename"],
            "path": row["path"],
            "page_num": row["page_num"],
            "snippet": row["text"],
            "mtime": row["mtime"],
            "author": row["author"] or "",
            "semantic": semantic_sim,
        }

    # Merge FTS-only chunks (not found by vector search)
    for r in fts_raw:
        cid = r["chunk_id"]
        if cid not in chunks:
            chunks[cid] = {
                "file_id": r["file_id"],
                "filename": r["filename"],
                "path": r["path"],
                "page_num": r["page_num"],
                "snippet": r["text"],
                "mtime": r["mtime"],
                "author": r["author"] or "",
                "semantic": 0.35,  # estimated semantic score for keyword-only matches
            }

    results = []
    for cid, info in chunks.items():
        semantic_sim = info["semantic"]
        fts_score = fts_norm.get(cid, 0.0)
        access_count = db_module.get_access_count(conn, info["file_id"])

        # Combined hybrid score
        hybrid = (
            HYBRID_SEMANTIC_WEIGHT * semantic_sim
            + HYBRID_FTS_WEIGHT * fts_score
        )

        # Heading boost
        heading = _heading_boost(query, info["snippet"])
        # Filename boost
        fn_boost = _filename_boost(query, info["filename"])

        # Final score with recency + access + boosts + penalty
        recency = normalize_recency(info["mtime"])
        access = normalize_access(access_count)
        penalty = 0.8 if is_index_page(info["snippet"]) else 1.0

        score = (
            hybrid
            + RECENCY_WEIGHT * recency
            + ACCESS_WEIGHT * access
            + heading
            + fn_boost
        ) * penalty

        results.append({
            "chunk_id": cid,
            "file_id": info["file_id"],
            "filename": info["filename"],
            "path": info["path"],
            "page_num": info["page_num"],
            "snippet": info["snippet"],
            "score": round(score, 4),
            "author": info.get("author", ""),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:limit]

    chunk_ids = [r["chunk_id"] for r in results]
    metadata = db_module.get_chunk_metadata_batch(conn, chunk_ids)
    for r in results:
        meta = metadata.get(r["chunk_id"], {})
        r["heading"] = meta.get("heading")
        r["concepts"] = meta.get("concepts", [])

    db_module.set_cache(conn, query_hash, json.dumps(results))
    db_module.log_search_event(conn, query, len(results), None)

    elapsed = round((time.time() - start) * 1000, 1)
    return results, False, elapsed
