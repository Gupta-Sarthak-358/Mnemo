import hashlib
import logging
from pathlib import Path

from . import db as db_module
from . import parser
from .chunker import chunk_text
from .embedder import load_model, embed_batch
from .enrich import extract_heading, extract_concepts
from .config import load_config

logger = logging.getLogger(__name__)


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def index_file(conn, path, model_name):
    path_obj = Path(path)
    path_str = str(path_obj)
    file_type = "pdf" if path_obj.suffix.lower() == ".pdf" else "txt"

    existing = db_module.file_exists_by_path(conn, path_str)
    if existing:
        if existing["index_status"] != "pending":
            fhash = file_hash(path_str)
            if fhash == existing["hash"]:
                return existing["id"]

    fhash = file_hash(path_str)
    if not existing and db_module.file_exists_by_hash(conn, fhash):
        logger.info("Skipping duplicate: %s", path_str)
        return None

    if file_type == "pdf":
        pages, total_pages = parser.parse_pdf(path_str)
    else:
        pages, total_pages = parser.parse_txt(path_str)

    if not pages:
        logger.warning("No content extracted from %s", path_str)
        return None

    author = ""
    if file_type == "pdf":
        meta = parser.get_pdf_metadata(path_str)
        author = meta.get("author", "")

    if existing:
        file_id = existing["id"]
        db_module.delete_file_chunks(conn, file_id)
        conn.execute(
            """UPDATE files SET mtime=?, ocr_used=?, total_pages=?, hash=?,
               index_status='indexing', embedding_model=?, author=? WHERE id=?""",
            (path_obj.stat().st_mtime, 0, total_pages, fhash, model_name, author, file_id),
        )
    else:
        file_id = db_module.insert_file(
            conn, path_str, path_obj.stat().st_mtime, file_type, fhash, model_name, author
        )
        conn.execute(
            "UPDATE files SET total_pages=? WHERE id=?",
            (total_pages, file_id),
        )

    db_module.set_file_indexing(conn, file_id)
    conn.commit()

    all_chunks = []
    ocr_count = 0
    for page in pages:
        if page["ocr_needed"]:
            ocr_count += 1
            db_module.upsert_page(
                conn, file_id, page["page_num"], "", page["quality"], "needs_ocr", "pending",
            )
            continue

        db_module.upsert_page(
            conn, file_id, page["page_num"], page["page_hash"], page["quality"], "extracted", "text",
        )

        page_chunks = chunk_text(page["text"], base_chunk_index=len(all_chunks))
        for c in page_chunks:
            c["page_num"] = page["page_num"]
        all_chunks.extend(page_chunks)

    conn.commit()

    total_chunks = len(all_chunks)
    BATCH_SIZE = 32
    for i in range(0, total_chunks, BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        try:
            results = embed_batch(texts)
        except Exception as e:
            logger.error("Embedding failed for %s batch %d: %s", path_str, i, e)
            db_module.update_file_status(conn, file_id, "failed")
            conn.commit()
            return None

        for chunk_data, (embedding, final_text) in zip(batch, results):
            chunk_data["text"] = final_text
            chunk_id = db_module.insert_chunk(
                conn,
                file_id,
                chunk_data["page_num"],
                chunk_data["chunk_index"],
                chunk_data["text"],
            )
            db_module.insert_embedding(conn, chunk_id, embedding)
            db_module.insert_fts(conn, chunk_id, chunk_data["text"])
            heading = extract_heading(chunk_data["text"])
            concepts = extract_concepts(chunk_data["text"])
            db_module.insert_chunk_metadata(conn, chunk_id, heading, concepts)

        conn.commit()

    db_module.update_file_status(conn, file_id, "complete", total_chunks)
    conn.commit()

    if ocr_count:
        logger.info(
            "Indexed %s: %d chunks (%d OCR pending)", path_str, total_chunks, ocr_count,
        )
    else:
        logger.info("Indexed %s: %d chunks", path_str, total_chunks)
    return file_id


def process_ocr_queue(conn):
    pages = db_module.get_pages_needing_ocr(conn, limit=5)
    for page in pages:
        text = parser.ocr_page(page["file_path"], page["page_num"])
        if not text:
            db_module.mark_page_ocr_done(conn, page["file_id"], page["page_num"])
            conn.commit()
            continue

        quality = parser.assess_page_quality(text)
        if quality < parser.OCR_QUALITY_THRESHOLD:
            db_module.mark_page_ocr_done(conn, page["file_id"], page["page_num"])
            conn.commit()
            continue

        page_chunks = chunk_text(text)

        for chunk_data in page_chunks:
            chunk_data["page_num"] = page["page_num"]
            try:
                embedding, final_text = embed_batch([chunk_data["text"]])[0]
            except Exception as e:
                logger.error(
                    "Embedding failed for OCR %s page %d: %s",
                    page["file_path"], page["page_num"], e,
                )
                continue
            chunk_data["text"] = final_text
            chunk_id = db_module.insert_chunk(
                conn,
                page["file_id"],
                chunk_data["page_num"],
                chunk_data["chunk_index"],
                chunk_data["text"],
            )
            db_module.insert_embedding(conn, chunk_id, embedding)
            db_module.insert_fts(conn, chunk_id, chunk_data["text"])
            heading = extract_heading(chunk_data["text"])
            concepts = extract_concepts(chunk_data["text"])
            db_module.insert_chunk_metadata(conn, chunk_id, heading, concepts)

        db_module.mark_page_ocr_done(conn, page["file_id"], page["page_num"])
        conn.execute(
            "UPDATE files SET ocr_used=1 WHERE id=?",
            (page["file_id"],),
        )
        conn.commit()
        logger.info(
            "OCR completed: %s page %d (%d chunks)",
            page["file_path"], page["page_num"], len(page_chunks),
        )


def index_folder(conn, folder_path, model_name):
    path = Path(folder_path)
    if not path.exists():
        logger.warning("Folder does not exist: %s", folder_path)
        return

    files = []
    for ext in ("*.pdf", "*.txt"):
        files.extend(path.rglob(ext))

    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    for fpath in files:
        try:
            index_file(conn, fpath, model_name)
        except Exception as e:
            logger.error("Error indexing %s: %s", fpath, e)


def initial_index(conn):
    config = load_config()
    model_name = config["embedding_model"]
    load_model(model_name)

    db_module.reset_stale_indexing(conn)
    conn.commit()

    folders = db_module.get_watched_folders(conn)
    for row in folders:
        index_folder(conn, row["path"], model_name)
