# ai-rotation-key

Roteador local de chaves de APIs de IA: um único endpoint OpenAI-compatível em `127.0.0.1`, com round-robin entre as chaves de cada modelo.

## O problema

Toda ferramenta de rotação/proxy de chaves quebra no Termux: elas dependem de Rust para compilar. Este projeto é **Python puro** — zero dependências (runtime e dev), só stdlib — então instala em segundos onde houver Python 3.14+.

O que ele faz:

- **Round-robin por modelo** — cada request usa a próxima chave daquele modelo, ciclicamente; os modelos de um provider dividem o ciclo das chaves dele.
- **Failover automático** — em 429 (cota) ou queda de conexão ele tenta a próxima chave; em 400/404 repassa direto, sem gastar o pool.
- **Um endpoint só** — o cliente aponta para `http://127.0.0.1:8792/v1` e o proxy cuida das chaves, do upstream e das assinaturas do Gemini.

## Instalação

Requisito: **Python 3.14+**. Fixe sempre a última tag (`v0.8.0`): toda tag passou por suíte verde e validação manual. A branch `dev` é trabalho em andamento.

### uv (recomendado)

```sh
uv tool install git+https://github.com/brunodavi/ai-rotation-key.git@v0.8.0
```

### pipx

```sh
pipx install git+https://github.com/brunodavi/ai-rotation-key.git@v0.8.0
```

### pip

```sh
pip install git+https://github.com/brunodavi/ai-rotation-key.git@v0.8.0
```

**No Linux:** o `pip` do sistema é gerenciado pela distribuição (PEP 668) — instalar assim é recusado, e a saída sugerida, `--break-system-packages`, é justamente a que pode quebrar pacotes do próprio sistema. Use `uv` ou `pipx` nesse caso.

**No Termux:** não existe essa trava e, como o projeto não tem dependências, não há nada a quebrar — `pip install` funciona direto.

## Uso

```sh
airkey init        # cria ~/.config/ai-rotation-key/config.json de exemplo
airkey edit        # abre o config no $EDITOR (use --opencode para o config do opencode)
airkey start       # sobe o servidor em 127.0.0.1 (porta do config, padrão 8792)
airkey export      # registra o servidor como provider no opencode (idempotente)
airkey sync-models # adiciona ao config os modelos que faltam (sync-models <provider> para um só)
```

Fluxo usual: `init` → edite o config com suas chaves → `sync-models` → `start` (ou `export` para usar pelo opencode). Formato do config em [`docs/config.md`](docs/config.md).

O comando canônico é `ai-rotation-key`; `airkey` é o atalho — os dois fazem o mesmo.

## Como funciona

O proxy recebe a chamada OpenAI-compatível, escolhe a próxima chave do modelo e repassa ao upstream; as respostas são sanitizadas e as `thought_signature` do Gemini 3.x voltam sozinhas para o histórico. O servidor escuta **apenas em `127.0.0.1`** e as chaves ficam somente no seu config local.

Fluxo completo, políticas, integração com o opencode e limitações: [`docs/arquitetura.md`](docs/arquitetura.md).

## Desenvolvimento

```sh
git clone https://github.com/brunodavi/ai-rotation-key.git
cd ai-rotation-key
uv venv && uv pip install -e .        # ou: pip install -e .
python scripts/install-git-hooks.py   # uma vez por clone
python -m unittest discover -s tests -v
```

TDD, formato de commit e o que cada hook faz: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Documentação

- [`docs/config.md`](docs/config.md) — referência do `config.json`: providers, namespacing, `filter-models`, mapeamento de gateway
- [`docs/arquitetura.md`](docs/arquitetura.md) — fluxo de um request, políticas, limitações e créditos
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — ambiente de dev, ciclo TDD, commits e hooks

## Licença

[MIT](LICENSE). Inspirado em [LiteLLM](https://github.com/BerriAI/litellm), [Hydra-gemini](https://github.com/LikithMeruvu/Hydra-gemini) e [Vercel AI SDK](https://sdk.vercel.ai/) — créditos em [`docs/arquitetura.md`](docs/arquitetura.md).

> Projeto desenvolvido com assistência de IA (OpenCode).
