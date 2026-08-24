# TODO_LIST

Fila de tarefas do projeto. **Escrita exclusiva do agente `planner`** (`.opencode/agent/planner.md`) —
nenhuma outra sessão deve editar este arquivo diretamente. Execução segue o AGENTS.md:
uma branch por parte, TDD RED → GREEN → REFACTOR, merge na master só após validação manual do dono.

## Fila (prontas para iniciar)

- [ ] `feat/custom-provider-descoberta` — provider customizado no config com mapeamento declarativo
      nativo null-safe por dot-path (ex.: "data[].id"): caminho dos ids no /models, sufixo do endpoint
      de chat, formato do header de auth. Sem dependências (dot-path próprio, não JSONPath lib).

- [ ] `feat/custom-provider-traducao` — tradução completa de corpo request/response do custom provider
      via dot-path null-safe (extrair/renomear campos entre formatos não-OpenAI e o contrato do proxy).

## Aguardando aprovação do dono (NÃO iniciar sem ok explícito)

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
      Padrão do dono: o init SEM flag usa opencode-zen com `"api-keys": ["public"]` e modelos free —
      onboarding zero-custo; ao criar, imprimir dica com curl pronto pra testar logo após
      `airkey start`, pedindo pro chat responder apenas "OK" (ex.:
      curl http://127.0.0.1:<porta>/v1/chat/completions -d '{"model":
      "opencode-zen/laguna-s-2.1-free", ...}').

- [ ] `feat/edit-harness` — terminologia: opencode é o HARNESS, não provider. Trocar a flag
      `edit --opencode` por forma autoexplicativa: preferir `edit --harness [nome]` (default
      implícito: opencode); se não couber, `edit -H <harness>` ou similar. Atualizar help,
      testes e README junto.

- [ ] `chore/sem-mensagens-de-migracao` — REMOVER orientações de migração de formatos antigos
      (model-keys, exclude-models): projeto criado recentemente, ninguém usa versão antiga.
      Erros de formato devem apenas explicar como o formato ATUAL funciona, sem texto de migração.

## Em andamento

(nenhuma)

## Concluídas

- [x] `refactor/commands` — mover a lógica de cada comando do CLI para `src/commands/<nome>.py`
      (init, edit, start, export, sync-models); `src/cli.py` fica só com argparse/wiring.
      ZERO mudança de comportamento; testes existentes continuam passando sem edição de asserções.

- [x] `refactor/providers` — centralizar o contrato real por provider em um registro único
      (módulo por provider embutido: base-url default, auth, quirks como UA); um humano adiciona
      provider novo criando UM arquivo. `DEFAULT_BASE_URLS` migra pra cá (load_config passa a consultar).

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
