import json
import os
import pathlib
import shutil
import unittest
from unittest import mock

from src.utils.config_paths import DEFAULT_PORT, config_path
from src.utils.init_config import init_config


class InitConfigTests(unittest.TestCase):
    def setUp(self):
        raiz = pathlib.Path(__file__).resolve().parents[1]
        self.scratch = raiz / "tmp" / ".scratch" / "test_init_config"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir(parents=True)
        self.home = self.scratch / "home"
        self.home.mkdir()
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def test_cria_config_de_exemplo_e_reporta_created_true(self):
        path, created = init_config()
        self.assertTrue(created)
        self.assertEqual(path, config_path())
        dados = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            dados,
            {
                "model-keys": {"gemini-3.5-flash": ["sk-exemplo-1", "sk-exemplo-2"]},
                "port": 8792,
            },
        )

    def test_nao_sobrescreve_config_existente(self):
        path, created = init_config()
        custom = {"model-keys": {"outro": ["sk-x"]}, "port": 9999}
        path.write_text(json.dumps(custom), encoding="utf-8")
        path2, created2 = init_config()
        self.assertFalse(created2)
        self.assertEqual(path2, path)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), custom)

    def test_cria_diretorios_pais_inexistentes(self):
        path, created = init_config()
        self.assertTrue(created)
        self.assertTrue(path.exists())
        self.assertIn(".config", str(path))

    def test_path_explicito_e_respeitado(self):
        alvo = self.scratch / "custom" / "cfg.json"
        path, created = init_config(alvo)
        self.assertTrue(created)
        self.assertEqual(path, alvo)
        self.assertTrue(alvo.exists())

    def test_conteudo_tem_indentacao_e_newline_final(self):
        path, _ = init_config()
        texto = path.read_text(encoding="utf-8")
        self.assertTrue(texto.endswith("\n"))
        self.assertIn("\n  ", texto)


if __name__ == "__main__":
    unittest.main()
