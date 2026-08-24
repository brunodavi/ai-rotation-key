import json
import os
import pathlib
import shutil
import unittest
from unittest import mock

from src.utils.update_models import sync_models
from tests.mock_server import MockServer


def _payload(*ids):
    return {
        "object": "list",
        "data": [{"id": i, "object": "model", "owned_by": "google"} for i in ids],
    }


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

    def tearDown(self):
        for upstream in (self.upstream_a, self.upstream_b):
            upstream.reset()
            upstream.stop()
        shutil.rmtree(self.scratch, ignore_errors=True)

    def _escrever_config(self, gemini_models=None, gemini_exclude=None):
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
        if gemini_exclude is not None:
            providers["gemini"]["exclude-models"] = gemini_exclude
        caminho = self.home / ".config" / "ai-rotation-key" / "config.json"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            json.dumps({"port": 8792, "providers": providers}), encoding="utf-8"
        )
        return caminho

    def _ler_config(self):
        return json.loads((self.home / ".config" / "ai-rotation-key" / "config.json").read_text(encoding="utf-8"))

    def test_adiciona_faltantes_preservando_ordem(self):
        caminho = self._escrever_config()
        self.upstream_a.register(
            "GET",
            "/v1/models",
            body=_payload("models/m-novo", "models/m-existente", "zzz-outro"),
        )
        self.upstream_b.register("GET", "/v1/models", body=_payload("models/m-b"))
        resultado = sync_models()
        self.assertFalse(resultado.houve_erro)
        self.assertTrue(resultado.salvo)
        rel = resultado.relatorios["gemini"]
        self.assertEqual(rel["adicionados"], ["m-novo", "zzz-outro"])
        self.assertEqual(rel["existentes"], 1)
        self.assertEqual(rel["excluidos"], 0)
        modelos = self._ler_config()["providers"]["gemini"]["models"]
        self.assertEqual(modelos, ["m-existente", "m-novo", "zzz-outro"])
        texto = pathlib.Path(caminho).read_text(encoding="utf-8")
        self.assertTrue(texto.endswith("\n"))

    def test_segunda_rodada_e_idempotente_sem_reescrita(self):
        self._escrever_config()
        resposta_a = _payload("models/m-novo")
        resposta_b = _payload("models/m-b")
        for _ in range(2):
            self.upstream_a.register("GET", "/v1/models", body=dict(resposta_a))
            self.upstream_b.register("GET", "/v1/models", body=dict(resposta_b))
        sync_models()
        antes = (self.home / ".config" / "ai-rotation-key" / "config.json").read_text(encoding="utf-8")
        resultado = sync_models()
        depois = (self.home / ".config" / "ai-rotation-key" / "config.json").read_text(encoding="utf-8")
        self.assertFalse(resultado.houve_erro)
        self.assertEqual(resultado.relatorios["gemini"]["adicionados"], [])
        self.assertFalse(resultado.salvo)
        self.assertEqual(antes, depois)

    def test_exclude_filtra_candidatos_sem_tocar_existentes(self):
        self._escrever_config(gemini_models=["tts-velho"], gemini_exclude=["*tts*"])
        self.upstream_a.register(
            "GET", "/v1/models", body=_payload("tts-novo", "chat-ok", "tts-velho")
        )
        resultado = sync_models(apenas="gemini")
        rel = resultado.relatorios["gemini"]
        self.assertEqual(rel["adicionados"], ["chat-ok"])
        self.assertEqual(rel["excluidos"], 2)
        modelos = self._ler_config()["providers"]["gemini"]["models"]
        self.assertEqual(modelos, ["tts-velho", "chat-ok"])

    def test_apenas_um_provider_nao_toca_os_outros(self):
        self._escrever_config()
        self.upstream_b.register("GET", "/v1/models", body=_payload("models/m-b2"))
        resultado = sync_models(apenas="outro")
        self.assertEqual(list(resultado.relatorios), ["outro"])
        self.assertEqual(len(self.upstream_a.requests), 0)
        self.assertTrue(resultado.salvo)

    def test_apenas_desconhecido_levanta_value_error_com_opcoes(self):
        self._escrever_config()
        with self.assertRaises(ValueError) as ctx:
            sync_models(apenas="fantasma")
        self.assertIn("gemini", str(ctx.exception))
        self.assertIn("outro", str(ctx.exception))

    def test_falha_parcial_continua_e_sinaliza(self):
        self._escrever_config()
        self.upstream_a.register("GET", "/v1/models", MockServer.DROP)
        self.upstream_b.register("GET", "/v1/models", body=_payload("models/m-b2"))
        resultado = sync_models()
        self.assertTrue(resultado.houve_erro)
        self.assertIsNone(resultado.relatorios["gemini"]["status"])
        self.assertIn("erro", resultado.relatorios["gemini"])
        self.assertEqual(resultado.relatorios["outro"]["adicionados"], ["m-b2"])

    def test_status_http_do_upstream_vira_erro_tipado_no_relatorio(self):
        self._escrever_config()
        self.upstream_a.register("GET", "/v1/models", status=401, body={"error": {}})
        resultado = sync_models()
        self.assertTrue(resultado.houve_erro)
        self.assertEqual(resultado.relatorios["gemini"]["status"], 401)


if __name__ == "__main__":
    unittest.main()
