# Mnemo — Product Specification (Current State)

> **This document reflects what is actually built, not what was planned.**
> Version: Post-v1 Alpha
> Last updated: June 2026

---

## What Mnemo Is

A local background daemon that watches folders, indexes PDF and TXT files semantically, learns access patterns, and lets users retrieve anything from their library using natural language — privately, instantly, without cloud.

**Tagline:** Find what you remember, not what you can describe.

---

## Current Architecture

```
[Watched Folders]
       ↓
[File Watcher — watchdog]
       ↓
[Parser Layer]
   ├── PDF → PyMuPDF (text extraction)
   │         ↓ page has <50 chars extracted →
   │         [OCR Queue — priority-ordered]
   │         [pdf2image + pytesseract]
   └── TXT → direct read
       ↓
[Chunker — paragraph-level with neighbor context]
       ↓
[Embedding — sentence-transformers / safe_embed()]
       ↓
[sqlite-vec — separated chunks + embeddings]
[FTS5 — full-text index for hybrid search]
       ↓
[Hybrid Ranking — semantic 0.70 + FTS5 0.30]
[+ heading boost 0.15 + filename boost 0.10]
[+ index-page penalty 0.80×]
[+ sentence scoring for snippet extraction]
       ↓
[FastAPI — local query endpoint]
       ↓
[Qt Launcher — Ctrl+M → floating window]
       ↓
[Results UI — grouped cards + snippets + concepts]
```

---

## Tech Stack (Actual)

| Component | Technology |
|-----------|-----------|
| Language | Python |
| API | FastAPI |
| File watching | watchdog |
| Database | SQLite (WAL mode) |
| Vector search | sqlite-vec |
| Full-text search | FTS5 (built into SQLite) |
| Embedding model | all-MiniLM-L6-v2 (sentence-transformers) |
| PDF parsing | PyMuPDF (fitz) |
| OCR | pdf2image + pytesseract + system Tesseract |
| UI framework | PyQt5 / Qt |
| Hotkey | pynput (global) |

---

## Database Schema (Current)

```sql
-- Migration tracking
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
    file_hash TEXT,           -- for deduplication
    index_status TEXT DEFAULT 'complete'  -- pending/indexing/complete/failed
);

-- Chunk text and metadata (SEPARATED from embeddings)
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    page_num INTEGER,
    chunk_index INTEGER,
    text TEXT,
    is_heading INTEGER DEFAULT 0
);

-- Chunk vectors (SEPARATED — allows re-embedding on model change)
CREATE VIRTUAL TABLE chunk_embeddings USING vec0(
    chunk_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);

-- FTS5 full-text index for hybrid search
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='id'
);

-- Access log
CREATE TABLE access_log (
    id INTEGER PRIMARY KEY,
    query TEXT,
    file_path TEXT,
    file_id INTEGER REFERENCES files(id),
    opened_at REAL
);

-- Every search event including no-click searches
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

-- Recent searches (shown on empty state)
CREATE TABLE recent_searches (
    id INTEGER PRIMARY KEY,
    query TEXT,
    searched_at REAL
);
```

**Key schema decisions:**
- `chunks` and `chunk_embeddings` are separate — re-embedding on model upgrade doesn't lose text data
- `files.file_hash` enables deduplication (same PDF in two watched folders)
- `files.index_status` enables crash recovery — `indexing` rows reset to `pending` on daemon restart
- `schema_version` enables safe schema evolution without full reindex

---

## Hybrid Search

Pure vector search failed on two classes of queries:
- Numeric queries ("Error 404" → retrieves chapter 404)
- Exact keyword queries where the term appears verbatim

Solution: hybrid retrieval with FTS5.

```python
SEMANTIC_WEIGHT = 0.70
FTS_WEIGHT = 0.30

def hybrid_search(query, limit=8):
    query_embedding = safe_embed(query)

    # Vector results
    vector_results = db.vector_search(query_embedding, limit=limit * 3)

    # FTS5 results
    fts_results = db.fts_search(query, limit=limit * 3)

    # Merge and re-rank
    merged = merge_results(vector_results, fts_results,
                           semantic_w=SEMANTIC_WEIGHT, fts_w=FTS_WEIGHT)

    return apply_boosts(merged)[:limit]
```

---

## Ranking Boosts

Applied on top of hybrid score:

```python
def apply_boosts(results):
    for r in results:
        score = r.base_score

        # Heading boost — headings are high-signal
        if r.is_heading:
            score += 0.15

        # Filename boost — query matches filename = strong signal
        if query_terms_in_filename(r.query, r.filename):
            score += 0.10

        # Index page penalty — pages with >50% "term → number" lines
        if r.is_index_page:
            score *= 0.80

        r.final_score = score
    return sorted(results, key=lambda r: r.final_score, reverse=True)
```

---

## Sentence Scoring for Snippet Extraction

Choosing which sentence from a chunk to show as the snippet:

```python
def score_sentence(sentence, query_terms):
    score = 0
    sentence_lower = sentence.lower()

    # Exact phrase match
    if full_query in sentence_lower:
        score += 5

    # Individual term matches
    for term in query_terms:
        if term in sentence_lower:
            score += 3

    # Consecutive terms
    if consecutive_terms_present(sentence_lower, query_terms):
        score += 2

    # Sentence is a heading
    if looks_like_heading(sentence):
        score += 1

    return score
```

---

## Safe Embedding

Most sentence-transformer tutorials skip this. Models have a 512-token hard limit. Exceeding it causes silent truncation producing garbage vectors.

```python
MAX_TOKENS = 400  # leave headroom below the 512 limit

def safe_embed(text):
    tokens = model.tokenize([text])['input_ids'][0]
    if len(tokens) > MAX_TOKENS:
        # truncate at word boundary
        words = text.split()
        while len(model.tokenize([' '.join(words)])['input_ids'][0]) > MAX_TOKENS:
            words = words[:-1]
        text = ' '.join(words)
    return model.encode(text, normalize_embeddings=True).tolist()
```

---

## OCR Pipeline

```
Open PDF
    ↓
Per-page text extraction (PyMuPDF)
    ↓
Page has <50 chars? → add to OCR queue (priority by recency)
Page has text? → chunk normally
    ↓
OCR queue processes in background
    ↓
OCR results indexed same as regular text
```

**OCR completion:** 1474 pages → 954 → 244 → 44 → 0. Daemon remained responsive throughout. Search latency stayed at 30–45ms during OCR processing.

**OCR availability check at startup:**
```python
def check_ocr():
    if shutil.which("tesseract") is None:
        log.warning("Tesseract not found. Scanned PDFs will be skipped. "
                    "Install: apt install tesseract-ocr / brew install tesseract")
        return False
    return True
```

No silent failure. User is told what's missing and how to fix it.

OCR is considered **done for v1**. Don't touch it again until users produce examples it genuinely fails on.

---

## Qt UI — Current State

**Window type:** Floating launcher (not a full desktop app)

**Hotkey:** `Ctrl+M` (global, registered via pynput)

*Note: Ctrl+Space stolen by Windows. Ctrl+Alt combinations produce AltGr characters on international keyboards (Ctrl+Alt+M → ṁ). Ctrl+M was clean across tested configurations.*

**Window lifecycle:**
- `setQuitOnLastWindowClosed(False)` — critical. Without this, hiding the window kills the Qt app.
- Hotkey shows/hides window. Does not restart it.
- `pyqtSignal()` (toggleRequested) for cross-thread hotkey → Qt communication. `QTimer.singleShot(0, toggle)` was unreliable.

**Empty state:**
- "Continue Reading" section (most recently opened files)
- Recent searches list (saved on file open, not on keystroke, deduped, capped at 20)

**Search state:**
- 300ms debounce after 3rd character (3-char minimum to avoid noise)
- Results appear as grouped cards

**Result card format:**
```
[Book Title — Author]
─ 5 matches ──────────────────────
p.307  Heading text
       Snippet with highlighted query terms...

p.521  Another heading
       Another snippet...

◆ Why this matched: concept1 · concept2 · concept3
[▼ More context]
```

**Score labels** (not raw numbers):
- ≥ 0.85 → Excellent
- ≥ 0.70 → Strong
- ≥ 0.50 → Good
- < 0.50 → Fair

**Grouping:** Multiple results from the same document are grouped into one card with sub-rows per page. Cleaner than listing the same book five times.

**Window geometry persistence** — size and position saved between sessions.

**Settings dialog:** Hotkey recording. User can change the hotkey.

**Theme detection:** Windows registry check for light/dark mode.

---

## Benchmark Results

**Corpus:** 190 queries across 12 categories
**Scope:** 170 non-negative queries evaluated for accuracy

| Metric | Result |
|--------|--------|
| Top-3 accuracy | **82%** |
| "Half-remembered memory" subset | **100%** |
| Average search latency | 28–45ms |

**Benchmark categories:**
- Exact keywords
- Acronyms
- Concepts
- Natural questions
- Half-remembered searches
- Visual memory ("the book with the wild boar cover")
- Cross-domain
- Ambiguous
- Comparative
- Typo queries
- Human memory fragments
- Negative queries

**Benchmark files:** `benchmarks/queries_v1.json`, `queries_v2.json`, `queries_v3.json`
**Results history:** `benchmarks/results/yyyy-mm-dd.json`

The queries/results separation means you can prove whether a change helped or not. Feelings are not evidence.

---

## What's Fully Working

- PDF and TXT parsing
- Lazy OCR (complete)
- Paragraph chunking with neighbor context
- Hybrid search (semantic 0.70 + FTS5 0.30)
- Heading boost (+0.15) and filename boost (+0.10)
- Index-page penalty (0.80×)
- Sentence-scored snippet extraction
- Context expansion (▼ More context)
- Same-document grouping with per-page sub-rows
- Recent searches (save on open, deduplicated, capped at 20)
- 3-character minimum search threshold
- 300ms debounce
- Theme detection (Windows registry)
- Settings dialog with hotkey recording
- Window geometry persistence
- "Continue Reading" + "Recent Searches" empty state
- Score labels (Excellent / Strong / Good / Fair)
- "Why this matched" concept tags (◆ icon)
- Highlighted query terms in snippets
- Global hotkey (Ctrl+M via pynput)
- Window show/hide lifecycle (correct — not restart)
- Page numbers displayed in results
- File open from result (default OS application)
- Background OCR queue (priority-ordered)
- Schema migration system (ADR log maintained, 9+ ADRs)
- Debugging CLI (`mnemo debug inspect-pdf`)

---

## Known Remaining Issues

1. **Reliable page jumping** — `#page=N` in browser URI ignored by some PDF viewers. **Resolved for Chrome/Brave** (verified working). Edge has known inconsistencies (scroll position caching) — mitigated with `?t=<timestamp>` cache-buster. Viewer detection priority: SumatraPDF → Chrome → Brave → Edge → system default.
2. **Result card typography** — Underscores in filenames, ".pdf" visible, spacing could be tighter.
3. **Smooth scrolling** — Qt default scroll sensitivity too aggressive.
4. **Better word highlighting** — Current highlighting functional but not polished.
5. **Dead code cleanup** — Unused `SearchWorker`, `QObject`, `QShortcut`, `QKeySequence` remnants.
6. **Cross-encoder reranker** — Not implemented. High potential ROI once 30–50 real failure cases justify it.

---

## File Scope

**v1:** `.pdf` (with OCR fallback) and `.txt`

**Post-v1 (do not add until v1 is stable):** `.docx`, `.md`, code files, `.epub`

---

## What Has Been Deliberately Excluded

Repeated because scope creep is real:

- No LLM summaries
- No AI chat / "ask your documents"
- No agents
- No note-taking
- No browser extension
- No cloud sync
- No collaboration
- No plugins
- No knowledge graph UI

These are not rejected because they're bad ideas. They're rejected because they don't answer "does this help someone remember?" better than what already exists.

---

## Dependencies

```
fastapi
uvicorn
watchdog
sentence-transformers
sqlite-vec
PyMuPDF          # fitz
PyQt5
pynput
pdf2image
pytesseract
# System: tesseract-ocr (apt / brew / UB Mannheim installer on Windows)
```

---

## ADR Log

At least 9 Architecture Decision Records maintained in `docs/development/decisions.md`. Key ones:

- ADR-001: sqlite-vec over ChromaDB/FAISS
- ADR-005: Paragraph chunking over fixed token windows
- ADR-007: Hybrid FTS5 + vector over pure vector
- ADR-009: `setQuitOnLastWindowClosed(False)` — window lifecycle fix
- (Others: migration system, separated chunk schema, OCR queue, hotkey selection)

---

## Development Platform

**Windows native** (not WSL for the daemon).

Reason: `watchdog` on WSL watching Windows folders via `/mnt/c/` is unreliable — `inotify` events don't propagate from NTFS through WSL. The global hotkey also needs to register with Windows directly. Core parsing/embedding/storage work fine in WSL, but the daemon must run natively on Windows.
