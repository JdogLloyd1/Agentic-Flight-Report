# shiny_app.py
# Shiny for Python — flight input, workflow status, collapsible agent outputs.
# (Named shiny_app.py so `import app` resolves to the package, not a sibling app.py.)

from __future__ import annotations

import asyncio
import sys
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

app_ui = ui.page_fluid(
    ui.tags.style(
        """
        .agent-panel pre { white-space: pre-wrap; font-size: 0.9rem; max-height: 420px; overflow: auto; }
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
        ui.input_text("flight_date", "Date (YYYY-MM-DD)", value="2026-03-31"),
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
            ui.div(ui.output_text_verbatim("out_a4"), class_="agent-panel"),
        ),
        ui.nav_panel(
            "Live data (Agent 1)",
            ui.div(ui.output_text_verbatim("out_a1"), class_="agent-panel"),
        ),
        ui.nav_panel(
            "Reference (Agent 2)",
            ui.div(ui.output_text_verbatim("out_a2"), class_="agent-panel"),
        ),
        ui.nav_panel(
            "Synthesis (Agent 3)",
            ui.div(ui.output_text_verbatim("out_a3"), class_="agent-panel"),
        ),
        ui.nav_panel(
            "Errors / trace",
            ui.div(ui.output_text_verbatim("out_err"), class_="agent-panel"),
        ),
    ),
)


def server(input, output, session):
    workflow_step = Value("Idle — click Run analysis.")

    @ui.bind_task_button(button_id="go")
    @extended_task
    async def workflow_task(ws: Value[str], ctx: FlightContext) -> dict[str, Any]:
        config.validate_ollama_cloud_credentials()
        ws.set(
            "Step 1 of 4 — Agents 1 & 2: live NAS/weather + FAA reference (running in parallel)…"
        )
        await asyncio.sleep(0.05)
        out = await asyncio.to_thread(run_agents_1_and_2, ctx, None)
        ws.set("Step 2 of 4 — Agent 3: merging live data with FAA reference context…")
        await asyncio.sleep(0.05)
        await asyncio.to_thread(run_agent_3, out, None)
        ws.set("Step 3 of 4 — Agent 4: personalized flight report…")
        await asyncio.sleep(0.05)
        await asyncio.to_thread(run_agent_4, out, None)
        ws.set("Step 4 of 4 — Complete. Results are in the tabs below.")
        return out

    @reactive.effect
    @reactive.event(input.go)
    def _start_workflow():
        if input.go() == 0:
            return
        ctx = FlightContext(
            carrier=input.carrier().strip() or "AA",
            flight_number=input.flight_number().strip() or "1",
            flight_date=input.flight_date().strip() or "2026-03-31",
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

    def _safe_block(key: str) -> str:
        st = workflow_task.status()
        if st == "error":
            try:
                workflow_task.result()
            except BaseException as e:  # noqa: BLE001
                return str(e)
            return ""
        try:
            wf = workflow_task.result()
        except SilentException:
            raise
        except Exception:
            return ""
        return str(wf.get(key) or "")

    @render.text
    def out_a1():
        return _safe_block("agent1_live")

    @render.text
    def out_a2():
        return _safe_block("agent2_reference")

    @render.text
    def out_a3():
        return _safe_block("agent3_synthesis")

    @render.text
    def out_a4():
        return _safe_block("agent4_report")

    @render.text
    def out_err():
        try:
            wf = workflow_task.result()
        except SilentException:
            raise
        except Exception as e:  # noqa: BLE001
            return str(e)
        errs = wf.get("errors") or []
        return "\n".join(errs) if errs else "(no errors)"


app = App(app_ui, server)
