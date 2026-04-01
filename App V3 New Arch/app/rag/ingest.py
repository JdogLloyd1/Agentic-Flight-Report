# ingest.py
# Build BM25 index: FAA PDF text (PyMuPDF) plus AFD airport index XML under airport_facilities/.

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from app.core.config import RAG_DATA_DIR


def _register_airport_code(index: dict[str, list[str]], code: str, chunk_id: str) -> None:
    """Map uppercase LID/NAVAID -> chunk_id(s) for hybrid lookup; dedupe per code."""
    c = (code or "").strip().upper()
    if len(c) < 2:
        return
    bucket = index.setdefault(c, [])
    if chunk_id not in bucket:
        bucket.append(chunk_id)


def _xml_text(el: ET.Element | None, tag: str) -> str:
    if el is None:
        return ""
    child = el.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _afd_xml_chunks(xml_path: Path, data_root: Path) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """
    Parse FAA d-TPP / AFD-style airport index XML (<airports><location><airport>...).
    One BM25 chunk per airport row so ICAO/LID/city/name queries can hit chart PDF pointers.

    Returns chunks plus a code -> chunk_id list map for hybrid structured retrieval.
    """
    tree = ET.parse(xml_path)
    root_el = tree.getroot()
    code_index: dict[str, list[str]] = {}
    if root_el.tag != "airports":
        return [], code_index

    try:
        rel_source = xml_path.relative_to(data_root).as_posix()
    except ValueError:
        rel_source = xml_path.name

    from_edate = (root_el.get("from_edate") or "").strip()
    to_edate = (root_el.get("to_edate") or "").strip()
    eff = ""
    if from_edate or to_edate:
        eff = f" (effective {from_edate} to {to_edate})" if to_edate else f" (from {from_edate})"

    chunks: list[dict[str, Any]] = []
    for loc in root_el.findall("location"):
        state = (loc.get("state") or "").strip()
        for ap in loc.findall("airport"):
            aptname = _xml_text(ap, "aptname")
            aptcity = _xml_text(ap, "aptcity")
            aptid = _xml_text(ap, "aptid")
            navidname = _xml_text(ap, "navidname")
            pdfs: list[str] = []
            pages = ap.find("pages")
            if pages is not None:
                for pdf_el in pages.findall("pdf"):
                    t = (pdf_el.text or "").strip()
                    if t:
                        pdfs.append(t)

            if not any((aptname, aptcity, aptid, navidname, pdfs)):
                continue

            parts: list[str] = []
            if state:
                parts.append(f"State/region: {state}")
            if aptname:
                parts.append(f"Airport name: {aptname}")
            if aptcity:
                parts.append(f"City or service area: {aptcity}")
            if aptid:
                parts.append(f"Airport identifier (LID): {aptid}")
            if navidname:
                parts.append(f"NAVAID index name: {navidname}")
            if pdfs:
                uniq = sorted(set(pdfs))
                parts.append("AFD chart PDF filename(s): " + ", ".join(uniq))
            parts.append(
                "FAA Airport/Facility Directory index entry"
                + eff
                + "; full text lives in the referenced PDF(s), not in this XML."
            )
            content = "\n".join(parts)
            if len(content) < 15:
                continue

            label = " / ".join(x for x in (state, aptid or navidname or aptname) if x)[:200]
            idx = len(chunks)
            chunk_id = f"{rel_source}:{idx}"
            chunks.append(
                {
                    "source": rel_source,
                    "section": label or "airport",
                    "content": content[:12000],
                    "chunk_id": chunk_id,
                    "kind": "afd_xml",
                }
            )
            if aptid:
                _register_airport_code(code_index, aptid, chunk_id)
            if navidname:
                _register_airport_code(code_index, navidname, chunk_id)
    return chunks, code_index


def _chunk_text(text: str, source: str) -> list[dict[str, Any]]:
    """Split long text into chunks; prefer lines that look like section headers."""
    lines = text.splitlines()
    chunks: list[dict[str, Any]] = []
    buf: list[str] = []
    section = "root"

    def flush() -> None:
        nonlocal buf, section
        body = "\n".join(buf).strip()
        if len(body) < 40:
            buf = []
            return
        chunks.append(
            {
                "source": source,
                "section": section,
                "content": body[:12000],
                "chunk_id": f"{source}:{len(chunks)}",
            }
        )
        buf = []

    header_re = re.compile(
        r"^(chapter|section|part)\s+[\d.]+|^\d+\.\d+[\s.]+[A-Za-z].{4,}$",
        re.IGNORECASE,
    )
    for line in lines:
        if header_re.match(line.strip()) and len(buf) > 30:
            flush()
            section = line.strip()[:200]
        buf.append(line)
        if sum(len(x) for x in buf) > 2800:
            flush()
    flush()

    if not chunks:
        # Fallback: sliding windows
        t = re.sub(r"\s+", " ", text).strip()
        w = 2400
        for i in range(0, len(t), w):
            part = t[i : i + w]
            if len(part) < 40:
                continue
            chunks.append(
                {
                    "source": source,
                    "section": f"window_{i // w}",
                    "content": part,
                    "chunk_id": f"{source}:w{i // w}",
                }
            )
    return chunks


def ingest_pdfs(data_dir: Path | None = None, out_path: Path | None = None) -> Path:
    """
    Scan data_dir for PDFs and airport_facilities/*.xml (AFD index).

    Writes ``index/chunks.json`` (BM25 corpus) and ``index/airport_index.json``
    (LID/NAVAID -> chunk_id for hybrid airport lookup).
    """
    root = Path(data_dir or RAG_DATA_DIR).resolve()
    index_dir = root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    out = out_path or (index_dir / "chunks.json")

    all_chunks: list[dict[str, Any]] = []
    merged_airport_index: dict[str, list[str]] = {}

    af_dir = root / "airport_facilities"
    if af_dir.is_dir():
        for xml_path in sorted(af_dir.glob("*.xml")):
            xml_chunks, partial_codes = _afd_xml_chunks(xml_path, root)
            all_chunks.extend(xml_chunks)
            for key, cid_list in partial_codes.items():
                bucket = merged_airport_index.setdefault(key, [])
                for cid in cid_list:
                    if cid not in bucket:
                        bucket.append(cid)

    airport_index_path = index_dir / "airport_index.json"
    airport_index_path.write_text(
        json.dumps(merged_airport_index, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    pdfs: list[Path] = list(root.glob("*.pdf")) + list(af_dir.glob("*.pdf"))

    for pdf in pdfs:
        try:
            doc = fitz.open(pdf)
        except Exception:  # noqa: BLE001
            continue
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text())
        doc.close()
        full = "\n".join(parts)
        try:
            rel = pdf.relative_to(root).as_posix()
        except ValueError:
            rel = pdf.name
        all_chunks.extend(_chunk_text(full, str(rel)))

    out.write_text(json.dumps(all_chunks, indent=2), encoding="utf-8")
    return out


def main() -> None:
    p = ingest_pdfs()
    ap = p.parent / "airport_index.json"
    print(f"Wrote {p} and {ap}")


if __name__ == "__main__":
    main()
