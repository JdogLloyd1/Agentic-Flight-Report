# opensky.py
# OpenSky Network — live ADS-B state vectors (anonymous or OAuth2).

from __future__ import annotations

import json
import os
from typing import Any

import requests

OPEN_SKY_STATES = "https://opensky-network.org/api/states/all"
USER_AGENT = "Agentic-Flight-Report/3.0 (OpenSky academic use)"


def _oauth_token() -> str | None:
    cid = os.environ.get("OPENSKY_CLIENT_ID")
    csec = os.environ.get("OPENSKY_CLIENT_SECRET")
    if not cid or not csec:
        return None
    try:
        r = requests.post(
            "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": cid,
                "client_secret": csec,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception:  # noqa: BLE001
        return None


def get_aircraft_states(
    icao24: str | None = None,
    bounding_box: dict[str, float] | None = None,
) -> str:
    """
    Live state vectors from OpenSky. Optional filters: icao24 hex, or lamin/lomin/lamax/lomax.
    """
    headers = {"User-Agent": USER_AGENT}
    token = _oauth_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params: dict[str, Any] = {}
    if icao24:
        params["icao24"] = icao24.strip().lower()
    if bounding_box:
        bb = bounding_box
        for k in ("lamin", "lomin", "lamax", "lomax"):
            if k in bb:
                params[k] = bb[k]

    try:
        r = requests.get(OPEN_SKY_STATES, params=params, headers=headers, timeout=45)
        payload: dict[str, Any] = {
            "source": "OpenSky Network",
            "url": r.url,
            "http_status": r.status_code,
            "authenticated": bool(token),
        }
        r.raise_for_status()
        payload["data"] = r.json()
        return json.dumps(payload, indent=2)
    except Exception as e:  # noqa: BLE001
        return json.dumps(
            {
                "source": "OpenSky Network",
                "error": str(e),
                "note": "OpenSky may block some cloud IPs; continue without live tracks if unavailable.",
            },
            indent=2,
        )
