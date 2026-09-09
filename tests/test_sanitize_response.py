import unittest

from src.providers.base import Provider


def _resposta_com_extra(**extras):
    return {"choices": [dict(extras)]}


class SanitizerResponseTests(unittest.TestCase):
    def setUp(self):
        self.san = Provider()

    def test_remove_de_message_preservando_resto(self):
        resp = _resposta_com_extra(
            message={
                "role": "assistant",
                "content": "ok",
                "extra_content": {"google": {"thought_signature": "sig"}},
            }
        )
        self.san.sanitize_response(resp)
        message = resp["choices"][0]["message"]
        self.assertEqual(message, {"role": "assistant", "content": "ok"})

    def test_remove_de_delta(self):
        resp = _resposta_com_extra(
            delta={"content": "pedaço", "extra_content": {"google": {}}}
        )
        self.san.sanitize_response(resp)
        self.assertEqual(resp["choices"][0]["delta"], {"content": "pedaço"})

    def test_regressao_remove_de_message_tool_calls(self):
        resp = _resposta_com_extra(
            finish_reason="tool_calls",
            message={
                "role": "assistant",
                "tool_calls": [{
                    "extra_content": {"google": {"thought_signature": "sig"}},
                    "function": {"arguments": "{}", "name": "get_time"},
                    "id": "call_1",
                    "type": "function",
                }],
            },
        )
        self.san.sanitize_response(resp)
        tool_call = resp["choices"][0]["message"]["tool_calls"][0]
        self.assertEqual(
            tool_call,
            {"function": {"arguments": "{}", "name": "get_time"}, "id": "call_1", "type": "function"},
        )

    def test_remove_de_delta_tool_calls(self):
        resp = _resposta_com_extra(
            delta={
                "tool_calls": [{
                    "extra_content": {"x": 1},
                    "function": {"name": "f", "arguments": "{}"},
                }]
            }
        )
        self.san.sanitize_response(resp)
        self.assertNotIn("extra_content", resp["choices"][0]["delta"]["tool_calls"][0])

    def test_remove_de_choice_tool_calls_direto(self):
        resp = _resposta_com_extra(
            tool_calls=[{"extra_content": {"x": 1}, "id": "call_2"}]
        )
        self.san.sanitize_response(resp)
        self.assertEqual(resp["choices"][0]["tool_calls"], [{"id": "call_2"}])

    def test_sem_choices_nao_quebra(self):
        for vazio in ({}, {"choices": []}, {"choices": None}):
            with self.subTest(payload=vazio):
                self.assertEqual(self.san.sanitize_response(vazio), vazio)


class SanitizerSseLineTests(unittest.TestCase):
    def setUp(self):
        self.san = Provider()

    def test_linha_modificada_e_reconstruida_no_formato_exato(self):
        chunk = {
            "choices": [{"delta": {"content": "oi", "extra_content": {"g": {}}}, "index": 0}]
        }
        linha = b"data: " + __import__("json").dumps(chunk).encode() + b"\n\n"
        saida = self.san.sanitize_sse_line(linha)
        self.assertTrue(saida.startswith(b"data: "))
        self.assertTrue(saida.endswith(b"\n\n"))
        self.assertNotIn(b"extra_content", saida)

    def test_linha_sem_mudancas_volta_byte_a_byte(self):
        bruto = b'data: {"choices":[{"delta":{"content":"x"},"index":0}]}\n\n'
        self.assertEqual(self.san.sanitize_sse_line(bruto), bruto)

    def test_done_passa_intacto(self):
        self.assertEqual(self.san.sanitize_sse_line(b"data: [DONE]\n\n"), b"data: [DONE]\n\n")

    def test_linha_nao_data_passa_intacta(self):
        bruto = b": keep-alive\n\n"
        self.assertEqual(self.san.sanitize_sse_line(bruto), bruto)

    def test_json_malformado_passa_intacto(self):
        bruto = b"data: nao-e-json\n\n"
        self.assertEqual(self.san.sanitize_sse_line(bruto), bruto)


if __name__ == "__main__":
    unittest.main()
