import copy


class SignatureCache:
    def __init__(self, cap=512):
        if cap <= 0:
            raise ValueError("cap deve ser positivo")
        self._cap = cap
        self._data = {}

    def signatures(self):
        return dict(self._data)

    def collect(self, payload):
        if not isinstance(payload, dict):
            return
        for choice in payload.get("choices") or []:
            if not isinstance(choice, dict):
                continue
            for campo in ("delta", "message"):
                container = choice.get(campo)
                if isinstance(container, dict):
                    self._coletar(container)
            self._coletar(choice)

    def inject(self, messages):
        for message in messages or []:
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            for tool_call in message.get("tool_calls") or []:
                if not isinstance(tool_call, dict):
                    continue
                if tool_call.get("id") in self._data and "extra_content" not in tool_call:
                    tool_call["extra_content"] = copy.deepcopy(self._data[tool_call["id"]])

    def _coletar(self, obj):
        for tool_call in obj.get("tool_calls") or []:
            if not isinstance(tool_call, dict):
                continue
            extra = tool_call.get("extra_content")
            if tool_call.get("id") and isinstance(extra, dict):
                self._armazenar(tool_call["id"], extra)

    def _armazenar(self, id_, extra):
        self._data.pop(id_, None)
        self._data[id_] = copy.deepcopy(extra)
        while len(self._data) > self._cap:
            self._data.pop(next(iter(self._data)))
