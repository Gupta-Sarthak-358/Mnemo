# Mnemo — Product Requirements Document

> **Product name:** Mnemo *(working title — replace if changed)*
> **Tagline:** Your files remember what you meant.
> **Document type:** Product Requirements Document (PRD)
> **Audience:** Product, strategy, and anyone who needs to understand *why* this exists before touching code
> **Version:** 1.0
> **Status:** Pre-build

---

## 1. The Problem

Human memory is contextual. Human file systems are alphabetical.

When someone reads a paper, they encode meaning — arguments, ideas, implications. When they need that paper again three weeks later, they remember fragments: the idea, the rough topic, maybe the feeling of reading it. They almost never remember the filename.

Yet every search tool on every operating system expects a filename.

The result: people spend measurable time every week searching for things they've already found once. The file exists. The knowledge exists. The memory of having read it exists. What doesn't exist is a bridge between how humans store meaning and how computers store files.

This is not a new problem. It is a consistently unsolved one — despite decades of operating systems, reference managers, and recently, AI-powered tools.

**The core failure of existing tools:**

Most tools solve the *collection* problem. Zotero helps you gather papers. Mendeley helps you organize them. Dropbox helps you store them. NotebookLM helps you query documents you manually upload to it.

None of them solve the *retrieval* problem for files that already exist in your system, in your folders, organized in whatever chaotic way you've been organizing them for years.

Mnemo solves exactly that. Nothing else.

---

## 2. The Insight

There are three things that make this product possible now when it wasn't five years ago:

**1. Small embedding models are good enough.** Models like `all-MiniLM-L6-v2` run entirely on CPU, use ~90MB of RAM, and produce semantic embeddings good enough to match conceptual queries to relevant paragraphs. No GPU, no cloud, no API key.

**2. SQLite is more capable than people realize.** With `sqlite-vec`, vector search lives inside SQLite. The entire product state — file metadata, chunk text, embeddings, access logs — fits in one `.db` file. Backup is `cp`. Migration is a version table.

**3. Local-first is a genuine differentiator now.** Every major AI product in this space requires cloud upload. Researchers with unpublished data, proprietary datasets, or institutional constraints cannot use them. The local constraint is not a limitation — it's the product.

---

## 3. Vision

Mnemo is a personal memory layer for your local files.

Not a search engine. Not a reference manager. Not a chatbot for your documents.

A memory layer — something that sits invisibly in the background, learns what you care about, and surfaces it the moment you need it. Like remembering, but reliable.

The end state: a researcher (or lawyer, or writer, or analyst) presses a hotkey, types a half-remembered idea, and finds the exact paragraph within two seconds. No folders. No filename guessing. No cloud. No configuration. No cognitive load.

The experience should feel less like searching and more like remembering.

---

## 4. Target Users

### Primary (v1): Researchers

**Who:** Academic researchers, PhD students, independent researchers. Anyone who accumulates PDFs faster than they can organize them.

**Volume:** Typically 100–2000 PDFs. Often a mix of properly named files and chaos.

**Pain:** Cannot retrieve specific paragraphs, methodologies, statistics, or citations from memory. Knows they read something; cannot locate it. Loses 30–60 minutes per week to this problem.

**Constraint:** Cannot upload unpublished work, proprietary data, or pre-publication papers to cloud tools. Local-first is non-negotiable.

**Motivation to try:** Already frustrated. Already aware the problem exists. Will install a daemon if the promise is specific enough.

### Revenue Target (post-v1): Knowledge Workers in Billable Professions

**Who:** Lawyers, consultants, financial analysts, journalists, policy researchers.

**Why they matter more economically:** A researcher losing 30 minutes feels inconvenience. A lawyer losing 30 minutes loses billable hours. Monetary pain converts faster than existential pain.

**Timing:** Build for researchers first to get the product right. Sell to this segment to get the business right.

### Not the Target (v1)

- General consumers (low file volume, low pain)
- Enterprise IT departments (procurement cycles, compliance complexity)
- Developers searching code (different chunking, different mental model)

---

## 5. User Personas

### Persona 1 — The Researcher (Primary)

**Name:** Priya, 28, PhD candidate in NLP

**Setup:** 800 PDFs accumulated over 3 years. Half in organized folders from her first year. Half in a Downloads folder and three project directories that grew organically.

**Behavior:** Downloads papers as she finds them, reads them in bursts, and returns to them weeks or months later. Uses Zotero for some papers. Not all of them. Can never remember which.

**Frustration:** "I know I read a paper that compared RLHF with direct preference optimization in low-resource settings. I cannot find it. I've spent 20 minutes searching."

**What she wants:** To type what she remembers and get the paper immediately. Without uploading anything. Without changing how she works.

**What she doesn't want:** Another app that requires her to import papers into it first.

---

### Persona 2 — The Independent Writer/Researcher

**Name:** Marcus, 41, freelance science journalist

**Setup:** 1200 PDFs, 400 TXT notes, and a folder structure that made sense in 2019 and hasn't since.

**Behavior:** Collects sources while researching articles. Comes back to them during writing, often months later. Remembers arguments, not filenames.

**Frustration:** "I bookmarked a study about long-term memory consolidation. It's somewhere in my Research folder. Probably. I've been looking for 15 minutes."

**What he wants:** To search the way he thinks — by idea, not by filename.

---

## 6. User Stories

**Core stories (must work in v1):**

- As a researcher, I want to type a concept and find the paper that discussed it, so I don't spend time digging through folders.
- As a researcher, I want results to show the exact paragraph that matched my query, so I can verify it's the right document before opening it.
- As a researcher, I want my files indexed automatically when I add them to my folder, so I don't have to manually import anything.
- As a researcher, I want scanned PDFs to be searchable too, so I can find older papers that were digitized as images.
- As a researcher, I want to open the file directly from search results, so I can go from query to reading in seconds.
- As a user, I want the tool to get better at finding what I specifically open, so it learns my personal usage patterns over time.

**Secondary stories (v1 if time, otherwise v2):**

- As a user, I want to know when a file couldn't be indexed and why, so I'm not confused when results are missing.
- As a user, I want to choose which folders are watched, so I don't index irrelevant system directories.
- As a user, I want to change the hotkey, so it doesn't conflict with other tools I use.

**Post-v1 stories:**

- As a researcher, I want to see how I navigated to a discovery — which searches led to which files — so I can reconstruct my research path.
- As a user with many files, I want cross-document queries like "which papers mention X," so I can find patterns across my library.

---

## 7. Jobs to Be Done

The product competes not just with other tools but with what users currently do to solve this problem.

| Job | Current solution | Mnemo's solution |
|-----|-----------------|-------------------|
| Find a paper by remembered idea | Scroll folders, guess filenames, Google the concept again | Type the idea, get the paper in 2 seconds |
| Retrieve a specific statistic from a paper | Open 5 candidate PDFs, Ctrl+F each one | Type the statistic context, get the paragraph |
| Find a paper read months ago | Zotero search (if imported), browser history, email to self | Type what you remember, behavioral ranking surfaces it |
| Access a scanned paper | Open the PDF, manually scroll through images | OCR-indexed at ingest, fully searchable |

---

## 8. Success Metrics

### Activation (does the user get value quickly?)
- Time from install to first successful retrieval: **< 10 minutes**
- Files indexed before user makes first search: **most recently modified files first, so top 20% of library indexed within 2 minutes**

### Retention (does the user keep coming back?)
- Daily active use: user opens at least one file via Mnemo per working day
- 30-day retention target: **60%+** (if they use it daily for a week, they keep using it)

### Quality (does search actually work?)
- Top-3 accuracy on retrieval evaluation dataset: **> 80%** before shipping
- User click-through rate on first result: track via `search_events`, target **> 50%**
- Searches with no click (result irrelevant): track and minimize

### Growth (for post-v1)
- Word of mouth: researchers share it with lab mates
- GitHub stars (if open-source) as proxy for developer trust

---

## 9. Competitive Positioning

### The landscape

| Tool | Type | Local? | Passive indexing? | Behavioral learning? |
|------|------|--------|-------------------|----------------------|
| Zotero | Reference manager | Partial | No (manual import) | No |
| Mendeley | Reference manager | No | No | No |
| NotebookLM | AI document Q&A | No | No | No |
| SciSpace | AI research tool | No | No | No |
| Spotlight | OS search | Yes | Yes | No |
| Windows Recall | OS search | Yes | Yes | No |
| Mnemo | Memory layer | Yes | Yes | Yes |

### The white space

Mnemo is the only tool that is simultaneously:
- Local-first (no upload, no account)
- Passive (no manual import ritual)
- Behaviorally adaptive (gets better for your specific usage over time)
- Portable (your `.db` file moves with you across machines)

### The OS threat

Apple Intelligence and Windows Copilot+ Recall are building OS-level semantic search. This is both a threat and a validation.

**What they will do well:** Generic semantic search for the average user.

**What they structurally cannot do:**
- Serve Linux users
- Serve air-gapped or offline environments
- Carry behavioral memory across machines (their data resets on reinstall)
- Serve users who cannot let an OS vendor index sensitive research
- Optimize for you specifically over time (they optimize for the average user)

The strategic anchor: compete on specialized memory for specialized users, not generic search for everyone.

---

## 10. Go-to-Market Strategy

### Phase 1 — Validation (v1)

**Channel:** Direct to researchers. Twitter/X academic community, r/PhD, r/academia, personal networks.

**Positioning:** "Local semantic search for your PDF library. No cloud. No import. Works on your existing folders."

**Goal:** 50–100 researchers using it daily. Gather qualitative feedback on retrieval quality, friction points, edge cases.

**Not doing:** Paid acquisition, Product Hunt launch, press. Too early. Product isn't validated yet.

### Phase 2 — Growth (post-v1)

**Channel:** If v1 retention is strong, launch on Product Hunt. Write a technical post on the architecture (attracts developer audience who become evangelists).

**Expand to:** Lawyers, consultants, analysts. Reposition messaging around "billable hours lost to searching."

**Pricing hypothesis:** Free for researchers (validation, word of mouth), paid tier for professionals ($10–15/month or one-time $40–60). No freemium complexity — one plan that just works, optional payment for sustainability.

### Phase 3 — Defensibility

The longer the behavioral layer accumulates, the harder Mnemo is to replace. This is the compounding moat — not network effects, but personal lock-in that deepens over time.

At scale: consider a one-click export of the `.db` file as a backup feature. Paradoxically, making it easy to leave makes users more willing to stay.

---

## 11. Pricing Thoughts

Not decided. Some options:

**Option A — Free + Paid tier**
- Free: up to 500 files, core search
- Paid ($12/month or $60 one-time): unlimited files, OCR, behavioral ranking, priority support
- Risk: 500 file limit feels arbitrary and annoying

**Option B — One-time purchase**
- $40–60 lifetime license
- Simple. No subscription anxiety. Fits the local-first ethos.
- Risk: no recurring revenue

**Option C — Fully free, open-source**
- Build reputation and trust. Monetize later via pro features or consulting.
- Fits the researcher audience (they expect free tools)
- Risk: no revenue path

**Recommendation for now:** Don't decide. Ship v1 free. Talk to users. Decide pricing when you understand what they value enough to pay for.

---

## 12. Feature Prioritization

### Must Have (v1)
- PDF parsing (text + OCR fallback)
- TXT parsing
- Paragraph-level chunking with neighbor context
- Semantic search via sqlite-vec
- Hotkey launcher (Ctrl+Space)
- Snippet results with click-to-open
- Automatic folder watching
- Access log + behavioral ranking
- Cold-start indexing (mtime-ordered)
- Schema migration system

### Should Have (v1 if capacity, else v2)
- Configurable hotkey
- First-run folder picker
- Daemon crash recovery
- File deduplication by hash
- Per-file index status (pending / indexing / complete / failed)

### Nice to Have (v2)
- Memory Trails (search journey reconstruction)
- DOCX support
- Re-embedding pipeline for model upgrades
- Cross-document queries ("which papers mention X")
- Adaptive ranking weights over time

### Will Not Do
- Cloud sync
- Accounts
- Chat interface / "ask your documents" mode
- Mobile app
- Browser extension
- Multi-user support
- Enterprise features

---

## 13. User Journey (v1)

```
1. INSTALL
   User downloads and installs Mnemo.
   Daemon starts automatically.

2. FIRST RUN
   A minimal prompt appears once:
   "Which folders should Mnemo watch?"
   User picks 1–3 folders. Done.
   Prompt never appears again.

3. BACKGROUND INDEXING
   Daemon indexes watched folders silently.
   Most recently modified files first.
   User can immediately start searching —
   even partial indexing is useful.

4. FIRST SEARCH
   User presses Ctrl+Space anywhere on the OS.
   A floating search box appears.
   User types a concept.
   Results appear within 1–2 seconds.
   Each result shows: filename + matched paragraph.

5. FILE OPEN
   User clicks a result.
   File opens in its default application.
   Access is logged silently.

6. OVER TIME
   Tool learns which files the user repeatedly opens
   after specific queries.
   Rankings become more personal.
   The product starts to feel like memory.

7. TRUST
   User stops thinking about where files are.
   They just search.
   The tool becomes invisible infrastructure.
```

---

## 14. Risks

### Product Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Search quality is mediocre | Medium | Critical | Retrieval eval dataset. Measure before shipping. |
| OCR is too slow on large libraries | High | Medium | Priority queue. Process recent files first. |
| Hotkey conflicts with OS | Medium | High | Make it configurable. Document known conflicts. |
| Scoped too narrowly (PDF+TXT) | Low | Low | Intentional. Expand after v1 proves quality. |
| SQLite hits performance ceiling at scale | Low | Medium | Benchmark at 1000 PDFs. sqlite-vec is fast. |

### Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OS vendors ship this natively | Medium | High | Focus on Linux, air-gapped, portable memory. |
| Researchers don't pay | High | Medium | Build for researchers, monetize via professionals. |
| Competitor copies the behavioral layer | Medium | Low | Personal data accumulation is the moat, not the feature. |

---

## 15. What This Is Not

Repeated here because scope creep is how products die.

- **Not a chatbot.** Users search. They don't converse with their documents.
- **Not a cloud product.** No upload. No account. No exceptions.
- **Not a reference manager.** Doesn't care how files are organized. Works on existing chaos.
- **Not an enterprise tool.** No admin dashboards, no team features, no compliance modes.
- **Not a note-taking app.** Mnemo reads files. It doesn't create them.

---

## 16. Open Questions

Things not decided yet that will need answers before or shortly after v1:

1. **Product name confirmed?** Working title is Mnemo. Decide before any public presence.
2. **Open-source or closed?** Affects distribution, trust, and business model significantly.
3. **Windows-first or cross-platform from day one?** Windows is the build target. Linux is the strategic audience. When do you serve both?
4. **Pricing model?** Don't decide until post-v1 user conversations.
5. **What does the icon look like?** Needs to live in the system tray. Should feel minimal and intelligent, not another colorful SaaS blob.
6. **Minimum supported file count for good behavioral ranking?** How many accesses before the behavioral signal meaningfully improves results? Probably 2–3 weeks of natural use. Worth measuring.

---

## 17. Post-v1 Vision

The long-term version of Mnemo is not a search tool.

It's a knowledge graph of one person's intellectual life — built passively, from files they already have, from behavior they naturally exhibit, from queries they intuitively form.

Eventually:
- Memory Trails show how discoveries were made
- Cross-document connections emerge without manual tagging
- The behavioral layer becomes a map of a person's intellectual history

None of that is in v1. All of it should inform what v1 is designed to not break.
