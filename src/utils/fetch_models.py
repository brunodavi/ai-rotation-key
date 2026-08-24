import json
from urllib import error, request


class FetchModelsError(Exception):
    def __init__(self, motivo, status=None):
        super().__init__(motivo)
        self.status = status


def fetch_models(base_url, api_key, timeout=30):
    url = base_url.rstrip("/") + "/models"
    req = request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
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
        entradas = dados["data"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise FetchModelsError(f"resposta de /models inesperada: {exc}") from None
    return [_normalizar_id(item["id"]) for item in entradas if isinstance(item, dict) and item.get("id")]


def _normalizar_id(model_id):
    if isinstance(model_id, str) and model_id.startswith("models/"):
        return model_id[len("models/"):]
    return model_id
