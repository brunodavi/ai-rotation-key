# Config

Arquivo: `~/.config/ai-rotation-key/config.json`

Crie com `airkey init` (escreve um exemplo) e edite com `airkey edit` (abre no `$EDITOR`, fallback `vi`). O servidor lê esse arquivo na subida.

## Formato

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

| Campo | Obrigatório | O que é |
|---|---|---|
| `port` | não | porta do servidor (padrão 8792); se estiver ocupada, deriva com +1 e loga a efetiva |
| `providers.<nome>` | sim | um dict por gateway — o nome é o namespace dos modelos dele |
| `api-keys` | sim | lista não vazia de strings; round-robin roda sobre ela |
| `models` | sim | lista não vazia de modelos expostos por esse provider |
| `base-url` | às vezes | endpoint raiz do upstream; tem default embutido para `gemini`, `openrouter` e `opencode-zen` (ver `src/providers/`), obrigatório para qualquer outro nome |
| `filter-models` | não | padrões glob usados pelo `sync-models` (ver abaixo) |

Formatos antigos (`model-keys`, `exclude-models`, `rota-models`, `sufixo-chat`) são rejeitados na carga, apontando o substituto — não há migração automática.

## Round-robin por provider

Cada provider tem seu próprio pool de chaves, e os modelos dele **dividem o mesmo ciclo**: um request usa a próxima chave da lista daquele provider, ciclicamente. O modelo pedido resolve para exatamente um provider (nome duplicado entre providers é erro de carga).

## Namespacing

- `/v1/models` e o `export` expõem os modelos como `<provider>/<modelo>` (ex.: `openrouter/gpt-4`, `opencode-zen/big-pickle`).
- O request aceita o nome prefixado ou o pelado. O pelado é aceito **só quando existe em um provider**; se existir em mais de um, o proxy responde `400` listando as opções — qualifique o que quiser.
- O prefixo é removido antes de repassar ao upstream: o config continua com os nomes pelados.
- O mesmo modelo em providers distintos é permitido.

## filter-models

Lista de padrões glob (case-sensitive, casam contra o id do modelo, sem prefixo `models/`):

- positivos = allowlist (se houver pelo menos um, só eles passam);
- `!padrão` remove (aplicado mesmo sem positivos);
- sem positivos, vale tudo menos os negativos — é assim que `!*tts*`, `!*image*`, `!*embedding*` e `!veo-*` cortam o que não serve para chat.

## sync-models

```sh
airkey sync-models          # todos os providers
airkey sync-models gemini   # apenas um
```

Faz `GET {base-url}{models-endpoint}` com a **primeira** chave do provider (auth via `auth-header`), resolve os ids com `path-models` (ou `data[].id`), aplica `filter-models` e adiciona ao config **só os que faltam** — nunca remove o que você já tinha e nunca testa os modelos (cota intacta).

Exit code `1` se qualquer provider falhar (HTTP ou conexão), mesmo com os outros ok. Um `path-models` que não encontra nada vira falha daquele provider, com o motivo no log.

## Gateway quase-compatível (mapeamento)

Providers cujo `/models` ou chat fogem do padrão OpenAI aceitam campos opcionais **flat** no próprio provider — todos ausentes = OpenAI-compatível puro:

```json
"meu-gateway": {
  "base-url": "https://gateway.exemplo/api",
  "api-keys": ["sua-chave"],
  "models-endpoint": "/catalogo",
  "path-models": "result.items[].modelId",
  "chat-endpoint": "/v2/chat",
  "chat-endpoint-stream": "/v2/chat:stream",
  "auth-header": "X-Key: {api-key}"
}
```

| Campo | O que faz | Default |
|---|---|---|
| `models-endpoint` | rota de descoberta anexada ao `base-url` | `/models` |
| `path-models` | caminho dot-path dos ids na resposta (null-safe: item sem o campo é pulado) | `data[].id` |
| `chat-endpoint` | rota anexada ao `base-url` no POST de chat; aceita `{model}` (ex.: `/models/{model}:generateContent`) | `/chat/completions` |
| `chat-endpoint-stream` | rota usada quando o cliente pede `stream: true` (também aceita `{model}`) | valor de `chat-endpoint` |
| `auth-header` | template do header de auth; `{api-key}` vira a chave do ciclo atual. Com `Nome: {api-key}` define também o nome do header (ex.: `x-goog-api-key: {api-key}`); sem dois-pontos, vira valor de `Authorization` | `Bearer {api-key}` |

O `path-models` precisa bater com a resposta **real** do gateway (o `sync-models` loga o erro se não achar nada); ids que venham como `models/<id>` têm o prefixo removido.

## OpenCode Zen (free)

Modelos free do zen funcionam até com a string `"public"` no lugar da key: `"api-keys": ["public"]` — é o mesmo acesso anônimo que o próprio opencode usa, limitado por IP pelo gateway. O proxy envia `User-Agent: ai-rotation-key/<versão>` em toda chamada upstream, requisito do Cloudflare do zen (rejeita o User-Agent padrão do Python).

Ver também: [`arquitetura.md`](arquitetura.md) — fluxo de um request, políticas e integração com o opencode.
