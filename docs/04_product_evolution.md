# Mnemo — Product Evolution

> **Purpose:** Describes the four stages of Mnemo's evolution, from search engine to personal memory.
> **Status:** Living document (updated as stages are reached or redefined)
> **Audience:** Product, engineering, and anyone evaluating Mnemo's trajectory

These stages describe *user value*, not technology. Each stage represents a qualitative shift in how the user experiences Mnemo — not a feature list. A stage is complete when the experience it describes feels natural, not when every item on a checklist is ticked.

---

## Stage 1 — Search Engine (Current v1)

**Tagline:** *Find files by idea, not filename.*

### What the user experiences

The user presses a hotkey, types a fragment of an idea, and gets ranked file results with snippets. They open the file and start reading. It is faster than OS search for conceptual queries and slower for exact filename matches. The user accepts this trade-off because the queries they fail on — "the paper about cache coherence" — are exactly the ones they couldn't solve before.

### What makes it work

- PDF + TXT parsing with OCR fallback
- Paragraph-level chunking with neighbor context
- Semantic vector search (sentence-transformers + sqlite-vec)
- Simple ranking: semantic similarity + recency + access frequency
- Global hotkey launcher with search UI
- File watcher for automatic indexing
- Query cache for repeated searches

### User tells us Stage 1 is done when

> "I find things I couldn't find before."

### Stage 1 is NOT done when

A user searching "sorting retrieved data" gets a paragraph about "sorting of data plays an important role" ranked above the page titled "Lesson 5: Sorting Retrieved Data." Stage 2 begins when we can fix this.

### What we're NOT doing in Stage 1

- Concept extraction
- Intent expansion
- Cross-document synthesis
- Research timeline
- "Continue Reading" as a product feature (the UI stub exists, but it's not yet the experience it needs to be)

---

## Stage 2 — Context Recovery

**Tagline:** *Find what you remember, not what you can describe.*

### What the user experiences

The user types "Error 404" and immediately sees that Mnemo understands this is an HTTP concept — not searching for pages numbered 404. Results show *why* each document matched, what *concepts* are discussed in the relevant section, and which *chapter* contains the answer. The user opens the file already knowing they found the right place.

When the user types "sorting retrieved data," the result titled "Lesson 5: Sorting Retrieved Data" ranks first — not because the model happens to understand headings, but because the retrieval pipeline treats headings, titles, and filenames as first-class signals alongside semantic similarity.

### What makes it work

- **Hybrid retrieval** — semantic search + BM25/FTS keyword search, fused with learned weights (0.70 semantic, 0.30 keyword as the v1 starting point)
- **Heading/title boost** — headings, chapter titles, and section names detected during parsing and scored as separate ranking signals (+0.15 heading boost, +0.10 filename boost)
- **Phrase detection** — technical terms ("HTTP 404," "SQL injection," "LRU cache") recognized as phrases, not disjoint words. The retrieval pipeline converts "Error 404" into an intent-aware query that prefers documents discussing HTTP errors
- **Concept extraction** — the important nouns and technical terms in each chunk are extracted and displayed alongside results as "Why this matched" indicators. The user scans meaning instead of raw text
- **Snippet extraction** — the displayed snippet centers on the most relevant sentence, not the chunk start. Users judge result quality by the snippet more than any other signal
- **Search behavior** — searches with 1-2 characters don't fire (too early, too noisy). Recent searches save only on document open, not on keystroke. History is deduplicated and capped at 20

### User tells us Stage 2 is done when

> "I know why it showed me that before I click it."

### Stage 2 is NOT done when

The user still occasionally opens a result to discover it was a false positive driven by a coincidental keyword match — and cannot understand why it appeared. Every result must be explainable.

---

## Stage 3 — Personal Memory

**Tagline:** *Better than your own memory.*

### What the user experiences

Mnemo knows what the user reads, what they skip, what they return to. It surfaces results not just by semantic relevance but by personal relevance — the same query returns different results for different users because their behavioral histories are different.

"Continue Reading" is no longer a UI stub. When the user opens Mnemo after a break, it shows not just recent searches but a contextual suggestion: "You were reading about Redis replication. The next relevant section is in Chapter 5, page 120."

The user searches "cache coherence" and the first result is the paper they opened three times last month — even if a different paper is semantically closer to the query. The behavioral signal is strong enough to override pure semantic ranking for queries where the user has a clear history.

### What makes it work

- **Behavioral ranking maturity** — after weeks or months of usage, the access log contains enough signal to meaningly adjust ranking weights. The 0.80/0.10/0.10 split shifts toward personal relevance over time
- **"Continue Reading" as a product** — tracking not just the last opened file but the reading session: where the user was, what they were searching for, what they opened next. A lightweight session model that connects queries to dwell time to subsequent queries
- **Research timeline** — reconstructs how knowledge was discovered over time. "Monday: searched 'transformer scaling' → opened 'Attention Is All You Need' → 30 minutes later: 'FlashAttention' → then: 'RoPE paper'" — surfaced when the user wonders "how did I find this?"
- **Context Cards** — each document result shows not just a snippet but the concepts it covers, the chapters it contains, and the confidence level of the match. The card is designed for recognition, not reading

### User tells us Stage 3 is done when

> "Mnemo finds what I need even when my query is wrong."

### Why this is hard

Stage 3 requires **time**. The behavioral layer needs weeks of real usage before it produces signal. Stage 3 cannot be built in a week — it can only be *enabled* by architecture and *realized* by time. Rushing to build features before the data exists produces artificial-feeling personalization that undermines trust.

---

## Stage 4 — Knowledge Companion

**Tagline:** *A second brain that works.*

### What the user experiences

Mnemo connects knowledge across documents automatically. The user searches a concept and gets answers from multiple sources, organized by perspective — not a flat list of results.

"CAP theorem" returns:

```
Mentioned in:

Database System Concepts
✓ consistency

Designing Data Intensive Applications
✓ availability

Distributed Systems
✓ partition tolerance
```

The user immediately knows which document discusses what aspect. No manual tagging. No folder organization. The connections emerge from the content itself.

When the user has a vague memory — "I think I read something about segment tree updates having logarithmic complexity" — Mnemo returns the answer directly:

```
Point update: O(log n)
Range update: O(log n)

Source: Competitive Programming Handbook, Page 84

[Supporting paragraph ▼]
```

The user almost never needs to open the file. They confirm the answer, recognize the source, and continue working. The open becomes a confirmation, not an exploration.

### What makes it work

- **Cross-document evidence** — a concept index that maps technical terms to their occurrences across files, showing which documents discuss which aspects of a concept
- **Intent expansion** — the search query is internally expanded into related terms before retrieval. "cache coherence" expands to "cache coherence, false sharing, MESI, coherence protocol, snooping, directory-based." The user doesn't need to know the exact vocabulary
- **Instant answer previews** — for well-defined queries (time complexity, definition, comparison), Mnemo shows the answer inline with a source citation. The answer is always attributed. The user can always open to verify
- **Merge duplicate results** — the same document appearing at pages 303, 846, and 1280 is shown as one entry with multiple page references, not three separate results

### How this differs from "AI"

Stage 4 does not generate answers. It *curates* them from content the user has read. Mnemo never says anything the user hasn't already encountered. It remembers. It connects. It organizes. It does not invent.

This distinction is critical. Generated answers are replaceable — the next chatbot will generate better ones. Curated answers are personal — they reflect what *this specific user* has learned. That cannot be replaced by a better model.

### User tells us Stage 4 is done when

> "Mnemo remembers things I forgot I knew."

---

## Stage Mapping

| Stage | User says | Key technical investment | Timeframe |
|-------|-----------|------------------------|-----------|
| 1 — Search Engine | "I find things I couldn't find before." | Parser, chunker, embeddings, vector DB, UI | Shipped (v1) |
| 2 — Context Recovery | "I know why it showed me that." | Hybrid retrieval, heading boost, concept extraction, phrase detection | Next |
| 3 — Personal Memory | "It finds what I need even when my query is wrong." | Behavioral maturity, session tracking, research timeline | 2-4 months of dogfooding |
| 4 — Knowledge Companion | "It remembers things I forgot I knew." | Cross-document index, intent expansion, answer previews | 4-8 months |

---

## What This Document Is For

The stage model serves three purposes:

1. **Prevents premature complexity.** We don't build concept extraction in Stage 1. We don't build cross-document indexes in Stage 2. Each stage earns the right to the next one.

2. **Provides a north star.** When deciding between two approaches, the one that moves toward Stage 4 wins. When a feature doesn't clearly serve any stage, it doesn't get built.

3. **Communicates trajectory.** A new contributor or investor reading this document should understand not just what Mnemo does today but what it will do in 12 months — and, more importantly, what it will *never* do.
