import ctypes
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import threading
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QScrollArea,
    QDialog, QPushButton, QCheckBox, QComboBox, QFileDialog, QSizePolicy,
    QSystemTrayIcon, QMenu, QProgressBar,
    QGraphicsDropShadowEffect,
)
from .icons import icon_label, icon_pixmap

logger = logging.getLogger(__name__)

API_BASE = "http://127.0.0.1:8765"


def _icon_path():
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
        for p in [base / "_internal" / "mnemo.ico", base / "mnemo.ico"]:
            if p.is_file():
                return str(p)
    return "mnemo.ico"


def api_search(query):
    try:
        from .config import load_config
        limit = load_config().get("max_results", 8)
        url = f"{API_BASE}/search?q={urllib.parse.quote(query)}&limit={limit}"
        with urllib.request.urlopen(url, timeout=3) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.error("Search API error: %s", e)
        return None


def api_log_open(query, file_path, file_id, page_num=None):
    try:
        data = json.dumps({
            "query": query,
            "file_path": file_path,
            "file_id": file_id,
            "page_num": page_num,
        }).encode()
        req = urllib.request.Request(
            f"{API_BASE}/log-open",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception as e:
        logger.error("Log open API error: %s", e)


_SUMATRA_CANDIDATES = [
    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "SumatraPDF", "SumatraPDF.exe"),
    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "SumatraPDF", "SumatraPDF.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\Default\\AppData\\Local"), "SumatraPDF", "SumatraPDF.exe"),
]
class PDFViewer:
    name = "auto"
    display = "Automatic"
    icon = "🖥"

    @staticmethod
    def available():
        return True

    @staticmethod
    def open(path, page=None):
        open_pdf(path, page)


class SumatraPDFViewer(PDFViewer):
    name = "sumatra"
    display = "SumatraPDF"
    icon = "📄"

    @staticmethod
    def available():
        return any(os.path.isfile(p) for p in _SUMATRA_CANDIDATES)

    @staticmethod
    def open(path, page=None):
        exe = _find_exe(_SUMATRA_CANDIDATES)
        if not exe:
            return default_fallback_open(path, page)
        viewer_page = page + 1 if page is not None else None
        args = [exe]
        if viewer_page is not None:
            args.extend(["-page", str(viewer_page)])
        args.append(path)
        subprocess.Popen(args)


class ChromeViewer(PDFViewer):
    name = "chrome"
    display = "Chrome"
    icon = "🌐"

    @staticmethod
    def available():
        return _find_exe(_CHROME_CANDIDATES) is not None

    @staticmethod
    def open(path, page=None):
        _open_browser(path, page, _CHROME_CANDIDATES)


class BraveViewer(PDFViewer):
    name = "brave"
    display = "Brave"
    icon = "🌐"

    @staticmethod
    def available():
        return _find_exe(_BRAVE_CANDIDATES) is not None

    @staticmethod
    def open(path, page=None):
        _open_browser(path, page, _BRAVE_CANDIDATES)


class EdgeViewer(PDFViewer):
    name = "edge"
    display = "Edge"
    icon = "🌐"

    @staticmethod
    def available():
        return _find_exe(_EDGE_CANDIDATES) is not None

    @staticmethod
    def open(path, page=None):
        _open_browser(path, page, _EDGE_CANDIDATES)


class SystemViewer(PDFViewer):
    name = "system"
    display = "System Default"
    icon = "⚙"

    @staticmethod
    def open(path, page=None):
        default_fallback_open(path, page)


_VIEWER_REGISTRY = [
    SumatraPDFViewer,
    ChromeViewer,
    BraveViewer,
    EdgeViewer,
    SystemViewer,
]


def _find_exe(candidates):
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _open_browser(path, page, candidates=None):
    viewer_page = page + 1 if page is not None else None
    if viewer_page is None:
        default_fallback_open(path)
        return
    encoded = urllib.parse.quote(os.path.abspath(path).replace(os.sep, '/'), safe='/:@')
    ts = int(time.monotonic() * 1000000)
    uri = f"file:///{encoded}?t={ts}#page={viewer_page}"
    exe = _find_exe(candidates) if candidates else _find_exe(_CHROME_CANDIDATES + _BRAVE_CANDIDATES + _EDGE_CANDIDATES)
    if exe:
        subprocess.Popen([exe, uri])
    else:
        subprocess.Popen(["cmd", "/c", "start", "", uri], shell=False)


def default_fallback_open(path, page=None):
    viewer_page = page + 1 if page is not None else None
    if sys.platform == "win32":
        if viewer_page is not None:
            encoded = urllib.parse.quote(os.path.abspath(path).replace(os.sep, '/'), safe='/:@')
            ts = int(time.monotonic() * 1000000)
            uri = f"file:///{encoded}?t={ts}#page={viewer_page}"
            subprocess.Popen(["cmd", "/c", "start", "", uri], shell=False)
        else:
            subprocess.Popen(["start", "", path], shell=True)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def resolve_viewer(preferred="auto"):
    if preferred and preferred != "auto":
        for v in _VIEWER_REGISTRY:
            if v.name == preferred and v.available():
                return v
    for v in _VIEWER_REGISTRY[:-1]:
        if v.available():
            return v
    return SystemViewer


def open_pdf(path, page=None):
    try:
        from .config import load_config
        cfg = load_config()
        viewer = resolve_viewer(cfg.get("preferred_viewer", "auto"))
        viewer.open(path, page)
    except Exception as e:
        logger.error("Failed to open file: %s", e)


def clean_snippet(text, max_chars=200):
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."
    return text


def detect_windows_theme():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "dark" if value == 0 else "light"
    except Exception:
        return "light"


LIGHT_COLORS = {
    "bg": "#f5f0e8", "fg": "#1a1a1a", "card_bg": "#faf7f0",
    "border": "#e8e0d0", "input_bg": "#faf7f0", "input_border": "#e0d8c8",
    "hover": "#ede6d8", "selected": "#d4c9b8", "secondary": "#666666",
    "muted": "#999999", "page": "#888888", "score": "#aaaaaa",
    "highlight_bg": "#fff3cd", "highlight_fg": "#856404",
    "accent": "#5B8DEF", "concept_bg": "#e8e4dc", "page_bg": "#dae4f0",
    "card_sep": "#2A2A2A", "card_hover": "#3A3A3A",
}

DARK_COLORS = {
    "bg": "#0F0F0F", "fg": "#E8E8E8", "card_bg": "#1E1E1E",
    "border": "#2A2A2A", "input_bg": "transparent", "input_border": "#2A2A2A",
    "hover": "#252525", "selected": "#333535", "secondary": "#C3C6D4",
    "muted": "#888888", "page": "#AAAAAA", "score": "#AAAAAA",
    "highlight_bg": "transparent", "highlight_fg": "#E8E8E8",
    "accent": "#5B8DEF", "concept_bg": "#252525", "page_bg": "#1E2D3D",
    "card_sep": "#2A2A2A", "card_hover": "#3A3A3A", "surface_lowest": "#0c0f0f",
}


STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","by","with",
    "is","are","was","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","shall","can","need",
    "this","that","these","those","i","me","my","we","our","you","your","it",
    "its","they","them","their","what","which","who","whom","not","no","nor",
    "none","so","just","too","very","all","each","every","both","few","more",
    "most","some","such","only","own","same","here","there","when","where",
    "why","how","about","into","over","after","before","between","under",
    "above","below","up","down","out","off","than","then","also","if","as",
}


def extract_best_sentences(text, query, max_sentences=2):
    if not text:
        return text
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return clean_snippet(text, 300)

    terms = [t for t in re.split(r"\W+", query.lower().strip()) if len(t) > 1 and t not in STOPWORDS]
    if not terms:
        return " ".join(sentences[:max_sentences])

    query_lower = query.lower().strip()

    scored = []
    for i, s in enumerate(sentences):
        sl = s.lower()
        score = 0
        if query_lower in sl:
            score += 5
        for t in terms:
            if t in sl:
                score += 3
        for j in range(len(terms) - 1):
            if terms[j] in sl and terms[j + 1] in sl:
                score += 2
        if len(s) < 120 and s[0].isupper() and not s.rstrip().endswith("."):
            score += 1
        if score > 0:
            scored.append((score, i, s))

    if not scored:
        return " ".join(sentences[:max_sentences])

    scored.sort(key=lambda x: (-x[0], x[1]))
    best_idx = scored[0][1]

    start = max(0, best_idx - 1)
    end = min(len(sentences), best_idx + max_sentences)
    return " ".join(sentences[start:end])


def score_label(score):
    if score >= 0.70:
        return "Excellent", "#2e7d32"
    elif score >= 0.50:
        return "Strong", "#1565c0"
    elif score >= 0.30:
        return "Good", "#e65100"
    else:
        return "Fair", "#666666"


def get_matched_concepts(text, query):
    if not query or not text:
        return []
    terms = [t for t in re.split(r"\W+", query.lower().strip()) if len(t) > 1 and t not in STOPWORDS]
    if not terms:
        return []
    text_lower = text.lower()
    return [t for t in terms if t in text_lower]


def record_last_open(file_path, filename, page_num, author=""):
    try:
        entries = _load_last_open_list()
        entries = [e for e in entries if e.get("filename") != filename]
        entries.append({"path": file_path, "filename": filename, "page": page_num, "author": author, "timestamp": time.time()})
        path = os.path.join(os.path.expanduser("~/.mnemo"), "last_open.json")
        with open(path, "w") as f:
            json.dump(entries[-5:], f)
    except Exception:
        pass


def load_last_open():
    return _load_last_open_list()


def _load_last_open_list():
    try:
        path = os.path.join(os.path.expanduser("~/.mnemo"), "last_open.json")
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return [data]
        return data
    except Exception:
        return []


def save_recent_searches(searches):
    try:
        seen = set()
        deduped = []
        for s in searches:
            q = s["query"] if isinstance(s, dict) else s
            if q not in seen:
                seen.add(q)
                entry = {"query": q, "page": s.get("page") if isinstance(s, dict) else None}
                deduped.append(entry)
        trimmed = deduped[-20:]
        path = os.path.join(os.path.expanduser("~/.mnemo"), "recent_searches.json")
        with open(path, "w") as f:
            json.dump(trimmed, f)
    except Exception:
        pass


def load_recent_searches():
    try:
        path = os.path.join(os.path.expanduser("~/.mnemo"), "recent_searches.json")
        with open(path) as f:
            data = json.load(f)
        if data and isinstance(data[0], str):
            return [{"query": s, "page": None} for s in data]
        return data
    except Exception:
        return []

def add_recent_search(query, page=None):
    searches = load_recent_searches()
    searches.append({"query": query, "page": page})
    save_recent_searches(searches)


def highlight_terms(text, query, highlight_bg, highlight_fg):
    if not query or not text:
        return text
    terms = [t for t in re.split(r"\W+", query.lower().strip()) if len(t) > 1 and t not in STOPWORDS]
    if not terms:
        return text
    pattern = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
    def replacer(m):
        return f'<span style="background:{highlight_bg};color:{highlight_fg};font-weight:600">{m.group()}</span>'
    return re.sub(pattern, replacer, text, flags=re.IGNORECASE)


_EDGE_CANDIDATES = [
    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Microsoft", "Edge", "Application", "msedge.exe"),
    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Microsoft", "Edge", "Application", "msedge.exe"),
]

_CHROME_CANDIDATES = [
    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\Default\\AppData\\Local"), "Google", "Chrome", "Application", "chrome.exe"),
]

_BRAVE_CANDIDATES = [
    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\Default\\AppData\\Local"), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
]


def clean_filename(filename):
    name = filename
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    elif name.lower().endswith(".txt"):
        name = name[:-5]
    name = name.replace("_", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name


def save_window_geometry(geometry):
    try:
        path = os.path.join(os.path.expanduser("~/.mnemo"), "window_geometry.json")
        with open(path, "w") as f:
            json.dump({"geometry": list(geometry)}, f)
    except Exception:
        pass


def book_color(filename):
    colors = ['#5B8DEF', '#4FD1C5', '#818CF8', '#F6AD55', '#FC8181', '#68D391', '#FBBF24', '#A78BFA']
    idx = int(hashlib.md5(filename.encode()).hexdigest(), 16) % len(colors)
    return colors[idx]


def load_window_geometry():
    try:
        path = os.path.join(os.path.expanduser("~/.mnemo"), "window_geometry.json")
        with open(path) as f:
            data = json.load(f)
            return bytes(data["geometry"])
    except Exception:
        return None


def make_chip(text, bg, fg, font_size=11):
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", font_size, QFont.Weight.Medium))
    lbl.setStyleSheet(f"background: {bg}; color: {fg}; padding: 4px 12px; border-radius: 6px;")
    return lbl


class _FirstRunDialog(QDialog):
    def __init__(self, colors):
        super().__init__()
        self._C = colors
        self._folders = []
        self.setWindowTitle("Welcome to Mnemo")
        self.setFixedSize(560, 420)
        self.setStyleSheet(f"background: {colors['bg']}; color: {colors['fg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("Welcome to Mnemo")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {colors['accent']}; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel("Your files remember what you meant.\nChoose folders to index.")
        subtitle.setFont(QFont("Segoe UI", 12))
        subtitle.setStyleSheet(f"color: {colors['secondary']}; background: transparent;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self._list = QVBoxLayout()
        self._list.setSpacing(4)
        layout.addLayout(self._list)

        add_btn = QPushButton("+ Add Folder")
        add_btn.setFont(QFont("Segoe UI", 11))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {colors['accent']}; color: white; border: none; padding: 8px 20px; border-radius: 6px;
            }}
            QPushButton:hover {{ background: {colors['card_hover']}; }}
        """)
        add_btn.clicked.connect(self._add_folder)
        layout.addWidget(add_btn)

        layout.addStretch()

        self._next_btn = QPushButton("Index Folders")
        self._next_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.setStyleSheet(f"""
            QPushButton {{
                background: {colors['accent']}; color: white; border: none; padding: 10px; border-radius: 6px;
            }}
            QPushButton:hover {{ background: {colors['card_hover']}; }}
            QPushButton:disabled {{ background: {colors['border']}; color: {colors['muted']}; }}
        """)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._start_indexing)
        layout.addWidget(self._next_btn)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select a folder to index")
        if folder:
            self._folders.append(folder)
            C = self._C
            label = QLabel(f"  {folder}")
            label.setFont(QFont("Segoe UI", 10))
            label.setStyleSheet(f"color: {C['fg']}; background: {C['card_bg']}; padding: 6px 10px; border-radius: 4px;")
            self._list.addWidget(label)
            self._next_btn.setEnabled(True)

    def _start_indexing(self):
        C = self._C
        self._next_btn.setEnabled(False)
        self._next_btn.setText("Indexing...")
        parent_layout = self.layout()
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background: {C['card_bg']}; border: none; border-radius: 4px; height: 6px;
            }}
            QProgressBar::chunk {{
                background: {C['accent']}; border-radius: 4px;
            }}
        """)
        parent_layout.insertWidget(parent_layout.count() - 1, self._progress)

        self._status = QLabel("Starting index...")
        self._status.setFont(QFont("Segoe UI", 10))
        self._status.setStyleSheet(f"color: {C['muted']}; background: transparent;")
        parent_layout.insertWidget(parent_layout.count() - 1, self._status)

        # Kick off indexing in background threads
        import urllib.request as _ur
        import urllib.parse as _up
        for folder in self._folders:
            t = threading.Thread(target=_ur.urlopen, args=(
                _ur.Request(
                    f"http://127.0.0.1:8765/index?path={_up.quote(folder)}",
                    method="POST",
                ),
            ), kwargs={"timeout": 600}, daemon=True)
            t.start()

        self._timer = QTimer()
        self._timer.timeout.connect(self._poll_status)
        self._timer.start(500)

    def _poll_status(self):
        import urllib.request, json
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:8765/status", timeout=2)
            data = json.loads(resp.read())
            indexed = data.get("files_indexed", 0)
            total = data.get("files_total", 0)
            status = data.get("status", "")
            if total > 0:
                self._progress.setRange(0, total)
                self._progress.setValue(indexed)
                self._status.setText(f"Indexed {indexed} of {total} files...")
            if status == "running" and total > 0 and indexed >= total:
                self._timer.stop()
                self._progress.setRange(0, 1)
                self._progress.setValue(1)
                self._status.setText(f"Ready. {indexed} files indexed.")
                self._next_btn.setText("Finish")
                self._next_btn.setEnabled(True)
                self._next_btn.clicked.disconnect()
                self._next_btn.clicked.connect(self.accept)
        except Exception:
            pass

    def selected_folders(self):
        return list(self._folders)


def run_ui():

    theme_mode = detect_windows_theme()
    C = DARK_COLORS if theme_mode == "dark" else LIGHT_COLORS
    logger.info("Theme: %s", theme_mode)

    def confidence_label(score):
        if score >= 0.70:
            return "Strong Match"
        elif score >= 0.50:
            return "Good Match"
        else:
            return "Mention"

    class FeaturedCard(QWidget):
        def __init__(self, result_data, query="", pages=None, parent=None):
            super().__init__(parent)
            self._data = result_data
            self._query = query
            self._pages = pages or []
            self._expanded = False
            self._snippet_widget = None
            self._selected = False
            self._build()

        def _build(self):
            self.setObjectName("featuredCard")
            self.setAttribute(Qt.WidgetAttribute.WA_Hover)
            self.setStyleSheet(f"""
                #featuredCard {{
                    background: {C['card_bg']}; border: 1px solid {C['border']}; border-radius: 8px;
                }}
                #featuredCard:hover {{
                    border-color: {C['card_hover']};
                }}
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(12)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 50))
            self.setGraphicsEffect(shadow)
            outer = QVBoxLayout(self)
            outer.setContentsMargins(12, 12, 12, 12)
            outer.setSpacing(12)

            color = book_color(self._data["filename"])

            # Header: icon | title + author | confidence badge
            header = QHBoxLayout()
            header.setSpacing(12)

            icon_w = QWidget()
            icon_w.setFixedSize(36, 44)
            icon_w.setStyleSheet(f"background: {C['card_bg']}; border-left: 3px solid {color}; border-radius: 4px;")
            icon_lbl = icon_label("book", 20, color)
            icon_l = QVBoxLayout(icon_w)
            icon_l.setContentsMargins(0, 0, 0, 0)
            icon_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_l.addWidget(icon_lbl)
            header.addWidget(icon_w)

            title_col = QVBoxLayout()
            title_col.setSpacing(2)
            name = QLabel(clean_filename(self._data["filename"]))
            name.setFont(QFont("Segoe UI", 15, QFont.Weight.Medium))
            name.setStyleSheet(f"color: {C['fg']}; background: transparent;")
            name.setWordWrap(False)
            title_col.addWidget(name)
            author = self._data.get("author")
            if author:
                a = QLabel(author[:60])
                a.setFont(QFont("Segoe UI", 12))
                a.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
                title_col.addWidget(a)
            heading = self._data.get("heading")
            if heading and heading != author:
                h = QLabel(heading[:80])
                h.setFont(QFont("Segoe UI", 12))
                h.setStyleSheet(f"color: {C['page']}; background: transparent;")
                title_col.addWidget(h)
            elif not author and heading:
                a = QLabel(heading[:60])
                a.setFont(QFont("Segoe UI", 12))
                a.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
                title_col.addWidget(a)
            header.addLayout(title_col, 1)

            conf = make_chip(confidence_label(self._data.get("score", 0)), C["concept_bg"], C["muted"], 12)
            header.addWidget(conf)
            outer.addLayout(header)

            # Snippet preview — 3 lines by default
            snippet = self._data.get("snippet", "")
            self._snippet_preview = None
            if snippet:
                preview_text = extract_best_sentences(snippet, self._query, 3)
                if preview_text:
                    self._snippet_preview = QLabel(preview_text)
                    self._snippet_preview.setFont(QFont("Segoe UI", 12))
                    self._snippet_preview.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
                    self._snippet_preview.setWordWrap(True)
                    outer.addWidget(self._snippet_preview)

            # Concept chips
            concepts = self._data.get("concepts", [])
            if concepts:
                seen = set()
                unique = []
                for c in concepts:
                    key = c.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        unique.append(c)
                chip_row = QHBoxLayout()
                chip_row.setSpacing(6)
                chip_row.setContentsMargins(0, 0, 0, 0)
                for c in unique[:5]:
                    chip_row.addWidget(make_chip(c.title(), C["concept_bg"], C["page"], 11))
                chip_row.addStretch()
                outer.addLayout(chip_row)

            # Pages + More context link
            bottom = QHBoxLayout()
            bottom.setSpacing(8)

            best_page = self._data.get("page_num")
            raw = best_page if best_page is not None else None
            main_chip = QWidget()
            main_chip.setStyleSheet(f"background: {C['page_bg']}; border-radius: 6px;")
            mc = QHBoxLayout(main_chip)
            mc.setContentsMargins(8, 2, 8, 2)
            mc.setSpacing(3)
            p_lbl = QLabel("p.")
            p_lbl.setFont(QFont("Segoe UI", 10))
            p_lbl.setStyleSheet(f"color: {C['accent']}; background: transparent;")
            mc.addWidget(p_lbl)
            p_num = QLabel(str(raw + 1 if raw is not None else "?"))
            p_num.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
            p_num.setStyleSheet(f"color: {C['accent']}; background: transparent;")
            mc.addWidget(p_num)
            main_chip.mousePressEvent = lambda e: self._open_page(self._data)
            main_chip.setCursor(Qt.CursorShape.PointingHandCursor)
            bottom.addWidget(main_chip)

            if len(self._pages) > 1:
                also = QLabel("Also on:")
                also.setFont(QFont("Segoe UI", 11))
                also.setStyleSheet(f"color: {C['muted']}; background: transparent;")
                bottom.addWidget(also)
                for p in self._pages[1:4]:
                    raw_pn = p.get("page_num")
                    disp = raw_pn + 1 if raw_pn is not None else "?"
                    chip = QLabel(str(disp))
                    chip.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
                    chip.setStyleSheet(f"background: {C['concept_bg']}; color: {C['page']}; padding: 2px 6px; border-radius: 6px;")
                    chip.setFixedHeight(22)
                    chip.setCursor(Qt.CursorShape.PointingHandCursor)
                    chip.mousePressEvent = lambda e, pd=p: self._open_page(pd)
                    bottom.addWidget(chip)

            bottom.addStretch()

            self._more_btn = QPushButton("More context →")
            self._more_btn.setFont(QFont("Segoe UI", 11))
            self._more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._more_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {C['accent']}; border: none; padding: 2px 8px; border-radius: 4px; }}
                QPushButton:hover {{ background: {C['hover']}; color: {C['accent']}; }}
            """)
            self._more_btn.clicked.connect(self._toggle_snippet)
            bottom.addWidget(self._more_btn)

            outer.addLayout(bottom)

            # Snippet (hidden)
            self._snippet_container = QWidget()
            self._snippet_container.setVisible(False)
            self._snippet_container.setStyleSheet(f"border-top: 1px solid {C['border']};")
            sc = QVBoxLayout(self._snippet_container)
            sc.setContentsMargins(0, 12, 0, 0)
            self._snippet_label = QLabel("")
            self._snippet_label.setFont(QFont("Segoe UI", 12))
            self._snippet_label.setStyleSheet(f"color: {C['secondary']}; background: transparent; border: none;")
            self._snippet_label.setWordWrap(True)
            self._snippet_label.setTextFormat(Qt.TextFormat.RichText)
            sc.addWidget(self._snippet_label)
            outer.addWidget(self._snippet_container)

            self.setCursor(Qt.CursorShape.PointingHandCursor)

        def set_selected(self, selected):
            self._selected = selected
            self.update()

        def paintEvent(self, event):
            super().paintEvent(event)
            if self._selected:
                p = QPainter(self)
                p.setPen(QPen(QColor(C['accent']), 2))
                p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
                p.end()

        def mousePressEvent(self, event):
            self._open_page(self._data)

        def _toggle_snippet(self):
            self._expanded = not self._expanded
            full_text = self._data.get("snippet", "")
            if self._expanded:
                display = clean_snippet(full_text, 800)
                self._more_btn.setText("Less context ←")
                if self._snippet_preview:
                    self._snippet_preview.setVisible(False)
            else:
                display = extract_best_sentences(full_text, self._query, 3)
                self._more_btn.setText("More context →")
                if self._snippet_preview:
                    self._snippet_preview.setVisible(True)
            self._snippet_label.setText(highlight_terms(display, self._query, C["highlight_bg"], C["highlight_fg"]))
            self._snippet_container.setVisible(self._expanded)

        def _open_page(self, data):
            q = self._query
            pn = data.get("page_num")
            api_log_open(q, data["path"], data["file_id"], pn)
            record_last_open(data["path"], data["filename"], pn, data.get("author", ""))
            add_recent_search(q, pn)
            open_pdf(data["path"], pn)
            w = self.window()
            if w:
                w.hide()

    class SecondaryCard(QWidget):
        def __init__(self, result_data, query="", parent=None):
            super().__init__(parent)
            self._data = result_data
            self._query = query
            self._selected = False
            self._build()

        def _build(self):
            clr = book_color(self._data["filename"])
            self.setObjectName("secondaryCard")
            self.setAttribute(Qt.WidgetAttribute.WA_Hover)
            self.setStyleSheet(f"""
                #secondaryCard {{
                    background: {C['card_bg']}; border: 1px solid {C['border']}; border-left: 4px solid {clr}; border-radius: 8px;
                }}
                #secondaryCard:hover {{
                    border-color: {C['card_hover']};
                    border-left-color: {clr};
                }}
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(8)
            shadow.setOffset(0, 1)
            shadow.setColor(QColor(0, 0, 0, 40))
            self.setGraphicsEffect(shadow)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            outer = QVBoxLayout(self)
            outer.setContentsMargins(12, 8, 12, 8)
            outer.setSpacing(4)

            top = QHBoxLayout()
            top.setSpacing(10)
            top.addWidget(icon_label("book", 18, clr))
            title_col = QVBoxLayout()
            title_col.setSpacing(1)
            name = QLabel(clean_filename(self._data["filename"]))
            name.setFont(QFont("Segoe UI", 12))
            name.setStyleSheet(f"color: {C['fg']}; background: transparent;")
            title_col.addWidget(name)
            heading = self._data.get("heading")
            if heading:
                h = QLabel(heading[:60])
                h.setFont(QFont("Segoe UI", 10))
                h.setStyleSheet(f"color: {C['page']}; background: transparent;")
                title_col.addWidget(h)
            top.addLayout(title_col, 1)
            conf = make_chip(confidence_label(self._data.get("score", 0)), C["concept_bg"], C["muted"], 11)
            top.addWidget(conf)
            outer.addLayout(top)

            meta = QHBoxLayout()
            meta.setSpacing(6)
            concepts = self._data.get("concepts", [])
            seen_c = set()
            unique_c = []
            for c in concepts:
                key = c.lower().strip()
                if key not in seen_c:
                    seen_c.add(key)
                    unique_c.append(c)
            for c in unique_c[:2]:
                meta.addWidget(make_chip(c.title(), C["concept_bg"], C["page"], 11))
            raw_pn = self._data.get("page_num")
            disp = raw_pn + 1 if raw_pn is not None else "?"
            pg = make_chip(f"p. {disp}", C["page_bg"], C["accent"], 11)
            pg.setStyleSheet(f"background: {C['page_bg']}; color: {C['accent']}; padding: 2px 8px; border-radius: 6px;")
            meta.addWidget(pg)
            meta.addStretch()
            outer.addLayout(meta)

        def set_selected(self, selected):
            self._selected = selected
            self.update()

        def paintEvent(self, event):
            super().paintEvent(event)
            if self._selected:
                p = QPainter(self)
                p.setPen(QPen(QColor(C['accent']), 2))
                p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
                p.end()

        def mousePressEvent(self, event):
            self._open_page(self._data)

        def _open_page(self, data):
            q = self._query
            pn = data.get("page_num")
            api_log_open(q, data["path"], data["file_id"], pn)
            record_last_open(data["path"], data["filename"], pn, data.get("author", ""))
            add_recent_search(q, pn)
            open_pdf(data["path"], pn)
            w = self.window()
            if w:
                w.hide()

    class SettingsDialog(QDialog):
        def __init__(self, cfg, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Settings")
            self.setFixedSize(480, 380)
            self._cfg = dict(cfg)
            self._new_combo = cfg.get("hotkey", "ctrl+alt+m")
            self._new_max_results = cfg.get("max_results", 8)

            from PyQt6.QtWidgets import QTabWidget, QSpinBox, QListWidget, QListWidgetItem

            lo = QVBoxLayout(self)
            lo.setContentsMargins(0, 0, 0, 0)
            lo.setSpacing(0)

            tabs = QTabWidget()
            tabs.setStyleSheet(f"""
                QTabWidget::pane {{ border: none; background: {C['bg']}; }}
                QTabBar::tab {{
                    padding: 8px 18px; font-family: 'Segoe UI'; font-size: 10pt;
                    color: {C['secondary']}; background: {C['card_bg']}; border: none;
                    border-right: 1px solid {C['border']};
                }}
                QTabBar::tab:selected {{ color: {C['accent']}; background: {C['bg']}; }}
            """)

            # --- Search tab ---
            search_tab = QWidget()
            st = QVBoxLayout(search_tab)
            st.setContentsMargins(20, 16, 20, 16)
            st.setSpacing(12)

            st.addWidget(QLabel("Global Hotkey:"))
            self.key_input = QLineEdit()
            self.key_input.setReadOnly(True)
            self.key_input.setPlaceholderText("Click Record then press a key combination...")
            self.key_input.setFont(QFont("Segoe UI", 12))
            self.key_input.setStyleSheet(f"""
                QLineEdit {{
                    padding: 8px 12px; border: 1px solid {C['border']}; border-radius: 6px;
                    background: {C['card_bg']}; color: {C['fg']};
                }}
            """)
            display = " + ".join(p.capitalize() if p in ("ctrl","alt","shift","win") else p.upper() for p in self._new_combo.split("+"))
            self.key_input.setText(display)
            self.record_btn = QPushButton("Record")
            self.record_btn.setCheckable(True)
            self.record_btn.setFont(QFont("Segoe UI", 10))
            self.record_btn.toggled.connect(self._on_record_toggled)
            kr = QHBoxLayout()
            kr.addWidget(self.key_input, 1)
            kr.addWidget(self.record_btn)
            st.addLayout(kr)

            st.addSpacing(8)
            st.addWidget(QLabel("Max Results:"))
            self.results_spin = QSpinBox()
            self.results_spin.setRange(2, 50)
            self.results_spin.setValue(self._new_max_results)
            self.results_spin.setFont(QFont("Segoe UI", 11))
            self.results_spin.setStyleSheet(f"""
                QSpinBox {{
                    padding: 6px 10px; border: 1px solid {C['border']}; border-radius: 6px;
                    background: {C['card_bg']}; color: {C['fg']};
                }}
            """)
            st.addWidget(self.results_spin)
            st.addStretch()

            # --- Viewer tab ---
            viewer_tab = QWidget()
            vt = QVBoxLayout(viewer_tab)
            vt.setContentsMargins(20, 16, 20, 16)
            vt.setSpacing(12)
            vt.addWidget(QLabel("PDF Viewer:"))
            self.viewer_combo = QComboBox()
            self.viewer_combo.addItem("Automatic", "auto")
            for v in _VIEWER_REGISTRY:
                if v.name != "auto" and v.available():
                    self.viewer_combo.addItem(v.display, v.name)
            current_viewer = cfg.get("preferred_viewer", "auto")
            idx = self.viewer_combo.findData(current_viewer)
            if idx >= 0:
                self.viewer_combo.setCurrentIndex(idx)
            self.viewer_combo.setStyleSheet(f"""
                QComboBox {{
                    padding: 6px 10px; border: 1px solid {C['border']}; border-radius: 6px;
                    background: {C['card_bg']}; color: {C['fg']};
                }}
                QComboBox::drop-down {{ border: none; }}
            """)
            vt.addWidget(self.viewer_combo)
            vt.addStretch()

            # --- Library tab ---
            library_tab = QWidget()
            lt = QVBoxLayout(library_tab)
            lt.setContentsMargins(20, 16, 20, 16)
            lt.setSpacing(8)

            lt.addWidget(QLabel("Watched Folders:"))
            self.folder_list = QListWidget()
            self.folder_list.setStyleSheet(f"""
                QListWidget {{
                    border: 1px solid {C['border']}; border-radius: 6px;
                    background: {C['card_bg']}; color: {C['fg']};
                    padding: 4px;
                }}
                QListWidget::item {{
                    padding: 6px 8px; border-radius: 4px;
                }}
                QListWidget::item:hover {{
                    background: {C['hover']};
                }}
            """)
            self._refresh_folder_list()
            lt.addWidget(self.folder_list, 1)

            folder_btns = QHBoxLayout()
            add_folder_btn = QPushButton("+ Add Folder")
            add_folder_btn.setFont(QFont("Segoe UI", 10))
            add_folder_btn.setStyleSheet(f"""
                QPushButton {{ background: {C['accent']}; color: #fff; border: none; border-radius: 6px; padding: 6px 16px; }}
                QPushButton:hover {{ opacity: 0.9; }}
            """)
            add_folder_btn.clicked.connect(self._on_add_folder)
            remove_folder_btn = QPushButton("Remove")
            remove_folder_btn.setFont(QFont("Segoe UI", 10))
            remove_folder_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {C['secondary']}; border: 1px solid {C['border']}; border-radius: 6px; padding: 6px 16px; }}
                QPushButton:hover {{ border-color: {C['accent']}; color: {C['accent']}; }}
            """)
            remove_folder_btn.clicked.connect(self._on_remove_folder)
            folder_btns.addWidget(add_folder_btn)
            folder_btns.addWidget(remove_folder_btn)
            folder_btns.addStretch()
            lt.addLayout(folder_btns)

            tabs.addTab(search_tab, "Search")
            tabs.addTab(viewer_tab, "Viewer")
            tabs.addTab(library_tab, "Library")
            lo.addWidget(tabs, 1)

            btn_row = QHBoxLayout()
            btn_row.addStretch()
            ok_btn = QPushButton("OK")
            ok_btn.setFont(QFont("Segoe UI", 10))
            ok_btn.setStyleSheet(f"background: {C['accent']}; color: #fff; border: none; border-radius: 6px; padding: 6px 20px;")
            ok_btn.clicked.connect(self.accept)
            btn_row.addWidget(ok_btn)
            lo.addLayout(btn_row)
            self.setStyleSheet(f"background: {C['bg']}; color: {C['fg']};")

        def _on_record_toggled(self, checked):
            if checked:
                self.key_input.clear()
                self.key_input.setPlaceholderText("Press key combination...")
                self.key_input.setFocus()

        def keyPressEvent(self, event):
            if self.record_btn.isChecked():
                if event.key() == Qt.Key.Key_Escape:
                    self.record_btn.setChecked(False)
                    return
                parts = []
                mods = event.modifiers()
                if mods & Qt.KeyboardModifier.ControlModifier:
                    parts.append("ctrl")
                if mods & Qt.KeyboardModifier.AltModifier:
                    parts.append("alt")
                if mods & Qt.KeyboardModifier.ShiftModifier:
                    parts.append("shift")
                if mods & Qt.KeyboardModifier.MetaModifier:
                    parts.append("win")
                key = event.key()
                if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
                    parts.append(chr(ord('0') + (key - Qt.Key.Key_0)))
                elif Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
                    parts.append(chr(ord('a') + (key - Qt.Key.Key_A)))
                elif key == Qt.Key.Key_Space:
                    parts.append("space")
                else:
                    return
                self._new_combo = "+".join(parts)
                display = " + ".join(p.capitalize() if p in ("ctrl","alt","shift","win") else p.upper() for p in parts)
                self.key_input.setText(display)
                self.record_btn.setChecked(False)
                return
            super().keyPressEvent(event)

        def _refresh_folder_list(self):
            self.folder_list.clear()
            from . import db as _db
            try:
                conn = _db.get_connection()
                folders = _db.get_watched_folders(conn)
                conn.close()
                for f in folders:
                    self.folder_list.addItem(f["path"])
            except Exception:
                pass

        def _on_add_folder(self):
            folder = QFileDialog.getExistingDirectory(self, "Select Library Folder")
            if folder:
                from . import db as _db
                from .config import load_config, save_config
                try:
                    conn = _db.get_connection()
                    _db.add_watched_folder(conn, folder)
                    conn.commit()
                    conn.close()
                    cf = load_config()
                    if folder not in cf.get("watched_folders", []):
                        cf.setdefault("watched_folders", []).append(folder)
                        save_config(cf)
                    self._refresh_folder_list()
                except Exception:
                    pass

        def _on_remove_folder(self):
            item = self.folder_list.currentItem()
            if item is None:
                return
            folder = item.text()
            from . import db as _db
            from .config import load_config, save_config
            try:
                conn = _db.get_connection()
                _db.remove_watched_folder(conn, folder)
                conn.commit()
                conn.close()
                cf = load_config()
                if folder in cf.get("watched_folders", []):
                    cf["watched_folders"].remove(folder)
                    save_config(cf)
                self._refresh_folder_list()
            except Exception:
                pass

        def combo(self):
            return self._new_combo

        def selected_viewer(self):
            return self.viewer_combo.currentData()

        def max_results(self):
            return self.results_spin.value()

    class SearchLineEdit(QLineEdit):
        navigateUp = pyqtSignal()
        navigateDown = pyqtSignal()
        activateSelected = pyqtSignal()
        dismiss = pyqtSignal()

        def keyPressEvent(self, event):
            if event.key() == Qt.Key.Key_Down:
                self.navigateDown.emit()
            elif event.key() == Qt.Key.Key_Up:
                self.navigateUp.emit()
            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.activateSelected.emit()
            elif event.key() == Qt.Key.Key_Escape:
                self.dismiss.emit()
            else:
                super().keyPressEvent(event)

    class SearchWindow(QWidget):
        toggleRequested = pyqtSignal()

        def __init__(self, hotkey_ref):
            super().__init__()
            self.setWindowTitle("Mnemo")
            self.setWindowFlags(Qt.WindowType.Window)
            self.setMinimumSize(640, 450)
            self.resize(820, 550)
            self.setStyleSheet(f"background: {C['bg']}; color: {C['fg']};")
            self._hotkey_ref = hotkey_ref
            self._result_cards = []
            self._selected_index = -1

            geo = load_window_geometry()
            if geo:
                self.restoreGeometry(geo)

            main = QVBoxLayout(self)
            main.setContentsMargins(0, 0, 0, 0)
            main.setSpacing(0)

            # Search bar — 56px
            search_bar = QWidget()
            search_bar.setFixedHeight(56)
            search_bar.setStyleSheet(f"background: {C['bg']}; border-bottom: 1px solid {C['border']};")
            sb_layout = QHBoxLayout(search_bar)
            sb_layout.setContentsMargins(16, 0, 16, 0)
            sb_layout.setSpacing(8)

            search_icon = icon_label("search", 20, C['secondary'])
            sb_layout.addWidget(search_icon)

            self.search_input = SearchLineEdit()
            self.search_input.setPlaceholderText("Search what you remember...")
            self.search_input.setFont(QFont("Segoe UI", 13))
            self.search_input.setStyleSheet(f"""
                QLineEdit {{
                    background: transparent; border: none; color: {C['fg']}; padding: 0;
                }}
                QLineEdit::placeholder {{ color: {C['muted']}; }}
            """)
            self.search_input.textChanged.connect(self.on_text_changed)
            self.search_input.navigateDown.connect(self._navigate_down)
            self.search_input.navigateUp.connect(self._navigate_up)
            self.search_input.activateSelected.connect(self._activate_selected)
            self.search_input.dismiss.connect(self.hide)
            sb_layout.addWidget(self.search_input, 1)

            self.settings_btn = QPushButton()
            self.settings_btn.setIcon(QIcon(icon_pixmap("settings", 20, C['muted'])))
            self.settings_btn.setFixedSize(32, 32)
            self.settings_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: none; color: {C['muted']}; border-radius: 6px; }}
                QPushButton:hover {{ background: {C['hover']}; color: {C['fg']}; }}
            """)
            self.settings_btn.clicked.connect(self._open_settings)
            sb_layout.addWidget(self.settings_btn)

            main.addWidget(search_bar)

            # Scroll area for results
            self.scroll = QScrollArea()
            self.scroll.setWidgetResizable(True)
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.scroll.setStyleSheet(f"""
                QScrollArea {{ border: none; background: {C['bg']}; }}
                QScrollBar:vertical {{ width: 6px; background: transparent; }}
                QScrollBar::handle:vertical {{ background: {C['border']}; border-radius: 3px; min-height: 30px; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            """)

            self.scroll_content = QWidget()
            self.scroll_content.setStyleSheet(f"background: {C['bg']};")
            self.scroll_layout = QVBoxLayout(self.scroll_content)
            self.scroll_layout.setContentsMargins(16, 8, 16, 8)
            self.scroll_layout.setSpacing(0)
            self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.scroll.setWidget(self.scroll_content)
            main.addWidget(self.scroll, 1)

            # Footer — 32px, subdued
            footer = QWidget()
            footer.setFixedHeight(32)
            footer.setStyleSheet(f"background: {C['bg']};")
            ftr = QHBoxLayout(footer)
            ftr.setContentsMargins(20, 0, 20, 0)

            def shortkey(text, key):
                w = QWidget()
                w.setStyleSheet("background: transparent;")
                r = QHBoxLayout(w)
                r.setContentsMargins(0, 0, 0, 0)
                r.setSpacing(4)
                k = QLabel(key)
                k.setFont(QFont("Segoe UI", 8))
                k.setStyleSheet(f"color: {C['muted']}; background: transparent;")
                l = QLabel(text.upper())
                l.setFont(QFont("Segoe UI", 9))
                l.setStyleSheet(f"color: {C['muted']}; background: transparent;")
                r.addWidget(k)
                r.addWidget(l)
                return w

            ftr.addWidget(shortkey("Navigate", "↑↓"))
            ftr.addWidget(shortkey("Open", "↵"))
            ftr.addWidget(shortkey("Dismiss", "ESC"))
            ftr.addStretch()
            self._status_lbl = QLabel("●")
            self._status_lbl.setFont(QFont("Segoe UI", 9))
            self._status_lbl.setStyleSheet(f"color: {C['muted']}; background: transparent;")
            ftr.addWidget(self._status_lbl)
            self._status_txt = QLabel("Engine Ready")
            self._status_txt.setFont(QFont("Segoe UI", 9))
            self._status_txt.setStyleSheet(f"color: {C['muted']}; background: transparent;")
            ftr.addWidget(self._status_txt)
            main.addWidget(footer)

            self._search_timer = QTimer()
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self._do_search)
            QTimer.singleShot(1000, self._check_daemon_health)
            self._current_query = ""
            self._last_query = ""
            self._recent_searches = load_recent_searches()
            self._last_open = load_last_open()
            self.toggleRequested.connect(self.toggle)

        def _clear_results(self):
            self._result_cards = []
            self._selected_index = -1
            while self.scroll_layout.count():
                item = self.scroll_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

        @staticmethod
        def _time_ago(ts):
            elapsed = time.time() - ts
            if elapsed < 3600:
                return "Last opened recently"
            elif elapsed < 86400:
                return f"Last opened {int(elapsed // 3600)}h ago"
            elif elapsed < 172800:
                return "Last opened yesterday"
            elif elapsed < 604800:
                return f"Last opened {int(elapsed // 86400)} days ago"
            else:
                return f"Last opened {int(elapsed // 604800)}w ago"

        def _build_continue_card(self, entry):
            cr = QWidget()
            cr.setObjectName("continueCard")
            cr.setStyleSheet(f"""
                #continueCard {{
                    background: {C['card_bg']}; border: 1px solid {C['border']}; border-radius: 8px;
                }}
                #continueCard:hover {{ border-color: {C['card_hover']}; }}
            """)
            cr_layout = QHBoxLayout(cr)
            cr_layout.setContentsMargins(12, 12, 12, 12)
            cr_layout.setSpacing(12)

            clr = book_color(entry.get("filename", ""))
            icon_w = QWidget()
            icon_w.setFixedSize(36, 44)
            icon_w.setStyleSheet(f"background: {C['card_bg']}; border-left: 3px solid {clr}; border-radius: 4px;")
            i_l = QVBoxLayout(icon_w)
            i_l.setContentsMargins(0, 0, 0, 0)
            i_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            i_l.addWidget(icon_label("book", 20, clr))
            cr_layout.addWidget(icon_w)

            ci = QVBoxLayout()
            ci.setSpacing(2)
            name = QLabel(clean_filename(entry.get("filename", "")))
            name.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
            name.setStyleSheet(f"color: {C['fg']}; background: transparent;")
            ci.addWidget(name)
            author_name = entry.get("author") or ""
            if author_name:
                a = QLabel(author_name[:50])
                a.setFont(QFont("Segoe UI", 11))
                a.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
                ci.addWidget(a)
            ts = entry.get("timestamp")
            if ts:
                ago = QLabel(self._time_ago(ts))
                ago.setFont(QFont("Segoe UI", 10))
                ago.setStyleSheet(f"color: {C['muted']}; background: transparent;")
                ci.addWidget(ago)
            saved_page = entry.get("page")
            disp = saved_page + 1 if saved_page is not None else "?"
            sub = QLabel(f"Page {disp}  ·  Resume →")
            sub.setFont(QFont("Segoe UI", 10))
            sub.setStyleSheet(f"color: {C['accent']}; background: transparent;")
            ci.addWidget(sub)
            cr_layout.addLayout(ci, 1)

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 45))
            cr.setGraphicsEffect(shadow)
            cr.setCursor(Qt.CursorShape.PointingHandCursor)
            cr.mousePressEvent = lambda e, d=entry: self._open_continue(d)
            return cr

        def _show_empty_state(self):
            self._clear_results()
            has_content = False

            # Continue Reading section
            continue_entries = self._last_open[-3:] if self._last_open else []
            if continue_entries:
                has_content = True
                sec = QLabel("CONTINUE READING")
                sec.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
                sec.setStyleSheet(f"color: {C['secondary']}; background: transparent; letter-spacing: 0.08em; padding-bottom: 14px;")
                self.scroll_layout.addWidget(sec)

                for entry in reversed(continue_entries):
                    cr = self._build_continue_card(entry)
                    self.scroll_layout.addWidget(cr)
                    self.scroll_layout.addSpacing(8)

            # Recent Searches section
            if self._recent_searches:
                has_content = True
                self.scroll_layout.addSpacing(16)
                sec = QLabel("RECENT SEARCHES")
                sec.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
                sec.setStyleSheet(f"color: {C['secondary']}; background: transparent; letter-spacing: 0.08em; padding-bottom: 14px;")
                self.scroll_layout.addWidget(sec)

                rs_box = QWidget()
                rs_box.setObjectName("recentSearchesBox")
                rs_box.setStyleSheet(f"""
                    #recentSearchesBox {{
                        background: {C['card_bg']}; border: 1px solid {C['border']}; border-radius: 8px;
                    }}
                """)
                rs_layout = QVBoxLayout(rs_box)
                rs_layout.setContentsMargins(8, 4, 8, 4)
                rs_layout.setSpacing(0)
                for entry in reversed(self._recent_searches[-8:]):
                    q = entry["query"] if isinstance(entry, dict) else entry
                    pg = entry.get("page") if isinstance(entry, dict) else None
                    display = q
                    if pg is not None:
                        display += f"  ·  p. {pg + 1}"
                    row = QWidget()
                    row.setStyleSheet("background: transparent;")
                    row.setCursor(Qt.CursorShape.PointingHandCursor)
                    row.mousePressEvent = lambda e, ent=entry: self._run_recent(ent)
                    rl = QHBoxLayout(row)
                    rl.setContentsMargins(8, 6, 8, 6)
                    rl.setSpacing(10)
                    ico = icon_label("search", 16, C['muted'])
                    rl.addWidget(ico)
                    label = QLabel(display)
                    label.setFont(QFont("Segoe UI", 12))
                    label.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
                    rl.addWidget(label, 1)
                    rs_layout.addWidget(row)
                self.scroll_layout.addWidget(rs_box)

            # Search tips when no recent activity
            if not has_content:
                sec = QLabel("QUICK START")
                sec.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
                sec.setStyleSheet(f"color: {C['secondary']}; background: transparent; letter-spacing: 0.08em; padding-bottom: 4px;")
                self.scroll_layout.addWidget(sec)

                tips = [
                    "Search what you remember — Mnemo understands meaning, not just keywords",
                    "Press Ctrl+M from anywhere to open this launcher",
                    "Use ↑↓ to navigate results, Enter to open",
                    "Click ⚙ to change your hotkey or PDF viewer",
                ]
                for tip in tips:
                    t = QLabel(f"  {tip}")
                    t.setFont(QFont("Segoe UI", 11))
                    t.setStyleSheet(f"color: {C['muted']}; background: transparent; padding: 5px 0;")
                    self.scroll_layout.addWidget(t)

        def _open_continue(self, data):
            record_last_open(data["path"], data.get("filename", ""), data.get("page"), data.get("author", ""))
            open_pdf(data["path"], data.get("page"))
            self.hide()

        def _run_recent(self, entry):
            q = entry["query"] if isinstance(entry, dict) else entry
            self.search_input.setText(q)
            self.search_input.setFocus()

        def _force_activate(self):
            flags = self.windowFlags()
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
            self.show()
            self.activateWindow()
            self.raise_()
            self.setWindowFlags(flags)
            self.show()

        def toggle(self):
            if not self.isVisible():
                self._recent_searches = load_recent_searches()
                self._last_open = load_last_open()
                self._force_activate()
                self.search_input.setText(self._last_query)
                self.search_input.setFocus()
                if self._last_query:
                    self.search_input.selectAll()
                elif not self._current_query:
                    self._show_empty_state()
            elif self.isActiveWindow():
                self.hide()
            else:
                self._force_activate()
                self.search_input.setFocus()

        def showEvent(self, event):
            super().showEvent(event)
            self.search_input.setFocus()
            self.search_input.selectAll()

        def on_text_changed(self, text):
            self._current_query = text
            self._last_query = text
            self._search_timer.stop()
            if len(text.strip()) >= 3:
                self._search_timer.start(300)
            else:
                self._show_empty_state()

        def _do_search(self):
            q = self._current_query.strip()
            if not q:
                self._show_empty_state()
                return
            result = api_search(q)
            self._show_results(result)

        def _show_results(self, result):
            self._clear_results()
            if not result or not result.get("results"):
                msg = QWidget()
                msg.setStyleSheet("background: transparent;")
                ml = QVBoxLayout(msg)
                ml.setAlignment(Qt.AlignmentFlag.AlignCenter)
                ml.setSpacing(4)
                if result and result.get("reason") == "loading":
                    t = QLabel("Mnemo is starting up...")
                    s = QLabel("The search model is still loading, results will appear shortly")
                else:
                    t = QLabel("No matches found")
                    s = QLabel("Try a different phrase or search for the concept itself")
                t.setFont(QFont("Segoe UI", 15))
                t.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
                t.setAlignment(Qt.AlignmentFlag.AlignCenter)
                ml.addWidget(t)
                s.setFont(QFont("Segoe UI", 12))
                s.setStyleSheet(f"color: {C['muted']}; background: transparent;")
                s.setAlignment(Qt.AlignmentFlag.AlignCenter)
                ml.addWidget(s)
                self.scroll_layout.addWidget(msg)
                self.scroll_layout.addStretch()
                return

            query = self._current_query
            groups = []
            for r in result["results"]:
                if groups and groups[-1]["filename"] == r["filename"]:
                    groups[-1]["pages"].append(r)
                else:
                    groups.append({"filename": r["filename"], "pages": [r]})

            # Best Match section
            if groups:
                sec = QLabel("BEST MATCH")
                sec.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
                sec.setStyleSheet(f"color: {C['secondary']}; background: transparent; letter-spacing: 0.08em; padding-bottom: 4px;")
                self.scroll_layout.addWidget(sec)
                first_group = groups[0]
                if len(first_group["pages"]) == 1:
                    card = FeaturedCard(first_group["pages"][0], query, parent=self)
                else:
                    card = FeaturedCard(first_group["pages"][0], query, pages=first_group["pages"], parent=self)
                self.scroll_layout.addWidget(card)
                self._result_cards.append(card)

                # Other Sources section
                if len(groups) > 1:
                    self.scroll_layout.addSpacing(24)
                    sec2 = QLabel("OTHER SOURCES")
                    sec2.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
                    sec2.setStyleSheet(f"color: {C['secondary']}; background: transparent; letter-spacing: 0.08em; padding-bottom: 4px;")
                    self.scroll_layout.addWidget(sec2)
                    for g in groups[1:]:
                        data = g["pages"][0]
                        card = SecondaryCard(data, query, parent=self)
                        self.scroll_layout.addWidget(card)
                        self.scroll_layout.addSpacing(8)
                        self._result_cards.append(card)

            if self._result_cards:
                import logging as _lg; _lg.warning("RESULTS: %d cards, highlighting 0", len(self._result_cards))
                self._selected_index = 0
                self._highlight_card(0)

        def _highlight_card(self, index):
            for i, c in enumerate(self._result_cards):
                c.set_selected(i == index)
                c.repaint()

        def _activate_selected(self):
            if 0 <= self._selected_index < len(self._result_cards):
                card = self._result_cards[self._selected_index]
                if hasattr(card, '_open_page'):
                    card._open_page(card._data)

        def _check_daemon_health(self):
            try:
                r = urllib.request.urlopen(f"{API_BASE}/status", timeout=2)
                if r.getcode() == 200:
                    self._status_lbl.setStyleSheet(f"color: #4ADE80; background: transparent;")
            except Exception:
                pass

        def _navigate_down(self):
            if self._result_cards:
                nxt = min(self._selected_index + 1, len(self._result_cards) - 1)
                if nxt != self._selected_index:
                    self._selected_index = nxt
                    self._highlight_card(nxt)
                    self.scroll.ensureWidgetVisible(self._result_cards[nxt])

        def _navigate_up(self):
            if self._result_cards:
                prv = max(self._selected_index - 1, 0)
                if prv != self._selected_index:
                    self._selected_index = prv
                    self._highlight_card(prv)
                    self.scroll.ensureWidgetVisible(self._result_cards[prv])

        def _open_settings(self):
            from .config import load_config, save_config
            cfg = load_config()
            dialog = SettingsDialog(cfg, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_hotkey = dialog.combo()
                new_viewer = dialog.selected_viewer()
                new_max = dialog.max_results()
                cfg["hotkey"] = new_hotkey
                cfg["preferred_viewer"] = new_viewer
                cfg["max_results"] = new_max
                save_config(cfg)
                self._hotkey_ref["raw"] = new_hotkey
                self._hotkey_ref["pynput"].stop()
                from pynput import keyboard
                parts = new_hotkey.lower().split("+")
                pynput_parts = []
                for p in parts:
                    p = p.strip()
                    if p in ("ctrl", "alt", "shift", "cmd", "win"):
                        pynput_parts.append(f"<{p}>")
                    elif p in ("space", "tab", "enter", "esc", "backspace"):
                        pynput_parts.append(f"<{p}>")
                    else:
                        pynput_parts.append(p)
                pynput_hotkey = "+".join(pynput_parts)

                def on_activate():
                    self.toggleRequested.emit()
                new_listener = keyboard.GlobalHotKeys({pynput_hotkey: on_activate})
                new_listener.start()
                self._hotkey_ref["pynput"] = new_listener
                logger.info("Settings updated: hotkey=%s viewer=%s max_results=%d", new_hotkey, new_viewer, new_max)

        def closeEvent(self, event):
            save_window_geometry(self.saveGeometry())
            event.ignore()
            self.hide()

        def resizeEvent(self, event):
            super().resizeEvent(event)
            save_window_geometry(self.saveGeometry())

        def moveEvent(self, event):
            super().moveEvent(event)
            save_window_geometry(self.saveGeometry())

        def keyPressEvent(self, event):
            if event.key() == Qt.Key.Key_Escape:
                self.hide()
            elif event.key() == Qt.Key.Key_Down:
                if self._result_cards:
                    nxt = min(self._selected_index + 1, len(self._result_cards) - 1)
                    if nxt != self._selected_index:
                        self._selected_index = nxt
                        self._highlight_card(nxt)
                        self.scroll.ensureWidgetVisible(self._result_cards[nxt])
            elif event.key() == Qt.Key.Key_Up:
                if self._result_cards:
                    prv = max(self._selected_index - 1, 0)
                    if prv != self._selected_index:
                        self._selected_index = prv
                        self._highlight_card(prv)
                        self.scroll.ensureWidgetVisible(self._result_cards[prv])
            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._activate_selected()
            else:
                super().keyPressEvent(event)

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.satvik.mnemo")

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(_icon_path()))
    app.setQuitOnLastWindowClosed(False)

    from pynput import keyboard
    from .config import load_config, save_config
    from . import db as db_module
    cfg = load_config()
    raw_hotkey = cfg.get("hotkey", "ctrl+alt+m")

    parts = raw_hotkey.lower().split("+")
    pynput_parts = []
    for p in parts:
        p = p.strip()
        if p in ("ctrl", "alt", "shift", "cmd", "win"):
            pynput_parts.append(f"<{p}>")
        elif p in ("space", "tab", "enter", "esc", "backspace"):
            pynput_parts.append(f"<{p}>")
        else:
            pynput_parts.append(p)
    pynput_hotkey = "+".join(pynput_parts)
    logger.info("Hotkey: %s", raw_hotkey)

    def on_activate():
        window.toggleRequested.emit()

    hotkey = keyboard.GlobalHotKeys({pynput_hotkey: on_activate})
    try:
        hotkey.start()
    except Exception as e:
        logger.error("Failed to start global hotkey '%s': %s", pynput_hotkey, e)

    hotkey_ref = {"raw": raw_hotkey, "pynput": hotkey}
    window = SearchWindow(hotkey_ref)
    window.setWindowIcon(QIcon(_icon_path()))

    # First-run onboarding
    if not cfg.get("watched_folders"):
        theme_mode = detect_windows_theme()
        C0 = DARK_COLORS if theme_mode == "dark" else LIGHT_COLORS
        dlg = _FirstRunDialog(C0)
        dlg.exec()
        # Save selected folders (indexing already triggered by dialog)
        folders = dlg.selected_folders()
        if folders:
            cfg["watched_folders"] = folders
            save_config(cfg)
            conn = db_module.get_connection()
            for folder in folders:
                db_module.add_watched_folder(conn, folder)
            conn.commit()
            conn.close()

    window.toggle()

    def _show_health():
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:8765/status", timeout=3)
            data = json.loads(resp.read())
            api_ok = True
        except Exception:
            data = {}
            api_ok = False
        try:
            sr = urllib.request.urlopen("http://127.0.0.1:8765/search?q=test&limit=1", timeout=3)
            sdata = json.loads(sr.read())
            search_latency = sdata.get("latency_ms", "—")
        except Exception:
            search_latency = "—"
        dlg = QDialog()
        dlg.setWindowTitle("Mnemo Health")
        dlg.setFixedSize(440, 380)
        theme_mode = detect_windows_theme()
        C0 = DARK_COLORS if theme_mode == "dark" else LIGHT_COLORS
        dlg.setStyleSheet(f"background: {C0['bg']}; color: {C0['fg']};")
        lo = QVBoxLayout(dlg)
        lo.setContentsMargins(24, 24, 24, 24)
        lo.setSpacing(10)
        checks = [
            ("Search API", "✓" if api_ok else "✗", "#4ADE80" if api_ok else "#F87171"),
            ("Embedding model", "✓" if data.get("model_ready") else "⟳", "#4ADE80" if data.get("model_ready") else "#FBBF24"),
            ("OCR available", "✓", "#4ADE80"),
            ("File watcher", "✓", "#4ADE80"),
            ("Search latency", f"{search_latency} ms" if search_latency != "—" else "—", "#4ADE80" if search_latency != "—" else "#F87171"),
        ]
        for label, val, color in checks:
            row = QHBoxLayout()
            row.setSpacing(8)
            dot = QLabel("●")
            dot.setFont(QFont("Segoe UI", 12))
            dot.setStyleSheet(f"color: {color}; background: transparent;")
            row.addWidget(dot)
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 11))
            lbl.setStyleSheet(f"color: {C0['secondary']}; background: transparent;")
            row.addWidget(lbl)
            row.addStretch()
            v = QLabel(str(val))
            v.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
            v.setStyleSheet(f"color: {C0['fg']}; background: transparent;")
            row.addWidget(v)
            lo.addLayout(row)
        lo.addSpacing(12)
        hr = QFrame()
        hr.setFrameShape(QFrame.Shape.HLine)
        hr.setStyleSheet(f"color: {C0['border']};")
        lo.addWidget(hr)
        lo.addSpacing(8)
        stats = [
            ("Indexed files", str(data.get("files_indexed", "—"))),
            ("Total files", str(data.get("files_total", "—"))),
            ("Total pages", str(data.get("pages_total", "—"))),
            ("OCR pending", str(data.get("pages_needing_ocr", "—"))),
        ]
        for label, val in stats:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 10))
            lbl.setStyleSheet(f"color: {C0['muted']}; background: transparent;")
            row.addWidget(lbl)
            row.addStretch()
            v = QLabel(val)
            v.setFont(QFont("Segoe UI", 10))
            v.setStyleSheet(f"color: {C0['secondary']}; background: transparent;")
            row.addWidget(v)
            lo.addLayout(row)
        lo.addStretch()
        btn = QPushButton("Close")
        btn.setFont(QFont("Segoe UI", 10))
        btn.setStyleSheet(f"background: {C0['accent']}; color: #fff; border: none; border-radius: 6px; padding: 8px;")
        btn.clicked.connect(dlg.accept)
        lo.addWidget(btn)
        dlg.exec()

    def _show_dashboard():
        try:
            resp = urllib.request.urlopen("http://127.0.0.1:8765/status", timeout=3)
            data = json.loads(resp.read())
        except Exception:
            data = {}
        dlg = QDialog()
        dlg.setWindowTitle("Mnemo Dashboard")
        dlg.setFixedSize(420, 320)
        theme_mode = detect_windows_theme()
        C0 = DARK_COLORS if theme_mode == "dark" else LIGHT_COLORS
        dlg.setStyleSheet(f"background: {C0['bg']}; color: {C0['fg']};")
        lo = QVBoxLayout(dlg)
        lo.setContentsMargins(24, 24, 24, 24)
        lo.setSpacing(12)
        stats = [
            ("Indexed files", str(data.get("files_indexed", "—"))),
            ("Total files", str(data.get("files_total", "—"))),
            ("Status", data.get("status", "—")),
            ("Pages", str(data.get("pages_total", "—"))),
            ("OCR pending", str(data.get("pages_needing_ocr", "—"))),
        ]
        for label, val in stats:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 11))
            lbl.setStyleSheet(f"color: {C0['secondary']}; background: transparent;")
            row.addWidget(lbl)
            row.addStretch()
            v = QLabel(val)
            v.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
            v.setStyleSheet(f"color: {C0['fg']}; background: transparent;")
            row.addWidget(v)
            lo.addLayout(row)
        lo.addStretch()
        btn = QPushButton("Close")
        btn.setFont(QFont("Segoe UI", 10))
        btn.setStyleSheet(f"background: {C0['accent']}; color: #fff; border: none; border-radius: 6px; padding: 8px;")
        btn.clicked.connect(dlg.accept)
        lo.addWidget(btn)
        dlg.exec()

    def _show_settings():
        window._open_settings()

    def _index_now():
        for folder in cfg.get("watched_folders", []):
            try:
                urllib.request.urlopen(
                    urllib.request.Request(f"http://127.0.0.1:8765/index?path={urllib.parse.quote(folder)}", method="POST"),
                    timeout=300,
                )
            except Exception:
                pass

    tray = QSystemTrayIcon(QIcon(_icon_path()), app)
    tray.setToolTip("Mnemo")
    menu = QMenu()

    open_action = menu.addAction("Open Search")
    open_action.setFont(QFont("Segoe UI", 10))
    open_action.triggered.connect(window.toggle)

    dash_action = menu.addAction("Dashboard")
    dash_action.setFont(QFont("Segoe UI", 10))
    dash_action.triggered.connect(_show_dashboard)

    settings_action = menu.addAction("Settings")
    settings_action.setFont(QFont("Segoe UI", 10))
    settings_action.triggered.connect(_show_settings)

    health_action = menu.addAction("Health")
    health_action.setFont(QFont("Segoe UI", 10))
    health_action.triggered.connect(_show_health)

    menu.addSeparator()
    index_action = menu.addAction("Index Now")
    index_action.setFont(QFont("Segoe UI", 10))
    index_action.triggered.connect(_index_now)

    menu.addSeparator()
    quit_action = menu.addAction("Quit")
    quit_action.setFont(QFont("Segoe UI", 10))
    quit_action.triggered.connect(app.quit)

    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: window.toggle() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
    tray.show()

    app.exec()
