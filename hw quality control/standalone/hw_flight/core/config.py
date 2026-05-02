# config.py — load .env and resolve paths for RAG and API settings.
# Derived from App V3 Local Run/app/core/config.py; paths point at this standalone tree.

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path, *, override: bool = False) -> None:
    """Load KEY=VALUE lines into os.environ."""
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
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = val


# standalone/ (this package's runtime root)
_STANDALONE_ROOT = Path(__file__).resolve().parent.parent.parent
# Agentic-Flight-Report repo root (parent of hw quality control/)
_REPO_ROOT = _STANDALONE_ROOT.parent.parent

# Repo .env first (shared keys), then standalone/.env overrides
load_env_file(_REPO_ROOT / ".env", override=False)
load_env_file(_STANDALONE_ROOT / ".env", override=True)

OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST") or "https://ollama.com"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL") or "qwen3.5:397b"
# Optional: model tag for run_validation.py only (falls back to OLLAMA_MODEL if unset).
OLLAMA_VALIDATION_MODEL = (
    os.environ.get("HW_FLIGHT_VALIDATION_MODEL") or os.environ.get("OLLAMA_VALIDATION_MODEL") or ""
).strip()
CHAT_URL = f"{OLLAMA_HOST.rstrip('/')}/api/chat"
OLLAMA_HEADERS = (
    {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {}
)
OLLAMA_CLOUD = "ollama.com" in (OLLAMA_HOST or "").lower()


def validate_ollama_cloud_credentials() -> None:
    """Raise ValueError if Ollama Cloud is used without OLLAMA_API_KEY."""
    if not OLLAMA_CLOUD:
        return
    if not OLLAMA_API_KEY:
        raise ValueError(
            "OLLAMA_API_KEY is not set. For Ollama Cloud, add it to standalone/.env "
            "or the repo .env. For local Ollama, set OLLAMA_HOST (e.g. http://127.0.0.1:11434)."
        )


MCP_BASE_URL = (os.environ.get("MCP_BASE_URL") or "").strip().rstrip("/")
TSA_WAIT_TIMES_PROXY_URL = (os.environ.get("TSA_WAIT_TIMES_PROXY_URL") or "").strip()

_rag_default = Path(__file__).resolve().parent.parent / "rag" / "data"
RAG_DATA_DIR = Path(os.environ.get("RAG_DATA_DIR") or _rag_default).resolve()


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)).strip())
    except (TypeError, ValueError):
        return default


# --- Context limits (homework standalone defaults keep Ollama Cloud round-trips tractable) ---
# MCP tool results are JSON strings; some APIs return 50k–80k+ chars. Feeding them all back
# into the next /api/chat can stall huge models for many minutes.
# Set HW_FLIGHT_MAX_TOOL_RESULT_CHARS=0 to disable truncation (full fidelity, slow).
MAX_TOOL_RESULT_CHARS = _int_env("HW_FLIGHT_MAX_TOOL_RESULT_CHARS", 14000)

# Agent 2 RAG prompt size: characters per excerpt and how many hits to include.
RAG_HIT_CONTENT_CHARS = _int_env("HW_FLIGHT_RAG_HIT_CONTENT_CHARS", 2800)
MAX_RAG_HITS_IN_PROMPT = _int_env("HW_FLIGHT_MAX_RAG_HITS", 12)

# requests.post timeout for each Ollama /api/chat call (seconds). Large cloud models can exceed 300s.
OLLAMA_REQUEST_TIMEOUT = float(os.environ.get("HW_FLIGHT_OLLAMA_TIMEOUT_SEC", "1200"))


def debug_verbose() -> bool:
    """
    If True, print per-request Ollama and per-tool MCP traces.
    On by default. Set HW_FLIGHT_DEBUG=0 (or false/off) to quiet inner-loop logs.
    """
    v = (os.environ.get("HW_FLIGHT_DEBUG") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def log_info(msg: str) -> None:
    """Always-on milestone line (orchestrator / agent boundaries)."""
    print(f"[hw_flight] {msg}", flush=True)


def log_verbose(msg: str) -> None:
    """Noisy diagnostics; gated by debug_verbose()."""
    if debug_verbose():
        print(f"[hw_flight] {msg}", flush=True)
