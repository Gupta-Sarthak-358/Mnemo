# Mnemo v1 Implementation Status

Version: 0.1-beta
Last Updated: 2026-06-25

---

## 1. What's Implemented

### Core Pipeline
- [x] PDF parsing (PyMuPDF)
- [x] TXT parsing
- [x] Paragraph-level chunking with neighbor context
- [x] Tiny paragraph merging (<60 words)
- [x] Embedding with sentence-transformers (all-MiniLM-L6-v2)
- [x] Token limit guard (400 tokens)
- [x] SQLite-vec vector storage
- [x] Batch embedding (32 chunks/batch)

### Storage
- [x] SQLite database with WAL mode
- [x] Schema migration system (version 7)
- [x] `files` table with per-file metadata
- [x] `pages` table with per-page tracking (quality, status, OCR attempts)
- [x] `chunks` table with text and metadata
- [x] `chunk_embeddings` virtual table (vec0)
- [x] `access_log` for behavioral ranking
- [x] `search_events` for query logging
- [x] `query_cache` for repeated queries

### File Watching
- [x] watchdog-based recursive folder watching
- [x] on_created / on_modified / on_deleted / on_moved handlers
- [x] Thread-local SQLite connections (per-thread safety)

### Search
- [x] FastAPI search endpoint (/search)
- [x] Ranking formula: 0.80 semantic + 0.10 recency + 0.10 access
- [x] Query cache (5 min TTL)
- [x] Latency measurement
- [x] Snippet results (first 300 chars)

### OCR
- [x] Quality-based page assessment (not word-count threshold)
- [x] Lazy OCR: index text first, OCR in background
- [x] OCR rate limiting (5 pages per 60s)
- [x] Garbage detection (non-alphanumeric ratio, Unicode ratio)
- [x] Per-page status tracking (extracted / needs_ocr / ocr_done)
- [x] Header/footer stripping (repeated line detection)

### Deduplication
- [x] File-level SHA256 deduplication
- [ ] Page-level deduplication — removed (see decisions.md)

### Hotkey Launcher (Phase 1 — v1.1)
- [x] Global hotkey via pynput (configurable in `config.json`)
- [x] Qt signal-based toggle (thread-safe cross-thread activation)
- [x] `setQuitOnLastWindowClosed(False)` — window stays alive as background companion
- [x] Normal resizable window (dropped FramelessWindowHint for v1)
- [x] Custom result cards (bold filename, page number, score, gray snippet)
- [x] Snippet cleanup (collapse whitespace, strip control chars)
- [x] Smooth per-pixel scrolling
- [x] Query persistence across show/hide cycles
- [x] Double-click + Enter to open results
- [x] PDF page jumping (SumatraPDF `-page N`, fallback `file://...#page=N`)
- [x] Window size 680×460 with minimum 500×300

### CLI
- [x] `mnemo debug inspect-pdf` — page-by-page OCR classification

### Benchmark
- [x] 20-query retrieval benchmark (4 categories)
  - Keyword: 5 queries
  - Conceptual: 5 queries
  - Vague memory: 5 queries
  - Ambiguous: 5 queries

---

## 2. Architecture

```
                          ┌─────────────────────┐
                          │  Main Thread         │
                          │  uvicorn (FastAPI)   │
                          │  8765                │
                          └──────┬──────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
             ┌──────┴──────┐          ┌───────┴───────┐
             │  Daemon     │          │  UI Thread     │
             │  Thread     │          │  PyQt6 + pynput│
             │  OCR worker │          │  QApplication  │
             │  Watcher    │          │  SearchWindow  │
             │  Indexer    │          │  (background)  │
             └──────┬──────┘          └───────┬───────┘
                    │                         │
                    └──────────┬──────────────┘
                               │
                    ┌──────────┴──────────┐
                    │  sqlite-vec (.db)    │
                    │  WAL mode            │
                    └─────────────────────┘

[Watched Folders]
       |
[File Watcher — watchdog] (daemon thread)
       |
[Parser Layer]
   PDF → PyMuPDF + quality check → chunking
   TXT → direct read → chunking
       |
[Pages Table]
   Per-page: quality, hash, status, method, OCR attempts
       |
[Chunker — paragraph + neighbor context + merge tiny]
       |
[Embedding — sentence-transformers (batch)]
       |
[sqlite-vec — chunks + embeddings separated]
       |
[FastAPI — /search, /status, /files, /log-open] (main thread)
       |
[Hotkey Launcher — configurable via config.json] (UI thread)
       |
[Results UI — custom cards, page jumping, smooth scroll]
```

### Key Design Decisions

**Separated chunks and embeddings** — Allows re-embedding without touching text/metadata when model changes.

**Pages table** — OCR is page-level, quality is page-level, future extraction metadata belongs at page granularity.

**Quality-based OCR** — Assesses text quality (alphabetic ratio, length, garbage chars) instead of naive word-count threshold. Verified on 4 representative PDFs.

**Thread-local connections** — Each thread (API, OCR worker, indexer, watcher) creates its own SQLite connection. WAL mode allows concurrent readers + single writer.

---

## 3. Validation

### Dataset
30 PDFs from `books_for_study/`:
- Programming books (DDIA, Head First Java, Kurose)
- Aptitude books (RS Aggarwal, Arun Sharma)
- Grammar (Wren & Martin)
- SAT prep, college booklets, competitive programming notes

### OCR Classification Inspection

| PDF | Pages | Extracted | OCR | Verdict |
|-----|-------|-----------|-----|---------|
| DDIA (modern tech) | 906 | 901 | 5 (cover) | Correct |
| Wren & Martin (scanned + OCR layer) | 939 | 937 | 2 | Correct |
| RS Aggarwal (fully scanned) | 197 | 0 | 197 | Correct |
| 4th SEM Booklet (typed, tables) | 55 | 55 | 0 | Correct |

### Retrieval Benchmarks

Benchmarks are versioned query JSON files in `benchmarks/` that are never overwritten. Results are saved to `benchmarks/results/YYYY-MM-DD.json` with full per-query detail.

| Benchmark | Queries | Top-3 | Notes |
|-----------|---------|-------|-------|
| v1 (2026-06-25) | 20 | 75% | Baseline (original expectations) |
| v2 (2026-06-25) | 20 | 90% | +index-page penalty, +benchmark corrections |
| v3 (2026-06-25) | 190 | 82% | Comprehensive eval (12 categories, excl. 20 negative) |

**v3 breakdown (82% on 170 non-negative queries):**

| Category | Count | Pass | Fail | Rate | Note |
|----------|-------|------|------|------|------|
| exact_keyword | 20 | 17 | 3 | 85% | Standard keyword retrieval |
| acronym | 15 | 9 | 6 | 60% | Worst category — tiny queries, low semantic signal |
| concept | 25 | 22 | 3 | 88% | Solid conceptual understanding |
| natural_question | 20 | 16 | 4 | 80% | Question-style search works well |
| half_remembered | 20 | 20 | 0 | **100%** | **Core Mnemo value — validated** |
| human_memory | 20 | 14 | 6 | 70% | Harder memory recall, still strong |
| visual_memory | 10 | 7 | 3 | 70% | Visual metadata missing from embeddings |
| cross_domain | 10 | 9 | 1 | 90% | Single-word cross-domain search |
| ambiguous | 10 | 8 | 2 | 80% | Broad terms work reasonably |
| comparative | 10 | 9 | 1 | 90% | "X vs Y" queries work well |
| adversarial | 10 | 8 | 2 | 80% | Handles minor typos, fails on severe ones |

**Failure classification (31 failures):**

| Type | Count | Handle |
|------|-------|--------|
| Genuine ranking failures | 8 | Fix when hybrid search or better model lands |
| Benchmark expectation issues | 6 | Acceptable lists adjusted |
| Corpus limitations | 7 | Concept not in any indexed book |
| Query ambiguity | 3 | Intrinsic to short/acronym queries |
| Future features | 7 | Defer to post-v1 |

**Negative queries:** 20/20 returned results. Not a bug — ANN vector search always finds the nearest neighbor. A relevance threshold is a post-v1 feature.

### Known Misses (v2, cold cache)
- "What happens when you type a URL in a browser" — Kurose at #4 (borderline pass)
- "How to design a rate limiter" — terminology mismatch; Alex Xu uses "token bucket"/"throttling"

---

## 4. Current System State

```
Status: Running (dogfooding phase) — v0.1-beta
Files: 30/30 indexed
Pages: 19,525 total
  Extracted: 17,744
  OCR pending: ~1,474
  OCR done: ~307
Duplicates: 0
Benchmark version: queries_v3.json (190 queries, 12 categories)
Benchmark results: benchmarks/results/2026-06-25_v3.json
Search failures log: docs/development/search_failures.md
```

### v1.1 Status (Phase 1 UX)

✅ Stable architecture, pipeline, OCR, indexing
✅ Honest benchmark with versioned queries and dated results
✅ Documented decisions (9 ADRs) and known failures
✅ 100% on half-remembered memory (core value proposition validated)
✅ Real evaluation corpus (190 queries, 12 categories)
✅ Hotkey launcher — configurable, resizable, stays alive as background companion
✅ PDF page jumping — SumatraPDF `-page N`, fallback `file://...#page=N`

**From here:** stop expanding benchmarks, stop adding heuristics. Use Mnemo daily. Collect real searches. Only revisit ranking after 30-50 real failures accumulate.

---

## 5. Known Limitations

- **Index/glossary pages** — Heuristic penalty (0.8x) applied for pages where >50% lines match "word, number" pattern. Verified to fix MVCC ranking. May have false positives on legitimate content with dense references.
- **Code-aware chunking** — Deferred. Embedding models may handle code well enough.
- **DOCX support** — Post-v1.
- **Memory Trails** — Post-v1.
- **Adaptive ranking weights** — Post-v1.
- **OCR throughput** — 5 pages/60s. Full OCR of ~1,500 pages will take ~5 hours.
- **Qt running in daemon thread** — Works stably for v1 but should move to main thread before tray integration or complex native event handling.
- **PDF page jumping** — `file://...#page=N` verified working on Chrome/Brave. Multi-viewer detection: SumatraPDF → Chrome → Brave → Edge → default. Edge has known `#page=N` caching issues — mitigated with `?t=<timestamp>` cache-buster. Viewer abstraction deferred to Phase 8.

---

## 6. Lessons Learned

1. **Word-count OCR detection was too naive.** Quality-based detection (alphabetic ratio, garbage detection, length) proved significantly better — reduced false OCR classifications by ~42%.

2. **Page-level deduplication created more complexity than value.** Empty/OCR pages all produced identical hashes, causing false duplicate counts. File-level SHA256 covers the real problem (same PDF in multiple folders).

3. **Inspection tools were more valuable than additional heuristics.** Running `inspect-pdf` on 4 representative PDFs revealed more about OCR quality than any metric ever could.

4. **Representative PDFs reveal problems synthetic tests never would.** Real books (scanned textbooks, formatted booklet, modern O'Reilly) exposed edge cases that toy PDFs wouldn't.

5. **Benchmark before optimizing.** The 20-query benchmark showed 75% top-3 accuracy. Now every change has a measurable target instead of "feels better."

6. **Score spreading can hide retrieval failures.** When all similarity scores are uniformly low, artificially spreading them makes the "least bad" result appear meaningfully better. It doesn't fix the core problem — poor embeddings for that query. Removed after review.

7. **Benchmark improvements must be separated from ranking improvements.** Changing acceptable-file lists (+2 queries) vs. index-page penalty (+1-2 queries) produced ~equal gains. Without separation, you'd think ranking alone produced +15%.

8. **Cache state must be consistent across benchmark runs.** Warm cache + cold cache comparisons measure two different systems. Every benchmark run should document whether cache was cleared.

9. **`QApplication.setQuitOnLastWindowClosed(False)` is mandatory for launcher-style apps.** By default, hiding the only visible window triggers `app.quit()`, destroying all Qt widgets. The next hotkey press then hits a deleted C++ object. This is a known Qt pitfall — every background/hotkey app must set this flag.

---

## 7. Next Steps (Dogfooding Phase)

**Freeze the indexing pipeline.** No more changes to OCR, chunking, embeddings, or ranking heuristics until real usage data accumulates.

1. Use Mnemo as the daily search tool for all study/reading lookups.
2. Collect every failed search into `docs/development/search_failures.md`.
3. Log queries that worked surprisingly well (wild boar patterns) — these define Mnemo's strengths.
4. Only after 30-50 real failures accumulate should ranking be revisited.
5. Expand benchmark queries from these real failures, not synthetic guesses.
6. Add `mnemo debug search` command for ad-hoc query inspection (when needed).
