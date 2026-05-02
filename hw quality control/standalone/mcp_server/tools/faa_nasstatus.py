# faa_nasstatus.py
# FAA NAS Status feed (nasstatus.faa.gov) — HTTP fetch, XML parse, JSON for agents.

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any

import requests

NASSTATUS_AIRPORT_STATUS_URL = (
    "https://nasstatus.faa.gov/api/airport-status-information"
)

USER_AGENT = "Agentic-Flight-Report/3.0 (FAA NASSTATUS reader)"


def _element_to_obj(elem: ET.Element) -> Any:
    """Recursively convert an XML element to JSON-serializable data."""
    children = list(elem)
    text = (elem.text or "").strip()
    if not children:
        return text if text else None
    out: dict[str, Any] = {}
    for child in children:
        tag = child.tag
        val = _element_to_obj(child)
        if tag in out:
            if not isinstance(out[tag], list):
                out[tag] = [out[tag]]
            out[tag].append(val)
        else:
            out[tag] = val
    if text:
        out["_text"] = text
    return out


def fetch_nasstatus_airport_status(
    url: str | None = None,
    include_parsed_json: bool = True,
) -> str:
    """
    Download the FAA NAS Status airport-status-information XML feed and return JSON text.
    """
    endpoint = (url or NASSTATUS_AIRPORT_STATUS_URL).strip()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/xml, text/xml, */*"}
    r = requests.get(endpoint, headers=headers, timeout=60)
    r.raise_for_status()
    raw_xml = r.text

    root = ET.fromstring(raw_xml)
    update_el = root.find("Update_Time")
    update_time = (update_el.text or "").strip() if update_el is not None else ""

    payload: dict[str, Any] = {
        "source": "FAA NASSTATUS",
        "api": "airport-status-information",
        "url": endpoint,
        "http_status": r.status_code,
        "update_time": update_time,
    }

    if include_parsed_json:
        inner: dict[str, Any] = {}
        for child in root:
            if child.tag in ("Update_Time", "Dtd_File"):
                inner[child.tag] = (child.text or "").strip()
            elif child.tag == "Delay_type":
                delay_types = inner.setdefault("Delay_types", [])
                delay_types.append(_element_to_obj(child))
            else:
                inner[child.tag] = _element_to_obj(child)
        payload["parsed"] = inner
    else:
        payload["raw_xml"] = raw_xml[:200000]

    return json.dumps(payload, indent=2)
