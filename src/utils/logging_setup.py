import logging
import sys

KEYMASKED = 12
KEYFULL = 14

logging.addLevelName(KEYMASKED, "KEYMASKED")
logging.addLevelName(KEYFULL, "KEYFULL")


def setup_logging(verbose=0):
    if verbose == 0:
        level = logging.INFO
    elif verbose == 1:
        level = logging.DEBUG
    elif verbose == 2:
        level = KEYMASKED
    else:
        level = KEYFULL
    root = logging.getLogger("airkey")
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(handler)
