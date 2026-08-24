import json
import unittest
import urllib.request

from src.utils.start_server import build_server
from tests.mock_server import MockServer


class HttpServerTests(unittest.TestCase):
    def setUp(self):
        self.upstream = MockServer()
        self.upstream.start()
        self.model_keys = {"gemini-3.1-flash-lite": ["sk-a", "sk-b"]}
        self.server = build_server(
            model_keys=self.model_keys,
            port=0,
            upstream=self.upstream.url("/v1/chat/completions"),
        )
        self.server_thread = __import__("threading").Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.server_thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        self.upstream.reset()
        self.upstream.stop()

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

    def test_post_v1_chat_completions_nao_stream(self):
        self.upstream.register("POST", "/v1/chat/completions", status=200, body={"choices": []})
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.1-flash-lite", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"choices": []})

    def test_rota_legada_sem_prefixo_v1_tambem_funciona(self):
        self.upstream.register("POST", "/v1/chat/completions", status=200, body={"ok": True})
        status, body = self._post(
            "/chat/completions",
            {"model": "gemini-3.1-flash-lite", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": True})

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
        self.upstream.register("POST", "/v1/chat/completions", status=200, body=resposta_com_extra)
        _, body = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.1-flash-lite", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertNotIn(b"extra_content", body)

    def test_get_v1_models_lista_modelos_do_config(self):
        with urllib.request.urlopen(self.base + "/v1/models", timeout=10) as res:
            dados = json.loads(res.read())
        ids = [m["id"] for m in dados["data"]]
        self.assertEqual(ids, ["gemini-3.1-flash-lite"])

    def test_get_raiz_responde_saude(self):
        with urllib.request.urlopen(self.base + "/", timeout=10) as res:
            self.assertEqual(res.status, 200)

    def test_stream_repassa_limpo_ate_done(self):
        chunks = [
            b'data: {"choices":[{"delta":{"content":"1","extra_content":{"g":{}}},"index":0}]}\n\n',
            b"data: [DONE]\n\n",
        ]
        self.upstream.register_stream("POST", "/v1/chat/completions", chunks)
        req = urllib.request.Request(
            self.base + "/v1/chat/completions",
            data=json.dumps({
                "model": "gemini-3.1-flash-lite",
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

    def test_rotaciona_429_atraves_do_servidor(self):
        self.upstream.register("POST", "/v1/chat/completions", status=429, body={"e": 1})
        self.upstream.register("POST", "/v1/chat/completions", status=200, body={"ok": "segunda"})
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.1-flash-lite", "messages": [{"role": "user", "content": "oi"}]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": "segunda"})

    def test_400_passa_direto_com_corpo_do_upstream(self):
        self.upstream.register("POST", "/v1/chat/completions", status=400, body={"erro": "ruim"})
        status, body = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.1-flash-lite", "messages": [{"role": "user", "content": "oi"}]},
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
        self.assertEqual(len(self.upstream.requests), 0)

    def test_rota_desconhecida_da_404_json(self):
        status, body = self._post("/outra/coisa", {"qualquer": 1})
        self.assertEqual(status, 404)

    def test_servidor_binda_apenas_em_localhost_por_padrao(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

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
        self.upstream.register("POST", "/v1/chat/completions", status=200, body=resposta)
        status1, body1 = self._post(
            "/v1/chat/completions",
            {"model": "gemini-3.1-flash-lite", "messages": [{"role": "user", "content": "liste"}]},
        )
        self.assertEqual(status1, 200)
        self.assertNotIn(b"extra_content", body1)

        historico = {
            "model": "gemini-3.1-flash-lite",
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
        self.upstream.register("POST", "/v1/chat/completions", status=200, body={"ok": True})
        status2, _ = self._post("/v1/chat/completions", historico)
        self.assertEqual(status2, 200)
        enviado = json.loads(self.upstream.requests[-1]["body"])
        tool_call = enviado["messages"][1]["tool_calls"][0]
        self.assertEqual(tool_call["extra_content"], {"google": {"thought_signature": "SIG-G"}})

    def test_stream_tambem_coleta_assinatura_para_reinjecao(self):
        chunks = [
            b'data: {"choices":[{"delta":{"tool_calls":[{"id":"call_s1","type":"function","function":{"name":"glob","arguments":"{}"},"extra_content":{"google":{"thought_signature":"SIG-S"}}}]},"index":0}]}\n\n',
            b"data: [DONE]\n\n",
        ]
        self.upstream.register_stream("POST", "/v1/chat/completions", chunks)
        req = urllib.request.Request(
            self.base + "/v1/chat/completions",
            data=json.dumps({
                "model": "gemini-3.1-flash-lite",
                "messages": [{"role": "user", "content": "liste"}],
                "stream": True,
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            recebido = res.read()
        self.assertNotIn(b"extra_content", recebido)

        historico = {
            "model": "gemini-3.1-flash-lite",
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
        self.upstream.register("POST", "/v1/chat/completions", status=200, body={"ok": True})
        self._post("/v1/chat/completions", historico)
        enviado = json.loads(self.upstream.requests[-1]["body"])
        tool_call = enviado["messages"][1]["tool_calls"][0]
        self.assertEqual(tool_call["extra_content"], {"google": {"thought_signature": "SIG-S"}})


if __name__ == "__main__":
    unittest.main()
