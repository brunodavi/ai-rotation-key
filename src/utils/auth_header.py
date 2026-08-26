"""Auth header template for upstream calls.

'Name: {api-key}' selects a custom header name (e.g. 'x-goog-api-key: ...');
a bare template such as 'Bearer {api-key}' targets Authorization.
"""

PADRAO = "Bearer {api-key}"


def montar_auth(template, api_key):
    texto = template or PADRAO
    if ":" in texto:
        nome, _, valor = texto.partition(":")
        return nome.strip(), valor.strip().format(**{"api-key": api_key})
    return "Authorization", texto.format(**{"api-key": api_key})
