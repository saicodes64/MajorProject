#!/usr/bin/env python3
"""Ingest the MetroPT-3 CSV into the tag-oriented TimescaleDB schema.

Pipeline:
  locate -> (extract) -> validate structure -> ensure schema ->
  upsert machine -> upsert tags -> chunked wide->long transform ->
  batched ON CONFLICT DO NOTHING inserts -> report.

Design notes:
  * Chunked reading (CHUNK_SIZE) — the full CSV is never loaded into memory.
  * Idempotent / safely re-runnable — the composite PK (timestamp, machine_id,
    tag_id) plus ON CONFLICT DO NOTHING means re-running never duplicates. For
    efficiency we also resume past the latest already-ingested timestamp.
  * Invalid rows (unparseable timestamp, non-numeric value) are counted and
    skipped rather than aborting the run.

Run from backend/:
    python scripts/ingest_metropt.py [optional/path/to/dataset.csv|.zip]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
from psycopg2.extras import execute_values
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import (
    CHUNK_SIZE,
    DOWNSAMPLE_ENABLED,
    DOWNSAMPLE_INTERVAL,
    INSERT_BATCH_SIZE,
    METROPT_SOURCE,
)
from app.database import get_engine
from app.database.schema import create_schema
from app.dataset import locate_dataset
from app.downsample import iter_downsampled_chunks
from app.tag_definitions import MACHINE, SIGNAL_COLUMNS, TAG_DEFINITIONS, TIMESTAMP_COLUMN


def upsert_machine(engine) -> int:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO machines (machine_code, name, machine_type, location, description)
                VALUES (:code, :name, :mtype, :loc, :descr)
                ON CONFLICT (machine_code) DO UPDATE SET
                    name = EXCLUDED.name,
                    machine_type = EXCLUDED.machine_type,
                    location = EXCLUDED.location,
                    description = EXCLUDED.description
                """
            ),
            {
                "code": MACHINE["machine_code"],
                "name": MACHINE["name"],
                "mtype": MACHINE["machine_type"],
                "loc": MACHINE["location"],
                "descr": MACHINE["description"],
            },
        )
        machine_id = conn.execute(
            text("SELECT id FROM machines WHERE machine_code = :code"),
            {"code": MACHINE["machine_code"]},
        ).scalar_one()
    print(f"[ingest] Machine '{MACHINE['machine_code']}' id={machine_id}")
    return machine_id


def upsert_tags(engine, machine_id: int) -> dict[str, int]:
    tag_ids: dict[str, int] = {}
    with engine.begin() as conn:
        for t in TAG_DEFINITIONS:
            conn.execute(
                text(
                    """
                    INSERT INTO tags
                        (machine_id, tag_name, display_name, data_type, unit, description)
                    VALUES (:mid, :tag, :disp, :dtype, :unit, :descr)
                    ON CONFLICT (machine_id, tag_name) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        data_type = EXCLUDED.data_type,
                        unit = EXCLUDED.unit,
                        description = EXCLUDED.description
                    """
                ),
                {
                    "mid": machine_id,
                    "tag": t["tag_name"],
                    "disp": t["display_name"],
                    "dtype": t["data_type"],
                    "unit": t["unit"],
                    "descr": t["description"],
                },
            )
        rows = conn.execute(
            text("SELECT id, tag_name FROM tags WHERE machine_id = :mid"),
            {"mid": machine_id},
        ).all()
    for rid, name in rows:
        tag_ids[name] = rid
    print(f"[ingest] {len(tag_ids)} tags ensured: {list(tag_ids.keys())}")
    return tag_ids


def latest_ingested_ts(engine, machine_id: int):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT max(timestamp) FROM sensor_readings WHERE machine_id = :mid"),
            {"mid": machine_id},
        ).scalar()


def validate_structure(csv_path: Path) -> list[str]:
    header = pd.read_csv(csv_path, nrows=0)
    cols = list(header.columns)
    if TIMESTAMP_COLUMN not in cols:
        raise ValueError(
            f"Required column '{TIMESTAMP_COLUMN}' not found. Columns: {cols}"
        )
    missing = [c for c in SIGNAL_COLUMNS if c not in cols]
    if missing:
        raise ValueError(
            f"Dataset is missing expected signal columns: {missing}. "
            f"Found columns: {cols}"
        )
    return cols


def _iter_source_chunks(csv_path: Path):
    """Yield wide chunks with a '_ts' datetime column + the signal columns.

    Branches on DOWNSAMPLE_ENABLED:
      * downsampled -> time-bucketed chunks (analog mean / digital majority),
        timestamps already clean; returns (df, bad_ts=0).
      * raw         -> raw ~10s rows with unparseable timestamps dropped/counted.
    """
    if DOWNSAMPLE_ENABLED:
        for df in iter_downsampled_chunks(csv_path, DOWNSAMPLE_INTERVAL, CHUNK_SIZE):
            df = df.rename(columns={"timestamp": "_ts"})
            yield df, 0
    else:
        usecols = [TIMESTAMP_COLUMN] + SIGNAL_COLUMNS
        for chunk in pd.read_csv(csv_path, chunksize=CHUNK_SIZE, usecols=usecols):
            ts = pd.to_datetime(chunk[TIMESTAMP_COLUMN], errors="coerce")
            bad = int(ts.isna().sum())
            chunk = chunk.assign(_ts=ts).dropna(subset=["_ts"]).drop(columns=[TIMESTAMP_COLUMN])
            yield chunk, bad


def insert_batch(raw_conn, rows) -> int:
    """Insert a list of (timestamp, machine_id, tag_id, value) tuples."""
    if not rows:
        return 0
    with raw_conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO sensor_readings (timestamp, machine_id, tag_id, value)
            VALUES %s
            ON CONFLICT (timestamp, machine_id, tag_id) DO NOTHING
            """,
            rows,
            page_size=10000,
        )
    raw_conn.commit()
    return len(rows)


def ingest(csv_path: Path) -> dict:
    engine = get_engine()

    print("[ingest] Ensuring schema / hypertable ...")
    create_schema(engine, verbose=True)

    cols = validate_structure(csv_path)
    print(f"[ingest] Source validated. Columns: {cols}")

    machine_id = upsert_machine(engine)
    tag_ids = upsert_tags(engine, machine_id)

    resume_after = latest_ingested_ts(engine, machine_id)
    if resume_after is not None:
        print(f"[ingest] Existing data found; resuming AFTER {resume_after} "
              "(already-ingested rows are skipped).")
    else:
        print("[ingest] No existing data; ingesting from the beginning.")

    # Map tag column -> tag_id once.
    col_to_tag = {t["csv_column"]: tag_ids[t["tag_name"]] for t in TAG_DEFINITIONS}

    raw_conn = engine.raw_connection()
    start = time.time()
    rows_read = 0
    rows_considered = 0
    readings_inserted = 0
    bad_timestamps = 0
    bad_values = 0
    pending: list[tuple] = []

    if DOWNSAMPLE_ENABLED:
        print(f"[ingest] Downsampling ENABLED: {DOWNSAMPLE_INTERVAL} buckets "
              "(analog=mean, digital=majority).")
    else:
        print("[ingest] Downsampling DISABLED: ingesting raw resolution.")

    try:
        for ci, (chunk, bad_ts) in enumerate(_iter_source_chunks(csv_path)):
            rows_read += len(chunk)
            bad_timestamps += bad_ts

            # Resume: skip rows at/before the last ingested timestamp.
            if resume_after is not None:
                cutoff = pd.Timestamp(resume_after)
                if cutoff.tzinfo is not None:
                    cutoff = cutoff.tz_localize(None)
                chunk = chunk[chunk["_ts"] > cutoff]
            if chunk.empty:
                print(f"  .. chunk {ci + 1}: skipped (already ingested)", end="\r")
                continue

            rows_considered += len(chunk)

            # Wide -> long. Build (timestamp, machine_id, tag_id, value) tuples.
            long = chunk.melt(
                id_vars=["_ts"],
                value_vars=SIGNAL_COLUMNS,
                var_name="col",
                value_name="value",
            )
            long["value"] = pd.to_numeric(long["value"], errors="coerce")
            before = len(long)
            long = long.dropna(subset=["value"])
            bad_values += before - len(long)
            long["tag_id"] = long["col"].map(col_to_tag)

            ts_list = long["_ts"].dt.to_pydatetime()
            tag_list = long["tag_id"].tolist()
            val_list = long["value"].tolist()
            pending.extend(
                (ts_list[i], machine_id, tag_list[i], val_list[i])
                for i in range(len(long))
            )

            # Flush in batches.
            while len(pending) >= INSERT_BATCH_SIZE:
                batch, pending = pending[:INSERT_BATCH_SIZE], pending[INSERT_BATCH_SIZE:]
                readings_inserted += insert_batch(raw_conn, batch)

            elapsed = time.time() - start
            rate = readings_inserted / elapsed if elapsed else 0
            print(f"  .. chunk {ci + 1}: rows_read={rows_read:,} "
                  f"readings_inserted={readings_inserted:,} "
                  f"({rate:,.0f}/s)", end="\r")

        # Flush remainder.
        if pending:
            readings_inserted += insert_batch(raw_conn, pending)
    finally:
        raw_conn.close()

    print()
    elapsed = time.time() - start
    summary = {
        "source_file": str(csv_path),
        "downsample_enabled": DOWNSAMPLE_ENABLED,
        "downsample_interval": DOWNSAMPLE_INTERVAL if DOWNSAMPLE_ENABLED else None,
        "rows_read": rows_read,
        "rows_considered": rows_considered,
        "readings_inserted_or_skipped": readings_inserted,
        "bad_timestamps_skipped": bad_timestamps,
        "non_numeric_values_skipped": bad_values,
        "elapsed_seconds": round(elapsed, 1),
        "machine_id": machine_id,
        "tag_count": len(tag_ids),
    }
    print("\n[ingest] DONE")
    for k, v in summary.items():
        print(f"  {k:<30}: {v}")
    print("\nNote: 'readings_inserted_or_skipped' counts rows sent to the DB; "
          "duplicates are silently ignored by ON CONFLICT DO NOTHING.")
    return summary


def main() -> None:
    explicit = sys.argv[1] if len(sys.argv) > 1 else (METROPT_SOURCE or None)
    csv_path = locate_dataset(explicit)
    ingest(csv_path)


if __name__ == "__main__":
    main()
