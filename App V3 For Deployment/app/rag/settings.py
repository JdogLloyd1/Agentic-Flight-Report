# settings.py
# RAG deployment defaults: Ollama chat sampling and related knobs live here so a bundle
# under app/rag/ is easy to tune on Posit Connect without hunting in app/core.

from __future__ import annotations

import os


def _float_env(key: str, default: str) -> float:
    raw = os.environ.get(key, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


# Change the literal for deployments where .env is not used; env OLLAMA_TEMPERATURE still wins when set.
_DEFAULT_TEMPERATURE = "0"
OLLAMA_TEMPERATURE = _float_env("OLLAMA_TEMPERATURE", _DEFAULT_TEMPERATURE)
