# http_bridge.py
# Minimal HTTP POST /tools/call so a remote Shiny app can use MCP_BASE_URL.

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from mcp_server.tools.registry import dispatch_tool

app = FastAPI(title="MCP tool bridge", version="1.0.0")


class ToolCallBody(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


@app.post("/tools/call", response_model=None)
def tools_call(body: ToolCallBody) -> dict[str, Any] | JSONResponse:
    """Return {result: str}; on unexpected failures return JSON with error + HTTP 500."""
    try:
        return {"result": dispatch_tool(body.name, body.arguments)}
    except Exception as e:  # noqa: BLE001 — last-resort; dispatch_tool normally returns JSON
        return JSONResponse(
            status_code=500,
            content={"error": "dispatch_failed", "detail": str(e), "type": type(e).__name__},
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
