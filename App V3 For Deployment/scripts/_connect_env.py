# _connect_env.py
# Load repo .env and read Posit Connect / rsconnect settings.

from __future__ import annotations

import os
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def ensure_config_loaded() -> None:
    """Import app.core.config so repo .env is applied (same as the Shiny app)."""
    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    import app.core.config  # noqa: F401 — side effect: load_env_file


def connect_api_key() -> str | None:
    return (
        os.environ.get("POSIT_CONNECT_PUBLISHER")
        or os.environ.get("CONNECT_API_KEY")
        or os.environ.get("RSCONNECT_API_KEY")
    )


def connect_server_url() -> str | None:
    url = (os.environ.get("CONNECT_SERVER") or os.environ.get("POSIT_CONNECT_SERVER") or "").strip()
    return url or None


def rsconnect_cli_prefix() -> list[str]:
    """Argv prefix for the rsconnect CLI. Use ``python -m rsconnect.main`` (there is no ``rsconnect.__main__``)."""
    return [sys.executable, "-m", "rsconnect.main"]
