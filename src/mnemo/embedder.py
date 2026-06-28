import logging
import threading

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model = None
_model_name = None
_lock = threading.Lock()
MAX_TOKENS = 400


def load_model(model_name: str):
    global _model, _model_name
    with _lock:
        if _model is None or _model_name != model_name:
            logger.info("Loading embedding model: %s", model_name)
            _model = SentenceTransformer(model_name)
            _model_name = model_name
            logger.info("Model loaded: %s", model_name)
    return _model


def get_model():
    return _model


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
