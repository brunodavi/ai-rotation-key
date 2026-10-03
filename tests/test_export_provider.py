import contextlib
import io
import json
import logging
import os
import pathlib
import shutil
import unittest
from unittest import mock

from src.utils.export_provider import PROVIDER_ID, export_provider
from tests._helpers import make_log_capture


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
        self._handler, self._restore_log, self._log_text = make_log_capture()

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)
        self._restore_log()

    def _nosso_config(self, providers, port=8792):
        path = self.home / ".config" / "ai-rotation-key" / "config.json"
        path.write_text(
            json.dumps({"providers": providers, "port": port}), encoding="utf-8"
        )
        return path

    @property
    def _opencode_path(self):
        # V1 e V2 leem o mesmo arquivo; muda só a forma do bloco.
        return self.home / ".config" / "opencode" / "opencode.json"

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
        retornado, acao = export_provider(harness="opencode")
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

    def test_name_do_modelo_com_slash_colapsa_para_dois_niveis(self):
        self._nosso_config(
            {
                "openrouter": {
                    "api-keys": ["sk-1"],
                    "models": ["poolside/laguna-s-2.1:free"],
                },
            },
            port=9000,
        )
        export_provider(harness="opencode")
        bloco = json.loads(self._opencode_path.read_text(encoding="utf-8"))["provider"][PROVIDER_ID]
        self.assertEqual(
            bloco["models"],
            {"openrouter/poolside/laguna-s-2.1:free": {"name": "openrouter/laguna-s-2.1:free"}},
        )

    def test_avisa_quando_nomes_de_exibicao_colidem(self):
        self._nosso_config(
            {
                "openrouter": {
                    "api-keys": ["sk-1"],
                    "models": ["vendor-a/tool-x", "vendor-b/tool-x"],
                },
            },
            port=9000,
        )
        _, acao = export_provider(harness="opencode")
        self.assertEqual(acao, "criado")
        texto = self._log_text()
        self.assertIn("se repete", texto.lower())
        self.assertIn("openrouter/tool-x", texto)
        self.assertIn("openrouter/vendor-a/tool-x", texto)
        self.assertIn("openrouter/vendor-b/tool-x", texto)

    def test_sem_colisao_nao_imprime_aviso(self):
        self._nosso_config(
            {
                "gemini": {"api-keys": ["sk-1"], "models": ["m"]},
            },
            port=9000,
        )
        export_provider(harness="opencode")
        self.assertNotIn("aviso", self._log_text().lower())
        export_provider(harness="opencode")
        self.assertNotIn("aviso", self._log_text().lower())

    def test_adiciona_quando_config_existe_sem_nosso_provider(self):
        self._nosso_config({"gemini": {"api-keys": ["sk-a"], "models": ["m"]}})
        self._opencode_path.parent.mkdir(parents=True, exist_ok=True)
        self._opencode_path.write_text(json.dumps({"provider": {"openai": {}}}), encoding="utf-8")
        _, acao = export_provider(harness="opencode")
        self.assertEqual(acao, "adicionado")

    def test_e_idempotente_nao_duplica_provider(self):
        self._nosso_config({"gemini": {"api-keys": ["sk-a"], "models": ["m"]}})
        _, acao1 = export_provider(harness="opencode")
        antes = json.loads(self._opencode_path.read_text(encoding="utf-8"))
        _, acao2 = export_provider(harness="opencode")
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

        _, acao = export_provider(harness="opencode")

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
        export_provider(harness="opencode")
        self._nosso_config({"gemini": {"api-keys": ["sk-2"], "models": ["novo"]}}, port=9500)
        _, acao = export_provider(harness="opencode")
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
            export_provider(harness="opencode")
        self.assertEqual(self._opencode_path.read_text(encoding="utf-8"), quebrado)


class ExportOpencode2Tests(unittest.TestCase):
    """Formato V2: arquivo `opencode.json`, chave `providers` e bloco nativo (package/settings)."""

    def setUp(self):
        raiz = pathlib.Path(__file__).resolve().parents[1]
        self.scratch = raiz / "tmp" / ".scratch" / "test_export_opencode2"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir(parents=True)
        self.home = self.scratch / "home"
        (self.home / ".config" / "ai-rotation-key").mkdir(parents=True)
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self._handler, self._restore_log, self._log_text = make_log_capture()

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)
        self._restore_log()

    def _nosso_config(self, providers, port=9000):
        path = self.home / ".config" / "ai-rotation-key" / "config.json"
        path.write_text(
            json.dumps({"providers": providers, "port": port}), encoding="utf-8"
        )
        return path

    @property
    def _path(self):
        return self.home / ".config" / "opencode" / "opencode.json"

    @property
    def _legacy_path(self):
        # config.json é o nome antigo: os dois binários ainda leem, mas não é onde exportamos.
        return self.home / ".config" / "opencode" / "config.json"

    def _dados(self):
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _gemini(self):
        return {"gemini": {"api-keys": ["sk-1"], "models": ["gemini-3.5-flash"]}}

    def test_padrao_grava_no_opencode_json_com_formato_v2(self):
        self._nosso_config(self._gemini(), port=9000)
        retornado, acao = export_provider()
        self.assertEqual(retornado, self._path)
        self.assertEqual(acao, "criado")
        dados = self._dados()
        self.assertEqual(dados["$schema"], "https://opencode.ai/config.json")
        bloco = dados["providers"][PROVIDER_ID]
        self.assertEqual(bloco["package"], "@opencode/ai/providers/openai-compatible")
        self.assertEqual(bloco["settings"]["baseURL"], "http://127.0.0.1:9000/v1")
        self.assertIn("apiKey", bloco["settings"])
        self.assertNotIn("npm", bloco)
        self.assertNotIn("options", bloco)
        self.assertEqual(
            bloco["models"],
            {"gemini/gemini-3.5-flash": {"name": "gemini/gemini-3.5-flash"}},
        )

    def test_padrao_nao_toca_no_config_json_legado(self):
        self._nosso_config(self._gemini())
        self._legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legado = {"provider": {"openai": {"npm": "antigo"}}}
        self._legacy_path.write_text(json.dumps(legado), encoding="utf-8")

        export_provider()

        self.assertEqual(
            json.loads(self._legacy_path.read_text(encoding="utf-8")), legado,
            "export não pode alterar o config.json legado",
        )
        self.assertIn(PROVIDER_ID, self._dados()["providers"])

    def test_harness_opencode_v1_grava_na_chave_provider_do_mesmo_arquivo(self):
        self._nosso_config(self._gemini())
        retornado, acao = export_provider(harness="opencode")
        self.assertEqual(retornado, self._path)
        self.assertEqual(acao, "criado")
        dados = self._dados()
        bloco = dados["provider"][PROVIDER_ID]
        self.assertEqual(bloco["npm"], "@ai-sdk/openai-compatible")
        self.assertEqual(bloco["options"]["baseURL"], "http://127.0.0.1:9000/v1")
        self.assertNotIn("providers", dados, "export V1 não pode criar a chave nativa V2")
        self.assertFalse(self._legacy_path.exists())

    def test_troca_de_harness_remove_a_entrada_antiga_do_outro_namespace(self):
        self._nosso_config(self._gemini())
        export_provider(harness="opencode")
        export_provider()

        dados = self._dados()
        self.assertNotIn(PROVIDER_ID, dados.get("provider", {}))
        self.assertIn(PROVIDER_ID, dados["providers"])

        export_provider(harness="opencode")
        dados = self._dados()
        self.assertIn(PROVIDER_ID, dados["provider"])
        self.assertNotIn(PROVIDER_ID, dados["providers"])

    def test_preserva_mcp_e_demais_chaves_do_arquivo_v2(self):
        self._nosso_config(self._gemini())
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existente = {
            "$schema": "https://opencode.ai/config.json",
            "model": "openai/gpt-x",
            "mcp": {"servers": {"ai-memory": {"type": "remote", "url": "http://127.0.0.1:1/mcp"}}},
            "providers": {
                "openai": {"settings": {"apiKey": "sk-outro"}},
                PROVIDER_ID: {"package": "antigo", "models": {}},
            },
        }
        self._path.write_text(json.dumps(existente), encoding="utf-8")

        _, acao = export_provider()

        self.assertEqual(acao, "atualizado")
        dados = self._dados()
        self.assertEqual(dados["model"], "openai/gpt-x")
        self.assertEqual(dados["mcp"], existente["mcp"])
        self.assertEqual(dados["providers"]["openai"], {"settings": {"apiKey": "sk-outro"}})
        self.assertEqual(
            dados["providers"][PROVIDER_ID]["package"],
            "@opencode/ai/providers/openai-compatible",
        )

    def test_segunda_execucao_fica_inalterado(self):
        self._nosso_config(self._gemini())
        _, acao1 = export_provider()
        _, acao2 = export_provider()
        self.assertEqual(acao1, "criado")
        self.assertEqual(acao2, "inalterado")
        self.assertEqual(len(self._dados()["providers"]), 1)

    def test_harness_desconhecido_levanta_value_error(self):
        self._nosso_config(self._gemini())
        with self.assertRaises(ValueError):
            export_provider(harness="opencode3")


if __name__ == "__main__":
    unittest.main()
