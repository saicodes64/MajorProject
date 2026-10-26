"""Tag response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: int
    tag_name: str
    display_name: str | None = None
    data_type: str | None = None  # "analog" | "digital"
    unit: str | None = None
    description: str | None = None
    created_at: datetime | None = None
