# registry.py
# Maps tool names to callables and OpenAI-style tool schemas for Ollama / MCP.

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from typing import Any

from . import (
    aviation_weather,
    faa_nasstatus,
    faa_tfr,
    noaa_weather,
    opensky,
    tsa_wait_times,
    web_search,
)

# 0. Tool implementations ############################################


TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "fetch_nasstatus_airport_status": faa_nasstatus.fetch_nasstatus_airport_status,
    "get_metar": aviation_weather.get_metar,
    "get_taf": aviation_weather.get_taf,
    "get_sigmets": aviation_weather.get_sigmets,
    "get_gairmets": aviation_weather.get_gairmets,
    "get_pireps": aviation_weather.get_pireps,
    "get_weather_alerts": noaa_weather.get_weather_alerts,
    "get_active_tfrs": faa_tfr.get_active_tfrs,
    "get_aircraft_states": opensky.get_aircraft_states,
    "get_tsa_wait_times": tsa_wait_times.get_tsa_wait_times,
    "url_query": web_search.url_query,
    "web_search_general": web_search.web_search_general,
}


def dispatch_tool(name: str, arguments: dict[str, Any] | None) -> str:
    """Invoke a registered tool by name; returns string (or JSON string) for the model."""
    if name not in TOOL_REGISTRY:
        return json.dumps({"error": "unknown_tool", "name": name})
    fn = TOOL_REGISTRY[name]
    args = dict(arguments or {})
    sig = inspect.signature(fn)
    params = sig.parameters
    # Drop unknown keys; apply defaults for missing optional params
    kwargs: dict[str, Any] = {}
    for pname, p in params.items():
        if pname in args:
            kwargs[pname] = args[pname]
        elif p.default is inspect.Parameter.empty and p.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            # Required missing — let TypeError surface after loop
            pass
    try:
        try:
            return fn(**kwargs)
        except TypeError:
            # Retry with only explicitly provided keys that exist on callable
            kwargs2 = {k: v for k, v in args.items() if k in params}
            return fn(**kwargs2)
    except Exception as e:  # noqa: BLE001 — return JSON for the model, do not break the tool loop
        return json.dumps(
            {
                "error": "tool_execution_failed",
                "tool": name,
                "detail": str(e),
                "exception_type": type(e).__name__,
            }
        )


# 1. Ollama / OpenAI-style tool list ##################################


def _fn(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


ALL_TOOL_SCHEMAS: list[dict[str, Any]] = [
    _fn(
        "fetch_nasstatus_airport_status",
        (
            "Fetch FAA NAS airport status (ground stops, GDPs, delays) from "
            "nasstatus.faa.gov as structured JSON."
        ),
        {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Optional override URL for the XML feed.",
                },
                "include_parsed_json": {
                    "type": "boolean",
                    "description": "If true, return parsed NAS data (default).",
                },
            },
            "required": [],
        },
    ),
    _fn(
        "get_metar",
        "Current METAR observation for an ICAO station (e.g. KDFW).",
        {
            "type": "object",
            "properties": {
                "station_id": {
                    "type": "string",
                    "description": "ICAO station id, e.g. KDFW.",
                },
                "hours_back": {
                    "type": "integer",
                    "description": "Hours of history to include (default 1).",
                },
            },
            "required": ["station_id"],
        },
    ),
    _fn(
        "get_taf",
        "Terminal aerodrome forecast for an ICAO station.",
        {
            "type": "object",
            "properties": {
                "station_id": {
                    "type": "string",
                    "description": "ICAO station id, e.g. KBOS.",
                },
            },
            "required": ["station_id"],
        },
    ),
    _fn(
        "get_sigmets",
        "Active SIGMETs; optional hazard_type: convective, turbulence, icing.",
        {
            "type": "object",
            "properties": {
                "hazard_type": {
                    "type": "string",
                    "description": "Optional SIGMET hazard filter.",
                },
            },
            "required": [],
        },
    ),
    _fn(
        "get_gairmets",
        (
            "Active G-AIRMETs; optional hazard_type: IFR, mountain_obscuration, "
            "turbulence, icing, freezing_level."
        ),
        {
            "type": "object",
            "properties": {
                "hazard_type": {"type": "string", "description": "Optional hazard filter."},
            },
            "required": [],
        },
    ),
    _fn(
        "get_pireps",
        "Recent pilot reports; optional station and search radius in NM.",
        {
            "type": "object",
            "properties": {
                "station_id": {"type": "string", "description": "Optional ICAO reference."},
                "distance_nm": {
                    "type": "integer",
                    "description": "Search radius in nautical miles (default 100).",
                },
            },
            "required": [],
        },
    ),
    _fn(
        "get_weather_alerts",
        "Active NWS weather alerts; optional area (e.g. state) and severity.",
        {
            "type": "object",
            "properties": {
                "area": {"type": "string", "description": "Optional state or area code."},
                "severity": {
                    "type": "string",
                    "description": "Optional: extreme, severe, moderate, ...",
                },
            },
            "required": [],
        },
    ),
    _fn(
        "get_active_tfrs",
        (
            "Active Temporary Flight Restrictions from FAA GeoServer WFS (same data as tfr.faa.gov). "
            "Returns NOTAM key, title, state, legal; omit geometry by default."
        ),
        {
            "type": "object",
            "properties": {
                "max_features": {
                    "type": "integer",
                    "description": "Max TFR features (1–500, default 300).",
                },
                "include_geometry": {
                    "type": "boolean",
                    "description": "If true, include GeoJSON geometry per feature (large payload).",
                },
            },
            "required": [],
        },
    ),
    _fn(
        "get_aircraft_states",
        (
            "Live ADS-B state vectors from OpenSky; optional icao24 hex or "
            "bounding_box with lamin/lomin/lamax/lomax."
        ),
        {
            "type": "object",
            "properties": {
                "icao24": {"type": "string", "description": "Optional aircraft ICAO24 hex."},
                "bounding_box": {
                    "type": "object",
                    "description": "Optional lat/lon bounding box.",
                },
            },
            "required": [],
        },
    ),
    _fn(
        "get_tsa_wait_times",
        "TSA checkpoint wait times for a US airport code (e.g. DFW).",
        {
            "type": "object",
            "properties": {
                "airport_code": {"type": "string", "description": "Airport code, e.g. DFW."},
            },
            "required": ["airport_code"],
        },
    ),
    _fn(
        "url_query",
        "Fetch a web page URL and return cleaned text content.",
        {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full HTTP(S) URL."},
                "max_chars": {"type": "integer", "description": "Max characters (default 20000)."},
            },
            "required": ["url"],
        },
    ),
    _fn(
        "web_search_general",
        "DuckDuckGo instant answer style search for live pointers.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "max_results": {"type": "integer", "description": "Max results (default 5)."},
            },
            "required": ["query"],
        },
    ),
]

# Agent 1 (data collector) default: NAS/weather/TFR/TSA only — no OpenSky, page fetch, or web search.
_AGENT_1_EXCLUDED_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "get_aircraft_states",
        "url_query",
        "web_search_general",
    }
)

DEFAULT_AGENT_TOOL_SCHEMAS: list[dict[str, Any]] = [
    s
    for s in ALL_TOOL_SCHEMAS
    if s.get("function", {}).get("name") not in _AGENT_1_EXCLUDED_TOOL_NAMES
]
