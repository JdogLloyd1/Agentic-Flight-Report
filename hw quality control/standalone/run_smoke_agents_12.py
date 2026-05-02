# Smoke test: run Agents 1 and 2 only (saves artifacts for Homework 3).
# Usage (from this folder):
#   python run_smoke_agents_12.py
#
# Requires: dependencies from requirements.txt, Ollama (cloud or local) per .env.example.

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_STANDALONE_ROOT = Path(__file__).resolve().parent
if str(_STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(_STANDALONE_ROOT))

from hw_flight.agents.orchestrator import (  # noqa: E402
    FlightContext,
    run_agents_1_and_2,
    run_agents_1_and_2_sequential,
)
from hw_flight.core import config as hw_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run standalone Agents 1–2 and save outputs.")
    parser.add_argument("--carrier", default="AA")
    parser.add_argument("--flight-number", default="849")
    parser.add_argument(
        "--date",
        dest="flight_date",
        default=None,
        help="Flight date YYYY-MM-DD (default: today, local timezone).",
    )
    parser.add_argument("--origin", default="DFW")
    parser.add_argument("--destination", default="BOS")
    parser.add_argument(
        "--model",
        default=None,
        help="Override OLLAMA_MODEL for this run (optional).",
    )
    parser.add_argument(
        "--out-dir",
        default=str(_STANDALONE_ROOT.parent / "experiment_data"),
        help="Directory for agent1_live.txt, agent2_reference.txt, run_manifest.json",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run Agent 2 after Agent 1 (avoids two simultaneous Ollama Cloud requests).",
    )
    args = parser.parse_args()
    flight_date = args.flight_date or date.today().isoformat()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    key_set = "yes" if hw_config.OLLAMA_API_KEY else "no"
    hw_config.log_info(
        f"smoke: OLLAMA_HOST={hw_config.OLLAMA_HOST} OLLAMA_MODEL={args.model or hw_config.OLLAMA_MODEL} "
        f"OLLAMA_CLOUD={hw_config.OLLAMA_CLOUD} API_KEY_set={key_set} "
        f"MCP_BASE_URL={hw_config.MCP_BASE_URL or '(in-process)'} "
        f"RAG_DATA_DIR={hw_config.RAG_DATA_DIR} HW_FLIGHT_DEBUG={hw_config.debug_verbose()} "
        f"MAX_TOOL_RESULT_CHARS={hw_config.MAX_TOOL_RESULT_CHARS} "
        f"RAG_HIT_CONTENT_CHARS={hw_config.RAG_HIT_CONTENT_CHARS} MAX_RAG_HITS={hw_config.MAX_RAG_HITS_IN_PROMPT} "
        f"OLLAMA_TIMEOUT_SEC={int(hw_config.OLLAMA_REQUEST_TIMEOUT)} sequential={args.sequential}"
    )
    hw_config.log_info(f"smoke: flight_date={flight_date} (override with --date YYYY-MM-DD)")

    ctx = FlightContext(
        carrier=args.carrier,
        flight_number=args.flight_number,
        flight_date=flight_date,
        origin=args.origin,
        destination=args.destination,
    )

    if args.sequential:
        print("Running Agents 1 then 2 (sequential)…", flush=True)
        out = run_agents_1_and_2_sequential(ctx, model=args.model)
    else:
        print("Running Agents 1 and 2 (parallel)…", flush=True)
        out = run_agents_1_and_2(ctx, model=args.model)

    (out_dir / "agent1_live.txt").write_text(out.get("agent1_live") or "", encoding="utf-8")
    (out_dir / "agent2_reference.txt").write_text(out.get("agent2_reference") or "", encoding="utf-8")

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "flight": {
            "carrier": ctx.carrier,
            "flight_number": ctx.flight_number,
            "flight_date": flight_date,
            "origin": ctx.origin,
            "destination": ctx.destination,
        },
        "model": args.model,
        "errors": out.get("errors") or [],
        "agent1_chars": len(out.get("agent1_live") or ""),
        "agent2_chars": len(out.get("agent2_reference") or ""),
    }
    (out_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote: {out_dir / 'agent1_live.txt'}", flush=True)
    print(f"Wrote: {out_dir / 'agent2_reference.txt'}", flush=True)
    print(f"Wrote: {out_dir / 'run_manifest.json'}", flush=True)
    if out.get("errors"):
        print("Errors:", out["errors"], flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
