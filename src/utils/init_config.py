import json
from pathlib import Path

from src.utils.config_paths import config_path

EXAMPLE_CONFIG = {
    "model-keys": {"gemini-3.5-flash": ["sk-exemplo-1", "sk-exemplo-2"]},
    "port": 8792,
}


def init_config(path=None):
    if path is None:
        path = config_path()
    path = Path(path)
    if path.exists():
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(EXAMPLE_CONFIG, indent=2) + "\n", encoding="utf-8")
    return path, True
