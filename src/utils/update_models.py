import json
import os
from collections import namedtuple
from pathlib import Path

from src.utils.config_paths import config_path
from src.utils.fetch_models import FetchModelsError, fetch_models
from src.utils.filter_models import filtrar_modelos
from src.utils.load_config import load_config

SyncResult = namedtuple("SyncResult", "relatorios salvo houve_erro path")


def sync_models(path=None, apenas=None):
    config = load_config(path)
    providers = config["providers"]
    if apenas is not None and apenas not in providers:
        raise ValueError(
            f"provider '{apenas}' não está no config — opções: {', '.join(providers)}"
        )
    alvos = list(providers) if apenas is None else [apenas]
    relatorios = {}
    houve_erro = False
    mudou = False
    for nome in alvos:
        try:
            relatorio = sync_provider(nome, providers[nome])
        except FetchModelsError as exc:
            relatorios[nome] = {"erro": str(exc), "status": exc.status}
            houve_erro = True
            continue
        relatorios[nome] = relatorio
        if relatorio["adicionados"]:
            mudou = True
    destino = Path(path) if path is not None else config_path()
    salvo = False
    if mudou:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        salvo = True
    return SyncResult(relatorios=relatorios, salvo=salvo, houve_erro=houve_erro, path=destino)


def sync_provider(nome, cfg):
    descobertos = fetch_models(
        cfg["base-url"],
        cfg["api-keys"][0],
        path_modelos=cfg.get("path-models"),
        auth_header=cfg.get("auth-header"),
    )
    aceitos = filtrar_modelos(descobertos, cfg.get("filter-models", []))
    atuais = set(cfg["models"])
    excluidos = len(descobertos) - len(aceitos)
    adicionados = []
    for modelo in aceitos:
        if modelo not in atuais and modelo not in adicionados:
            adicionados.append(modelo)
    cfg["models"].extend(adicionados)
    existentes = len(aceitos) - len(adicionados)
    return {"adicionados": adicionados, "excluidos": excluidos, "existentes": existentes}
