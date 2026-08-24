import json
import os
import pathlib
import shutil
import unittest
from unittest import mock

from src.utils.config_paths import DEFAULT_PORT, config_path
from src.utils.load_config import load_config


class LoadConfigTests(unittest.TestCase):
    def setUp(self):
        raiz = pathlib.Path(__file__).resolve().parents[1]
        self.scratch = raiz / "tmp" / ".scratch" / "test_load_config"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir(parents=True)
        self.home = self.scratch / "home"
        self.home.mkdir()
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def _escrever(self, conteudo: str):
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(conteudo, encoding="utf-8")
        return path

    def test_carrega_exemplo_gerado_pelo_init(self):
        from src.utils.init_config import init_config

        init_config()
        dados = load_config()
        self.assertEqual(
            dados,
            {
                "model-keys": {"gemini-3.5-flash": ["sk-exemplo-1", "sk-exemplo-2"]},
                "port": 8792,
            },
        )

    def test_port_ausente_vira_default(self):
        self._escrever(json.dumps({"model-keys": {"m": ["sk-a"]}}))
        dados = load_config()
        self.assertEqual(dados["port"], DEFAULT_PORT)
        self.assertEqual(dados["port"], 8792)

    def test_port_customizada_e_normalizada_para_int(self):
        self._escrever(json.dumps({"model-keys": {"m": ["sk-a"]}, "port": 9999}))
        self.assertEqual(load_config()["port"], 9999)

    def test_port_invalida_levanta_value_error(self):
        for ruim in ("abc", 0, -1, 1.5, None):
            with self.subTest(port=ruim):
                self._escrever(json.dumps({"model-keys": {"m": ["sk-a"]}, "port": ruim}))
                with self.assertRaises(ValueError):
                    load_config()

    def test_arquivo_ausente_menciona_init(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            load_config()
        self.assertIn("init", str(ctx.exception))

    def test_json_quebrado_levanta_value_error(self):
        self._escrever("{model-keys: quebrado")
        with self.assertRaises(ValueError):
            load_config()

    def test_model_keys_ausente_levanta_value_error(self):
        self._escrever(json.dumps({"port": 8792}))
        with self.assertRaises(ValueError):
            load_config()

    def test_model_keys_invalido_levanta_value_error(self):
        casos = [
            {},
            "texto",
            {"m": "sk-string"},
            {"m": []},
            {"m": [1, 2]},
            {"": ["sk-a"]},
        ]
        for model_keys in casos:
            with self.subTest(model_keys=model_keys):
                self._escrever(json.dumps({"model-keys": model_keys}))
                with self.assertRaises(ValueError):
                    load_config()

    def test_path_explicito_sobrepoe_default(self):
        alvo = self.scratch / "outro.json"
        alvo.write_text(json.dumps({"model-keys": {"x": ["sk-z"]}, "port": 7000}), encoding="utf-8")
        dados = load_config(alvo)
        self.assertEqual(dados["model-keys"], {"x": ["sk-z"]})
        self.assertEqual(dados["port"], 7000)


if __name__ == "__main__":
    unittest.main()
