import math
import time
from typing import Optional

import config
import database
from models import Position, Anomaly


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two GPS coordinates."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def detect_impossible_speed(positions: list[Position], cycle_id: int) -> list[Anomaly]:
    """Flag positions where the implied speed since the last known fix is unrealistic."""
    anomalies = []
    for pos in positions:
        if pos.on_ground:
            continue
        if pos.time_position is None:
            continue

        prev_rows = database.positions_for_icao(pos.icao24, limit=2)
        if not prev_rows:
            continue

        prev = prev_rows[0]
        if prev["cycle_id"] == cycle_id:
            # same cycle — skip, we only compare across cycles
            if len(prev_rows) < 2:
                continue
            prev = prev_rows[1]

        prev_time = prev["time_position"]
        if prev_time is None:
            continue

        dt = pos.time_position - prev_time
        if dt <= 0:
            continue

        dist_km = haversine_km(prev["latitude"], prev["longitude"],
                               pos.latitude, pos.longitude)
        speed_kmh = (dist_km / dt) * 3600

        if speed_kmh > config.MAX_GROUND_SPEED_KMH:
            anomalies.append(Anomaly(
                icao24=pos.icao24,
                type="impossible_speed",
                detail=(
                    f"{pos.icao24} implied {speed_kmh:.0f} km/h "
                    f"({dist_km:.1f} km in {dt}s)"
                ),
                value=round(speed_kmh, 1),
                threshold=config.MAX_GROUND_SPEED_KMH,
            ))
    return anomalies


def detect_stale(positions: list[Position], cycle_time: int) -> list[Anomaly]:
    """Flag positions whose last_contact is too old relative to the cycle time."""
    anomalies = []
    for pos in positions:
        if pos.last_contact is None:
            continue
        age = cycle_time - pos.last_contact
        if age > config.STALE_SECONDS:
            anomalies.append(Anomaly(
                icao24=pos.icao24,
                type="stale",
                detail=(
                    f"{pos.icao24} last heard {age}s ago "
                    f"(threshold {config.STALE_SECONDS}s)"
                ),
                value=float(age),
                threshold=float(config.STALE_SECONDS),
            ))
    return anomalies


def detect_out_of_bounds(positions: list[Position]) -> list[Anomaly]:
    """Flag positions outside the France bounding box."""
    lat_min, lon_min, lat_max, lon_max = config.FRANCE_BBOX
    anomalies = []
    for pos in positions:
        in_bounds = (
            lat_min <= pos.latitude <= lat_max
            and lon_min <= pos.longitude <= lon_max
        )
        if not in_bounds:
            anomalies.append(Anomaly(
                icao24=pos.icao24,
                type="out_of_bounds",
                detail=(
                    f"{pos.icao24} at ({pos.latitude:.3f}, {pos.longitude:.3f}) "
                    f"is outside France bbox"
                ),
                value=None,
                threshold=None,
            ))
    return anomalies


def detect_all(positions: list[Position], cycle_id: int,
               cycle_time: Optional[int] = None) -> list[Anomaly]:
    """Run all three detectors and return the combined anomaly list."""
    if cycle_time is None:
        cycle_time = int(time.time())
    return (
        detect_impossible_speed(positions, cycle_id)
        + detect_stale(positions, cycle_time)
        + detect_out_of_bounds(positions)
    )
