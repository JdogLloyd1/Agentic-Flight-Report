# reference_analyst.py
# Agent 2 — BM25 RAG over FAA docs, then interpretive analyst pass.

from __future__ import annotations

from app.core import ollama_client
from app.rag.search import format_reference_hits, lookup_airport_chunks, search_reference

ROLE = """You are Agent 2: Reference Analyst for FAA procedures and airport context.

You receive (1) structured AFD index rows for origin/destination airport identifiers when available,
and (2) BM25 keyword excerpts from FAA Order 7110.65 and other indexed PDFs.
Synthesize the most relevant material for the flight: ground delay and ground stop concepts, weather-related
ATC considerations, and any airport-specific notes that apply to the origin or destination.

Output:
- A short bullet list of the most relevant procedural ideas (cite source filenames in parentheses).
- If excerpts are empty or weak, say so and list what topics would have helped.
"""


def _default_queries(carrier: str, origin: str, destination: str) -> list[str]:
    """carrier, origin, destination should already be normalized (strip + upper)."""
    return [
        f"{origin} ground delay program ground stop",
        f"{destination} IFR runway approach",
        "convective weather SIGMET ATC traffic management",
        "ground delay program GDP metering",
        f"{carrier} hub delay operations",
    ]


def _merge_sort_key(h: dict) -> tuple[int, float, str]:
    """Structured airport rows first, then higher BM25 score, then chunk_id."""
    tier = 0 if h.get("retrieval") == "structured" else 1
    return (tier, -float(h.get("score", 0.0)), str(h.get("chunk_id", "")))


def run_reference_analyst(
    carrier: str,
    flight_number: str,
    flight_date: str,
    origin: str,
    destination: str,
    model: str | None = None,
    extra_queries: list[str] | None = None,
) -> str:
    """Retrieve hybrid RAG chunks (structured airport index + BM25), then run the analyst LLM."""
    carrier_n = carrier.strip().upper()
    o = origin.strip().upper()
    d = destination.strip().upper()

    by_id: dict[str, dict] = {}
    for ap in (o, d):
        if len(ap) < 2:
            continue
        for h in lookup_airport_chunks(ap):
            cid = str(h.get("chunk_id", ""))
            if not cid or cid in by_id:
                continue
            r = dict(h)
            r["score"] = 1.0
            r["retrieval"] = "structured"
            by_id[cid] = r

    queries = list(extra_queries or []) + _default_queries(carrier_n, o, d)
    for q in queries:
        for h in search_reference(q, top_k=4):
            cid = str(h.get("chunk_id", ""))
            if not cid:
                continue
            sc = float(h.get("score", 0.0))
            if cid in by_id and by_id[cid].get("retrieval") == "structured":
                continue
            if cid not in by_id:
                nh = dict(h)
                nh["retrieval"] = "bm25"
                by_id[cid] = nh
            elif sc > float(by_id[cid].get("score", 0.0)):
                nh = dict(h)
                nh["retrieval"] = "bm25"
                by_id[cid] = nh

    merged = sorted(by_id.values(), key=_merge_sort_key)
    block = format_reference_hits(merged[:20])
    task = (
        f"Flight: {carrier} {flight_number} on {flight_date} from {origin} to {destination}.\n\n"
        f"Reference excerpts (airport index + BM25):\n{block if block.strip() else '(No index — run: python -m app.rag.ingest from App V3 New Arch; place PDFs and/or airport_facilities/*.xml under app/rag/data.)'}"
    )
    return ollama_client.agent_run(ROLE, task, tools=None, model=model)
