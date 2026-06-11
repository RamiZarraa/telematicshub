from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Position:
    icao24: str
    callsign: Optional[str]
    origin_country: Optional[str]
    longitude: float
    latitude: float
    geo_altitude: Optional[float]
    velocity: Optional[float]       # m/s, as reported by OpenSky
    true_track: Optional[float]     # heading in degrees
    vertical_rate: Optional[float]
    on_ground: bool
    time_position: Optional[int]    # epoch s of last position update
    last_contact: Optional[int]     # epoch s of last signal of any kind

    @classmethod
    def from_raw_vector(cls, vec: list) -> Optional[Position]:
        """Map an OpenSky state-vector list to a Position.

        Returns None when latitude or longitude are missing — a position
        without coordinates is useless downstream.

        OpenSky vector indices:
            0  icao24          1  callsign         2  origin_country
            3  time_position   4  last_contact     5  longitude
            6  latitude        7  baro_altitude    8  on_ground
            9  velocity        10 true_track       11 vertical_rate
            13 geo_altitude
        """
        if not vec or len(vec) < 11:
            return None
        if vec[6] is None or vec[5] is None:
            return None

        callsign = vec[1].strip() if isinstance(vec[1], str) else vec[1]

        return cls(
            icao24=vec[0],
            callsign=callsign or None,
            origin_country=vec[2],
            longitude=float(vec[5]),
            latitude=float(vec[6]),
            geo_altitude=vec[13] if len(vec) > 13 else None,
            velocity=vec[9],
            true_track=vec[10],
            vertical_rate=vec[11] if len(vec) > 11 else None,
            on_ground=bool(vec[8]),
            time_position=vec[3],
            last_contact=vec[4],
        )


@dataclass
class Anomaly:
    icao24: str
    type: str                       # 'impossible_speed' | 'stale' | 'out_of_bounds'
    detail: str                     # human-readable explanation
    value: Optional[float]          # measured value that triggered the flag
    threshold: Optional[float]      # limit it breached
    position_id: Optional[int] = None   # filled after DB insert
