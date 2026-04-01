# server.py
# MCP server entry — FastMCP with SSE ASGI app for local run and Posit Connect.

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.tools.registry import TOOL_REGISTRY

mcp = FastMCP(
    "Airspace Intelligence",
    instructions=(
        "FAA NAS status, aviation weather, NWS alerts, TFR awareness, OpenSky, "
        "MyTSA, and web helpers for live operational data."
    ),
)

for _tool_name, _fn in TOOL_REGISTRY.items():
    mcp.add_tool(_fn, name=_tool_name)

# ASGI app for uvicorn / Connect: uvicorn mcp_server.server:app --host 0.0.0.0 --port 8765
app = mcp.sse_app()


def main() -> None:
    """Run MCP over SSE (default path /sse depending on MCP version)."""
    mcp.run(transport="sse", host="0.0.0.0", port=8765)


if __name__ == "__main__":
    main()
