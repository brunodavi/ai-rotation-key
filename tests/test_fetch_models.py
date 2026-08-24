import json
import unittest

from src.utils.fetch_models import FetchModelsError, fetch_models
from tests.mock_server import MockServer


def _payload(*ids):
    return {"object": "list", "data": [{"id": i, "object": "model", "owned_by": "google"} for i in ids]}


class FetchModelsTests(unittest.TestCase):
    def setUp(self):
        self.upstream = MockServer()
        self.upstream.start()
        self.url = self.upstream.url("/v1") + "/models"

    def tearDown(self):
        self.upstream.reset()
        self.upstream.stop()

    def _registrar(self, status=200, payload=None, headers=None):
        self.upstream.register("GET", "/v1/models", status=status, body=payload if payload is not None else {}, headers=headers)

    def test_200_parseia_ids_da_resposta_real(self):
        self._registrar(payload=_payload("models/gemini-3.5-flash", "models/gemini-3.1-flash-lite"))
        modelos = fetch_models(self.upstream.url("/v1"), "sk-chave")
        self.assertEqual(modelos, ["gemini-3.5-flash", "gemini-3.1-flash-lite"])

    def test_prefixo_models_e_removido_somente_no_inicio(self):
        self._registrar(payload=_payload(
            "models/gemini-3.5-flash",
            "gpt-4o-mini",
            "moonshotai/kimi-k2",
            "models/models/estranho",
        ))
        modelos = fetch_models(self.upstream.url("/v1"), "sk-chave")
        self.assertEqual(modelos, ["gemini-3.5-flash", "gpt-4o-mini", "moonshotai/kimi-k2", "models/estranho"])

    def test_envia_bearer_com_a_chave_informada(self):
        self._registrar(payload=_payload("m"))
        fetch_models(self.upstream.url("/v1"), "sk-minha-chave")
        auth = self.upstream.requests[-1]["headers"]["Authorization"]
        self.assertEqual(auth, "Bearer sk-minha-chave")

    def test_envia_user_agent_do_projeto_nao_python(self):
        self._registrar(payload=_payload("m"))
        fetch_models(self.upstream.url("/v1"), "sk-chave")
        ua = self.upstream.requests[-1]["headers"].get("User-Agent", "")
        self.assertTrue(ua.startswith("ai-rotation-key/"), f"User-Agent inesperado: {ua!r}")
        self.assertNotIn("Python", ua)

    def test_base_url_com_barra_final_nao_duplica_barra(self):
        self._registrar(payload=_payload("m"))
        modelos = fetch_models(self.upstream.url("/v1") + "/", "sk")
        self.assertEqual(modelos, ["m"])
        self.assertTrue(all(r["path"] == "/v1/models" for r in self.upstream.requests))

    def test_401_vira_fetch_models_error_com_status(self):
        self._registrar(status=401, payload={"error": {"message": "invalid"}})
        with self.assertRaises(FetchModelsError) as ctx:
            fetch_models(self.upstream.url("/v1"), "sk-invalida")
        self.assertEqual(ctx.exception.status, 401)
        self.assertIn("401", str(ctx.exception))

    def test_404_tambem_vira_fetch_models_error_com_status(self):
        self._registrar(status=404, payload={"error": {"message": "não encontrado"}})
        with self.assertRaises(FetchModelsError) as ctx:
            fetch_models(self.upstream.url("/v1"), "sk")
        self.assertEqual(ctx.exception.status, 404)

    def test_conexao_recusada_vira_fetch_models_error_sem_status(self):
        with self.assertRaises(FetchModelsError) as ctx:
            fetch_models("http://127.0.0.1:9/v1", "sk")
        self.assertIsNone(ctx.exception.status)

    def test_drop_de_conexao_vira_fetch_models_error(self):
        self.upstream.register("GET", "/v1/models", MockServer.DROP)
        with self.assertRaises(FetchModelsError):
            fetch_models(self.upstream.url("/v1"), "sk")

    def test_payload_malformado_levanta_erro_claro(self):
        self._registrar(status=200, payload={"inesperado": True})
        with self.assertRaises(FetchModelsError):
            fetch_models(self.upstream.url("/v1"), "sk")


def urllib_error_sem_rota():
    return unittest.case._Outcome(None) if False else None


if __name__ == "__main__":
    unittest.main()
