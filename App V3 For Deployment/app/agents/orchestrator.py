# orchestrator.py
# Coordinates Agents 1–4; Agents 1 and 2 run in parallel.

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from app.agents import airspace_synthesizer
from app.agents import data_collector
from app.agents import flight_advisor
from app.agents import reference_analyst


@dataclass
class FlightContext:
    carrier: str
    flight_number: str
    flight_date: str
    origin: str
    destination: str


def _data_collector_task(ctx: FlightContext) -> str:
    return (
        f"Collect live operational data for this flight: {ctx.carrier} {ctx.flight_number} "
        f"on {ctx.flight_date} from {ctx.origin} to {ctx.destination}. "
        "Normalize origin and destination to ICAO (US: K + IATA when the user gives 3-letter codes, e.g. DFW→KDFW). "
        "Use those ICAO codes for all AWC tool calls; respond with the strict JSON schema from your system instructions only."
    )


def _empty_workflow_result(ctx: FlightContext) -> dict[str, Any]:
    return {
        "flight": ctx,
        "agent1_live": None,
        "agent2_reference": None,
        "agent3_synthesis": None,
        "agent4_report": None,
        "errors": [],
    }


def run_agents_1_and_2(
    ctx: FlightContext,
    model: str | None = None,
) -> dict[str, Any]:
    """Agents 1 and 2 in parallel; mutates and returns the same result dict."""
    out = _empty_workflow_result(ctx)
    task1 = _data_collector_task(ctx)

    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(data_collector.run_data_collector, task1, model)
        f2 = ex.submit(
            reference_analyst.run_reference_analyst,
            ctx.carrier,
            ctx.flight_number,
            ctx.flight_date,
            ctx.origin,
            ctx.destination,
            model,
        )
        try:
            out["agent1_live"] = f1.result()
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"agent1: {e}")
            out["agent1_live"] = ""
        try:
            out["agent2_reference"] = f2.result()
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"agent2: {e}")
            out["agent2_reference"] = ""

    return out


def run_agent_3(
    out: dict[str, Any],
    model: str | None = None,
) -> None:
    """Agent 3 — airspace synthesis; mutates out."""
    try:
        out["agent3_synthesis"] = airspace_synthesizer.run_airspace_synthesizer(
            out["agent1_live"] or "",
            out["agent2_reference"] or "",
            model=model,
        )
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"agent3: {e}")
        out["agent3_synthesis"] = ""


def run_agent_4(
    out: dict[str, Any],
    model: str | None = None,
) -> None:
    """Agent 4 — flight advisor; mutates out."""
    ctx = out["flight"]
    try:
        out["agent4_report"] = flight_advisor.run_flight_advisor(
            out["agent3_synthesis"] or "",
            ctx.carrier,
            ctx.flight_number,
            ctx.flight_date,
            ctx.origin,
            ctx.destination,
            model=model,
        )
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"agent4: {e}")
        out["agent4_report"] = ""


def run_workflow(
    ctx: FlightContext,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Run Agents 1 and 2 in parallel, then Agent 3, then Agent 4.

    Returns intermediate outputs for debugging and UI panels.
    """
    out = run_agents_1_and_2(ctx, model=model)
    run_agent_3(out, model=model)
    run_agent_4(out, model=model)
    return out
