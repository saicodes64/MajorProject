"""Machine response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MachineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_code: str
    name: str
    machine_type: str | None = None
    location: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    tag_count: int | None = Field(
        None, description="Number of tags defined for this machine."
    )
    latest_data_timestamp: datetime | None = Field(
        None, description="Most recent reading timestamp for this machine."
    )
