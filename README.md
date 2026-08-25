# ai-rotation-key

Roteador round-robin de chaves de APIs de IA. Leve e simples, feito para rodar no Termux.

## Motivação

Ferramentas comuns de rotação/proxy de chaves quebram no Termux por exigirem Rust para compilar dependências. Este projeto é **Python puro**: zero dependências em runtime e desenvolvimento — só stdlib (setuptools entra apenas como build-backend do empacotamento).

## Instalação

```sh
pip install git+https://github.com/brunodavi/ai-rotation-key.git@v0.5.0
```

Requisito: Python 3.14+. A branch padrão (`dev`) recebe trabalho em andamento — para uso estável, instale sempre fixando a **última tag** (toda tag passou por suíte verde e validação manual).

Desenvolvimento (clone + editable + hooks):

```sh
git clone https://github.com/brunodavi/ai-rotation-key.git
cd ai-rotation-key
pip install -e .
python scripts/install-git-hooks.py   # uma vez: suíte+segredos no commit, gate de versão no push de tags
```

## Uso

```sh
# Cria config de exemplo em ~/.config/ai-rotation-key/config.json
airkey init

# Abre o config no $EDITOR (fallback: vi)
airkey edit

# Abre o config do opencode (~/.config/opencode/config.json)
airkey edit --opencode

# Sobe o servidor local (escuta apenas em 127.0.0.1)
airkey start

# Registra este servidor como provider no ~/.config/opencode/config.json (idempotente, não duplica)
airkey export

# Busca /models de cada provider e adiciona os faltantes ao config
airkey sync-models          # todos os providers
airkey sync-models gemini   # apenas um
```

O comando canônico é `ai-rotation-key`; `airkey` é o atalho — use o que preferir, ambos fazem o mesmo.

### Config

`~/.config/ai-rotation-key/config.json` — providers com suas chaves e modelos. Round-robin **por provider**: os modelos de um provider dividem o ciclo das chaves dele. `base-url` é opcional para `gemini`, `openrouter` e `opencode-zen` (defaults embutidos) e obrigatório para outros providers.

> Dica OpenCode Zen: modelos free funcionam até com a string `"public"` no lugar da key (`"api-keys": ["public"]`) — é o mesmo acesso anônimo que o próprio opencode usa, limitado por IP pelo gateway. O proxy envia um `User-Agent` próprio em todas as chamadas upstream (requisito do Cloudflare do zen).

```json
{
  "port": 8792,
  "providers": {
    "gemini": {
      "api-keys": ["sk-exemplo-1", "sk-exemplo-2"],
      "filter-models": ["!*tts*", "!*image*", "!*embedding*", "!veo-*"],
      "models": ["gemini-3.5-flash", "gemini-3.1-flash-lite"]
    },
    "openai": {
      "base-url": "https://api.openai.com/v1",
      "api-keys": ["sk-sua-chave-openai"],
      "models": ["gpt-4o-mini"]
    }
  }
}
```

`sync-models` lista os modelos de cada provider via `GET {base-url}/models` e adiciona só os faltantes — **nunca testa os modelos** (cota intacta) e nunca remove o que você já tinha. Padrões glob em `filter-models` filtram candidatos: positivos são allowlist, `!padrão` remove; sem positivos, tudo menos os negativos (TTS, imagem, embeddings etc.); casam com o id sem prefixo `models/`.

Os modelos são expostos com namespace `<provider>/<modelo>` (ex.: `openrouter/gpt-4`, `opencode-zen/big-pickle`) para evitar confusão entre gateways; requests aceitam também o nome pelado quando ele só existe em um provider. O mesmo modelo em providers distintos é permitido — qualifique quando ambos atenderem.

### Gateway quase-compatível (mapeamento customizado)

Providers cujo `/models` ou chat fogem do padrão OpenAI aceitam campos opcionais de mapeamento — todos ausentes = comportamento padrão:

```json
"meu-gateway": {
  "base-url": "https://gateway.exemplo/api",
  "api-keys": ["sua-chave"],
  "models-endpoint": "/catalogo",
  "path-models": "result.items[].modelId",
  "chat-endpoint": "/v2/chat",
  "auth-header": "X-Key: {api-key}"
}
```

| Campo | O que faz | Default |
|---|---|---|
| `models-endpoint` | rota de descoberta anexada ao `base-url` | `/models` |
| `path-models` | caminho dot-path dos ids na resposta (null-safe: item sem o campo é pulado) | `data[].id` |
| `chat-endpoint` | rota anexada ao `base-url` no POST de chat | `/chat/completions` |
| `auth-header` | template do header de autenticação (`{api-key}` vira a chave do ciclo atual) | `Bearer {api-key}` |

Se `path-models` não encontrar nada, o `sync-models` reporta falha daquele provider com o motivo — nada é adicionado.

## Como funciona

O proxy recebe chamadas OpenAI-compatíveis, escolhe a próxima chave do modelo pedido (round-robin) e repassa ao upstream. Em 429 ou erro de conexão ele tenta automaticamente a próxima chave; em 400/404 repassa direto sem gastar o pool. Assinaturas `thought_signature` de tool calls (exigidas pelo Gemini 3.x no turno seguinte) são guardadas e reinjetadas automaticamente — o cliente nunca vê campos extras.

Detalhes, políticas e limitações: [`docs/arquitetura.md`](docs/arquitetura.md).

## Inspiração

Inspirado (e creditado) em [LiteLLM](https://github.com/BerriAI/litellm), [Hydra-gemini](https://github.com/LikithMeruvu/Hydra-gemini) e [Vercel AI SDK](https://sdk.vercel.ai/) — ver seção de créditos na documentação de arquitetura.

## Desenvolvimento

Branch padrão é a `dev` (trabalho em andamento); as **tags são as versões estáveis** — cada tag passou pela suíte completa e validação manual antes de ser publicada (o push de tag valida semver, consistência com o `pyproject.toml`, suíte e árvore limpa).

Testes (unittest stdlib):

```sh
python -m unittest discover -s tests -v
```

Commits seguem `<tipo>(<escopo>): <FASE> - <mensagem>`, com fase TDD por tipo (test→RED, feat→GREEN, refactor→REFACTOR, fix→RED|GREEN; docs/chore sem fase) — o hook de commit-msg valida.

## Segurança

O servidor escuta **apenas em `127.0.0.1`** — suas chaves e requests não ficam acessíveis de outros dispositivos da rede. As chaves ficam somente no seu config local; o projeto não as envia para nenhum lugar além do upstream configurado. O hook de pre-commit escaneia tudo que vai ser commitado em busca de padrões de chave de API e bloqueia o commit se encontrar algo.

Gemini 3.x exige que a `thought_signature` dos tool calls volte no histórico do turno seguinte: o proxy guarda essas assinaturas em cache e reinjeta automaticamente — o cliente nunca vê campos extras.

## Licença

[MIT](LICENSE)

> Projeto desenvolvido com assistência de IA (OpenCode).
