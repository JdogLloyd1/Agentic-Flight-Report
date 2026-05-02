# orchestrator.py — Agents 1–4 coordination (homework copy).
# Derived from App V3 Local Run/app/agents/orchestrator.py.

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from hw_flight.agents import airspace_synthesizer
from hw_flight.agents import data_collector
from hw_flight.agents import flight_advisor
from hw_flight.agents import reference_analyst
from hw_flight.core import config


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

    config.log_info(
        f"run_agents_1_and_2: start flight={ctx.carrier}{ctx.flight_number} "
        f"{ctx.flight_date} {ctx.origin}->{ctx.destination} model={model!r}"
    )
    t0 = time.perf_counter()

    with ThreadPoolExecutor(max_workers=2) as ex:
        config.log_info("run_agents_1_and_2: submitting Agent 1 (data_collector) and Agent 2 (reference_analyst)")
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
        config.log_info("run_agents_1_and_2: waiting on Agent 1 result()…")
        try:
            out["agent1_live"] = f1.result()
            config.log_info(
                f"run_agents_1_and_2: Agent 1 finished ok chars={len(out['agent1_live'] or '')} "
                f"elapsed_s={time.perf_counter() - t0:.2f}"
            )
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"agent1: {e}")
            out["agent1_live"] = ""
            config.log_info(f"run_agents_1_and_2: Agent 1 FAILED: {e!r}")
        config.log_info("run_agents_1_and_2: waiting on Agent 2 result()…")
        try:
            out["agent2_reference"] = f2.result()
            config.log_info(
                f"run_agents_1_and_2: Agent 2 finished ok chars={len(out['agent2_reference'] or '')} "
                f"elapsed_s={time.perf_counter() - t0:.2f}"
            )
        except Exception as e:  # noqa: BLE001
            out["errors"].append(f"agent2: {e}")
            out["agent2_reference"] = ""
            config.log_info(f"run_agents_1_and_2: Agent 2 FAILED: {e!r}")

    config.log_info(f"run_agents_1_and_2: done total_elapsed_s={time.perf_counter() - t0:.2f}")
    return out


def run_agents_1_and_2_sequential(
    ctx: FlightContext,
    model: str | None = None,
) -> dict[str, Any]:
    """Same as run_agents_1_and_2 but Agent 2 runs after Agent 1 finishes (one Ollama call at a time)."""
    out = _empty_workflow_result(ctx)
    task1 = _data_collector_task(ctx)
    config.log_info(
        f"run_agents_1_and_2_sequential: flight={ctx.carrier}{ctx.flight_number} "
        f"{ctx.flight_date} {ctx.origin}->{ctx.destination} model={model!r}"
    )
    t0 = time.perf_counter()
    config.log_info("sequential: starting Agent 1 (data_collector)")
    try:
        out["agent1_live"] = data_collector.run_data_collector(task1, model)
        config.log_info(
            f"sequential: Agent 1 ok chars={len(out['agent1_live'] or '')} "
            f"elapsed_s={time.perf_counter() - t0:.2f}"
        )
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"agent1: {e}")
        out["agent1_live"] = ""
        config.log_info(f"sequential: Agent 1 FAILED: {e!r}")
    config.log_info("sequential: starting Agent 2 (reference_analyst)")
    try:
        out["agent2_reference"] = reference_analyst.run_reference_analyst(
            ctx.carrier,
            ctx.flight_number,
            ctx.flight_date,
            ctx.origin,
            ctx.destination,
            model,
        )
        config.log_info(
            f"sequential: Agent 2 ok chars={len(out['agent2_reference'] or '')} "
            f"elapsed_s={time.perf_counter() - t0:.2f}"
        )
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"agent2: {e}")
        out["agent2_reference"] = ""
        config.log_info(f"sequential: Agent 2 FAILED: {e!r}")
    config.log_info(f"run_agents_1_and_2_sequential: done total_elapsed_s={time.perf_counter() - t0:.2f}")
    return out


def run_agent_3(
    out: dict[str, Any],
    model: str | None = None,
    role: str | None = None,
) -> None:
    """Agent 3 — airspace synthesis; mutates out."""
    try:
        out["agent3_synthesis"] = airspace_synthesizer.run_airspace_synthesizer(
            out["agent1_live"] or "",
            out["agent2_reference"] or "",
            model=model,
            role=role,
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
    agent3_role: str | None = None,
) -> dict[str, Any]:
    """
    Run Agents 1 and 2 in parallel, then Agent 3, then Agent 4.

    Returns intermediate outputs for debugging and UI panels.
    """
    out = run_agents_1_and_2(ctx, model=model)
    run_agent_3(out, model=model, role=agent3_role)
    run_agent_4(out, model=model)
    return out
