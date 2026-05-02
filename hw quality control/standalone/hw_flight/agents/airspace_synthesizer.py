# airspace_synthesizer.py — Agent 3 (merge live JSON + reference text).
# Derived from App V3 Local Run/app/agents/airspace_synthesizer.py; adds optional `role` for experiments.

from __future__ import annotations

from hw_flight.core import ollama_client

ROLE = """You are Agent 3: Airspace Synthesizer.

Agent 1 may supply LIVE DATA as a single JSON object with keys including: airports (origin_icao, destination_icao), nas_status_faa, operational_weather_awc_nws, system_level_delays_cancellations, other_operational_factors, network_summary_hubs, data_gaps_and_limitations. Parse those fields when present; treat status fields as ground truth for whether data was retrieved.

Merge Live Data (Agent 1) with Reference Context (Agent 2). Clearly separate:
- what is live operational data vs
- what is background FAA reference material.

Produce a structured report with sections (use ## markdown headings and optional --- between sections).
Do not use long rows of "=" characters as dividers—they break HTML layout; use "---" on its own line instead.

1) NAS Status (FAA)
2) Current Operational Weather (AWC / NWS)
3) System-Level Delays and Cancellations (if inferable from data)
4) Other Operational Factors (NOTAMs/TFR awareness, TSA, airline/airport issues if present)
5) Network-Level Summary by Region and Hub — highlight top 3-5 impacted hubs if identifiable

Label live vs reference clearly (short tags in parentheses are fine). Be explicit when data is missing or uncertain."""


def run_airspace_synthesizer(
    live_data: str,
    reference_analysis: str,
    model: str | None = None,
    role: str | None = None,
) -> str:
    """Merge Agent 1 + Agent 2. Pass `role` to override the default Agent 3 system prompt (prompt A/B/C experiments)."""
    task = (
        "=== LIVE DATA (Agent 1) ===\n"
        f"{live_data}\n\n"
        "=== REFERENCE ANALYSIS (Agent 2) ===\n"
        f"{reference_analysis}\n"
    )
    system = role if role is not None else ROLE
    return ollama_client.agent_run(system, task, tools=None, model=model)
