# Product Specification: Personal Memory Layer for Files

> **Working title:** Unnamed (to be decided)
> **Tagline:** Your files remember what you meant.
> **Version:** 1.1 Spec (updated after two critique rounds)
> **Status:** Ready to build

---

## One-Line Description

A local background daemon that watches your folders, indexes your files semantically, learns your access patterns, and lets you retrieve anything from your own library using natural language — privately, instantly, without cloud.

---

## The Problem It Solves

People remember *what* they read. They don't remember *where* they saved it.

Traditional OS search expects a filename. Human memory stores a concept. This tool bridges that gap — locally, passively, and without requiring any change to how users currently organize (or fail to organize) their files.

---

## Target User (v1)

**Primary:** Researchers with large PDF libraries (100–1000+ papers)

**Why them first:** Pain is highest. Volume is largest. Most likely to have scanned PDFs (validates OCR investment). Most likely to have sensitive data (validates local-first approach). Will not upload unpublished work to cloud tools.

**Revenue target (post-validation):** Lawyers, consultants, analysts, journalists — people who lose billable hours searching, not existential peace of mind.

---

## Core Framing

**Not:** "Semantic search for files"
**Not:** "AI file retrieval"
**Not:** "Vector search for documents"

**Yes:** "Your files remember what you meant."

This framing is not marketing polish. It describes what the behavioral layer actually does. When a user searches "attention paper" and the tool surfaces exactly what they always open — they stop thinking "good search" and start thinking "this thing knows me." That transition from utility to habit is where retention lives.

---

## What v1 Does

1. Watch selected folders for new/modified files
2. Automatically parse and index PDF and TXT files
3. Handle scanned PDFs via OCR fallback with priority queue
4. Accept natural language queries via hotkey launcher
5. Return ranked results with matched paragraph snippets
6. Open file directly from results in default OS application
7. Log access behavior and search events to improve future rankings
8. Schema migration system from day one

---

## What v1 Does NOT Do

- No DOCX parsing
- No image/figure understanding (skipped entirely)
- No cloud sync
- No accounts
- No settings dashboard
- No onboarding wizard
- No themes or UI customization
- No analytics or telemetry
- No web interface
- No cross-document synthesis or Q&A
- No Memory Trails (post-v1)

---

## Architecture Overview

```
[Watched Folders]
       ↓
[File Watcher — watchdog]
       ↓
[Parser Layer]
   ├── PDF → PyMuPDF (text extraction)
   │         ↓ if page has <50 chars →
   │         [OCR Queue — priority-ordered]
   │         [pdf2image + pytesseract]
   └── TXT → direct read
       ↓
[Chunker — paragraph-level with neighbor context]
       ↓
[Embedding Model — sentence-transformers]
       ↓
[sqlite-vec — separated chunks + embeddings + logs]
       ↓
[FastAPI — local query endpoint + query cache]
       ↓
[Hotkey Launcher — Ctrl+Space]
       ↓
[Results UI — search box + snippet list + open file]
```

---

## Tech Stack

### Backend
| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python | Ecosystem, existing familiarity, Nyx Core overlap |
| API | FastAPI | Already in Nyx Core, lightweight |
| File watching | `watchdog` | Standard, cross-platform |

### Storage
| Component | Choice | Reason |
|-----------|--------|--------|
| Database | SQLite | Single file, transactional, portable, backs up with `cp` |
| Vector search | `sqlite-vec` | Vectors inside SQLite, no serialization ritual |

**Why not ChromaDB:** Adds dependency overhead, becomes maintenance obligation.
**Why not FAISS:** Doesn't persist natively — serialize/deserialize cycle on every restart, fragile across OS updates.

### Embedding
| Component | Choice |
|-----------|--------|
| Model | `all-MiniLM-L6-v2` or `bge-small-en` |
| Library | `sentence-transformers` |

Model choice matters less than chunking strategy (~3% vs ~30% quality impact). Pick either. Switch later with re-embed pipeline.

### Parsing
| Component | Choice |
|-----------|--------|
| PDF text extraction | `PyMuPDF` (fitz) |
| PDF→image for OCR | `pdf2image` |
| OCR engine | `pytesseract` + Tesseract (system install) |
| TXT | Direct read |

### UI
| Component | Choice |
|-----------|--------|
| Hotkey | `Ctrl+Space` |
| Framework | Minimal — plain system tray + floating window (decide at build time) |

---

## Detailed Component Specs

### 1. Schema and Migration (Build First)

Before any other table. Non-negotiable.

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at REAL
);

INSERT INTO schema_version VALUES (1, unixepoch());
```

Migration runner:

```python
def run_migrations(db):
    version = db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    if version < 2:
        run_migration_2(db)
        db.execute("INSERT INTO schema_version VALUES (2, unixepoch())")
    # etc.
```

**Why this first:** Schema will evolve — access logs, query embeddings, folder config, search sessions. Without migrations, schema changes mean deleting the database and reindexing. The irony of a memory tool forgetting your memory because of a schema change is too obvious to risk.

---

### 2. Full Database Schema

```sql
-- Migration tracking (always first)
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at REAL
);

-- Indexed files
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE,
    filename TEXT,
    mtime REAL,
    date_indexed REAL,
    ocr_used INTEGER DEFAULT 0,
    file_type TEXT  -- 'pdf' or 'txt'
);

-- Chunk text and metadata (SEPARATED from embeddings)
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    page_num INTEGER,
    chunk_index INTEGER,
    text TEXT
);

-- Chunk vectors (SEPARATED from metadata)
-- This allows re-embedding without touching chunk text
CREATE VIRTUAL TABLE chunk_embeddings USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);

-- Access log: what file was opened after what query
CREATE TABLE access_log (
    id INTEGER PRIMARY KEY,
    query TEXT,
    file_path TEXT,
    file_id INTEGER REFERENCES files(id),
    opened_at REAL
);

-- Search events: every search, including those with no click
CREATE TABLE search_events (
    id INTEGER PRIMARY KEY,
    query TEXT,
    result_count INTEGER,
    clicked_rank INTEGER,  -- NULL if nothing clicked
    timestamp REAL
);

-- Watched folders
CREATE TABLE watched_folders (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE,
    added_at REAL,
    active INTEGER DEFAULT 1
);
```

**Why chunks and chunk_embeddings are separated:** When the embedding model changes (and it will — better models come out), re-embedding should not require touching text or metadata. Decoupled from day one prevents painful schema surgery later.

**Why search_events is separate from access_log:** `access_log` records opens. `search_events` records everything — including searches where the user looked at results and clicked nothing. "Searched, never clicked" is a signal that results were irrelevant. "Searched, clicked result #3, not #1" is a signal that ranking needs work. Both are future training data. Store them now.

---

### 3. File Watcher

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and is_supported(event.src_path):
            queue_for_indexing(event.src_path, priority='normal')

    def on_modified(self, event):
        if not event.is_directory and is_supported(event.src_path):
            queue_for_indexing(event.src_path, priority='normal')

    def on_deleted(self, event):
        remove_from_index(event.src_path)

    def on_moved(self, event):
        # Handle file moves: update path, don't reindex content
        update_file_path(event.src_path, event.dest_path)

def is_supported(path):
    return path.endswith(('.pdf', '.txt'))
```

**Note on `on_moved`:** Files moved between watched folders should update the path in the database without triggering a full reindex. The content hasn't changed. This is easy to miss and results in duplicate index entries if ignored.

---

### 4. Parser Layer

#### PDF Parsing

```python
import fitz  # PyMuPDF

def parse_pdf(path):
    doc = fitz.open(path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text()
        if len(text.strip()) < 50:
            # Scanned page — add to OCR queue, don't block
            ocr_queue.add(path, page_num, priority=get_priority(path))
            text = ""  # placeholder until OCR completes
        pages.append((page_num, text))
    return pages
```

#### OCR Queue (Priority-Ordered)

```python
import heapq

class OCRQueue:
    def __init__(self):
        self._queue = []

    def add(self, path, page_num, priority='normal'):
        # Priority: recent=0, normal=1, large=2
        p = {'recent': 0, 'normal': 1, 'large': 2}[priority]
        heapq.heappush(self._queue, (p, path, page_num))

    def process_next(self):
        if self._queue:
            _, path, page_num = heapq.heappop(self._queue)
            return ocr_page(path, page_num)
```

**Why a queue:** A 400-page scanned dissertation triggers 400 image renders and 400 OCR passes. Without a queue, one document blocks indexing for everything else. Priority: recently accessed files first, large scanned jobs last.

#### OCR Page

```python
from pdf2image import convert_from_path
import pytesseract

def ocr_page(path, page_num):
    images = convert_from_path(path, first_page=page_num+1, last_page=page_num+1)
    if images:
        return pytesseract.image_to_string(images[0])
    return ""
```

#### OCR Availability Check (At Startup)

```python
import shutil

def check_ocr():
    if shutil.which("tesseract") is None:
        log.warning(
            "Tesseract not found. Scanned PDFs will be skipped. "
            "Install with: apt install tesseract-ocr (Linux) "
            "or brew install tesseract (macOS)"
        )
        return False
    return True
```

No silent failure. User is told exactly what's missing and how to fix it.

---

### 5. Chunking Strategy

**Unit:** Paragraph (split on double newline `\n\n`)

**Context window:** Each chunk includes the paragraph before and after it

```python
def chunk_text(text):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    for i, para in enumerate(paragraphs):
        prev = paragraphs[i-1] if i > 0 else ""
        next_ = paragraphs[i+1] if i < len(paragraphs)-1 else ""
        chunk = "\n\n".join(filter(None, [prev, para, next_]))
        chunks.append({
            'text': chunk,
            'core_paragraph': para,
            'chunk_index': i
        })
    return chunks
```

**Why paragraph-level:** Humans remember ideas in context. Nobody remembers "token 1042 through 1537." They remember "the section where the author argued memory scales poorly." The chunk reflects that.

**Why neighbor context:** Retrieval quality improves when the embedding captures the paragraph's semantic neighborhood, not just its isolated content.

---

### 6. Embedding

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed(text):
    return model.encode(text, normalize_embeddings=True).tolist()
```

**Token limit awareness:** Most sentence-transformer models have a 512-token limit. Chunks longer than this get silently truncated. Add a check:

```python
MAX_TOKENS = 400  # leave headroom

def safe_embed(text):
    tokens = model.tokenize([text])['input_ids'][0]
    if len(tokens) > MAX_TOKENS:
        # truncate at word boundary
        text = text[:MAX_TOKENS * 4]  # rough char estimate
    return embed(text)
```

This is a known failure mode that most RAG tutorials skip. Without it, long paragraphs get truncated mid-sentence at embedding time, producing garbage vectors with no error raised.

---

### 7. Indexing Pipeline

```python
def index_file(path):
    # 1. Parse
    if path.endswith('.pdf'):
        pages = parse_pdf(path)
    else:
        pages = [(0, open(path).read())]

    # 2. Store file record
    file_id = db.insert_file(path)

    # 3. Chunk, embed, store
    for page_num, text in pages:
        chunks = chunk_text(text)
        for chunk in chunks:
            embedding = safe_embed(chunk['text'])
            chunk_id = db.insert_chunk(file_id, page_num, chunk)
            db.insert_embedding(chunk_id, embedding)
```

**Cold start ordering:** When indexing a new folder, sort files by `mtime` descending before queuing. Most recently touched files index first. User gets useful results within minutes, not after waiting for the full library.

---

### 8. Query Flow

```python
def search(query, limit=8):
    # Check cache first
    cached = query_cache.get(query)
    if cached:
        return cached

    # Embed query
    query_embedding = safe_embed(query)

    # Vector search
    raw_results = db.vector_search(query_embedding, limit=limit * 3)

    # Re-rank
    ranked = rank_results(raw_results, query)[:limit]

    # Cache and return
    query_cache.set(query, ranked)
    return ranked
```

---

### 9. Ranking Formula

```python
def score(semantic_sim, mtime, access_count):
    recency = normalize_recency(mtime)      # 0–1, decays over time
    access = normalize_access(access_count) # 0–1, log scale

    return (0.80 * semantic_sim) + (0.10 * recency) + (0.10 * access)
```

**v1 weights: 0.80 / 0.10 / 0.10**

Original proposal was 0.60/0.25/0.15. Corrected because: recency at 0.25 would surface a file modified yesterday over the paper that's actually relevant. Semantic dominates until the access log earns its weight through sufficient signal. Adjust weights empirically as behavioral data accumulates.

---

### 10. Query Cache

```python
from functools import lru_cache
import time

class QueryCache:
    def __init__(self, ttl=300):  # 5 min TTL
        self._cache = {}
        self.ttl = ttl

    def get(self, query):
        if query in self._cache:
            result, ts = self._cache[query]
            if time.time() - ts < self.ttl:
                return result
        return None

    def set(self, query, result):
        self._cache[query] = (result, time.time())
```

**Why:** Humans repeat approximate queries. "Attention paper," "attention memory paper," "paper about attention scaling" are the same search intent. After 1000 PDFs and 200k chunks, latency grows. Cache shaves noticeable time off perceived responsiveness.

---

### 11. Results Display

Each result shows:

```
[paper_on_transformer_memory.pdf]
"...the authors argue that fixed-length context windows
impose a fundamental ceiling on reasoning depth,
particularly for tasks requiring..."

[Open]
```

No score numbers. The snippet is the confidence signal. Users recognize the passage or they don't. Show 5–8 results. Log the click (or lack of it) in `search_events`.

---

### 12. Retrieval Evaluation Dataset

Build this alongside the parser. Not after.

```json
[
  {
    "query": "paper comparing RAG and fine-tuning",
    "correct_file": "rag_vs_finetuning_2024.pdf"
  },
  {
    "query": "attention mechanism context window limits",
    "correct_file": "attention_is_all_you_need.pdf"
  }
]
```

100 pairs minimum. Measure top-1 and top-3 accuracy. Run this benchmark every time you change chunking strategy, ranking formula, or embedding model.

**Without this:** you're doing astrology. Every change is a gut feeling. "I think this feels better" is not engineering.

**With this:** every architectural decision produces a number. You can prove whether paragraph chunking beats fixed-window. You can prove whether the behavioral layer improves results. You can prove whether switching models is worth it.

---

### 13. API Endpoints

```
GET  /search?q={query}&limit={n}     → ranked results with snippets
POST /index?path={folder_path}       → add folder to watch list
GET  /status                         → daemon health, files indexed, OCR status
GET  /files                          → list all indexed files
DELETE /files?path={file_path}       → remove file from index
POST /log-open                       → record file open event
```

---

## Dependencies

```
# Core
fastapi
uvicorn
watchdog
sentence-transformers
sqlite-vec
PyMuPDF  # fitz

# OCR (soft dependency — system Tesseract required separately)
pdf2image
pytesseract

# Standard library
sqlite3
pathlib
logging
heapq
```

---

## Build Order

1. Schema + migration runner
2. Retrieval evaluation dataset (100 pairs)
3. PDF parser (PyMuPDF + OCR fallback)
4. TXT parser
5. Chunker (paragraph + neighbor context)
6. Embedding pipeline (with token limit guard)
7. sqlite-vec schema (separated chunks + embeddings)
8. Cold-start indexer (mtime-ordered queue)
9. OCR priority queue
10. File deduplication check
11. FastAPI search endpoint
12. Ranking formula
13. Query cache
14. File watcher (watchdog)
15. `on_moved` handler
16. Access log + search_events logging
17. Hotkey launcher UI
18. Open file on click (OS default handler)
19. Daemon startup (OCR check, folder config)

---

## What We Know But Haven't Fully Considered

These are real problems that will surface during build. Not blocking for v1 start, but need answers before shipping.

### 1. File Deduplication
**Problem:** Same PDF saved in two watched folders gets indexed twice. Search returns duplicate results.
**Solution:** Hash file contents on index. If hash exists in DB, skip. Store hash in `files` table.
**Why it matters:** Researchers often have the same paper in `Downloads/`, `Papers/`, and a project folder. Triple results for one file destroys trust.

### 2. Model Versioning
**Problem:** If the embedding model changes (MiniLM → bge-small → anything better), old embeddings in the DB were produced by the old model. Mixing embeddings from different models produces garbage results.
**Solution:** Store model name and version in the `files` table. On model change, flag all embeddings as stale and reindex. The separated chunk/embedding schema makes this possible without losing text data.
**Why it matters:** You will want to upgrade the model eventually. Without this, you delete the DB and start over.

### 3. Re-embedding Pipeline
**Problem:** Related to above. How do you re-embed 10,000 chunks when switching models?
**Solution:** Background job that iterates `chunks` table, re-embeds, updates `chunk_embeddings`. Runs at low priority. Existing embeddings remain searchable until replaced.
**Why it matters:** A tool that requires full reindex on model upgrade will never get upgraded.

### 4. Memory Usage of Sentence-Transformers
**Problem:** `sentence-transformers` loads the full model into memory on daemon startup. MiniLM is ~90MB RAM. bge-small is similar. This is a background daemon — it should be invisible.
**Solution:** Load model once at startup, keep in memory. Don't reload per query. For very memory-constrained environments, consider ONNX-quantized versions of the models (4× smaller, minimal quality loss).
**Why it matters:** If the daemon uses 500MB RAM, users will kill it.

### 5. Tokenization Limit (Addressed in Spec, Worth Flagging Again)
**Problem:** sentence-transformer models have a 512-token hard limit. Chunks exceeding this are silently truncated. A 1000-word paragraph gets cut in half with no warning.
**Solution:** Already in spec — `safe_embed()` with token check. Just don't skip implementing it.
**Why it matters:** Silent truncation produces incorrect embeddings with no error. Retrieval degrades mysteriously.

### 6. Password-Protected PDFs
**Problem:** PyMuPDF raises an exception on encrypted PDFs.
**Solution:** Wrap parser in try/except. Log as "skipped — password protected." Don't crash the daemon.
**Why it matters:** Researchers sometimes have DRM-protected papers. One bad file shouldn't kill the indexer.

### 7. Corrupt or Malformed PDFs
**Problem:** Some PDFs have broken internal structure. PyMuPDF handles most gracefully but not all.
**Solution:** Wrap every file parse in try/except. Log failures with path and error. Continue indexing the rest.
**Why it matters:** Same as above. One corrupt file in 500 shouldn't stop the queue.

### 8. Cross-Platform Hotkey Handling
**Problem:** `Ctrl+Space` conflicts with input method switching on Linux (IBus, Fcitx). On macOS it conflicts with Spotlight. On Windows it's usually free.
**Solution:** Make the hotkey configurable in a simple config file. Default to `Ctrl+Space` on Windows, something else on Linux/macOS, and document the conflict.
**Why it matters:** The hotkey is the entire UI. If it doesn't register or conflicts with the OS, the product doesn't exist for that user.

### 9. First-Run Experience
**Problem:** Daemon starts, watches nothing, indexes nothing. User doesn't know what to do.
**Solution:** On first run, open a minimal setup prompt: pick folders to watch. Store in `watched_folders` table. Then disappear.
**Why it matters:** "Forget it exists" only works after you've told it where to look. The first-run moment is the only time the product is allowed to ask for attention.

### 10. Index Size Estimation
**Problem:** Unknown how large the SQLite DB grows per 100 PDFs.
**Rough estimate:** Average academic PDF is ~50 pages, ~25k words. With neighbor-context chunks at ~200 words each, that's ~125 chunks per PDF. At 384-float embeddings (1.5KB each), 100 PDFs ≈ ~19MB for embeddings alone, plus text. 1000 PDFs ≈ 200–400MB.
**Why it matters:** SQLite handles this comfortably. But users need to know where the DB lives and roughly how large it will grow. Surprises on disk space kill trust.

### 11. Incremental Re-indexing vs Full Reindex
**Problem:** File is modified. Do you re-index the whole file or diff it?
**Solution for v1:** Full file reindex on modification. Delete all chunks for that `file_id`, reparse, rechunk, re-embed. Simple and correct.
**Why it matters:** Diffing PDFs at the chunk level is complex and not worth it for v1. Full reindex of a single file is fast enough. Just make sure `ON DELETE CASCADE` is set on the chunks foreign key.

### 12. Daemon Crash Recovery
**Problem:** Daemon crashes mid-index. Files are partially indexed. On restart, how do you know what was completed?
**Solution:** Add `index_status` to `files` table: `pending`, `indexing`, `complete`, `failed`. On startup, reset any `indexing` rows to `pending` and requeue them.
**Why it matters:** Without this, a crash leaves ghost entries — files that appear indexed but aren't. Search silently misses them.

---

## Non-Goals (Permanently)

- No cloud. No exceptions.
- No accounts.
- No telemetry.
- No syncing to any external service.
- No "chat with your documents" feature.
- No browser extension.
- No mobile app.
- No multi-user support.

If any of these become tempting, re-read the tagline: *Your files remember what you meant.* Local. Passive. Private. Invisible.

---

## Post-v1 Roadmap (Do Not Touch Until v1 Ships)

| Feature | Why |
|---------|-----|
| Memory Trails | Store search journeys. Reconstruct how you discovered an idea. |
| DOCX support | Expands file coverage meaningfully |
| Adaptive ranking weights | Let access patterns shift 0.80/0.10/0.10 over time |
| Cross-document synthesis | "Which papers mention X?" — different complexity class |
| ONNX quantized models | Reduce memory footprint for low-RAM machines |
| Lawyer/consultant vertical | Different UI needs, higher willingness to pay |
