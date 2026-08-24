import os
import subprocess
from pathlib import Path


def edit_config(path=None):
    if path is None:
        path = Path(os.environ["HOME"]) / ".config" / "ai-rotation-key" / "config.json"
    editor = os.environ.get("EDITOR") or "vi"
    return subprocess.run([editor, str(path)])
