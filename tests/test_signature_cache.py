import unittest

from src.utils.signature_cache import SignatureCache


def _tc(id_, sig=None, **campos):
    tool_call = {"id": id_, "type": "function", "function": {"name": "f", "arguments": "{}"}}
    if sig is not None:
        tool_call["extra_content"] = {"google": {"thought_signature": sig}}
    tool_call.update(campos)
    return tool_call


class CollectTests(unittest.TestCase):
    def setUp(self):
        self.cache = SignatureCache()

    def test_coleta_de_message_tool_calls(self):
        payload = {"choices": [{"message": {"role": "assistant", "tool_calls": [_tc("call_1", "sig1")]}}]}
        self.cache.collect(payload)
        self.assertEqual(self.cache.signatures(), {"call_1": {"google": {"thought_signature": "sig1"}}})

    def test_coleta_de_delta_tool_calls_em_stream(self):
        payload = {"choices": [{"delta": {"tool_calls": [_tc("call_2", "sig2")]}}]}
        self.cache.collect(payload)
        self.assertEqual(list(self.cache.signatures()), ["call_2"])

    def test_coleta_de_choice_tool_calls_direto(self):
        payload = {"choices": [{"tool_calls": [_tc("call_3", "sig3")]}]}
        self.cache.collect(payload)
        self.assertEqual(list(self.cache.signatures()), ["call_3"])

    def test_sem_assinatura_nao_coleta(self):
        payload = {"choices": [{"message": {"tool_calls": [_tc("call_4")]}}]}
        self.cache.collect(payload)
        self.assertEqual(self.cache.signatures(), {})

    def test_payload_sem_choices_nao_quebra(self):
        for vazio in (None, {}, {"choices": []}):
            with self.subTest(payload=vazio):
                self.cache.collect(vazio)
                self.assertEqual(self.cache.signatures(), {})

    def test_assinatura_repetida_atualiza_valor_do_id(self):
        self.cache.collect({"choices": [{"delta": {"tool_calls": [_tc("c1", "velha")]}}]})
        self.cache.collect({"choices": [{"delta": {"tool_calls": [_tc("c1", "nova")]}}]})
        self.assertEqual(
            self.cache.signatures()["c1"],
            {"google": {"thought_signature": "nova"}},
        )


class InjectTests(unittest.TestCase):
    def setUp(self):
        self.cache = SignatureCache()
        self.cache.collect({
            "choices": [{"message": {"tool_calls": [_tc("call_9", "sig9")]}}]
        })

    def test_injeta_no_historico_do_assistant(self):
        mensagens = [
            {"role": "user", "content": "lista arquivos"},
            {"role": "assistant", "content": " ", "tool_calls": [_tc("call_9")]},
            {"role": "tool", "tool_call_id": "call_9", "content": "[]"},
        ]
        self.cache.inject(mensagens)
        tool_call = mensagens[1]["tool_calls"][0]
        self.assertEqual(tool_call["extra_content"], {"google": {"thought_signature": "sig9"}})

    def test_nao_sobrescreve_extra_content_existente(self):
        original = {"google": {"thought_signature": "original"}}
        mensagens = [{"role": "assistant", "tool_calls": [_tc("call_9", sig=None)]}]
        mensagens[0]["tool_calls"][0]["extra_content"] = original
        self.cache.inject(mensagens)
        self.assertEqual(mensagens[0]["tool_calls"][0]["extra_content"], original)

    def test_mensagens_sem_tool_calls_intocadas(self):
        mensagens = [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "olá"}]
        antes = [dict(m) for m in mensagens]
        self.cache.inject(mensagens)
        self.assertEqual(mensagens, antes)

    def test_ids_desconhecidos_sao_ignorados(self):
        mensagens = [{"role": "assistant", "tool_calls": [_tc("outro-id")]}]
        self.cache.inject(mensagens)
        self.assertNotIn("extra_content", mensagens[0]["tool_calls"][0])

    def test_cap_evicta_mais_antigo(self):
        cache = SignatureCache(cap=2)
        for i in range(3):
            cache.collect({"choices": [{"message": {"tool_calls": [_tc(f"c{i}", f"s{i}")]}}]})
        assinaturas = cache.signatures()
        self.assertNotIn("c0", assinaturas)
        self.assertIn("c2", assinaturas)


if __name__ == "__main__":
    unittest.main()
