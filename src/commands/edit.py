from src.utils.config_paths import opencode_config_path
from src.utils.edit_config import edit_config


def run(args):
    if getattr(args, "opencode", False):
        return edit_config(opencode_config_path())
    return edit_config()
