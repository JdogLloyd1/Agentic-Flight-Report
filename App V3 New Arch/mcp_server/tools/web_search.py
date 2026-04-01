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
    """Fetch a URL and return cleaned text (HTML stripped)."""
    try:
        max_chars_int = int(max_chars)
    except (TypeError, ValueError):
        max_chars_int = 20000
    u = (url or "").strip()
    if not u:
        return json.dumps({"error": "empty url"})
    try:
        response = requests.get(
            u, timeout=20, headers={"User-Agent": USER_AGENT_PAGE}
        )
        response.raise_for_status()
    except Exception as e:  # noqa: BLE001
        return f"Error fetching URL {u}: {e}"

    html = response.text
    text = re.sub(r"(?is)<script.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return f"No readable text content found at {u}."
    return text[:max_chars_int]


def web_search_general(query: str, max_results: int = 5) -> str:
    """DuckDuckGo Instant Answer API — summarized pointers (not full web index)."""
    try:
        max_results_int = int(max_results)
    except (TypeError, ValueError):
        max_results_int = 5
    q = (query or "").strip()
    if not q:
        return json.dumps({"error": "empty query"})
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
        return f"Error performing web search for '{q}': {e}"

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
        return f"No results found for general search query: {q}"
    return "\n".join(pieces)
