import pathlib
import shutil
import subprocess
import sys
import unittest

from scripts.hooks import commit_hook

RAIZ = pathlib.Path(__file__).resolve().parents[1]
HOOK = RAIZ / "scripts" / "hooks" / "commit_hook.py"


class PrePushTests(unittest.TestCase):
    STDIN = (
        "refs/heads/dev 6d0561e refs/heads/dev 479bbcb\n"
        "refs/tags/v0.6.0 aaa111 refs/tags/v0.6.0 000000\n"
        "refs/tags/v0.7.0 bbb222 refs/tags/v0.7.0 000000\n"
    )

    def test_extrai_somente_tags_do_stdin_do_pre_push(self):
        self.assertEqual(
            commit_hook.tags_de_push(self.STDIN),
            ["v0.6.0", "v0.7.0"],
        )

    def test_sem_tags_nao_gera_nada(self):
        self.assertEqual(commit_hook.tags_de_push("refs/heads/dev a b c d\n"), [])

    def test_tag_deve_bater_com_a_versao_do_pyproject(self):
        erro = commit_hook.validar_tag("v0.9.9", versao="0.6.0", tags_existentes={"v0.5.0"})
        self.assertIsNotNone(erro)
        self.assertIn("v0.6.0", erro)

    def test_versao_precisa_subir_sobre_a_maior_existente(self):
        self.assertIsNone(commit_hook.validar_tag("v0.6.0", versao="0.6.0",
                                                  tags_existentes={"v0.4.0", "v0.5.0"}))
        self.assertIsNotNone(commit_hook.validar_tag("v0.5.0", versao="0.5.0",
                                                     tags_existentes={"v0.4.0", "v0.5.0"}))
        self.assertIsNotNone(commit_hook.validar_tag("v0.4.0", versao="0.5.0",
                                                     tags_existentes={"v0.4.0"}))

    def test_formato_semver_obrigatorio(self):
        for ruim in ("release-1", "v1", "v1.2", "v1.2.3.4"):
            with self.subTest(tag=ruim):
                self.assertIsNotNone(commit_hook.validar_tag(ruim, versao="0.6.0",
                                                             tags_existentes=set()))

    def test_versao_lida_do_pyproject_real(self):
        self.assertRegex(commit_hook.ler_versao_pyproject(RAIZ), r"^\d+\.\d+\.\d+$")


class ValidarPinReadmeTests(unittest.TestCase):
    def setUp(self):
        self.scratch = RAIZ / "tmp" / ".scratch" / "test_commit_hook_pin"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def _readme(self, pin=None):
        linha = ""
        if pin:
            linha = f"pip install git+https://github.com/brunodavi/ai-rotation-key.git@{pin}\n"
        (self.scratch / "README.md").write_text(f"# título\n\n{linha}", encoding="utf-8")

    def test_pin_desatualizado_bloqueia_apontando_ambas_as_versoes(self):
        self._readme("v0.5.0")
        erro = commit_hook.validar_pin_readme("v0.7.0", raiz=self.scratch)
        self.assertIsNotNone(erro)
        self.assertIn("@v0.5.0", erro)
        self.assertIn("v0.7.0", erro)

    def test_pin_atualizado_passa(self):
        self._readme("v0.8.0")
        self.assertIsNone(commit_hook.validar_pin_readme("v0.8.0", raiz=self.scratch))

    def test_sem_pin_bloqueia_com_orientacao(self):
        self._readme(None)
        erro = commit_hook.validar_pin_readme("v0.8.0", raiz=self.scratch)
        self.assertIsNotNone(erro)
        self.assertIn("git+", erro)

    def test_repo_real_tem_o_pin_da_ultima_tag(self):
        self.assertIsNone(commit_hook.validar_pin_readme(
            f"v{commit_hook.ler_versao_pyproject(RAIZ)}", raiz=RAIZ,
        ))


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
