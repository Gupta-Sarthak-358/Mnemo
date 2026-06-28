# Mnemo — Product Thesis

> **Tagline:** Remember ideas, not filenames.
> **Status:** Permanent (updated rarely, if ever)
> **Audience:** Anyone building or deciding what Mnemo becomes

This document sits above the PRD, spec, and roadmap. It describes what Mnemo is for, what it will never become, and how to decide whether a feature belongs. It should almost never change. If a decision contradicts this document, the feature is wrong — not this document.

---

## Vision

Mnemo is a **personal memory engine**.

It is not a document search tool. It is not a PDF chatbot. It is not a knowledge base.

Its purpose is to reduce the cognitive effort required to remember and recover information a person has previously encountered.

The promise is simple:

> **Remember ideas, not filenames.**

A user who vaguely remembers learning something weeks or months ago should be able to reconstruct that memory faster through Mnemo than through their own recollection. When that becomes consistently true, Mnemo stops being a search tool and becomes infrastructure — the kind of utility people keep installed for years because removing it would cost more cognitive effort than keeping it.

---

## The Problem

Modern computers assume people remember files. Humans rarely do.

People remember fragments:

- "The networking book with the wild boar."
- "That chapter about congestion control."
- "I read something about Redis last month."
- "There was a comparison between Memcached and Redis."

Traditional search requires the user to translate an imperfect memory into exact keywords. This translation step is where retrieval fails — not because the file is missing, but because the bridge between human memory and file storage doesn't exist.

**Mnemo works in the opposite direction:** the user provides an incomplete memory. Mnemo reconstructs the context.

---

## Mission

**Reduce cognitive load.**

Every feature should answer one question: *Does this reduce the amount the user has to remember?*

If the answer is no, the feature does not belong in Mnemo.

---

## Mental Model

The workflow should evolve from:

```
Memory → Search → Manual inspection → Reading
```

to:

```
Memory → Context recovery → Recognition → Continue learning
```

**Recognition is easier than recall.** Mnemo should maximize recognition — showing users the familiar shape of what they forgot, so they recognize it rather than having to describe it precisely.

---

## Product Principles

### 1. Memory before search

Search is an implementation detail. Memory recovery is the product. Every interaction should feel less like querying a database and more like remembering.

### 2. Context before snippets

Users should immediately understand why something matched. Every result should communicate:
- Why did this match?
- What concepts does it discuss?
- Why should I open it?

A user should recognize the result as correct before clicking it — not after reading three paragraphs.

### 3. Recognition over precision

Humans scan. They rarely read search results line by line. Results should expose concepts, chapters, pages, and relationships before raw paragraphs. The visual hierarchy should prioritize what the user needs to *recognize*, not what the system needs to *return*.

### 4. Retrieval before generation

Generated text should never replace source material. Mnemo exists to help people recover knowledge they already encountered, not manufacture new text. Answers must always point back to their origin. No summaries that substitute for reading. No chat that invents citations.

### 5. Local first

User knowledge belongs to the user. Everything must continue working without the internet. Privacy is a feature, not a marketing bullet.

### 6. Explainability

Every ranking decision should be understandable. The user should know why something appeared. Trust comes from transparency — when a result surprises, the user should be able to see *why* it surfaced.

---

## Product Pillars

### Pillar 1 — Recover forgotten information

The core use case: "I know I read this. Where is it?"

### Pillar 2 — Reduce navigation effort

Open the correct place immediately — the exact page, not just the file.

### Pillar 3 — Preserve learning context

Remember where the user stopped. Remember related discoveries. Reconnect fragmented research across days, weeks, and months.

### Pillar 4 — Connect knowledge across documents

A concept should exist beyond individual documents. The user searches for ideas. Mnemo maps those ideas back to sources, showing how different documents discuss the same concept from different angles.

---

## Future Experience

A search result should feel like a memory resurfacing.

Instead of:

```
Database System Concepts
Page 303
Snippet: "..."
```

The result should communicate:

```
Database System Concepts

Why this matched
• SQL Injection
• Prepared Statements
• Parameterized Queries

Chapter: Database Security
Relevant pages: 303, 846, 1280
Confidence: Very High

Related concepts
XSS · Stored Procedures · Escaping
```

The user recognizes the result before opening it. That recognition is the product.

---

## Anti-Goals

Mnemo must not become:

- **A chatbot.** Users search. They don't converse with their files.
- **A generic AI assistant.** Mnemo only knows what you've read. It should never pretend to know more.
- **An agent platform.** No executing actions, no writing emails, no booking meetings.
- **A note-taking application.** Mnemo reads files. It doesn't create them.
- **Another "chat with your PDFs" tool.** Hundreds exist. Users try them once and forget they're installed.

These features are valuable only if they strengthen memory recovery. Otherwise they distract from the product's identity.

---

## Decision Filter

Before implementing any feature, ask:

1. **Does this help someone recover knowledge they already encountered?**
2. **Does this reduce cognitive load?**
3. **Would someone use this several times every day?**

If any answer is no, the feature belongs on the backlog, not in the product.

The hardest decisions aren't about what to build — they're about what to refuse. This filter exists to make those refusals easier.

---

## Success Metric

Mnemo succeeds when users stop thinking:

> "I need to search for that file."

and instead think:

> "I'll ask Mnemo. It'll remember."

When that happens, Mnemo is no longer competing with file search. It is competing with forgetting.
