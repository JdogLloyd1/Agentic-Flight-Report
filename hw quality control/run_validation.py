# run_validation.py — Phase 3: AI validation of Agent 3 syntheses → validation_scores.csv
#
# Usage:
#   cd "hw quality control"
#   python run_validation.py
#
# Reads experiment_data/synthesis_runs/index.csv (or all *.md in that folder).

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

_HWQC = Path(__file__).resolve().parent
_STANDALONE = _HWQC / "standalone"
if str(_STANDALONE) not in sys.path:
    sys.path.insert(0, str(_STANDALONE))

from hw_flight.core import config as hw_config  # noqa: E402
from hw_flight.core import ollama_client  # noqa: E402

VALIDATOR_ROLE = """You are a strict technical QA reviewer for merged aviation briefings (Agent 3 output). Your job is to **differentiate** quality: most drafts are imperfect. **Do not default to 4–5.** If you are unsure between two integers, pick the **lower**.

You are given THREE blocks in the user message:
1) LIVE DATA (Agent 1 JSON)
2) REFERENCE ANALYSIS (Agent 2 text)
3) SYNTHESIS (Agent 3 markdown to score)

### Scale calibration (use every time)
- **5** — Exceptional: no material flaw on that dimension; would serve as a teaching example.
- **4** — Strong: one **minor** issue only (e.g. small wording slip, tiny omission that does not change decisions).
- **3** — Acceptable: **clear** limitations (missing nuance, uneven coverage, vague attribution, or mild overconfidence) but still usable with caution.
- **2** — Weak: serious gaps, confusing structure, or multiple unsupported claims; would need rework.
- **1** — Fails: unsafe mix-ups, contradictions of live data, or unusable narrative.

**5 is rare.** If three or more dimensions are 5, you must justify that in `details` with specific evidence. **Do not assign the same integer to all five dimensions** unless you can cite why each dimension truly matches that level (independent judgment per dimension).

### Deduct points when you see (non-exhaustive)
- Live vs reference tagging is inconsistent, easy to misread, or buries operational facts under generic reference prose.
- Any theme **material** to this flight appears in Agent 1/2 but is **absent**, **generic**, or **not operationalized** in the synthesis.
- Numbers, programs (GDP/GS), times, or airport IDs **do not match** the LIVE JSON or are **over-precise** vs what the JSON supports.
- Agent 1 shows empty/error/partial tool output and the synthesis **hides** that, **assumes success**, or **fills** with confident detail not in the payload.
- **Padding**: repeated boilerplate, long reference quotes without adding decision value, or sections that could be cut 30%+ without loss.
- Executive-style briefs: if they **drop** operational specifics that appear in LIVE JSON (delays, programs, key hazards), cap **section_coverage** at **3** and penalize **grounding**/**gap_calibration** if they imply completeness.

### checklist_coverage_pct
Count the share of **expected** `##` sections for this briefing style that contain **substantive** content tied to the inputs—not empty headings or placeholder bullets. Round to nearest **5**.

Output **one JSON object only** — no markdown fences, no extra text.

JSON keys (exact):
- "live_reference_separation" (integer 1–5)
- "section_coverage" (integer 1–5)
- "grounding" (integer 1–5)
- "gap_calibration" (integer 1–5)
- "concision" (integer 1–5)
- "checklist_coverage_pct" (integer 0–100)
- "grounding_gate" (boolean): true only if you see **no clear** contradiction of LIVE JSON facts.
- "details" (string, max 60 words): Name **at least one concrete strength and one concrete weakness** (quote or point to section/claim).

After you decide the scores, the user will compute overall_score as the mean of the five integer dimensions (live_reference_separation, section_coverage, grounding, gap_calibration, concision)."""


def _build_task(agent1: str, agent2: str, synthesis: str) -> str:
    return (
        "=== LIVE DATA (Agent 1) ===\n"
        f"{agent1}\n\n"
        "=== REFERENCE ANALYSIS (Agent 2) ===\n"
        f"{agent2}\n\n"
        "=== SYNTHESIS (Agent 3) ===\n"
        f"{synthesis}\n"
    )


def _parse_validator_json(raw: str) -> dict:
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("No JSON object in validator response")
    return json.loads(m.group(0))


def _overall_score(row: dict) -> float:
    keys = [
        "live_reference_separation",
        "section_coverage",
        "grounding",
        "gap_calibration",
        "concision",
    ]
    vals = [float(row[k]) for k in keys]
    return round(sum(vals) / len(vals), 4)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Agent 3 synthesis files; write validation_scores.csv")
    parser.add_argument("--data-dir", default=str(_HWQC / "experiment_data"))
    parser.add_argument(
        "--index",
        default="synthesis_runs/index.csv",
        help="Relative to data-dir; lists synthesis files",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Ollama model tag; default HW_FLIGHT_VALIDATION_MODEL, else OLLAMA_MODEL",
    )
    parser.add_argument(
        "--output",
        default="validation_scores.csv",
        help="Relative to data-dir",
    )
    args = parser.parse_args()

    validation_model = (
        args.model or hw_config.OLLAMA_VALIDATION_MODEL or hw_config.OLLAMA_MODEL
    )
    hw_config.log_info(f"validation model={validation_model}")

    data_dir = Path(args.data_dir)
    index_path = data_dir / args.index
    if not index_path.is_file():
        raise SystemExit(f"Missing index: {index_path}")

    live = (data_dir / "agent1_live.txt").read_text(encoding="utf-8")
    ref = (data_dir / "agent2_reference.txt").read_text(encoding="utf-8")

    out_csv = data_dir / args.output
    fieldnames = [
        "prompt_id",
        "run_id",
        "synthesis_path",
        "live_reference_separation",
        "section_coverage",
        "grounding",
        "gap_calibration",
        "concision",
        "checklist_coverage_pct",
        "grounding_gate",
        "overall_score",
        "details",
        "validator_model",
    ]

    rows_out: list[dict] = []
    with index_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, rec in enumerate(reader):
            rel = rec.get("rel_path") or ""
            synth_path = data_dir / rel
            if not synth_path.is_file():
                hw_config.log_info(f"skip missing file: {synth_path}")
                continue
            synthesis = synth_path.read_text(encoding="utf-8")
            task = _build_task(live, ref, synthesis)
            hw_config.log_info(
                f"validate row {i + 1}: {rec.get('run_id')} chars={len(synthesis)}"
            )
            raw = ollama_client.agent_run(
                VALIDATOR_ROLE, task, tools=None, model=validation_model
            )
            try:
                data = _parse_validator_json(raw)
            except Exception as e:  # noqa: BLE001
                hw_config.log_info(f"parse failed for {rec.get('run_id')}: {e!r}")
                data = {
                    "live_reference_separation": 1,
                    "section_coverage": 1,
                    "grounding": 1,
                    "gap_calibration": 1,
                    "concision": 1,
                    "checklist_coverage_pct": 0,
                    "grounding_gate": False,
                    "details": f"parse_error: {e}",
                }
            overall = _overall_score(data)
            rows_out.append(
                {
                    "prompt_id": rec.get("prompt_id", ""),
                    "run_id": rec.get("run_id", ""),
                    "synthesis_path": rel,
                    "live_reference_separation": int(data["live_reference_separation"]),
                    "section_coverage": int(data["section_coverage"]),
                    "grounding": int(data["grounding"]),
                    "gap_calibration": int(data["gap_calibration"]),
                    "concision": int(data["concision"]),
                    "checklist_coverage_pct": int(data.get("checklist_coverage_pct", 0)),
                    "grounding_gate": bool(data.get("grounding_gate", False)),
                    "overall_score": overall,
                    "details": str(data.get("details", ""))[:500],
                    "validator_model": validation_model,
                }
            )

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)

    hw_config.log_info(f"wrote {len(rows_out)} rows to {out_csv}")
    print(f"Done. {out_csv}", flush=True)


if __name__ == "__main__":
    main()
