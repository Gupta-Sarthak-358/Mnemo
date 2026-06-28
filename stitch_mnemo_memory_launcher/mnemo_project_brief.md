# Project Brief: Mnemo Memory Engine

## 1. Vision & Core Concept
Mnemo is a local-first application designed for **memory recovery**, not just file search. Unlike traditional database-driven search tools, Mnemo is built to surface the exact document and page associated with a half-remembered idea. The interface is designed to feel like a "memory resurfacing"—intuitive, fast, and calm.

**Core User Journey:**
1. User enters a fragmented query (e.g., "how b-trees balance").
2. Mnemo immediately surfaces the specific book, the relevant concepts, and the exact page.
3. User verifies the match via concept chips or a brief snippet.
4. User opens the document directly to the relevant page.

---

## 2. Design Principles
*   **Typography-First Hierarchy**: Information is communicated through size, weight, and color contrast. Icons and badges are minimized to reduce cognitive load.
*   **Calm & Focused**: Dark mode by default. No AI flourishes, gradients, or distracting animations.
*   **Native Desktop Feel**: Inspired by Raycast, Linear, and Arc. A floating, centered launcher interface (820px x 720px).
*   **Deterministic Identity**: Every document is assigned a unique, consistent color accent derived from its title, aiding in instant visual recognition.

---

## 3. Interface Specifications

### Layout Structure
- **Search Bar**: 56px tall, compact, subtle 1px focus border.
- **Results Area**: Scrollable area divided into "BEST MATCH" and "OTHER SOURCES".
- **Keyboard Bar**: Fixed bottom bar with shortcuts (NAVIGATE, OPEN, DISMISS).

### Components
#### Featured Card (Best Match)
- **Header**: Document icon with title-derived color accent, 16px title, 13px author, and a confidence label (Strong Match, Good Match, Mention).
- **Concept Chips**: Pill-shaped tags (12px) showing *why* the result matched.
- **Page Chips**: Distinctly styled clickable chips for the "Best page" and "Also on" results.
- **Context Toggle**: A "More context" button that expands a 3-4 sentence snippet with query terms in **bold**.

#### Secondary Cards
- Subordinate visual weight.
- No action buttons visible until hover/focus.
- Compact single-row layout for metadata.

---

## 4. Technical Requirements
- **Performance**: Search results must appear in <30ms to maintain the "memory" illusion.
- **Local-First**: Data remains on the user's machine.
- **Typography**: Inter (System Sans-Serif).
- **Corner Radii**: 12px for the window; 8px for cards.
- **Color Palette**: 
  - Background: `#0F0F0F`
  - Card: `#1A1A1A`
  - Border: `#2A2A2A`
  - Accent: Blue (`#5B8DEF`) or title-derived deterministic colors.

---

## 5. Success Criteria
A user should be able to identify the best match, the core concepts, and the target page within 10 seconds of searching. The interface must remain readable and "quiet" even with multiple sources found.