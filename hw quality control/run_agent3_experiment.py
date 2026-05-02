# run_agent3_experiment.py — Phase 2: generate Agent 3 syntheses for prompts A/B/C × N runs.
#
# Usage (from repo, with venv that has standalone deps + path):
#   cd "hw quality control"
#   ..\.venv\Scripts\python.exe run_agent3_experiment.py --n 10
#
# Prereq: experiment_data/agent1_live.txt and agent2_reference.txt (e.g. from run_smoke_agents_12.py).

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HWQC = Path(__file__).resolve().parent
_STANDALONE = _HWQC / "standalone"
if str(_STANDALONE) not in sys.path:
    sys.path.insert(0, str(_STANDALONE))

from agent3_prompts import PROMPT_B_EXEC_BRIEF, PROMPT_C_CONSERVATIVE  # noqa: E402
from hw_flight.agents.airspace_synthesizer import ROLE as PROMPT_A_BASELINE  # noqa: E402
from hw_flight.agents.airspace_synthesizer import run_airspace_synthesizer  # noqa: E402
from hw_flight.core import config as hw_config  # noqa: E402


def _prompts() -> dict[str, str]:
    return {
        "A": PROMPT_A_BASELINE,
        "B": PROMPT_B_EXEC_BRIEF,
        "C": PROMPT_C_CONSERVATIVE,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Agent 3 prompt experiment (A/B/C × N).")
    parser.add_argument(
        "--data-dir",
        default=str(_HWQC / "experiment_data"),
        help="Directory with agent1_live.txt and agent2_reference.txt",
    )
    parser.add_argument("--n", type=int, default=10, help="Runs per prompt (total files = 3×N).")
    parser.add_argument("--model", default=None, help="Override OLLAMA_MODEL for this run.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    live_path = data_dir / "agent1_live.txt"
    ref_path = data_dir / "agent2_reference.txt"
    if not live_path.is_file() or not ref_path.is_file():
        raise SystemExit(
            f"Missing {live_path.name} or {ref_path.name} under {data_dir}. Run smoke test first."
        )

    live = live_path.read_text(encoding="utf-8")
    ref = ref_path.read_text(encoding="utf-8")

    out_dir = data_dir / "synthesis_runs"
    out_dir.mkdir(parents=True, exist_ok=True)

    index_path = out_dir / "index.csv"
    fieldnames = [
        "prompt_id",
        "run_id",
        "rel_path",
        "model",
        "created_at_utc",
        "chars",
    ]

    new_rows: list[dict[str, str | int]] = []
    prompts = _prompts()
    model_used = args.model or hw_config.OLLAMA_MODEL

    hw_config.log_info(
        f"agent3_experiment: n={args.n} model={model_used} out={out_dir} "
        f"timeout_s={int(hw_config.OLLAMA_REQUEST_TIMEOUT)}"
    )

    for pid in ("A", "B", "C"):
        role = prompts[pid]
        for run in range(1, args.n + 1):
            run_id = f"{pid}_{run:03d}"
            fname = f"{run_id}.md"
            fpath = out_dir / fname
            hw_config.log_info(f"agent3_experiment: generating {run_id} …")
            text = run_airspace_synthesizer(live, ref, model=args.model, role=role)
            fpath.write_text(text, encoding="utf-8")
            rel = f"synthesis_runs/{fname}"
            new_rows.append(
                {
                    "prompt_id": pid,
                    "run_id": run_id,
                    "rel_path": rel,
                    "model": model_used,
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "chars": str(len(text)),
                }
            )
            hw_config.log_info(f"agent3_experiment: wrote {fname} chars={len(text)}")

    write_header = not index_path.is_file()
    with index_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        for row in new_rows:
            w.writerow(row)

    manifest = data_dir / "agent3_experiment_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "n_per_prompt": args.n,
                "model": model_used,
                "rows_appended": len(new_rows),
                "index_csv": str(index_path.relative_to(data_dir)),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    hw_config.log_info(f"agent3_experiment: appended {len(new_rows)} rows to {index_path}")
    print(f"Done. Outputs under {out_dir}", flush=True)


if __name__ == "__main__":
    main()
