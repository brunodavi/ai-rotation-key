import argparse

from src.utils.edit_config import edit_config
from src.utils.export_provider import PROVIDER_ID, export_provider
from src.utils.init_config import init_config
from src.utils.start_server import start_server
from src.utils.update_models import sync_models

_MENSAGENS_EXPORT = {
    "criado": "provider registrado — config do opencode criado em {path}",
    "adicionado": f"provider '{PROVIDER_ID}' adicionado em {{path}}",
    "atualizado": f"provider '{PROVIDER_ID}' atualizado em {{path}} (baseURL/models sincronizados)",
    "inalterado": f"provider '{PROVIDER_ID}' já estava configurado em {{path}}",
}


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="ai-rotation-key",
        description="Roteador round-robin de chaves de APIs de IA",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Cria ~/.config/ai-rotation-key/config.json de exemplo")
    sub.add_parser("edit", help="Abre o config no $EDITOR (fallback: vi)")
    sub.add_parser("start", help="Sobe o servidor local")
    sub.add_parser("export", help="Registra este servidor como provider no opencode")
    sync = sub.add_parser(
        "sync-models",
        help="Busca /models de cada provider e adiciona os faltantes ao config",
    )
    sync.add_argument(
        "provider",
        nargs="?",
        default=None,
        help="(opcional) sincroniza apenas este provider; padrão: todos",
    )
    return parser


def _imprimir_sync(resultado):
    for nome, rel in resultado.relatorios.items():
        if "erro" in rel:
            if rel.get("status"):
                print(f"{nome}: erro HTTP {rel['status']}: {rel['erro']}")
            else:
                print(f"{nome}: erro de conexão: {rel['erro']}")
            continue
        if rel["adicionados"]:
            print(
                f"{nome}: +{len(rel['adicionados'])} adicionados · "
                f"{rel['excluidos']} excluídos pelo exclude-models · "
                f"{rel['existentes']} já existiam"
            )
        elif rel["excluidos"]:
            print(f"{nome}: inalterado ({rel['excluidos']} excluídos pelo exclude-models)")
        else:
            print(f"{nome}: inalterado — nada a adicionar")
    if resultado.salvo:
        print(f"config atualizado em {resultado.path}")


def main(argv=None):
    args = _build_parser().parse_args(argv)
    handlers = {
        "init": init_config,
        "edit": edit_config,
        "start": start_server,
        "export": export_provider,
        "sync-models": sync_models,
    }
    if args.command == "sync-models":
        try:
            resultado = sync_models(apenas=args.provider)
        except ValueError as exc:
            print(str(exc))
            raise SystemExit(1) from None
        _imprimir_sync(resultado)
        if resultado.houve_erro:
            raise SystemExit(1)
        return resultado
    resultado = handlers[args.command]()
    if args.command == "init" and isinstance(resultado, tuple) and len(resultado) == 2:
        path, created = resultado
        if created:
            print(f"config criado em {path}")
        else:
            print(f"config já existe em {path} — sem alterar")
    if args.command == "export" and isinstance(resultado, tuple) and len(resultado) == 2:
        path, acao = resultado
        modelo_msg = _MENSAGENS_EXPORT.get(acao, f"provider '{PROVIDER_ID}' processado em {{path}}")
        print(modelo_msg.format(path=path))
    return resultado
