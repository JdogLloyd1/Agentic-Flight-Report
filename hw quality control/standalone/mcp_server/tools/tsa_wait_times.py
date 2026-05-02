# tsa_wait_times.py
# TSA checkpoint wait times — legacy DHS MyTSA endpoint often redirects; optional proxy URL.

from __future__ import annotations

import json
from typing import Any

import requests

try:
    from app.core.config import TSA_WAIT_TIMES_PROXY_URL
except ImportError:
    import os

    TSA_WAIT_TIMES_PROXY_URL = (os.environ.get("TSA_WAIT_TIMES_PROXY_URL") or "").strip()

# Documented at https://www.dhs.gov/mytsa-api-documentation — may 302 to www.tsa.gov (HTML).
LEGACY_MYTSA_JSON = (
    "https://apps.tsa.dhs.gov/MyTSAWebService/GetConfirmedWaitTimes.ashx"
)
USER_AGENT = "Agentic-Flight-Report/3.0 (TSA wait times reader)"


def _fetch_proxy(airport_code: str) -> dict[str, Any] | None:
    if not TSA_WAIT_TIMES_PROXY_URL:
        return None
    url = TSA_WAIT_TIMES_PROXY_URL.format(
        airport_code=airport_code,
        code=airport_code,
    )
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,*/*"}
    r = requests.get(url, headers=headers, timeout=25)
    payload: dict[str, Any] = {
        "source": "TSA wait times (proxy)",
        "airport": airport_code,
        "url": r.url,
        "http_status": r.status_code,
    }
    try:
        r.raise_for_status()
        payload["data"] = r.json()
    except Exception as e:  # noqa: BLE001
        payload["error"] = str(e)
        payload["raw_text"] = (r.text or "")[:4000]
    return payload


def _fetch_legacy_json(airport_code: str) -> dict[str, Any]:
    """Call documented MyTSA JSON endpoint without following redirects."""
    params = {"ap": airport_code, "output": "json"}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,*/*"}
    r = requests.get(
        LEGACY_MYTSA_JSON,
        params=params,
        headers=headers,
        timeout=20,
        allow_redirects=False,
    )
    base: dict[str, Any] = {
        "source": "MyTSA (legacy DHS API)",
        "airport": airport_code,
        "requested_url": r.url,
        "http_status": r.status_code,
    }
    if r.is_redirect:
        loc = r.headers.get("Location") or ""
        base["legacy_api_status"] = "redirect"
        base["redirect_location"] = loc[:500]
        base["note"] = (
            "The documented MyTSA JSON endpoint returned an HTTP redirect instead of JSON. "
            "TSA has consolidated web properties; programmatic access may require the MyTSA mobile app "
            "or a self-hosted proxy. Set TSA_WAIT_TIMES_PROXY_URL in the server environment to a URL "
            "that returns JSON for this airport (see mcp_server/tools/tsa_wait_times.py). "
            "Reference: https://www.dhs.gov/mytsa-api-documentation"
        )
        return base

    if r.status_code != 200:
        base["legacy_api_status"] = "http_error"
        base["error"] = (r.text or "")[:2000]
        return base

    try:
        base["data"] = r.json()
    except Exception as e:  # noqa: BLE001
        base["legacy_api_status"] = "not_json"
        base["error"] = str(e)
        base["raw_text"] = (r.text or "")[:8000]
    else:
        base["legacy_api_status"] = "ok"
    return base


def get_tsa_wait_times(airport_code: str) -> str:
    """Security wait times for a US airport (e.g. DFW, LAX — typically 3-letter code)."""
    code = (airport_code or "").strip().upper()
    if not code:
        return json.dumps({"source": "MyTSA", "error": "empty_airport_code"})

    if TSA_WAIT_TIMES_PROXY_URL:
        proxy = _fetch_proxy(code)
        if proxy is not None:
            return json.dumps(proxy, indent=2)

    return json.dumps(_fetch_legacy_json(code), indent=2)
