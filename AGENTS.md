# Objetivo
Roteador round-robin de chaves de APIs de IA. Leve e simples, para funcionar no Termux (motivação: ferramentas comuns quebram no Termux por exigirem Rust para compilar).

# Comandos
- Instalar (dev): `pip install -e .`
- Instalar hooks git (uma vez por clone): `python scripts/install-git-hooks.py`
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
    - Validado ao vivo (tmp/spikes/opencode-custom-provider.md): config.json É carregado pelo opencode; usar id próprio + npm "@ai-sdk/openai-compatible" + baseURL http://127.0.0.1:<porta>/v1; NUNCA sobrescrever providers embutidos (openai usa /v1/responses e hijacka o small_model interno); models do export usam key namespaced `<provider>/<modelo>` e name curto em 2 níveis
- Config: ~/.config/ai-rotation-key/config.json (ler/escrever com módulo json)
  - Formato atual: {"port": 8792, "providers": {"<nome>": {"base-url": "...", "api-keys": [...], "filter-models": [...], "models": [...]}}}
  - base-url opcional para providers com default no registro (gemini, openrouter, opencode-zen — ver src/providers/)
  - Namespacing: /v1/models e export expõem `<provider>/<modelo>`; request aceita prefixado ou pelado (pelado ambíguo entre providers → 400 com opções); prefixo removido antes do upstream; config continua com nomes pelados; mesmo modelo em providers distintos é permitido
  - Rotação por provider (modelos do mesmo provider dividem o ciclo); formato antigo model-keys rejeitado
- HTTP 100% stdlib: servidor com http.server.ThreadingHTTPServer, chamadas upstream com urllib.request
- Toda chamada upstream (forward/stream/fetch_models) envia `User-Agent: ai-rotation-key/<versão>` (`src/utils/user_agent.py`) — o gateway do OpenCode Zen rejeita User-Agent Python atrás do Cloudflare (erro 1010)
- Rotação: round-robin simples por modelo — cada request usa a próxima chave da lista do modelo pedido, ciclicamente
- Rotação NUNCA acontece em 400/404 (chave válida/request ruim/modelo morto) — só em 429 e erro de conexão
- thought_signature de tool calls (Gemini 3.x): cache `id → assinatura` e reinjeção no histórico do turno seguinte (`src/utils/signature_cache.py`) — a API exige o round-trip e o cliente não deve ver extra_content
- Testes: unittest stdlib, unitários + integração

# Estrutura
- main.py (entrypoint), src/cli.py (só argparse/wiring), src/commands/<comando>.py (lógica de cada comando CLI), src/utils/__init__.py (barrel) + src/utils/<cada_funcao>.py, scripts/ (hooks git: install-git-hooks.py + hooks/commit_hook.py), tmp/todo-list/ (fila de tarefas)
- tests/, tmp/ (ignorado pelo git)

# Convenções
- Commits seguem o padrão com fase TDD definido em # Workflow TDD & Git (validado pelo hook commit-msg)
- README.md enxuto: instalação fixando a última tag, comandos e motivação (erro no Termux por causa do Rust); sem notas de migração de versões antigas

# Workflow TDD & Git
- TDD à risca: validação do comportamento real → RED (erro na asserção, stub mínimo necessário) → GREEN → REFACTOR
- Branch de trabalho é a `dev` (antes `master`): commits diretos e push em QUALQUER estado — inclusive RED; dev é ambiente de desenvolvimento
  - Formato: `<tipo>(<escopo-opcional>): <FASE> - <mensagem>` · Fase por tipo: test→RED ·
    feat→GREEN · refactor→REFACTOR · fix→RED|GREEN · docs/chore SEM fase · Merge/Revert imunes ·
    REFACTOR é opcional no ciclo
- TAGS são PROD (pre-push valida): só sobem com versão semver MAIOR que a última existente, batendo com `pyproject.toml`, suíte verde e árvore limpa
- A cada ciclo comprovado — suíte verde + validação manual do dono — subir a versão no pyproject e criar a tag do estado estável
- Hooks automáticos (`scripts/install-git-hooks.py`, uma vez por clone):
  - pre-commit: escaneia staged por segredos (sk-/AIza…), arquivo espúrio sem extensão e
    qualquer caminho em tmp/ — NÃO roda a suíte (o ciclo TDD exige commitar em RED)
  - commit-msg: valida o formato acima
  - pre-push: gate de PROD para tags (versão/semver/suíte/árvore) — é AQUI que a suíte roda
    no push; push de branch comum não testa (dev aceita qualquer estado)
- Testes de integração SEMPRE via `tests/mock_server.py`: rotas as-is com respostas registráveis, `reset()` por teste, sequenciais (1 worker, sem paralelismo)
- Porta em teste: efêmera por padrão; se fixada via `AI_ROTATION_MOCK_PORT`, anti-colisão +1 (`find_free_port`)
- NADA fora do projeto (Termux não tem /tmp): fixtures de HOME em `tmp/.scratch/`, nunca tempfile do sistema; servidor real deriva porta com +1 e loga a efetiva

# Agent
- Usar ./tmp para guardar informações e validações sobre APIs/documentações e seus contratos reais
    - ./tmp/spikes: validações encontradas em .md
    - ./tmp/apis/<nome>: pastas com request/response
    - ./tmp/scripts: validar lib nativa do Python ou debug
    - ./tmp/repos: clones shallow de repositórios de referência, só para leitura (HydraGemini, LiteLLM, opencode)
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
- Tarefas vivem em `tmp/todo-list/` (gitignored, local ao dono) — flat, SEM subpastas de status:
  todo `.md` ali é pendente; o que está em andamento é o arquivo que a sessão corrente implementa
  (código não-committado na dev registra o resto); tarefa pronta = arquivo apagado — NÃO há
  TODO_LIST.md versionado e NÃO existe registro de concluídas: histórico mora no git (commits + tags)
  - Ordem = prioridade via prefixo numérico (`<n>-<tipo>-<nome>.md`); ideia nova entra SEMPRE no fim;
    reordenar = renomear prefixos
  - Tarefas com `> ⚠️ NÃO INICIAR sem ok explícito do dono` no topo exigem aprovação antes de começar
- Agente `planner` (`.opencode/agent/planner.md`): investiga projeto + web + spikes e escreve as
  tarefas SEMPRE fechando escopo com perguntas ao dono. Permissões: leitura de tudo, escrita SÓ em
  `tmp/todo-list/`, bash só para `mv` dentro da pasta, sem subagentes, nunca executa.
- Cada arquivo de tarefa nasce inteiro num único write — nunca editar parcialmente; mudar = reescrever
- Fluxo: ideia vaga → sessão com `planner` (primário ou @planner) → arquivo no fim da lista →
  implementação direto na dev conforme Workflow TDD & Git → validação do dono → tag do ciclo →
  arquivo da tarefa apagado

# Repositórios de Referência
- HydraGemini
- LiteLLM
