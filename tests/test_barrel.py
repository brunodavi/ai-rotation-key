import unittest

import src.utils


class BarrelTests(unittest.TestCase):
    def test_todos_os_nomes_de_all_sao_importaveis(self):
        for nome in src.utils.__all__:
            with self.subTest(nome=nome):
                self.assertTrue(hasattr(src.utils, nome), f"barrel não exporta {nome}")

    def test_barrel_cobre_a_superficie_publica_dos_modulos(self):
        esperados = {
            "DEFAULT_PORT",
            "config_dir",
            "config_path",
            "edit_config",
            "PROVIDER_ID",
            "export_provider",
            "find_free_port",
            "DEFAULT_UPSTREAM",
            "forward_request",
            "init_config",
            "load_config",
            "RoundRobin",
            "sanitize_request",
            "sanitize_response_payload",
            "sanitize_sse_line",
            "SignatureCache",
            "build_server",
            "start_server",
        }
        self.assertEqual(set(src.utils.__all__), esperados)


if __name__ == "__main__":
    unittest.main()
