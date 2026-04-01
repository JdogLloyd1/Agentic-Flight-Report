# faa_tfr.py
# FAA Temporary Flight Restrictions — best-effort fetch from public TFR pages.

from __future__ import annotations

import json
import re
from typing import Any

import requests

TFR_LIST_URL = "https://tfr.faa.gov/tfr2/list.html"
USER_AGENT = "Agentic-Flight-Report/3.0 (FAA TFR reader)"


def get_active_tfrs() -> str:
    """
    Fetch TFR list HTML and extract link samples. The FAA site is HTML-first;
    this is not a full NOTAM geometry parser.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,*/*"}
    try:
        r = requests.get(TFR_LIST_URL, headers=headers, timeout=45)
        r.raise_for_status()
        html = r.text
    except Exception as e:  # noqa: BLE001
        return json.dumps(
            {
                "source": "FAA TFR",
                "url": TFR_LIST_URL,
                "error": str(e),
                "note": "TFR feed may be unavailable; continue analysis without TFR detail.",
            },
            indent=2,
        )

    pairs = re.findall(
        r'href="([^"]+save_pages[^"]*)"[^>]*>([^<]{1,300})',
        html,
        flags=re.IGNORECASE,
    )
    items: list[dict[str, Any]] = [
        {"href": h[:500], "text": t.strip()[:500]} for h, t in pairs[:80]
    ]
    notam_ids = re.findall(r"\b([0-9]{1,4}/[0-9]{2})\b", html)[:40]

    payload: dict[str, Any] = {
        "source": "FAA TFR (list page)",
        "url": TFR_LIST_URL,
        "http_status": r.status_code,
        "extracted_links_sample": items,
        "notam_like_ids_sample": list(dict.fromkeys(notam_ids))[:25],
        "note": "Structured NOTAM/TFR geometry is not parsed here; use for awareness only.",
    }
    return json.dumps(payload, indent=2)
