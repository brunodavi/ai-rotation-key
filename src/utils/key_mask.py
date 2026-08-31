def key_index(key):
    return key


def key_masked(key):
    if len(key) <= 8:
        return key
    return key[:4] + "..." + key[-4:]


def key_full(key):
    return key
