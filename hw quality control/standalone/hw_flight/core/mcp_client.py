# mcp_client.py — execute MCP tools (in-process or HTTP bridge).
# Derived from App V3 Local Run/app/core/mcp_client.py; imports hw_flight.core.config.

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from hw_flight.core import config


def call_tool(name: str, arguments: dict[str, Any] | None) -> str:
    """
    Run a tool by name. If MCP_BASE_URL is set, POST to /tools/call on that server;
    otherwise import and run the local registry (same code as the MCP server).
    """
    if not config.MCP_BASE_URL:
        from mcp_server.tools.registry import dispatch_tool  # noqa: PLC0415

        config.log_verbose(f"MCP in-process call_tool name={name} args_keys={list((arguments or {}).keys())}")
        t0 = time.perf_counter()
        out: str = ""
        try:
            out = dispatch_tool(name, arguments)
        finally:
            elapsed = time.perf_counter() - t0
            snippet = (out[:200] + "…") if len(out) > 200 else out
            config.log_verbose(
                f"MCP in-process call_tool done name={name} elapsed_s={elapsed:.2f} result_chars={len(out)} "
                f"preview={snippet!r}"
            )
        return out

    url = f"{config.MCP_BASE_URL}/tools/call"
    payload = {"name": name, "arguments": arguments or {}}
    config.log_verbose(f"MCP HTTP call_tool url={url} name={name}")
    t0 = time.perf_counter()
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
            if not isinstance(body, dict):
                return json.dumps(
                    {
                        "error": "mcp_bridge_unexpected_body",
                        "detail": str(body)[:2000],
                    }
                )
            if "result" not in body:
                return json.dumps(
                    {
                        "error": "mcp_bridge_missing_result",
                        "detail": str(body)[:2000],
                    }
                )
            raw = body["result"]
            if raw is None:
                return json.dumps(
                    {"error": "mcp_bridge_null_result", "detail": "Bridge returned null result."}
                )
            if isinstance(raw, str):
                out = raw
            else:
                out = json.dumps(raw)
            elapsed = time.perf_counter() - t0
            config.log_verbose(f"MCP HTTP call_tool done name={name} elapsed_s={elapsed:.2f} result_chars={len(out)}")
            return out
    except httpx.RequestError as e:
        elapsed = time.perf_counter() - t0
        config.log_verbose(f"MCP HTTP call_tool failed name={name} elapsed_s={elapsed:.2f} err={e!r}")
        return json.dumps({"error": "mcp_bridge_connection_error", "detail": str(e)})


def list_tool_schemas() -> list[dict[str, Any]]:
    """OpenAI-style tool schemas for Ollama Agent 1."""
    from mcp_server.tools.registry import DEFAULT_AGENT_TOOL_SCHEMAS  # noqa: PLC0415

    return list(DEFAULT_AGENT_TOOL_SCHEMAS)
