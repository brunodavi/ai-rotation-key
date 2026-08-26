"""Hook unificado do projeto — chamado pelos shims em .git/hooks.

Uso:
    commit_hook.py pre-commit            → nada de segredo/lixo/tmp no staged
    commit_hook.py commit-msg <arquivo>  → valida `<tipo>(<escopo>): [FASE - ]mensagem`
    commit_hook.py pre-push (stdin)      → tags são PROD: semver subindo, versão do
                                           pyproject consistente, pin do README na
                                           tag, SUÍTE verde, árvore limpa

Fases obrigatórias: test→RED · feat→GREEN · refactor→REFACTOR · fix→RED|GREEN.
docs/chore não levam fase. Merge/Revert são imunes.

A suíte NÃO roda no pre-commit de propósito: o fluxo TDD exige commitar em RED;
a qualidade é gateada apenas na publicação de tag (prod).
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
SEMVER_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def tags_de_push(stdin_texto):
    """Extrai nomes de tags das linhas de refs do stdin do pre-push."""
    tags = []
    for linha in stdin_texto.splitlines():
        partes = linha.split()
        if len(partes) >= 4 and partes[0].startswith("refs/tags/"):
            tags.append(partes[0].removeprefix("refs/tags/"))
    return tags


def _tupla_semver(tag):
    casado = SEMVER_TAG.match(tag)
    if not casado:
        return None
    return tuple(int(parte) for parte in casado.groups())


def ler_versao_pyproject(raiz="."):
    conteudo = open(os.path.join(raiz, "pyproject.toml"), encoding="utf-8").read()
    casado = re.search(r'^version\s*=\s*"([^"]+)"', conteudo, flags=re.M)
    return casado.group(1) if casado else ""


PIN_README = re.compile(r"git\+https://github\.com/brunodavi/ai-rotation-key\.git@(\S+)")


def validar_pin_readme(tag, raiz="."):
    """O pin de instalação do README precisa apontar para a tag publicada."""
    try:
        conteudo = open(os.path.join(raiz, "README.md"), encoding="utf-8").read()
    except OSError:
        return "README.md não encontrado — o pin de instalação (@vX.Y.Z) é obrigatório"
    casado = PIN_README.search(conteudo)
    if not casado:
        return ("README.md sem pin de instalação — inclua "
                "'pip install git+...ai-rotation-key.git@" + tag + "'")
    pin = casado.group(1)
    if pin != tag:
        return (f"pin do README (@{pin}) não bate com a tag '{tag}' — "
                f"atualize o README antes de publicar")
    return None


def validar_tag(tag, versao, tags_existentes):
    """Valida uma tag a ser publicada (prod). Retorna None ou texto do erro."""
    tupla = _tupla_semver(tag)
    if tupla is None:
        return f"tag '{tag}' fora do padrão semver vX.Y.Z"

    if tag != f"v{versao}":
        return (f"tag '{tag}' não bate com a versão do pyproject.toml "
                f"(v{versao}) — suba a versão antes de taggear")

    maior_existente = max(
        (_tupla_semver(t) for t in tags_existentes if _tupla_semver(t)),
        default=(0, 0, 0),
    )
    if tupla <= maior_existente:
        return (f"versão '{tag}' precisa ser MAIOR que a maior já existente "
                f"(v{maior_existente[0]}.{maior_existente[1]}.{maior_existente[2]})")
    return None


def pre_push():
    tags = tags_de_push(sys.stdin.read())
    if not tags:
        _saida("push sem tags — nada a validar (dev pode subir em qualquer estado)")
        return 0

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

    sujo = subprocess.run(["git", "status", "--porcelain"],
                          capture_output=True, text=True).stdout.strip()
    if sujo:
        falhas.append("árvore de trabalho não está limpa — commite antes de taggear")

    versao = ler_versao_pyproject()
    locais = set(subprocess.run(["git", "tag", "-l", "v*"],
                                capture_output=True, text=True).stdout.split())
    for tag in tags:
        erro = validar_tag(tag, versao, locais - {tag})
        if erro:
            falhas.append(erro)
            continue
        erro = validar_pin_readme(tag)
        if erro:
            falhas.append(erro)

    for item in falhas:
        _erro(item)
    if falhas:
        _saida("tag é PROD: corrija tudo antes de publicar (--no-verify para forçar)")
        return 1
    _saida(f"tags OK: {', '.join(tags)}")
    return 0


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
        print("uso: commit_hook.py <pre-commit | commit-msg <arquivo> | pre-push>",
              file=sys.stderr)
        return 2
    if argv[1] == "pre-commit":
        return pre_commit()
    if argv[1] == "pre-push":
        return pre_push()
    if argv[1] == "commit-msg" and len(argv) >= 3:
        return commit_msg(argv[2])
    print("uso: commit_hook.py <pre-commit | commit-msg <arquivo> | pre-push>",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
