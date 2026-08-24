import os
from pathlib import Path

DEFAULT_PORT = 8792


def config_dir() -> Path:
    return Path(os.environ["HOME"]) / ".config" / "ai-rotation-key"


def config_path() -> Path:
    return config_dir() / "config.json"


def opencode_config_path() -> Path:
    return Path(os.environ["HOME"]) / ".config" / "opencode" / "config.json"
