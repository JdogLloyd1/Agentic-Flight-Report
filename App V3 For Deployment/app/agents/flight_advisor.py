# flight_advisor.py
# Agent 4 — personalized traveler-facing risk summary and recommendations.

from __future__ import annotations

from app.core import ollama_client

ROLE = """You are Agent 4: Flight Advisor for passengers.

Given the network summary and the user's specific flight details, produce:
- A plain-language risk level: low / moderate / high (with one sentence rationale)
- Key risk drivers (weather, congestion, ATC programs, airport-specific)
- Practical recommendations (arrive early, check alternate flights, rebooking, etc.)
- Uncertainty and disclaimer: you are not an official FAA/airline source; data may be incomplete.

Keep the tone calm, specific, and actionable."""


def run_flight_advisor(
    network_summary: str,
    carrier: str,
    flight_number: str,
    flight_date: str,
    origin: str,
    destination: str,
    model: str | None = None,
) -> str:
    task = (
        f"Flight: {carrier} {flight_number} on {flight_date}\n"
        f"Route: {origin} → {destination}\n\n"
        "=== NETWORK SUMMARY (Agent 3) ===\n"
        f"{network_summary}\n"
    )
    return ollama_client.agent_run(ROLE, task, tools=None, model=model)
