# TelematicsHub

A real-time telematics integration pipeline built to mirror what Shippeo does at scale.
Ingests 2 000+ live GPS positions every 30 seconds, runs 3 anomaly detectors,
and generates an AI cycle summary via a local LLM — all from a single `uvicorn api:app`.

Instead of truck telematics providers, the data source is the **OpenSky Network API**
(live aircraft transponders), which provides the same kind of raw GPS state vectors
a telematics provider would push: coordinates, speed, heading, timestamps.

---

## Live demo

```
uvicorn api:app
```

Open `http://localhost:8000/dashboard`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Every 30 seconds                         │
│                                                                  │
│  OpenSky Network API                                            │
│  /states/all?bbox=Western Europe                                │
│         │                                                        │
│         ▼                                                        │
│   ingester.py          fetch_states() → raw vectors [list]      │
│         │              normalize()    → Position objects         │
│         ▼                                                        │
│   database.py          INSERT positions (cycle_id)              │
│         │                                                        │
│         ▼                                                        │
│   anomaly.py           detect_impossible_speed()  haversine     │
│                        detect_stale()             last_contact  │
│                        detect_out_of_bounds()     France bbox   │
│         │                                                        │
│         ▼                                                        │
│   database.py          INSERT anomalies                         │
│         │                                                        │
│         ▼                                                        │
│   ai_summary.py        Ollama / llama3  →  cycle summary text   │
│         │                                                        │
│         ▼                                                        │
│   SQLite DB            cycles · positions · anomalies           │
│         │                                                        │
│         ▼                                                        │
│   api.py               FastAPI REST API                         │
│         │                                                        │
│         ▼                                                        │
│   dashboard.html       Leaflet map · live markers · AI sidebar  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| API | FastAPI + Uvicorn |
| Storage | SQLite |
| HTTP client | requests |
| Scheduler | schedule + threading |
| LLM | Ollama (llama3, local GPU) |
| Frontend | Leaflet.js (single HTML, no build) |

---

## Anomaly detectors

### 1. Impossible speed
Computes the [haversine](https://en.wikipedia.org/wiki/Haversine_formula) great-circle
distance between a position and its previous known fix for the same vehicle ID.
Divides by the time delta to get an implied speed. Flags when `> 1200 km/h`.

```
dist_km = haversine(prev_lat, prev_lon, lat, lon)
speed   = (dist_km / delta_t) * 3600   # km/h
```

This catches coordinate jumps — the classic GPS data quality defect where a vehicle
"teleports" between two fixes due to a bad packet or clock skew.

### 2. Stale data
Flags positions where `cycle_time − last_contact > 60s`. The vehicle is still present
in the feed with its last known coordinates, but no fresh signal has been received.
Acting on stale positions means wrong ETAs and false alerts downstream.

### 3. Out of bounds
Ingestion uses a wide Western-Europe bounding box. Any position outside the France
bbox is flagged. In a production system this would be configurable per customer
(e.g. "expected region = France + Benelux").

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard` | Live map dashboard |
| GET | `/health` | Status + last cycle id |
| GET | `/positions` | Positions (`cycle_id`, `icao24`, `limit`) |
| GET | `/anomalies` | Anomalies (`type`, `cycle_id`, `limit`) |
| GET | `/summary` | AI cycle summary (`cycle_id`) |
| GET | `/docs` | Auto-generated Swagger UI |

---

## Setup

```bash
make install   # creates venv, installs deps, pulls llama3
make run       # starts the API + scheduler
```

Then open `http://localhost:8000/dashboard`.

**Optional — OpenSky credentials** (raises rate limit from 100 to 4000 req/day):
```bash
cp .env.example .env
# fill in OPENSKY_USERNAME and OPENSKY_PASSWORD
```

---

## Database schema

```sql
cycles     — one row per ingestion run (timestamps, counts, AI summary)
positions  — normalized GPS fix per vehicle per cycle
anomalies  — one row per finding, linked to cycle + position
```

---

## Why this maps to Shippeo's stack

Shippeo ingests real-time GPS positions from telematics providers (Trimble, Webfleet,
etc.), normalizes heterogeneous formats into a unified position model, validates data
quality, and detects anomalies before forwarding clean data to ETA algorithms.

TelematicsHub replicates this pipeline end-to-end:

| Shippeo concept | TelematicsHub equivalent |
|---|---|
| Telematics provider feed | OpenSky Network API (real GPS) |
| Raw position vector | OpenSky state vector (17 fields) |
| Normalized position model | `Position` dataclass |
| Data quality validation | 3 anomaly detectors |
| Storage | SQLite (same relational model) |
| REST API | FastAPI `/positions` `/anomalies` |
| Observability | AI cycle summary via local LLM |
