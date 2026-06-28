# Mnemo

**Your files remember what you meant.**

Mnemo is a local-first semantic file search engine for PDFs and text files. It indexes your documents at the paragraph level, embeds them with sentence-transformers, and lets you search by meaning — not just keywords. Everything runs locally. No cloud, no telemetry, no data leaves your machine.

## How it works

```
PDF/TXT → paragraph chunking → sentence-transformers embeddings → sqlite-vec storage
                                                                    ↓
User query → hybrid search (semantic 0.70 + FTS5 0.30) → heading/filename boost → top 8 results
                                                                    ↓
                                                         PyQt6 desktop launcher (Ctrl+M)
```

### Pipeline

| Step | Tool | Description |
|------|------|-------------|
| Parsing | PyMuPDF | Extract text from PDFs, plain text from TXT |
| Chunking | `chunker.py` | Paragraph-level chunks with neighbor context; merges tiny paragraphs (<60 words) |
| Embedding | `sentence-transformers` | `all-MiniLM-L6-v2` model; batch encoding |
| Storage | `sqlite-vec` | Vector similarity search in SQLite |
| Full-text | FTS5 | `porter unicode61` tokenizer for keyword fallback |
| Hybrid ranking | `search.py` | 0.70 semantic + 0.30 FTS5 → heading boost (0.15) → filename boost (0.10) → index-page penalty (0.8×) |
| OCR | Tesseract | Quality-based page assessment; lazy background OCR (5 pages/60s); header/footer stripper |
| Dedup | SHA256 | File-level deduplication |
| Metadata | `enrich.py` | Heading extraction + concept extraction (TF-IDF-style) per chunk |

### UI Features

- **Ctrl+M** global hotkey to toggle search window
- **FeaturedCard** — Best match with book icon (deterministic color from filename hash), author, confidence label, concept chips, page chips, inline snippet toggle
- **SecondaryCard** — Compact view for remaining results with left accent border
- **↑↓ keyboard navigation** with visual selection highlight
- **Theme detection** — Auto-detects Windows dark/light mode
- **Recent searches** — Saved to `~/.mnemo/recent_searches.json`
- **Continue Reading** — Quick-resume last opened document
- **Settings dialog** — Change hotkey, pick preferred PDF viewer
- **PDF Viewer abstraction** — Auto-detects SumatraPDF, Chrome, Brave, Edge, or system default
- **SVG icons** — Material Design icons rendered with `QSvgRenderer`

## Quick Start

### Prerequisites

- Python 3.10+
- Tesseract OCR (optional, for scanned PDFs): [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

### Setup

```bash
git clone https://github.com/Gupta-Sarthak-358/Mnemo.git
cd Mnemo
python -m venv .venv
.venv\Scripts\pip install -e .
```

### Run

```bash
.venv\Scripts\python -m mnemo.daemon
```

Or double-click `start_mnemo.bat` (Desktop shortcut).

On first run, it will ask for folders to watch. You can also add folders later via the API.

### Usage

1. Press **Ctrl+M** to open the search window
2. Type a query (minimum 3 characters)
3. Results appear in real-time with concept chips explaining why each matched
4. **↑↓** to navigate, **Enter** to open, **Esc** to dismiss
5. Click "More context" to expand inline snippets

## API Endpoints

The daemon runs on `http://127.0.0.1:8765`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/search?q=...&limit=8` | Search query |
| `GET` | `/status` | Daemon and index status |
| `GET` | `/files` | List indexed files |
| `POST` | `/index?path=...` | Add a folder to watch |
| `DELETE` | `/files?path=...` | Remove a file |
| `POST` | `/log-open` | Log file open event |

## Benchmarks

**v3 — 190 queries, 12 categories — 82% Top-3 on 170 non-negative queries**

```bash
python benchmark.py --queries benchmarks/queries_v3.json
```

[Full results](benchmarks/2026-06-25.md)

## Project Structure

```
src/mnemo/
├── daemon.py       # Entry point — starts API, UI, OCR worker, file watcher
├── api.py          # FastAPI endpoints
├── db.py           # SQLite schema (10 migrations), vector/FTS5 search
├── parser.py       # PDF/TXT parsing, page quality, OCR check
├── chunker.py      # Paragraph-level chunking with context
├── embedder.py     # sentence-transformers model loading
├── indexer.py      # Index pipeline — dedup, chunk, embed, OCR queue
├── search.py       # Hybrid search (semantic + FTS5)
├── enrich.py       # Heading + concept extraction
├── ui.py           # PyQt6 desktop launcher
├── icons.py        # Material Design SVG icons
├── config.py       # Config management (~/.mnemo/config.json)
├── watcher.py      # File system watcher
└── debug.py        # CLI debug commands

docs/
├── new/            # Product docs: thesis, discussion, spec, PRD, roadmap
├── development/    # Engineering state, ADR log, search failure log
└── (legacy)        # Superseded product docs

stitch_mnemo_memory_launcher/
├── DESIGN.md       # Design system reference (colors, typography, spacing)
├── screen.png      # Desktop launcher mockup
└── code.html       # HTML/CSS reference implementation
```

## Configuration

File: `~/.mnemo/config.json`

```json
{
  "watched_folders": ["C:\\Users\\You\\Documents"],
  "hotkey": "ctrl+alt+m",
  "embedding_model": "all-MiniLM-L6-v2",
  "max_results": 8,
  "theme": "auto",
  "preferred_viewer": "auto"
}
```

Change the hotkey or viewer in the Settings dialog (gear icon in the search bar).

## Development

### Project Philosophy

1. **No cloud** — everything runs locally. No accounts, no sync, no telemetry.
2. **Pipeline freeze** — no chunking/embedding/ranking changes until 30–50 real-world failures accumulate.
3. **Dogfood-driven** — daily use logs failures to `docs/development/search_failures.md`. Only bug fixes, retrieval improvements with benchmark gains, and UX polish are permitted.

### Key Decisions

- Hybrid search (0.70 semantic + 0.30 FTS5) over pure semantic — better for exact terms and rare queries
- Concept chips over raw snippets as primary information — users identify relevance faster
- Sentence-scored snippet extraction — exact phrase +5, term match +3, consecutive terms +2, heading-like +1
- Page numbers stored 0-indexed in DB, +1 for viewer display
- Qt in daemon thread (stable for v1; migrate to main thread before tray integration)

### Product Roadmap

See [docs/new/04_roadmap.md](docs/new/04_roadmap.md) for the 4-stage evolution plan.

## Tech Stack

- **Backend**: Python, FastAPI, Uvicorn
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`)
- **Vector DB**: sqlite-vec
- **Full-text**: SQLite FTS5 (porter unicode61)
- **PDF**: PyMuPDF (fitz), pdf2image + pytesseract
- **UI**: PyQt6
- **Hotkey**: pynput
- **File watching**: watchdog

## License

Private — all rights reserved.
