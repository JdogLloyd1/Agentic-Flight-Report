# faa_tfr.py
# FAA Temporary Flight Restrictions — GeoServer WFS (same source as tfr.faa.gov map).

from __future__ import annotations

import json
from typing import Any

import requests

# Layer used by the public TFR web app (see tfr.faa.gov Nuxt config).
GEOSERVER_WFS = "https://tfr.faa.gov/geoserver/TFR/ows"
USER_AGENT = "Agentic-Flight-Report/3.0 (FAA TFR WFS reader)"


def _summarize_feature(
    feature: dict[str, Any],
    *,
    include_geometry: bool,
) -> dict[str, Any]:
    props = feature.get("properties") or {}
    out: dict[str, Any] = {
        "notam_key": props.get("NOTAM_KEY"),
        "title": props.get("TITLE"),
        "state": props.get("STATE"),
        "legal": props.get("LEGAL"),
        "last_modification": props.get("LAST_MODIFICATION_DATETIME"),
        "location_id": props.get("CNS_LOCATION_ID"),
    }
    if include_geometry:
        out["geometry"] = feature.get("geometry")
    return {k: v for k, v in out.items() if v is not None}


def get_active_tfrs(
    max_features: int = 300,
    include_geometry: bool = False,
) -> str:
    """
    Active TFRs from FAA GeoServer WFS (FeatureCollection JSON).
    Geometry is omitted by default to keep payloads model-friendly.
    """
    cap = max(1, min(int(max_features), 500))
    params: dict[str, str] = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "TFR:V_TFR_LOC",
        "outputFormat": "application/json",
        "srsname": "EPSG:3857",
        "maxFeatures": str(cap),
    }
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, */*"}
    try:
        r = requests.get(GEOSERVER_WFS, params=params, headers=headers, timeout=60)
        payload: dict[str, Any] = {
            "source": "FAA TFR (GeoServer WFS)",
            "layer": "TFR:V_TFR_LOC",
            "url": r.url,
            "http_status": r.status_code,
        }
        r.raise_for_status()
        data = r.json()
    except Exception as e:  # noqa: BLE001
        return json.dumps(
            {
                "source": "FAA TFR (GeoServer WFS)",
                "url": GEOSERVER_WFS,
                "error": str(e),
                "note": "WFS fetch failed; TFR data may be temporarily unavailable.",
            },
            indent=2,
        )

    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        return json.dumps(
            {
                "source": "FAA TFR (GeoServer WFS)",
                "url": r.url,
                "error": "unexpected_wfs_payload",
                "note": "Expected GeoJSON FeatureCollection.",
            },
            indent=2,
        )

    raw_features = data.get("features") or []
    summaries = [
        _summarize_feature(f, include_geometry=include_geometry) for f in raw_features
    ]
    out: dict[str, Any] = {
        "source": "FAA TFR (GeoServer WFS)",
        "layer": "TFR:V_TFR_LOC",
        "url": r.url,
        "http_status": r.status_code,
        "feature_count": len(raw_features),
        "max_features_requested": cap,
        "features": summaries,
        "note": (
            "Summaries from NOTAM_KEY / TITLE / STATE / LEGAL. "
            "Set include_geometry=true for GeoJSON geometry (large). "
            "Not a substitute for full NOTAM text; verify critical ops with official sources."
        ),
    }
    return json.dumps(out, indent=2)
