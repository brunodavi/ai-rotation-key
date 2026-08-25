import json
from urllib import error, request

from src.utils.dot_path import resolver
from src.utils.user_agent import USER_AGENT


class FetchModelsError(Exception):
    def __init__(self, motivo, status=None):
        super().__init__(motivo)
        self.status = status


def fetch_models(base_url, api_key, timeout=30, path_modelos=None, auth_header=None):
    url = base_url.rstrip("/") + "/models"
    template = auth_header or "Bearer {api-key}"
    req = request.Request(
        url,
        headers={
            "Authorization": template.format(**{"api-key": api_key}),
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=timeout) as res:
            bruto = res.read()
    except error.HTTPError as exc:
        raise FetchModelsError(
            f"HTTP {exc.code} ao listar modelos: {exc.read().decode('utf-8', 'replace')[:200]}",
            status=exc.code,
        ) from None
    except (error.URLError, OSError) as exc:
        raise FetchModelsError(f"conexão falhou: {exc}") from None
    try:
        dados = json.loads(bruto.decode("utf-8"))
    except (json.JSONDecodeError, TypeError) as exc:
        raise FetchModelsError(f"resposta de /models inesperada: {exc}") from None

    if path_modelos is None:
        try:
            entradas = dados["data"]
            ids = [item["id"] for item in entradas if isinstance(item, dict) and item.get("id")]
        except (KeyError, TypeError) as exc:
            raise FetchModelsError(f"resposta de /models inesperada: {exc}") from None
    else:
        ids = resolver(dados, path_modelos)
        if not ids or not all(isinstance(i, str) and i for i in ids):
            raise FetchModelsError(
                f"path-models '{path_modelos}' não encontrou ids na resposta — "
                f"confira o caminho contra a resposta real do gateway"
            )
    return [_normalizar_id(i) for i in ids]


def _normalizar_id(model_id):
    if isinstance(model_id, str) and model_id.startswith("models/"):
        return model_id[len("models/"):]
    return model_id
