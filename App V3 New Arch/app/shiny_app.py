# shiny_app.py
# Shiny for Python — flight input, workflow status, collapsible agent outputs.
# (Named shiny_app.py so `import app` resolves to the package, not a sibling app.py.)

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

# Project root on sys.path for `mcp_server` (the `app` package is app/, not app.py).
_ROOT = Path(__file__).resolve().parent.parent
_rs = str(_ROOT)
if _rs in sys.path:
    sys.path.remove(_rs)
sys.path.insert(0, _rs)

from shiny import App, reactive, render, ui
from shiny.reactive import Value, extended_task
from shiny.types import SilentException

from app.core import config
from app.agents.orchestrator import (
    FlightContext,
    run_agent_3,
    run_agent_4,
    run_agents_1_and_2,
)


def _parse_json_loose(s: str) -> Any | None:
    """Parse Agent 1 output: raw JSON or optional ```-fenced block."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    lines = s.splitlines()
    if len(lines) >= 2 and lines[0].strip().startswith("```"):
        body = lines[1:]
        while body and body[-1].strip() == "```":
            body = body[:-1]
        inner = "\n".join(body).strip()
        try:
            return json.loads(inner)
        except json.JSONDecodeError:
            return None
    return None


def _render_agent1_json(raw: str):
    """Pretty-print JSON for the Live data tab; fall back to monospace pre."""
    parsed = _parse_json_loose(raw)
    if parsed is not None:
        text = json.dumps(parsed, indent=2, ensure_ascii=False)
        return ui.tags.pre(text, class_="mb-0 small agent-json")
    disp = (raw or "").strip()
    if not disp:
        return ui.p("(empty)", class_="text-muted mb-0")
    return ui.tags.pre(disp, class_="mb-0 small agent-json")


def _format_errors_list(errs: list[Any] | None) -> str:
    if not errs:
        return "(no errors)"
    return "\n".join(str(x) for x in errs)


def _normalize_agent_markdown_text(raw: str) -> str:
    """
    Models often emit long runs of '=' as ASCII dividers. In proportional fonts those look uneven,
    and unbroken '=' strings overflow the panel. Map them to markdown that wraps and renders as rules.
    """
    if not raw:
        return raw
    out: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if len(stripped) >= 24 and re.fullmatch(r"=+", stripped):
            out.append("")
            out.append("---")
            continue
        line = re.sub(r"={8,}", " — ", line)
        out.append(line)
    return "\n".join(out)


app_ui = ui.page_fluid(
    ui.tags.style(
        """
        .agent-panel {
            font-size: 0.9rem;
            max-height: 420px;
            overflow: auto;
            padding: 0.5rem 0;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        .agent-panel hr {
            margin: 0.75rem 0;
            border: 0;
            border-top: 1px solid #dee2e6;
            max-width: 100%;
        }
        .agent-panel pre { white-space: pre-wrap; }
        .agent-json {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 0.85rem;
            line-height: 1.45;
        }
        .status-ok { color: #0a7; }
        .status-warn { color: #c60; }
        .workflow-panel {
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            padding: 0.75rem 1rem;
            margin-bottom: 1rem;
            background: #f8f9fa;
        }
        """
    ),
    ui.h2("Airspace Intelligence Agent"),
    ui.output_ui("config_warning"),
    ui.p(
        "Multi-agent workflow: live NAS/weather tools (Agent 1), FAA reference search (Agent 2), "
        "synthesis (Agent 3), and personalized advice (Agent 4). Ollama Cloud requires OLLAMA_API_KEY in .env."
    ),
    ui.layout_columns(
        ui.input_text("carrier", "Carrier (IATA)", value="AA"),
        ui.input_text("flight_number", "Flight number", value="849"),
        ui.input_date("flight_date", "Flight date", value=date.today()),
        ui.input_text("origin", "Origin (ICAO/IATA)", value="DFW"),
        ui.input_text("destination", "Destination", value="BOS"),
        col_widths=(2, 2, 2, 3, 3),
    ),
    ui.input_task_button(
        "go",
        "Run analysis",
        label_busy="Running workflow…",
        class_="btn-primary",
    ),
    ui.div(ui.output_ui("workflow_progress"), class_="workflow-panel"),
    ui.navset_tab(
        ui.nav_panel(
            "Final report (Agent 4)",
            ui.div(ui.output_ui("out_a4"), class_="agent-panel"),
        ),
        ui.nav_panel(
            "Synthesis (Agent 3)",
            ui.div(ui.output_ui("out_a3"), class_="agent-panel"),
        ),
        ui.nav_panel(
            "Reference (Agent 2)",
            ui.div(ui.output_ui("out_a2"), class_="agent-panel"),
        ),
        ui.nav_panel(
            "Live data (Agent 1)",
            ui.div(ui.output_ui("out_a1"), class_="agent-panel"),
        ),
        ui.nav_panel(
            "Errors / trace",
            ui.div(ui.output_ui("out_err"), class_="agent-panel"),
        ),
    ),
)


def server(input, output, session):
    workflow_step = Value("Idle — click Run analysis.")
    # Filled incrementally so tabs can render before the full workflow finishes.
    live_data_v = Value[str | None](None)
    reference_v = Value[str | None](None)
    synthesis_v = Value[str | None](None)
    report_v = Value[str | None](None)
    errors_v = Value[str | None](None)

    @ui.bind_task_button(button_id="go")
    @extended_task
    async def workflow_task(ws: Value[str], ctx: FlightContext) -> dict[str, Any]:
        live_data_v.set(None)
        reference_v.set(None)
        synthesis_v.set(None)
        report_v.set(None)
        errors_v.set(None)

        config.validate_ollama_cloud_credentials()
        ws.set(
            "Step 1 of 4 — Agents 1 & 2: live NAS/weather + FAA reference (running in parallel)…"
        )
        await asyncio.sleep(0.05)
        out = await asyncio.to_thread(run_agents_1_and_2, ctx, None)
        live_data_v.set(out.get("agent1_live") or "")
        reference_v.set(out.get("agent2_reference") or "")
        errors_v.set(_format_errors_list(out.get("errors")))

        ws.set("Step 2 of 4 — Agent 3: merging live data with FAA reference context…")
        await asyncio.sleep(0.05)
        await asyncio.to_thread(run_agent_3, out, None)
        synthesis_v.set(out.get("agent3_synthesis") or "")
        errors_v.set(_format_errors_list(out.get("errors")))

        ws.set("Step 3 of 4 — Agent 4: personalized flight report…")
        await asyncio.sleep(0.05)
        await asyncio.to_thread(run_agent_4, out, None)
        report_v.set(out.get("agent4_report") or "")
        errors_v.set(_format_errors_list(out.get("errors")))

        ws.set("Step 4 of 4 — Complete. Results are in the tabs below.")
        return out

    @reactive.effect
    @reactive.event(input.go)
    def _start_workflow():
        if input.go() == 0:
            return
        fd = input.flight_date()
        if isinstance(fd, date):
            flight_date_str = fd.isoformat()
        else:
            flight_date_str = (str(fd).strip() if fd is not None else "") or date.today().isoformat()
        ctx = FlightContext(
            carrier=input.carrier().strip() or "AA",
            flight_number=input.flight_number().strip() or "1",
            flight_date=flight_date_str,
            origin=input.origin().strip() or "DFW",
            destination=input.destination().strip() or "BOS",
        )
        workflow_task.invoke(workflow_step, ctx)

    @render.ui
    def config_warning():
        if config.OLLAMA_CLOUD and not config.OLLAMA_API_KEY:
            return ui.div(
                ui.p(
                    ui.strong("Configuration: "),
                    "Set OLLAMA_API_KEY in your .env for Ollama Cloud, or set OLLAMA_HOST to a local Ollama URL.",
                    class_="mb-0 small",
                ),
                class_="alert alert-warning py-2",
                role="alert",
            )
        return None

    @render.ui
    def error_banner():
        st = workflow_task.status()
        if st != "error":
            return None
        try:
            workflow_task.result()
        except BaseException as e:  # noqa: BLE001
            msg = str(e)
        else:
            msg = "Unknown error"
        return ui.div(
            ui.p(ui.strong("Workflow failed"), class_="text-danger mb-1"),
            ui.p(msg, class_="small mb-0"),
            class_="alert alert-danger",
            role="alert",
        )

    @render.ui
    def workflow_progress():
        st = workflow_task.status()
        label = workflow_step()

        if st == "initial":
            return ui.div(
                ui.p(label, class_="text-muted mb-1"),
                ui.p(
                    "The button shows a spinner while the workflow runs; steps update here.",
                    class_="small text-muted mb-0",
                ),
            )

        if st == "running":
            return ui.div(
                ui.div(
                    ui.tags.span(
                        class_="spinner-border spinner-border-sm me-2",
                        role="status",
                        aria_hidden="true",
                    ),
                    ui.span("In progress", class_="fw-semibold text-primary"),
                    class_="d-flex align-items-center mb-2",
                ),
                ui.p(label, class_="mb-0 small"),
            )

        if st == "success":
            return ui.div(
                ui.p(ui.strong("Done."), class_="status-ok mb-1"),
                ui.p(label, class_="small text-muted mb-0"),
            )

        if st == "error":
            try:
                workflow_task.result()
            except BaseException as e:  # noqa: BLE001
                msg = str(e)
            else:
                msg = "Unknown error"
            return ui.div(
                ui.p(ui.strong("Workflow failed."), class_="text-danger mb-1"),
                ui.p(msg, class_="small mb-0"),
            )

        # cancelled
        return ui.p("Cancelled.", class_="text-muted mb-0")

    def _render_agent_markdown(text: str):
        return ui.markdown(_normalize_agent_markdown_text(text or ""))

    @render.ui
    def out_a1():
        workflow_task.status()
        workflow_step()
        v = live_data_v()
        if v is None:
            st = workflow_task.status()
            if st == "running":
                return ui.p("Running Agents 1 & 2…", class_="text-muted mb-0")
            return ui.p("(not run yet)", class_="text-muted mb-0")
        return _render_agent1_json(v)

    @render.ui
    def out_a2():
        workflow_task.status()
        workflow_step()
        v = reference_v()
        if v is None:
            st = workflow_task.status()
            if st == "running":
                return ui.p("Running Agents 1 & 2…", class_="text-muted mb-0")
            return ui.p("(not run yet)", class_="text-muted mb-0")
        return _render_agent_markdown(v)

    @render.ui
    def out_a3():
        workflow_task.status()
        workflow_step()
        v = synthesis_v()
        if v is None:
            st = workflow_task.status()
            if st == "running":
                if live_data_v() is None:
                    return ui.p("Waiting for Agents 1 & 2…", class_="text-muted mb-0")
                return ui.p("Running Agent 3…", class_="text-muted mb-0")
            return ui.p("(not run yet)", class_="text-muted mb-0")
        return _render_agent_markdown(v)

    @render.ui
    def out_a4():
        workflow_task.status()
        workflow_step()
        v = report_v()
        if v is None:
            st = workflow_task.status()
            if st == "running":
                if synthesis_v() is None:
                    return ui.p("Waiting for earlier steps…", class_="text-muted mb-0")
                return ui.p("Running Agent 4…", class_="text-muted mb-0")
            return ui.p("(not run yet)", class_="text-muted mb-0")
        return _render_agent_markdown(v)

    @render.ui
    def out_err():
        workflow_task.status()
        workflow_step()
        ev = errors_v()
        if ev is not None:
            return _render_agent_markdown(ev)
        st = workflow_task.status()
        if st == "error":
            try:
                workflow_task.result()
            except SilentException:
                raise
            except Exception as e:  # noqa: BLE001
                return _render_agent_markdown(str(e))
        if st == "running":
            return ui.p("Errors will appear here as the run progresses.", class_="text-muted mb-0")
        return ui.p("(not run yet)", class_="text-muted mb-0")


app = App(app_ui, server)
