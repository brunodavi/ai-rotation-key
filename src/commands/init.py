import logging

from src.utils.init_config import init_config

_log = logging.getLogger("airkey")


def run(args):
    resultado = init_config()
    if isinstance(resultado, tuple) and len(resultado) == 2:
        path, criado = resultado
        if criado:
            _log.info("config criado em %s", path)
        else:
            _log.info("config já existe em %s — sem alterar", path)
    return resultado
