"""Body translation between OpenAI chat format and custom gateway formats.

Declarative dot-path maps (see config provider fields):
  - request-map  {destination_path: source_path}    OpenAI -> upstream
  - response-map {openai_field_path: upstream_path} upstream -> OpenAI
  - role-map     {openai_role: upstream_role}

Paths use the null-safe dot-path dialect from src.utils.dot_path. A path
containing an empty bracket `[]` iterates a list; both sides of a request-map
entry must agree on iteration (both iterate or none does), otherwise the map
is rejected. Missing sources are skipped: nodes are never created from absent
values. The response builder always returns a valid OpenAI envelope, lowers
`finish_reason` values and defaults each mapped message role to "assistant".
"""

import json
import re
import time
import uuid

from src.utils.dot_path import _tokens, resolver

_VAZIO = re.compile(r"\[\]")


def translate_request(data, mapping, role_map=None):
    saida = {}
    for destino, origem in mapping.items():
        iteracoes_destino, iteracoes_origem = len(_VAZIO.findall(destino)), len(_VAZIO.findall(origem))
        if iteracoes_destino != iteracoes_origem:
            raise ValueError(
                f"request-map inconsistente: '{destino}' e '{origem}' devem iterar "
                f"do mesmo lado (use [] nos dois caminhos ou em nenhum)"
            )
        if iteracoes_origem:
            _copiar_paralelo(saida, data, destino, origem, role_map)
        else:
            _copiar_simples(saida, data, destino, origem, role_map)
    return saida


def translate_response(payload, mapping):
    saida = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "choices": [],
        "usage": {},
    }
    for destino, origem in mapping.items():
        encontrados = resolver(payload, origem)
        if not encontrados:
            continue
        valor = encontrados[0]
        if destino.rsplit(".", 1)[-1] == "finish_reason" and isinstance(valor, str):
            valor = valor.lower()
        _definir(saida, destino, valor)
    for choice in saida["choices"]:
        mensagem = choice.get("message") if isinstance(choice, dict) else None
        if isinstance(mensagem, dict):
            mensagem.setdefault("role", "assistant")
    return saida


def translate_chunk(payload, mapping):
    saida = translate_response(payload, mapping)
    saida["object"] = "chat.completion.chunk"
    for choice in saida["choices"]:
        mensagem = choice.pop("message", None)
        choice["delta"] = mensagem if isinstance(mensagem, dict) else {}
        choice.setdefault("finish_reason", None)
    return saida


def translate_sse_line(line, mapping):
    """Translate one native SSE line to OpenAI delta bytes.

    Returns None for lines that must be dropped: non-data events (comments,
    keep-alives, stray blank lines) and native [DONE] markers — the proxy
    synthesizes its own terminator. Lines with invalid JSON pass through
    unchanged.
    """
    texto = line.decode("utf-8", errors="ignore")
    if not texto.startswith("data:"):
        return None
    bruto = texto.split("data:", 1)[1].strip()
    if not bruto or "[DONE]" in bruto:
        return None
    try:
        chunk = json.loads(bruto)
    except json.JSONDecodeError:
        return line
    traduzido = translate_chunk(chunk, mapping)
    return f"data: {json.dumps(traduzido)}\n\n".encode("utf-8")


def _copiar_paralelo(saida, dados, destino, origem, role_map):
    prefixo, _, sufixo = origem.partition("[]")
    achados = resolver(dados, prefixo)
    itens = achados[0] if achados and isinstance(achados[0], list) else []
    aplica_role = sufixo == "role" or sufixo.endswith(".role")
    for indice, item in enumerate(itens):
        valores = resolver(item, sufixo) if sufixo.strip() else [item]
        if not valores or valores[0] is None:
            continue
        valor = valores[0]
        if aplica_role and role_map:
            valor = role_map.get(valor, valor)
        _definir(saida, destino.replace("[]", f"[{indice}]", 1), valor)


def _copiar_simples(saida, dados, destino, origem, role_map):
    achados = resolver(dados, origem)
    if not achados:
        return
    valor = achados[0]
    ultimo = origem.rsplit(".", 1)[-1]
    if role_map and (ultimo == "role" or origem.endswith(".role")):
        valor = role_map.get(valor, valor)
    _definir(saida, destino, valor)


def _definir(raiz, caminho, valor):
    passos = list(_tokens(caminho))
    no = raiz
    for posicao, (tipo, chave) in enumerate(passos[:-1]):
        seguinte = passos[posicao + 1][0]
        padrao = [] if seguinte in ("indice", "iterar") else {}
        if tipo == "chave":
            if not isinstance(no, dict):
                return
            atual = no.get(chave)
            if not isinstance(atual, (dict, list)):
                no[chave] = padrao
            no = no[chave]
        elif isinstance(no, list):
            no = _estender(no, chave)
            atual = no[chave]
            if not isinstance(atual, (dict, list)):
                no[chave] = padrao
            no = no[chave]
        else:
            return
    tipo, chave = passos[-1]
    if tipo == "chave":
        if isinstance(no, dict):
            no[chave] = valor
    elif isinstance(no, list):
        _estender(no, chave)[chave] = valor


def _estender(lista, indice):
    while len(lista) <= indice:
        lista.append(None)
    return lista
