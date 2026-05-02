# Homework 3 pipeline (`hw quality control/`)

Self-contained flow after **Phase 0** (`standalone/`). **Do not edit `App V3 Local Run/`.**

## Prerequisites

- Python **venv** with `standalone/requirements.txt` installed (includes `pandas`, `pingouin`, `scipy`, `matplotlib`).
- `standalone/.env`: `OLLAMA_API_KEY`, optional `OLLAMA_HOST`, `OLLAMA_MODEL`, optional `HW_FLIGHT_VALIDATION_MODEL` (e.g. **`gpt-oss:120b-cloud`** for `run_validation.py`), `HW_FLIGHT_OLLAMA_TIMEOUT_SEC` (default **1200**), tool/RAG limits as needed.
- For reliable cloud runs: use **`run_smoke_agents_12.py --sequential`** (see `standalone/README.md`).

## Phase 1 — Freeze Agent 1 & 2 artifacts

From `standalone/`:

```bash
python run_smoke_agents_12.py --sequential
```

Writes:

- `experiment_data/agent1_live.txt`
- `experiment_data/agent2_reference.txt`
- `experiment_data/run_manifest.json`

Flight **date** defaults to **today**; override with `--date YYYY-MM-DD`.

## Phase 2 — Agent 3 prompt experiment (A, B, C × N)

From **`hw quality control/`** (parent of `standalone/`):

```bash
cd "hw quality control"
standalone\.venv\Scripts\python.exe run_agent3_experiment.py --n 10
```

- `--n` = runs **per** prompt (total syntheses = `3 × n`).
- Outputs: `experiment_data/synthesis_runs/*.md` and appends **`synthesis_runs/index.csv`**.

Prompts: **`agent3_prompts.py`** (B, C) + baseline **A** from `hw_flight.agents.airspace_synthesizer`.

To avoid mixing batches, delete or rename `experiment_data/synthesis_runs/` (or only `index.csv`) before a fresh experiment.

## Phase 3 — Validation

```bash
standalone\.venv\Scripts\python.exe run_validation.py
```

Reads live/reference + each synthesis listed in `synthesis_runs/index.csv`, calls the **validator** LLM, writes **`experiment_data/validation_scores.csv`**.

## Phase 4 — Statistics

```bash
standalone\.venv\Scripts\python.exe run_statistics.py
```

Runs Bartlett + ANOVA or Welch ANOVA (and t-test if only two groups), prints tables, saves **`experiment_data/overall_score_by_prompt.png`**.

## Rubric / documentation

- **Criteria table & design notes:** `validation_criteria.md`
- **Course references:** `Reference Docs/HOMEWORK3.md`, `Reference Docs/02_ai_quality_control modified.py`, `Reference Docs/03_statistical_comparison.py`

## Git links for submission

Point graders at files under **`hw quality control/`** and **`hw quality control/standalone/`** in your repo (raw URLs on GitHub).
