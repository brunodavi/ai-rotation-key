import logging


def key_masked(key):
    if len(key) <= 8:
        return key
    return key[:4] + "..." + key[-4:]


def key_full(key):
    return key


_KEYMASKED = 12
_KEYFULL = 14


def format_key(key, position, total):
    log = logging.getLogger("airkey")
    if log.level >= _KEYFULL:
        return key_full(key)
    if log.level >= _KEYMASKED:
        return key_masked(key)
    return f"{position}/{total}"
