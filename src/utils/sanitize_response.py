import copy
import json


def strip_extra_content(choice):
    for campo in ("delta", "message"):
        container = choice.get(campo)
        if isinstance(container, dict):
            container.pop("extra_content", None)
            _limpar_tool_calls(container)
    _limpar_tool_calls(choice)


def sanitize_response_payload(resp):
    for choice in resp.get("choices") or []:
        strip_extra_content(choice)
    return resp


def sanitize_sse_line(line, collector=None):
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
    limpo = sanitize_response_payload(copy.deepcopy(chunk))
    if limpo == chunk:
        return line
    return f"data: {json.dumps(limpo)}\n\n".encode("utf-8")


def _limpar_tool_calls(obj):
    for tool_call in obj.get("tool_calls") or []:
        if isinstance(tool_call, dict):
            tool_call.pop("extra_content", None)
