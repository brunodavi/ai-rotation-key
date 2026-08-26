import unittest

from src.utils.translate_body import (
    translate_chunk,
    translate_request,
    translate_response,
    translate_sse_line,
)


GEMINI_REQUEST_MAP = {
    "contents[].role": "messages[].role",
    "contents[].parts[0].text": "messages[].content",
}

GEMINI_RESPONSE_MAP = {
    "choices[0].message.content": "candidates[0].content.parts[0].text",
    "choices[0].finish_reason": "candidates[0].finishReason",
    "usage.prompt_tokens": "usageMetadata.promptTokenCount",
    "usage.completion_tokens": "usageMetadata.candidatesTokenCount",
    "usage.total_tokens": "usageMetadata.totalTokenCount",
}


class TranslateRequestTests(unittest.TestCase):
    def test_mensagens_openai_viram_contents_gemini(self):
        corpo = {
            "model": "gemini-3.6-flash",
            "messages": [
                {"role": "user", "content": "oi"},
                {"role": "assistant", "content": "tudo bem"},
                {"role": "user", "content": "qual o sentido?"},
            ],
        }
        saida = translate_request(corpo, GEMINI_REQUEST_MAP, role_map={"assistant": "model"})
        self.assertEqual(saida, {
            "contents": [
                {"role": "user", "parts": [{"text": "oi"}]},
                {"role": "model", "parts": [{"text": "tudo bem"}]},
                {"role": "user", "parts": [{"text": "qual o sentido?"}]},
            ],
        })

    def test_role_map_so_afeta_campos_de_role(self):
        corpo = {"messages": [{"role": "user", "content": "model"}]}
        saida = translate_request(
            corpo,
            GEMINI_REQUEST_MAP,
            role_map={"user": "MODEL"},
        )
        self.assertEqual(saida["contents"][0]["parts"][0]["text"], "model")
        self.assertEqual(saida["contents"][0]["role"], "MODEL")

    def test_sem_role_map_roles_passam_cruas(self):
        corpo = {"messages": [{"role": "assistant", "content": "oi"}]}
        saida = translate_request(corpo, GEMINI_REQUEST_MAP)
        self.assertEqual(saida["contents"][0]["role"], "assistant")

    def test_null_safe_mensagem_sem_conteudo_nao_quebra(self):
        corpo = {
            "messages": [
                {"role": "user"},
                {"role": "assistant", "content": "oi"},
                {"role": "user", "content": ""},
            ],
        }
        saida = translate_request(corpo, GEMINI_REQUEST_MAP)
        self.assertEqual(len(saida["contents"]), 3)
        self.assertEqual(saida["contents"][0], {"role": "user"})
        self.assertEqual(saida["contents"][2], {"role": "user", "parts": [{"text": ""}]})

    def test_campos_escalam_via_copia_simples(self):
        corpo = {
            "messages": [{"role": "user", "content": "oi"}],
            "temperature": 0.7,
            "max_tokens": 256,
        }
        mapa = dict(GEMINI_REQUEST_MAP)
        mapa["generationConfig.temperature"] = "temperature"
        mapa["generationConfig.maxOutputTokens"] = "max_tokens"
        saida = translate_request(corpo, mapa)
        self.assertEqual(saida["generationConfig"], {
            "temperature": 0.7,
            "maxOutputTokens": 256,
        })

    def test_origem_ausente_em_copia_simples_nao_cria_no(self):
        corpo = {"messages": [{"role": "user", "content": "oi"}]}
        mapa = {"generationConfig.stopSequences": "stop"}
        saida = translate_request(corpo, mapa)
        self.assertEqual(saida, {})

    def test_saida_tem_apenas_o_que_foi_mapeado(self):
        corpo = {
            "model": "gemini-3.6-flash",
            "stream": True,
            "messages": [{"role": "user", "content": "oi"}],
        }
        saida = translate_request(corpo, GEMINI_REQUEST_MAP)
        self.assertEqual(list(saida.keys()), ["contents"])

    def test_iteracao_em_apenas_um_lado_levanta_value_error(self):
        corpo = {"messages": [{"role": "user", "content": "oi"}]}
        with self.assertRaises(ValueError):
            translate_request(corpo, {"contents[].role": "model"})


class TranslateResponseTests(unittest.TestCase):
    def test_resposta_native_vira_openai(self):
        upstream = {
            "candidates": [{
                "content": {"parts": [{"text": "OK"}], "role": "model"},
                "finishReason": "STOP",
                "index": 0,
            }],
            "usageMetadata": {
                "promptTokenCount": 5,
                "candidatesTokenCount": 1,
                "totalTokenCount": 70,
            },
        }
        saida = translate_response(upstream, GEMINI_RESPONSE_MAP)
        self.assertEqual(saida["choices"], [{
            "message": {"role": "assistant", "content": "OK"},
            "finish_reason": "stop",
        }])
        self.assertEqual(saida["usage"], {
            "prompt_tokens": 5,
            "completion_tokens": 1,
            "total_tokens": 70,
        })
        self.assertEqual(saida["object"], "chat.completion")
        self.assertTrue(saida["id"])
        self.assertIsInstance(saida["created"], int)

    def test_envelope_valido_mesmo_com_upstream_vazio(self):
        saida = translate_response({}, GEMINI_RESPONSE_MAP)
        self.assertEqual(saida["choices"], [])
        self.assertEqual(saida["usage"], {})
        self.assertEqual(saida["object"], "chat.completion")

    def test_null_safe_parte_aninhada_ausente_mantem_resto(self):
        upstream = {"candidates": [{"finishReason": "SAFETY"}]}
        saida = translate_response(upstream, GEMINI_RESPONSE_MAP)
        self.assertEqual(saida["choices"], [{"finish_reason": "safety"}])
        self.assertEqual(saida["usage"], {})

    def test_finish_reason_normalizada_para_minusculas(self):
        upstream = {"candidates": [{"finishReason": "MAX_TOKENS"}]}
        saida = translate_response(upstream, GEMINI_RESPONSE_MAP)
        self.assertEqual(saida["choices"], [{"finish_reason": "max_tokens"}])


class TranslateChunkTests(unittest.TestCase):
    def test_chunk_native_vira_delta_openai(self):
        chunk = {
            "candidates": [{"content": {"parts": [{"text": "1, 2"}], "role": "model"}, "index": 0}],
            "usageMetadata": {"totalTokenCount": 245},
        }
        saida = translate_chunk(chunk, GEMINI_RESPONSE_MAP)
        self.assertEqual(saida["object"], "chat.completion.chunk")
        self.assertEqual(saida["choices"], [{
            "delta": {"role": "assistant", "content": "1, 2"},
            "finish_reason": None,
        }])
        self.assertEqual(saida["usage"], {"total_tokens": 245})

    def test_chunk_final_carrega_finish_reason(self):
        chunk = {
            "candidates": [{
                "content": {"parts": [{"text": ""}], "role": "model"},
                "finishReason": "STOP",
                "index": 0,
            }],
        }
        saida = translate_chunk(chunk, GEMINI_RESPONSE_MAP)
        self.assertEqual(saida["choices"], [{
            "delta": {"role": "assistant", "content": ""},
            "finish_reason": "stop",
        }])

    def test_chunk_sem_nada_mapeavel_ainda_e_valido(self):
        saida = translate_chunk({}, GEMINI_RESPONSE_MAP)
        self.assertEqual(saida["object"], "chat.completion.chunk")
        self.assertEqual(saida["choices"], [])


class TranslateSseLineTests(unittest.TestCase):
    def test_linha_data_traduzida_em_bytes(self):
        linha = b'data: {"candidates": [{"content": {"parts": [{"text": "ola"}]}}]}\n\n'
        saida = translate_sse_line(linha, GEMINI_RESPONSE_MAP)
        self.assertTrue(saida.startswith(b"data: "))
        self.assertIn(b'"delta"', saida)
        self.assertIn(b'"content"', saida)
        self.assertTrue(saida.endswith(b"\n\n"))

    def test_linha_sem_data_cai_no_modo_traducao(self):
        self.assertIsNone(translate_sse_line(b": keep-alive\n\n", GEMINI_RESPONSE_MAP))
        self.assertIsNone(translate_sse_line(b"\n", GEMINI_RESPONSE_MAP))

    def test_json_quebrado_passa_inalterado(self):
        linha = b"data: {quebrado\n\n"
        self.assertEqual(translate_sse_line(linha, GEMINI_RESPONSE_MAP), linha)

    def test_done_native_some(self):
        self.assertIsNone(translate_sse_line(b"data: [DONE]\n\n", GEMINI_RESPONSE_MAP))


if __name__ == "__main__":
    unittest.main()
