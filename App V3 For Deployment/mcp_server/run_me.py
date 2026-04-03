# mcp_server/run_me.py
# Local MCP SSE server (FastMCP). Run from repo root: python mcp_server/run_me.py
# Default: reload off. Set MCP_RELOAD=1 for dev. For the HTTP bridge used with MCP_BASE_URL, see README.

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    os.chdir(_ROOT)
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))

    import uvicorn

    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "8765"))
    reload_on = os.environ.get("MCP_RELOAD", "").lower() in ("1", "true", "yes")
    uvicorn.run(
        "mcp_server.server:app",
        host=host,
        port=port,
        reload=reload_on,
    )


if __name__ == "__main__":
    main()
