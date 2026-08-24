import json
from pathlib import Path

from src.providers import default_base_url
from src.utils.config_paths import DEFAULT_PORT, config_path

_EXEMPLO = {
    "port": 8792,
    "providers": {
        "gemini": {
            "api-keys": ["sk-exemplo-1", "sk-exemplo-2"],
            "models": ["gemini-3.5-flash", "gemini-3.1-flash-lite"],
        }
    },
}


def init_config(path=None):
    if path is None:
        path = config_path()
    path = Path(path)
    if path.exists():
        return path, False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_EXEMPLO, indent=2) + "\n", encoding="utf-8")
    return path, True


def load_config(path=None):
    if path is None:
        path = config_path()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"config não encontrado em {path}; rode 'ai-rotation-key init'")
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"config inválido ({path}): JSON quebrado — {exc}") from exc
    port = _validar_port(dados.get("port", DEFAULT_PORT))
    providers = _validar_providers(dados)
    return {"port": port, "providers": providers}


def _validar_port(port):
    if isinstance(port, bool) or not isinstance(port, int) or port <= 0:
        raise ValueError(f"'port' deve ser int positivo, recebido {port!r}")
    return port


def _validar_providers(dados):
    if "model-keys" in dados:
        raise ValueError(
            "formato antigo ('model-keys') não é mais suportado — migre para "
            "'providers': {\"<provider>\": {\"api-keys\": [...], \"models\": [...]}}"
        )
    providers_dados = dados.get("providers")
    if isinstance(providers_dados, dict) and any(
        isinstance(cfg, dict) and "exclude-models" in cfg
        for cfg in providers_dados.values()
    ):
        raise ValueError(
            "formato antigo ('exclude-models') não é mais suportado — migre para 'filter-models': "
            "padrões positivos são allowlist e '!padrao' remove (ex.: [\"*free*\", \"!*vision*\"]; "
            "sem positivos, tudo menos os negativos)"
        )
    providers = dados.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ValueError("config precisa de 'providers' como dict não-vazio")
    vistos = {}
    for nome, cfg in providers.items():
        if not isinstance(nome, str) or not nome:
            raise ValueError(f"nome de provider inválido: {nome!r}")
        if not isinstance(cfg, dict):
            raise ValueError(f"provider '{nome}' deve ser um objeto")
        api_keys = cfg.get("api-keys")
        if not isinstance(api_keys, list) or not api_keys or not all(
            isinstance(chave, str) and chave for chave in api_keys
        ):
            raise ValueError(f"'api-keys' do provider '{nome}' deve ser lista não-vazia de strings")
        modelos = cfg.get("models")
        if not isinstance(modelos, list) or not modelos or not all(
            isinstance(modelo, str) and modelo for modelo in modelos
        ):
            raise ValueError(f"'models' do provider '{nome}' deve ser lista não-vazia de strings")
        filtros = cfg.get("filter-models", [])
        if not isinstance(filtros, list) or not all(
            isinstance(p, str) and p for p in filtros
        ):
            raise ValueError(
                f"'filter-models' do provider '{nome}' deve ser lista de padrões (strings) "
                f"não-vazios; '!padrao' exclui"
            )
        base_url = cfg.get("base-url") or default_base_url(nome)
        if not base_url:
            raise ValueError(
                f"provider '{nome}' é desconhecido e não tem 'base-url' — informe uma, "
                f"ex.: \"base-url\": \"https://api.exemplo.com/v1\""
            )
        for modelo in modelos:
            if modelo in vistos and vistos[modelo] != nome:
                raise ValueError(
                    f"modelo '{modelo}' declarado em dois providers ('{vistos[modelo]}' e '{nome}')"
                )
            vistos[modelo] = nome
        providers[nome] = {
            "base-url": base_url,
            "api-keys": api_keys,
            "filter-models": filtros,
            "models": modelos,
        }
    return providers
