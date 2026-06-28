# Discussion Context: How This Product Was Born

## Origin

Started from a simple prompt: *"Tell me a small problem that needs to be solved with software."*

The answer was the "where did I save that?" problem — the universal experience of remembering a concept from a document but not being able to locate the file. OS search tools match filenames. Not ideas. Not sentences. Not memory.

That single observation expanded into a full product conversation, two rounds of external AI critique, and a set of architectural corrections that materially changed the build plan.

---

## The Core Problem Statement

Human file organization is mostly wishful thinking. Folders named:

```
Research
Research_New
Research_Final
Research_Final_2
Research_Final_2_UseThisOne
```

Six weeks later, you're searching for "that article about memory constraints and transformers" while staring at 437 PDFs named like archaeological artifacts.

**The fundamental mismatch:**

Humans remember *concepts* — "the PDF that compared RAG and fine-tuning."

Traditional search expects *filenames* — `rag_vs_finetuning_2025.pdf`.

These are different things. Nobody built the bridge. That's the product.

---

## The Right Framing (And Why It Matters)

**Wrong:** "Semantic search for files"

**Wrong:** "AI file retrieval"

**Wrong:** "Vector search for documents"

**Right:** "Your files remember what you meant."

This isn't marketing polish. It describes what the behavioral layer actually does. When a user searches "attention paper" and the tool surfaces the exact paper they always open — they stop thinking "good search" and start thinking "this thing knows me." That transition from utility to habit is where retention lives.

Nobody buys search. People buy finding the thing they forgot. People buy recovering lost context. People pay to avoid feeling stupid.

---

## Who Feels This Pain

- Researchers with hundreds to thousands of papers
- Students losing references mid-thesis
- Writers losing sources mid-essay
- Developers losing documentation mid-project
- Lawyers losing case documents mid-brief

---

## The Customer Distinction (Important)

**Researchers** are the right *validation* customer. Their pain is clearest, their libraries most chaotic, and they can articulate exactly what's missing better than anyone.

**Researchers are the wrong *revenue* customer.** Grant constraints, university bureaucracy, limited software budgets. A PhD student feels existential pain — abundant and unfortunately difficult to monetize.

**Lawyers, consultants, analysts, journalists** lose *billable hours* searching. A lawyer spending 20 minutes locating a case document feels monetary pain immediately.

**Strategy:** Build for researchers first to get the product right. Sell to lawyers and consultants to get the business right. Don't confuse who helps you build it with who pays for it.

---

## Competitive Landscape

### Existing tools and why they don't fully solve it

| Tool | What it does | What it misses |
|------|-------------|----------------|
| Zotero | Organizes + searches metadata | Requires manual import, no semantic retrieval |
| Mendeley | PDF management | Same gaps as Zotero |
| SciSpace | AI Q&A on papers | Only works on papers found through SciSpace |
| NotebookLM | Q&A on uploaded docs | Manual upload, cloud-dependent |
| Elicit | Literature synthesis | Online papers only, not your local library |
| Spotlight / Windows Search | Filename + basic content | No semantic understanding |

**The pattern:** Researchers still complain despite these tools existing. That means the problem isn't solved. Existing solutions don't fit existing workflows — researchers already have folders, Zotero libraries, lab drives. They don't want to migrate. They want something that works on what they already have.

The strongest sentence in the product concept isn't about embeddings. It's: *"Works on the folders you already have."* Asking researchers to reorganize their document graveyards is how products die.

### The OS Threat

Apple Intelligence (macOS) and Windows Copilot+ (Recall) are doing OS-level file indexing. This changes the strategic question from "Can we build semantic file search?" to "Can we build something operating systems won't prioritize?"

**What OS vendors won't optimize for:**
- Linux users
- Air-gapped / offline environments
- Researchers with sensitive unpublished data
- Cross-platform consistency
- Custom ranking logic
- Local model choice by user
- Behavioral memory that moves with you across machines

OS movement into this space is scary and also proof you're not hallucinating a market. The window is real but probably 18–24 months before native tools are good enough for average users. Competing on generic search is eventually a losing battle. Competing on specialized memory is stronger.

---

## Key Design Decisions and Their Reasoning

### 1. Framing
"Personal memory layer for files" — not search. Decided early and validated by every subsequent critique.

### 2. UI Philosophy
Full desktop app (React + Tauri) was the first instinct. Rejected. Tauri + React means you end up building settings pages, onboarding flows, themes, and account systems while core search quality is still mediocre.

**Correct v1 UI:** Background daemon + `Ctrl+Space` hotkey + search box + snippet results + click to open. Nothing else.

### 3. Stack Selection
- **ChromaDB rejected:** Dependency overhead becomes maintenance obligation.
- **FAISS rejected:** Doesn't persist natively — serialize/deserialize cycle on every restart, fragile across OS updates.
- **`sqlite-vec` chosen:** Vector search inside SQLite. One `.db` file. Metadata, access logs, embeddings, all transactional. Entire product state is one file you back up with `cp`.

### 4. Chunking Strategy
Paragraph-level with neighbor context. Not fixed token windows. MiniLM vs bge-small is a ~3% quality difference. Chunking strategy is a ~30% quality difference. Most RAG projects die here, not at the model choice.

### 5. Ranking Signals
Three signals: semantic similarity + recency (`mtime`) + access frequency from logs.

**Updated weights after critique:** `0.80 semantic + 0.10 recency + 0.10 access` for v1. Original proposal was 0.60/0.25/0.15 — too much weight on recency, which would surface files modified yesterday over actually relevant papers. Semantic dominates until the access log earns its weight through sufficient signal.

### 6. The Behavioral Layer
When a user opens a file from results, log it. After weeks of use, the same query consistently opening the same file boosts that file's ranking for that user. No ML. No GPU. Just evidence. The tool learns what *you* mean by your own queries.

This is where the product stops being semantic search. Semantic search is becoming commodity infrastructure. Behavioral memory is not. One user's "attention paper" is Vaswani et al. Another's is FlashAttention. The query is identical. The intent is personal. Over time you stop ranking documents — you rank memories.

### 7. Cold Start Solution
Index by `mtime` descending. Files touched last week are almost certainly what you'll search for this week. User gets useful results in minutes while the daemon finishes the rest in background.

### 8. Confidence Communication
Show the matched paragraph snippet. Don't show a numerical score. The evidence is the confidence signal — users recognize the passage or they don't. 0.73 means nothing. Seeing the actual sentence means everything.

### 9. OCR
Yes, as a soft dependency. Tesseract check at startup. If missing, scanned PDFs are logged as skipped with a clear message. No silent failure. Researchers will have 20–30% scanned papers — skipping OCR breaks the tool for them.

### 10. File Scope
PDF + TXT only for v1. DOCX, markdown, code files are post-v1. Scope discipline is the strongest engineering decision in the whole spec.

---

## Architectural Corrections (From Critique Round 2)

### Migration table on day one
Add `schema_version` table before writing any other table. Costs twenty minutes. Saves a catastrophic reindex disaster when the schema evolves. The irony of a memory tool forgetting your memory because of a schema change is too on the nose to risk.

### Separate chunk schema
Original spec had vectors and metadata in one virtual table. Corrected to separate `chunks` (text + metadata) from `chunk_embeddings` (vectors only). Reason: when the embedding model changes — and it will — you want to re-embed without touching text and metadata. Decoupled from the start.

### OCR queue with priority
Researchers have 500–3000 PDFs. A 400-page scanned dissertation can trigger 400 image renders and 400 OCR passes, blocking the entire indexing queue. Solution: tiered OCR queue — recent PDFs first, large scanned jobs last. Users get searchable results fast.

### Query cache
1000 PDFs, 200k chunks — latency grows. Humans repeat approximate queries ("attention paper," "attention memory paper," "attention scaling paper"). A lightweight cache on similar queries shaves perceived latency without complexity.

### Retrieval evaluation dataset
Build 100 query-to-file pairs immediately. Measure top-1 and top-3 accuracy every time chunking, ranking, or embeddings change. Without this you're doing astrology. With it, you're engineering.

### search_events table
Separate from `access_log`. Stores every search, including ones where the user searched and never clicked. "Searched, never clicked" and "searched, clicked result #3" are future ranking signals. Store them from day one. Storage is cheap. Human memory is not — that's the entire reason this product exists.

---

## The Moat — Honest Assessment

**The behavioral layer is useful but not a venture-scale network-effects moat.** Competitors can copy `query -> clicked_file` in an afternoon.

**The deeper moat is the accumulated retrieval dataset:** query + clicked file + dwell time + repeat access + ignored results. Millions of personal relevance judgments. Much harder to recreate. The moat isn't the feature — it's the dataset generated by the feature.

**But there's a local-first constraint:** You cannot aggregate behavioral data across users if everything stays on device. So this is not a network-effects moat. It's a personal lock-in moat — which is actually stronger for retention. Nobody churns from a tool that knows six months of their specific behavior. Different kind of defensibility. Be clear-eyed about which one you're building.

Spotlight resets on reinstall. Windows Recall resets on machine migration. This tool, with its SQLite file, carries six months of behavioral memory that moves with the user. OS tools optimize for the average user. This tool optimizes for you specifically, over time.

---

## Post-v1 Feature: Memory Trails

Not in v1. Soon after.

Store the journey, not just the destination:

```
query → opened file → time spent → next file opened
```

Researchers remember paths. "I found Paper A, which led me to Paper B, which referenced Paper C." Reconstructing that journey transforms the product from file retrieval into knowledge reconstruction. Nobody does this. It's the feature that makes the product feel like a research partner rather than a search box.

---

## Relation to Existing Work

`sqlite-vec`, `FastAPI`, and background daemon architecture overlap significantly with Nyx Core's existing infrastructure. This is not starting from zero. The chunking pipeline, embedding model integration, and file watching are additive to patterns already built.
