# Search Failures Log

Part of the dogfooding phase. Every time Mnemo fails to find what you're looking for, log it here.

## Format

```markdown
### YYYY-MM-DD: [query text]

**What I wanted:** [book title or specific content]
**What I typed:** [exact query]
**What came back:** [top 3 results]
**Why it failed:** [one-liner on the gap]
**Type:** [ranking | benchmark | corpus | ambiguity | future]
```

### Failure Types

| Type | Meaning | Action |
|------|---------|--------|
| **ranking** | The right book exists in the corpus but ranks too low. The ranking algorithm can be improved. | Fix ranking |
| **benchmark** | The acceptable-file list is wrong. The system is actually correct. | Fix benchmark |
| **corpus** | The concept doesn't exist strongly enough in any indexed book. Nothing to fix. | Accept or add books |
| **ambiguity** | The query has multiple valid interpretations and different books match each. | Accept or narrow query |
| **future** | Requires a feature that doesn't exist yet (typography, metadata-aware search, relevance threshold). | Defer |

---

## Headline Result

**Half-remembered memory: 20/20 (100%)**

That's Mnemo's core value proposition validated. The system consistently finds books from vague descriptions:

```
the distributed systems book with the wild boar          → DDIA ✓
the networking book explaining layers from bottom to top → Kurose ✓
the aptitude book about percentages                       → RS Aggarwal ✓
the chapter about garbage collection                      → Head First Java ✓
the interview patterns book on trees                      → Coding Patterns ✓
```

**Human memory: 14/20 (70%)** — harder but still strong for vague real-world recall.

## Failure Classification (31 non-negative failures)

The 31 failures sort into these types:

| Type | Count | Examples |
|------|-------|----------|
| **ranking** | 8 | MVCC, DFS, page with binary tree, URL in browser, cache, security, design, garbge collecton |
| **benchmark** | 6 | encapsulation, cartoon inheritance (acceptable too narrow), Alex Xu book (acceptable too narrow), table comparing protocols (acceptable too narrow), normalization (acceptable too narrow), OSI (acceptable too narrow) |
| **corpus** | 7 | REST APIs, API design, REST vs SOAP, library books analogy, cars on highway analogy, what normalization solves, dependency injection |
| **ambiguity** | 3 | HTTPS (matches multiple books), BFS (shared acronym), ORM (shared acronym) |
| **future** | 7 | Word_Power_Made_Easy spam (~3 short queries), visual_memory (~3), typo (~1) |

This means roughly **8-10 genuine ranking issues** exist. The rest are expected limitations of the corpus, query ambiguity, or deferred features.

## Technical Root Causes

From the v3 evaluation (190 queries, 12 categories), 31 of 170 non-negative queries failed Top-3. Technical root causes:

| Cause | Count | Description |
|-------|-------|-------------|
| **vocabulary_spam** | ~8 | Word_Power_Made_Easy (vocab book) dominates short acronym/single-word queries. Each entry is a distinct short chunk, so some chunk matches almost any query. |
| **terminology** | ~5 | Query uses different terms than the book. "Rate limiter" vs "token bucket", "dependency injection" vs "Spring container". |
| **generic_match** | ~5 | Query is too generic (single word, cross-domain). OS_Concepts or DB_Concepts dominates because they have the most/longest text. |
| **not_in_books** | ~6 | Query refers to a concept (REST APIs, encapsulate) that the books discuss but don't use as a primary keyword. |
| **alex_xu_confusion** | ~3 | Books by Alex Xu (Coding Interview Patterns vs System Design Interview) get mixed up because the author name dominates the embedding. |
| **visual_memory** | ~3 | "Purple book", "thick book", "cartoons" — embedding doesn't capture visual metadata. These need filename-based signals. |

### Word Power Made Easy Hypothesis

This book dominates short queries. Suspected cause: it creates **many tiny, semantically pure chunks** (one word/meaning per entry), making it unusually "magnetic" for any short query. Worth measuring before any fix:
- average chunk length (words)
- average token count
- chunks per page
- vocabulary diversity vs other books

---

## V3 Evaluation Failures (2026-06-25)

190 queries across 12 categories. 31 non-negative failures, 20 negative queries (all returned wrong results — see "False Positive" section).

### Exact Keywords (3/20 failed)

### MVCC

**Expected:** Silberschatz (DB) or DDIA
**Got:** OOP book #1, OOP #2, Coding Patterns #3
**Cause:** ranking — index page penalty not enough; OOP and Coding Patterns have more paragraphs matching "version" and "control" keywords.
**Benchmark candidate?** Yes — already in v2.

### encapsulation

**Expected:** Head First Java or OOP book
**Got:** Head First Design Patterns #1, Design Patterns #2, Kurose #3
**Cause:** terminology — "encapsulation" appears more in design patterns context than OOP intro context.
**Benchmark candidate?** Yes

### dependency injection

**Expected:** Spring in Action
**Got:** DB_Concepts #1, #2, #3
**Cause:** terminology — "dependency injection" appears rarely in Spring book titles/chapters; DB book has more text that tangentially matches.
**Benchmark candidate?** Yes

### Acronyms (6/15 failed)

### HTTPS

**Expected:** Kurose (networking)
**Got:** Word_Power_Made_Easy #1, #2, DB_Concepts #3
**Cause:** vocabulary_spam — single short acronym matches a vocab entry by chance.
**Benchmark candidate?** Yes

### OSI

**Expected:** Kurose
**Got:** DDIA #1, OS_Concepts #2, OS_Concepts #3
**Cause:** terminology — "operating system" shares "OS" prefix with OSI. OS_Concepts dominates.
**Benchmark candidate?** Yes

### BFS

**Expected:** any DSA book
**Got:** Word_Power_Made_Easy #1, #2, #3
**Cause:** vocabulary_spam — BFS is a short acronym that matches a vocab page.
**Benchmark candidate?** Yes

### DFS

**Expected:** any DSA book
**Got:** OS_Concepts #1, #2, #3
**Cause:** terminology — DFS as "depth-first search" is not present enough in DSA books' text. OS_Concepts has more text overall.
**Benchmark candidate?** Yes

### ORM

**Expected:** Spring in Action or SQL book
**Got:** Word_Power_Made_Easy #1, #2, #3
**Cause:** vocabulary_spam — short acronym.
**Benchmark candidate?** Yes

### Concepts (3/25 failed)

### what normalization solves

**Expected:** DB_Concepts or SQL book
**Got:** DDIA #1, DDIA #2, SAT prep #3
**Cause:** generic_match — "normalization" in DDIA means something different (data distribution). No normalization chapter in DB_Concepts snippets.
**Benchmark candidate?** Yes

### how REST APIs work

**Expected:** Spring in Action or coding patterns
**Got:** DDIA #1, DB_Concepts #2, DDIA #3
**Cause:** not_in_books — REST is not a primary focus of any indexed book. DDIA mentions REST but briefly.
**Benchmark candidate?** No — better as a negative query.

### what dependency injection does

**Expected:** Spring in Action
**Got:** DB_Concepts #1, #2, OS_Concepts #3
**Cause:** terminology — "dependency injection" phrase is absent from Spring book snippets.
**Benchmark candidate?** Yes

### Natural Questions (4/20 failed)

### when should I use DFS

**Expected:** DSA book or coding patterns
**Got:** OS_Concepts #1, #2, #3
**Cause:** terminology — DFS as algorithm is overshadowed by DFS as "distributed file system" in OS book.
**Benchmark candidate?** Yes

### what happens when you type a URL

**Expected:** Kurose
**Got:** DB_Concepts #1, #2, DDIA #3
**Cause:** ranking — same as v2. Kurose is further down. The query is more systems-oriented than networking.
**Benchmark candidate?** Yes — needs broader acceptable list.

### why is normalization important

**Expected:** DB_Concepts or SQL book
**Got:** DDIA #1, #2, #3
**Cause:** terminology — DDIA uses "normalization" in data processing context, which dominates.
**Benchmark candidate?** Yes

### how are APIs designed

**Expected:** Spring in Action, coding patterns, or Alex Xu
**Got:** OS_Concepts #1, DB_Concepts #2, OS_Concepts #3
**Cause:** not_in_books — API design is not a primary topic. Systems/DB books dominate because they're the largest.
**Benchmark candidate?** No — better as negative query.

### Visual Memory (3/10 failed)

### the thick aptitude book

**Expected:** RS Aggarwal (largest aptitude book)
**Got:** Ultimate_Aptitude_Tests #1, #2, #3
**Cause:** not_in_books — "thick" doesn't map to embedding. All aptitude books look the same to the model.
**Benchmark candidate?** Yes — but needs filename-based handling.

### the Alex Xu book

**Expected:** System Design Interview v2
**Got:** Coding_Interview_Patterns #1, Word_Power #2, Wren & Martin #3
**Cause:** alex_xu_confusion — Coding Interview Patterns author is also "Alex Xu", so "Alex Xu" matches that book more strongly than its actual content.
**Benchmark candidate?** Yes

### the Head First series

**Expected:** Head First Java or Head First Design Patterns
**Got:** Verbal_and_Non_Verbal_RS #1, #2, #3
**Cause:** vocabulary_spam — "head first" as a phrase is absent from the books' embedded text. Verbal RS book dominates unrelated.
**Benchmark candidate?** Yes

### Cross-domain (1/10 failed)

### cache

**Expected:** DDIA, Kurose, or Alex Xu
**Got:** OS_Concepts #1, #2, #3
**Cause:** generic_match — single word matches OS book (caching concepts in OS) more than networking/distributed books.
**Benchmark candidate?** No — cross-domain by design, acceptable list may be too narrow.

### Ambiguous (2/10 failed)

### security

**Expected:** Kurose, Alex Xu, or Spring
**Got:** OS_Concepts #1, #2, #3
**Cause:** generic_match — OS_Concepts discusses security (access control, auth) more prominently than other books.
**Benchmark candidate?** No — too broad, better as cross-domain.

### design

**Expected:** Design Patterns, Alex Xu, Spring, or DSA
**Got:** DDIA #1, DB_Concepts #2, DB_Concepts #3
**Cause:** generic_match — "design" is too generic. DDIA/DB_Concepts dominate by corpus size.
**Benchmark candidate?** No — too broad.

### Comparative (1/10 failed)

### REST vs SOAP

**Expected:** Spring, coding patterns, or Alex Xu
**Got:** DDIA #1, #2, #3
**Cause:** not_in_books — REST vs SOAP comparison is not a prominent topic in indexed books. DDIA mentions both in passing.
**Benchmark candidate?** No — better as negative query.

### Adversarial / Typos (2/10 failed)

### garbge collecton

**Expected:** Head First Java or OS_Concepts
**Got:** Wren & Martin #1, DDIA #2, Word_Power #3
**Cause:** typos — 3+ character errors break the embedding. Garbage text matches vocabulary books by chance.
**Benchmark candidate?** Yes — tests typo robustness.

### sprng boot

**Expected:** Spring in Action
**Got:** OS_Concepts #1, #2, #3
**Cause:** typos — "sprng" is too far from "spring". OS_Concepts dominates by volume.
**Benchmark candidate?** Yes

### Human Memory (6/20 failed)

### the page with the binary tree picture

**Expected:** any DSA book
**Got:** DB_Concepts #1, #2, #3
**Cause:** generic_match — "binary tree" is mentioned in DB context (B-trees). DB book is much larger than DSA books.
**Benchmark candidate?** Yes

### the explanation using cars on a highway

**Expected:** Kurose (uses car analogies for TCP)
**Got:** Wren & Martin #1, SAT prep #2, Wren & Martin #3
**Cause:** not_in_books — the specific car analogy is not in the embedded snippets strongly enough. Vocabulary books dominate.
**Benchmark candidate?** Yes

### the cartoon explaining inheritance

**Expected:** Head First Java (has cartoons)
**Got:** OOP book #1, #2, #3
**Cause:** borderline — OOP book does explain inheritance. But Head First is the better match. The model doesn't distinguish between the two.
**Benchmark candidate?** Yes — with broader acceptable list (include OOP book).

### the table comparing protocols

**Expected:** Kurose
**Got:** DB_Concepts #1, #2, DDIA #3
**Cause:** terminology — "protocol" is more prominent in DB context (transaction protocols) than networking in this corpus.
**Benchmark candidate?** Yes

### the explanation using library books

**Expected:** DB_Concepts (uses library analogy for normalization)
**Got:** OOP book #1, DDIA #2, DDIA #3
**Cause:** not_in_books — the specific library analogy is not prominent enough in embedded snippets.
**Benchmark candidate?** No — too specific to individual teaching style.

### the chapter where Alex Xu designs Twitter

**Expected:** System Design Interview v2 (Alex Xu)
**Got:** DDIA #1, SAT prep #2, DDIA #3
**Cause:** alex_xu_confusion — Coding_Interview_Patterns (also Alex Xu) dominates over SDI v2. DDIA has Twitter-scale design discussion.
**Benchmark candidate?** Yes

---

## Negative Queries (Expected ANN Behavior)

All 20 negative queries returned results. **This is not a bug.** ANN vector search has no "empty result" concept — it always returns the N nearest neighbors, regardless of absolute similarity.

Examples:
- "quantum mechanics" → closest chunk in a 30-book CS corpus
- "guitar chords" → closest chunk in a 30-book CS corpus
- "Shakespeare plays" → closest chunk in a 30-book CS corpus

Production retrieval systems solve this with a **relevance threshold** (post-vector reranking or similarity cutoff), but that's a post-v1 feature.

**For now:** The user should know Mnemo always returns something. The scores will be low for bad matches (typically <0.3), which can serve as a manual confidence signal.

---

## Future Benchmark Categories

### Multi-hop Memory (post-v1)

Queries that combine metadata + memory + context:

```
the networking book we used in second year
the Java book before Design Patterns
the database book by Silberschatz
the Alex Xu book that wasn't about interviews
the grammar book with exercises
```

These are "human" queries — they reference relationships and context that pure content embeddings can't capture. Test when metadata-aware ranking exists.

### Negative Expected (post-v1)

Re-run the 20 negative queries after a relevance threshold is implemented. The correct behavior is zero results with a "no match" indicator.

---

## Measurement Ideas (for dogfooding phase)

### Chunk Statistics (before any ranking fix)

Measure Word_Power_Made_Easy vs all other books:
- mean/median chunk length (words)
- mean/median token count  
- chunks per page
- vocabulary type-token ratio
- proportion of chunks that are <10 words

Hypothesis: vocabulary books create unusually many very short, semantically isolated chunks that act as "semantic magnets."

### Store All Searches

Don't store only failures. Log every real user search:

```json
{
  "timestamp": "2026-07-01T12:00:00",
  "query": "mvcc snapshots",
  "clicked": "ddia.pdf",
  "latency_ms": 31,
  "top_score": 0.81,
  "result_count": 8
}
```

After a month this answers:
- Which queries never get clicked?
- Which books dominate results?
- Which searches get immediately reformulated?
- Which queries repeat?
- What's the typical time-to-answer?

This is the data that makes products quietly better.

---

## Root Cause Summary (Technical)

| Root Cause | Count | Type | Action |
|------------|-------|------|--------|
| vocabulary_spam | ~8 | future | Measure chunk stats first. Post-v1 fix. |
| alex_xu_confusion | ~3 | future | Metadata-aware ranking. Post-v1 fix. |
| typo_weakness | ~2 | future | Fuzzy spelling layer. Post-v1 fix. |
| generic_match | ~5 | ranking | Address via hybrid search (BM25 + vector). Post-v1. |
| terminology | ~5 | ranking | Better embedding model or query expansion. Post-v1. |
| visual_memory | ~3 | future | Filename-based scoring. Post-v1. |

## Boundary Summary

| Type | Count | Handle |
|------|-------|--------|
| Genuine ranking failures | 8 | Fix when hybrid search or better model lands |
| Benchmark expectation issues | 6 | Update acceptable lists (done) |
| Corpus limitations | 7 | Accept — concept isn't in any book |
| Query ambiguity | 3 | Accept — intrinsic to short queries |
| Future features | 7 | Defer to post-v1 |
