# Cursor / AI context — App V3 (Airspace Intelligence Agent)

This file orients automated coding tools to the **App V3 For Deployment** tree (Posit Connect bundle). Human feature docs and screenshots live under **`App V3 Local Run/`**.

## Table of Contents

- [Project summary](#project-summary)
- [Repository layout](#repository-layout)
- [Tech stack](#tech-stack)
- [Entry points and run order](#entry-points-and-run-order)
- [Conventions](#conventions)
- [Environment](#environment)
- [APIs and libraries](#apis-and-libraries)
- [Code examples](#code-examples)
- [Reference links](#reference-links)

## Project summary

**App V3** implements a four-agent pipeline (data collection → reference search → synthesis → flight advice) behind a **Shiny for Python** UI. Agent 1 uses **Ollama’s chat API with tool calling**; tools are implemented in `mcp_server/tools/` and either invoked **in process** or via a remote **MCP HTTP/SSE** server when `MCP_BASE_URL` is set. Agent 2 uses **BM25** keyword search over an on-disk chunk index, not vector embeddings. The repo root [`PLAN.md`](../PLAN.md) describes the product architecture and external APIs in detail.

## Repository layout

All paths are relative to **`App V3 For Deployment/`**.

| Path | Role |
|------|------|
| [`app/shiny_app.py`](app/shiny_app.py) | Shiny `App` definition: flight form, `extended_task` workflow, tabbed outputs for agents 1–4 and errors. |
| [`app/run_me.py`](app/run_me.py) | Local entry: `shiny run app/shiny_app.py`; add `SHINY_RELOAD=1` for `--reload`. |
| [`scripts/deploy_shiny.py`](scripts/deploy_shiny.py) | `rsconnect deploy shiny` → entry `app.shiny_app:app`. |
| [`scripts/deploy_mcp_http_bridge.py`](scripts/deploy_mcp_http_bridge.py) | `rsconnect deploy fastapi` → entry `mcp_server.http_bridge:app` (FastAPI/ASGI, not generic `deploy api`). |
| [`scripts/_connect_env.py`](scripts/_connect_env.py) | Loads `.env`; reads `CONNECT_SERVER`, publisher key. |
| [`app/agents/orchestrator.py`](app/agents/orchestrator.py) | `FlightContext`, `run_agents_1_and_2`, `run_agent_3`, `run_agent_4`. |
| [`app/agents/data_collector.py`](app/agents/data_collector.py) | Agent 1 — tool loop + Ollama. |
| [`app/agents/reference_analyst.py`](app/agents/reference_analyst.py) | Agent 2 — `search_reference` + LLM. |
| [`app/agents/airspace_synthesizer.py`](app/agents/airspace_synthesizer.py) | Agent 3. |
| [`app/agents/flight_advisor.py`](app/agents/flight_advisor.py) | Agent 4. |
| [`app/core/config.py`](app/core/config.py) | Loads `.env` from **this app folder**, Ollama and MCP settings. |
| [`app/core/ollama_client.py`](app/core/ollama_client.py) | Chat completions with optional tools. |
| [`app/core/mcp_client.py`](app/core/mcp_client.py) | HTTP client for remote MCP when configured. |
| [`app/rag/ingest.py`](app/rag/ingest.py) | Build `chunks.json` (and related indexes). |
| [`app/rag/search.py`](app/rag/search.py) | `search_reference()` BM25. |
| [`mcp_server/server.py`](mcp_server/server.py) | MCP server entry. |
| [`mcp_server/http_bridge.py`](mcp_server/http_bridge.py) | HTTP/SSE bridge for local tools. |
| [`mcp_server/tools/registry.py`](mcp_server/tools/registry.py) | `TOOL_REGISTRY`, `ALL_TOOL_SCHEMAS`, `DEFAULT_AGENT_TOOL_SCHEMAS`, `dispatch_tool`. |
| [`mcp_server/tools/*.py`](mcp_server/tools/) | One module per API area (NAS, AWC, NOAA, TFR, OpenSky, TSA, web). |
| [`simple_run.md`](simple_run.md) | Human quickstart for run commands. |
| [`screenshots/`](screenshots/) | Images for [`README.md`](README.md). |

## Tech stack

- **Python 3** — see [`requirements.txt`](requirements.txt) for `shiny`, `rank_bm25`, MCP SDK, HTTP clients, etc.
- **Shiny for Python** — UI and reactivity; app object is `app` in `shiny_app.py`.
- **Ollama** — [Chat API](https://github.com/ollama/ollama/blob/main/docs/api.md) at `{OLLAMA_HOST}/api/chat` with optional `tools` array.
- **MCP** — Tools registered with OpenAI-style `function` schemas; see [`mcp_server/tools/registry.py`](mcp_server/tools/registry.py).

## Entry points and run order

1. **Optional:** `python -m app.rag.ingest` — refresh BM25 index under `app/rag/data/index/`.
2. **Shiny UI:** `python app/run_me.py` → open http://127.0.0.1:8000 (defaults `SHINY_HOST`, `SHINY_PORT`).
3. **Optional MCP SSE server:** `python mcp_server/run_me.py` — default **http://127.0.0.1:8765** (`/sse`). For the HTTP bridge Shiny uses with `MCP_BASE_URL`, run `uvicorn mcp_server.http_bridge:app` locally or deploy it with `scripts/deploy_mcp_http_bridge.py`.

Orchestration order: **Agent 1 ∥ Agent 2** → **Agent 3** → **Agent 4** (see [`orchestrator.py`](app/agents/orchestrator.py)).

## Conventions

- **Style:** Follow [`.cursor/rules/coding_style.mdc`](../.cursor/rules/coding_style.mdc) for `.py` edits in this repo.
- **README style:** Human doc: [`README.md`](README.md) (developer-oriented TOC and sections). Root plan: [`PLAN.md`](../PLAN.md).
- **Tools:** Add implementations in `mcp_server/tools/`, register in `TOOL_REGISTRY` and `ALL_TOOL_SCHEMAS` in [`registry.py`](mcp_server/tools/registry.py). Agent 1’s default schema list excludes `get_aircraft_states`, `url_query`, `web_search_general` unless you widen `DEFAULT_AGENT_TOOL_SCHEMAS`.
- **Config:** [`app/core/config.py`](app/core/config.py) — `OLLAMA_CLOUD` gates API key requirement; `MCP_BASE_URL` empty means in-process tool dispatch from the Shiny process.

## Environment

Copy [`.env.example`](.env.example) to `.env` in **`App V3 For Deployment`**. Never commit secrets. Includes `CONNECT_SERVER`, `POSIT_CONNECT_PUBLISHER` / `CONNECT_API_KEY` for rsconnect; runtime keys: `OLLAMA_*`, `MCP_BASE_URL`, `RAG_DATA_DIR`, `TSA_WAIT_TIMES_PROXY_URL`, `OPENSKY_*`.

## APIs and libraries

| Resource | Documentation |
|----------|----------------|
| Ollama HTTP API | https://github.com/ollama/ollama/blob/main/docs/api.md |
| Shiny for Python | https://shiny.posit.co/py/ |
| FastMCP / MCP Python SDK | https://github.com/jlowin/fastmcp (or the MCP SDK version pinned in `requirements.txt`) |
| FAA NASSTATUS | https://nasstatus.faa.gov/ |
| Aviation Weather Center Data API | https://aviationweather.gov/data/api/ |
| NWS API | https://www.weather.gov/documentation/services-web-api |
| OpenSky Network | https://opensky-network.org/apidoc/ |
| rank_bm25 | https://pypi.org/project/rank-bm25/ |

## Code examples

**Orchestrator: parallel agents 1 and 2**

```python
# See app/agents/orchestrator.py
with ThreadPoolExecutor(max_workers=2) as ex:
    f1 = ex.submit(data_collector.run_data_collector, task1, model)
    f2 = ex.submit(reference_analyst.run_reference_analyst, ...)
```

**Config: Ollama Cloud vs local**

```python
# app/core/config.py — OLLAMA_HOST defaults to https://ollama.com; set OLLAMA_HOST=http://127.0.0.1:11434 for local
CHAT_URL = f"{OLLAMA_HOST.rstrip('/')}/api/chat"
```

**BM25 search**

```python
# app/rag/search.py — search_reference(query, top_k=5)
from app.rag.search import search_reference
rows = search_reference("ground delay program ORD", top_k=5)
```

**Tool dispatch**

```python
# mcp_server/tools/registry.py
from mcp_server.tools.registry import dispatch_tool
out = dispatch_tool("get_metar", {"station_id": "KDFW"})
```

## Reference links

| Resource | URL |
|----------|-----|
| Ollama API | https://github.com/ollama/ollama/blob/main/docs/api.md |
| Shiny for Python | https://shiny.posit.co/py/ |
| rsconnect-python | https://docs.posit.co/rsconnect-python/ |
| Mermaid | https://mermaid.js.org/intro/ |
| CommonMark | https://commonmark.org/help/ |
| Project plan (this repo) | [`PLAN.md`](../PLAN.md) |
