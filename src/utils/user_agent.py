from importlib import metadata

try:
    _versao = metadata.version("ai-rotation-key")
except metadata.PackageNotFoundError:
    _versao = "dev"

USER_AGENT = f"ai-rotation-key/{_versao}"
