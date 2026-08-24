class MockServer:
    DROP = object()

    def __init__(self):
        self.port = None

    def start(self, port=None):
        raise NotImplementedError("subir servidor fake")

    def register(self, method, path, status=200, body=b"", headers=None):
        raise NotImplementedError("registrar rota as-is")

    def register_stream(self, method, path, chunks, status=200, headers=None):
        raise NotImplementedError("registrar rota streaming")

    def reset(self):
        raise NotImplementedError("limpar registros")

    def stop(self):
        raise NotImplementedError("desligar servidor")
