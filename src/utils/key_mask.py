def mask_key(key):
    if len(key) <= 4:
        return key[:2] + "**"
    return key[:2] + "*" * (len(key) - 4) + key[-2:]
