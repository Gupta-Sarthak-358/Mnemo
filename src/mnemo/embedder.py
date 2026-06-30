import logging
import sys
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_model = None
_model_name = None
_model_loading = False
_lock = threading.Lock()
MAX_TOKENS = 400


def _get_bundled_model_path(name: str):
    """Return bundled model path if available, else None."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
        candidates = [
            base / "_internal" / "models" / name,
            base / "models" / name,
        ]
    else:
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "models" / name,
        ]
    for local in candidates:
        if local.is_dir() and (local / "model.safetensors").is_file():
            return str(local)
    return None


def load_model(model_name: str):
    global _model, _model_name, _model_loading
    _model_loading = True
    with _lock:
        if _model is None or _model_name != model_name:
            from sentence_transformers import SentenceTransformer
            local_path = _get_bundled_model_path(model_name)
            if local_path:
                logger.info("Loading bundled model from %s", local_path)
                _model = SentenceTransformer(local_path)
            else:
                logger.info("Downloading embedding model (first time only)...")
                print("\nDownloading embedding model (first time only)...")
                _model = SentenceTransformer(model_name)
            _model_name = model_name
            logger.info("Model loaded: %s", model_name)
    _model_loading = False
    return _model


def get_model():
    return _model


def is_model_ready():
    return _model is not None and not _model_loading


def get_model_name():
    return _model_name


def safe_embed(text: str):
    model = get_model()
    if model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")
    tokens = model.tokenize([text])["input_ids"][0]
    if len(tokens) > MAX_TOKENS:
        ratio = MAX_TOKENS / len(tokens)
        char_limit = int(len(text) * ratio * 1.1)
        text = text[:char_limit].rsplit(" ", 1)[0]
    embedding = model.encode(text, normalize_embeddings=True).tolist()
    return embedding, text


def embed_batch(texts):
    model = get_model()
    if model is None:
        raise RuntimeError("Model not loaded.")
    safe_texts = []
    for t in texts:
        tokens = model.tokenize([t])["input_ids"][0]
        if len(tokens) > MAX_TOKENS:
            ratio = MAX_TOKENS / len(tokens)
            char_limit = int(len(t) * ratio * 1.1)
            t = t[:char_limit].rsplit(" ", 1)[0]
        safe_texts.append(t)
    embeddings = model.encode(safe_texts, normalize_embeddings=True).tolist()
    return list(zip(embeddings, safe_texts))
