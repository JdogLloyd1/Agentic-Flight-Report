# mcp_server/run_me.py
# Local MCP server (uvicorn + FastMCP SSE). Run from repo root: python mcp_server/run_me.py

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
    uvicorn.run(
        "mcp_server.server:app",
        host=host,
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
