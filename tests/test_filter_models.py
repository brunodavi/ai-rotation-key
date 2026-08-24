import unittest

from src.utils.filter_models import filtrar_modelos

CANDIDATOS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-tts",
    "gemini-vision-pro",
    "poolside/laguna-s-2.1:free",
    "z-ai/glm-5.2:free",
]


class FiltrarModelosTests(unittest.TestCase):
    def test_sem_filtros_passa_tudo(self):
        self.assertEqual(filtrar_modelos(CANDIDATOS, []), CANDIDATOS)

    def test_somente_negativos_devolve_tudo_menos_os_casados(self):
        resultado = filtrar_modelos(CANDIDATOS, ["!*tts*", "!*vision*"])
        self.assertEqual(resultado, [
            "gemini-3.5-flash",
            "poolside/laguna-s-2.1:free",
            "z-ai/glm-5.2:free",
        ])

    def test_positivos_sao_allowlist(self):
        resultado = filtrar_modelos(CANDIDATOS, ["*:free*"])
        self.assertEqual(resultado, ["poolside/laguna-s-2.1:free", "z-ai/glm-5.2:free"])

    def test_negativo_vence_positivo(self):
        candidatos = [*CANDIDATOS, "vision-free-x"]
        resultado = filtrar_modelos(candidatos, ["*free*", "!*vision*"])
        self.assertEqual(resultado, [
            "poolside/laguna-s-2.1:free",
            "z-ai/glm-5.2:free",
        ])

    def test_casamento_e_case_sensitive(self):
        self.assertEqual(filtrar_modelos(["ABC"], ["abc"]), [])
        self.assertEqual(filtrar_modelos(["ABC"], ["ABC"]), ["ABC"])

    def test_negativo_so_remove_quando_prefixo_exclamacao(self):
        resultado = filtrar_modelos(["!tts-1", "tts-2"], ["!tts-*"])
        self.assertEqual(resultado, ["!tts-1"])


if __name__ == "__main__":
    unittest.main()
