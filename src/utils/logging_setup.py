import logging
import sys

KEYDEBUG = 9
KEYMASKED = 8
KEYFULL = 7

logging.addLevelName(KEYDEBUG, "KEYDEBUG")
logging.addLevelName(KEYMASKED, "KEYMASKED")
logging.addLevelName(KEYFULL, "KEYFULL")


def _keydebug(self, msg, *args, **kwargs):
    if self.isEnabledFor(KEYDEBUG):
        self._log(KEYDEBUG, msg, args, **kwargs)


def _keymasked(self, msg, *args, **kwargs):
    if self.isEnabledFor(KEYMASKED):
        self._log(KEYMASKED, msg, args, **kwargs)


def _keyfull(self, msg, *args, **kwargs):
    if self.isEnabledFor(KEYFULL):
        self._log(KEYFULL, msg, args, **kwargs)


logging.Logger.keydebug = _keydebug
logging.Logger.keymasked = _keymasked
logging.Logger.keyfull = _keyfull


def setup_logging(verbose=0):
    if verbose == 0:
        level = logging.INFO
    elif verbose == 1:
        level = logging.DEBUG
    elif verbose == 2:
        level = KEYDEBUG
    else:
        level = KEYFULL
    root = logging.getLogger("airkey")
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(handler)
