#!/usr/bin/env python3
"""Verify the ingested MetroPT-3 data in PostgreSQL + TimescaleDB.

Confirms the database holds REAL MetroPT-3 data (not generated) by reporting:
counts, timestamp range, per-tag readings, sample records, min/max per tag,
missing-data checks, and hypertable / index status.

Run from backend/:
    python scripts/verify_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import get_engine


def section(title: str) -> None:
    print("\n" + "-" * 70)
    print(title)
    print("-" * 70)


def main() -> None:
    engine = get_engine()
    with engine.connect() as conn:
        section("COUNTS")
        machines = conn.execute(text("SELECT count(*) FROM machines")).scalar()
        tags = conn.execute(text("SELECT count(*) FROM tags")).scalar()
        readings = conn.execute(text("SELECT count(*) FROM sensor_readings")).scalar()
        print(f"machines         : {machines}")
        print(f"tags             : {tags}")
        print(f"sensor_readings  : {readings:,}")

        section("MACHINES")
        for row in conn.execute(text(
            "SELECT id, machine_code, name, machine_type, location FROM machines ORDER BY id"
        )):
            print(f"  [{row.id}] {row.machine_code} | {row.name} | "
                  f"{row.machine_type} | {row.location}")

        section("TIMESTAMP RANGE")
        rng = conn.execute(text(
            "SELECT min(timestamp) AS mn, max(timestamp) AS mx FROM sensor_readings"
        )).one()
        print(f"earliest : {rng.mn}")
        print(f"latest   : {rng.mx}")

        section("READINGS PER TAG (with min / max / avg)")
        rows = conn.execute(text(
            """
            SELECT t.tag_name, t.display_name, t.data_type, t.unit,
                   count(sr.*) AS n,
                   min(sr.value) AS vmin, max(sr.value) AS vmax, avg(sr.value) AS vavg
            FROM tags t
            LEFT JOIN sensor_readings sr ON sr.tag_id = t.id
            GROUP BY t.id, t.tag_name, t.display_name, t.data_type, t.unit
            ORDER BY t.id
            """
        ))
        print(f"  {'tag':<16}{'type':<9}{'unit':<6}{'count':>12}"
              f"{'min':>12}{'max':>12}{'avg':>12}")
        for r in rows:
            unit = r.unit or "-"
            avg = f"{r.vavg:.3f}" if r.vavg is not None else "-"
            vmin = f"{r.vmin:.3f}" if r.vmin is not None else "-"
            vmax = f"{r.vmax:.3f}" if r.vmax is not None else "-"
            print(f"  {r.tag_name:<16}{r.data_type:<9}{unit:<6}{r.n:>12,}"
                  f"{vmin:>12}{vmax:>12}{avg:>12}")

        section("MISSING-DATA CHECK")
        # Expected readings per tag = distinct timestamps (each tag sampled together).
        distinct_ts = conn.execute(text(
            "SELECT count(DISTINCT timestamp) FROM sensor_readings"
        )).scalar()
        print(f"distinct timestamps         : {distinct_ts:,}")
        expected = distinct_ts * tags if distinct_ts else 0
        print(f"expected readings (ts*tags) : {expected:,}")
        print(f"actual readings             : {readings:,}")
        gap = expected - readings
        print(f"gap (expected - actual)     : {gap:,}"
              + ("  (complete)" if gap == 0 else "  (some tag/ts values absent)"))

        section("SAMPLE RECORDS (earliest 10, joined)")
        for r in conn.execute(text(
            """
            SELECT sr.timestamp, m.machine_code, t.tag_name, t.unit, sr.value
            FROM sensor_readings sr
            JOIN machines m ON m.id = sr.machine_id
            JOIN tags t ON t.id = sr.tag_id
            ORDER BY sr.timestamp, t.id
            LIMIT 10
            """
        )):
            unit = f" {r.unit}" if r.unit else ""
            print(f"  {r.timestamp} | {r.machine_code} | {r.tag_name:<16} = "
                  f"{r.value}{unit}")

        section("TIMESCALEDB HYPERTABLE STATUS")
        try:
            ht = conn.execute(text(
                """
                SELECT hypertable_name, num_chunks
                FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'sensor_readings'
                """
            )).first()
            if ht:
                print(f"hypertable       : {ht.hypertable_name}")
                print(f"chunks           : {ht.num_chunks}")
                comp = conn.execute(text(
                    """
                    SELECT count(*) FILTER (WHERE is_compressed) AS compressed,
                           count(*) AS total
                    FROM timescaledb_information.chunks
                    WHERE hypertable_name = 'sensor_readings'
                    """
                )).first()
                print(f"compressed chunks: {comp.compressed} / {comp.total}")
            else:
                print("sensor_readings is NOT a hypertable "
                      "(TimescaleDB may be unavailable).")
        except Exception as exc:
            print(f"Hypertable info unavailable: {exc}")

        section("INDEXES ON sensor_readings")
        for r in conn.execute(text(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'sensor_readings' ORDER BY indexname
            """
        )):
            print(f"  {r.indexname}")

    print("\nVerification complete.\n")


if __name__ == "__main__":
    main()
