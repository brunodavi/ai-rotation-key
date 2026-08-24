from src.utils.update_models import sync_models


def _imprimir_relatorio(resultado):
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
                f"{rel['excluidos']} filtrados por filter-models · "
                f"{rel['existentes']} já existiam"
            )
        elif rel["excluidos"]:
            print(f"{nome}: inalterado ({rel['excluidos']} filtrados por filter-models)")
        else:
            print(f"{nome}: inalterado — nada a adicionar")
    if resultado.salvo:
        print(f"config atualizado em {resultado.path}")


def run(args):
    try:
        resultado = sync_models(apenas=args.provider)
    except ValueError as exc:
        print(str(exc))
        raise SystemExit(1) from None
    _imprimir_relatorio(resultado)
    if resultado.houve_erro:
        raise SystemExit(1)
    return resultado
