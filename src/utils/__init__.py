"""Barrel vazio de propósito.

Importar `src.utils` NÃO carrega os submódulos, evitando o import circular
com `src.providers` (utils/load_config e utils/start_server dependem de
src.providers). Importe os módulos direto, ex.: `from src.utils.load_config import ...`.
A sanitização de payload vive em `src.sanitizer` e nas subclasses de provider.
"""
