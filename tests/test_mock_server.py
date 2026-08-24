import json
import os
import unittest
import urllib.error
import urllib.request
from unittest import mock

from tests.mock_server import MockServer


class MockServerTests(unittest.TestCase):
    def setUp(self):
        self.servidor = MockServer()
        self.servidor.start()

    def tearDown(self):
        self.servidor.reset()
        self.servidor.stop()

    def _request(self, path, data=None, method=None, headers=None):
        req = urllib.request.Request(self.servidor.url(path), data=data, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status, dict(res.headers), res.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def test_register_responde_exatamente_o_registrado(self):
        self.servidor.register("POST", "/v1/chat", status=201, body={"ok": True}, headers={"X-Marca": "sim"})
        status, headers, body = self._request("/v1/chat", data=b"{}", method="POST")
        self.assertEqual(status, 201)
        self.assertEqual(headers["X-Marca"], "sim")
        self.assertEqual(json.loads(body), {"ok": True})
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_fila_429_entao_200_consumida_em_ordem(self):
        self.servidor.register("POST", "/r", status=429, body={"erro": "cota"})
        self.servidor.register("POST", "/r", status=200, body={"ok": 2})
        s1, _, b1 = self._request("/r", data=b"1", method="POST")
        s2, _, b2 = self._request("/r", data=b"2", method="POST")
        self.assertEqual((s1, s2), (429, 200))
        self.assertEqual(json.loads(b2), {"ok": 2})

    def test_stream_chega_chunks_na_ordem_com_flush(self):
        chunks = [b"data: a\n\n", b"data: b\n\n", b"data: [DONE]\n\n"]
        self.servidor.register_stream("POST", "/sse", chunks)
        req = urllib.request.Request(self.servidor.url("/sse"), data=b"{}", method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            recebido = b"".join(line for line in res)
        self.assertEqual(recebido, b"".join(chunks))

    def test_drop_fecha_conexao_sem_resposta(self):
        self.servidor.register("GET", "/cai", MockServer.DROP)
        with self.assertRaises((urllib.error.URLError, ConnectionError, OSError)):
            self._request("/cai")

    def test_reset_limpa_filas_e_rota_nova_da_500(self):
        self.servidor.register("GET", "/x", status=200, body=b"velho")
        self.servidor.reset()
        status, _, body = self._request("/x")
        self.assertEqual(status, 500)
        self.assertIn(b"sem resposta registrada", body)

    def test_dois_servidores_simultaneos_sem_colisao(self):
        outro = MockServer()
        outro.start()
        try:
            self.assertNotEqual(self.servidor.port, outro.port)
            outro.register("GET", "/s", body=b"outro")
            with urllib.request.urlopen(outro.url("/s"), timeout=10) as res:
                self.assertEqual(res.read(), b"outro")
        finally:
            outro.stop()

    def test_env_fixa_a_porta_preferida_quando_livre(self):
        outro = MockServer()
        with mock.patch.dict(os.environ, {"AI_ROTATION_MOCK_PORT": "28991"}):
            outro.start()
            try:
                self.assertEqual(outro.port, 28991)
            finally:
                outro.reset()
                outro.stop()

    def test_body_lido_antes_de_responder_mantendo_keep_alive(self):
        self.servidor.register("POST", "/eco", status=200, body=b"fim1")
        self.servidor.register("POST", "/eco", status=200, body=b"fim2")
        s1, _, _ = self._request("/eco", data=b'{"grande": "' + b"x" * 5000 + b'"}', method="POST")
        s2, _, b2 = self._request("/eco", data=b"{}", method="POST")
        self.assertEqual((s1, s2), (200, 200))
        self.assertEqual(b2, b"fim2")


if __name__ == "__main__":
    unittest.main()
