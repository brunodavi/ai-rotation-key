import copy
import json


class Sanitizer:
    """Tradução de payload entre o formato OpenAI (recebido do opencode)
    e o formato que a API do provider espera/retorna.

    Cada provider sobescreve o que precisar; o comportamento genérico
    (whitelist de keys, mensagens, tools, SSE e extra_content) vive aqui.
    """

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

    def sanitize_request(self, data):
        limpo = {chave: valor for chave, valor in data.items() if chave in self.ALLOWED_KEYS}
        mensagens = limpo.get("messages")
        if not mensagens:
            limpo["messages"] = [dict(m) for m in self.FALLBACK_MESSAGES]
        else:
            limpo["messages"] = [self._padronizar_message(m) for m in mensagens]
        if isinstance(limpo.get("tools"), list):
            limpo["tools"] = self._normalizar_tools(limpo["tools"])
        return limpo

    def sanitize_response(self, resp):
        for choice in resp.get("choices") or []:
            self._strip_extra_content(choice)
        return resp

    def sanitize_sse_line(self, line, collector=None):
        texto = line.decode("utf-8", errors="ignore")
        if not texto.startswith("data:") or "[DONE]" in texto:
            return line
        bruto = texto.split("data:", 1)[1].strip()
        if not bruto:
            return line
        try:
            chunk = json.loads(bruto)
        except json.JSONDecodeError:
            return line
        if collector is not None:
            collector(chunk)
        limpo = self.sanitize_response(copy.deepcopy(chunk))
        if limpo == chunk:
            return line
        return f"data: {json.dumps(limpo)}\n\n".encode("utf-8")

    def _padronizar_message(self, message):
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

    def _normalizar_tools(self, tools):
        normalizadas = []
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            if "type" in tool and "function" in tool:
                normalizadas.append(tool)
            elif "name" in tool or "parameters" in tool:
                funcao = {
                    "name": tool.get("name", "unknown_function"),
                    "parameters": tool.get("parameters", {}),
                }
                if "description" in tool:
                    funcao["description"] = tool["description"]
                normalizadas.append({"type": "function", "function": funcao})
            else:
                normalizadas.append(tool)
        return normalizadas

    def _strip_extra_content(self, choice):
        for campo in ("delta", "message"):
            container = choice.get(campo)
            if isinstance(container, dict):
                container.pop("extra_content", None)
                self._limpar_tool_calls(container)
        self._limpar_tool_calls(choice)

    def _limpar_tool_calls(self, obj):
        for tool_call in obj.get("tool_calls") or []:
            if isinstance(tool_call, dict):
                tool_call.pop("extra_content", None)
