# tsa_wait_times.py
# MyTSA confirmed wait times (best-effort).

from __future__ import annotations

import json

import requests

MYTSA_URL = "https://apps.tsa.dhs.gov/MyTSAWebService/GetConfirmedWaitTimes.ashx"
USER_AGENT = "Agentic-Flight-Report/3.0 (MyTSA reader)"


def get_tsa_wait_times(airport_code: str) -> str:
    """Security wait times for a US airport (e.g. DFW, LAX — typically 3-letter code)."""
    code = (airport_code or "").strip().upper()
    params = {"ap": code, "output": "json"}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,*/*"}
    try:
        r = requests.get(MYTSA_URL, params=params, headers=headers, timeout=20)
        payload = {
            "source": "MyTSA",
            "airport": code,
            "url": r.url,
            "http_status": r.status_code,
        }
        try:
            payload["data"] = r.json()
        except Exception:  # noqa: BLE001
            payload["raw_text"] = (r.text or "")[:8000]
        return json.dumps(payload, indent=2)
    except Exception as e:  # noqa: BLE001
        return json.dumps(
            {
                "source": "MyTSA",
                "airport": code,
                "error": str(e),
                "note": "MyTSA may be unavailable; continue without checkpoint wait data.",
            },
            indent=2,
        )
