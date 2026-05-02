# Provenance (Homework 3 — Phase 0)

This **`standalone/`** tree is a **self-contained copy** of the App **V3 Local Run** pipeline pieces needed to run Agents 1–4 **without modifying** [`App V3 Local Run`](../../App%20V3%20Local%20Run/) (reference only).

## Copied verbatim (then left unedited except packaging)

- Entire **`mcp_server/`** directory from `App V3 Local Run/mcp_server/`.

## Copied / adapted (imports and paths only)

Python modules under **`hw_flight/`** are derived from:

| Homework path | Upstream reference |
|---------------|-------------------|
| `hw_flight/core/config.py` | `App V3 Local Run/app/core/config.py` |
| `hw_flight/core/mcp_client.py` | `App V3 Local Run/app/core/mcp_client.py` |
| `hw_flight/core/ollama_client.py` | `App V3 Local Run/app/core/ollama_client.py` |
| `hw_flight/rag/settings.py` | `App V3 Local Run/app/rag/settings.py` |
| `hw_flight/rag/search.py` | `App V3 Local Run/app/rag/search.py` |
| `hw_flight/agents/data_collector.py` | `App V3 Local Run/app/agents/data_collector.py` |
| `hw_flight/agents/reference_analyst.py` | `App V3 Local Run/app/agents/reference_analyst.py` |
| `hw_flight/agents/airspace_synthesizer.py` | `App V3 Local Run/app/agents/airspace_synthesizer.py` (+ optional `role` for experiments) |
| `hw_flight/agents/flight_advisor.py` | `App V3 Local Run/app/agents/flight_advisor.py` |
| `hw_flight/agents/orchestrator.py` | `App V3 Local Run/app/agents/orchestrator.py` (+ `agent3_role` / `role` passthrough) |

## RAG index data (runtime, not source)

- `hw_flight/rag/data/index/chunks.json`
- `hw_flight/rag/data/index/airport_index.json`

Copied from `App V3 Local Run/app/rag/data/index/`. Large binary-ish JSON; required for Agent 2 BM25 + airport hybrid retrieval.

## New in homework (not in upstream)

- `run_smoke_agents_12.py` — saves `experiment_data/` artifacts.
- `README.md`, `requirements.txt`, `.env.example`, this file.

Approximate snapshot date: **2026-04-26** (repo state on the student machine when Phase 0 was built).
