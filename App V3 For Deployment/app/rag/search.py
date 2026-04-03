# search.py
# BM25 keyword search over ingested FAA chunks (rank_bm25).

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from app.core.config import RAG_DATA_DIR

logger = logging.getLogger(__name__)

_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "is",
    "are",
    "be",
    "as",
    "at",
    "by",
    "that",
    "this",
    "it",
    "from",
}


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOP and len(w) > 1]


_INDEX: tuple[list[dict[str, Any]], BM25Okapi | None] | None = None
_AIRPORT_INDEX: dict[str, list[str]] | None = None


def _load_index() -> tuple[list[dict[str, Any]], BM25Okapi | None]:
    global _INDEX  # noqa: PLW0603 — small process-local cache
    if _INDEX is not None:
        return _INDEX
    path = Path(RAG_DATA_DIR) / "index" / "chunks.json"
    if not path.is_file():
        _INDEX = ([], None)
        return _INDEX
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load RAG index at %s: %s — search disabled.", path, e)
        _INDEX = ([], None)
        return _INDEX
    if not isinstance(raw, list):
        _INDEX = ([], None)
        return _INDEX
    rows = [c for c in raw if isinstance(c, dict)]
    corpus = [str(c.get("content", "") or "") for c in rows]
    tokenized = [_tokenize(c) for c in corpus]
    if not any(tokenized):
        _INDEX = (rows, None)
        return _INDEX
    bm25 = BM25Okapi(tokenized)
    _INDEX = (rows, bm25)
    return _INDEX


def _load_airport_index() -> dict[str, list[str]]:
    """LID / NAVAID string -> chunk_ids (from ingest); empty dict if missing."""
    global _AIRPORT_INDEX  # noqa: PLW0603
    if _AIRPORT_INDEX is not None:
        return _AIRPORT_INDEX
    path = Path(RAG_DATA_DIR) / "index" / "airport_index.json"
    if not path.is_file():
        _AIRPORT_INDEX = {}
        return _AIRPORT_INDEX
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load airport index at %s: %s — hybrid lookup disabled.", path, e)
        _AIRPORT_INDEX = {}
        return _AIRPORT_INDEX
    if not isinstance(raw, dict):
        _AIRPORT_INDEX = {}
        return _AIRPORT_INDEX
    _AIRPORT_INDEX = {str(k).upper(): v for k, v in raw.items() if isinstance(v, list)}
    return _AIRPORT_INDEX


def _airport_code_variants(code: str) -> list[str]:
    """Try US ICAO Kxxx -> xxx so KJFK matches AFD LID JFK."""
    c = (code or "").strip().upper()
    if not c:
        return []
    out: list[str] = [c]
    if len(c) == 4 and c.startswith("K") and c[1:].isalpha():
        out.append(c[1:])
    return list(dict.fromkeys(out))


def lookup_airport_chunks(code: str) -> list[dict[str, Any]]:
    """
    Hybrid retrieval: exact AFD rows by airport LID or NAVAID name (not BM25).

    Uses ``index/airport_index.json`` from ingest. Tries ``K``-prefixed ICAO
    as an alias for the 3-letter LID when applicable.
    """
    variants = _airport_code_variants(code)
    if not variants:
        return []

    ap_idx = _load_airport_index()
    if not ap_idx:
        return []

    chunk_ids: list[str] = []
    for v in variants:
        for cid in ap_idx.get(v, []):
            if cid not in chunk_ids:
                chunk_ids.append(cid)

    if not chunk_ids:
        return []

    chunk_ids.sort()

    rows, _ = _load_index()
    by_id = {str(c.get("chunk_id", "")): c for c in rows if c.get("chunk_id")}
    out: list[dict[str, Any]] = []
    for cid in chunk_ids:
        row = by_id.get(cid)
        if not row:
            continue
        r = dict(row)
        r["score"] = 1.0
        r["retrieval"] = "structured"
        out.append(r)
    return out


def search_reference(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Search the FAA document index by keyword relevance (BM25).

    Returns
    -------
    list[dict]
        Ranked chunks: source, section, content, score (when index exists).
    """
    rows, bm25 = _load_index()
    if not rows or bm25 is None:
        return []

    q = _tokenize(query)
    if not q:
        return []

    scores = bm25.get_scores(q)
    # Tie-break: descending score, then ascending chunk_id (stable vs corpus row order).
    ranked = sorted(
        range(len(scores)),
        key=lambda i: (
            -float(scores[i]),
            str(rows[i].get("chunk_id", "") or f"__row_{i}__"),
        ),
    )[:top_k]
    out: list[dict[str, Any]] = []
    for i in ranked:
        r = dict(rows[i])
        r["score"] = float(scores[i])
        out.append(r)
    return out


def format_reference_hits(hits: list[dict[str, Any]]) -> str:
    """Plain text block for prompts."""
    lines: list[str] = []
    for h in hits:
        how = "structured (airport index)" if h.get("retrieval") == "structured" else "bm25"
        lines.append(
            f"---\nretrieval: {how}\nsource: {h.get('source')}\nsection: {h.get('section')}\n"
            f"score: {h.get('score', 0):.4f}\n{h.get('content', '')[:6000]}\n"
        )
    return "\n".join(lines)
