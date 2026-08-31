import http.client
import json
import logging
from urllib import error, request

from src.utils.auth_header import PADRAO as AUTH_PADRAO, montar_auth
from src.utils.user_agent import USER_AGENT

_log = logging.getLogger("airkey")

_ROTACIONAVEIS = (error.URLError, OSError, http.client.HTTPException)

DEFAULT_UPSTREAM = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"


def forward_request(round_robin, model, payload, url=DEFAULT_UPSTREAM, timeout=120,
                    auth_header=None):
    status, body, headers = _falha_conexao("upstream não alcançado")
    for _ in range(round_robin.count(model)):
        chave = round_robin.next(model)
        _log.debug("key=%s tentativa=%d/%d", chave[:2] + "*" * (len(chave) - 4) + chave[-2:] if len(chave) > 4 else chave[:2] + "**", _ + 1, round_robin.count(model))
        nome_auth, valor_auth = montar_auth(auth_header, chave)
        req = request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                nome_auth: valor_auth,
                "User-Agent": USER_AGENT,
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
