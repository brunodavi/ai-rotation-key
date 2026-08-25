import unittest

from src.utils.dot_path import resolver

DADOS = {
    "data": [
        {"id": "a", "meta": {"tipo": "chat"}},
        {"id": "b", "meta": {"tipo": "embed"}},
    ],
    "total": 2,
    "items": [{"modelId": "m1"}, {"modelId": "m2"}, {"modelId": "m3"}],
}


class ResolverTests(unittest.TestCase):
    def test_caminho_simples_para_lista_de_ids(self):
        self.assertEqual(resolver(DADOS, "data[].id"), ["a", "b"])

    def test_caminho_aninhado_apos_iteracao(self):
        self.assertEqual(resolver(DADOS, "data[].meta.tipo"), ["chat", "embed"])

    def test_indice_numerico(self):
        self.assertEqual(resolver(DADOS, "items[1].modelId"), ["m2"])
        self.assertEqual(resolver(DADOS, "items[-1].modelId"), ["m3"])

    def test_chave_simples_sem_array(self):
        self.assertEqual(resolver(DADOS, "total"), [2])

    def test_null_safe_chave_ausente_e_pulada(self):
        dados = {"data": [{"id": "x"}, {"outra": 1}, {"id": "y"}]}
        self.assertEqual(resolver(dados, "data[].id"), ["x", "y"])

    def test_null_safe_indice_fora_do_range(self):
        self.assertEqual(resolver(DADOS, "data[9].id"), [])

    def test_raiz_nao_dict_retorna_vazio(self):
        self.assertEqual(resolver("texto", "a.b"), [])
        self.assertEqual(resolver(None, "a"), [])
        self.assertEqual(resolver([1, 2], "0"), [1])

    def test_caminho_vazio_levanta_value_error(self):
        with self.assertRaises(ValueError):
            resolver(DADOS, "")
        with self.assertRaises(ValueError):
            resolver(DADOS, "   ")

    def test_valores_none_no_meio_do_caminho(self):
        dados = {"a": None}
        self.assertEqual(resolver(dados, "a.b"), [])


if __name__ == "__main__":
    unittest.main()
