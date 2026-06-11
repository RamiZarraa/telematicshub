import requests

import config
from models import Position


def _build_auth():
    """Return the best available auth for OpenSky.

    Priority: username/password (Basic Auth) > OAuth2 > anonymous.
    Basic Auth is the simplest way to raise the rate limit with an OpenSky account.
    """
    if config.OPENSKY_USERNAME and config.OPENSKY_PASSWORD:
        return (config.OPENSKY_USERNAME, config.OPENSKY_PASSWORD)
    return None


def fetch_states() -> list[list]:
    """Fetch raw state vectors from OpenSky for the ingest bounding box.

    Returns a list of raw vectors (each is a list of ~17 values).
    Returns an empty list on any network or API error so the cycle continues.
    """
    lat_min, lon_min, lat_max, lon_max = config.INGEST_BBOX
    params = {
        "lamin": lat_min,
        "lomin": lon_min,
        "lamax": lat_max,
        "lomax": lon_max,
    }

    auth = _build_auth()
    if auth:
        print(f"[ingester] using Basic Auth as {config.OPENSKY_USERNAME}")

    try:
        resp = requests.get(
            config.OPENSKY_STATES_URL,
            params=params,
            auth=auth,
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        if resp.status_code == 429:
            print("[ingester] Rate limited by OpenSky — skipping cycle")
            return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("states") or []
    except Exception as exc:
        print(f"[ingester] fetch failed: {exc}")
        return []


def normalize(raw: list[list]) -> list[Position]:
    """Convert raw OpenSky vectors to Position objects, dropping invalid ones."""
    positions = []
    for vec in raw:
        pos = Position.from_raw_vector(vec)
        if pos is not None:
            positions.append(pos)
    return positions
