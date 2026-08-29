ALLOWED_KEYS = {
    "model",
    "messages",
    "temperature",
    "max_tokens",
    "max_completion_tokens",
    "top_p",
    "stream",
    "tools",
    "tool_choice",
    "stop",
    "response_format",
    "seed",
    "presence_penalty",
    "frequency_penalty",
}

FALLBACK_MESSAGES = [{"role": "user", "content": "Hello"}]


def sanitize_request(data):
    limpo = {chave: valor for chave, valor in data.items() if chave in ALLOWED_KEYS}
    mensagens = limpo.get("messages")
    if not mensagens:
        limpo["messages"] = [dict(m) for m in FALLBACK_MESSAGES]
    else:
        limpo["messages"] = [
            _padronizar_message(m)
            for m in mensagens
            if m.get("role") != "system"
        ]
    if isinstance(limpo.get("tools"), list):
        limpo["tools"] = _normalizar_tools(limpo["tools"])
    return limpo


def _padronizar_message(message):
    padronizada = dict(message)
    conteudo = padronizada.get("content")
    if isinstance(conteudo, list):
        partes = [
            bloco.get("text", "")
            for bloco in conteudo
            if isinstance(bloco, dict) and bloco.get("type") == "text"
        ]
        padronizada["content"] = " ".join(partes).strip() or " "
    elif not conteudo:
        padronizada["content"] = " "
    return padronizada


def _normalizar_tools(tools):
    normalizadas = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        if "type" in tool and "function" in tool:
            normalizadas.append(tool)
        elif "name" in tool or "parameters" in tool:
            funcao = {"name": tool.get("name", "unknown_function"), "parameters": tool.get("parameters", {})}
            if "description" in tool:
                funcao["description"] = tool["description"]
            normalizadas.append({"type": "function", "function": funcao})
        else:
            normalizadas.append(tool)
    return normalizadas
