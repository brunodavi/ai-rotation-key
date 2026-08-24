import http.client
import json
from urllib import error, request

DEFAULT_UPSTREAM = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

_ROTACIONAVEIS = (error.URLError, OSError, http.client.HTTPException)


def forward_request(round_robin, model, payload, url=DEFAULT_UPSTREAM, timeout=120):
    status, body, headers = _falha_conexao("upstream não alcançado")
    for _ in range(round_robin.count(model)):
        chave = round_robin.next(model)
        req = request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {chave}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout) as res:
                return res.status, res.read(), dict(res.headers)
        except error.HTTPError as exc:
            if exc.code == 429:
                status, body, headers = exc.code, exc.read(), dict(exc.headers)
                continue
            return exc.code, exc.read(), dict(exc.headers)
        except _ROTACIONAVEIS as exc:
            status, body, headers = _falha_conexao(str(exc))
            continue
    return status, body, headers


def _falha_conexao(motivo):
    return 502, json.dumps({"error": {"message": f"conexão falhou: {motivo}"}}).encode(), {}
