import contextlib
import io
import os
import pathlib
import unittest
from unittest import mock

from collections import namedtuple

from src.cli import _build_parser, main

SyncResultFake = namedtuple("SyncResultFake", "relatorios salvo houve_erro path")


class CliRoutingTests(unittest.TestCase):
    def test_subcomandos_disparam_handlers_corretos(self):
        casos = [
            (["init"], "src.commands.init", "init_config"),
            (["edit"], "src.commands.edit", "edit_config"),
            (["start"], "src.commands.start", "start_server"),
            (["export"], "src.commands.export", "export_provider"),
        ]
        for argv, modulo, nome in casos:
            with self.subTest(comando=argv[0]):
                with mock.patch(f"{modulo}.{nome}", return_value=None) as handler:
                    main(argv)
                handler.assert_called_once_with()

    def test_sync_models_sem_arg_passa_apenas_none(self):
        fake = SyncResultFake({}, False, False, pathlib.Path("/tmp/x"))
        with mock.patch("src.commands.sync_models.sync_models", return_value=fake) as handler:
            main(["sync-models"])
        handler.assert_called_once_with(apenas=None)

    def test_sync_models_com_provider_passa_apenas(self):
        fake = SyncResultFake({}, False, False, pathlib.Path("/tmp/x"))
        with mock.patch("src.commands.sync_models.sync_models", return_value=fake) as handler:
            main(["sync-models", "gemini"])
        handler.assert_called_once_with(apenas="gemini")

    def test_sync_models_imprime_relatorio_por_provider(self):
        fake = SyncResultFake(
            {
                "gemini": {"adicionados": ["a", "b"], "excluidos": 31, "existentes": 2},
                "outro": {"adicionados": [], "excluidos": 0, "existentes": 5},
                "quebrado": {"erro": "boom", "status": 401},
            },
            True,
            True,
            pathlib.Path("/tmp/opencode"),
        )
        saida = io.StringIO()
        with mock.patch("src.commands.sync_models.sync_models", return_value=fake), contextlib.redirect_stdout(saida):
            with self.assertRaises(SystemExit) as ctx:
                main(["sync-models"])
        self.assertEqual(ctx.exception.code, 1)
        texto = saida.getvalue()
        self.assertIn("gemini: +2 adicionados", texto)
        self.assertIn("31 filtrados por filter-models", texto)
        self.assertIn("2 já existiam", texto)
        self.assertIn("outro: inalterado", texto)
        self.assertIn("quebrado: erro HTTP 401", texto)
        self.assertIn(str(fake.path), texto)

    def test_sync_models_provider_desconhecido_sai_com_mensagem(self):
        saida = io.StringIO()
        with mock.patch("src.commands.sync_models.sync_models", side_effect=ValueError("provider 'x' não está no config — opções: gemini")):
            with contextlib.redirect_stdout(saida):
                with self.assertRaises(SystemExit) as ctx:
                    main(["sync-models", "x"])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("não está no config", saida.getvalue())

    def test_retorno_do_handler_propagado(self):
        sentinela = object()
        with mock.patch("src.commands.init.init_config", return_value=sentinela):
            self.assertIs(main(["init"]), sentinela)

    def test_edit_flag_opencode_abre_config_do_opencode(self):
        with mock.patch("src.commands.edit.edit_config", return_value=None) as handler:
            main(["edit", "--opencode"])
        esperado = pathlib.Path(os.environ["HOME"]) / ".config" / "opencode" / "config.json"
        handler.assert_called_once_with(esperado)

    def test_edit_sem_flag_abre_o_config_do_projeto(self):
        with mock.patch("src.commands.edit.edit_config", return_value=None) as handler:
            main(["edit"])
        handler.assert_called_once_with()

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
        with mock.patch("src.commands.init.init_config", return_value=(caminho, True)):
            saida = io.StringIO()
            with contextlib.redirect_stdout(saida):
                main(["init"])
            self.assertIn(str(caminho), saida.getvalue())
            self.assertIn("criado", saida.getvalue())

    def test_init_ja_existente_avisa_sem_sobrescrever(self):
        caminho = pathlib.Path("/tmp/fake") / "config.json"
        with mock.patch("src.commands.init.init_config", return_value=(caminho, False)):
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
                with mock.patch("src.commands.export.export_provider", return_value=(caminho, acao)):
                    saida = io.StringIO()
                    with contextlib.redirect_stdout(saida):
                        main(["export"])
                    self.assertIn(trecho, saida.getvalue())
                    self.assertIn(str(caminho), saida.getvalue())


if __name__ == "__main__":
    unittest.main()
