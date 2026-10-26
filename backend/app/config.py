"""Centralised configuration loaded from environment variables / .env.

No credentials are hardcoded. Values come from the process environment, falling
back to the project-local ``.env`` file when present.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# backend/app/config.py -> project root is three levels up.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Load .env from the project root if it exists (does not override real env vars).
load_dotenv(PROJECT_ROOT / ".env")


def _require(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Required environment variable '{name}' is not set.")
    return value


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
POSTGRES_USER = os.getenv("POSTGRES_USER", "iiot")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "iiot_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "iiot_platform")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

# ---------------------------------------------------------------------------
# Dataset / ingestion
# ---------------------------------------------------------------------------
METROPT_SOURCE = os.getenv("METROPT_SOURCE", "")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "100000"))
INSERT_BATCH_SIZE = int(os.getenv("INSERT_BATCH_SIZE", "10000"))

# Downsampling: aggregate the raw ~10s cadence into fixed time buckets before
# ingestion, targeting ~2-3M readings (see scripts/estimate_downsample.py).
# Set DOWNSAMPLE_ENABLED=false to ingest the full raw resolution instead.
DOWNSAMPLE_ENABLED = os.getenv("DOWNSAMPLE_ENABLED", "true").lower() in {"1", "true", "yes"}
DOWNSAMPLE_INTERVAL = os.getenv("DOWNSAMPLE_INTERVAL", "90s")

REPORT_PATH = PROCESSED_DIR / "dataset_report.json"

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
API_TITLE = "IIoT Monitoring Platform API"
API_VERSION = "1.0.0"
# Comma-separated list of allowed CORS origins for the React dev server.
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]
# Safety cap: max raw points returned by the trend endpoint before aggregation
# is forced. Protects the browser from the 1.5M-row dataset.
MAX_TREND_POINTS = int(os.getenv("MAX_TREND_POINTS", "2000"))
