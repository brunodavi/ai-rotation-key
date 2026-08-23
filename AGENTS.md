# Objetivo
Roteamento de chaves de APIs leves e simples, para funcionar para termux

# Tech
- Usar python puro sem libs, sem requirements.txt
- Usar ~/.config/ai-rotation-key/config.json
- Python >=3.14.6 (opcional)
- Ser um CLI cinfiguravel, init (cria config.json de exemplo), edit (abre config.json), start (iniciar servidor)
- Tests unitarios e de integracao
- Estrutura simples de pastas src/cli.py, main.py, utils/__init__ (barrel), utils/cada_funcao.py
- README.md simples com instalacao via github, comandos e motivação (erro termux por causa do rust)
- conventional commits
- sem lint

# Agent
- Usar ./tmp para guardar informações e validações sobre apis/documentações e seus comtratos reais
    - ./tmp/spikes validacoes encontradas com .md
    - ./tmp/apis/<nome> pastas com request response
    - ./tmp/scripts para validar uma lib nativa do python ou debug
- Sempre validar o comportamento real antes de asumir
- Sempre seguir TDD a risca
    - Validação do comportamento real
    - RED (erro na acersao, stub minimo necessario)
    - GREEN
    - REFACTOR

# Harness
- Usado para validar comportamento opencode

# Modelos/Gateways
- [ ] Gemini
- [ ] OpenRouter
- [ ] OpenCode Zen
- [ ] OpenCode Go
- [ ] OpenAi
- [ ] Deep Seek
- [ ] Qwen

# Repositórios de Referencia
- HydraGemini
- LiteLLM
