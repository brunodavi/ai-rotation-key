# Contribuindo

Guia de quem vai mexer no código. Para instalar e usar, comece pelo [README](README.md).

## Ambiente

```sh
git clone https://github.com/brunodavi/ai-rotation-key.git
cd ai-rotation-key
uv venv && uv pip install -e .        # ou: pip install -e .
python scripts/install-git-hooks.py   # uma vez por clone
```

Regras do ambiente:

- **Python puro: ZERO dependências** (runtime e dev), sem `requirements.txt`. Única exceção: `setuptools` como build-backend do empacotamento.
- Alvo: Python 3.14+.
- **Sem lint** — decisão registrada, não adicionar.
- **Nada fora do projeto**: fixtures de HOME em `tmp/.scratch/`, nunca `tempfile` do sistema (no Termux não existe `/tmp` no lugar). Tudo em `tmp/` é ignorado pelo git.

Estrutura: `main.py` (entrypoint), `src/cli.py` (só argparse/wiring), `src/commands/<comando>.py` (lógica de cada comando), `src/utils/<cada_funcao>.py` + `src/utils/__init__.py` (barrel), `scripts/` (hooks), `tests/`.

## Testes

```sh
python -m unittest discover -s tests -v   # suíte completa
python -m unittest tests.test_<modulo>    # um módulo
```

- unittest stdlib, unitários + integração.
- Integração **sempre** via `tests/mock_server.py`: rotas *as-is* com respostas registráveis em fila, `reset()` por teste, execução sequencial (1 worker, sem paralelismo).
- Porta efêmera por padrão; `AI_ROTATION_MOCK_PORT` fixa a porta com anti-colisão +1 (`find_free_port`).

## Workflow TDD & Git

TDD à risca: **validação do comportamento real → RED** (erro na asserção, stub mínimo necessário) **→ GREEN → REFACTOR** (REFACTOR é opcional no ciclo).

Branch de trabalho é a `dev` (antes `master`): commits diretos e push em **qualquer** estado — inclusive RED; `dev` é ambiente de desenvolvimento.

Formato do commit (validado pelo hook `commit-msg`):

```
<tipo>(<escopo-opcional>): <FASE> - <mensagem>
```

| tipo | fase |
|---|---|
| `test` | `RED` |
| `feat` | `GREEN` |
| `refactor` | `REFACTOR` |
| `fix` | `RED` ou `GREEN` |
| `docs` / `chore` | sem fase |
| `Merge` / `Revert` | imunes |

**Tags são PROD** (o `pre-push` valida): só sobem com versão semver **maior** que a última existente, batendo com `pyproject.toml`, com o pin de instalação do README apontando para a tag publicada, suíte verde e árvore limpa. A cada ciclo comprovado (suíte verde + validação manual do dono) suba a versão no `pyproject.toml` e crie a tag do estado estável.

## Hooks

`scripts/install-git-hooks.py` cria shims em `.git/hooks` que delegam para `scripts/hooks/commit_hook.py`. Os hooks são locais (`.git` não é versionado) — rode o script depois de cada clone.

| Hook | O que faz |
|---|---|
| `pre-commit` | varre o staged por segredos (`sk-`/`AIza…`), arquivo espúrio sem extensão e qualquer caminho em `tmp/`. **Não roda a suíte** — de propósito: o ciclo TDD exige commitar em RED. |
| `post-commit` | push automático do branch atual (`dev` sempre atualizado, mesmo em RED); nunca bloqueia o commit |
| `commit-msg` | valida o formato da mensagem acima |
| `pre-push` | gate de PROD para tags: semver, versão do `pyproject.toml`, pin do README, **suíte verde** e árvore limpa. Push de branch comum não testa. |

Para pular um gate deliberadamente: `git commit --no-verify`.

## Debug (tmux + pdb)

No Termux dá para depurar sem sair do terminal:

1. Adicione `breakpoint()` no ponto desejado (código e/ou teste).
2. `tmux new-session -d -s debug "python -m unittest tests.test_<modulo>.<Classe>.<metodo> -v"`
3. `tmux capture-pane -t debug -p` para ver a tela.
4. `tmux send-keys -t debug "<comando_pdb>" Enter` — úteis: `p <var>`, `n`, `s`, `c`, `l`, `w`, `q`.
5. `tmux kill-session -t debug` quando terminar.

Estratégia: debrue **apenas o teste que falha**, com `breakpoint()` relevantes — não rode a suíte inteira para depurar. Cuidado: se o script terminar antes de um `input()`/loop, a sessão tmux morre sozinha e o `capture-pane` mostra "no server running".

## Documentação

- [`docs/config.md`](docs/config.md) — referência do `config.json`
- [`docs/arquitetura.md`](docs/arquitetura.md) — fluxo, políticas, limitações e créditos
- `AGENTS.md` — instruções do agente que atua neste repo (mantido à parte do README)
