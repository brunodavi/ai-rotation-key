# ai-rotation-key

Roteador round-robin de chaves de APIs de IA. Leve e simples, feito para rodar no Termux.

## Motivação

Ferramentas comuns de rotação/proxy de chaves quebram no Termux por exigirem Rust para compilar dependências. Este projeto é **Python puro**: zero dependências em runtime e desenvolvimento — só stdlib (setuptools entra apenas como build-backend do empacotamento).

## Instalação

```sh
pip install git+https://github.com/brunodavi/ai-rotation-key.git
```

Requisito: Python 3.14+

Desenvolvimento (clone + editable):

```sh
git clone https://github.com/brunodavi/ai-rotation-key.git
cd ai-rotation-key
pip install -e .
```

## Uso

```sh
# Cria config de exemplo em ~/.config/ai-rotation-key/config.json
ai-rotation-key init   # ou use o atalho: airkey init

# Abre o config no $EDITOR (fallback: vi)
ai-rotation-key edit

# Sobe o servidor local (escuta apenas em 127.0.0.1)
ai-rotation-key start

# Registra este servidor como provider no ~/.config/opencode/config.json (idempotente, não duplica)
ai-rotation-key export

# Busca /models de cada provider e adiciona os faltantes ao config
airkey sync-models          # todos os providers
airkey sync-models gemini   # apenas um
```

### Config

`~/.config/ai-rotation-key/config.json` — providers com suas chaves e modelos. Round-robin **por provider**: os modelos de um provider dividem o ciclo das chaves dele. `base-url` é opcional para `gemini` (default embutido) e obrigatório para outros providers.

```json
{
  "port": 8792,
  "providers": {
    "gemini": {
      "api-keys": ["sk-exemplo-1", "sk-exemplo-2"],
      "exclude-models": ["*tts*", "*image*", "*embedding*", "veo-*"],
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

`sync-models` lista os modelos de cada provider via `GET {base-url}/models` e adiciona só os faltantes — **nunca testa os modelos** (cota intacta) e nunca remove o que você já tinha. Padrões glob em `exclude-models` filtram candidatos indesejados (TTS, imagem, embeddings etc.); casam com o id sem prefixo `models/`.

> v0.2.0: o formato antigo com `model-keys` foi removido — recrie o config com `airkey init`.

## Como funciona

O proxy recebe chamadas OpenAI-compatíveis, escolhe a próxima chave do modelo pedido (round-robin) e repassa ao upstream. Em 429 ou erro de conexão ele tenta automaticamente a próxima chave; em 400/404 repassa direto sem gastar o pool. Assinaturas `thought_signature` de tool calls (exigidas pelo Gemini 3.x no turno seguinte) são guardadas e reinjetadas automaticamente — o cliente nunca vê campos extras.

Detalhes, políticas e limitações: [`docs/arquitetura.md`](docs/arquitetura.md).

## Inspiração

Inspirado (e creditado) em [LiteLLM](https://github.com/BerriAI/litellm), [Hydra-gemini](https://github.com/LikithMeruvu/Hydra-gemini) e [Vercel AI SDK](https://sdk.vercel.ai/) — ver seção de créditos na documentação de arquitetura.

## Desenvolvimento

Testes (unittest stdlib):

```sh
python -m unittest discover -s tests -v
```

## Segurança

O servidor escuta **apenas em `127.0.0.1`** — suas chaves e requests não ficam acessíveis de outros dispositivos da rede. As chaves ficam somente no seu config local; o projeto não as envia para nenhum lugar além do upstream configurado.

Gemini 3.x exige que a `thought_signature` dos tool calls volte no histórico do turno seguinte: o proxy guarda essas assinaturas em cache e reinjeta automaticamente — o cliente nunca vê campos extras.

## Licença

[MIT](LICENSE)

> Projeto desenvolvido com assistência de IA (OpenCode).
