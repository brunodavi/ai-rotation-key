import json
from pathlib import Path

from src.utils.config_paths import config_path

EXEMPLO_CONFIG = {
    "port": 8792,
    "providers": {
        "gemini": {
            "api-keys": ["sk-exemplo-1", "sk-exemplo-2"],
            "filter-models": [
                "!*tts*",
                "!*image*",
                "!*embedding*",
                "!veo-*",
                "!*lyria*",
                "!*robotics*",
                "!*native-audio*",
                "!*live*",
                "!aqa",
                "!antigravity*",
                "!*computer-use*",
                "!*deep-research*",
            ],
            "models": ["gemini-3.5-flash", "gemini-3.1-flash-lite"],
        }
    },
}


def init_config(path=None):
    if path is None:
        path = config_path()
    path = Path(path)
    if path.exists():
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(EXEMPLO_CONFIG, indent=2) + "\n", encoding="utf-8")
    return path, True
