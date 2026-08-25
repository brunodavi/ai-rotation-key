import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request

from src.utils.config_paths import DEFAULT_PORT
from src.utils.find_free_port import find_free_port
from src.utils.forward_request import AUTH_PADRAO, forward_request
from src.utils.load_config import load_config
from src.utils.round_robin import RoundRobin
from src.utils.sanitize_request import sanitize_request
from src.utils.sanitize_response import sanitize_response_payload, sanitize_sse_line
from src.utils.signature_cache import SignatureCache
from src.utils.user_agent import USER_AGENT

_CHAT_ROTAS = ("/chat/completions", "/v1/chat/completions")
_HEADERS_HOP_BY_HOP = ("content-length", "transfer-encoding", "content-encoding")
_SUFIXO_CHAT = "/chat/completions"


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
        try:
            provider, modelo_bare = self.server.resolver(modelo)
        except ValueError as exc:
            self._enviar_json(400, {"error": {"message": str(exc)}})
            return
        dados["model"] = modelo_bare
        self.server.signature_cache.inject(dados.get("messages") or [])
        payload = json.dumps(dados).encode("utf-8")
        cfg = self.server.providers[provider]
        url = cfg["base-url"].rstrip("/") + cfg.get("sufixo-chat", _SUFIXO_CHAT)

        if dados.get("stream"):
            self._repassar_stream(provider, payload, url)
            return
        status, corpo, _ = forward_request(
            self.server.round_robin, provider, payload, url=url,
            auth_header=cfg.get("auth-header"),
        )
        try:
            resposta = json.loads(corpo)
            self.server.signature_cache.collect(resposta)
            corpo = json.dumps(sanitize_response_payload(resposta)).encode("utf-8")
        except (json.JSONDecodeError, TypeError):
            pass
        self._enviar_json(status, None, raw=corpo)

    def _repassar_stream(self, provider, payload, url):
        rr = self.server.round_robin
        template = self.server.providers[provider].get("auth-header") or AUTH_PADRAO
        res = None
        for tentativa in range(rr.count(provider)):
            chave = rr.next(provider)
            req = request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": template.format(**{"api-key": chave}),
                    "User-Agent": USER_AGENT,
                },
                method="POST",
            )
            try:
                res = request.urlopen(req, timeout=120)
                break
            except error.HTTPError as exc:
                corpo_erro = exc.read()
                if exc.code == 429 and tentativa < rr.count(provider) - 1:
                    continue
                self._enviar_json(exc.code, None, raw=corpo_erro)
                return
            except (error.URLError, OSError, __import__("http").client.HTTPException) as exc:
                if tentativa >= rr.count(provider) - 1:
                    self._enviar_json(502, {"error": {"message": f"conexão falhou: {exc}"}})
                    return
                continue
        if res is None:
            return
        try:
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
        except (ConnectionResetError, BrokenPipeError, OSError):
            return
        finally:
            res.close()

    def _enviar_json(self, status, obj, raw=None):
        corpo = raw if raw is not None else json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


def build_server(providers, port=0, host="127.0.0.1"):
    model_to_provider = {}
    bare_to_providers = {}
    model_ids = []
    vistos = set()
    for nome, cfg in providers.items():
        for modelo in cfg["models"]:
            namespaced = f"{nome}/{modelo}"
            if namespaced in vistos:
                continue
            vistos.add(namespaced)
            model_ids.append(namespaced)
            model_to_provider[namespaced] = nome
            bare_to_providers.setdefault(modelo, []).append(nome)

    def resolver(pedido):
        alvo = model_to_provider.get(pedido)
        if alvo is not None:
            return alvo, pedido.split("/", 1)[1]
        candidatos = bare_to_providers.get(pedido, [])
        if len(candidatos) == 1:
            return candidatos[0], pedido
        if len(candidatos) > 1:
            opcoes = ", ".join(f"{n}/{pedido}" for n in candidatos)
            raise ValueError(
                f"modelo ambíguo: '{pedido}' existe em vários providers — "
                f"qualifique com um de: {opcoes}"
            )
        raise ValueError(f"modelo não configurado: '{pedido}'")

    server = ThreadingHTTPServer((host, port), ProxyHandler)
    server.providers = providers
    server.round_robin = RoundRobin(
        {nome: cfg["api-keys"] for nome, cfg in providers.items()}
    )
    server.model_to_provider = model_to_provider
    server.model_ids = model_ids
    server.resolver = resolver
    server.signature_cache = SignatureCache()
    return server


def start_server():
    config = load_config()
    porta_config = config.get("port", DEFAULT_PORT)
    porta = find_free_port(porta_config) if porta_config != 0 else 0
    server = build_server(providers=config["providers"], port=porta)
    if porta != porta_config:
        print(f"[aviso] porta {porta_config} ocupada; usando {porta}", flush=True)
    print(
        f"ai-rotation-key em http://127.0.0.1:{server.server_address[1]}/v1 (apenas localhost)",
        flush=True,
    )
    print(f"providers: {', '.join(server.providers)}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
