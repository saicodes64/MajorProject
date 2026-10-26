"""Reading / trend / statistics response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LatestReadingOut(BaseModel):
    """The most recent value of a single tag."""

    machine_id: int
    tag_id: int
    tag_name: str
    display_name: str | None = None
    data_type: str | None = None
    unit: str | None = None
    timestamp: datetime | None = Field(None, description="Timestamp of the latest value.")
    value: float | None = Field(None, description="Latest value (None if no data).")
    status: str = Field(
        "Monitoring",
        description="Status band (Normal/Warning/Critical/Monitoring). See thresholds config.",
    )


class TrendPoint(BaseModel):
    """A single point in a (possibly aggregated) trend series."""

    timestamp: datetime
    value: float | None = Field(None, description="avg within the bucket, or raw value.")
    min: float | None = Field(None, description="Min within the bucket (aggregated only).")
    max: float | None = Field(None, description="Max within the bucket (aggregated only).")


class TrendResponse(BaseModel):
    machine_id: int
    tag_id: int
    tag_name: str
    display_name: str | None = None
    unit: str | None = None
    start_time: datetime
    end_time: datetime
    aggregated: bool = Field(..., description="True if values are time-bucketed averages.")
    interval: str | None = Field(
        None, description="Aggregation bucket size (e.g. '1 minute'); null if raw."
    )
    point_count: int
    points: list[TrendPoint]


class SummaryItem(BaseModel):
    """Per-tag snapshot: latest value + full-history stats + status, in one shot."""

    tag_id: int
    tag_name: str
    display_name: str | None = None
    data_type: str | None = None
    unit: str | None = None
    current: float | None = None
    current_timestamp: datetime | None = None
    minimum: float | None = None
    maximum: float | None = None
    average: float | None = None
    stddev: float | None = None
    count: int = 0
    status: str = "Monitoring"


class StatisticsOut(BaseModel):
    machine_id: int
    tag_id: int
    tag_name: str
    display_name: str | None = None
    unit: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    current: float | None = Field(None, description="Most recent value in the range.")
    current_timestamp: datetime | None = None
    minimum: float | None = None
    maximum: float | None = None
    average: float | None = None
    stddev: float | None = Field(None, description="Population standard deviation.")
    count: int = 0
    status: str = "Monitoring"
