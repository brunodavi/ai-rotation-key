from src.providers import gemini, opencode_zen, openrouter
from src.sanitizer import Sanitizer

_SANITIZERS = {
    gemini.NAME: gemini.GeminiSanitizer,
    openrouter.NAME: openrouter.OpenRouterSanitizer,
    opencode_zen.NAME: opencode_zen.OpenCodeZenSanitizer,
}

_BASE_URLS = {
    gemini.NAME: gemini.BASE_URL,
    openrouter.NAME: openrouter.BASE_URL,
    opencode_zen.NAME: opencode_zen.BASE_URL,
}


def nomes_conhecidos():
    return set(_SANITIZERS)


def default_base_url(nome):
    return _BASE_URLS.get(nome)


def create_sanitizer(nome):
    cls = _SANITIZERS.get(nome, Sanitizer)
    return cls()
