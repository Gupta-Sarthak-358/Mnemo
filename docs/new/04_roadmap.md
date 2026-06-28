# Mnemo — Roadmap

> What comes next, in what order, and why.
> Everything here is prioritized by impact on the core promise: help someone find what they remember.

---

## Where We Are

Mnemo is a working alpha. The infrastructure is stable. OCR is done. Search works at 82% Top-3 accuracy. The UI is functional.

The question is no longer "can we build this?" It's "how do we make it indispensable?"

**The current bottleneck is not engineering. It is information retrieval and experience polish.**

Architectural changes yield 1–2% improvement. UX changes yield 50%. Keep this ratio in mind when prioritizing.

---

## Feature Freeze Policy

**No new features until existing ones are proven.**

The only permitted code changes are:

1. Retrieval quality improvements **backed by benchmark gains**
2. Bug fixes
3. Packaging and reliability work
4. UX polish that reduces friction

Everything else goes into `v2_ideas.md` — written down, admired briefly, ignored until v1 ships.

---

## Phase 5 — Retrieval Quality (Current Priority)

**Goal:** Push Top-3 accuracy from 82% to 85%+ on real queries, not synthetic ones.

### 5.1 Failure Collection
Build and maintain `docs/development/search_failures.md`.

Every failed search gets:
```
Date:
Query:
Expected document:
Returned document:
Why it failed:
Category: [vocabulary mismatch / numeric / acronym / ambiguous / other]
Fix attempted:
Resolved: [yes/no]
```

Target: 50–100 documented real failures before changing anything in the ranking pipeline. The categories that emerge will tell you exactly where to invest.

### 5.2 Acronym Handling
Current failure mode: "MVCC" retrieves correctly, "multi-version concurrency control" may not retrieve the same document because the chunk uses the abbreviation without spelling it out.

Potential fix: at index time, expand known acronyms. At query time, expand query acronyms. Small lookup table, high-ROI.

Only implement if failure log shows this is a real category.

### 5.3 Query Expansion / Intent Understanding
Current: embedding of literal query string.

Future: understand what the user is trying to recover.

Example:
- Query: "where did I read that cache gets slower because of coherence"
- Expanded: cache, cache coherence, false sharing, MESI, coherence protocol

Better retrieval without a bigger model — just better retrieval. Implement after failure log shows vocabulary mismatch is a top failure category.

### 5.4 Cross-Encoder Reranker (Research Phase)
A small local cross-encoder reranker is one of the highest-leverage single improvements possible once the retrieval pipeline is stable.

Current pipeline: query embedding → vector + FTS retrieval → ranking formula

With reranker: query + chunk pair → cross-encoder score → final ranking

Cross-encoders are slower (run on top N candidates, not whole index) but dramatically more accurate for the final ranking step.

**Do not implement until:**
- 30–50 real failure cases are documented
- Failure analysis shows ranking quality (not retrieval recall) is the limiting factor
- A benchmark exists to prove the improvement before shipping it

Research options: `ms-marco-MiniLM-L-6-v2` (small, local, designed for this purpose).

---

## Phase 6 — Dogfooding

**Goal:** Turn daily use into product intelligence.

### 6.1 Daily Use Protocol
Every working day:
1. Press `Ctrl+M`
2. Search for something real
3. Did it find it?
4. If not → log in `search_failures.md` immediately

### 6.2 Real Query Corpus
After 4–6 weeks of dogfooding, you'll have a genuine query corpus. These are worth more than 10,000 synthetic benchmark queries because they reflect how you actually search, not how you imagine you search.

Add them to a `queries_v4.json` (dogfood-derived) benchmark set. This set becomes the true quality bar.

### 6.3 Behavioral Signal Activation
Access logs are being collected. After 2–4 weeks of real use, the behavioral layer starts producing signal. Verify:
- Are frequently opened files ranking higher for their corresponding queries?
- Is the access log actually influencing results?
- What's the lift in accuracy when behavioral signal is included vs excluded?

Measure this. Don't assume.

---

## Phase 7 — Packaging and Reliability

**Goal:** Anyone can install Mnemo in under 5 minutes. It runs without babysitting.

### 7.1 Installer
Windows: NSIS or Inno Setup installer. Ships Python runtime, all dependencies, Tesseract, poppler.
Linux: `.deb` or AppImage.

Target: download → double-click → running. No terminal. No pip. No configuration files.

### 7.2 Auto-Start
Register with OS startup:
- Windows: registry `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Linux: `.config/autostart/` or systemd user service

### 7.3 System Tray
Minimal tray icon: shows indexing progress, allows folder management, pause/resume, quit.
Not a settings dashboard. Four options maximum.

### 7.4 Crash Restart
Watchdog process monitors daemon. If daemon exits unexpectedly, restart it. Log the crash. Surface to tray icon.

### 7.5 Crash Recovery (Already Partially Implemented)
`index_status = 'pending'` for any file in `'indexing'` state at startup. Already in schema. Verify this works correctly across crash scenarios.

### 7.6 PDF Viewer Abstraction
Current: multi-viewer detection (SumatraPDF → Chrome → Brave → Edge) with `#page=N` URI. Verified working on Chrome/Brave. Edge mitigated with `?t=<timestamp>` cache-buster. Viewer abstraction deferred to Phase 8.

Target architecture:
```python
class PDFViewer:
    def open(self, path): ...
    def open_at_page(self, path, page): ...
    def supports_page_jump(self): ...

class SumatraPDFViewer(PDFViewer): ...
class BrowserViewer(PDFViewer): ...
class AcrobatViewer(PDFViewer): ...
```

Detect available viewers at startup. Use best available. Let user configure preferred viewer in settings.

SumatraPDF is the right default on Windows — free, fast, reliable page jumping via CLI (`SumatraPDF.exe -page N file.pdf`).

---

## Phase 8 — Experience Polish

**Goal:** The product feels like muscle memory, not software.

Only start this after months of dogfooding. You need to know what actually bothers people, not what you imagine bothers them.

### 8.1 Result Card Typography
- Remove underscores from filenames
- Strip ".pdf" extension from display
- Author detection and display
- Chapter/section heading in card
- Better spacing between cards and within cards

### 8.2 Scroll Behavior
Qt default scroll sensitivity is too aggressive. Smooth scrolling with configurable speed.

### 8.3 Keyboard Navigation
- Arrow keys to move between results
- Enter to open selected result
- Escape to dismiss or clear
- Tab to move between result cards

Full keyboard flow. No mouse required from hotkey to file open.

### 8.4 Search History
Browse previous searches. Navigate with arrow keys. Click to re-run.

### 8.5 Word Highlighting Polish
Current highlighting is functional. Improve: highlight matched terms in snippet, dim non-matching text slightly, bold exact phrase matches.

### 8.6 Window Behavior Refinement
- Clear search text on each open (launcher feel) or persist? — decide after dogfooding
- Remember last window position? — already implemented, verify it feels right
- Single monitor vs multi-monitor positioning

---

## Post-v1 Features (Do Not Build Until v1 Stable for Months)

### Memory Trails
Store the research journey, not just the destination.

```
Query → opened file → time spent → next file opened
```

Reconstruct: "How did I discover this idea?" Researchers remember paths. "I found Paper A, which led me to Paper B, which referenced Paper C." Nobody else does this.

### Context Cards
Result shows not just a snippet but:
- Why this matched (concepts)
- What the document discusses in relation to the query
- Confidence level
- Related concepts to explore

Users recognize the result before opening it.

### Continue Reading
When you open a file at page 420, Mnemo remembers. Next search in the same area:
> "Continue from where you left off — Database System Concepts, page 436: Replication"

That's memory. Not search.

### Cross-Document Evidence
Search "CAP theorem" and see:
- Database System Concepts → discusses consistency
- Designing Data-Intensive Applications → discusses availability
- Distributed Systems → discusses partition tolerance

Concepts mapped across documents. Researchers would use this constantly.

### DOCX Support
High demand. Low engineering complexity. Just needs `python-docx`. Add after v1 is stable.

### Adaptive Ranking Weights
Currently 0.70 semantic / 0.30 FTS. Over time, let behavioral data shift these per-user. A user who searches very precisely benefits from higher FTS weight. A user who searches conceptually benefits from higher semantic weight. Enough data to distinguish this after months of use.

---

## What Will Never Be Built

No matter how tempting:

| Feature | Why Not |
|---------|---------|
| LLM chat / "Ask your PDFs" | People do this once a week. Finding a document happens five times a day. Daily products win. |
| Cloud sync | Destroys the core value proposition for the target user. |
| Collaboration / sharing | Different product entirely. |
| Browser extension | Different product entirely. |
| Mobile app | Different product entirely. |
| AI agents | No. |
| Knowledge graph visualization | Pretty. Not useful daily. |
| Plugin system | Complexity for unclear gain. |

These may be valuable. They are not Mnemo.

---

## The Evaluation Discipline

Every retrieval change must produce a measurable benchmark improvement before shipping.

The benchmark is not a formality. It is the only honest answer to "did this get better?"

```
Change hypothesis
    ↓
Implement
    ↓
Run benchmark
    ↓
Numbers improved? → Ship
Numbers same? → Revert
Numbers worse? → Revert and understand why
```

"I think this feels better" is astrology. Numbers win arguments.

---

## The Long-Term Vision

The roadmap above describes a tool. The thesis describes something more.

The stages:

| Stage | Description |
|-------|-------------|
| 1 — Search Engine | Better Ctrl+F (current) |
| 2 — Context Recovery | Understand why something matched before opening it |
| 3 — Personal Memory | Behavioral layer makes it yours specifically |
| 4 — Knowledge Companion | Reconstruct research journeys. Connect ideas across documents. Help you think. |

Stage 4 is years away. Stage 1 is working. The path between them is clear: ship, dogfood, measure, improve, repeat.

The product Mnemo is competing with is not a search engine. It is forgetting.
