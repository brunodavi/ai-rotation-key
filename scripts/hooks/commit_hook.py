"""Hook unificado do projeto — chamado pelos shims em .git/hooks.

Uso:
    commit_hook.py pre-commit            → suíte verde + nada de segredo/lixo no staged
    commit_hook.py commit-msg <arquivo>  → valida `<tipo>(<escopo>): [FASE - ]mensagem`

Fases obrigatórias: test→RED · feat→GREEN · refactor→REFACTOR · fix→RED|GREEN.
docs/chore não levam fase. Merge/Revert são imunes.
"""

import os
import re
import subprocess
import sys

FASE_OBRIGATORIA = {
    "test": {"RED"},
    "feat": {"GREEN"},
    "refactor": {"REFACTOR"},
    "fix": {"RED", "GREEN"},
}
SEM_FASE = {"docs", "chore"}
SEGREDOS = re.compile(
    r"(sk-or-v1-|sk-proj-|sk-ant-api|AIza)[A-Za-z0-9_\-]{10,}|sk-[A-Za-z0-9]{32,}"
)


def _erro(texto):
    print(f"[hook] BLOQUEADO: {texto}", file=sys.stderr)
    return 1


def _saida(texto):
    print(f"[hook] {texto}", file=sys.stderr)


def validar_mensagem(primeira_linha):
    """Retorna None se a mensagem segue o padrão; texto do erro caso contrário."""
    if primeira_linha.startswith(("Merge ", "Revert ")):
        return None

    casado = re.match(r"^([a-z]+)(\([^)]*\))?: (.+)$", primeira_linha)
    if not casado:
        return ("use '<tipo>(<escopo>): <mensagem>' — "
                "tipos: test/feat/fix/refactor/docs/chore")
    tipo, _, resto = casado.groups()

    if tipo in SEM_FASE:
        if re.match(r"^(RED|GREEN|REFACTOR) - ", resto):
            return f"'{tipo}' não leva fase TDD"
        return None

    validas = ", ".join(sorted(FASE_OBRIGATORIA.get(tipo, {"RED", "GREEN", "REFACTOR"})))
    fase = re.match(r"^(RED|GREEN|REFACTOR) - .+$", resto)
    if not fase:
        return (f"'{tipo}' exige fase TDD ({validas}) — "
                f"ex.: '{tipo}(escopo): GREEN - mensagem'")
    if resto.split(" ")[0] not in FASE_OBRIGATORIA.get(tipo, set(fase.group(1))):
        return f"fase inválida para '{tipo}' (use {validas})"
    return None


def falhas_de_staged(caminhos):
    """Recebe caminhos staged; retorna lista de problemas (vazia = limpo)."""
    falhas = []
    for caminho in caminhos:
        if caminho == "tmp" or caminho.startswith("tmp/"):
            falhas.append(f"tmp/ nunca vai pro repo (gitignore ou --no-verify se for intencional): {caminho!r}")
            continue
        if re.fullmatch(r"[^A-Za-z._-]+", os.path.basename(caminho)):
            falhas.append(f"arquivo espúrio no staged: {caminho!r}")
            continue
        try:
            conteudo = open(caminho, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        achado = SEGREDOS.search(conteudo)
        if achado:
            falhas.append(
                f"possível segredo em {caminho} (padrão {achado.group(0)[:14]}...)"
            )
    return falhas


def pre_commit():
    falhas = []

    resultado = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        falhas.append("suíte de testes falhou:\n" + (resultado.stderr or "")[-2000:])
    else:
        _saida("suíte verde")

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        capture_output=True,
        text=True,
    ).stdout.split("\0")
    falhas.extend(falhas_de_staged(filter(None, staged)))

    for item in falhas:
        _erro(item)
    if falhas:
        _saida("corrija e tente de novo; para pular deliberadamente: git commit --no-verify")
        return 1
    return 0


def commit_msg(caminho_msg):
    primeira = open(caminho_msg, encoding="utf-8").readline().strip()
    erro = validar_mensagem(primeira)
    if erro:
        return _erro(erro)
    return 0


def main(argv):
    if len(argv) < 2:
        print("uso: commit_hook.py <pre-commit | commit-msg <arquivo>>", file=sys.stderr)
        return 2
    if argv[1] == "pre-commit":
        return pre_commit()
    if argv[1] == "commit-msg" and len(argv) >= 3:
        return commit_msg(argv[2])
    print("uso: commit_hook.py <pre-commit | commit-msg <arquivo>>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
