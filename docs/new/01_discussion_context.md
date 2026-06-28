# Mnemo — Discussion Context & Engineering History

> This document explains how Mnemo came to be and why things are the way they are.
> Read this when you forget the reasoning behind a decision, or need to understand how the project evolved.

---

## Origin

Started from a single observation: humans remember meaning, not filenames.

Most "semantic search" tools begin with technology — "vectors are cool, what can we build?" Mnemo started from the failure mode: people spend measurable time every week searching for things they've already found once. The file exists. The memory of reading it exists. The bridge between how humans store meaning and how computers store files does not exist.

That gap is the product.

---

## The Six Phases of Mnemo's Development

### Phase 1 — Proof of Concept
**Question:** Can we build a local semantic search engine at all?

Everything was technical. PDF → Extract → Chunk → Embed → Search. Success criteria: it indexes, it returns something, it doesn't crash. This is where most student projects start and stop — they have technology, not a product.

### Phase 2 — Engineering
This is where Mnemo became software, not a demo.

Built in this phase:
- OCR pipeline with lazy fallback
- Background daemon with thread-local SQLite connections
- File watcher (watchdog)
- Schema migration system
- Pages abstraction
- sqlite-vec integration
- Benchmarking infrastructure
- Debugging CLI (`mnemo debug inspect-pdf`)

The inspection-first philosophy emerged here. `mnemo debug inspect-pdf` is worth more than ten parser heuristics because inspection tools compound — heuristics accumulate debt.

### Phase 3 — Validation
The mindset shift: from "can I make OCR smarter?" to "did OCR actually fail?"

Instead of assuming improvements, everything was measured. The benchmark system (queries_v1.json → v2 → v3) was established, separating benchmark definition from execution from history. Changes that didn't produce measurable benchmark gains were removed — including score normalization experiments that "felt right" but didn't move the numbers.

Removing code is harder than adding it. This phase did it.

### Phase 4 — Product Thinking
The biggest shift wasn't technical. It was the framing:

> "Forget filenames. Remember ideas."

Every feature now had a north star. Not "is this technically clever?" but "does this help users remember?" This is when the product thesis crystallized and architectural decisions started resembling product decisions.

### Phase 5 — Dogfooding
Intentional decision: no more ranking tweaks without evidence.

```
Use it daily → Collect failures → Fix real problems
```

Real queries exposed what synthetic benchmarks couldn't. The benchmark corpus grew to 190 queries across 12 categories including "half-remembered memory" queries — the hardest class and the most important one. 100% accuracy on that subset. That's the metric that matters.

### Phase 6 — Experience Design (Current)
The bottleneck shifted from engineering to UX.

What occupied recent work: typography, scrolling, launcher behavior, hotkeys, result cards, window lifecycle, page jumping. Users cannot perceive the difference between cosine similarity 0.84 and 0.87. They absolutely notice whether `Ctrl+M` responds instantly, whether arrow keys work, whether the window feels like a launcher or a dialog box.

The product now resembles Everything, Alfred, and PowerToys Run more than it resembles a search engine. That's the correct comparison class.

---

## Key Architectural Decisions and Why They Were Made

### sqlite-vec over ChromaDB / FAISS
ChromaDB adds dependency overhead. FAISS doesn't persist natively — serialize/deserialize on every restart, fragile across OS updates. sqlite-vec puts vector search inside SQLite. One `.db` file. Entire product state is one file you back up with `cp`.

### Hybrid search (semantic + FTS5)
Pure vector search failed on numeric queries ("Error 404" → chapter 404) and exact keyword queries. Adding FTS5 at 0.30 weight alongside semantic at 0.70 fixed a class of failures without hurting the general case. The weights were set empirically, not theoretically.

### Paragraph chunking with neighbor context
Fixed 500-token windows cut across paragraph boundaries. Neighbor context gives the embedding the semantic neighborhood of the target passage, not just its isolated content. Quality difference is ~30% vs ~3% for model choice.

### Separated chunk schema
`chunks` table for text/metadata. `chunk_embeddings` virtual table for vectors. Decoupled so re-embedding on model upgrade doesn't require touching text data.

### Migration system on day one
`schema_version` table added before any other table. Schema evolved to include access_log, search_events, watched_folders, FTS5 index, heading detection. Without migrations, each schema change would mean deleting the database — catastrophic for a memory tool.

### Hotkey: Ctrl+M (not Ctrl+Space)
Ctrl+Space conflicts with Windows system shortcuts. Ctrl+Alt combinations produce special characters on international keyboards via AltGr (Ctrl+Alt+M → ṁ on many layouts). Ctrl+M was clean, available, and registered correctly after switching to US keyboard layout during development. Settings dialog allows user reconfiguration.

---

## All Bugs Encountered and Their Fixes

### Infrastructure
1. **Two daemon processes fighting for port 8765** — root cause of most "daemon died" issues. Fix: single daemon with process lock file.
2. **`setQuitOnLastWindowClosed(True)`** — hiding the window called `app.quit()`, destroying all Qt widgets. Second hotkey: `RuntimeError: wrapped C/C++ object of type SearchWindow has been deleted`. Fix: `setQuitOnLastWindowClosed(False)` (ADR-009).
3. **`QTimer.singleShot(0, toggle)` unreliable cross-thread** — replaced with `pyqtSignal()` (`toggleRequested`).
4. **Window activation on Windows** — `_force_activate()` workaround using temporary `WindowStaysOnTopHint`.
5. **AltGr conflict** — `Ctrl+Alt` combos produce special characters on international keyboards. Hotkey changed from `Ctrl+Alt+M` to `Ctrl+M`.
6. **sqlite-vec requires `k = ?`** — not just `LIMIT`, or the query silently returns all rows.
7. **Thread-local SQLite connections** — each thread needs its own connection (WAL mode).
8. **`PYTHONIOENCODING=utf-8` required** — for Unicode filenames in PowerShell.

### Embedding / Retrieval
9. **Token truncation** — sentence-transformers silently truncates at 512 tokens. Fix: `safe_embed()` with token count check before embedding.
10. **Index page penalty** — pages with >50% "term → number" lines scored 0.8× to reduce false positives from index/bibliography pages.
11. **"Error 404" → retrieves chapter 404, page 404** — pure semantic search fails on numeric queries. Fix: hybrid FTS5 + vector search.
12. **"Sorting Retrieved Data" → wrong paragraph** — heading missing from semantic context. Fix: heading boost (+0.15).

### UX
13. **Three-way hotkey conflict** — pynput + Qt key events + settings dialog all interpret keys differently. Fix: clean parser with no VK/digit mapping.
14. **Recent searches recorded every keystroke** — `["R", "Re", "Red", "Redi", "Redis"]`. Fix: save only on document open.
15. **Recent searches had duplicates and no cap** — Fix: deduplicate, cap at 20.
16. **Short queries triggered full search** — Fix: 3-character minimum before search fires.
17. **Results displayed raw similarity scores** — Fix: score labels (Excellent / Strong / Good / Fair).
18. **Page jumping failed in some PDFs** — Edge URI had unencoded spaces. Fix: `urllib.parse.quote`.
19. **Context expansion not visible** — length comparison was wrong. Fix: sentence-count threshold.
20. **Grouped results were cluttered** — separate "Open" buttons per result. Fix: clickable `QPushButton` rows.

---

## Decisions That Were Made and Then Reversed

**Score normalization / spreading** — Implemented, benchmarked, found no measurable improvement, removed. The best optimization was negative lines of code.

**Page deduplication** — Removed. Added complexity without clear benefit.

**Bibliography heuristics** — Removed. Too specific, accumulated debt.

**Code chunking** — Removed. Different audience, different product.

Every removed feature made the product stronger. Removal is harder than addition and rarer. The project did it repeatedly.

---

## Competitive Context

Tools that exist but don't fully solve it: Zotero (manual import), Mendeley (same), SciSpace (cloud, their papers only), NotebookLM (cloud, manual upload), Spotlight/Windows Search (filename + basic content, no semantic understanding), Windows Recall (OS-level but resets on reinstall, can't index sensitive unpublished data).

The white space: local, passive, behaviorally adaptive, portable. Mnemo is the only tool that is simultaneously all four.

The OS threat is real (Apple Intelligence, Windows Recall) and also validation that the market exists. Strategic response: serve the users OS vendors structurally cannot — Linux, air-gapped, sensitive data, cross-platform, portable behavioral memory.

---

## Where the Project Stands Now

The backend is stable. OCR is complete. The benchmark is at 82% Top-3 accuracy (190 queries). The UI looks like a real application. The hotkey works. The window lifecycle is correct.

The bottleneck has permanently shifted from engineering to information retrieval and experience design. Architectural changes now yield 1–2% gains. UX changes yield 50%.

The product has crossed a line. It no longer needs more architecture. It needs daily use, real failure collection, and ruthless focus on its single promise.
