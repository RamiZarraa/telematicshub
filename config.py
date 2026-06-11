import os
from pathlib import Path

# --- minimal .env loader ---------------------------------------------------
_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _val = _line.partition("=")
        os.environ.setdefault(_key.strip(), _val.strip())

# --- OpenSky ---------------------------------------------------------------
OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"
OPENSKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)
OPENSKY_CLIENT_ID = os.getenv("OPENSKY_CLIENT_ID", "").strip()
OPENSKY_CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET", "").strip()
OPENSKY_USERNAME = os.getenv("OPENSKY_USERNAME", "").strip()
OPENSKY_PASSWORD = os.getenv("OPENSKY_PASSWORD", "").strip()

# Wider Western-Europe box used for ingestion (lat_min, lon_min, lat_max, lon_max).
# Deliberately larger than France so out-of-bounds detector fires on real data.
INGEST_BBOX = (36.0, -10.0, 55.0, 15.0)

# "Expected" region — positions outside this are flagged out_of_bounds.
FRANCE_BBOX = (41.0, -5.5, 51.5, 9.5)

# --- pipeline --------------------------------------------------------------
POLL_INTERVAL_SECONDS = 30
HTTP_TIMEOUT_SECONDS = 15

MAX_GROUND_SPEED_KMH = 1200.0   # above this implies a bad coordinate jump
STALE_SECONDS = 60              # last_contact older than this vs cycle time

# --- Ollama ----------------------------------------------------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT_SECONDS = 60

# --- storage ---------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", "telematicshub.db")
