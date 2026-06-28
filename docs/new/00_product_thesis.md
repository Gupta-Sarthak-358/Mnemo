# Mnemo — Product Thesis

> This document sits above all others. It is not about implementation. It is about identity.
> It should almost never change. Read it before building anything new.

---

## Vision

Mnemo is a personal memory engine.

It is not a document search tool. It is not a PDF chatbot. It is not a knowledge base.

Its purpose is to reduce the cognitive effort required to remember and recover information that a person has previously encountered.

The promise:

> **Find what you remember, not what you can describe.**

---

## The Problem

Modern computers assume people remember files. Humans rarely do.

People remember fragments:

- "The networking book with the wild boar."
- "That chapter about congestion control."
- "I read something about Redis last month."
- "There was a comparison between Memcached and something else."

Traditional search requires the user to translate an imperfect memory into exact keywords. Mnemo works in the opposite direction. The user provides an incomplete memory. Mnemo reconstructs the context.

---

## Mission

Reduce cognitive load. Every feature should answer one question:

> **Does this reduce the amount the user has to remember?**

If the answer is no, it does not belong in Mnemo.

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

Recognition is easier than recall. Mnemo should maximize recognition.

---

## Product Principles

**1. Memory before search**
Search is an implementation detail. Memory recovery is the product.

**2. Context before snippets**
Users should immediately understand why something matched — what concepts it discusses, why they should open it.

**3. Recognition over precision**
Humans scan. Results should expose concepts, chapters, pages, and relationships before raw paragraphs.

**4. Retrieval before generation**
Generated text should never replace source material. Mnemo exists to help people recover knowledge, not manufacture it. Answers always point back to their origin.

**5. Local first**
User knowledge belongs to the user. Everything works without the internet. Privacy is a feature, not a marketing bullet.

**6. Explainability**
Every ranking decision should be understandable. Trust comes from transparency.

---

## Product Pillars

**Pillar 1 — Recover forgotten information**
"I know I read this."

**Pillar 2 — Reduce navigation effort**
Open the correct place immediately.

**Pillar 3 — Preserve learning context**
Remember where the user stopped. Reconnect fragmented research.

**Pillar 4 — Connect knowledge**
A concept exists beyond individual documents. The user searches for ideas. Mnemo maps those ideas back to sources.

---

## Anti-Goals

Mnemo should never become:

- A chatbot
- A generic AI assistant
- An agent platform
- A note-taking application
- "Chat with your PDFs"

These features are valuable only if they strengthen memory recovery. Otherwise they dilute the product's identity and compete in a market Mnemo cannot win.

---

## Decision Filter

Before implementing any feature, ask:

1. Does this help someone recover knowledge they already encountered?
2. Does this reduce cognitive load?
3. Would someone use this multiple times every day?

If any answer is no, the feature belongs on a backlog — not in the product.

---

## Long-Term Features That Strengthen the Mission

These are permitted because they serve the core promise:

- **Context Cards** — Explain why a document matched, not just what it contains
- **Concept Extraction** — Surface the ideas in a result so users scan meaning, not paragraphs
- **Continue Reading** — Remember where the user left off and resume naturally
- **Research Timeline** — Reconstruct how knowledge was discovered over time
- **Cross-Document Evidence** — Show how multiple documents discuss the same concept
- **Intent Expansion** — Interpret vague memories into meaningful retrieval queries

---

## Success Metric

Mnemo succeeds when users stop thinking:

> "I need to search for that file."

and instead think:

> "I'll ask Mnemo. It'll remember."

When that happens, Mnemo is no longer competing with file search. It is competing with forgetting.

---

## The Long-Term Competitor

Mnemo's long-term competitor is not Windows Search, Spotlight, or NotebookLM.

It is human memory.

Every feature should answer: *"If someone vaguely remembers learning something six months ago, can Mnemo reconstruct that memory faster than they can?"*

If the answer keeps becoming yes, Mnemo becomes one of those rare utilities that quietly lives in the background for years — like a password manager or clipboard manager. Not flashy. Just removes a small frustration dozens of times a day. The kind of software people miss the moment it's gone.
