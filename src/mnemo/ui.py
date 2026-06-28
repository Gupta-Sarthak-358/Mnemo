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

from PyQt6.QtCore import Qt, QTimer, QEvent, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QIcon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QScrollArea,
    QDialog, QPushButton, QComboBox, QSizePolicy,
    QGraphicsDropShadowEffect,
)
from .icons import icon_label, icon_pixmap

logger = logging.getLogger(__name__)

API_BASE = "http://127.0.0.1:8765"


def api_search(query):
    try:
        url = f"{API_BASE}/search?q={urllib.parse.quote(query)}&limit=8"
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
    "bg": "#0F0F0F", "fg": "#E8E8E8", "card_bg": "#1A1A1A",
    "border": "#2A2A2A", "input_bg": "transparent", "input_border": "#2A2A2A",
    "hover": "#252525", "selected": "#333535", "secondary": "#C3C6D4",
    "muted": "#888888", "page": "#AAAAAA", "score": "#AAAAAA",
    "highlight_bg": "transparent", "highlight_fg": "#E8E8E8",
    "accent": "#5B8DEF", "concept_bg": "#252525", "page_bg": "#1E2A3A",
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


def save_last_open(file_path, filename, page_num, author=""):
    try:
        path = os.path.join(os.path.expanduser("~/.mnemo"), "last_open.json")
        with open(path, "w") as f:
            json.dump({"path": file_path, "filename": filename, "page": page_num, "author": author}, f)
    except Exception:
        pass


def load_last_open():
    try:
        path = os.path.join(os.path.expanduser("~/.mnemo"), "last_open.json")
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def save_recent_searches(searches):
    try:
        seen = set()
        deduped = []
        for s in searches:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
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
            return json.load(f)
    except Exception:
        return []


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
    lbl.setStyleSheet(f"background: {bg}; color: {fg}; padding: 2px 8px; border-radius: 6px;")
    lbl.setFixedHeight(22)
    return lbl


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
            self._build()

        @staticmethod
        def _make_badge(score):
            if score >= 0.70:
                label_text = "Strong"
                bg = "#1A3A2A"
                dot = "🟢"
            elif score >= 0.50:
                label_text = "Good"
                bg = "#3A3A1A"
                dot = "🟡"
            else:
                label_text = "Mention"
                bg = "#2A2A2A"
                dot = "⚪"
            badge = QLabel(f"{dot} {label_text}")
            badge.setFont(QFont("Segoe UI", 11))
            badge.setStyleSheet(f"background: {bg}; color: {C['fg']}; padding: 2px 10px; border-radius: 10px;")
            badge.setFixedHeight(22)
            return badge

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
                #featuredCard[nav_selected="true"] {{
                    border-color: {C['accent']};
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
            author_name = self._data.get("author") or self._data.get("heading")
            if author_name:
                a = QLabel(author_name[:50])
                a.setFont(QFont("Segoe UI", 12))
                a.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
                title_col.addWidget(a)
            header.addLayout(title_col, 1)

            header.addWidget(self._make_badge(self._data.get("score", 0)))
            outer.addLayout(header)

            # Why this matched — one-sentence explanation from snippet
            snippet = self._data.get("snippet", "")
            if snippet:
                explanation = extract_best_sentences(snippet, self._query, 1)
                if explanation:
                    why_lbl = QLabel(explanation)
                    why_lbl.setFont(QFont("Segoe UI", 12))
                    why_lbl.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
                    why_lbl.setWordWrap(True)
                    outer.addWidget(why_lbl)

            # Concept chips
            concepts = self._data.get("concepts", [])
            if concepts:
                chip_row = QHBoxLayout()
                chip_row.setSpacing(6)
                chip_row.setContentsMargins(0, 0, 0, 0)
                for c in concepts[:5]:
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
                also.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
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

            self._more_btn = QPushButton("More context")
            self._more_btn.setFont(QFont("Segoe UI", 11))
            self._more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._more_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {C['muted']}; border: none; padding: 0 4px; }}
                QPushButton:hover {{ color: {C['accent']}; }}
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

            # Click anywhere to open (on Enter or double-click)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        def mousePressEvent(self, event):
            self._open_page(self._data)

        def _toggle_snippet(self):
            self._expanded = not self._expanded
            full_text = self._data.get("snippet", "")
            if self._expanded:
                display = extract_best_sentences(full_text, self._query, 4)
                display = clean_snippet(display, 600)
                self._more_btn.setText("Less context")
            else:
                display = ""
                self._more_btn.setText("More context")
            self._snippet_label.setText(highlight_terms(display, self._query, C["highlight_bg"], C["highlight_fg"]))
            self._snippet_container.setVisible(self._expanded)

        def _open_page(self, data):
            q = self._query
            pn = data.get("page_num")
            api_log_open(q, data["path"], data["file_id"], pn)
            save_last_open(data["path"], data["filename"], pn, data.get("author", ""))
            open_pdf(data["path"], pn)
            w = self.window()
            if w:
                w.hide()

    class SecondaryCard(QWidget):
        def __init__(self, result_data, query="", parent=None):
            super().__init__(parent)
            self._data = result_data
            self._query = query
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
                #secondaryCard[nav_selected="true"] {{
                    border-color: {C['accent']};
                    border-left-color: {C['accent']};
                }}
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(8)
            shadow.setOffset(0, 1)
            shadow.setColor(QColor(0, 0, 0, 40))
            self.setGraphicsEffect(shadow)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            outer = QVBoxLayout(self)
            outer.setContentsMargins(12, 10, 12, 10)
            outer.setSpacing(4)

            top = QHBoxLayout()
            top.setSpacing(10)
            top.addWidget(icon_label("book", 18, clr))
            name = QLabel(clean_filename(self._data["filename"]))
            name.setFont(QFont("Segoe UI", 12))
            name.setStyleSheet(f"color: {C['fg']}; background: transparent;")
            top.addWidget(name, 1)
            top.addWidget(FeaturedCard._make_badge(self._data.get("score", 0)))
            outer.addLayout(top)

            meta = QHBoxLayout()
            meta.setSpacing(6)
            concepts = self._data.get("concepts", [])
            for c in concepts[:2]:
                meta.addWidget(make_chip(c.title(), C["concept_bg"], C["page"], 11))
            raw_pn = self._data.get("page_num")
            disp = raw_pn + 1 if raw_pn is not None else "?"
            pg = make_chip(f"p. {disp}", C["page_bg"], C["accent"], 11)
            pg.setStyleSheet(f"background: {C['page_bg']}; color: {C['accent']}; padding: 2px 8px; border-radius: 6px;")
            meta.addWidget(pg)
            meta.addStretch()
            outer.addLayout(meta)

        def mousePressEvent(self, event):
            self._open_page(self._data)

        def _open_page(self, data):
            q = self._query
            pn = data.get("page_num")
            api_log_open(q, data["path"], data["file_id"], pn)
            save_last_open(data["path"], data["filename"], pn, data.get("author", ""))
            open_pdf(data["path"], pn)
            w = self.window()
            if w:
                w.hide()

    class SettingsDialog(QDialog):
        def __init__(self, current_hotkey, current_viewer="auto", parent=None):
            super().__init__(parent)
            self.setWindowTitle("Settings")
            self.setFixedSize(380, 260)
            self._new_combo = current_hotkey
            self._viewer = current_viewer

            layout = QVBoxLayout()
            layout.setSpacing(12)

            layout.addWidget(QLabel("Global Hotkey:"))
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
            display = " + ".join(p.capitalize() if p in ("ctrl","alt","shift","win") else p.upper() for p in current_hotkey.split("+"))
            self.key_input.setText(display)
            self.record_btn = QPushButton("Record")
            self.record_btn.setCheckable(True)
            self.record_btn.setFont(QFont("Segoe UI", 10))
            self.record_btn.toggled.connect(self._on_record_toggled)
            key_row = QHBoxLayout()
            key_row.addWidget(self.key_input, 1)
            key_row.addWidget(self.record_btn)
            layout.addLayout(key_row)

            layout.addWidget(QLabel("PDF Viewer:"))
            self.viewer_combo = QComboBox()
            self.viewer_combo.addItem("Automatic", "auto")
            for v in _VIEWER_REGISTRY:
                if v.name != "auto" and v.available():
                    self.viewer_combo.addItem(v.display, v.name)
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
            layout.addWidget(self.viewer_combo)

            btn_row = QHBoxLayout()
            btn_row.addStretch()
            ok_btn = QPushButton("OK")
            ok_btn.setFont(QFont("Segoe UI", 10))
            ok_btn.setStyleSheet(f"background: {C['accent']}; color: #fff; border: none; border-radius: 6px; padding: 6px 20px;")
            ok_btn.clicked.connect(self.accept)
            btn_row.addWidget(ok_btn)
            layout.addLayout(btn_row)
            self.setLayout(layout)
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

        def combo(self):
            return self._new_combo

        def selected_viewer(self):
            return self.viewer_combo.currentData()

    class SearchWindow(QWidget):
        toggleRequested = pyqtSignal()

        def __init__(self, hotkey_ref):
            super().__init__()
            self.setWindowTitle("Mnemo")
            self.setWindowFlags(Qt.WindowType.Window)
            self.setMinimumSize(640, 480)
            self.resize(820, 720)
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

            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("Search what you remember...")
            self.search_input.setFont(QFont("Segoe UI", 13))
            self.search_input.setStyleSheet(f"""
                QLineEdit {{
                    background: transparent; border: none; color: {C['fg']}; padding: 0;
                }}
                QLineEdit::placeholder {{ color: {C['muted']}; }}
            """)
            self.search_input.textChanged.connect(self.on_text_changed)
            self.search_input.installEventFilter(self)
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
            self.scroll_layout.setContentsMargins(24, 8, 24, 8)
            self.scroll_layout.setSpacing(0)
            self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.scroll.setWidget(self.scroll_content)
            main.addWidget(self.scroll, 1)

            # Footer — 32px, subdued
            footer = QWidget()
            footer.setFixedHeight(32)
            footer.setStyleSheet(f"background: {C['surface_lowest']};")
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
            status = QLabel("● Engine Ready")
            status.setFont(QFont("Segoe UI", 9))
            status.setStyleSheet(f"color: {C['muted']}; background: transparent;")
            ftr.addWidget(status)
            main.addWidget(footer)

            self._search_timer = QTimer()
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self._do_search)
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

        def _show_empty_state(self):
            self._clear_results()
            # Continue Reading section
            if self._last_open:
                sec = QLabel("CONTINUE READING")
                sec.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
                sec.setStyleSheet(f"color: {C['secondary']}; background: transparent; letter-spacing: 0.08em; padding-bottom: 4px;")
                self.scroll_layout.addWidget(sec)

                cr = QWidget()
                cr.setStyleSheet(f"background: {C['card_bg']}; border: 1px solid {C['border']}; border-radius: 8px;")
                cr_layout = QHBoxLayout(cr)
                cr_layout.setContentsMargins(12, 10, 12, 10)
                cr_layout.setSpacing(10)
                icon = icon_label("book", 20, C['accent'])
                ci = QVBoxLayout()
                name = QLabel(clean_filename(self._last_open.get("filename", "")))
                name.setFont(QFont("Segoe UI", 12))
                name.setStyleSheet(f"color: {C['fg']}; background: transparent;")
                ci.addWidget(name)
                author_name = self._last_open.get("author") or ""
                if author_name:
                    a = QLabel(author_name[:50])
                    a.setFont(QFont("Segoe UI", 11))
                    a.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
                    ci.addWidget(a)
                saved_page = self._last_open.get("page")
                disp = saved_page + 1 if saved_page is not None else "?"
                sub = QLabel(f"LAST READ: P. {disp}")
                sub.setFont(QFont("Segoe UI", 9))
                sub.setStyleSheet(f"color: {C['secondary']}; background: transparent;")
                ci.addWidget(sub)
                cr_layout.addLayout(ci, 1)
                cr.setCursor(Qt.CursorShape.PointingHandCursor)
                cr_data = self._last_open
                cr.mousePressEvent = lambda e, d=cr_data: self._open_continue(d)
                self.scroll_layout.addWidget(cr)

            # Recent Searches section
            if self._recent_searches:
                self.scroll_layout.addSpacing(8)
                sec = QLabel("RECENT SEARCHES")
                sec.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
                sec.setStyleSheet(f"color: {C['secondary']}; background: transparent; letter-spacing: 0.08em; padding-bottom: 4px;")
                self.scroll_layout.addWidget(sec)
                for sq in reversed(self._recent_searches[-5:]):
                    r = QLabel(f"  {sq}")
                    r.setFont(QFont("Segoe UI", 12))
                    r.setStyleSheet(f"color: {C['secondary']}; background: transparent; padding: 4px 0;")
                    r.setCursor(Qt.CursorShape.PointingHandCursor)
                    q_text = sq
                    r.mousePressEvent = lambda e, q=q_text: self._run_recent(q)
                    self.scroll_layout.addWidget(r)

        def _open_continue(self, data):
            open_pdf(data["path"], data.get("page"))
            self.hide()

        def _run_recent(self, q):
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
                nl = QLabel("No results found")
                nl.setFont(QFont("Segoe UI", 13))
                nl.setStyleSheet(f"color: {C['muted']}; background: transparent; padding: 40px 0;")
                nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.scroll_layout.addWidget(nl)
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
                    self.scroll_layout.addSpacing(16)
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
                self._selected_index = 0
                self._highlight_card(0)

        def _highlight_card(self, index):
            for i, c in enumerate(self._result_cards):
                c.setProperty("nav_selected", "true" if i == index else "")
                c.style().unpolish(c)
                c.style().polish(c)

        def _activate_selected(self):
            if 0 <= self._selected_index < len(self._result_cards):
                card = self._result_cards[self._selected_index]
                if hasattr(card, '_open_page'):
                    card._open_page(card._data)

        def eventFilter(self, obj, event):
            if obj is self.search_input and event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Down:
                    if self._result_cards:
                        nxt = min(self._selected_index + 1, len(self._result_cards) - 1)
                        if nxt != self._selected_index:
                            self._selected_index = nxt
                            self._highlight_card(nxt)
                            self.scroll.ensureWidgetVisible(self._result_cards[nxt])
                    return True
                elif event.key() == Qt.Key.Key_Up:
                    if self._result_cards:
                        prv = max(self._selected_index - 1, 0)
                        if prv != self._selected_index:
                            self._selected_index = prv
                            self._highlight_card(prv)
                            self.scroll.ensureWidgetVisible(self._result_cards[prv])
                    return True
                elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._activate_selected()
                    return True
                elif event.key() == Qt.Key.Key_Escape:
                    self.hide()
                    return True
            return super().eventFilter(obj, event)

        def _open_settings(self):
            from .config import load_config, save_config
            cfg = load_config()
            dialog = SettingsDialog(
                cfg.get("hotkey", "ctrl+alt+m"),
                cfg.get("preferred_viewer", "auto"),
                self,
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_hotkey = dialog.combo()
                new_viewer = dialog.selected_viewer()
                cfg["hotkey"] = new_hotkey
                cfg["preferred_viewer"] = new_viewer
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
                logger.info("Hotkey updated: %s, viewer: %s", new_hotkey, new_viewer)

        def closeEvent(self, event):
            save_window_geometry(self.saveGeometry())
            super().closeEvent(event)

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
                self.scroll.verticalScrollBar().setValue(
                    self.scroll.verticalScrollBar().value() + 40
                )
            elif event.key() == Qt.Key.Key_Up:
                self.scroll.verticalScrollBar().setValue(
                    self.scroll.verticalScrollBar().value() - 40
                )
            else:
                super().keyPressEvent(event)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    from pynput import keyboard
    from .config import load_config
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
    app.exec()
