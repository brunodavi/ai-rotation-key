import logging

from src.utils.update_models import sync_models

_log = logging.getLogger("airkey")


def _imprimir_relatorio(resultado):
    for nome, rel in resultado.relatorios.items():
        if "erro" in rel:
            if rel.get("status"):
                _log.error("%s: erro HTTP %s: %s", nome, rel["status"], rel["erro"])
            else:
                _log.error("%s: erro de conexão: %s", nome, rel["erro"])
            continue
        if rel["adicionados"]:
            _log.info(
                "%s: +%d adicionados · %d filtrados por filter-models · %d já existiam",
                nome, len(rel["adicionados"]), rel["excluidos"], rel["existentes"],
            )
        elif rel["excluidos"]:
            _log.info("%s: inalterado (%d filtrados por filter-models)", nome, rel["excluidos"])
        else:
            _log.info("%s: inalterado — nada a adicionar", nome)
    if resultado.salvo:
        _log.info("config atualizado em %s", resultado.path)


def run(args):
    try:
        resultado = sync_models(apenas=args.provider)
    except ValueError as exc:
        _log.error(str(exc))
        raise SystemExit(1) from None
    _imprimir_relatorio(resultado)
    if resultado.houve_erro:
        raise SystemExit(1)
    return resultado
