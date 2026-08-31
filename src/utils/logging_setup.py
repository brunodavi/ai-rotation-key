import logging
import sys


def setup_logging(verbose=0):
    level = logging.INFO if verbose == 0 else logging.DEBUG
    root = logging.getLogger("airkey")
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(handler)
