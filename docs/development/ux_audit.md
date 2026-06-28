# UX Audit — June 28, 2026

> The backend understands your memory. The frontend says "here's a QWidget with some labels."

## Scores vs Stitch design system

| Aspect              | Current | Stitch |
| ------------------- | ------- | ------ |
| Visual hierarchy    | 5/10    | 9/10   |
| Information density | 6/10    | 9/10   |
| Scannability        | 5/10    | 9/10   |
| Product identity    | 6/10    | 9.5/10 |
| Desktop feel        | 7/10    | 9.5/10 |
| Recognition-first   | 5/10    | 10/10  |

## Problems

### 1. Massive empty space (P0)
~50% of window is empty for single results. Everything feels disconnected.

### 2. Result card isn't a card (P0)
Floating content with no visual container. Stitch puts each result inside a surface.

### 3. BEST MATCH too far from search bar (P1)
~150px gap. Should be ~20px.

### 4. Result starts too low (P1)
Book icon starts halfway down. Results should be near the top (Raycast/Alfred pattern).

### 5. Search bar branding (P2)
Placeholder "Search your library..." is generic. Better: "Search what you remember..." or "Remember something..."

### 6. Card spacing inconsistency (P1)
Some sections compressed, others have giant gaps. Should follow 8px grid.

### 7. "Why this matched" shows metadata, not concepts (P0)
Shows "Book", "Any", "Edition", "Chapter" — metadata, not actual concepts. Should show "SQL", "Normalization", "BCNF", "Dependencies".

### 8. Confidence label should be a badge (P2)
"Mention" floats detached. Should be pills: 🟢 Strong, 🟡 Good, ⚪ Mention.

### 9. Buttons look like Windows Forms (P2)
"Open" and "More Context" look like standard desktop buttons. Need modern styling.

### 10. Footer too dominant (P2)
Shortcut hints are a great idea but visually dominate. Should fade into background.

## Continue Reading screen

Current is sparse: book name + author + page number.

Desired: richer cards with cover, last-read section, next relevant section, contextual resume button.

## Recent Searches

Should be visually richer — icons, chips, not plain text.

## Typography

Four distinct sizes needed:
- Search: 22px
- Title: 18px
- Section: 12px
- Metadata: 11px

Currently everything feels like 14px.

## Chips

Visually nice but semantically weak. Replace metadata with actual extracted concepts.

## Product identity

Mnemo is a **memory engine**, not a launcher (Raycast) or a file searcher.

- Raycast: execution-first (launch app, run command, done)
- Mnemo: recognition-first (vague memory → recognition → confidence → recovery)

The UI should allocate more space to **explaining why something matched**.

## Priorities

### P0 — Next session
1. Fix whitespace — compress vertically, move results up
2. Introduce actual card containers
3. Make concepts meaningful (not metadata)

### P1 — Soon
4. Document identity (covers, authors, colors)
5. Make "Continue Reading" feel alive (context about where they stopped, why)

### P2 — Polish
6. Confidence badges (pills with color)
7. Search bar branding (placeholder text, lighter border)
8. Modernize buttons
9. Footer less dominant
10. Typography hierarchy
11. Recent searches visual

## Stitch disagreements

- Open button: remove, Enter should open
- Book icon too generic (use generated covers or color identity eventually)
- Continue Reading too small (it's a differentiator)
- Expanded snippet still too paragraph-heavy
