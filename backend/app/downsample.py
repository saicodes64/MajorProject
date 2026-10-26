"""Time-bucket downsampling for MetroPT-3 ingestion.

Phase 1 ingested the raw ~10 s cadence, producing ~22.7M readings. For the
monitoring dashboard that is unnecessarily large. We downsample the raw CSV to a
fixed time bucket BEFORE loading, targeting ~2-3M readings while preserving:

  * full timestamp coverage (every bucket with data across Feb-Sep 2020),
  * all 15 industrial tags,
  * analog trends  -> bucket MEAN (smooths 10 s jitter, keeps the shape),
  * digital state   -> bucket MAJORITY vote (round(mean) of the 0/1 signal).

The raw CSV is never modified; this is a read-only transform.

Boundary correctness: the CSV is chronological, so we read it in chunks and
carry the trailing (possibly incomplete) bucket forward to the next chunk, so no
bucket is ever split across two chunks. The full file is never held in memory.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from app.config import CHUNK_SIZE
from app.tag_definitions import (
    ANALOG_COLUMNS,
    DIGITAL_COLUMNS,
    SIGNAL_COLUMNS,
    TIMESTAMP_COLUMN,
)

# Default pandas offset alias for the bucket size. Chosen (see estimate script)
# so the result lands in the ~2-3M reading target.
DEFAULT_INTERVAL = "90s"

_AGG = {**{c: "mean" for c in ANALOG_COLUMNS}, **{c: "mean" for c in DIGITAL_COLUMNS}}


def _aggregate(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Bucket a wide DataFrame (indexed by '_ts') and aggregate per tag.

    Analog -> mean; digital -> majority (round of the mean), kept as 0.0/1.0.
    Returns a wide DataFrame with a 'timestamp' column (the bucket start).
    """
    bucket = df["_ts"].dt.floor(interval)
    grouped = df.groupby(bucket, sort=True)
    agg = grouped[SIGNAL_COLUMNS].mean()
    # Digital signals: collapse the averaged 0/1 back to a discrete majority state.
    for c in DIGITAL_COLUMNS:
        agg[c] = agg[c].round().clip(0, 1)
    agg = agg.reset_index(names="timestamp")
    return agg


def iter_downsampled_chunks(
    csv_path: Path, interval: str = DEFAULT_INTERVAL, chunk_size: int = CHUNK_SIZE
) -> Iterator[pd.DataFrame]:
    """Yield wide, downsampled chunks (columns: timestamp + 15 signals).

    Handles bucket boundaries via a carry buffer so no bucket is split.
    """
    usecols = [TIMESTAMP_COLUMN] + SIGNAL_COLUMNS
    carry: pd.DataFrame | None = None

    for chunk in pd.read_csv(csv_path, chunksize=chunk_size, usecols=usecols):
        ts = pd.to_datetime(chunk[TIMESTAMP_COLUMN], errors="coerce")
        chunk = chunk.assign(_ts=ts).dropna(subset=["_ts"])
        if chunk.empty:
            continue
        if carry is not None and not carry.empty:
            chunk = pd.concat([carry, chunk], ignore_index=True)

        buckets = chunk["_ts"].dt.floor(interval)
        last_bucket = buckets.iloc[-1]
        # Rows in the last (still-open) bucket are held back for the next chunk.
        carry = chunk[buckets == last_bucket]
        complete = chunk[buckets < last_bucket]
        if not complete.empty:
            yield _aggregate(complete, interval)

    if carry is not None and not carry.empty:
        yield _aggregate(carry, interval)


def estimate(
    csv_path: Path, intervals: list[str], chunk_size: int = CHUNK_SIZE
) -> dict:
    """Count raw rows and, per candidate interval, the resulting bucket count.

    Reads the CSV once, maintaining a set of distinct floored timestamps per
    interval. Writes nothing. Returns a report dict.
    """
    usecols = [TIMESTAMP_COLUMN]
    raw_rows = 0
    bad_ts = 0
    bucket_sets: dict[str, set] = {iv: set() for iv in intervals}
    ts_min = None
    ts_max = None

    for chunk in pd.read_csv(csv_path, chunksize=chunk_size, usecols=usecols):
        raw_rows += len(chunk)
        ts = pd.to_datetime(chunk[TIMESTAMP_COLUMN], errors="coerce")
        bad_ts += int(ts.isna().sum())
        ts = ts.dropna()
        if ts.empty:
            continue
        cmin, cmax = ts.min(), ts.max()
        ts_min = cmin if ts_min is None else min(ts_min, cmin)
        ts_max = cmax if ts_max is None else max(ts_max, cmax)
        for iv in intervals:
            # store as int64 ns to keep the set small/fast
            bucket_sets[iv].update(ts.dt.floor(iv).astype("int64").unique().tolist())

    n_tags = len(SIGNAL_COLUMNS)
    raw_readings = raw_rows * n_tags
    per_interval = []
    for iv in intervals:
        buckets = len(bucket_sets[iv])
        readings = buckets * n_tags
        per_interval.append(
            {
                "interval": iv,
                "buckets": buckets,
                "readings": readings,
                "reduction_pct": round(100 * (1 - readings / raw_readings), 2)
                if raw_readings
                else 0.0,
            }
        )

    return {
        "raw_rows": raw_rows,
        "unparseable_timestamps": bad_ts,
        "tags": n_tags,
        "raw_readings": raw_readings,
        "timestamp_min": None if ts_min is None else ts_min.isoformat(),
        "timestamp_max": None if ts_max is None else ts_max.isoformat(),
        "candidates": per_interval,
    }
