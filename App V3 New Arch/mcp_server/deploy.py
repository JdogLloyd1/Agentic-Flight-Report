# deploy.py
# Publish the MCP SSE app to Posit Connect using rsconnect-python (optional).

from __future__ import annotations

import os
import sys

from pathlib import Path


def main() -> None:
    key = os.environ.get("POSIT_CONNECT_PUBLISHER")
    if not key:
        print("Set POSIT_CONNECT_PUBLISHER in .env for rsconnect.", file=sys.stderr)
        sys.exit(1)
    try:
        import rsconnect  # noqa: PLC0415 — optional dependency
    except ImportError:
        print("Install rsconnect-python: pip install rsconnect-python", file=sys.stderr)
        sys.exit(1)

    repo = Path(__file__).resolve().parent.parent
    os.chdir(repo)
    # Adjust server URL and app name for your Connect instance.
    print(
        "Configure Connect server URL and app name inside this script before deploying.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
