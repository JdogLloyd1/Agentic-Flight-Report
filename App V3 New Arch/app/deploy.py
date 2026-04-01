# deploy.py
# Publish the Shiny app to Posit Connect with rsconnect-python (configure server URL first).

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
        import rsconnect  # noqa: F401, PLC0415
    except ImportError:
        print("Install rsconnect-python: pip install rsconnect-python", file=sys.stderr)
        sys.exit(1)

    _repo = Path(__file__).resolve().parent.parent
    print(
        "Edit app/deploy.py with your Connect server URL, app name, and rsconnect.deploy_python_api "
        "call. Entry: app.shiny_app:app",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
