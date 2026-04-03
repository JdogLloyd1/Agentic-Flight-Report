# ollama_client.py
# Ollama Cloud /api/chat — text chat and multi-turn tool calling (Agent 1).

from __future__ import annotations

import json
from typing import Any

import requests

from app.core import config
from app.core import mcp_client
from app.rag import settings as rag_settings


def _post_chat(body: dict[str, Any]) -> dict[str, Any]:
    """POST /api/chat and return parsed JSON message envelope; raises ValueError on recoverable failures."""
    headers = {**config.OLLAMA_HEADERS, "Content-Type": "application/json"}
    try:
        r = requests.post(config.CHAT_URL, json=body, headers=headers, timeout=300)
    except requests.exceptions.Timeout as e:
        raise ValueError("Ollama API request timed out (300s). Try again or reduce tool usage.") from e
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Ollama API request failed: {e}") from e

    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        code = r.status_code
        if code in (401, 403):
            raise ValueError(
                "Ollama API rejected the request (HTTP %s). Check OLLAMA_API_KEY and model access."
                % code
            ) from e
        if code == 429:
            raise ValueError("Ollama API rate limit (HTTP 429). Try again in a moment.") from e
        if code >= 500:
            raise ValueError("Ollama API server error (HTTP %s). Try again later." % code) from e
        snippet = (r.text or "")[:400]
        raise ValueError("Ollama API error (HTTP %s): %s" % (code, snippet or str(e))) from e

    try:
        return r.json()
    except json.JSONDecodeError as e:
        raise ValueError(
            "Ollama returned non-JSON (HTTP %s). Check OLLAMA_HOST and network."
            % r.status_code
        ) from e


def chat_text(
    messages: list[dict[str, Any]],
    model: str | None = None,
) -> str:
    """Single or multi-turn chat without tools."""
    config.validate_ollama_cloud_credentials()
    m = model or config.OLLAMA_MODEL
    body: dict[str, Any] = {
        "model": m,
        "messages": messages,
        "stream": False,
        "options": {"temperature": rag_settings.OLLAMA_TEMPERATURE},
    }
    data = _post_chat(body)
    msg = data.get("message") or {}
    return (msg.get("content") or "").strip()


def chat_with_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    model: str | None = None,
    max_rounds: int = 25,
) -> str:
    """
    Run a tool-calling loop until the model returns final text (no tool_calls).
    Executes tools via app.core.mcp_client.call_tool.
    """
    config.validate_ollama_cloud_credentials()
    m = model or config.OLLAMA_MODEL
    msgs: list[dict[str, Any]] = list(messages)

    for _ in range(max_rounds):
        body: dict[str, Any] = {
            "model": m,
            "messages": msgs,
            "tools": tools,
            "stream": False,
            "options": {"temperature": rag_settings.OLLAMA_TEMPERATURE},
        }
        data = _post_chat(body)
        msg = data.get("message") or {}
        tool_calls = msg.get("tool_calls")

        if tool_calls:
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": msg.get("content") or "",
            }
            assistant_msg["tool_calls"] = tool_calls
            msgs.append(assistant_msg)

            for tc in tool_calls:
                fn = tc.get("function") or {}
                raw_name = fn.get("name")
                if raw_name is None or (isinstance(raw_name, str) and not raw_name.strip()):
                    out = json.dumps(
                        {
                            "error": "invalid_tool_call",
                            "detail": "Missing or empty function name in tool_calls.",
                        }
                    )
                else:
                    name = str(raw_name).strip()
                    raw_args = fn.get("arguments")
                    if isinstance(raw_args, str):
                        try:
                            args = json.loads(raw_args) if (raw_args or "").strip() else {}
                        except json.JSONDecodeError:
                            args = {}
                    else:
                        args = raw_args if isinstance(raw_args, dict) else {}
                    try:
                        out = mcp_client.call_tool(name, args)
                    except Exception as e:  # noqa: BLE001 — surface to model as JSON
                        out = json.dumps(
                            {
                                "error": "mcp_call_failed",
                                "detail": str(e),
                                "type": type(e).__name__,
                            }
                        )
                tool_msg: dict[str, Any] = {"role": "tool", "content": out}
                if tc.get("id"):
                    tool_msg["tool_call_id"] = tc["id"]
                msgs.append(tool_msg)
            continue

        return (msg.get("content") or "").strip()

    raise ValueError(
        "Tool-calling loop stopped after %s rounds without a final assistant message."
        % (max_rounds,)
    )


def agent_run(
    role: str,
    task: str,
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
) -> str:
    """Single-shot system+user message; uses tools if provided."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": role},
        {"role": "user", "content": task},
    ]
    if tools:
        return chat_with_tools(messages, tools, model=model)
    return chat_text(messages, model=model)
