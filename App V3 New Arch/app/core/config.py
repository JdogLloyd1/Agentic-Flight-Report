# config.py
# Load .env and resolve paths for RAG and API settings.

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ when the key is not already set."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_env_file(_REPO_ROOT / ".env")

OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST") or "https://ollama.com"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL") or "qwen3.5:397b"
CHAT_URL = f"{OLLAMA_HOST.rstrip('/')}/api/chat"
OLLAMA_HEADERS = (
    {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {}
)
# True when targeting Ollama Cloud (default host); local Ollama does not require an API key.
OLLAMA_CLOUD = "ollama.com" in (OLLAMA_HOST or "").lower()


def validate_ollama_cloud_credentials() -> None:
    """Raise ValueError if Ollama Cloud is used without OLLAMA_API_KEY."""
    if not OLLAMA_CLOUD:
        return
    if not OLLAMA_API_KEY:
        raise ValueError(
            "OLLAMA_API_KEY is not set. For Ollama Cloud, copy .env.example to .env and add your key. "
            "For a local Ollama server, set OLLAMA_HOST (e.g. http://127.0.0.1:11434)."
        )

MCP_BASE_URL = (os.environ.get("MCP_BASE_URL") or "").strip().rstrip("/")

# RAG: default to app/rag/data unless RAG_DATA_DIR is set
_rag_default = Path(__file__).resolve().parent.parent / "rag" / "data"
RAG_DATA_DIR = Path(os.environ.get("RAG_DATA_DIR") or _rag_default).resolve()
