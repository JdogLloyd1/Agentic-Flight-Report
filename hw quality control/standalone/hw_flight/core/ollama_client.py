# ollama_client.py — Ollama /api/chat; tool-calling loop for Agent 1.
# Derived from App V3 Local Run/app/core/ollama_client.py.

from __future__ import annotations

import json
import time
from typing import Any

import requests

from hw_flight.core import config
from hw_flight.core import mcp_client
from hw_flight.rag import settings as rag_settings


def _post_chat(body: dict[str, Any], *, label: str = "chat") -> dict[str, Any]:
    """POST /api/chat and return parsed JSON message envelope."""
    model = body.get("model", "")
    has_tools = bool(body.get("tools"))
    n_msgs = len(body.get("messages") or [])
    config.log_verbose(
        f"Ollama POST start label={label} model={model} messages={n_msgs} tools={has_tools} url={config.CHAT_URL}"
    )
    t0 = time.perf_counter()
    headers = {**config.OLLAMA_HEADERS, "Content-Type": "application/json"}
    try:
        r = requests.post(
            config.CHAT_URL,
            json=body,
            headers=headers,
            timeout=config.OLLAMA_REQUEST_TIMEOUT,
        )
    except requests.exceptions.Timeout as e:
        raise ValueError(
            "Ollama API request timed out (%ss). Try HW_FLIGHT_OLLAMA_TIMEOUT_SEC, a smaller model, "
            "or run Agents 1–2 sequentially (see run_smoke_agents_12.py --sequential)."
            % int(config.OLLAMA_REQUEST_TIMEOUT)
        ) from e
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
        data = r.json()
    except json.JSONDecodeError as e:
        raise ValueError(
            "Ollama returned non-JSON (HTTP %s). Check OLLAMA_HOST and network."
            % r.status_code
        ) from e
    elapsed = time.perf_counter() - t0
    msg = data.get("message") or {}
    tcalls = msg.get("tool_calls")
    config.log_verbose(
        f"Ollama POST done label={label} http={r.status_code} elapsed_s={elapsed:.2f} "
        f"tool_calls={len(tcalls) if isinstance(tcalls, list) else 0} "
        f"content_chars={len(msg.get('content') or '')}"
    )
    return data


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
    config.log_info("chat_text: single Ollama request (no tools)")
    data = _post_chat(body, label="chat_text")
    msg = data.get("message") or {}
    return (msg.get("content") or "").strip()


def chat_with_tools(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    model: str | None = None,
    max_rounds: int = 25,
) -> str:
    """Run a tool-calling loop until the model returns final text (no tool_calls)."""
    config.validate_ollama_cloud_credentials()
    m = model or config.OLLAMA_MODEL
    msgs: list[dict[str, Any]] = list(messages)
    config.log_info(
        f"chat_with_tools: model={m} tool_schema_count={len(tools)} max_rounds={max_rounds}"
    )

    for round_i in range(1, max_rounds + 1):
        config.log_verbose(f"tool loop round {round_i}/{max_rounds} (message_count={len(msgs)})")
        body: dict[str, Any] = {
            "model": m,
            "messages": msgs,
            "tools": tools,
            "stream": False,
            "options": {"temperature": rag_settings.OLLAMA_TEMPERATURE},
        }
        data = _post_chat(body, label=f"tools_r{round_i}")
        msg = data.get("message") or {}
        tool_calls = msg.get("tool_calls")

        if tool_calls:
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": msg.get("content") or "",
            }
            assistant_msg["tool_calls"] = tool_calls
            msgs.append(assistant_msg)

            config.log_verbose(
                f"assistant requested {len(tool_calls)} tool call(s): "
                f"{[str((tc.get('function') or {}).get('name')) for tc in tool_calls]}"
            )
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
                    except Exception as e:  # noqa: BLE001
                        out = json.dumps(
                            {
                                "error": "mcp_call_failed",
                                "detail": str(e),
                                "type": type(e).__name__,
                            }
                        )
                    max_tc = config.MAX_TOOL_RESULT_CHARS
                    if max_tc > 0 and len(out) > max_tc:
                        dropped = len(out) - max_tc
                        config.log_verbose(
                            f"truncating tool result for model: tool={name} "
                            f"from {len(out)} to {max_tc} chars (dropped {dropped})"
                        )
                        out = (
                            out[:max_tc]
                            + f"\n... [hw_flight: truncated {dropped} chars from tool {name}]"
                        )
                tool_msg: dict[str, Any] = {"role": "tool", "content": out}
                if tc.get("id"):
                    tool_msg["tool_call_id"] = tc["id"]
                msgs.append(tool_msg)
            continue

        config.log_info(
            f"chat_with_tools: final assistant text after {round_i} round(s), "
            f"chars={len((msg.get('content') or '').strip())}"
        )
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
    m = model or config.OLLAMA_MODEL
    config.log_info(
        f"agent_run: model={m} tools={'yes' if tools else 'no'} task_chars={len(task)}"
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": role},
        {"role": "user", "content": task},
    ]
    if tools:
        return chat_with_tools(messages, tools, model=model)
    return chat_text(messages, model=model)
