def fetch_models(base_url, api_key, timeout=30):
    raise NotImplementedError("buscar lista de modelos no upstream")


class FetchModelsError(Exception):
    def __init__(self, motivo, status=None):
        super().__init__(motivo)
        self.status = status
