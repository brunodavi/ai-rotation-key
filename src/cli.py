import argparse

from src.commands.edit import run as _edit
from src.commands.export import run as _export
from src.commands.init import run as _init
from src.commands.start import run as _start
from src.commands.sync_models import run as _sync_models


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


def main(argv=None):
    args = _build_parser().parse_args(argv)
    handlers = {
        "init": _init,
        "edit": _edit,
        "start": _start,
        "export": _export,
        "sync-models": _sync_models,
    }
    return handlers[args.command](args)
