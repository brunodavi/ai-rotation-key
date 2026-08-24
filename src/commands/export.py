from src.utils.export_provider import PROVIDER_ID, export_provider

_MENSAGENS = {
    "criado": "provider registrado — config do opencode criado em {path}",
    "adicionado": f"provider '{PROVIDER_ID}' adicionado em {{path}}",
    "atualizado": f"provider '{PROVIDER_ID}' atualizado em {{path}} (baseURL/models sincronizados)",
    "inalterado": f"provider '{PROVIDER_ID}' já estava configurado em {{path}}",
}


def run(args):
    resultado = export_provider()
    if isinstance(resultado, tuple) and len(resultado) == 2:
        path, acao = resultado
        modelo_msg = _MENSAGENS.get(acao, f"provider '{PROVIDER_ID}' processado em {{path}}")
        print(modelo_msg.format(path=path))
    return resultado
