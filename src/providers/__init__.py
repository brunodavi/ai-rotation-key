from src.providers import gemini, opencode_zen, openrouter

_REGISTRO = {modulo.NAME: modulo for modulo in (gemini, openrouter, opencode_zen)}


def nomes_conhecidos():
    return set(_REGISTRO)


def default_base_url(nome):
    modulo = _REGISTRO.get(nome)
    return modulo.BASE_URL if modulo else None
