# mcp_client.py
# Execute MCP tools — in-process dispatch from mcp_server.tools, or HTTP if MCP_BASE_URL is set.

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core import config


def call_tool(name: str, arguments: dict[str, Any] | None) -> str:
    """
    Run a tool by name. If MCP_BASE_URL is set, POST to /tools/call on that server;
    otherwise import and run the local registry (same code as the MCP server).
    """
    if not config.MCP_BASE_URL:
        from mcp_server.tools.registry import dispatch_tool  # noqa: PLC0415

        return dispatch_tool(name, arguments)

    url = f"{config.MCP_BASE_URL}/tools/call"
    payload = {"name": name, "arguments": arguments or {}}
    try:
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, json=payload)
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError:
                detail: str | Any = (r.text or "")[:1200]
                try:
                    j = r.json()
                    if isinstance(j, dict):
                        detail = j.get("detail", j.get("error", j))
                except json.JSONDecodeError:
                    pass
                return json.dumps(
                    {
                        "error": "mcp_bridge_http_error",
                        "status": r.status_code,
                        "detail": detail,
                    }
                )
            try:
                body = r.json()
            except json.JSONDecodeError:
                return json.dumps(
                    {
                        "error": "mcp_bridge_invalid_json",
                        "detail": (r.text or "")[:800],
                    }
                )
    except httpx.RequestError as e:
        return json.dumps({"error": "mcp_bridge_connection_error", "detail": str(e)})

    return str(body.get("result", body))


def list_tool_schemas() -> list[dict[str, Any]]:
    """OpenAI-style tool schemas for Ollama (Agent 1)."""
    from mcp_server.tools.registry import ALL_TOOL_SCHEMAS  # noqa: PLC0415

    return list(ALL_TOOL_SCHEMAS)
