"""SensorReading model — the main time-series fact table.

Narrow, tag-oriented design: one row = one (machine, tag) value at one instant.
This becomes a TimescaleDB hypertable partitioned on ``timestamp``.

Note on keys: a TimescaleDB hypertable requires any unique/primary key to include
the partitioning column. We therefore use a composite primary key of
(machine_id, tag_id, timestamp). This also gives us natural idempotency: re-running
ingestion uses ON CONFLICT DO NOTHING against this key so duplicates are skipped.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    # Generic numeric value. Analogue measurements and digital 0/1 states both
    # fit a single double-precision column, keeping the model source-agnostic.
    value: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<SensorReading m={self.machine_id} t={self.tag_id} "
            f"@{self.timestamp} = {self.value}>"
        )
