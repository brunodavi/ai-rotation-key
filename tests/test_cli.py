import contextlib
import io
import pathlib
import unittest
from unittest import mock

from src.cli import _build_parser, main


class CliRoutingTests(unittest.TestCase):
    def test_subcomandos_disparam_handlers_corretos(self):
        casos = [
            (["init"], "init_config"),
            (["edit"], "edit_config"),
            (["start"], "start_server"),
            (["export"], "export_provider"),
        ]
        for argv, nome in casos:
            with self.subTest(comando=argv[0]):
                with mock.patch(f"src.cli.{nome}", return_value=None) as handler:
                    main(argv)
                handler.assert_called_once_with()

    def test_retorno_do_handler_propagado(self):
        sentinela = object()
        with mock.patch("src.cli.init_config", return_value=sentinela):
            self.assertIs(main(["init"]), sentinela)

    def test_comando_invalido_sai_com_codigo_2(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["inexistente"])
        self.assertEqual(ctx.exception.code, 2)

    def test_sem_comando_sai_com_codigo_2(self):
        with self.assertRaises(SystemExit) as ctx:
            main([])
        self.assertEqual(ctx.exception.code, 2)

    def test_help_lista_os_quatro_comandos(self):
        ajuda = _build_parser().format_help()
        for comando in ("init", "edit", "start", "export"):
            self.assertIn(comando, ajuda)


class CliOutputTests(unittest.TestCase):
    def test_init_criado_imprime_caminho(self):
        caminho = pathlib.Path("/tmp/fake") / "config.json"
        with mock.patch("src.cli.init_config", return_value=(caminho, True)):
            saida = io.StringIO()
            with contextlib.redirect_stdout(saida):
                main(["init"])
            self.assertIn(str(caminho), saida.getvalue())
            self.assertIn("criado", saida.getvalue())

    def test_init_ja_existente_avisa_sem_sobrescrever(self):
        caminho = pathlib.Path("/tmp/fake") / "config.json"
        with mock.patch("src.cli.init_config", return_value=(caminho, False)):
            saida = io.StringIO()
            with contextlib.redirect_stdout(saida):
                main(["init"])
            self.assertIn("já existe", saida.getvalue())
            self.assertIn("sem alterar", saida.getvalue())

    def test_export_imprime_acao_realizada_e_caminho(self):
        caminho = pathlib.Path("/tmp/fake") / "opencode.json"
        for acao, trecho in (
            ("criado", "criado"),
            ("adicionado", "adicionado"),
            ("atualizado", "atualizado"),
            ("inalterado", "já estava configurado"),
        ):
            with self.subTest(acao=acao):
                with mock.patch("src.cli.export_provider", return_value=(caminho, acao)):
                    saida = io.StringIO()
                    with contextlib.redirect_stdout(saida):
                        main(["export"])
                    self.assertIn(trecho, saida.getvalue())
                    self.assertIn(str(caminho), saida.getvalue())


if __name__ == "__main__":
    unittest.main()
