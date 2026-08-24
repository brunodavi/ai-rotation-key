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
- Empacotamento: pyproject.toml com `[project.scripts]`; o CLI vira comando `ai-rotation-key` (atalho: `airkey`) após `pip install -e .`
- Python alvo: 3.14.6 (versão instalada neste Termux)
- CLI: `init` (cria config.json de exemplo), `edit` (abre o config), `start` (sobe servidor), `export` (registra o provider no opencode), `sync-models [provider]` (adiciona faltantes de /models ao config, respeitando filter-models; exit 1 com falha parcial)
  - Parsing com argparse
  - `edit` usa `$EDITOR` com fallback `vi` (subprocess.run); flag `--opencode` abre o config do opencode
  - `export` adiciona este servidor como provider em ~/.config/opencode/config.json: lê o JSON existente, checa se o provider já existe antes de adicionar (idempotente, não duplica), preserva os demais providers e escreve de volta com módulo json
    - Validado ao vivo (tmp/spikes/opencode-custom-provider.md): config.json É carregado pelo opencode; usar id próprio + npm "@ai-sdk/openai-compatible" + baseURL http://127.0.0.1:<porta>/v1; NUNCA sobrescrever providers embutidos (openai usa /v1/responses e hijacka o small_model interno); models saem das chaves do model-keys
- Config: ~/.config/ai-rotation-key/config.json (ler/escrever com módulo json)
  - Formato v0.2.0: {"port": 8792, "providers": {"<nome>": {"base-url": "...", "api-keys": [...], "models": [...]}}}
  - base-url opcional para providers com default no registro (gemini, openrouter, opencode-zen — ver src/providers/)
  - Namespacing: /v1/models e export expõem `<provider>/<modelo>`; request aceita prefixado ou pelado (pelado ambíguo entre providers → 400 com opções); prefixo removido antes do upstream; config continua com nomes pelados; mesmo modelo em providers distintos é permitido
  - Rotação por provider (modelos do mesmo provider dividem o ciclo); formato antigo model-keys rejeitado
- HTTP 100% stdlib: servidor com http.server.ThreadingHTTPServer, chamadas upstream com urllib.request
- Rotação: round-robin simples por modelo — cada request usa a próxima chave da lista do modelo pedido, ciclicamente
- Rotação NUNCA acontece em 400/404 (chave válida/request ruim/modelo morto) — só em 429 e erro de conexão
- thought_signature de tool calls (Gemini 3.x): cache `id → assinatura` e reinjeção no histórico do turno seguinte (`src/utils/signature_cache.py`) — a API exige o round-trip e o cliente não deve ver extra_content
- Testes: unittest stdlib, unitários + integração

# Estrutura
- main.py (entrypoint), src/cli.py (só argparse/wiring), src/commands/<comando>.py (lógica de cada comando CLI), src/utils/__init__.py (barrel) + src/utils/<cada_funcao>.py
- tests/, tmp/ (ignorado pelo git)

# Convenções
- Conventional commits
- README.md simples: instalação direta via `pip install git+https://github.com/brunodavi/ai-rotation-key.git`, comandos e motivação (erro no Termux por causa do Rust)

# Workflow TDD & Git
- Uma branch por parte (`feat/<nome>` / `fix/<nome>`); commits entre os ciclos RED → GREEN → REFACTOR dentro da branch (`test:`, `feat:`, `refactor:`)
- Merge na master SOMENTE após validação manual do usuário e confirmação explícita
- Partes independentes em git worktrees sob `tmp/wt/<branch>`, implementadas por agentes em paralelo
- Barrel `src/utils/__init__.py` NÃO é editado nas branches — imports diretos do módulo; consolidação acontece pós-merge na master
- Testes de integração SEMPRE via `tests/mock_server.py`: rotas as-is com respostas registráveis, `reset()` por teste, sequenciais (1 worker, sem paralelismo)
- Porta em teste: efêmera por padrão; se fixada via `AI_ROTATION_MOCK_PORT`, anti-colisão +1 (`find_free_port`)
- NADA fora do projeto (Termux não tem /tmp): fixtures de HOME em `tmp/.scratch/`, nunca tempfile do sistema; servidor real deriva porta com +1 e loga a efetiva

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
- [x] Gemini
- [x] OpenRouter
- [x] OpenCode Zen
- [ ] OpenCode Go (pausado: exige assinatura/cartão)
- [ ] OpenAi
- [ ] Qwen

# Planejamento & Tarefas
- Tarefas vivem em `TODO_LIST.md` (raiz do repo). Escrita NELE é EXCLUSIVA do agente `planner`
  (`.opencode/agent/planner.md`).
- Agente `planner`: investiga o projeto (código, testes, docs, tmp/spikes) + web, e registra tarefas
  no TODO_LIST.md SEMPRE fechando escopo com perguntas ao dono até a tarefa ficar inequívoca para
  quem for executar. Permissões: leitura de tudo, escrita SÓ em TODO_LIST.md, sem bash, sem subagentes,
  nunca executa tarefas.
- Fluxo: ideia vaga → sessão com `planner` (primário ou @planner) → tarefa especificada na fila →
  outra sessão cria a branch (`feat/<nome>` etc.) e executa conforme Workflow TDD & Git →
  ao concluir, pedir ao `planner` para marcar `[x]` e mover para Concluídas.

# Repositórios de Referência
- HydraGemini
- LiteLLM
