# Homework 3 — Standalone V3-style pipeline (Phase 0+)

**Full homework flow (Phases 1–4):** see [`../HOMEWORK_PIPELINE.md`](../HOMEWORK_PIPELINE.md).

This folder runs **Agents 1–4** the same way as **App V3 Local Run**, using **copied** code and data so **nothing under `App V3 Local Run/` needs to change**. See [PROVENANCE.md](PROVENANCE.md) for the file mapping.

## Layout

- `mcp_server/` — MCP tool implementations (in-process dispatch by default).
- `hw_flight/` — config, Ollama client, RAG search, agents, orchestrator.
- `run_smoke_agents_12.py` — run Agents **1 and 2** only; writes `../experiment_data/`.
- `../experiment_data/` — created when you run the smoke script (gitignored optional).

## Setup

1. Create a virtual environment (recommended) and install deps:

   ```bash
   cd "hw quality control/standalone"
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and set **`OLLAMA_API_KEY`** / **`OLLAMA_HOST`** / **`OLLAMA_MODEL`** to match how you run Ollama (cloud vs local). The loader also reads the **repo root** `.env` first, then overrides from `standalone/.env`.

3. Confirm RAG index files exist:

   - `hw_flight/rag/data/index/chunks.json`
   - `hw_flight/rag/data/index/airport_index.json`

   If missing, copy them from `App V3 Local Run/app/rag/data/index/` (see PROVENANCE).

## Run Agents 1–2 (smoke test)

From **`standalone/`**:

```bash
python run_smoke_agents_12.py
```

If Ollama Cloud times out or feels slow, try **`python run_smoke_agents_12.py --sequential`** (one API flight at a time) and/or raise **`HW_FLIGHT_OLLAMA_TIMEOUT_SEC`** (default **1200**). For validation, set **`HW_FLIGHT_VALIDATION_MODEL`** (e.g. **`gpt-oss:120b-cloud`**) so `run_validation.py` can use a smaller/faster model than **`OLLAMA_MODEL`**.

Optional flags: `--carrier`, `--flight-number`, `--date`, `--origin`, `--destination`, `--model`, `--out-dir`, `--sequential`.

Outputs:

- `experiment_data/agent1_live.txt`
- `experiment_data/agent2_reference.txt`
- `experiment_data/run_manifest.json`

By default the flight **`--date`** is **today** (`YYYY-MM-DD` in the machine’s local timezone). Pass `--date` to override.

## Run full workflow in Python

```python
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path("standalone").resolve()))

from hw_flight.agents.orchestrator import FlightContext, run_workflow

out = run_workflow(
    FlightContext("AA", "849", date.today().isoformat(), "DFW", "BOS"),
    model=None,          # default from env
    agent3_role=None,    # pass a string to override Agent 3 system prompt
)
print(out["agent3_synthesis"])
```

## Troubleshooting

- **Debug logging**: Lines prefixed with `[hw_flight]` show where the run is spending time. Milestone lines always print; per-request Ollama and per-tool MCP lines print unless you set **`HW_FLIGHT_DEBUG=0`** (or `false` / `off`) in the environment.
- **Huge tool payloads / slow second Ollama round**: Some MCP tools return 50k–80k+ character JSON. The next `/api/chat` can then take many minutes on cloud. This bundle **truncates** tool results to **`HW_FLIGHT_MAX_TOOL_RESULT_CHARS`** (default **14000**; set **`0`** to disable) and caps Agent 2 RAG excerpts via **`HW_FLIGHT_RAG_HIT_CONTENT_CHARS`** / **`HW_FLIGHT_MAX_RAG_HITS`**.
- **OLLAMA_API_KEY**: Required when `OLLAMA_HOST` points at Ollama Cloud (`ollama.com`).
- **MCP tools**: Default is **in-process** `mcp_server` (no separate server). To use an HTTP bridge, set `MCP_BASE_URL` in `.env`.
- **Agent 2 empty**: Check RAG `chunks.json` path and `RAG_DATA_DIR` if you relocated data.
