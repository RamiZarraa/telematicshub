import threading
import time
from collections import Counter

import schedule

import ai_summary
import anomaly
import database
import ingester


def build_stats(cycle_id: int, positions: list, anomalies: list) -> dict:
    breakdown = Counter(a.type for a in anomalies)
    top_countries = Counter(
        p.origin_country for p in positions if p.origin_country
    ).most_common(5)

    speeds = [
        a.value for a in anomalies
        if a.type == "impossible_speed" and a.value is not None
    ]
    fastest_kmh = max(speeds) if speeds else 0.0

    sample_anomalies = [
        a.detail for a in anomalies
        if a.type == "impossible_speed"
    ][:3]

    return {
        "cycle_id": cycle_id,
        "position_count": len(positions),
        "anomaly_count": len(anomalies),
        "anomaly_breakdown": dict(breakdown),
        "top_countries": top_countries,
        "fastest_kmh": fastest_kmh,
        "sample_anomalies": sample_anomalies,
    }


def run_cycle() -> None:
    cycle_time = int(time.time())
    cycle_id = database.insert_cycle(cycle_time)
    print(f"[cycle {cycle_id}] started")

    # 1. fetch + normalize
    raw = ingester.fetch_states()
    positions = ingester.normalize(raw)
    print(f"[cycle {cycle_id}] {len(raw)} raw vectors → {len(positions)} positions")

    # 2. persist positions
    position_ids = database.insert_positions(cycle_id, positions)
    for pos, pid in zip(positions, position_ids):
        pos_with_id = pos   # position_id is on Anomaly, not Position — no change needed

    # 3. detect anomalies
    detected = anomaly.detect_all(positions, cycle_id, cycle_time)
    print(f"[cycle {cycle_id}] {len(detected)} anomalies detected")

    # 4. persist anomalies
    database.insert_anomalies(cycle_id, detected)

    # 5. AI summary
    stats = build_stats(cycle_id, positions, detected)
    summary = ai_summary.generate(stats)
    print(f"[cycle {cycle_id}] summary: {summary[:80]}...")

    # 6. close cycle
    database.finish_cycle(cycle_id, len(raw), len(positions), len(detected))
    database.update_cycle_summary(cycle_id, summary)
    print(f"[cycle {cycle_id}] done")


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

_stop_event = threading.Event()


def start_scheduler() -> threading.Thread:
    """Start run_cycle on a background daemon thread, firing every POLL_INTERVAL_SECONDS."""
    import config

    schedule.every(config.POLL_INTERVAL_SECONDS).seconds.do(run_cycle)

    def loop():
        while not _stop_event.is_set():
            schedule.run_pending()
            time.sleep(1)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread


def stop_scheduler() -> None:
    _stop_event.set()


if __name__ == "__main__":
    database.init_db()
    run_cycle()
