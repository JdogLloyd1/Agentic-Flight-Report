# settings.py — Ollama chat sampling defaults.
# Derived from App V3 Local Run/app/rag/settings.py.

from __future__ import annotations

import os


def _float_env(key: str, default: str) -> float:
    raw = os.environ.get(key, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


_DEFAULT_TEMPERATURE = "0"
OLLAMA_TEMPERATURE = _float_env("OLLAMA_TEMPERATURE", _DEFAULT_TEMPERATURE)
