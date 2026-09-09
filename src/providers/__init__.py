from src.providers import gemini, opencode_zen, openrouter
from src.providers.base import Provider

__all__ = ["gemini", "opencode_zen", "openrouter", "Provider"]


def nomes_conhecidos():
    return set(Provider._registry)


def default_base_url(nome):
    cls = Provider._registry.get(nome)
    return cls.base_url if cls else None


def create_provider(nome):
    cls = Provider._registry.get(nome, Provider)
    return cls()
