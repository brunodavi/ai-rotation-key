import itertools
import threading


class RoundRobin:
    def __init__(self, model_keys):
        if not isinstance(model_keys, dict) or not model_keys:
            raise ValueError("model_keys deve ser dict não-vazio {modelo: [chaves]}")
        for modelo, chaves in model_keys.items():
            if not isinstance(chaves, list) or not chaves:
                raise ValueError(f"modelo '{modelo}' precisa de lista não-vazia de chaves")
        self._pools = {modelo: itertools.cycle(chaves) for modelo, chaves in model_keys.items()}
        self._lock = threading.Lock()

    def next(self, model):
        with self._lock:
            try:
                return next(self._pools[model])
            except KeyError:
                raise KeyError(f"modelo desconhecido: '{model}'") from None

    def count(self, model):
        raise NotImplementedError("contar chaves do modelo")
