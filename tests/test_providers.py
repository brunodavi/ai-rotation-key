import json
import unittest

from src.providers import (
    create_provider,
    default_base_url,
    nomes_conhecidos,
)


class ProvidersRegistroTests(unittest.TestCase):
    def test_registro_expoe_os_tres_providers_embutidos(self):
        self.assertEqual(nomes_conhecidos(), {"gemini", "openrouter", "opencode-zen"})

    def test_default_base_url_de_cada_provider_e_o_contrato_real(self):
        casos = {
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
            "openrouter": "https://openrouter.ai/api/v1",
            "opencode-zen": "https://opencode.ai/zen/v1",
        }
        for nome, esperada in casos.items():
            with self.subTest(provider=nome):
                self.assertEqual(default_base_url(nome), esperada)

    def test_desconhecido_retorna_none(self):
        self.assertIsNone(default_base_url("fornecedor-x"))
        self.assertIsNone(default_base_url(""))


class ProviderClassesTests(unittest.TestCase):
    def test_cada_provider_exporta_uma_subclasse_de_provider(self):
        from src.providers import gemini, opencode_zen, openrouter
        from src.providers.base import Provider

        for modulo, cls in (
            (gemini, gemini.Gemini),
            (openrouter, openrouter.OpenRouter),
            (opencode_zen, opencode_zen.OpenCodeZen),
        ):
            with self.subTest(provider=cls.__name__):
                self.assertTrue(issubclass(cls, Provider))

    def test_cada_classe_declara_name_e_base_url(self):
        from src.providers import gemini, opencode_zen, openrouter

        for cls, nome, base in (
            (gemini.Gemini, "gemini", "https://generativelanguage.googleapis.com/v1beta/openai"),
            (openrouter.OpenRouter, "openrouter", "https://openrouter.ai/api/v1"),
            (opencode_zen.OpenCodeZen, "opencode-zen", "https://opencode.ai/zen/v1"),
        ):
            with self.subTest(provider=nome):
                self.assertEqual(cls.name, nome)
                self.assertEqual(cls.base_url, base)


class CreateProviderTests(unittest.TestCase):
    def test_create_provider_para_provider_conhecido(self):
        for nome in ("gemini", "openrouter", "opencode-zen"):
            with self.subTest(provider=nome):
                prov = create_provider(nome)
                self.assertEqual(prov.name, nome)
                self.assertTrue(callable(prov.sanitize_request))
                self.assertTrue(callable(prov.sanitize_response))
                self.assertTrue(callable(prov.sanitize_sse_line))

    def test_create_provider_para_desconhecido_usa_base(self):
        from src.providers.base import Provider

        prov = create_provider("prov-x")
        self.assertIsInstance(prov, Provider)

    def test_gemini_remove_chaves_fora_da_whitelist(self):
        dados = {
            "model": "gemini-3.5-flash",
            "messages": [{"role": "user", "content": "oi"}],
            "logprobs": True,
            "user": "fulano",
        }
        limpo = create_provider("gemini").sanitize_request(dados)
        self.assertEqual(set(limpo), {"model", "messages"})

    def test_gemini_normaliza_tools_legado(self):
        legada = {"name": "get_time", "parameters": {"type": "object"}}
        limpo = create_provider("gemini").sanitize_request({
            "model": "m",
            "messages": [{"role": "user", "content": "oi"}],
            "tools": [legada],
        })
        self.assertEqual(limpo["tools"][0]["type"], "function")
        self.assertEqual(limpo["tools"][0]["function"]["name"], "get_time")

    def test_gemini_remove_extra_content(self):
        resp = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "ok",
                    "extra_content": {"google": {"thought_signature": "sig"}},
                }
            }]
        }
        resultado = create_provider("gemini").sanitize_response(resp)
        message = resultado["choices"][0]["message"]
        self.assertEqual(message, {"role": "assistant", "content": "ok"})
        self.assertNotIn("extra_content", message)

    def test_gemini_remove_extra_content_no_sse(self):
        chunk = {
            "choices": [{"delta": {"content": "oi", "extra_content": {"g": {}}}, "index": 0}]
        }
        linha = b"data: " + json.dumps(chunk).encode() + b"\n\n"
        saida = create_provider("gemini").sanitize_sse_line(linha)
        self.assertNotIn(b"extra_content", saida)
        self.assertTrue(saida.startswith(b"data: "))
        self.assertTrue(saida.endswith(b"\n\n"))


if __name__ == "__main__":
    unittest.main()
