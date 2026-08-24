import unittest

from src.providers import default_base_url, nomes_conhecidos


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


if __name__ == "__main__":
    unittest.main()
