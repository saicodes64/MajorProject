"""Shared / misc response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    status: str = Field(..., description="'ok' when the API and DB are reachable.")
    database: str = Field(..., description="'connected' or 'unavailable'.")
    timescaledb: bool = Field(..., description="Whether the TimescaleDB extension is active.")
    reading_count: int | None = Field(
        None, description="Total rows in sensor_readings (None if DB unavailable)."
    )
    latest_data_timestamp: datetime | None = Field(
        None,
        description=(
            "Most recent timestamp present in the data. The frontend anchors its "
            "relative time ranges (last 1h/6h/24h) to this value because the "
            "MetroPT-3 dataset is historical (Feb-Sep 2020)."
        ),
    )
    server_time: datetime = Field(..., description="Current server wall-clock time.")
