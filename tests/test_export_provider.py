import json
import os
import pathlib
import shutil
import unittest
from unittest import mock

from src.utils.export_provider import PROVIDER_ID, export_provider


class ExportProviderTests(unittest.TestCase):
    def setUp(self):
        raiz = pathlib.Path(__file__).resolve().parents[1]
        self.scratch = raiz / "tmp" / ".scratch" / "test_export_provider"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir(parents=True)
        self.home = self.scratch / "home"
        (self.home / ".config" / "ai-rotation-key").mkdir(parents=True)
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def _nosso_config(self, providers, port=8792):
        path = self.home / ".config" / "ai-rotation-key" / "config.json"
        path.write_text(
            json.dumps({"providers": providers, "port": port}), encoding="utf-8"
        )
        return path

    @property
    def _opencode_path(self):
        return self.home / ".config" / "opencode" / "config.json"

    def test_cria_config_do_opencode_quando_nao_existe(self):
        self._nosso_config(
            {
                "gemini": {"api-keys": ["sk-1"], "models": ["gemini-3.5-flash"]},
                "openai": {
                    "base-url": "https://api.openai.com/v1",
                    "api-keys": ["sk-2"],
                    "models": ["gpt-4o-mini"],
                },
            },
            port=9000,
        )
        retornado, acao = export_provider()
        self.assertEqual(retornado, self._opencode_path)
        self.assertEqual(acao, "criado")
        dados = json.loads(self._opencode_path.read_text(encoding="utf-8"))
        self.assertEqual(dados["$schema"], "https://opencode.ai/config.json")
        bloco = dados["provider"][PROVIDER_ID]
        self.assertEqual(bloco["npm"], "@ai-sdk/openai-compatible")
        self.assertEqual(bloco["options"]["baseURL"], "http://127.0.0.1:9000/v1")
        self.assertIn("apiKey", bloco["options"])
        self.assertEqual(
            bloco["models"],
            {
                "gemini/gemini-3.5-flash": {"name": "gemini/gemini-3.5-flash"},
                "openai/gpt-4o-mini": {"name": "openai/gpt-4o-mini"},
            },
        )

    def test_adiciona_quando_config_existe_sem_nosso_provider(self):
        self._nosso_config({"gemini": {"api-keys": ["sk-a"], "models": ["m"]}})
        self._opencode_path.parent.mkdir(parents=True, exist_ok=True)
        self._opencode_path.write_text(json.dumps({"provider": {"openai": {}}}), encoding="utf-8")
        _, acao = export_provider()
        self.assertEqual(acao, "adicionado")

    def test_e_idempotente_nao_duplica_provider(self):
        self._nosso_config({"gemini": {"api-keys": ["sk-a"], "models": ["m"]}})
        _, acao1 = export_provider()
        antes = json.loads(self._opencode_path.read_text(encoding="utf-8"))
        _, acao2 = export_provider()
        depois = json.loads(self._opencode_path.read_text(encoding="utf-8"))
        self.assertEqual(acao1, "criado")
        self.assertEqual(acao2, "inalterado")
        self.assertEqual(len(depois["provider"]), 1)
        self.assertEqual(antes["provider"][PROVIDER_ID], depois["provider"][PROVIDER_ID])

    def test_preserva_outros_providers_e_chaves_top_level(self):
        self._nosso_config({"gemini": {"api-keys": ["sk-1"], "models": ["meu-modelo"]}})
        existente = {
            "$schema": "https://opencode.ai/config.json",
            "model": "openai/gpt-x",
            "mcp": {"srv": {"enabled": False}},
            "provider": {
                "openai": {"options": {"apiKey": "sk-outro"}},
                PROVIDER_ID: {"npm": "antigo", "models": {}},
            },
        }
        self._opencode_path.parent.mkdir(parents=True, exist_ok=True)
        self._opencode_path.write_text(json.dumps(existente), encoding="utf-8")

        _, acao = export_provider()

        self.assertEqual(acao, "atualizado")
        dados = json.loads(self._opencode_path.read_text(encoding="utf-8"))
        self.assertEqual(dados["model"], "openai/gpt-x")
        self.assertEqual(dados["mcp"], {"srv": {"enabled": False}})
        self.assertEqual(dados["provider"]["openai"], {"options": {"apiKey": "sk-outro"}})
        nosso = dados["provider"][PROVIDER_ID]
        self.assertNotEqual(nosso, {"npm": "antigo", "models": {}}, "sub-bloco deve ser atualizado")
        self.assertIn("baseURL", nosso["options"])

    def test_atualiza_baseurl_e_models_se_nosso_config_mudou(self):
        self._nosso_config({"gemini": {"api-keys": ["sk-1"], "models": ["velho"]}}, port=8792)
        export_provider()
        self._nosso_config({"gemini": {"api-keys": ["sk-2"], "models": ["novo"]}}, port=9500)
        _, acao = export_provider()
        self.assertEqual(acao, "atualizado")
        bloco = json.loads(self._opencode_path.read_text(encoding="utf-8"))["provider"][PROVIDER_ID]
        self.assertEqual(bloco["options"]["baseURL"], "http://127.0.0.1:9500/v1")
        self.assertEqual(list(bloco["models"]), ["gemini/novo"])

    def test_json_malformado_levanta_value_error_sem_destruir_arquivo(self):
        self._nosso_config({"gemini": {"api-keys": ["sk-1"], "models": ["m"]}})
        self._opencode_path.parent.mkdir(parents=True, exist_ok=True)
        quebrado = "{ provider: "
        self._opencode_path.write_text(quebrado, encoding="utf-8")
        with self.assertRaises(ValueError):
            export_provider()
        self.assertEqual(self._opencode_path.read_text(encoding="utf-8"), quebrado)


if __name__ == "__main__":
    unittest.main()
