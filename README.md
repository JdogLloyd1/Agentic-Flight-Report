# Agentic-Flight-Report

AI agentic workflow to describe the US airspace picture, causes of delays and cancellations, and flight-specific guidance using live NAS and weather tools plus FAA reference search (BM25 RAG) and a Shiny for Python UI.

## App V3 (current build)

The stack is split into two folders:

| Folder | Purpose |
|--------|---------|
| **[`App V3 Local Run/`](App%20V3%20Local%20Run/)** | **Local development** — run Shiny and optional MCP on your machine; full README, screenshots, and architecture. |
| **[`App V3 For Deployment/`](App%20V3%20For%20Deployment/)** | **Posit Connect** — `rsconnect-python` scripts, `runtime.txt`, production-oriented defaults, deploy instructions. |

- **[`App V3 Local Run/README.md`](App%20V3%20Local%20Run/README.md)** — architecture, tool table, RAG, local run, screenshots.
- **[`App V3 Local Run/README_CURSOR.md`](App%20V3%20Local%20Run/README_CURSOR.md)** — file map and conventions for AI-assisted development.
- **[`App V3 For Deployment/README.md`](App%20V3%20For%20Deployment/README.md)** — Connect deployment, env vars, `scripts/deploy_*.py`.

High-level architecture and API notes: **[`PLAN.md`](PLAN.md)**.
