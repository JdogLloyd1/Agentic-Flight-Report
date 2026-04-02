# app/run_me.py
# Local Shiny UI. Run from repo root: python app/run_me.py

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    os.chdir(_ROOT)
    host = os.environ.get("SHINY_HOST", "127.0.0.1")
    port = os.environ.get("SHINY_PORT", "8000")
    cmd = [
        sys.executable,
        "-m",
        "shiny",
        "run",
        "app/shiny_app.py",
        "--reload",
        "--host",
        host,
        "--port",
        port,
    ]
    raise SystemExit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
