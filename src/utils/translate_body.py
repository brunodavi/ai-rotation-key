"""Body translation between OpenAI chat format and custom gateway formats.

Declarative dot-path maps (see config provider fields):
  - request-map  {destination_path: source_path}   OpenAI -> upstream
  - response-map {openai_field_path: upstream_path} upstream -> OpenAI
  - role-map     {openai_role: upstream_role}

Paths use the null-safe dot-path dialect from src.utils.dot_path. A path
containing an empty bracket `[]` iterates a list; both sides of a request-map
entry must agree on iteration (both iterate or none does), otherwise the map
is rejected.
"""


def translate_request(data, mapping, role_map=None):
    raise NotImplementedError


def translate_response(payload, mapping):
    raise NotImplementedError
