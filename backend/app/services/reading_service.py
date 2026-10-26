"""Sensor-reading data access: latest values, trends, statistics.

Performance strategy for the ~1.5M-row (22.7M-reading) dataset:
  * latest values use DISTINCT ON (tag_id) + the (tag_id, timestamp DESC) index.
  * trends are ALWAYS time-range filtered and downsampled with TimescaleDB
    ``time_bucket`` when the raw point count would exceed MAX_TREND_POINTS, so the
    browser never receives more than ~MAX_TREND_POINTS points.
  * statistics are aggregated entirely in the database.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import MAX_TREND_POINTS
from app.thresholds import compute_status

# Approximate native cadence of the dataset (seconds). Used only to decide
# whether downsampling is needed; the actual data drives the queries.
NATIVE_CADENCE_SECONDS = 10

# "Nice" bucket sizes (seconds -> Postgres interval literal), ascending.
_BUCKETS: list[tuple[int, str]] = [
    (10, "10 seconds"),
    (30, "30 seconds"),
    (60, "1 minute"),
    (300, "5 minutes"),
    (600, "10 minutes"),
    (1800, "30 minutes"),
    (3600, "1 hour"),
    (21600, "6 hours"),
    (43200, "12 hours"),
    (86400, "1 day"),
    (604800, "7 days"),
]


def _choose_bucket(span_seconds: float, max_points: int) -> tuple[int, str] | None:
    """Return (seconds, interval_literal) small enough to keep points <= max.

    Returns None if even raw resolution stays under the cap (no aggregation).
    """
    if span_seconds <= 0:
        return None
    raw_points = span_seconds / NATIVE_CADENCE_SECONDS
    if raw_points <= max_points:
        return None
    for secs, literal in _BUCKETS:
        if span_seconds / secs <= max_points:
            return secs, literal
    return _BUCKETS[-1]


def get_latest_per_tag(db: Session, machine_id: int | None = None) -> list[dict]:
    """Latest value for each tag (optionally for one machine)."""
    params: dict = {}
    where = ""
    if machine_id is not None:
        where = "WHERE sr.machine_id = :mid"
        params["mid"] = machine_id

    rows = db.execute(
        text(
            f"""
            SELECT DISTINCT ON (sr.tag_id)
                   sr.machine_id, sr.tag_id, sr.timestamp, sr.value,
                   t.tag_name, t.display_name, t.data_type, t.unit
            FROM sensor_readings sr
            JOIN tags t ON t.id = sr.tag_id
            {where}
            ORDER BY sr.tag_id, sr.timestamp DESC
            """
        ),
        params,
    ).mappings()

    out = []
    for r in rows:
        d = dict(r)
        d["status"] = compute_status(d["tag_name"], d["value"])
        out.append(d)
    return out


def get_trend(
    db: Session,
    machine_id: int,
    tag_id: int,
    start_time: datetime,
    end_time: datetime,
    interval: str | None = None,
) -> dict:
    """Return a time-range-filtered, optionally downsampled trend series.

    ``interval`` (a Postgres interval literal such as '1 minute') forces a bucket
    size. When omitted, a bucket is auto-selected so the response stays within
    MAX_TREND_POINTS.
    """
    span = (end_time - start_time).total_seconds()

    chosen = None
    if interval:
        chosen = (None, interval)  # explicit; trust the caller
    else:
        chosen = _choose_bucket(span, MAX_TREND_POINTS)

    base_params = {
        "mid": machine_id,
        "tid": tag_id,
        "start": start_time,
        "end": end_time,
    }

    if chosen is not None:
        interval_literal = chosen[1]
        # date_bin is native PostgreSQL (14+) and works with or without the
        # TimescaleDB extension, so trends aggregate correctly on plain Postgres.
        rows = db.execute(
            text(
                """
                SELECT date_bin(CAST(:bucket AS interval), timestamp,
                                TIMESTAMPTZ '2000-01-01') AS ts,
                       avg(value) AS avg_v,
                       min(value) AS min_v,
                       max(value) AS max_v
                FROM sensor_readings
                WHERE machine_id = :mid AND tag_id = :tid
                  AND timestamp >= :start AND timestamp <= :end
                GROUP BY ts
                ORDER BY ts
                """
            ),
            {**base_params, "bucket": interval_literal},
        ).mappings()
        points = [
            {
                "timestamp": r["ts"],
                "value": float(r["avg_v"]) if r["avg_v"] is not None else None,
                "min": float(r["min_v"]) if r["min_v"] is not None else None,
                "max": float(r["max_v"]) if r["max_v"] is not None else None,
            }
            for r in rows
        ]
        aggregated = True
    else:
        interval_literal = None
        rows = db.execute(
            text(
                """
                SELECT timestamp AS ts, value
                FROM sensor_readings
                WHERE machine_id = :mid AND tag_id = :tid
                  AND timestamp >= :start AND timestamp <= :end
                ORDER BY timestamp
                LIMIT :lim
                """
            ),
            {**base_params, "lim": MAX_TREND_POINTS + 1},
        ).mappings()
        points = [
            {"timestamp": r["ts"], "value": float(r["value"]), "min": None, "max": None}
            for r in rows
        ]
        aggregated = False

    return {
        "aggregated": aggregated,
        "interval": interval_literal,
        "points": points,
        "point_count": len(points),
    }


def get_summary(db: Session, machine_id: int) -> list[dict]:
    """Per-tag current value + full-history stats + status, in a single round trip.

    Powers the KPI cards and the tag table without 15 separate requests. Each tag's
    aggregate and latest value are computed via LATERAL subqueries served by the
    (tag_id, timestamp DESC) index.
    """
    rows = db.execute(
        text(
            """
            SELECT t.id AS tag_id, t.tag_name, t.display_name, t.data_type, t.unit,
                   s.n, s.mn, s.mx, s.av, s.sd,
                   l.value AS current, l.timestamp AS current_ts
            FROM tags t
            LEFT JOIN LATERAL (
                SELECT count(*) AS n, min(value) AS mn, max(value) AS mx,
                       avg(value) AS av, stddev_pop(value) AS sd
                FROM sensor_readings sr
                WHERE sr.tag_id = t.id AND sr.machine_id = :mid
            ) s ON TRUE
            LEFT JOIN LATERAL (
                SELECT value, timestamp
                FROM sensor_readings sr
                WHERE sr.tag_id = t.id AND sr.machine_id = :mid
                ORDER BY timestamp DESC
                LIMIT 1
            ) l ON TRUE
            WHERE t.machine_id = :mid
            ORDER BY t.id
            """
        ),
        {"mid": machine_id},
    ).mappings()

    def _f(v):
        return float(v) if v is not None else None

    out = []
    for r in rows:
        current = _f(r["current"])
        out.append(
            {
                "tag_id": r["tag_id"],
                "tag_name": r["tag_name"],
                "display_name": r["display_name"],
                "data_type": r["data_type"],
                "unit": r["unit"],
                "current": current,
                "current_timestamp": r["current_ts"],
                "minimum": _f(r["mn"]),
                "maximum": _f(r["mx"]),
                "average": _f(r["av"]),
                "stddev": _f(r["sd"]),
                "count": int(r["n"]) if r["n"] is not None else 0,
                "status": compute_status(r["tag_name"], current),
            }
        )
    return out


def get_statistics(
    db: Session,
    machine_id: int,
    tag_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> dict:
    """Aggregate statistics for a tag over an optional time range."""
    clauses = ["machine_id = :mid", "tag_id = :tid"]
    params: dict = {"mid": machine_id, "tid": tag_id}
    if start_time is not None:
        clauses.append("timestamp >= :start")
        params["start"] = start_time
    if end_time is not None:
        clauses.append("timestamp <= :end")
        params["end"] = end_time
    where = " AND ".join(clauses)

    agg = db.execute(
        text(
            f"""
            SELECT count(*) AS n,
                   min(value) AS mn,
                   max(value) AS mx,
                   avg(value) AS av,
                   stddev_pop(value) AS sd
            FROM sensor_readings
            WHERE {where}
            """
        ),
        params,
    ).mappings().first()

    current = db.execute(
        text(
            f"""
            SELECT timestamp AS ts, value
            FROM sensor_readings
            WHERE {where}
            ORDER BY timestamp DESC
            LIMIT 1
            """
        ),
        params,
    ).mappings().first()

    def _f(v):
        return float(v) if v is not None else None

    current_value = _f(current["value"]) if current else None

    return {
        "current": current_value,
        "current_timestamp": current["ts"] if current else None,
        "minimum": _f(agg["mn"]) if agg else None,
        "maximum": _f(agg["mx"]) if agg else None,
        "average": _f(agg["av"]) if agg else None,
        "stddev": _f(agg["sd"]) if agg else None,
        "count": int(agg["n"]) if agg else 0,
    }
