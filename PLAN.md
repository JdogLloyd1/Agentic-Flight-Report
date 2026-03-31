# Airspace Intelligence Agent — Project Plan

## Overview

An AI-powered application that builds a real-time understanding of the US airspace picture — including significant weather systems, FAA ground stops, TFRs, and TSA delays — and uses that context to predict the impact on a specific flight.

The agent uses **tool-calling** for live data fetching and **RAG** for reference/historical knowledge, synthesizing both into a structured impact prediction.

---

## Architecture

```
Data Ingestion Layer (Tool-Calling)
├── FAA NASSTATUS API          → Ground stops, GDPs, en route programs
├── FAA TFR Feed               → Temporary Flight Restrictions
├── aviationweather.gov API    → METARs, TAFs, SIGMETs, AIRMETs, PIREPs
├── NOAA api.weather.gov       → Active weather alerts, gridded forecasts
├── FlightAware AeroAPI        → Specific flight status, delays, cancellations
├── OpenSky Network API        → Live ADS-B position data (free)
└── MyTSA Endpoint             → Airport security wait times

RAG Knowledge Layer
├── FAA Order 7110.65          → ATC procedures and ground stop reasoning
├── Airport facility directories → Runway configs, known weather sensitivities
├── Historical delay patterns  → Baseline delay expectations by airport/season
├── Airline delay/cancel policies → Passenger impact reasoning
└── ICAO weather decode reference → METAR/TAF interpretation

Agent Orchestration Layer (Claude)
├── ReAct loop: reason → call tool → observe → reason
├── Parallel tool calls for airspace picture synthesis
├── RAG queries for interpretive context
├── Cross-reference flight route against active threats
└── Output: impact prediction with confidence score

Output Layer
├── Natural language flight briefing
├── Confidence-scored delay/cancellation prediction
└── Recommended passenger actions
```

---

## Agent Tool Definitions

These are the discrete tools the agent can invoke during its reasoning loop:

| Tool | Data Source | Purpose |
|---|---|---|
| `get_ground_stops(airport?)` | FAA NASSTATUS | Active GDPs and ground stops |
| `get_weather_alerts(region?)` | NOAA api.weather.gov | Active NWS weather alerts |
| `get_sigmets_airmets()` | aviationweather.gov | In-flight hazard advisories |
| `get_flight_status(flight_id)` | FlightAware AeroAPI | Real-time flight status + route |
| `get_tsa_wait_times(airport)` | MyTSA endpoint | Security checkpoint wait times |
| `get_active_tfrs()` | FAA TFR feed | Temporary Flight Restrictions |
| `get_metar_taf(icao_code)` | aviationweather.gov | Airport weather observations + forecasts |
| `get_live_position(flight_id)` | OpenSky Network | Live ADS-B aircraft position |

---

## Agent Reasoning Loop (Example)

**User input:** "Analyze AA 237 BOS→ORD departing at 3pm"

```
Step 1: [Tool] get_flight_status("AA237")          → route, gate, current status
Step 2: [Tool] get_ground_stops("ORD")             → active GDP at destination
Step 3: [Tool] get_sigmets_airmets()               → convective SIGMETs over Great Lakes
Step 4: [Tool] get_metar_taf("KORD"), get_metar_taf("KBOS")  → current + forecast wx
Step 5: [Tool] get_tsa_wait_times("BOS")           → security wait at departure airport
Step 6: [RAG]  "ORD delay patterns summer convection"         → historical baseline
Step 7: [RAG]  "GDP ground delay program procedures"          → reasoning context
Step 8: [Synthesize] → structured impact prediction
```

**Key principle:** Tool-calling answers *"what is happening right now"*. RAG answers *"what does this mean and how bad is it typically"*.

---

## RAG Pipeline Notes

- **Chunk FAA documents by logical section**, not by page — procedural units are more useful than arbitrary page breaks
- **Embed historical delay data** as structured summaries per airport + season + condition type
- **Short TTL caching** on tool results: 30 sec for flight position, 2–5 min for weather and ground stops
- Consider **Redis** or an in-memory cache to avoid hammering APIs on repeated queries

---

## Suggested File Structure

```
airspace-agent/
├── PLAN.md                    # This file
├── .cursorrules               # Cursor AI system prompt / architectural rules
├── .env                       # API keys (never commit)
├── .env.example               # Key names without values (commit this)
│
├── src/
│   ├── agent/
│   │   ├── index.ts           # Main agent loop (ReAct)
│   │   ├── tools.ts           # Tool definitions and handlers
│   │   └── synthesize.ts      # Impact prediction synthesis
│   │
│   ├── data/
│   │   ├── faa.ts             # FAA NASSTATUS + TFR clients
│   │   ├── weather.ts         # aviationweather.gov + NOAA clients
│   │   ├── flights.ts         # FlightAware + OpenSky clients
│   │   └── tsa.ts             # MyTSA client
│   │
│   ├── rag/
│   │   ├── ingest.ts          # Document ingestion + chunking
│   │   ├── embed.ts           # Embedding pipeline
│   │   └── query.ts           # RAG query interface
│   │
│   └── ui/
│       └── index.tsx          # Frontend (optional)
│
├── docs/
│   └── faa-7110-65.pdf        # Reference documents for RAG corpus
│
└── README.md
```

---

## API Access Setup Instructions

### 1. FlightAware AeroAPI
- **URL:** https://www.flightaware.com/aeroapi/
- **Cost:** Free tier available (limited requests/month); paid tiers scale up
- **Steps:**
  1. Create an account at flightaware.com
  2. Navigate to **AeroAPI** in your account dashboard
  3. Generate an API key
  4. Docs: https://www.flightaware.com/aeroapi/portal/documentation
- **Env var:** `FLIGHTAWARE_API_KEY`

### 2. aviationweather.gov (NOAA)
- **URL:** https://aviationweather.gov/data/api/
- **Cost:** Free, no authentication required
- **Steps:**
  1. No signup needed — open REST API
  2. Review the endpoint docs at https://aviationweather.gov/data/api/
  3. Key endpoints: `/api/data/metar`, `/api/data/taf`, `/api/data/sigmet`, `/api/data/pirep`
- **Env var:** None required

### 3. NOAA Weather API (api.weather.gov)
- **URL:** https://www.weather.gov/documentation/services-web-api
- **Cost:** Free, no authentication required
- **Steps:**
  1. No signup needed — open REST API
  2. Docs: https://api.weather.gov/
  3. Useful endpoints: `/alerts/active`, `/gridpoints/{office}/{x},{y}/forecast`
- **Env var:** None required (User-Agent header recommended: `your-app-name, your@email.com`)

### 4. FAA NASSTATUS (Ground Delays & Ground Stops)
- **URL:** https://nasstatus.faa.gov/
- **Cost:** Free, no authentication required
- **Steps:**
  1. No signup needed
  2. XML feed: `https://nasstatus.faa.gov/api/airport-status-information`
  3. Also check: https://www.fly.faa.gov/flyfaa/usmap.jsp for reference
- **Env var:** None required

### 5. FAA TFR Feed
- **URL:** https://tfr.faa.gov/
- **Cost:** Free, no authentication required
- **Steps:**
  1. No signup needed
  2. GeoJSON feed: `https://tfr.faa.gov/tfr2/list.html`
  3. Individual TFR data available at `https://tfr.faa.gov/save_pages/detail_{id}.xml`
- **Env var:** None required

### 6. OpenSky Network API
- **URL:** https://opensky-network.org/apidoc/
- **Cost:** Free (anonymous access rate-limited; free account increases limits)
- **Steps:**
  1. Register at https://opensky-network.org/
  2. Use your username/password for HTTP Basic Auth (or anonymous for basic access)
  3. Docs: https://openskynetwork.github.io/opensky-api/
- **Env var:** `OPENSKY_USERNAME`, `OPENSKY_PASSWORD`

### 7. MyTSA Wait Times
- **URL:** https://apps.tsa.dhs.gov/mytsa/ccp_data.xml
- **Cost:** Free, no authentication required
- **Steps:**
  1. No signup needed — publicly accessible XML endpoint
  2. Note: This endpoint is not officially documented by TSA; treat it as best-effort
  3. Fallback: scrape TSA advisory pages at https://www.tsa.gov/travel/security-screening
- **Env var:** None required

### 8. Anthropic API (Claude — Agent Brain)
- **URL:** https://console.anthropic.com/
- **Cost:** Pay-per-token; see https://www.anthropic.com/pricing
- **Steps:**
  1. Create an account at https://console.anthropic.com/
  2. Navigate to **API Keys** and generate a key
  3. Recommended model: `claude-sonnet-4-20250514` for agent loops (balance of speed + reasoning)
  4. Docs: https://docs.anthropic.com/
- **Env var:** `ANTHROPIC_API_KEY`

---

## .env.example

```
# Anthropic
ANTHROPIC_API_KEY=

# FlightAware
FLIGHTAWARE_API_KEY=

# OpenSky (optional — anonymous access works without these)
OPENSKY_USERNAME=
OPENSKY_PASSWORD=

# No keys needed for:
# - aviationweather.gov
# - api.weather.gov
# - FAA NASSTATUS
# - FAA TFR feed
# - MyTSA endpoint
```

---

## MVP Build Order

1. **Stand up data clients** — wire up each API endpoint in `src/data/`, verify responses
2. **Define agent tools** — wrap each client as a callable tool in `src/agent/tools.ts`
3. **Build the agent loop** — ReAct loop with Claude in `src/agent/index.ts`
4. **Test with a single flight** — run the full loop against a live flight, inspect reasoning
5. **Add RAG layer** — ingest FAA docs, embed, wire into agent reasoning
6. **Add caching** — Redis or in-memory TTL cache on tool results
7. **Build UI** — simple input (flight number + departure time) → briefing output

---

## Key Design Decisions

- **Tool-calling over RAG for live data** — never RAG over flight or weather data; always fetch fresh
- **Parallel tool calls where possible** — fetch METAR for departure + arrival simultaneously
- **Structured output from synthesis step** — JSON schema for delay prediction (probability, severity, recommended action) before rendering to natural language
- **Graceful degradation** — if MyTSA or a non-critical endpoint is down, agent continues with available data and notes the gap in its briefing
