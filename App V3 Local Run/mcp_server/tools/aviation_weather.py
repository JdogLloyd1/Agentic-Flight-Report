# aviation_weather.py
# aviationweather.gov Data API — METAR, TAF, SIGMET, G-AIRMET, PIREP.

from __future__ import annotations

import json
from typing import Any

import requests

# Official Data API base (see https://aviationweather.gov/data/api/)
AWC_API = "https://aviationweather.gov/api/data"
USER_AGENT = "Agentic-Flight-Report/3.0 (AWC API; contact via repo maintainer)"


def _get_json(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{AWC_API.rstrip('/')}/{path.lstrip('/')}"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    r = requests.get(url, params=params or {}, headers=headers, timeout=45)
    out: dict[str, Any] = {
        "source": "aviationweather.gov",
        "url": r.url,
        "http_status": r.status_code,
    }
    if r.status_code == 204 or not (r.text or "").strip():
        out["data"] = None
        out["note"] = "No report returned (empty or 204). Station or time window may have no data."
        return out
    try:
        r.raise_for_status()
        out["data"] = r.json()
    except Exception as e:  # noqa: BLE001 — return structured error for the model
        out["error"] = str(e)
        out["text_snippet"] = (r.text or "")[:4000]
    return out


def get_metar(station_id: str, hours_back: int = 1) -> str:
    """Current METAR observations for an ICAO station."""
    sid = (station_id or "").strip().upper()
    params = {"ids": sid, "format": "json", "hours": max(1, int(hours_back))}
    return json.dumps(_get_json("metar", params), indent=2)


def get_taf(station_id: str) -> str:
    """Terminal aerodrome forecast for an ICAO station."""
    sid = (station_id or "").strip().upper()
    params = {"ids": sid, "format": "json"}
    return json.dumps(_get_json("taf", params), indent=2)


def get_sigmets(hazard_type: str | None = None) -> str:
    """Active SIGMETs (optional filter: convective, turbulence, icing)."""
    params: dict[str, Any] = {"format": "json"}
    if hazard_type:
        params["hazard"] = hazard_type.strip().lower()
    return json.dumps(_get_json("sigmet", params), indent=2)


def get_gairmets(hazard_type: str | None = None) -> str:
    """Active G-AIRMETs (optional hazard filter)."""
    params: dict[str, Any] = {"format": "json"}
    if hazard_type:
        params["hazard"] = hazard_type.strip().lower()
    return json.dumps(_get_json("gairmet", params), indent=2)


def get_pireps(station_id: str | None = None, distance_nm: int = 100) -> str:
    """Recent PIREPs, optionally near a station within distance_nm."""
    params: dict[str, Any] = {"format": "json", "distance": max(1, int(distance_nm))}
    if station_id:
        params["id"] = station_id.strip().upper()
    return json.dumps(_get_json("pirep", params), indent=2)
