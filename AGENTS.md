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

# Roadmap UX/DX (decisões fechadas — implementar nesta ordem)
Decisões do dono do projeto registradas como subtarefas; cada item = uma branch própria
(`refactor/<nome>` / `feat/<nome>`), TDD à risca, merge só após validação manual.

## DX (fundação primeiro)
- [ ] `refactor/commands` — mover a lógica de cada comando do CLI para `src/commands/<nome>.py`
      (init, edit, start, export, sync-models); `src/cli.py` fica só com argparse/wiring.
      ZERO mudança de comportamento; testes existentes continuam passando sem edição de asserções.
- [x] `refactor/providers` — centralizar o contrato real por provider em um registro único
      (módulo por provider embutido: base-url default, auth, quirks como UA); um humano adiciona
      provider novo criando UM arquivo. `DEFAULT_BASE_URLS` migra pra cá (load_config passa a consultar).

## UX (em cima da fundação)
- [x] `feat/edit-opencode` — flag `--opencode` no comando `edit`: abre o config do opencode
      (~/.config/opencode/config.json) no $EDITOR com o mesmo fluxo atual ($EDITOR, fallback vi).
- [x] `feat/filter-models` — SUBSTITUI exclude-models por filter-models (lista de globs):
      padrão positivo = allowlist; prefixo `!` = remove do resultado; sem positivos = tudo menos
      os negativos (ex.: ["*free*", "!*vision*"]). Aplica no sync-models e na validação da carga;
      config com exclude-models é rejeitado com orientação de migração (mesmo tratamento do model-keys).
- [x] `feat/namespacing` — modelos expostos como `<provider>/<modelo>` em /v1/models e no roteamento;
      request aceita também nome pelado quando não-ambíguo (ambíguo → 400 pedindo qualificação);
      o prefixo próprio é removido antes de ir ao upstream; sync-models continua gravando pelado no
      config; mesmo modelo em providers distintos passa a ser PERMITIDO (namespaces únicos por
      construção — hoje conflito = ValueError na carga).
- [ ] `feat/custom-provider-descoberta` — provider customizado no config com mapeamento declarativo
      nativo null-safe por dot-path (ex.: "data[].id"): caminho dos ids no /models, sufixo do endpoint
      de chat, formato do header de auth. Sem dependências (dot-path próprio, não JSONPath lib).
- [ ] `feat/custom-provider-traducao` — tradução completa de corpo request/response do custom provider
      via dot-path null-safe (extrair/renomear campos entre formatos não-OpenAI e o contrato do proxy).

## Extras (pedidos posteriores — NÃO iniciar sem aprovação)
- [ ] `refactor/providers-declarativos` — UNIFICAR os dois mundos (registro embutido × custom):
      registro vira estrutura de DADOS declarativa (ex.: `{nome: {"base-url": ..., "sufixo-chat":
      ..., "path-models": ..., "header-auth": ...}}`), consultável e SOBRESCRIVÍVEL por config.json;
      provider customizado usa o MESMO schema inline. Objetivo do dono: alterar só isso já configura
      os padrões de cada provider único — adicionar provider vira literalmente só config, sem código.
      Substitui/absorve os módulos `src/providers/*.py` atuais (hoje só NAME + BASE_URL).
      Executar DEPOIS/AJUNTO das partes de custom-provider (mesmo mecanismo).
- [ ] `feat/init-por-provider` — `init` passa a gerar exemplo POR provider: `airkey init --gemini`
      cria o config só com aquele provider (placeholders de key + modelos de exemplo + filter-models
      sugeridos, vindos do registro). Se flags dinâmicas `--<nome>` não couberem bem no argparse,
      fallback pré-aprovado: `init -p/--provider <nome>`.
- [ ] `feat/edit-harness` — terminologia: opencode é o HARNESS, não provider. Trocar a flag
      `edit --opencode` por forma autoexplicativa: preferir `edit --harness [nome]` (default
      implícito: opencode); se não couber, `edit -H <harness>` ou similar. Atualizar help,
      testes e README junto.
- [ ] `chore/sem-mensagens-de-migracao` — REMOVER orientações de migração de formatos antigos
      (model-keys, exclude-models): projeto criado recentemente, ninguém usa versão antiga.
      Erros de formato devem apenas explicar como o formato ATUAL funciona, sem texto de migração.

# Repositórios de Referência
- HydraGemini
- LiteLLM
