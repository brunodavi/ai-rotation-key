#!/usr/bin/env python3
"""Proxy debugger para ai-rotation-key.

Fica entre opencode e airkey, capturando o que passa sem modificar nada.
Salva samples em tmp/debug-proxy/{timestamp}-{provider}-result.json.

Uso:
    python scripts/proxy-debugger.py
    python scripts/proxy-debugger.py --upstream-port 8792 --listen-port 8793
"""

import argparse
import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config_paths import config_path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "tmp" / "debug-proxy"
HEADERS_HOP_BY_HOP = ("content-length", "transfer-encoding", "content-encoding")


class DebugProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, formato, *args):
        pass

    def do_GET(self):
        self._enviar_json(200, {"status": "debug-proxy", "upstream": self.server.upstream_url})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        bruto = self.rfile.read(length) if length > 0 else b""

        try:
            dados_brutos = json.loads(bruto.decode("utf-8")) if bruto else {}
        except json.JSONDecodeError as exc:
            self._enviar_json(400, {"error": {"message": f"JSON inválido: {exc}"}})
            return

        if not isinstance(dados_brutos, dict):
            dados_brutos = {}

        modelo = dados_brutos.get("model") or "unknown"
        provider = self._resolve_provider(modelo)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        sample = {
            "timestamp": timestamp,
            "provider": provider,
            "model": modelo,
            "request": {"raw": dados_brutos},
            "response": {},
        }

        upstream_url = self.server.upstream_url.rstrip("/") + self.path
        sample["request"]["forwarded_url"] = upstream_url

        status, corpo, headers = self._forward(upstream_url, bruto)

        sample["response"]["status"] = status
        sample["response"]["upstream_headers"] = dict(headers) if headers else {}

        try:
            resposta = json.loads(corpo) if corpo else None
        except (json.JSONDecodeError, TypeError):
            resposta = None

        if resposta is not None:
            sample["response"]["upstream"] = resposta
        else:
            sample["response"]["upstream_raw"] = corpo.decode("utf-8", errors="replace")[:5000]

        self._save_sample(sample, provider, timestamp)

        self.send_response(status)
        for header, valor in (headers or {}).items():
            if header.lower() not in HEADERS_HOP_BY_HOP:
                self.send_header(header, valor)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _resolve_provider(self, model):
        for nome, cfg in self.server.providers.items():
            if model in cfg.get("models", []):
                return nome
            if model.startswith(f"{nome}/"):
                bare = model.split("/", 1)[1]
                if bare in cfg.get("models", []):
                    return nome
        return None

    def _forward(self, url, raw_body):
        headers = {"Content-Type": "application/json"}
        req = request.Request(url, data=raw_body, headers=headers, method="POST")
        try:
            res = request.urlopen(req, timeout=120)
            corpo = res.read()
            return res.status, corpo, res.headers
        except error.HTTPError as exc:
            return exc.code, exc.read(), exc.headers
        except (error.URLError, OSError) as exc:
            return 502, json.dumps({"error": {"message": str(exc)}}).encode("utf-8"), None

    def _save_sample(self, sample, provider, timestamp):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        nome = f"{timestamp}-{provider or 'unknown'}-result.json"
        caminho = OUTPUT_DIR / nome
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2, ensure_ascii=False)
        print(f"[debug-proxy] salvo: {caminho}", flush=True)

    def _enviar_json(self, status, obj):
        corpo = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


def load_config():
    caminho = config_path()
    if not caminho.exists():
        print(f"[erro] config não encontrado: {caminho}", file=sys.stderr)
        sys.exit(1)
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Proxy debugger para ai-rotation-key")
    parser.add_argument("--upstream-port", type=int, default=8792)
    parser.add_argument("--listen-port", type=int, default=8793)
    args = parser.parse_args()

    config = load_config()
    providers = config.get("providers", {})

    upstream_url = f"http://127.0.0.1:{args.upstream_port}"

    server = ThreadingHTTPServer(("127.0.0.1", args.listen_port), DebugProxyHandler)
    server.providers = providers
    server.upstream_url = upstream_url

    print(f"[debug-proxy] ouvindo em http://127.0.0.1:{args.listen_port}")
    print(f"[debug-proxy] upstream: {upstream_url}")
    print(f"[debug-proxy] providers: {', '.join(providers.keys())}")
    print(f"[debug-proxy] samples em: {OUTPUT_DIR}")
    print("[debug-proxy] Ctrl+C para parar\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
