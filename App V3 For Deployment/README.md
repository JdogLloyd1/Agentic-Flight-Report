# Airspace Intelligence Agent — App V3 (Posit Connect deployment)

This tree matches **[`App V3 Local Run/`](../App%20V3%20Local%20Run/)** functionally but is tuned for **publishing to Posit Connect** with `rsconnect-python`, runtime defaults suited to hosted execution, and deploy scripts for the Shiny UI and the **MCP HTTP tool bridge**.

For day-to-day development on your laptop, prefer **`App V3 Local Run`**.

## Contents

- [Requirements](#requirements)
- [Install](#install)
- [Configure (.env and Connect)](#configure-env-and-connect)
- [Deploy order](#deploy-order)
- [Deploy scripts](#deploy-scripts)
- [Runtime behavior](#runtime-behavior)
- [Local smoke tests](#local-smoke-tests)
- [Architecture notes](#architecture-notes)
- [Docs and screenshots](#docs-and-screenshots)

## Requirements

- Python **3.11** recommended (see [`runtime.txt`](runtime.txt); align with your Connect instance).
- [`requirements.txt`](requirements.txt) includes **`rsconnect-python`** for the deploy scripts.
- Network access from Connect workers to **Ollama Cloud** or your approved **Ollama** endpoint, and to public FAA/NOAA APIs (and optional OpenSky / TSA proxy as configured).

## Install

From this directory:

```bash
pip install -r requirements.txt
```

Copy [`.env.example`](.env.example) to `.env` and fill in values (see below).

## Configure (.env and Connect)

| Variable | Role |
|----------|------|
| `CONNECT_SERVER` | Base URL of Posit Connect (e.g. `https://connect.example.com/`). Used by deploy scripts. |
| `POSIT_CONNECT_PUBLISHER` or `CONNECT_API_KEY` | Publisher API key for `rsconnect` (same secret; either name works in scripts). |
| `OLLAMA_API_KEY`, `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_TEMPERATURE` | Ollama chat — set on **each** deployed content item in the Connect **Vars** tab (or pass `-E` during deploy). |
| `MCP_BASE_URL` | After the HTTP bridge is deployed, set this on the **Shiny** content to the bridge’s **public base URL** (no trailing slash). Leave empty to run tools **in-process** inside the Shiny worker. |
| `RAG_DATA_DIR` | Optional override; default is `app/rag/data` in the bundle. |
| `TSA_WAIT_TIMES_PROXY_URL`, `OPENSKY_*` | As in the local app. |

**Important:** `.env` is for your **publish workstation** and for local tests. On the server, Connect injects environment variables you configure in the **Connect dashboard**; mirror secrets there for production.

## Deploy order

1. **Optional but typical:** Deploy the **MCP HTTP bridge** first (`mcp_server.http_bridge:app` — exposes `POST /tools/call` and `GET /health`). Copy the content’s public URL.
2. In Connect **Vars** for the **Shiny** content, set `MCP_BASE_URL` to that URL (or deploy Shiny with `-E MCP_BASE_URL=...`).
3. Deploy the **Shiny** app (`app.shiny_app:app`).
4. Ensure **`python -m app.rag.ingest`** has been run before bundling so `app/rag/data/index/` ships with the app (Agent 2).

## Deploy scripts

From this directory, with `CONNECT_SERVER` and a publisher key in `.env`:

```bash
python scripts/deploy_mcp_http_bridge.py
python scripts/deploy_shiny.py
```

Options (both scripts):

- `-t "Title on Connect"` — content title.
- `--no-verify` — if Connect cannot be reached for post-deploy checks from your network.
- `-E NAME=value` — forward vars into the Connect bundle metadata (repeatable); you can also set vars only in the Connect UI.

The Shiny entry point is **`app.shiny_app:app`**. The tool bridge is published with **`rsconnect deploy fastapi`** (FastAPI/ASGI). Do **not** use `deploy api` for that app — that subcommand targets the generic Python API mode (e.g. Flask-style); FastAPI content needs **`python-fastapi`** mode on Connect ([rsconnect-python deploy commands](https://docs.posit.co/rsconnect-python/commands/deploy/)).

Bundles exclude `screenshots/`, `scripts/`, and common caches to keep uploads smaller.

**rsconnect-python alignment (see docs):** use **`CONNECT_SERVER`** and **`CONNECT_API_KEY`** (or `-s` / `-k`); optional **`-n`** server nickname via `rsconnect add` so you do not pass URL/key every time. **`--exclude`** patterns are globs — run deploy from this folder or rely on the scripts’ `cwd` + `"."` so patterns do not match sibling projects. Shiny for Python requires Connect **2022.07.0+**; FastAPI requires **2021.08.0+**. Use **`runtime.txt`** / **`--override-python-version`** if your local Python differs from the server.

## Runtime behavior

- **`python app/run_me.py`** — runs Shiny without `--reload` unless you set **`SHINY_RELOAD=1`** (closer to Connect behavior).
- **`python mcp_server/run_me.py`** — SSE MCP server; **`MCP_RELOAD=1`** enables uvicorn reload for development.
- On Connect, processes run behind Connect’s proxy; **server-side** `httpx` calls from Shiny to `MCP_BASE_URL` do not require browser CORS.

## Local smoke tests

**HTTP bridge** (what the Shiny app expects when `MCP_BASE_URL` is set):

```bash
python -m uvicorn mcp_server.http_bridge:app --host 127.0.0.1 --port 8766
```

Set `MCP_BASE_URL=http://127.0.0.1:8766` and run `python app/run_me.py`.

**Shiny** at http://127.0.0.1:8000 — default host/port unchanged; use `SHINY_HOST` / `SHINY_PORT` if needed.

## Architecture notes

- **In-process tools** (`MCP_BASE_URL` empty): same as local — tools execute inside the Shiny worker.
- **Split deployment** (`MCP_BASE_URL` set): Agent 1 calls **`POST {MCP_BASE_URL}/tools/call`** — only the **http_bridge** app provides that route; the FastMCP **SSE** app (`mcp_server.server:app`) does not.

## Docs and screenshots

- Full feature documentation and screenshots: **[`App V3 Local Run/README.md`](../App%20V3%20Local%20Run/README.md)**.
- AI-oriented file map: [`README_CURSOR.md`](README_CURSOR.md).
- Product plan (repo root): [`PLAN.md`](../PLAN.md).

## License and disclaimers

Outputs are **AI-generated** and **not** official FAA or airline information. Always verify operational decisions with dispatch, ATC, and your carrier.
