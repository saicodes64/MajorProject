"""Tag (signal/point) model.

A tag is one measurable signal on a machine (e.g. a pressure or a valve state).
This is the industrial "tag" abstraction common to Kepware / OPC UA / historians,
which is why readings reference a tag rather than a fixed CSV column.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("machine_id", "tag_name", name="uq_tags_machine_tagname"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    # Signal class: "analog" (real measurement) or "digital" (electrical signal).
    data_type: Mapped[str | None] = mapped_column(String(50))
    # Engineering unit; NULL when the dataset documentation provides none.
    unit: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    machine: Mapped["Machine"] = relationship(back_populates="tags")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tag {self.tag_name} ({self.data_type})>"
