"""Instala os hooks git do projeto — rode uma vez por clone:

    python scripts/install-git-hooks.py

Cria shims em .git/hooks que delegam para scripts/hooks/commit_hook.py:
  pre-commit   → nada de segredo/arquivo espúrio/tmp no staged
  post-commit  → push automático do branch atual
  commit-msg   → valida `<tipo>(<escopo>): [FASE - ]mensagem`
  pre-push     → gate de PROD nas tags: semver/versão/pin do README + suíte verde + árvore limpa

A suíte NÃO roda no pre-commit de propósito (o fluxo TDD exige commitar em RED):
ela é gate exclusivo do pre-push, e só quando o push leva tag.

Os hooks são locais (.git não é versionado); rode este script após novo clone.
"""

RESUMO = (
    "hooks ativos: segredos/lixo/tmp no pre-commit, push automático no post-commit, "
    "formato no commit-msg, tags=prod (suíte verde) no pre-push"
)

import os
import stat
import sys

SHIM = """#!/bin/sh
exec "{python}" "{hook}" {args}
"""


def _hook_absoluto():
    return os.path.abspath(os.path.join("scripts", "hooks", "commit_hook.py"))


def escrever(nome, args):
    destino = os.path.join(".git", "hooks", nome)
    conteudo = SHIM.format(python=sys.executable, hook=_hook_absoluto(), args=args)
    with open(destino, "w", encoding="utf-8") as arq:
        arq.write(conteudo)
    modo = os.stat(destino).st_mode
    os.chmod(destino, modo | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"instalado: {destino} -> commit_hook.py {args}")


def main():
    if not os.path.isdir(".git"):
        print("erro: rode da raiz do repositório (pasta .git ausente)", file=sys.stderr)
        return 1
    if not os.path.isfile(_hook_absoluto()):
        print("erro: scripts/hooks/commit_hook.py não encontrado", file=sys.stderr)
        return 1
    escrever("pre-commit", "pre-commit")
    escrever("post-commit", "post-commit")
    escrever("commit-msg", 'commit-msg "$@"')
    escrever("pre-push", "pre-push")
    print(RESUMO)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
