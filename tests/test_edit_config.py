import os
import pathlib
import shutil
import subprocess
import unittest
from unittest import mock

from src.utils.edit_config import edit_config


class EditConfigTests(unittest.TestCase):
    def setUp(self):
        raiz = pathlib.Path(__file__).resolve().parents[1]
        self.scratch = raiz / "tmp" / ".scratch" / "test_edit_config"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def test_editor_touch_invoca_com_path_e_returncode_zero(self):
        path = self.scratch / "config.json"
        with mock.patch.dict(os.environ, {"EDITOR": "touch"}):
            resultado = edit_config(path)
        self.assertTrue(path.exists(), "editor não foi invocado com o caminho")
        self.assertEqual(resultado.returncode, 0)
        self.assertIsInstance(resultado, subprocess.CompletedProcess)

    def test_editor_ausente_usa_vi_e_retorna_completed_process_mockado(self):
        path = self.scratch / "config.json"
        fake = mock.Mock()
        env_sem_editor = {k: v for k, v in os.environ.items() if k != "EDITOR"}
        with mock.patch.dict(os.environ, env_sem_editor, clear=True):
            with mock.patch("subprocess.run", return_value=fake) as run_mock:
                resultado = edit_config(path)
        run_mock.assert_called_once_with(["vi", str(path)])
        self.assertIs(resultado, fake)

    def test_editor_string_vazia_usa_vi(self):
        path = self.scratch / "config.json"
        fake = mock.Mock()
        with mock.patch.dict(os.environ, {"EDITOR": ""}):
            with mock.patch("subprocess.run", return_value=fake) as run_mock:
                resultado = edit_config(path)
        run_mock.assert_called_once_with(["vi", str(path)])
        self.assertIs(resultado, fake)

    def test_path_explicito_usado_como_esta_sem_resolver_home(self):
        path = self.scratch / "explicito.json"
        fake = mock.Mock()
        home_falso = str(self.scratch / "home-falso")
        with mock.patch.dict(os.environ, {"EDITOR": "touch", "HOME": home_falso}):
            with mock.patch("subprocess.run", return_value=fake) as run_mock:
                resultado = edit_config(path)
        run_mock.assert_called_once_with(["touch", str(path)])
        self.assertIs(resultado, fake)


if __name__ == "__main__":
    unittest.main()
