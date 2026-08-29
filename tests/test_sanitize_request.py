import unittest

from src.utils.sanitize_request import sanitize_request


class SanitizeRequestTests(unittest.TestCase):
    def test_remove_chaves_fora_da_whitelist(self):
        dados = {
            "model": "gemini-3.5-flash",
            "messages": [{"role": "user", "content": "oi"}],
            "logprobs": True,
            "user": "fulano",
            "n": 3,
        }
        limpo = sanitize_request(dados)
        self.assertEqual(set(limpo), {"model", "messages"})
        self.assertEqual(limpo["model"], "gemini-3.5-flash")

    def test_mantem_chaves_permitidas_com_valores_intactos(self):
        dados = {
            "model": "m",
            "messages": [{"role": "user", "content": "oi"}],
            "temperature": 0.7,
            "max_tokens": 100,
            "top_p": 0.9,
            "stream": True,
            "stop": ["\n"],
            "seed": 42,
        }
        limpo = sanitize_request(dados)
        for chave, valor in dados.items():
            self.assertEqual(limpo[chave], valor)

    def test_mensagens_ausentes_ou_vazias_ganham_fallback(self):
        self.assertEqual(
            sanitize_request({"model": "m"})["messages"],
            [{"role": "user", "content": "Hello"}],
        )
        self.assertEqual(
            sanitize_request({"model": "m", "messages": []})["messages"],
            [{"role": "user", "content": "Hello"}],
        )

    def test_content_falso_vira_espaco(self):
        mensagens = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": None},
            {"role": "user"},
            {"role": "user", "content": "real"},
        ]
        saida = sanitize_request({"model": "m", "messages": mensagens})["messages"]
        self.assertEqual(saida[0]["content"], " ")
        self.assertEqual(saida[1]["content"], " ")
        self.assertEqual(saida[2]["content"], " ")
        self.assertEqual(saida[3]["content"], "real")

    def test_tool_formato_legado_e_normalizada(self):
        legada = {"name": "get_time", "description": "hora atual", "parameters": {"type": "object"}}
        limpo = sanitize_request({"model": "m", "tools": [legada]})
        self.assertEqual(
            limpo["tools"],
            [{
                "type": "function",
                "function": {
                    "name": "get_time",
                    "parameters": {"type": "object"},
                    "description": "hora atual",
                },
            }],
        )

    def test_tool_moderna_passa_intocada(self):
        moderna = {
            "type": "function",
            "function": {"name": "f", "parameters": {}, "description": "d"},
        }
        limpo = sanitize_request({"model": "m", "tools": [moderna]})
        self.assertIs(limpo["tools"][0], moderna)

    def test_tools_mistas_descartam_nao_dict(self):
        mistas = [
            "lixo",
            {"name": "legada", "parameters": {}},
            {"type": "function", "function": {"name": "nova"}},
        ]
        limpo = sanitize_request({"model": "m", "tools": mistas})
        self.assertEqual(len(limpo["tools"]), 2)
        self.assertEqual(limpo["tools"][0]["type"], "function")
        self.assertEqual(limpo["tools"][1]["function"]["name"], "nova")

    def test_content_lista_texto_vira_string(self):
        mensagens = [
            {"role": "user", "content": [{"type": "text", "text": "ola"}]},
        ]
        saida = sanitize_request({"model": "m", "messages": mensagens})["messages"]
        self.assertEqual(saida[0]["content"], "ola")
        self.assertIsInstance(saida[0]["content"], str)

    def test_content_lista_misturar_texto_e_outros(self):
        mensagens = [
            {"role": "user", "content": [
                {"type": "text", "text": "olá"},
                {"type": "image_url", "image_url": {"url": "data:..."}},
            ]},
        ]
        saida = sanitize_request({"model": "m", "messages": mensagens})["messages"]
        self.assertEqual(saida[0]["content"], "olá")

    def test_content_lista_vazia_vira_espaco(self):
        mensagens = [{"role": "user", "content": []}]
        saida = sanitize_request({"model": "m", "messages": mensagens})["messages"]
        self.assertEqual(saida[0]["content"], " ")

    def test_content_string_simples_nao_muda(self):
        mensagens = [{"role": "user", "content": "hello"}]
        saida = sanitize_request({"model": "m", "messages": mensagens})["messages"]
        self.assertEqual(saida[0]["content"], "hello")

    def test_mensagem_system_e_filtrada(self):
        mensagens = [
            {"role": "system", "content": "voce e um assistente"},
            {"role": "user", "content": "oi"},
        ]
        saida = sanitize_request({"model": "m", "messages": mensagens})["messages"]
        self.assertEqual(len(saida), 1)
        self.assertEqual(saida[0]["role"], "user")

    def test_mensagem_system_no_meio_e_filtrada(self):
        mensagens = [
            {"role": "user", "content": "oi"},
            {"role": "system", "content": "instrucao"},
            {"role": "assistant", "content": "ola"},
            {"role": "user", "content": "tudo bem?"},
        ]
        saida = sanitize_request({"model": "m", "messages": mensagens})["messages"]
        roles = [m["role"] for m in saida]
        self.assertNotIn("system", roles)
        self.assertEqual(len(saida), 3)


if __name__ == "__main__":
    unittest.main()
