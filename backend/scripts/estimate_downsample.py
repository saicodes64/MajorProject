#!/usr/bin/env python3
"""Report the expected reduction from downsampling BEFORE ingesting.

Reads the raw MetroPT-3 CSV once (chunked, writes nothing) and prints, for a set
of candidate time buckets, how many readings would result and the reduction vs
the raw ~22.7M-reading ingestion. Use this to pick DOWNSAMPLE_INTERVAL.

Run from backend/:
    python scripts/estimate_downsample.py [interval ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import METROPT_SOURCE
from app.dataset import locate_dataset
from app.downsample import estimate

DEFAULT_CANDIDATES = ["30s", "60s", "90s", "120s", "300s"]
TARGET_LOW, TARGET_HIGH = 2_000_000, 3_000_000


def main() -> None:
    intervals = sys.argv[1:] or DEFAULT_CANDIDATES
    csv_path = locate_dataset(METROPT_SOURCE or None)
    print(f"[estimate] Source: {csv_path}")
    print(f"[estimate] Candidate intervals: {intervals}\n")

    rep = estimate(csv_path, intervals)

    print("=" * 72)
    print("DOWNSAMPLING REDUCTION ESTIMATE")
    print("=" * 72)
    print(f"Raw rows (timestamps)   : {rep['raw_rows']:,}")
    print(f"Tags per row            : {rep['tags']}")
    print(f"Raw readings (current)  : {rep['raw_readings']:,}")
    print(f"Timestamp coverage      : {rep['timestamp_min']} -> {rep['timestamp_max']}")
    print(f"Target band             : {TARGET_LOW:,} - {TARGET_HIGH:,} readings")
    print("-" * 72)
    print(f"{'interval':>10} {'buckets(rows)':>16} {'readings':>16} "
          f"{'reduction':>11}  in-target")
    for c in rep["candidates"]:
        in_target = TARGET_LOW <= c["readings"] <= TARGET_HIGH
        mark = "  <== YES" if in_target else ""
        print(f"{c['interval']:>10} {c['buckets']:>16,} {c['readings']:>16,} "
              f"{c['reduction_pct']:>10}%{mark}")
    print("=" * 72)

    in_band = [c for c in rep["candidates"] if TARGET_LOW <= c["readings"] <= TARGET_HIGH]
    if in_band:
        best = min(in_band, key=lambda c: abs(c["readings"] - (TARGET_LOW + TARGET_HIGH) / 2))
        print(f"\nRecommended interval: {best['interval']} "
              f"(~{best['readings']:,} readings, {best['reduction_pct']}% reduction)")
        print(f"Set it with:  DOWNSAMPLE_INTERVAL={best['interval']}  in .env")
    else:
        print("\nNo candidate landed in the target band; try other intervals as args.")


if __name__ == "__main__":
    main()
