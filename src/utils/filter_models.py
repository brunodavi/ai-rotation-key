import fnmatch


def filtrar_modelos(candidatos, filtros):
    positivos = [f for f in filtros if not f.startswith("!")]
    negativos = [f[1:] for f in filtros if f.startswith("!")]
    resultado = []
    for modelo in candidatos:
        if any(fnmatch.fnmatchcase(modelo, neg) for neg in negativos):
            continue
        if positivos and not any(fnmatch.fnmatchcase(modelo, pos) for pos in positivos):
            continue
        resultado.append(modelo)
    return resultado
