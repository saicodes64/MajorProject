"""Schema creation: ORM tables + TimescaleDB hypertable, indexes and policies.

Idempotent and safe to run repeatedly. If the TimescaleDB extension is not
available the script still creates the plain PostgreSQL tables (readings will
work, just without hypertable acceleration) and warns.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.models import Base


def timescaledb_available(engine: Engine) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'"
            )
        ).first()
    return row is not None


def create_schema(engine: Engine, verbose: bool = True) -> dict:
    """Create all tables, the hypertable, indexes and policies. Returns status."""
    status = {"timescaledb": False, "hypertable": False, "compression": False}

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    has_ts = timescaledb_available(engine)
    if has_ts:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        status["timescaledb"] = True
        log("[schema] TimescaleDB extension ensured.")
    else:
        log("[schema] WARNING: TimescaleDB extension not available; "
            "creating plain PostgreSQL tables only.")

    # Create tables from the ORM metadata (machines, tags, sensor_readings).
    Base.metadata.create_all(engine)
    log("[schema] Tables created (machines, tags, sensor_readings).")

    if has_ts:
        with engine.begin() as conn:
            # Convert sensor_readings into a hypertable on the time dimension.
            conn.execute(
                text(
                    "SELECT create_hypertable('sensor_readings', 'timestamp', "
                    "if_not_exists => TRUE, migrate_data => TRUE)"
                )
            )
            status["hypertable"] = True
            log("[schema] sensor_readings is now a hypertable (time = timestamp).")

    # Indexes to optimise the required query patterns. These complement the
    # composite PK (machine_id, tag_id, timestamp).
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_readings_machine_tag_time "
                "ON sensor_readings (machine_id, tag_id, timestamp DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_readings_tag_time "
                "ON sensor_readings (tag_id, timestamp DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_readings_machine_time "
                "ON sensor_readings (machine_id, timestamp DESC)"
            )
        )
    log("[schema] Indexes ensured (machine+tag+time, tag+time, machine+time).")

    if has_ts:
        # Compression is genuinely useful here: the dataset is static historical
        # data, highly compressible, and segmenting by tag keeps per-tag scans
        # fast. Compress chunks older than 7 days.
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE sensor_readings SET ("
                        "timescaledb.compress, "
                        "timescaledb.compress_segmentby = 'machine_id, tag_id', "
                        "timescaledb.compress_orderby = 'timestamp DESC')"
                    )
                )
                conn.execute(
                    text(
                        "SELECT add_compression_policy('sensor_readings', "
                        "INTERVAL '7 days', if_not_exists => TRUE)"
                    )
                )
            status["compression"] = True
            log("[schema] Compression enabled (segment by machine_id, tag_id; "
                "policy: chunks older than 7 days).")
        except Exception as exc:  # pragma: no cover - older TS versions
            log(f"[schema] Compression not enabled: {exc}")

    return status


if __name__ == "__main__":
    from app.database import get_engine

    result = create_schema(get_engine())
    print(f"[schema] Done: {result}")
