import importlib
import io
import re
import subprocess
import sys
import unittest
from unittest import mock

from scripts.hooks import commit_hook

instalador = importlib.import_module("scripts.install-git-hooks")


def _linha_hook(texto, nome):
    """Linha da listagem de hooks, no formato `  <nome> → <comportamento>`."""
    padrao = re.compile(rf"^\s*{re.escape(nome)}\s+→")
    for linha in (texto or "").splitlines():
        if padrao.match(linha):
            return linha
    return None


def _segmento_do_resumo(resumo, nome):
    """Trecho da frase final que fala do hook `<nome>` (separada por vírgulas)."""
    for parte in resumo.split(","):
        if nome in parte:
            return parte
    return None


class DocumentacaoDoInstaladorTests(unittest.TestCase):
    """O que o instalador anuncia precisa bater com o que os hooks fazem."""

    def test_linha_do_pre_commit_no_docstring_nao_anuncia_suite(self):
        linha = _linha_hook(instalador.__doc__, "pre-commit")
        self.assertIsNotNone(linha, "docstring perdeu a linha do pre-commit")
        self.assertNotIn("suíte", linha)

    def test_docstring_precisa_listar_o_pre_push_com_a_suite(self):
        linha = _linha_hook(instalador.__doc__, "pre-push")
        self.assertIsNotNone(linha, "docstring não documenta o pre-push")
        self.assertIn("suíte", linha)

    def test_resumo_nao_anuncia_suite_no_pre_commit(self):
        segmento = _segmento_do_resumo(instalador.RESUMO, "pre-commit")
        self.assertIsNotNone(segmento, "RESUMO não fala do pre-commit")
        self.assertNotIn("suíte", segmento)

    def test_resumo_aponta_a_suite_para_o_pre_push(self):
        segmento = _segmento_do_resumo(instalador.RESUMO, "pre-push")
        self.assertIsNotNone(segmento, "RESUMO não fala do pre-push")
        self.assertIn("suíte", segmento)


class ComportamentoRealDosHooksTests(unittest.TestCase):
    """Fonte da verdade das mensagens: a suíte roda só no pre-push."""

    @staticmethod
    def _run_gravando(chamadas):
        def run(cmd, **kwargs):
            chamadas.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="")
        return run

    def test_pre_commit_nunca_invoca_a_suite(self):
        chamadas = []
        with mock.patch.object(commit_hook.subprocess, "run",
                               self._run_gravando(chamadas)):
            self.assertEqual(commit_hook.pre_commit(), 0)
        self.assertFalse(any("unittest" in cmd for cmd in chamadas), chamadas)

    def test_pre_push_com_tag_invoca_a_suite(self):
        chamadas = []
        stdin = io.StringIO("refs/tags/v9.9.9 aaa refs/tags/v9.9.9 bbb\n")
        with mock.patch.object(commit_hook.subprocess, "run",
                               self._run_gravando(chamadas)), \
                mock.patch.object(sys, "stdin", stdin):
            commit_hook.pre_push()
        self.assertTrue(any("unittest" in cmd for cmd in chamadas), chamadas)


if __name__ == "__main__":
    unittest.main()
