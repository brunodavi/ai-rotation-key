import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request

from src.utils.config_paths import DEFAULT_PORT
from src.utils.find_free_port import find_free_port
from src.utils.forward_request import DEFAULT_UPSTREAM, forward_request
from src.utils.load_config import load_config
from src.utils.round_robin import RoundRobin
from src.utils.sanitize_request import sanitize_request
from src.utils.sanitize_response import sanitize_response_payload, sanitize_sse_line
from src.utils.signature_cache import SignatureCache

_CHAT_ROTAS = ("/chat/completions", "/v1/chat/completions")
_HEADERS_HOP_BY_HOP = ("content-length", "transfer-encoding", "content-encoding")


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, formato, *args):
        pass

    def do_GET(self):
        if self.path == "/v1/models":
            dados = {
                "object": "list",
                "data": [
                    {"id": modelo, "object": "model", "owned_by": "ai-rotation-key"}
                    for modelo in self.server.model_ids
                ],
            }
            self._enviar_json(200, dados)
            return
        if self.path == "/":
            corpo = b"ai-rotation-key rodando"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
            return
        self._enviar_json(404, {"error": {"message": f"rota desconhecida: {self.path}"}})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        bruto = self.rfile.read(length) if length > 0 else b""
        if self.path.rstrip("/") not in _CHAT_ROTAS:
            self._enviar_json(404, {"error": {"message": f"rota desconhecida: {self.path}"}})
            return
        try:
            dados = json.loads(bruto.decode("utf-8")) if bruto else {}
        except json.JSONDecodeError as exc:
            self._enviar_json(400, {"error": {"message": f"JSON inválido: {exc}"}})
            return

        dados = sanitize_request(dados if isinstance(dados, dict) else {})
        modelo = dados.get("model") or self.server.model_ids[0]
        self.server.signature_cache.inject(dados.get("messages") or [])
        if modelo not in self.server.model_ids:
            self._enviar_json(400, {"error": {"message": f"modelo não configurado: '{modelo}'"}})
            return
        payload = json.dumps(dados).encode("utf-8")

        if dados.get("stream"):
            self._repassar_stream(modelo, payload)
            return
        status, corpo, _ = forward_request(
            self.server.round_robin, modelo, payload, url=self.server.upstream
        )
        try:
            resposta = json.loads(corpo)
            self.server.signature_cache.collect(resposta)
            corpo = json.dumps(sanitize_response_payload(resposta)).encode("utf-8")
        except (json.JSONDecodeError, TypeError):
            pass
        self._enviar_json(status, None, raw=corpo)

    def _repassar_stream(self, modelo, payload):
        rr = self.server.round_robin
        res = None
        for tentativa in range(rr.count(modelo)):
            chave = rr.next(modelo)
            req = request.Request(
                self.server.upstream,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {chave}",
                },
                method="POST",
            )
            try:
                res = request.urlopen(req, timeout=120)
                break
            except error.HTTPError as exc:
                corpo_erro = exc.read()
                if exc.code == 429 and tentativa < rr.count(modelo) - 1:
                    continue
                self._enviar_json(exc.code, None, raw=corpo_erro)
                return
            except (error.URLError, OSError, __import__("http").client.HTTPException) as exc:
                if tentativa >= rr.count(modelo) - 1:
                    self._enviar_json(502, {"error": {"message": f"conexão falhou: {exc}"}})
                    return
                continue
        if res is None:
            return
        self.send_response(200)
        for header, valor in res.headers.items():
            if header.lower() not in _HEADERS_HOP_BY_HOP:
                self.send_header(header, valor)
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        coletor = self.server.signature_cache.collect
        for linha in res:
            self.wfile.write(sanitize_sse_line(linha, collector=coletor))
            self.wfile.flush()
        res.close()

    def _enviar_json(self, status, obj, raw=None):
        corpo = raw if raw is not None else json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


def build_server(model_keys, port=0, upstream=None):
    server = ThreadingHTTPServer(("", port), ProxyHandler)
    server.round_robin = RoundRobin(model_keys)
    server.model_ids = list(model_keys)
    server.upstream = upstream or DEFAULT_UPSTREAM
    server.signature_cache = SignatureCache()
    return server


def start_server():
    config = load_config()
    porta_config = config.get("port", DEFAULT_PORT)
    porta = find_free_port(porta_config) if porta_config != 0 else 0
    server = build_server(model_keys=config["model-keys"], port=porta)
    if porta != porta_config:
        print(f"[aviso] porta {porta_config} ocupada; usando {porta}", flush=True)
    print(f"ai-rotation-key em http://127.0.0.1:{server.server_address[1]}/v1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
