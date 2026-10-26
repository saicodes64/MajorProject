"""Health / connectivity checks."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session


def check_health(db: Session) -> dict:
    """Probe the database and return a health payload.

    Never raises on DB failure — returns a degraded payload so /api/health can
    still answer and the frontend can show a disconnected state.
    """
    result = {
        "status": "error",
        "database": "unavailable",
        "timescaledb": False,
        "reading_count": None,
        "latest_data_timestamp": None,
        "server_time": datetime.now(timezone.utc),
    }
    try:
        db.execute(text("SELECT 1"))
        result["database"] = "connected"

        ts_row = db.execute(
            text(
                "SELECT extname FROM pg_extension WHERE extname = 'timescaledb'"
            )
        ).first()
        result["timescaledb"] = ts_row is not None

        agg = db.execute(
            text("SELECT count(*) AS n, max(timestamp) AS mx FROM sensor_readings")
        ).mappings().first()
        result["reading_count"] = int(agg["n"]) if agg else 0
        result["latest_data_timestamp"] = agg["mx"] if agg else None

        result["status"] = "ok"
    except Exception:
        # Leave the degraded defaults in place.
        pass
    return result


def latest_data_timestamp(db: Session) -> datetime | None:
    return db.execute(
        text("SELECT max(timestamp) FROM sensor_readings")
    ).scalar()
