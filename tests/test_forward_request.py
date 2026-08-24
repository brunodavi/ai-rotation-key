import json
import unittest

from src.utils.forward_request import DEFAULT_UPSTREAM, forward_request
from src.utils.round_robin import RoundRobin
from tests.mock_server import MockServer


class ForwardRequestTests(unittest.TestCase):
    def setUp(self):
        self.upstream = MockServer()
        self.upstream.start()
        self.url = self.upstream.url("/v1/chat/completions")
        self.payload = json.dumps({"model": "m", "messages": []}).encode()

    def tearDown(self):
        self.upstream.reset()
        self.upstream.stop()

    def _rr(self, chaves):
        return RoundRobin({"modelo": chaves})

    def test_200_na_primeira_chave_nao_tenta_segunda(self):
        rr = self._rr(["sk-a", "sk-b"])
        self.upstream.register("POST", "/v1/chat/completions", status=200, body={"ok": 1})
        status, body, headers = forward_request(rr, "modelo", self.payload, url=self.url)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": 1})
        self.assertEqual(len(self.upstream.requests), 1)

    def test_429_rotaciona_e_autorizacao_troca_por_chave(self):
        rr = self._rr(["sk-a", "sk-b"])
        self.upstream.register("POST", "/v1/chat/completions", status=429, body={"e": 1})
        self.upstream.register("POST", "/v1/chat/completions", status=200, body={"ok": 2})
        status, body, _ = forward_request(rr, "modelo", self.payload, url=self.url)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": 2})
        auth1 = self.upstream.requests[0]["headers"]["Authorization"]
        auth2 = self.upstream.requests[1]["headers"]["Authorization"]
        self.assertEqual(auth1, "Bearer sk-a")
        self.assertEqual(auth2, "Bearer sk-b")

    def test_pool_esgotado_em_429_devolve_ultimo(self):
        rr = self._rr(["sk-a", "sk-b"])
        rota = "POST /v1/chat/completions"
        self.upstream.register("POST", "/v1/chat/completions", status=429, body={"e": 1})
        self.upstream.register("POST", "/v1/chat/completions", status=429, body={"e": 2})
        status, body, _ = forward_request(rr, "modelo", self.payload, url=self.url)
        self.assertEqual(status, 429)
        self.assertEqual(json.loads(body), {"e": 2})

    def test_400_nao_rotaciona_e_preserva_fila(self):
        rr = self._rr(["sk-a", "sk-b"])
        self.upstream.register("POST", "/v1/chat/completions", status=400, body={"erro": "request ruim"})
        self.upstream.register("POST", "/v1/chat/completions", status=200, body={"sobrou": True})
        status, body, _ = forward_request(rr, "modelo", self.payload, url=self.url)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body), {"erro": "request ruim"})
        self.assertEqual(len(self.upstream.requests), 1, "não deveria tentar segunda chave")

    def test_404_de_modelo_morto_nao_rotaciona(self):
        rr = self._rr(["sk-a", "sk-b"])
        self.upstream.register("POST", "/v1/chat/completions", status=404, body={"erro": "modelo morto"})
        status, _, _ = forward_request(rr, "modelo", self.payload, url=self.url)
        self.assertEqual(status, 404)
        self.assertEqual(len(self.upstream.requests), 1)

    def test_drop_de_conexao_rotaciona_para_proxima_chave(self):
        rr = self._rr(["sk-a", "sk-b"])
        self.upstream.register("POST", "/v1/chat/completions", MockServer.DROP)
        self.upstream.register("POST", "/v1/chat/completions", status=200, body={"ok": "depois do drop"})
        status, body, _ = forward_request(rr, "modelo", self.payload, url=self.url)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": "depois do drop"})
        self.assertEqual(len(self.upstream.requests), 2)

    def test_conexao_recusada_em_todas_devolve_502_json(self):
        rr = self._rr(["sk-a", "sk-b"])
        status, body, _ = forward_request(
            rr, "modelo", self.payload, url="http://127.0.0.1:9/closed"
        )
        self.assertEqual(status, 502)
        self.assertIn(b"error", body)

    def test_envia_user_agent_do_projeto_nao_python(self):
        rr = self._rr(["sk-a"])
        self.upstream.register("POST", "/v1/chat/completions", status=200, body={"ok": 1})
        forward_request(rr, "modelo", self.payload, url=self.url)
        ua = self.upstream.requests[0]["headers"].get("User-Agent", "")
        self.assertTrue(ua.startswith("ai-rotation-key/"), f"User-Agent inesperado: {ua!r}")
        self.assertNotIn("Python", ua)

    def test_default_upstream_e_o_endpoint_openai_compativel_do_gemini(self):
        self.assertEqual(
            DEFAULT_UPSTREAM,
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        )


if __name__ == "__main__":
    unittest.main()
