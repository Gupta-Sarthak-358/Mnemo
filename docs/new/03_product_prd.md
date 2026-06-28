# Mnemo — Product Requirements Document

> **Version:** 1.1 (updated post-alpha build)
> **Status:** Alpha built and working. Entering dogfooding phase.

---

## One-Line Description

A local background daemon that watches your folders, indexes your files semantically, learns your behavior, and lets you retrieve anything using how you actually remember it — privately, without cloud, without changing how you work.

---

## Current Product State

Mnemo is no longer a spec. It is running software.

The backend is stable. OCR is complete. The launcher UI is functional. Hybrid search is working at 82% Top-3 accuracy on a 190-query benchmark. The hotkey works globally. The window lifecycle is correct.

The bottleneck has shifted from engineering to retrieval quality and experience polish. Every meaningful improvement from here is either search quality (measurable) or UX feel (observable). Neither requires new infrastructure.

---

## The Problem

Human memory is contextual. Human file systems are alphabetical.

People remember fragments — the argument, the rough topic, sometimes the feeling of reading something. They don't remember filenames. Yet every OS search tool expects a filename.

The result: people spend real time every week searching for things they've already found once.

**The existing tools and why they fail:**

| Tool | What it misses |
|------|---------------|
| Zotero / Mendeley | Manual import required. Doesn't work on existing folders. |
| SciSpace / NotebookLM | Cloud. Can't use with unpublished or sensitive data. |
| Spotlight / Windows Search | Filename and basic content match. No semantic understanding. |
| Windows Recall | Resets on reinstall. No portable behavioral memory. |

Mnemo's white space: local, passive, behaviorally adaptive, portable across machines.

---

## Target Users

### Primary (v1): Researchers
Large PDF libraries (100–2000 papers). Cannot upload sensitive data. Already frustrated with existing tools. Articulate about what's missing.

### Revenue Target (post-v1): Knowledge Workers in Billable Professions
Lawyers, consultants, analysts, journalists. They lose billable hours, not just time. Monetary pain converts faster.

**Strategy:** Build for researchers to get the product right. Sell to professionals to get the business right.

---

## User Personas

### Priya — PhD Candidate, NLP
800 PDFs over 3 years. Half organized, half chaos. Searches for "that paper comparing RLHF with DPO in low-resource settings" — can't find it after 20 minutes. Doesn't want to import papers into another tool. Just wants to type what she remembers.

### Marcus — Freelance Science Journalist
1200 PDFs, 400 TXT notes, a folder structure that made sense in 2019. Collects sources while researching, returns months later. Remembers arguments, not filenames. Needs to search the way he thinks.

---

## What Mnemo Does (Validated)

1. Watches selected folders for new/modified files
2. Indexes PDFs and TXT files automatically
3. Handles scanned PDFs via background OCR (priority queue)
4. Accepts natural language queries via `Ctrl+M` launcher
5. Returns hybrid-ranked results (semantic + keyword) with paragraph snippets
6. Groups multiple results from the same document into one card
7. Shows page numbers, score labels, "Why this matched" concept tags
8. Opens file directly from results (default OS application)
9. Logs access behavior for future ranking improvement
10. Shows "Continue Reading" and "Recent Searches" on empty state
11. Allows hotkey reconfiguration via settings dialog

---

## What Mnemo Does Not Do (v1)

- No DOCX, markdown, or code file parsing
- No cloud sync or accounts
- No "chat with your documents"
- No LLM summaries
- No settings dashboard (minimal settings dialog only)
- No web interface
- No mobile app

---

## User Journey (Actual, Post-Build)

```
1. INSTALL
   User installs Mnemo. Daemon starts.

2. FIRST RUN
   Folder picker appears once.
   User picks folders. Disappears forever.

3. BACKGROUND INDEXING
   Daemon indexes silently, most recently modified files first.
   Search is available immediately — partial indexing is useful.

4. SEARCH
   User presses Ctrl+M anywhere.
   Floating launcher appears.
   User types 3+ characters → 300ms debounce → results appear.
   Results show: book title, page numbers, snippets, concepts.
   Latency: 28–45ms.

5. OPEN
   User clicks a result.
   File opens in default application.
   Access logged silently.

6. OVER TIME
   Access logs shape ranking.
   Recent searches surface in empty state.
   The tool personalizes to this user's specific behavior.

7. TRUST
   User stops thinking about where files are.
   They just search.
   The launcher becomes muscle memory.
```

---

## Success Metrics

### Quality (current)
- Top-3 accuracy: **82%** (190-query benchmark)
- "Half-remembered memory" subset: **100%**
- Search latency: **28–45ms**
- Target before shipping to users: Top-3 > **85%**

### Activation
- Time from install to first successful retrieval: < 10 minutes
- First useful results available before full library indexed: ✓ (mtime-ordered indexing)

### Retention (to measure post-release)
- Daily active searches per user
- Click-through rate on first result (target: >50%)
- Searches with no click (relevance signal)
- 30-day retention target: 60%+

---

## Competitive Positioning

Mnemo is the only tool that is simultaneously:
- Local-first (no upload, no account)
- Passive (no import ritual — works on existing folders)
- Behaviorally adaptive (gets more accurate for your specific usage over time)
- Portable (`.db` file moves with you across machines)

**The OS threat:** Apple Intelligence and Windows Recall are building OS-level semantic search. Strategic response: serve users they structurally cannot — Linux, air-gapped environments, sensitive research data, portable behavioral memory.

**The personal moat:** Spotlight resets on reinstall. Windows Recall resets on migration. Mnemo's `.db` file carries six months of behavioral memory. OS tools optimize for the average user. Mnemo optimizes for you specifically, over time.

---

## Go-to-Market (When Ready)

### Phase 1 — Controlled Dogfooding (Now)
Use it daily. Collect real failure cases in `failures.md`. Build a genuine sense of what it's bad at before telling anyone about it.

### Phase 2 — Early Adopters
Direct outreach to researchers — Twitter/X academic community, r/PhD, r/academia. Positioning: "Local semantic search for your PDF library. No cloud. No import. Works on your existing folders."

Goal: 50–100 daily users providing qualitative feedback.

### Phase 3 — Public Launch
Product Hunt after Phase 2 retention is validated. Technical blog post on architecture (attracts developer evangelists).

### Phase 4 — Expand Vertical
Reposition for lawyers and consultants. "Recover billable hours lost to searching." Different pain, same product.

---

## Pricing (Undecided)

Don't decide until after real user conversations in Phase 2. Current hypothesis:

- **Free** for researchers (validation, word of mouth, trust-building)
- **Paid** for professionals ($40–60 one-time or $10–12/month) — people who lose money, not just time, when they can't find something

Open-source is worth considering for the trust it builds with the research audience. Decide after Phase 2.

---

## Feature Prioritization

### Must Ship (blocking v1 release)
- Reliable page jumping (viewer abstraction)
- Cleaner result card typography
- Dead code cleanup
- Crash recovery validation

### Should Have (v1.1)
- Cross-encoder reranker (once 50+ real failures justify it)
- Better snippet highlighting
- Smooth scrolling
- Query expansion / intent understanding
- Acronym handling improvement

### Post-v1
- Memory Trails (search journey reconstruction)
- DOCX support
- Cross-document evidence ("which papers mention X")
- Adaptive ranking weights
- Linux packaging

### Never (without strong evidence of mission alignment)
- LLM chat with documents
- Cloud sync
- Collaboration features
- Browser extension
- Mobile app

---

## Open Questions

1. **Open-source or closed?** Affects distribution, trust, and business model significantly. Decide before public launch.
2. **Windows-first or cross-platform?** Linux is the strategic audience. When do you serve both?
3. **PDF viewer abstraction** — which viewers to support first (SumatraPDF, browser, Acrobat)?
4. **Reranker threshold** — how many real failure cases before cross-encoder experiment is justified?
5. **System tray icon** — design and behavior on minimize.
