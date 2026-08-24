import json
import os
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.utils.find_free_port import find_free_port


class MockServer:
    DROP = object()

    def __init__(self):
        self.port = None
        self._server = None
        self._thread = None
        self._rotas = {}

    class _Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, formato, *args):
            pass

        def _consumir(self, method):
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                self.rfile.read(length)
            key = (method, self.path.split("?")[0])
            self.server.requests.append({
                "method": method,
                "path": self.path,
                "headers": dict(self.headers),
                "body": b"",
            })
            fila = self.server.registrations.get(key)
            if not fila:
                self._enviar_json(500, {"error": "mock: sem resposta registrada"})
                return
            resposta = fila.popleft()
            if resposta is MockServer.DROP:
                self.close_connection = True
                return
            if resposta["stream"]:
                self.send_response(resposta["status"])
                headers = dict(resposta["headers"])
                headers.setdefault("Connection", "close")
                for header, valor in headers.items():
                    self.send_header(header, valor)
                self.end_headers()
                self.close_connection = True
                for chunk in resposta["chunks"]:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                return
            corpo = resposta["body"]
            self.send_response(resposta["status"])
            headers = dict(resposta["headers"])
            headers.setdefault("Content-Type", "application/json")
            headers.setdefault("Content-Length", str(len(corpo)))
            for header, valor in headers.items():
                self.send_header(header, valor)
            self.end_headers()
            self.wfile.write(corpo)

        def _enviar_json(self, status, obj):
            corpo = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            self._consumir("GET")

        def do_POST(self):
            self._consumir("POST")

        def do_PUT(self):
            self._consumir("PUT")

        def do_DELETE(self):
            self._consumir("DELETE")

    def start(self, port=None):
        preferida = port or os.environ.get("AI_ROTATION_MOCK_PORT")
        if preferida:
            porta = find_free_port(int(preferida))
        else:
            porta = 0
        self._server = ThreadingHTTPServer(("127.0.0.1", porta), self._Handler)
        self._server.daemon_threads = True
        self._server.registrations = self._rotas
        self._server.requests = []
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def url(self, path="/"):
        return f"http://127.0.0.1:{self.port}{path}"

    def register(self, method, path, status=200, body=b"", headers=None):
        corpo = json.dumps(body).encode("utf-8") if isinstance(body, (dict, list)) else body
        self._fila(method, path).append({
            "status": status,
            "body": corpo,
            "headers": dict(headers or {}),
            "stream": False,
        })

    def register_stream(self, method, path, chunks, status=200, headers=None):
        base = {"Content-Type": "text/event-stream", "Cache-Control": "no-cache"}
        base.update(headers or {})
        self._fila(method, path).append({
            "status": status,
            "headers": base,
            "chunks": list(chunks),
            "stream": True,
        })

    def reset(self):
        self._rotas.clear()
        if self._server is not None:
            self._server.requests.clear()

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join(timeout=5)
            self._server = None
            self._thread = None

    def _fila(self, method, path):
        return self._rotas.setdefault((method.upper(), path.split("?")[0]), deque())
