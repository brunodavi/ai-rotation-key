DEFAULT_UPSTREAM = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"


def forward_request(round_robin, model, payload, url=DEFAULT_UPSTREAM, timeout=120):
    raise NotImplementedError("repassar payload ao upstream com rotação de chaves")
