from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

import database
import main


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class PositionResponse(BaseModel):
    id: int
    cycle_id: int
    icao24: str
    callsign: Optional[str]
    origin_country: Optional[str]
    longitude: float
    latitude: float
    geo_altitude: Optional[float]
    velocity: Optional[float]
    true_track: Optional[float]
    on_ground: bool
    last_contact: Optional[int]
    ingested_at: int


class AnomalyResponse(BaseModel):
    id: int
    cycle_id: int
    icao24: str
    type: str
    detail: Optional[str]
    value: Optional[float]
    threshold: Optional[float]
    detected_at: int


class CycleSummaryResponse(BaseModel):
    id: int
    started_at: int
    finished_at: Optional[int]
    raw_count: Optional[int]
    position_count: Optional[int]
    anomaly_count: Optional[int]
    summary: Optional[str]


# ---------------------------------------------------------------------------
# Lifespan: init DB + start scheduler on startup, stop on shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    main.run_cycle()
    thread = main.start_scheduler()
    yield
    main.stop_scheduler()


app = FastAPI(title="TelematicsHub", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(Path(__file__).parent / "dashboard.html")


@app.get("/health")
def health():
    cycle = database.latest_cycle()
    return {
        "status": "ok",
        "last_cycle_id": cycle["id"] if cycle else None,
    }


@app.get("/positions", response_model=list[PositionResponse])
def get_positions(
    cycle_id: Optional[int] = Query(None),
    icao24: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    rows = database.latest_positions(cycle_id=cycle_id, icao24=icao24, limit=limit)
    return [dict(row) for row in rows]


@app.get("/anomalies", response_model=list[AnomalyResponse])
def get_anomalies(
    cycle_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    rows = database.recent_anomalies(cycle_id=cycle_id, anomaly_type=type, limit=limit)
    return [dict(row) for row in rows]


@app.get("/summary", response_model=CycleSummaryResponse)
def get_summary(cycle_id: Optional[int] = Query(None)):
    cycle = database.latest_cycle(cycle_id=cycle_id)
    if cycle is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No cycle found")
    return dict(cycle)
