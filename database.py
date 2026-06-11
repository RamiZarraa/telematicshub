import sqlite3
import time
from typing import Optional

import config
from models import Position, Anomaly


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cycles (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at     INTEGER NOT NULL,
                finished_at    INTEGER,
                raw_count      INTEGER,
                position_count INTEGER,
                anomaly_count  INTEGER,
                summary        TEXT
            );

            CREATE TABLE IF NOT EXISTS positions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id       INTEGER NOT NULL REFERENCES cycles(id),
                icao24         TEXT NOT NULL,
                callsign       TEXT,
                origin_country TEXT,
                longitude      REAL,
                latitude       REAL,
                geo_altitude   REAL,
                velocity       REAL,
                true_track     REAL,
                vertical_rate  REAL,
                on_ground      INTEGER,
                time_position  INTEGER,
                last_contact   INTEGER,
                ingested_at    INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_positions_cycle ON positions(cycle_id);
            CREATE INDEX IF NOT EXISTS idx_positions_icao  ON positions(icao24);

            CREATE TABLE IF NOT EXISTS anomalies (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id    INTEGER NOT NULL REFERENCES cycles(id),
                position_id INTEGER REFERENCES positions(id),
                icao24      TEXT NOT NULL,
                type        TEXT NOT NULL,
                detail      TEXT,
                value       REAL,
                threshold   REAL,
                detected_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_anomalies_cycle ON anomalies(cycle_id);
            CREATE INDEX IF NOT EXISTS idx_anomalies_type  ON anomalies(type);
        """)


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def insert_cycle(started_at: int) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO cycles (started_at) VALUES (?)", (started_at,)
        )
        return cur.lastrowid


def finish_cycle(cycle_id: int, raw_count: int,
                 position_count: int, anomaly_count: int) -> None:
    with _connect() as conn:
        conn.execute(
            """UPDATE cycles
               SET finished_at=?, raw_count=?, position_count=?, anomaly_count=?
               WHERE id=?""",
            (int(time.time()), raw_count, position_count, anomaly_count, cycle_id),
        )


def update_cycle_summary(cycle_id: int, summary: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE cycles SET summary=? WHERE id=?", (summary, cycle_id)
        )


def insert_positions(cycle_id: int, positions: list[Position]) -> list[int]:
    """Insert all positions for a cycle, return their row IDs in order."""
    now = int(time.time())
    rows = [
        (cycle_id, p.icao24, p.callsign, p.origin_country,
         p.longitude, p.latitude, p.geo_altitude,
         p.velocity, p.true_track, p.vertical_rate,
         int(p.on_ground), p.time_position, p.last_contact, now)
        for p in positions
    ]
    with _connect() as conn:
        ids = []
        for row in rows:
            cur = conn.execute(
                """INSERT INTO positions
                   (cycle_id, icao24, callsign, origin_country,
                    longitude, latitude, geo_altitude,
                    velocity, true_track, vertical_rate,
                    on_ground, time_position, last_contact, ingested_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                row,
            )
            ids.append(cur.lastrowid)
        return ids


def insert_anomalies(cycle_id: int, anomalies: list[Anomaly]) -> None:
    now = int(time.time())
    with _connect() as conn:
        conn.executemany(
            """INSERT INTO anomalies
               (cycle_id, position_id, icao24, type, detail, value, threshold, detected_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            [
                (cycle_id, a.position_id, a.icao24, a.type,
                 a.detail, a.value, a.threshold, now)
                for a in anomalies
            ],
        )


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def latest_positions(cycle_id: Optional[int] = None,
                     icao24: Optional[str] = None,
                     limit: int = 100) -> list[sqlite3.Row]:
    query = "SELECT * FROM positions"
    conditions, params = [], []
    if cycle_id is not None:
        conditions.append("cycle_id = ?")
        params.append(cycle_id)
    if icao24 is not None:
        conditions.append("icao24 = ?")
        params.append(icao24)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY ingested_at DESC LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        return conn.execute(query, params).fetchall()


def recent_anomalies(cycle_id: Optional[int] = None,
                     anomaly_type: Optional[str] = None,
                     limit: int = 100) -> list[sqlite3.Row]:
    query = "SELECT * FROM anomalies"
    conditions, params = [], []
    if cycle_id is not None:
        conditions.append("cycle_id = ?")
        params.append(cycle_id)
    if anomaly_type is not None:
        conditions.append("type = ?")
        params.append(anomaly_type)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY detected_at DESC LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        return conn.execute(query, params).fetchall()


def latest_cycle(cycle_id: Optional[int] = None) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        if cycle_id is not None:
            return conn.execute(
                "SELECT * FROM cycles WHERE id=?", (cycle_id,)
            ).fetchone()
        return conn.execute(
            "SELECT * FROM cycles WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()


def positions_for_icao(icao24: str, limit: int = 2) -> list[sqlite3.Row]:
    """Return the most recent positions for an aircraft (used by speed detector)."""
    with _connect() as conn:
        return conn.execute(
            """SELECT * FROM positions WHERE icao24=?
               ORDER BY ingested_at DESC LIMIT ?""",
            (icao24, limit),
        ).fetchall()
