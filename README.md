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
ai-rotation-key init

# Abre o config no $EDITOR (fallback: vi)
ai-rotation-key edit

# Sobe o servidor local (escuta apenas em 127.0.0.1)
ai-rotation-key start

# Registra este servidor como provider no ~/.config/opencode/config.json (idempotente, não duplica)
ai-rotation-key export
```

### Config

`~/.config/ai-rotation-key/config.json` — mapa de nome de modelo → lista de chaves, pensado para integração com o opencode. Round-robin por modelo: cada request usa a próxima chave da lista do modelo pedido, ciclicamente.

```json
{
  "model-keys": {
    "<nome-modelo>": ["sk-sua-chave-1", "sk-sua-chave-2"]
  }
}
```

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
