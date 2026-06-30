import hashlib
import logging
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import fitz

logger = logging.getLogger(__name__)

OCR_AVAILABLE = False
OCR_QUALITY_THRESHOLD = 0.5


def _bundled_tesseract():
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
        candidates = [
            base / "_internal" / "tesseract" / "tesseract.exe",
            base / "tesseract" / "tesseract.exe",
        ]
    else:
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "tesseract" / "tesseract.exe",
        ]
    for exe in candidates:
        if exe.is_file():
            return str(exe)
    return None


def check_ocr():
    global OCR_AVAILABLE
    tesseract = shutil.which("tesseract")
    if tesseract is None:
        tesseract = _bundled_tesseract()
    if tesseract is None:
        common = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if common.exists():
            tesseract = str(common)
    if tesseract is not None:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract
        except ImportError:
            pass
        OCR_AVAILABLE = True
        return True
    logger.warning(
        "Tesseract not found. Scanned PDFs will be skipped. "
        "Install with: winget install TesseractOCR (Windows) "
        "or apt install tesseract-ocr (Linux) "
        "or brew install tesseract (macOS)"
    )
    return False


def assess_page_quality(text):
    if not text or not text.strip():
        return 0.0

    text = text.strip()
    length = len(text)
    if length == 0:
        return 0.0

    alpha_chars = sum(1 for c in text if c.isalpha())
    alpha_ratio = alpha_chars / max(length, 1)

    printable = sum(1 for c in text if c.isprintable())
    printable_ratio = printable / max(length, 1)

    words = text.split()
    avg_word_len = sum(len(w) for w in words) / max(len(words), 1) if words else 0

    garbage_pattern = re.compile(r"(.)\1{4,}")
    garbage_ratio = len("".join(garbage_pattern.findall(text))) / max(length, 1)
    garbage_penalty = 1.0 - min(garbage_ratio * 2, 1.0)

    spaces = text.count(" ")
    whitespace_ratio = spaces / max(length, 1)

    score = 0.0
    score += min(length / 500, 1.0) * 0.25
    score += alpha_ratio * 0.30
    score += printable_ratio * 0.15
    score += min(avg_word_len / 6, 1.0) * 0.10
    score += garbage_penalty * 0.10
    score += min(whitespace_ratio * 10, 1.0) * 0.10

    return round(min(max(score, 0.0), 1.0), 4)


def is_ocr_garbage(text):
    if not text or not text.strip():
        return True
    text = text.strip()
    if len(text) < 10:
        return True
    non_alnum = sum(1 for c in text if not c.isalnum() and not c.isspace())
    if non_alnum / max(len(text), 1) > 0.4:
        return True
    weird = sum(1 for c in text if ord(c) > 127)
    if weird / max(len(text), 1) > 0.3:
        return True
    return False


def hash_page_text(text):
    return hashlib.sha256(text.strip().encode()).hexdigest()


def strip_headers_footers(pages_text):
    if len(pages_text) < 5:
        return pages_text

    candidates = Counter()
    for text in pages_text:
        lines = text.strip().split("\n")
        if lines:
            candidates[lines[0].strip()] += 1
        if len(lines) > 1:
            candidates[lines[-1].strip()] += 1

    threshold = max(3, int(len(pages_text) * 0.7))
    repeated = {line for line, count in candidates.items() if count >= threshold and len(line) < 100}

    if not repeated:
        return pages_text

    cleaned = []
    for text in pages_text:
        lines = text.split("\n")
        while lines and lines[0].strip() in repeated:
            lines.pop(0)
        while lines and lines[-1].strip() in repeated:
            lines.pop()
        cleaned.append("\n".join(lines))
    return cleaned


def parse_pdf(path):
    pages = []
    try:
        doc = fitz.open(path)
        raw_texts = []
        for page_num, page in enumerate(doc):
            raw_texts.append(page.get_text())
        doc.close()

        cleaned_texts = strip_headers_footers(raw_texts)

        for page_num, text in enumerate(cleaned_texts):
            quality = assess_page_quality(text)
            if quality < OCR_QUALITY_THRESHOLD:
                pages.append({
                    "page_num": page_num,
                    "text": "",
                    "quality": quality,
                    "page_hash": "",
                    "ocr_needed": True,
                })
            else:
                pages.append({
                    "page_num": page_num,
                    "text": text,
                    "quality": quality,
                    "page_hash": hash_page_text(text),
                    "ocr_needed": False,
                })
        return pages, len(pages)
    except Exception as e:
        logger.error("Failed to parse PDF %s: %s", path, e)
        return [], 0


MAX_OCR_PIXELS = 50_000_000
MAX_OCR_TILE_HEIGHT = 8000
OCR_TILE_OVERLAP = 200
OCR_DPI = 200


def _ocr_image_safe(img):
    """OCR an image, tiling if too tall to avoid Tesseract's dimension limit."""
    import pytesseract
    from PIL import Image
    width, height = img.size
    if height <= MAX_OCR_TILE_HEIGHT:
        return pytesseract.image_to_string(img)
    texts = []
    y = 0
    while y < height:
        tile = img.crop((0, y, width, min(y + MAX_OCR_TILE_HEIGHT, height)))
        text = pytesseract.image_to_string(tile)
        texts.append(text)
        y += MAX_OCR_TILE_HEIGHT - OCR_TILE_OVERLAP
    return "\n".join(texts)


def ocr_page(path, page_num):
    if not OCR_AVAILABLE:
        return ""
    try:
        import fitz
        from PIL import Image
        import io

        doc = fitz.open(path)
        page = doc[page_num]
        rect = page.rect

        dpi = OCR_DPI
        width = int(rect.width * dpi / 72)
        height = int(rect.height * dpi / 72)
        pixels = width * height
        if pixels > MAX_OCR_PIXELS:
            dpi = max(72, int(dpi * (MAX_OCR_PIXELS / pixels) ** 0.5))

        pix = page.get_pixmap(dpi=dpi)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        text = _ocr_image_safe(image)
        doc.close()
        if is_ocr_garbage(text):
            logger.warning("OCR garbage detected for %s page %d", path, page_num)
            return ""
        return text
    except Exception as e:
        logger.error("OCR failed for %s page %d: %s", path, page_num, e)
    return ""


def get_pdf_metadata(path):
    try:
        doc = fitz.open(path)
        meta = doc.metadata or {}
        doc.close()
        author = (meta.get("author") or "").strip()
        return {"author": author}
    except Exception as e:
        logger.error("Failed to read metadata from %s: %s", path, e)
        return {}


def parse_txt(path):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        quality = assess_page_quality(text)
        pg_hash = hash_page_text(text)
        return [{
            "page_num": 0,
            "text": text,
            "quality": quality,
            "page_hash": pg_hash,
            "ocr_needed": False,
        }], 1
    except Exception as e:
        logger.error("Failed to parse TXT %s: %s", path, e)
        return [], 0
