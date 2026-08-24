import json
import os
from pathlib import Path

from src.utils.load_config import load_config

PROVIDER_ID = "ai-rotation-key"
OPENCODE_SCHEMA = "https://opencode.ai/config.json"


def export_provider():
    config = load_config()
    opencode_path = Path(os.environ["HOME"]) / ".config" / "opencode" / "config.json"
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
    return opencode_path, acao


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
    return {
        "npm": "@ai-sdk/openai-compatible",
        "name": "AI Rotation Key (local)",
        "options": {
            "baseURL": f"http://127.0.0.1:{config['port']}/v1",
            "apiKey": "sk-dummy",
        },
        "models": {modelo: {"name": modelo} for modelo in config["model-keys"]},
    }
