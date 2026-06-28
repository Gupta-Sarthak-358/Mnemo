# Architecture Decision Log

## 2026-06-25

---

### ADR-001: Pages table

**Decision:** Introduce a dedicated `pages` table.

**Reason:** OCR is page-level. Quality scoring is page-level. Future extraction metadata (contains_images, contains_tables, language) belongs at page granularity, not on files or chunks.

**Alternatives considered:** Keeping metadata on `chunks`.

**Rejected because:** Chunks are downstream artifacts (paragraphs with neighbor context). A single page can produce multiple chunks. Page-level properties don't belong on individual chunks.

---

### ADR-002: Quality-based OCR instead of word-count threshold

**Decision:** Replace `if len(page.get_text().strip()) < 50: OCR()` with `if assess_page_quality(text) < 0.5: OCR()`.

**Reason:** The word-count heuristic misclassified children's books, slides, and scientific posters (few words, perfectly readable). Quality scoring considers: text length, alphabetic ratio, printable character ratio, avg word length, garbage character ratio, whitespace distribution.

**Validation:** Verified on 4 diverse PDFs (DDIA, Wren & Martin, RS Aggarwal, college booklet). Classification was correct in all cases. Reduced unnecessary OCR by ~42%.

---

### ADR-003: SQLite with thread-local connections

**Decision:** Each background thread creates its own SQLite connection. WAL mode enabled. No shared connection pool.

**Reason:** SQLite connections are not thread-safe. Using a single shared connection with `check_same_thread=False` risks corruption. Thread-local connections with WAL mode allow concurrent reads + single writer.

**Alternatives considered:** Dedicated database thread with a queue.

**Rejected because:** For v1 scale (< 1000 files), thread-local connections are simpler and sufficiently safe. WAL mode handles concurrent access.

---

### ADR-004: Remove page-level deduplication

**Decision:** Remove page-level duplicate detection. Keep only file-level SHA256 deduplication.

**Reason:** Page-level dedup introduced false positives (empty/OCR pages all hash to same value). The real problem is the same PDF existing in multiple folders, which file-level SHA256 handles. Occasional duplicate pages (copyright, blank) cost negligible storage and indexing time.

**What was tried:** Hashing page text after header/footer stripping, with synthetic hashes for short text. Both approaches created more edge cases than they solved.

---

### ADR-005: Separated chunks and chunk_embeddings

**Decision:** `chunks` (text + metadata) and `chunk_embeddings` (vectors only) are separate tables.

**Reason:** When the embedding model changes (and it will), you want to re-embed without touching text and metadata. Decoupled from day one.

**Implementation:** `chunk_embeddings` is a sqlite-vec virtual table with `chunk_id` FK to `chunks(id)`.

---

### ADR-006: Lazy (background) OCR

**Decision:** Index extractable text immediately. Queue low-quality pages for background OCR processing.

**Reason:** Users get searchable results within minutes (most recently modified files first). OCR of hundreds of pages happens invisibly. The user never waits for OCR to complete before first search.

**Rate limiting:** Max 5 OCR pages per 60 seconds to avoid CPU starvation.

---

### ADR-007: sqlite-vec over FAISS or ChromaDB

**Decision:** Use `sqlite-vec` for vector search.

**Reason:** Vectors live inside SQLite. No serialization/deserialization cycle on restart. Entire product state is one `.db` file. Backup is `cp`.

**Rejected:**
- **FAISS**: Doesn't persist natively. Fragile across OS updates.
- **ChromaDB**: Added dependency overhead becomes maintenance obligation.

---

### ADR-008: Benchmark before optimizing

**Decision:** Build a 20-query retrieval benchmark before tuning ranking, chunking, or model selection.

**Reason:** Every architectural change now produces a measurable number (Top-1, Top-3, latency) instead of "feels better."

**Categories:** keyword (5), conceptual (5), vague memory (5), ambiguous (5) — tests different retrieval modes.

**Current baseline:** Top-1: 65%, Top-3: 75%, Avg latency: 45ms.

---

### ADR-009: `setQuitOnLastWindowClosed(False)` for launcher lifetime

**Decision:** Call `app.setQuitOnLastWindowClosed(False)` immediately after `QApplication(...)`.

**Reason:** By default, `QApplication.quit()` fires when the last visible window is hidden. For a launcher that should stay alive as a background companion (show/hide via hotkey), this causes `app.exec()` to return and all Qt widgets to be destroyed. The next hotkey press then crashes with `RuntimeError: wrapped C/C++ object of type SearchWindow has been deleted`.

**Impact on UX:**
- Window stays alive across show/hide cycles
- Search query persists across invocations
- No crash on second hotkey press

**Affects:** `src/mnemo/ui.py` — `run_ui()` function.

**Tradeoff:** The process now explicitly keeps running; exit must be handled via Ctrl+C or task manager. Acceptable for a daemon-style application.

---

## 2026-06-27

---

### ADR-010: Page number indexing (0-indexed DB, 1-indexed viewer)

**Decision:** Store page numbers as 0-indexed in the database (matching `enumerate(doc)` from PyMuPDF). Convert to 1-indexed only at the viewer boundary in `open_pdf()`.

**Reason:** The PDF page numbering ecosystem is fragmented:
- PyMuPDF enumerates pages starting at 0 (`enumerate(doc)` → 0, 1, 2...)
- SumatraPDF expects 1-indexed pages (`-page N` where page 1 = first page)
- Browser `#page=N` fragments expect 1-indexed pages
- Users expect to see "p.1" for the first page

**Viewer detection priority:** SumatraPDF → Chrome → Brave → Edge → system default. Edge's PDF viewer inconsistently handles `#page=N` on local `file:///` URIs due to scroll position caching. A `?t=<microsecond_timestamp>` cache-buster is prepended to the URI for Edge compatibility.

**Tradeoff:** Old saved "Continue Reading" positions (stored before ADR-010) are 0-indexed and will be off by 1 page until the user opens a new result. Acceptable for a transition period.

**Affected functions:**
- `open_pdf()` — adds `+1` before passing to viewer
- `_render_grouped()`, `_render_single()` — displays `page_num + 1`
- `save_last_open()`, `api_log_open()` — stores/logs raw (0-indexed) page_num
