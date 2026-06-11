import json
import requests

import config


def generate(stats: dict) -> str:
    """Send cycle stats to Ollama and return a 2-3 sentence summary.

    Falls back to a templated string if Ollama is unavailable so a cycle
    never fails because of the LLM.
    """
    prompt = (
        "You are a telematics data-quality analyst. "
        "Given the following ingestion cycle statistics, write exactly 2-3 sentences "
        "summarizing the data volume and the most notable anomalies. "
        "Be concise and professional.\n\n"
        f"Cycle ID: {stats['cycle_id']}\n"
        f"Positions ingested: {stats['position_count']}\n"
        f"Total anomalies: {stats['anomaly_count']}\n"
        f"Breakdown: {stats['anomaly_breakdown']}\n"
        f"Top countries: {stats['top_countries']}\n"
        f"Fastest implied speed: {stats['fastest_kmh']} km/h\n"
        f"Sample anomalies: {stats['sample_anomalies']}\n"
    )

    try:
        resp = requests.post(
            config.OLLAMA_URL,
            json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=config.OLLAMA_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
    except Exception as exc:
        print(f"[ai_summary] Ollama unavailable: {exc} — using fallback")
        return _fallback(stats)


def _fallback(stats: dict) -> str:
    bd = stats["anomaly_breakdown"]
    return (
        f"Cycle {stats['cycle_id']} ingested {stats['position_count']} positions "
        f"with {stats['anomaly_count']} anomalies detected "
        f"({bd.get('impossible_speed', 0)} impossible speed, "
        f"{bd.get('stale', 0)} stale, "
        f"{bd.get('out_of_bounds', 0)} out of bounds). "
        f"Fastest implied speed was {stats['fastest_kmh']} km/h."
    )
