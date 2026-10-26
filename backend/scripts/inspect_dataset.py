#!/usr/bin/env python3
"""MetroPT-3 dataset inspection & validation.

Reads the raw CSV in chunks (never loads it fully into memory) and produces:
  * data/processed/dataset_report.json  (machine-readable)
  * a readable console summary

It verifies the ACTUAL file structure rather than assuming it. Nothing here is
hardcoded about column meaning beyond matching the documented signal names from
app.tag_definitions (which come straight from the official documentation).

Run from the backend/ directory:
    python scripts/inspect_dataset.py [optional/path/to/dataset.csv|.zip]
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Make `app` importable when run as a script from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import CHUNK_SIZE, METROPT_SOURCE, REPORT_PATH, PROCESSED_DIR
from app.dataset import locate_dataset
from app.tag_definitions import (
    ANALOG_COLUMNS,
    DIGITAL_COLUMNS,
    SIGNAL_COLUMNS,
    TIMESTAMP_COLUMN,
)


def _json_safe(value):
    """Convert numpy/pandas scalars to plain JSON-serialisable Python types."""
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        f = float(value)
        return None if math.isnan(f) else f
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def inspect(csv_path: Path) -> dict:
    print(f"[inspect] Source file: {csv_path}")
    print(f"[inspect] Size: {csv_path.stat().st_size / (1024 * 1024):.1f} MB")

    # --- Header / columns (read just one row) ---
    header_df = pd.read_csv(csv_path, nrows=1)
    columns = list(header_df.columns)
    print(f"[inspect] Columns ({len(columns)}): {columns}")

    # Identify the unnamed index column (empty / 'Unnamed: 0').
    index_like = [c for c in columns if c == "" or str(c).startswith("Unnamed")]

    # --- Accumulators ---
    total_rows = 0
    missing_counts = {c: 0 for c in columns}
    # numeric running stats for signal columns
    num_stats = {
        c: {"min": math.inf, "max": -math.inf, "sum": 0.0, "count": 0,
            "sumsq": 0.0, "non_numeric": 0}
        for c in SIGNAL_COLUMNS
    }
    digital_uniques = {c: set() for c in DIGITAL_COLUMNS}
    ts_min: pd.Timestamp | None = None
    ts_max: pd.Timestamp | None = None
    ts_unparseable = 0
    duplicate_timestamps = 0
    prev_last_ts: pd.Timestamp | None = None
    # sampling interval histogram (seconds -> count)
    interval_counts: dict[float, int] = {}
    seen_ts_duplicates_within_chunk = 0

    dtype_sample = {}

    reader = pd.read_csv(csv_path, chunksize=CHUNK_SIZE)
    for i, chunk in enumerate(reader):
        total_rows += len(chunk)

        # record dtypes once
        if not dtype_sample:
            dtype_sample = {c: str(chunk[c].dtype) for c in chunk.columns}

        # missing values per column
        miss = chunk.isna().sum()
        for c in chunk.columns:
            missing_counts[c] += int(miss[c])

        # timestamps
        if TIMESTAMP_COLUMN in chunk.columns:
            ts = pd.to_datetime(chunk[TIMESTAMP_COLUMN], errors="coerce")
            ts_unparseable += int(ts.isna().sum())
            valid_ts = ts.dropna()
            if not valid_ts.empty:
                cmin, cmax = valid_ts.min(), valid_ts.max()
                ts_min = cmin if ts_min is None else min(ts_min, cmin)
                ts_max = cmax if ts_max is None else max(ts_max, cmax)

                # duplicate timestamps within chunk
                seen_ts_duplicates_within_chunk += int(valid_ts.duplicated().sum())

                # sampling intervals (within chunk + bridge across chunks)
                series = valid_ts.reset_index(drop=True)
                if prev_last_ts is not None:
                    series = pd.concat(
                        [pd.Series([prev_last_ts]), series], ignore_index=True
                    )
                diffs = series.diff().dropna().dt.total_seconds()
                for d in diffs:
                    interval_counts[d] = interval_counts.get(d, 0) + 1
                prev_last_ts = valid_ts.iloc[-1]

        # numeric stats for signal columns
        for c in SIGNAL_COLUMNS:
            if c not in chunk.columns:
                continue
            col = pd.to_numeric(chunk[c], errors="coerce")
            num_stats[c]["non_numeric"] += int(col.isna().sum() - miss[c])
            valid = col.dropna()
            if not valid.empty:
                num_stats[c]["min"] = min(num_stats[c]["min"], float(valid.min()))
                num_stats[c]["max"] = max(num_stats[c]["max"], float(valid.max()))
                num_stats[c]["sum"] += float(valid.sum())
                num_stats[c]["sumsq"] += float((valid**2).sum())
                num_stats[c]["count"] += int(valid.count())

        # digital unique values (bounded; stop collecting if it explodes)
        for c in DIGITAL_COLUMNS:
            if c in chunk.columns and len(digital_uniques[c]) <= 50:
                digital_uniques[c].update(
                    pd.to_numeric(chunk[c], errors="coerce").dropna().unique().tolist()
                )

        print(f"  .. processed chunk {i + 1} "
              f"(rows so far: {total_rows:,})", end="\r")

    print()  # newline after progress

    duplicate_timestamps = seen_ts_duplicates_within_chunk

    # --- Finalise numeric stats ---
    numerical = {}
    for c in SIGNAL_COLUMNS:
        s = num_stats[c]
        if s["count"] > 0:
            mean = s["sum"] / s["count"]
            variance = max(s["sumsq"] / s["count"] - mean**2, 0.0)
            numerical[c] = {
                "min": _json_safe(s["min"]),
                "max": _json_safe(s["max"]),
                "mean": _json_safe(mean),
                "std": _json_safe(math.sqrt(variance)),
                "count": s["count"],
                "non_numeric_values": s["non_numeric"],
            }
        else:
            numerical[c] = {
                "min": None, "max": None, "mean": None, "std": None,
                "count": 0, "non_numeric_values": s["non_numeric"],
            }

    # --- Sampling interval summary ---
    interval_summary = None
    if interval_counts:
        total_intervals = sum(interval_counts.values())
        # dominant (modal) interval
        dominant = max(interval_counts.items(), key=lambda kv: kv[1])
        top = sorted(interval_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        interval_summary = {
            "dominant_interval_seconds": _json_safe(dominant[0]),
            "dominant_interval_pct": round(100 * dominant[1] / total_intervals, 4),
            "distinct_intervals": len(interval_counts),
            "top_intervals_seconds": [
                {"seconds": _json_safe(sec), "count": cnt,
                 "pct": round(100 * cnt / total_intervals, 4)}
                for sec, cnt in top
            ],
            "min_interval_seconds": _json_safe(min(interval_counts)),
            "max_interval_seconds": _json_safe(max(interval_counts)),
        }

    # --- Digital uniques ---
    digital = {
        c: sorted(_json_safe(v) for v in digital_uniques[c])
        for c in DIGITAL_COLUMNS
    }

    # --- Invalid value notes ---
    invalid = {}
    for c in SIGNAL_COLUMNS:
        nn = numerical[c]["non_numeric_values"]
        if nn:
            invalid[c] = {"non_numeric_values": nn}
    if ts_unparseable:
        invalid[TIMESTAMP_COLUMN] = {"unparseable_timestamps": ts_unparseable}

    report = {
        "generated_at": datetime.now().isoformat(),
        "source_file": str(csv_path),
        "file_size_mb": round(csv_path.stat().st_size / (1024 * 1024), 2),
        "row_count": total_rows,
        "column_count": len(columns),
        "columns": columns,
        "index_like_columns": index_like,
        "signal_columns_expected": SIGNAL_COLUMNS,
        "signal_columns_present": [c for c in SIGNAL_COLUMNS if c in columns],
        "signal_columns_missing": [c for c in SIGNAL_COLUMNS if c not in columns],
        "dtypes": dtype_sample,
        "timestamp": {
            "column": TIMESTAMP_COLUMN,
            "min": _json_safe(ts_min),
            "max": _json_safe(ts_max),
            "unparseable_count": ts_unparseable,
            "duplicate_count": int(duplicate_timestamps),
        },
        "missing_values": {c: int(v) for c, v in missing_counts.items()},
        "missing_values_total": int(sum(missing_counts.values())),
        "numerical_statistics": numerical,
        "digital_unique_values": digital,
        "sampling_interval": interval_summary,
        "invalid_values": invalid,
        "analog_columns": ANALOG_COLUMNS,
        "digital_columns": DIGITAL_COLUMNS,
    }
    return report


def print_summary(report: dict) -> None:
    line = "=" * 70
    print("\n" + line)
    print("MetroPT-3 DATASET VALIDATION SUMMARY")
    print(line)
    print(f"Source            : {report['source_file']}")
    print(f"File size         : {report['file_size_mb']} MB")
    print(f"Rows              : {report['row_count']:,}")
    print(f"Columns           : {report['column_count']}")
    print(f"Column names      : {', '.join(report['columns'])}")
    if report["signal_columns_missing"]:
        print(f"!! MISSING signals : {report['signal_columns_missing']}")
    else:
        print("All 15 documented signal columns present : YES")

    ts = report["timestamp"]
    print(f"Timestamp range   : {ts['min']}  ->  {ts['max']}")
    print(f"Unparseable ts    : {ts['unparseable_count']}")
    print(f"Duplicate ts      : {ts['duplicate_count']}")
    print(f"Missing values    : {report['missing_values_total']} total")

    si = report["sampling_interval"]
    if si:
        print(f"Sampling interval : {si['dominant_interval_seconds']}s "
              f"({si['dominant_interval_pct']}% of gaps); "
              f"{si['distinct_intervals']} distinct gap sizes "
              f"(min {si['min_interval_seconds']}s / max {si['max_interval_seconds']}s)")

    print("\nAnalogue signal statistics (min / max / mean):")
    for c in report["analog_columns"]:
        s = report["numerical_statistics"].get(c, {})
        print(f"  {c:<16} min={s.get('min')!s:>12}  "
              f"max={s.get('max')!s:>12}  mean={s.get('mean')!s:>12}")

    print("\nDigital signal unique values:")
    for c in report["digital_columns"]:
        print(f"  {c:<16} {report['digital_unique_values'].get(c)}")

    if report["invalid_values"]:
        print("\nInvalid values detected:")
        for c, info in report["invalid_values"].items():
            print(f"  {c}: {info}")
    else:
        print("\nInvalid values detected: NONE")
    print(line + "\n")


def main() -> None:
    explicit = sys.argv[1] if len(sys.argv) > 1 else (METROPT_SOURCE or None)
    csv_path = locate_dataset(explicit)

    report = inspect(csv_path)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[inspect] Report written to {REPORT_PATH}")

    print_summary(report)


if __name__ == "__main__":
    main()
