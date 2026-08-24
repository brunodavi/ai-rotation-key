from src.utils.init_config import init_config


def run(args):
    resultado = init_config()
    if isinstance(resultado, tuple) and len(resultado) == 2:
        path, criado = resultado
        if criado:
            print(f"config criado em {path}")
        else:
            print(f"config já existe em {path} — sem alterar")
    return resultado
