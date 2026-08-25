"""Dot-path null-safe próprio (stdlib) — ex.: "data[].id", "items[0].modelId".

`resolver(dados, caminho)` sempre devolve LISTA:
  - `[]`      itera um array
  - `[n]`     índice numérico (negativo funciona como em Python)
  - `chave`   acesso a dicionário (numérico sobre lista age como índice)

Nada encontrado (chave ausente, índice fora do range, nó não-navegável) → lista vazia,
nunca exceção. Apenas caminho vazio levanta ValueError.
"""

import re

_TOKEN = re.compile(r"\.([A-Za-z_][\w-]*)|\[(\d*)\]")


def _tokens(caminho):
    primeiro = caminho.split(".", 1)[0].split("[", 1)[0]
    if primeiro:
        yield "chave", primeiro
    resto = caminho[len(primeiro):]
    for casado in _TOKEN.finditer(resto):
        chave, indice = casado.group(1), casado.group(2)
        if chave:
            yield "chave", chave
        elif indice == "":
            yield "iterar", None
        else:
            yield "indice", int(indice)


def resolver(dados, caminho):
    """Navega `dados` seguindo `caminho`; devolve lista com os valores encontrados."""
    if not caminho or not caminho.strip():
        raise ValueError("caminho dot-path vazio")
    fila = [dados]
    for tipo, valor in _tokens(caminho.strip()):
        proximo = []
        for no in fila:
            if tipo == "chave":
                if isinstance(no, dict) and valor in no:
                    proximo.append(no[valor])
                elif isinstance(no, list) and str(valor).lstrip("-").isdigit():
                    try:
                        proximo.append(no[int(valor)])
                    except IndexError:
                        pass
            elif tipo == "indice":
                if isinstance(no, list):
                    try:
                        proximo.append(no[valor])
                    except IndexError:
                        pass
            else:
                if isinstance(no, list):
                    proximo.extend(no)
        fila = proximo
        if not fila:
            break
    return fila
