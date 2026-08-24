import argparse

from src.utils.edit_config import edit_config
from src.utils.export_provider import export_provider
from src.utils.init_config import init_config
from src.utils.start_server import start_server


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
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    handlers = {
        "init": init_config,
        "edit": edit_config,
        "start": start_server,
        "export": export_provider,
    }
    resultado = handlers[args.command]()
    if args.command == "init":
        path, created = resultado
        if created:
            print(f"config criado em {path}")
        else:
            print(f"config já existe em {path} — sem alterar")
    return resultado
