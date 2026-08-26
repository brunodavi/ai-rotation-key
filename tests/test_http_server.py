import io
import json
import threading
import unittest
import urllib.error
import urllib.request

from src.utils.start_server import ProxyHandler, build_server
from tests.mock_server import MockServer


class HttpServerTests(unittest.TestCase):
    def setUp(self):
        self.upstream_a = MockServer()
        self.upstream_a.start()
        self.upstream_b = MockServer()
        self.upstream_b.start()
        self.providers = {
            "gemini": {
                "base-url": self.upstream_a.url("/v1"),
                "api-keys": ["sk-a1", "sk-a2"],
                "models": ["gemini-3.5-flash", "gemini-3.1-flash-lite"],
            },
            "outro": {
                "base-url": self.upstream_b.url("/v1"),
                "api-keys": ["sk-b1"],
                "models": ["modelo-outro"],
            },
        }
        self.server = build_server(providers=self.providers, port=0)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        for upstream in (self.upstream_a, self.upstream_b):
            upstream.reset()
            upstream.stop()

    @property
    def base(self):
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def _post(self, path, payload):
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def _registro(self, modelo="gemini-3.5-flash", status=200, body=None, stream_chunks=None):
        alvo = self.upstream_a if modelo.startswith("gemini") else self.upstream_b
        if stream_chunks is not None:
            alvo.register_stream("POST", "/v1/chat/completions", stream_chunks)
        else:
            alvo.register("POST", "/v1/chat/completions", status=status, body=body if body is not None else {"choices": []})
        return alvo

    def test_post_v1_chat_completions_nao_stream(self):
        self._registro(body={"choices": []})
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"choices": []})

    def test_rota_legada_sem_prefixo_v1_tambem_funciona(self):
        self._registro(body={"ok": True})
        status, body = self._post(
            "/chat/completions",
            {"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": True})

    def test_cada_modelo_vai_pro_upstream_do_seu_provider(self):
        self.upstream_a.register("POST", "/v1/chat/completions", status=200, body={"de": "gemini"})
        self.upstream_b.register("POST", "/v1/chat/completions", status=200, body={"de": "outro"})
        _, body_a = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "oi"}]},
        )
        _, body_b = self._post(
            "/v1/chat/completions",
            {"model": "modelo-outro", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(json.loads(body_a), {"de": "gemini"})
        self.assertEqual(json.loads(body_b), {"de": "outro"})

    def test_rotacao_e_independente_por_provider(self):
        self.upstream_a.register("POST", "/v1/chat/completions", status=429, body={"e": 1})
        self.upstream_a.register("POST", "/v1/chat/completions", status=200, body={"ok": "a2"})
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": "a2"})
        auths = [r["headers"]["Authorization"] for r in self.upstream_a.requests]
        self.assertEqual(auths, ["Bearer sk-a1", "Bearer sk-a2"])
        self.assertEqual(len(self.upstream_b.requests), 0, "provider B não deveria ser tocado")

    def test_resposta_nao_stream_vem_sanitizada(self):
        resposta_com_extra = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "ok",
                    "extra_content": {"google": {"thought_signature": "x"}},
                }
            }]
        }
        self._registro(body=resposta_com_extra)
        _, body = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertNotIn(b"extra_content", body)

    def test_get_v1_models_lista_uniao_na_ordem_dos_providers(self):
        with urllib.request.urlopen(self.base + "/v1/models", timeout=10) as res:
            dados = json.loads(res.read())
        ids = [m["id"] for m in dados["data"]]
        self.assertEqual(ids, [
            "gemini/gemini-3.5-flash",
            "gemini/gemini-3.1-flash-lite",
            "outro/modelo-outro",
        ])

    def test_request_prefixado_remove_o_prefixo_antes_do_upstream(self):
        self.upstream_b.register("POST", "/v1/chat/completions", status=200, body={"de": "outro"})
        status, _ = self._post(
            "/v1/chat/completions",
            {"model": "outro/modelo-outro", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 200)
        enviado = json.loads(self.upstream_b.requests[-1]["body"])
        self.assertEqual(enviado["model"], "modelo-outro")

    def test_modelo_com_slash_proprio_recebe_namespace_e_upstream_ve_inteiro(self):
        self.providers["openrouter"] = {
            "base-url": self.upstream_a.url("/or"),
            "api-keys": ["sk-o1"],
            "models": ["poolside/laguna:free"],
        }
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        self.server = build_server(providers=self.providers, port=0)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.upstream_a.register("POST", "/or/chat/completions", status=200, body={"ok": 1})
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "openrouter/poolside/laguna:free", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 200)
        enviado = json.loads(self.upstream_a.requests[-1]["body"])
        self.assertEqual(enviado["model"], "poolside/laguna:free")

    def test_mesmo_modelo_em_dois_providers_e_aceito_no_build(self):
        providers = {
            "a": {
                "base-url": self.upstream_a.url("/v1"),
                "api-keys": ["sk-a"],
                "models": ["comum"],
            },
            "b": {
                "base-url": self.upstream_b.url("/v1"),
                "api-keys": ["sk-b"],
                "models": ["comum"],
            },
        }
        server = build_server(providers=providers, port=0)
        server.server_close()
        ids = server.model_ids
        self.assertEqual(sorted(ids), ["a/comum", "b/comum"])

    def test_nome_pelado_ambiguo_da_400_pedindo_qualificacao(self):
        self.providers["outro"]["models"].append("gemini-3.5-flash")
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        self.server = build_server(providers=self.providers, port=0)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 400)
        texto = body.decode()
        self.assertIn("gemini/", texto)
        self.assertIn("outro/", texto)

    def test_gateway_customizado_usa_sufixo_chat_e_template_auth(self):
        self.providers["gw"] = {
            "base-url": self.upstream_b.url("/gw"),
            "api-keys": ["sk-gw1", "sk-gw2"],
            "models": ["m-custom"],
            "chat-endpoint": "/v2/chat",
            "auth-header": "X-Key: {api-key}",
        }
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        self.server = build_server(providers=self.providers, port=0)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        self.upstream_b.register("POST", "/gw/v2/chat", status=200, body={"de": "custom"})
        status, _ = self._post(
            "/v1/chat/completions",
            {"model": "gw/m-custom", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 200)
        enviado = json.loads(self.upstream_b.requests[-1]["body"])
        self.assertEqual(enviado["model"], "m-custom")
        self.assertEqual(self.upstream_b.requests[-1]["headers"].get("X-Key"), "sk-gw1")

        chunks = [b'data: {"choices":[{"delta":{"content":"1"}}]}\n\n', b"data: [DONE]\n\n"]
        self.upstream_b.register_stream("POST", "/gw/v2/chat", chunks)
        status, recebido = self._post(
            "/v1/chat/completions",
            {"model": "gw/m-custom", "messages": [{"role": "user", "content": "oi"}],
             "stream": True},
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            self.upstream_b.requests[-1]["headers"].get("X-Key"),
            self.upstream_b.requests[0]["headers"].get("X-Key"),
        )

    def test_provider_com_traducao_converte_request_e_response(self):
        self.providers["nat"] = {
            "base-url": self.upstream_b.url("/native"),
            "api-keys": ["sk-n1"],
            "models": ["gemini-3.6-flash"],
            "chat-endpoint": "/models/{model}:generateContent",
            "auth-header": "x-goog-api-key: {api-key}",
            "request-map": {
                "contents[].role": "messages[].role",
                "contents[].parts[0].text": "messages[].content",
            },
            "response-map": {
                "choices[0].message.content": "candidates[0].content.parts[0].text",
                "choices[0].finish_reason": "candidates[0].finishReason",
                "usage.total_tokens": "usageMetadata.totalTokenCount",
            },
            "role-map": {"assistant": "model"},
        }
        self._reiniciar_servidor()
        self.upstream_b.register("POST", "/native/models/gemini-3.6-flash:generateContent", status=200, body={
            "candidates": [{
                "content": {"parts": [{"text": "OLA"}], "role": "model"},
                "finishReason": "STOP",
                "index": 0,
            }],
            "usageMetadata": {"promptTokenCount": 5, "totalTokenCount": 42},
        })
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "nat/gemini-3.6-flash", "messages": [
                {"role": "user", "content": "oi"},
                {"role": "assistant", "content": "tudo bem"},
                {"role": "user", "content": "confirma?"},
            ]},
        )
        self.assertEqual(status, 200)
        enviado = json.loads(self.upstream_b.requests[-1]["body"])
        self.assertEqual(enviado["contents"], [
            {"role": "user", "parts": [{"text": "oi"}]},
            {"role": "model", "parts": [{"text": "tudo bem"}]},
            {"role": "user", "parts": [{"text": "confirma?"}]},
        ])
        self.assertNotIn("messages", enviado)
        self.assertNotIn("model", enviado)
        cabecalhos = self.upstream_b.requests[-1]["headers"]
        self.assertEqual(cabecalhos.get("x-goog-api-key"), "sk-n1")
        self.assertNotIn("Authorization", cabecalhos)
        resposta = json.loads(body)
        self.assertEqual(resposta["object"], "chat.completion")
        self.assertEqual(resposta["choices"], [{
            "message": {"role": "assistant", "content": "OLA"},
            "finish_reason": "stop",
        }])
        self.assertEqual(resposta["usage"], {"total_tokens": 42})

    def test_provider_com_traducao_converte_stream_com_done_sintetico(self):
        self.providers["nat"] = {
            "base-url": self.upstream_b.url("/native"),
            "api-keys": ["sk-n1"],
            "models": ["gemini-3.6-flash"],
            "chat-endpoint": "/models/{model}:streamGenerateContent?alt=sse",
            "auth-header": "x-goog-api-key: {api-key}",
            "request-map": {
                "contents[].role": "messages[].role",
                "contents[].parts[0].text": "messages[].content",
            },
            "response-map": {
                "choices[0].message.content": "candidates[0].content.parts[0].text",
                "choices[0].finish_reason": "candidates[0].finishReason",
            },
            "role-map": {"assistant": "model"},
        }
        self._reiniciar_servidor()
        self.upstream_b.register_stream(
            "POST",
            "/native/models/gemini-3.6-flash:streamGenerateContent?alt=sse",
            [
                b'data: {"candidates": [{"content": {"parts": [{"text": "1"}], "role": "model"}, "index": 0}]}\n\n',
                b'data: {"candidates": [{"content": {"parts": [{"text": ", 2"}], "role": "model"}, "finishReason": "STOP", "index": 0}]}\n\n',
            ],
        )
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "nat/gemini-3.6-flash", "messages": [{"role": "user", "content": "conte"}],
             "stream": True},
        )
        self.assertEqual(status, 200)
        linhas = [l for l in body.decode("utf-8").split("\n\n") if l.startswith("data:")]
        self.assertEqual(linhas[-1], "data: [DONE]")
        chunks = [json.loads(l[len("data: "):]) for l in linhas[:-1]]
        self.assertEqual(chunks[0]["object"], "chat.completion.chunk")
        self.assertEqual(chunks[0]["choices"][0]["delta"]["content"], "1")
        self.assertEqual(chunks[1]["choices"][0]["delta"]["content"], ", 2")
        self.assertEqual(chunks[1]["choices"][0]["finish_reason"], "stop")

    def test_erro_do_upstream_traduzido_passa_cru_sem_traducao(self):
        self.providers["nat"] = {
            "base-url": self.upstream_b.url("/native"),
            "api-keys": ["sk-n1"],
            "models": ["gemini-3.6-flash"],
            "chat-endpoint": "/models/{model}:generateContent",
            "auth-header": "x-goog-api-key: {api-key}",
            "request-map": {
                "contents[].role": "messages[].role",
                "contents[].parts[0].text": "messages[].content",
            },
            "response-map": {
                "choices[0].message.content": "candidates[0].content.parts[0].text",
            },
        }
        self._reiniciar_servidor()
        erro_native = {
            "error": {"code": 400, "message": "Role 'assistant' is not supported.",
                      "status": "INVALID_ARGUMENT"},
        }
        self.upstream_b.register(
            "POST", "/native/models/gemini-3.6-flash:generateContent",
            status=400, body=erro_native,
        )
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "nat/gemini-3.6-flash", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body), erro_native)

    def _reiniciar_servidor(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        self.server = build_server(providers=self.providers, port=0)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def test_stream_com_cliente_desconectado_nao_propaga_erro(self):
        """opencode pode abortar o stream a qualquer momento — handler engole e segue."""
        chunks = [b'data: {"choices":[{"delta":{"content":"x"}}]}\n\n', b"data: [DONE]\n\n"]
        self.upstream_a.register_stream("POST", "/v1/chat/completions", chunks)

        class ClienteFugiu(ProxyHandler):
            def __init__(self):
                pass

            def send_response(self, *args):
                pass

            def send_header(self, chave, valor):
                pass

            def end_headers(self):
                raise ConnectionResetError(104, "Connection reset by peer")

            def log_message(self, *args):
                pass

        handler = ClienteFugiu()
        handler.server = self.server
        handler.command = "POST"
        handler.request_version = "HTTP/1.1"
        handler.client_address = ("127.0.0.1", 0)
        handler.wfile = io.BytesIO()

        handler._repassar_stream(
            "gemini", b"{}", self.upstream_a.url("/v1/chat/completions")
        )

    def test_get_raiz_responde_saude(self):
        with urllib.request.urlopen(self.base + "/", timeout=10) as res:
            self.assertEqual(res.status, 200)

    def test_stream_repassa_limpo_ate_done(self):
        chunks = [
            b'data: {"choices":[{"delta":{"content":"1","extra_content":{"g":{}}},"index":0}]}\n\n',
            b"data: [DONE]\n\n",
        ]
        self._registro(stream_chunks=chunks)
        req = urllib.request.Request(
            self.base + "/v1/chat/completions",
            data=json.dumps({
                "model": "gemini-3.5-flash",
                "messages": [{"role": "user", "content": "oi"}],
                "stream": True,
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            recebido = res.read()
        self.assertNotIn(b"extra_content", recebido)
        self.assertTrue(recebido.endswith(b"data: [DONE]\n\n"))

    def test_stream_e_nao_stream_enviam_user_agent_do_projeto(self):
        corpo = {"choices": [{"message": {"role": "assistant", "content": "oi"}}]}
        self._registro(body=corpo)
        self._post("/v1/chat/completions", {
            "model": "gemini-3.5-flash",
            "messages": [{"role": "user", "content": "oi"}],
        })
        ua_nao_stream = self.upstream_a.requests[-1]["headers"].get("User-Agent", "")
        chunks = [b'data: {"choices":[{"delta":{"content":"1"}}]}\n\n', b"data: [DONE]\n\n"]
        self._registro(stream_chunks=chunks)
        self._post("/v1/chat/completions", {
            "model": "gemini-3.5-flash",
            "messages": [{"role": "user", "content": "oi"}],
            "stream": True,
        })
        ua_stream = self.upstream_a.requests[-1]["headers"].get("User-Agent", "")
        for ua in (ua_nao_stream, ua_stream):
            self.assertTrue(ua.startswith("ai-rotation-key/"), f"User-Agent inesperado: {ua!r}")
            self.assertNotIn("Python", ua)

    def test_400_passa_direto_com_corpo_do_upstream(self):
        self._registro(status=400, body={"erro": "ruim"})
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body), {"erro": "ruim"})

    def test_modelo_fora_do_config_da_400_sem_ir_ao_upstream(self):
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "desconhecido", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 400)
        self.assertIn(b"desconhecido", body)
        self.assertEqual(len(self.upstream_a.requests), 0)
        self.assertEqual(len(self.upstream_b.requests), 0)

    def test_rota_desconhecida_da_404_json(self):
        status, body = self._post("/outra/coisa", {"qualquer": 1})
        self.assertEqual(status, 404)

    def test_servidor_binda_apenas_em_localhost_por_padrao(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_modelo_duplicado_entre_providers_nao_recusado_no_build(self):
        duplicados = {
            "a": {"base-url": "http://x/v1", "api-keys": ["k"], "models": ["mesmo"]},
            "b": {"base-url": "http://y/v1", "api-keys": ["k"], "models": ["mesmo"]},
        }
        server = build_server(providers=duplicados)
        server.server_close()
        self.assertEqual(sorted(server.model_ids), ["a/mesmo", "b/mesmo"])

    def test_assinatura_de_tool_call_e_reinjetada_no_proximo_request(self):
        resposta = {
            "choices": [{
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": " ",
                    "tool_calls": [{
                        "id": "call_g1",
                        "type": "function",
                        "function": {"name": "glob", "arguments": "{}"},
                        "extra_content": {"google": {"thought_signature": "SIG-G"}},
                    }],
                },
            }]
        }
        self._registro(body=resposta)
        status1, body1 = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "liste"}]},
        )
        self.assertEqual(status1, 200)
        self.assertNotIn(b"extra_content", body1)

        historico = {
            "model": "gemini-3.5-flash",
            "messages": [
                {"role": "user", "content": "liste"},
                {
                    "role": "assistant",
                    "content": " ",
                    "tool_calls": [{
                        "id": "call_g1",
                        "type": "function",
                        "function": {"name": "glob", "arguments": "{}"},
                    }],
                },
                {"role": "tool", "tool_call_id": "call_g1", "content": "[]"},
            ],
        }
        self._registro(body={"ok": True})
        status2, _ = self._post("/v1/chat/completions", historico)
        self.assertEqual(status2, 200)
        enviado = json.loads(self.upstream_a.requests[-1]["body"])
        tool_call = enviado["messages"][1]["tool_calls"][0]
        self.assertEqual(tool_call["extra_content"], {"google": {"thought_signature": "SIG-G"}})

    def test_stream_tambem_coleta_assinatura_para_reinjecao(self):
        chunks = [
            b'data: {"choices":[{"delta":{"tool_calls":[{"id":"call_s1","type":"function","function":{"name":"glob","arguments":"{}"},"extra_content":{"google":{"thought_signature":"SIG-S"}}}]},"index":0}]}\n\n',
            b"data: [DONE]\n\n",
        ]
        self._registro(stream_chunks=chunks)
        req = urllib.request.Request(
            self.base + "/v1/chat/completions",
            data=json.dumps({
                "model": "gemini-3.5-flash",
                "messages": [{"role": "user", "content": "liste"}],
                "stream": True,
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            res.read()
        historico = {
            "model": "gemini-3.5-flash",
            "messages": [
                {"role": "user", "content": "liste"},
                {
                    "role": "assistant",
                    "content": " ",
                    "tool_calls": [{
                        "id": "call_s1",
                        "type": "function",
                        "function": {"name": "glob", "arguments": "{}"},
                    }],
                },
            ],
        }
        self._registro(body={"ok": True})
        self._post("/v1/chat/completions", historico)
        enviado = json.loads(self.upstream_a.requests[-1]["body"])
        tool_call = enviado["messages"][1]["tool_calls"][0]
        self.assertEqual(tool_call["extra_content"], {"google": {"thought_signature": "SIG-S"}})


if __name__ == "__main__":
    unittest.main()
