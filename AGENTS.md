# Objetivo
Roteador round-robin de chaves de APIs de IA. Leve e simples, para funcionar no Termux (motivação: ferramentas comuns quebram no Termux por exigirem Rust para compilar).

# Comandos
- Instalar (dev): `pip install -e .`
- Todos os testes: `python -m unittest discover -s tests -v`
- Um módulo de teste: `python -m unittest tests.test_<modulo>`
- Sem lint (decisão: não adicionar)

# Tech
- Python puro: ZERO dependências, runtime e dev. Sem requirements.txt
  - Única exceção: setuptools como build-backend do empacotamento (nativo do Python)
- Empacotamento: pyproject.toml com `[project.scripts]`; o CLI vira comando `ai-rotation-key` após `pip install -e .`
- Python alvo: 3.14.6 (versão instalada neste Termux)
- CLI: `init` (cria config.json de exemplo), `edit` (abre o config), `start` (sobe servidor), `export` (registra o provider no opencode)
  - Parsing com argparse
  - `edit` usa `$EDITOR` com fallback `vi` (subprocess.run)
  - `export` adiciona este servidor como provider em ~/.config/opencode/config.json: lê o JSON existente, checa se o provider já existe antes de adicionar (idempotente, não duplica), preserva os demais providers e escreve de volta com módulo json
- Config: ~/.config/ai-rotation-key/config.json (ler/escrever com módulo json)
  - Formato: {"model-keys": {"<nome-modelo>": ["sk-chave1", "sk-chave2"]}}
  - Chave por nome de modelo — formato escolhido para integração com o opencode
- HTTP 100% stdlib: servidor com http.server.ThreadingHTTPServer, chamadas upstream com urllib.request
- Rotação: round-robin simples por modelo — cada request usa a próxima chave da lista do modelo pedido, ciclicamente
- Testes: unittest stdlib, unitários + integração

# Estrutura
- main.py (entrypoint), src/cli.py, src/utils/__init__.py (barrel) + src/utils/<cada_funcao>.py
- tests/, tmp/ (ignorado pelo git)

# Convenções
- Conventional commits
- README.md simples: instalação direta via `pip install git+https://github.com/brunodavi/ai-rotation-key.git`, comandos e motivação (erro no Termux por causa do Rust)

# Agent
- Usar ./tmp para guardar informações e validações sobre APIs/documentações e seus contratos reais
    - ./tmp/spikes: validações encontradas em .md
    - ./tmp/apis/<nome>: pastas com request/response
    - ./tmp/scripts: validar lib nativa do Python ou debug
    - ./tmp/repos: clones shallow de repositórios de referência, só para leitura (HydraGemini, LiteLLM)
- Sempre validar o comportamento real antes de assumir
- Sempre seguir TDD à risca: validação do comportamento real → RED (erro na asserção, stub mínimo necessário) → GREEN → REFACTOR
- Projeto também usado como harness para validar comportamento do opencode

# Modelos/Gateways
- [ ] Gemini
- [ ] OpenRouter
- [ ] OpenCode Zen
- [ ] OpenCode Go
- [ ] OpenAi
- [ ] Deep Seek
- [ ] Qwen

# Repositórios de Referência
- HydraGemini
- LiteLLM
