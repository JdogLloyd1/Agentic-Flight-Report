# nasstatus_workflow.py
# Two-agent workflow: (1) NASSTATUS fetch via tool, (2) report + analysis from fetch output.
# Requires OLLAMA_API_KEY in repo .env for Ollama Cloud (see functions.py).

from __future__ import annotations

import os
import sys

# Ensure tool function resolves when this file is __main__
from faa_nasstatus_tool import (
    NASSTATUS_TOOL_METADATA,
    fetch_nasstatus_airport_status,
)
from functions import DEFAULT_MODEL, agent_run, load_env_file
from pathlib import Path

# Reload .env from repo root if needed (functions.py already loads parent .env)
load_env_file(Path(__file__).resolve().parent.parent / ".env")


ROLE_FETCH = """You are the NAS data agent. You MUST call the registered tool function \
fetch_nasstatus_airport_status exactly once (use default arguments: no url, include_parsed_json true). \
Do not write Python code, markdown fences, or placeholders. Do not describe what you would do—only \
invoke the tool so the system executes it."""


ROLE_ANALYST = """You are an aviation operations analyst. Given JSON or structured NAS Status \
data from the FAA feed, produce a clear report for dispatch or flight planning: \
(1) Executive summary of NAS constraints, (2) Notable airports and programs (GDP, ground stop, \
closures) with airport IDs, (3) Operational implications and risks, (4) Suggested monitoring \
or next checks. Use only the provided data; note if the feed is sparse or empty."""


def _is_valid_nas_json_payload(text: str) -> bool:
    """True if this looks like output from fetch_nasstatus_airport_status (not model hallucination)."""
    t = (text or "").strip()
    return "FAA NASSTATUS" in t and "airport-status-information" in t and (
        '"parsed"' in t or '"raw_xml"' in t
    )


def run_nasstatus_report_workflow(
    task: str | None = None,
    model: str | None = None,
) -> tuple[str, str]:
    """
    Run agent 1 (tool fetch) then agent 2 (report from fetch output).

    Returns
    -------
    tuple[str, str]
        (fetch_agent_output, analysis_text)
    """
    m = model or DEFAULT_MODEL
    fetch_task = task or (
        "Retrieve the latest FAA NAS airport status using the tool. "
        "Call fetch_nasstatus_airport_status with default parameters."
    )

    fetch_out = agent_run(
        role=ROLE_FETCH,
        task=fetch_task,
        tools=NASSTATUS_TOOL_METADATA,
        model=m,
    )

    # If the model did not actually execute the tool (weak tool adherence), fetch directly.
    if not _is_valid_nas_json_payload(str(fetch_out)):
        print(
            "Note: fetch agent did not return valid tool output; using direct API fetch.",
            file=sys.stderr,
        )
        fetch_out = fetch_nasstatus_airport_status()

    analysis_task = (
        "Here is the FAA NAS Status data (JSON from the fetch step). "
        "Write the report and analysis as instructed in your system role.\n\n"
        f"{fetch_out}"
    )

    report = agent_run(
        role=ROLE_ANALYST,
        task=analysis_task,
        tools=None,
        model=m,
    )
    return fetch_out, report


def main() -> None:
    if not os.environ.get("OLLAMA_API_KEY"):
        print(
            "Warning: OLLAMA_API_KEY not set. Set it in .env for Ollama Cloud, "
            "or run a local Ollama instance without a key.",
            file=sys.stderr,
        )
    fetch_json, report = run_nasstatus_report_workflow()
    print("=== Agent 1: fetch output (JSON string) ===\n")
    print(fetch_json[:4000] + ("...\n" if len(fetch_json) > 4000 else "\n"))
    print("=== Agent 2: report & analysis ===\n")
    print(report)


if __name__ == "__main__":
    main()
