import json
import os
import pathlib
import shutil
import unittest
from unittest import mock

from src.providers import default_base_url
from src.utils.config_paths import DEFAULT_PORT, config_path
from src.utils.load_config import load_config


class LoadConfigTests(unittest.TestCase):
    def setUp(self):
        raiz = pathlib.Path(__file__).resolve().parents[1]
        self.scratch = raiz / "tmp" / ".scratch" / "test_load_config"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir(parents=True)
        self.home = self.scratch / "home"
        self.home.mkdir()
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def _escrever(self, conteudo):
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo if isinstance(conteudo, str) else json.dumps(conteudo), encoding="utf-8")
        return path

    def test_carrega_exemplo_gerado_pelo_init(self):
        from src.utils.init_config import init_config

        init_config()
        dados = load_config()
        self.assertEqual(dados["port"], 8792)
        gemini = dados["providers"]["gemini"]
        self.assertEqual(gemini["api-keys"], ["sk-exemplo-1", "sk-exemplo-2"])
        self.assertIn("gemini-3.5-flash", gemini["models"])

    def test_base_url_default_do_gemini_e_resolvida_na_carga(self):
        self._escrever({
            "providers": {
                "gemini": {
                    "api-keys": ["sk-a"],
                    "models": ["gemini-3.5-flash"],
                }
            }
        })
        dados = load_config()
        self.assertEqual(
            dados["providers"]["gemini"]["base-url"],
            "https://generativelanguage.googleapis.com/v1beta/openai",
        )

    def test_base_url_default_do_openrouter_e_resolvida_na_carga(self):
        self._escrever({
            "providers": {
                "openrouter": {
                    "api-keys": ["sk-or-a"],
                    "models": ["poolside/laguna-s-2.1:free"],
                }
            }
        })
        dados = load_config()
        self.assertEqual(
            dados["providers"]["openrouter"]["base-url"],
            "https://openrouter.ai/api/v1",
        )

    def test_base_url_default_do_opencode_zen_e_resolvida_na_carga(self):
        self._escrever({
            "providers": {
                "opencode-zen": {
                    "api-keys": ["sk-zen"],
                    "models": ["laguna-s-2.1-free"],
                }
            }
        })
        dados = load_config()
        self.assertEqual(
            dados["providers"]["opencode-zen"]["base-url"],
            "https://opencode.ai/zen/v1",
        )

    def test_base_url_customizada_preservada(self):
        self._escrever({
            "providers": {
                "minha-caixa": {
                    "base-url": "http://10.0.0.5:8000/v1",
                    "api-keys": ["sk-a"],
                    "models": ["modelo-local"],
                }
            }
        })
        dados = load_config()
        self.assertEqual(dados["providers"]["minha-caixa"]["base-url"], "http://10.0.0.5:8000/v1")

    def test_port_ausente_vira_default(self):
        self._escrever({"providers": {"gemini": {"api-keys": ["sk-a"], "models": ["m"]}}})
        self.assertEqual(load_config()["port"], DEFAULT_PORT)

    def test_port_invalida_levanta_value_error(self):
        for ruim in ("abc", 0, -1, 1.5, None):
            with self.subTest(port=ruim):
                self._escrever({
                    "port": ruim,
                    "providers": {"gemini": {"api-keys": ["sk-a"], "models": ["m"]}},
                })
                with self.assertRaises(ValueError):
                    load_config()

    def test_arquivo_ausente_menciona_init(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            load_config()
        self.assertIn("init", str(ctx.exception))

    def test_json_quebrado_levanta_value_error(self):
        self._escrever("{providers: quebrado")
        with self.assertRaises(ValueError):
            load_config()

    def test_providers_ausente_ou_vazio_levanta_value_error(self):
        for providers in (None, {}, "texto"):
            with self.subTest(providers=providers):
                payload = {} if providers is None else {"providers": providers}
                self._escrever(payload)
                with self.assertRaises(ValueError):
                    load_config()

    def test_provider_com_campos_invalidos_levanta_value_error(self):
        casos = [
            {"api-keys": [], "models": ["m"]},
            {"api-keys": ["sk"], "models": []},
            {"api-keys": "sk-string", "models": ["m"]},
            {"api-keys": [1], "models": ["m"]},
            {"api-keys": ["sk"], "models": ""},
            {"api-keys": ["sk"]},
            {"models": ["m"]},
        ]
        for provider in casos:
            with self.subTest(provider=provider):
                self._escrever({"providers": {"gemini": provider}})
                with self.assertRaises(ValueError):
                    load_config()

    def test_provider_desconhecido_sem_base_url_levanta_value_error(self):
        self._escrever({
            "providers": {"fornecedor-x": {"api-keys": ["sk-a"], "models": ["m"]}}
        })
        with self.assertRaises(ValueError) as ctx:
            load_config()
        self.assertIn("base-url", str(ctx.exception))

    def test_modelo_duplicado_entre_providers_e_permitido_namespaces_unicos(self):
        self._escrever({
            "providers": {
                "gemini": {"api-keys": ["sk-a"], "models": ["comum", "só-gemini"]},
                "openai": {
                    "base-url": "https://api.openai.com/v1",
                    "api-keys": ["sk-b"],
                    "models": ["comum"],
                },
            }
        })
        dados = load_config()
        self.assertEqual(dados["providers"]["gemini"]["models"], ["comum", "só-gemini"])
        self.assertEqual(dados["providers"]["openai"]["models"], ["comum"])

    def test_mapeamento_customizado_validado_e_preservado(self):
        provider = {
            "base-url": "https://gw.exemplo/api",
            "api-keys": ["sk-a"],
            "models": ["m1"],
            "models-endpoint": "/catalogo",
            "path-models": "result.items[].modelId",
            "chat-endpoint": "/v2/chat",
            "auth-header": "X-Key: {api-key}",
        }
        self._escrever({"providers": {"meu-gateway": provider}})
        dados = load_config()
        mapeado = dados["providers"]["meu-gateway"]
        self.assertEqual(mapeado["models-endpoint"], "/catalogo")
        self.assertEqual(mapeado["path-models"], "result.items[].modelId")
        self.assertEqual(mapeado["chat-endpoint"], "/v2/chat")
        self.assertEqual(mapeado["auth-header"], "X-Key: {api-key}")

    def test_mapeamento_sem_campos_nao_aparece_no_dict(self):
        self._escrever({
            "providers": {"gemini": {"api-keys": ["sk-a"], "models": ["m"]}}
        })
        dados = load_config()
        gemini = dados["providers"]["gemini"]
        for campo in ("models-endpoint", "path-models", "chat-endpoint", "auth-header"):
            self.assertNotIn(campo, gemini)

    def test_mapeamento_invalido_levanta_value_error(self):
        casos = [
            {"models-endpoint": ""},
            {"models-endpoint": 42},
            {"path-models": ""},
            {"path-models": 42},
            {"chat-endpoint": "   "},
            {"chat-endpoint": []},
            {"auth-header": "sem placeholder"},
            {"auth-header": "{chave}"},
        ]
        for mapeamento in casos:
            with self.subTest(mapeamento=mapeamento):
                provider = {
                    "base-url": "https://gw.exemplo/api",
                    "api-keys": ["sk-a"],
                    "models": ["m"],
                }
                provider.update(mapeamento)
                self._escrever({"providers": {"meu-gateway": provider}})
                with self.assertRaises(ValueError) as ctx:
                    load_config()
                self.assertIn("mapeamento", str(ctx.exception))

    def test_maps_de_traducao_validados_e_preservados(self):
        provider = {
            "base-url": "https://generativelanguage.googleapis.com/v1beta",
            "api-keys": ["sk-a"],
            "models": ["gemini-3.6-flash"],
            "chat-endpoint": "/models/{model}:generateContent",
            "auth-header": "x-goog-api-key: {api-key}",
            "request-map": {
                "contents[].role": "messages[].role",
                "contents[].parts[].text": "messages[].content",
            },
            "response-map": {
                "choices[0].message.content": "candidates[0].content.parts[0].text",
                "choices[0].finish_reason": "candidates[0].finishReason",
                "usage.prompt_tokens": "usageMetadata.promptTokenCount",
                "usage.completion_tokens": "usageMetadata.candidatesTokenCount",
                "usage.total_tokens": "usageMetadata.totalTokenCount",
            },
            "role-map": {"assistant": "model"},
        }
        self._escrever({"providers": {"gemini-native": provider}})
        dados = load_config()
        traduzido = dados["providers"]["gemini-native"]
        self.assertEqual(
            traduzido["request-map"]["contents[].parts[].text"],
            "messages[].content",
        )
        self.assertEqual(
            traduzido["response-map"]["choices[0].message.content"],
            "candidates[0].content.parts[0].text",
        )
        self.assertEqual(traduzido["role-map"], {"assistant": "model"})

    def test_maps_de_traducao_ausentes_nao_aparecem_no_dict(self):
        self._escrever({
            "providers": {"gemini": {"api-keys": ["sk-a"], "models": ["m"]}}
        })
        dados = load_config()
        gemini = dados["providers"]["gemini"]
        for campo in ("request-map", "response-map", "role-map"):
            self.assertNotIn(campo, gemini)

    def test_maps_de_traducao_invalidos_levanta_value_error(self):
        casos = [
            ("request-map", "texto-solto"),
            ("request-map", 42),
            ("request-map", []),
            ("request-map", {}),
            ("request-map", {"contents[]": ""}),
            ("request-map", {"": "messages[].content"}),
            ("request-map", {"contents[].role": 42}),
            ("response-map", {"a.b": ""}),
            ("role-map", ["assistant"]),
            ("role-map", {"assistant": ""}),
            ("role-map", {"assistant": 42}),
            ("role-map", {"": "model"}),
        ]
        for campo, valor in casos:
            with self.subTest(campo=campo, valor=valor):
                provider = {
                    "base-url": "https://gw.exemplo/api",
                    "api-keys": ["sk-a"],
                    "models": ["m"],
                    campo: valor,
                }
                self._escrever({"providers": {"meu-gateway": provider}})
                with self.assertRaises(ValueError) as ctx:
                    load_config()
                mensagem = str(ctx.exception)
                self.assertIn(campo, mensagem)
                self.assertIn("meu-gateway", mensagem)

    def test_nomes_antigos_do_mapeamento_rejeitados(self):
        for antigo in ("rota-models", "sufixo-chat"):
            with self.subTest(antigo=antigo):
                provider = {
                    "base-url": "https://gw.exemplo/api",
                    "api-keys": ["sk-a"],
                    "models": ["m"],
                    antigo: "/qualquer",
                }
                self._escrever({"providers": {"meu-gateway": provider}})
                with self.assertRaises(ValueError) as ctx:
                    load_config()
                mensagem = str(ctx.exception)
                self.assertIn(antigo, mensagem)
                self.assertIn("endpoint", mensagem)

    def test_formato_antigo_model_keys_rejeitado_com_orientacao(self):
        self._escrever({"model-keys": {"gemini-3.5-flash": ["sk-velha"]}})
        with self.assertRaises(ValueError) as ctx:
            load_config()
        mensagem = str(ctx.exception)
        self.assertIn("model-keys", mensagem)
        self.assertIn("providers", mensagem)

    def test_exclude_models_formato_antigo_rejeitado_com_orientacao(self):
        self._escrever({
            "providers": {
                "gemini": {
                    "api-keys": ["sk-a"],
                    "models": ["m"],
                    "exclude-models": ["*tts*"],
                }
            }
        })
        with self.assertRaises(ValueError) as ctx:
            load_config()
        mensagem = str(ctx.exception)
        self.assertIn("exclude-models", mensagem)
        self.assertIn("filter-models", mensagem)

    def test_filter_models_opcional_e_validado(self):
        casos_invalidos = ("texto", [""], [1], {"a": 1})
        for filtros in casos_invalidos:
            with self.subTest(filtros=filtros):
                self._escrever({
                    "providers": {
                        "gemini": {
                            "api-keys": ["sk-a"],
                            "models": ["m"],
                            "filter-models": filtros,
                        }
                    }
                })
                with self.assertRaises(ValueError):
                    load_config()
        for valido in ([], ["*free*", "!*vision*"]):
            with self.subTest(filtros=valido):
                provider = {"api-keys": ["sk-a"], "models": ["m"]}
                if valido:
                    provider["filter-models"] = valido
                self._escrever({"providers": {"gemini": provider}})
                dados = load_config()
                self.assertEqual(dados["providers"]["gemini"]["filter-models"], valido)

    def test_defaults_conhecem_gemini(self):
        self.assertEqual(
            default_base_url("gemini"),
            "https://generativelanguage.googleapis.com/v1beta/openai",
        )

    def test_defaults_conhecem_openrouter(self):
        self.assertEqual(default_base_url("openrouter"), "https://openrouter.ai/api/v1")

    def test_defaults_conhecem_opencode_zen(self):
        self.assertEqual(default_base_url("opencode-zen"), "https://opencode.ai/zen/v1")

    def test_path_explicito_sobrepoe_default(self):
        alvo = self.scratch / "outro.json"
        alvo.write_text(json.dumps({
            "port": 7000,
            "providers": {"gemini": {"api-keys": ["sk-z"], "models": ["x"]}},
        }), encoding="utf-8")
        dados = load_config(alvo)
        self.assertEqual(dados["port"], 7000)
        self.assertEqual(list(dados["providers"]), ["gemini"])

    def test_config_path_continua_no_lugar_de_sempre(self):
        from src.utils.config_paths import config_path

        self.assertEqual(config_path().name, "config.json")


if __name__ == "__main__":
    unittest.main()
