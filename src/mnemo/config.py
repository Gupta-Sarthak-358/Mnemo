import json
import os
from pathlib import Path

localappdata = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
CONFIG_DIR = Path(localappdata) / "Mnemo"
CONFIG_FILE = CONFIG_DIR / "config.json"
DB_PATH = CONFIG_DIR / "mnemo.db"

DEFAULT_CONFIG = {
    "watched_folders": [],
    "hotkey": "ctrl+alt+m",
    "embedding_model": "all-MiniLM-L6-v2",
    "max_results": 8,
    "theme": "light",
    "preferred_viewer": "auto",
    "noise_cleaning": {
        "enabled": True,
        "min_occurrences": 10,
        "max_words": 8,
    },
}


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    ensure_config_dir()
    if CONFIG_FILE.exists():
        data = json.loads(CONFIG_FILE.read_text())
        return {**DEFAULT_CONFIG, **data}
    return dict(DEFAULT_CONFIG)


def save_config(config):
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
