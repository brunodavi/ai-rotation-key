import json
from pathlib import Path

from src.utils.config_paths import DEFAULT_PORT, config_path


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
    model_keys = _validar_model_keys(dados.get("model-keys"))
    port = _validar_port(dados.get("port", DEFAULT_PORT))
    return {"model-keys": model_keys, "port": port}


def _validar_model_keys(model_keys):
    if not isinstance(model_keys, dict) or not model_keys:
        raise ValueError("config precisa de 'model-keys' como dict não-vazio {modelo: [chaves]}")
    for modelo, chaves in model_keys.items():
        if not isinstance(modelo, str) or not modelo:
            raise ValueError(f"nome de modelo inválido em 'model-keys': {modelo!r}")
        if not isinstance(chaves, list) or not chaves:
            raise ValueError(f"chaves do modelo '{modelo}' devem ser lista não-vazia")
        if not all(isinstance(chave, str) and chave for chave in chaves):
            raise ValueError(f"chaves do modelo '{modelo}' devem ser strings não-vazias")
    return model_keys


def _validar_port(port):
    if isinstance(port, bool) or not isinstance(port, int) or port <= 0:
        raise ValueError(f"'port' deve ser int positivo, recebido {port!r}")
    return port
