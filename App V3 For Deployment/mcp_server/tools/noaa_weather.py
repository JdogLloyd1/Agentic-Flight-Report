# noaa_weather.py
# api.weather.gov — active weather alerts.

from __future__ import annotations

import json
from typing import Any

import requests

NWS_ALERTS = "https://api.weather.gov/alerts/active"
USER_AGENT = "Agentic-Flight-Report/3.0 (NWS API; academic use)"


def get_weather_alerts(area: str | None = None, severity: str | None = None) -> str:
    """Active NWS weather alerts; optional state/area and severity filter."""
    params: dict[str, Any] = {}
    if area:
        # NWS accepts area (state) as query param in some deployments; also try zone if needed
        params["area"] = area.strip().upper()
    if severity:
        params["severity"] = severity.strip().lower()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json, application/json",
    }
    r = requests.get(NWS_ALERTS, params=params, headers=headers, timeout=45)
    payload: dict[str, Any] = {
        "source": "api.weather.gov",
        "url": r.url,
        "http_status": r.status_code,
    }
    try:
        r.raise_for_status()
        payload["data"] = r.json()
    except Exception as e:  # noqa: BLE001
        payload["error"] = str(e)
        payload["text_snippet"] = (r.text or "")[:4000]
    return json.dumps(payload, indent=2)
