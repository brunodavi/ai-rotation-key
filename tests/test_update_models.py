import json
import os
import pathlib
import shutil
import unittest
from unittest import mock

from src.utils.update_models import sync_models
from tests.mock_server import MockServer


def _payload(*ids):
    return {"object": "list", "data": [{"id": i, "object": "model", "owned_by": "google"} for i in ids]}


class SyncModelsTests(unittest.TestCase):
    def setUp(self):
        raiz = pathlib.Path(__file__).resolve().parents[1]
        self.scratch = raiz / "tmp" / ".scratch" / "test_update_models"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir(parents=True)
        self.home = self.scratch / "home"
        self.home.mkdir()
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

        self.upstream_a = MockServer()
        self.upstream_a.start()
        self.upstream_b = MockServer()
        self.upstream_b.start()
        self.config_path = self.home / ".config" / "ai-rotation-key" / "config.json"
        self._escrever_config()

    def tearDown(self):
        for upstream in (self.upstream_a, self.upstream_b):
            upstream.reset()
            upstream.stop()
        shutil.rmtree(self.scratch, ignore_errors=True)

    def _escrever_config(self, gemini_models=None):
        providers = {
            "gemini": {
                "base-url": self.upstream_a.url("/v1"),
                "api-keys": ["sk-a1", "sk-a2"],
                "models": gemini_models if gemini_models is not None else ["m-existente"],
            },
            "outro": {
                "base-url": self.upstream_b.url("/v1"),
                "api-keys": ["sk-b1"],
                "exclude-models": ["*proibido*"],
                "models": ["m-b"],
            },
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"port": 8792, "providers": providers}), encoding="utf-8"
        )

    def _ler_config(self):
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def test_adiciona_faltantes_preservando_ordem(self):
        self.upstream_a.register(
            "GET",
            "/v1/models",
            payload=_payload("models/m-novo", "models/m-existente", "zzz-outro"),
        )
        relatorios, houve_erro = sync_models()
        self.assertFalse(houve_erro)
        rel = relatorios["gemini"]
        self.assertEqual(rel["adicionados"], ["m-novo", "zzz-outro"])
        self.assertEqual(rel["existentes"], 1)
        modelos = self._ler_config()["providers"]["gemini"]["models"]
        self.assertEqual(modelos, ["m-existente", "m-novo", "zzz-outro"])

    def test_segunda_rodada_e_idempotente_sem_reescrita(self):
        self.upstream_a.register("GET", "/v1/models", payload=_payload("models/m-novo"))
        sync_models()
        antes = self.config_path.read_text(encoding="utf-8")
        relatorios, houve_erro = sync_models()
        depois = self.config_path.read_text(encoding="utf-8")
        self.assertFalse(houve_erro)
        self.assertEqual(relatorios["gemini"]["adicionados"], [])
        self.assertEqual(antes, depois)

    def test_exclude_filtra_candidatos_sem_tocar_existentes(self):
        self._escrever_config(gemini_models=["tts-velho"])
        self.upstream_a.register(
            "GET", "/v1/models", payload=_payload("tts-novo", "chat-ok", "tts-velho")
        )
        relatorios, _ = sync_models(apenas="gemini")
        rel = relatorios["gemini"]
        self.assertEqual(rel["adicionados"], ["chat-ok"])
        self.assertGreaterEqual(rel["excluidos"], 1)
        modelos = self._ler_config()["providers"]["gemini"]["models"]
        self.assertIn("tts-velho", modelos, "existente que casa com exclude não pode ser removido")

    def test_apenas_um_provider_nao_toca_os_outros(self):
        self.upstream_b.register("GET", "/v1/models", payload=_payload("m-b2"))
        relatorios, _ = sync_models(apenas="outro")
        self.assertEqual(list(relatorios), ["outro"])
        self.assertEqual(len(self.upstream_a.requests), 0)

    def test_apenas_desconhecido_levanta_value_error_com_opcoes(self):
        with self.assertRaises(ValueError) as ctx:
            sync_models(apenas="fantasma")
        self.assertIn("gemini", str(ctx.exception))
        self.assertIn("outro", str(ctx.exception))

    def test_falha_parcial_continua_e_sinaliza(self):
        self.upstream_a.register("GET", "/v1/models", MockServer.DROP)
        self.upstream_b.register("GET", "/v1/models", payload=_payload("m-b2"))
        relatorios, houve_erro = sync_models()
        self.assertTrue(houve_erro)
        self.assertIsNone(relatorios["gemini"]["status"])
        self.assertIn("erro", relatorios["gemini"])
        self.assertEqual(relatorios["outro"]["adicionados"], ["m-b2"])

    def test_status_http_do_upstream_vira_erro_tipado_no_relatorio(self):
        self.upstream_a.register("GET", "/v1/models", status=401, body={"error": {}})
        relatorios, houve_erro = sync_models()
        self.assertTrue(houve_erro)
        self.assertEqual(relatorios["gemini"]["status"], 401)


if __name__ == "__main__":
    unittest.main()
