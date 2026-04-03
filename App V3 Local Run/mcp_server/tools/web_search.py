# web_search.py
# url_query and DuckDuckGo instant answer — general web retrieval.

from __future__ import annotations

import json
import re
from typing import Any

import requests

USER_AGENT_PAGE = "Mozilla/5.0 (compatible; Agentic-Flight-Report/3.0)"
USER_AGENT_API = "Agentic-Flight-Report/3.0 (DuckDuckGo)"


def url_query(url: str, max_chars: int = 20000) -> str:
    """Fetch a URL and return cleaned text (HTML stripped) as JSON for the model."""
    try:
        max_chars_int = int(max_chars)
    except (TypeError, ValueError):
        max_chars_int = 20000
    u = (url or "").strip()
    if not u:
        return json.dumps({"source": "url_fetch", "error": "empty_url"})
    try:
        response = requests.get(
            u, timeout=20, headers={"User-Agent": USER_AGENT_PAGE}
        )
        response.raise_for_status()
    except Exception as e:  # noqa: BLE001
        return json.dumps(
            {
                "source": "url_fetch",
                "url": u,
                "error": str(e),
                "note": "HTTP fetch failed; continue without this page.",
            },
            indent=2,
        )

    html = response.text
    text = re.sub(r"(?is)<script.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return json.dumps(
            {
                "source": "url_fetch",
                "url": u,
                "http_status": response.status_code,
                "note": "No readable text after HTML strip.",
            },
            indent=2,
        )
    payload: dict[str, Any] = {
        "source": "url_fetch",
        "url": u,
        "http_status": response.status_code,
        "text": text[:max_chars_int],
    }
    return json.dumps(payload, indent=2)


def web_search_general(query: str, max_results: int = 5) -> str:
    """DuckDuckGo Instant Answer API — summarized pointers (not full web index)."""
    try:
        max_results_int = int(max_results)
    except (TypeError, ValueError):
        max_results_int = 5
    q = (query or "").strip()
    if not q:
        return json.dumps({"source": "DuckDuckGo", "error": "empty_query"})
    params = {"q": q, "format": "json", "no_redirect": 1, "no_html": 1}
    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params=params,
            timeout=15,
            headers={"User-Agent": USER_AGENT_API},
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:  # noqa: BLE001
        return json.dumps(
            {
                "source": "DuckDuckGo",
                "query": q,
                "error": str(e),
                "note": "Instant Answer API request failed.",
            },
            indent=2,
        )

    pieces: list[str] = []
    abstract = data.get("AbstractText")
    if abstract:
        pieces.append(f"Abstract: {abstract}")
    heading = data.get("Heading")
    if heading:
        pieces.append(f"Heading: {heading}")
    related = data.get("RelatedTopics", [])[:max_results_int]
    for item in related:
        if isinstance(item, dict) and item.get("Text"):
            t = item.get("Text", "")
            u_item = item.get("FirstURL", "")
            pieces.append(f"- {t} (URL: {u_item})")
    if not pieces:
        return json.dumps(
            {
                "source": "DuckDuckGo",
                "query": q,
                "note": "No Instant Answer results for this query.",
            },
            indent=2,
        )
    payload: dict[str, Any] = {
        "source": "DuckDuckGo",
        "query": q,
        "summary_lines": pieces,
    }
    return json.dumps(payload, indent=2)
