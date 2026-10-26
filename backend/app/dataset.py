"""Locate (and if necessary extract) the MetroPT-3 source CSV.

Resolution order:
  1. An explicit path (CLI arg or METROPT_SOURCE env var).
  2. Any .csv already present under data/raw/.
  3. Any .zip under data/raw/ -> extracted in place, then its .csv used.

Keeps the dataset entirely inside data/raw/ (which is git-ignored).
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from app.config import RAW_DIR


def _find_csv(directory: Path) -> Path | None:
    csvs = sorted(directory.rglob("*.csv"))
    return csvs[0] if csvs else None


def _extract_zips(directory: Path) -> None:
    for zip_path in sorted(directory.glob("*.zip")):
        print(f"[dataset] Extracting {zip_path.name} ...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(directory)


def locate_dataset(explicit: str | None = None) -> Path:
    """Return the path to the MetroPT-3 CSV, extracting a ZIP if required."""
    # 1. Explicit path
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_absolute():
            # resolve relative to project root for convenience
            from app.config import PROJECT_ROOT

            p = (PROJECT_ROOT / p).resolve()
        if p.is_file() and p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p) as zf:
                zf.extractall(p.parent)
            csv = _find_csv(p.parent)
            if csv:
                return csv
        if p.is_file():
            return p
        raise FileNotFoundError(f"Specified dataset path does not exist: {p}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 2. CSV already present
    csv = _find_csv(RAW_DIR)
    if csv:
        return csv

    # 3. Extract ZIPs then look again
    _extract_zips(RAW_DIR)
    csv = _find_csv(RAW_DIR)
    if csv:
        return csv

    raise FileNotFoundError(
        f"No MetroPT-3 CSV/ZIP found. Place the dataset in {RAW_DIR} or set "
        "METROPT_SOURCE to its path."
    )
