import pathlib
import shutil
import subprocess
import sys
import unittest

from scripts.hooks import commit_hook

RAIZ = pathlib.Path(__file__).resolve().parents[1]
HOOK = RAIZ / "scripts" / "hooks" / "commit_hook.py"


class ValidarMensagemTests(unittest.TestCase):
    def _validar(self, mensagem):
        return commit_hook.validar_mensagem(mensagem)

    def test_matriz_do_padrao(self):
        casos_aceitos = [
            "test(cli): RED - validação",
            "feat(hooks): GREEN - commit_hook unificado",
            "refactor: REFACTOR - algo",
            "fix(x): RED - correção",
            "docs: nota qualquer",
            "chore: versão",
            "Merge branch 'x'",
            "Revert \"chore: versão\"",
        ]
        casos_bloqueados = [
            "mensagem sem padrão",
            "fix(x): REFACTOR - fase errada",
            "chore(x): RED - proibido",
            "docs: RED - proibido",
            "test(cli): GREEN - fase errada",
            "test(cli): sem fase",
            "feat(hooks): sem fase",
            "Tipos: maiúsculo não vale",
        ]
        for mensagem in casos_aceitos:
            with self.subTest(aceito=mensagem):
                self.assertIsNone(self._validar(mensagem))
        for mensagem in casos_bloqueados:
            with self.subTest(bloqueado=mensagem):
                self.assertIsNotNone(self._validar(mensagem))


class FalhasStagedTests(unittest.TestCase):
    def setUp(self):
        raiz = pathlib.Path(__file__).resolve().parents[1]
        self.scratch = raiz / "tmp" / ".scratch" / "test_commit_hook"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def _arquivo(self, nome, conteudo=""):
        caminho = self.scratch / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
        return str(caminho)

    def test_segredo_detectado_e_limpo_passa(self):
        # montada em runtime: o fonte não pode conter literal casável com o scanner
        segredo = "sk-" + "a1B2c3D4e5" * 4
        com_segredo = self._arquivo("vazado.txt", f"minha key {segredo}")
        falhas = commit_hook.falhas_de_staged([com_segredo])
        self.assertEqual(len(falhas), 1)
        self.assertIn("segredo", falhas[0])

        limpo = self._arquivo("ok.txt", "key fake sk-exemplo-1 não casa")
        self.assertEqual(commit_hook.falhas_de_staged([limpo]), [])

    def test_arquivo_espurio_sem_extensao(self):
        espurio = self._arquivo("1", "traceback antigo")
        falhas = commit_hook.falhas_de_staged([espurio])
        self.assertEqual(len(falhas), 1)
        self.assertIn("espúrio", falhas[0])

    def test_arquivos_normais_nao_falham(self):
        normal = self._arquivo("src_modulo.py", "print('oi')\n")
        aninhado = self._arquivo("sub/pasta.txt", "")
        self.assertEqual(commit_hook.falhas_de_staged([normal, aninhado]), [])

    def test_tmp_nunca_pode_ir_pro_staged(self):
        falhas = commit_hook.falhas_de_staged(["tmp/apis/x/key.txt", "tmp"])
        self.assertEqual(len(falhas), 2)
        self.assertIn("tmp/", falhas[0])


if __name__ == "__main__":
    unittest.main()
