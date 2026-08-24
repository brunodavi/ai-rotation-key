import tomllib
import unittest
from pathlib import Path


class PackagingTests(unittest.TestCase):
    def setUp(self):
        raiz = Path(__file__).resolve().parents[1]
        self.pyproject = tomllib.loads((raiz / "pyproject.toml").read_text(encoding="utf-8"))

    def test_scripts_apontam_para_o_entrypoint_principal(self):
        scripts = self.pyproject["project"]["scripts"]
        self.assertTrue(scripts)
        for nome, alvo in scripts.items():
            with self.subTest(script=nome):
                self.assertEqual(alvo, "main:main")

    def test_alias_curto_esta_registrado_e_nada_mais(self):
        scripts = self.pyproject["project"]["scripts"]
        self.assertEqual(set(scripts), {"ai-rotation-key", "airkey"})


if __name__ == "__main__":
    unittest.main()
