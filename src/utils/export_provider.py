import json
import logging
from pathlib import Path

from src.utils.config_paths import opencode_config_path
from src.utils.load_config import load_config

_log = logging.getLogger("airkey")

PROVIDER_ID = "ai-rotation-key"
OPENCODE_SCHEMA = "https://opencode.ai/config.json"


def export_provider():
    config = load_config()
    opencode_path = opencode_config_path()
    existia = opencode_path.exists()
    atual = _ler_existente(opencode_path)
    providers = atual.setdefault("provider", {})
    bloco = _bloco(config)
    anterior = providers.get(PROVIDER_ID)
    if not existia:
        acao = "criado"
    elif anterior is None:
        acao = "adicionado"
    elif anterior == bloco:
        return opencode_path, "inalterado"
    else:
        acao = "atualizado"
    providers[PROVIDER_ID] = bloco
    atual.setdefault("$schema", OPENCODE_SCHEMA)
    opencode_path.parent.mkdir(parents=True, exist_ok=True)
    opencode_path.write_text(json.dumps(atual, indent=2) + "\n", encoding="utf-8")
    _avisar_nomes_duplicados(bloco)
    return opencode_path, acao


def _avisar_nomes_duplicados(bloco):
    por_nome = {}
    for key, info in bloco["models"].items():
        por_nome.setdefault(info["name"], []).append(key)
    for nome, keys in por_nome.items():
        if len(keys) > 1:
            _log.warning(
                "nome de exibição '%s' se repete em %d modelos: "
                "%s — use o id completo na hora de escolher",
                nome, len(keys), ", ".join(sorted(keys)),
            )


def _ler_existente(path):
    if not path.exists():
        return {}
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"config do opencode inválido ({path}): JSON quebrado — corrija manualmente"
        ) from exc
    if not isinstance(dados, dict):
        raise ValueError(f"config do opencode inválido ({path}): raiz deve ser um objeto")
    return dados


def _bloco(config):
    modelos = {
        f"{nome}/{modelo}": {"name": f"{nome}/{modelo.split('/')[-1]}"}
        for nome, provider in config["providers"].items()
        for modelo in provider["models"]
    }
    return {
        "npm": "@ai-sdk/openai-compatible",
        "name": "AI Rotation Key (local)",
        "options": {
            "baseURL": f"http://127.0.0.1:{config['port']}/v1",
            "apiKey": "sk-dummy",
        },
        "models": modelos,
    }
