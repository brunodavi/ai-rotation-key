import logging


class _ListWriter:
    def __init__(self, lst):
        self._list = lst

    def write(self, s):
        self._list.append(s)

    def flush(self):
        pass


def make_log_capture(level=logging.DEBUG):
    """Retorna (handler, restore_fn, text_fn) para capturar output do logger 'airkey'."""
    root = logging.getLogger("airkey")
    original_level = root.level
    original_handlers = root.handlers[:]
    log_output = []
    handler = logging.StreamHandler(_ListWriter(log_output))
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(level)

    def restore():
        root.setLevel(original_level)
        root.handlers = original_handlers

    def text():
        handler.flush()
        return "".join(log_output)

    return handler, restore, text
