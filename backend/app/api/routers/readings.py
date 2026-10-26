"""Reading endpoints: latest, trend, statistics."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import (
    LatestReadingOut,
    StatisticsOut,
    SummaryItem,
    TrendPoint,
    TrendResponse,
)
from app.services import reading_service, tag_service
from app.thresholds import compute_status

router = APIRouter(prefix="/api/readings", tags=["readings"])


def _require_tag(db: Session, tag_id: int) -> dict:
    tag = tag_service.get_tag(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")
    return tag


@router.get(
    "/latest",
    response_model=list[LatestReadingOut],
    summary="Latest value per tag",
)
def latest(
    machine_id: int | None = Query(None, description="Restrict to one machine."),
    db: Session = Depends(get_db),
) -> list[LatestReadingOut]:
    """Efficient current-state snapshot: one row per tag (no history sent)."""
    rows = reading_service.get_latest_per_tag(db, machine_id)
    return [LatestReadingOut(**r) for r in rows]


@router.get(
    "/summary",
    response_model=list[SummaryItem],
    summary="Per-tag snapshot (current + stats + status)",
)
def summary(
    machine_id: int = Query(..., description="Machine id."),
    db: Session = Depends(get_db),
) -> list[SummaryItem]:
    """One call returning, for every tag, its latest value plus full-history
    min/max/avg/stddev/count and status. Backs the KPI cards and tag table."""
    return [SummaryItem(**s) for s in reading_service.get_summary(db, machine_id)]


@router.get("/trend", response_model=TrendResponse, summary="Historical trend")
def trend(
    machine_id: int = Query(..., description="Machine id."),
    tag_id: int = Query(..., description="Tag id."),
    start_time: datetime = Query(..., description="ISO start (inclusive)."),
    end_time: datetime = Query(..., description="ISO end (inclusive)."),
    interval: str | None = Query(
        None,
        description="Optional Postgres interval literal (e.g. '1 minute'). "
        "If omitted, the server auto-downsamples to stay within its point cap.",
    ),
    db: Session = Depends(get_db),
) -> TrendResponse:
    if start_time >= end_time:
        raise HTTPException(
            status_code=422, detail="start_time must be before end_time"
        )
    tag = _require_tag(db, tag_id)

    result = reading_service.get_trend(
        db, machine_id, tag_id, start_time, end_time, interval
    )
    return TrendResponse(
        machine_id=machine_id,
        tag_id=tag_id,
        tag_name=tag["tag_name"],
        display_name=tag["display_name"],
        unit=tag["unit"],
        start_time=start_time,
        end_time=end_time,
        aggregated=result["aggregated"],
        interval=result["interval"],
        point_count=result["point_count"],
        points=[TrendPoint(**p) for p in result["points"]],
    )


@router.get(
    "/statistics", response_model=StatisticsOut, summary="Tag statistics"
)
def statistics(
    machine_id: int = Query(..., description="Machine id."),
    tag_id: int = Query(..., description="Tag id."),
    start_time: datetime | None = Query(None, description="Optional ISO start."),
    end_time: datetime | None = Query(None, description="Optional ISO end."),
    db: Session = Depends(get_db),
) -> StatisticsOut:
    if start_time is not None and end_time is not None and start_time >= end_time:
        raise HTTPException(
            status_code=422, detail="start_time must be before end_time"
        )
    tag = _require_tag(db, tag_id)

    stats = reading_service.get_statistics(
        db, machine_id, tag_id, start_time, end_time
    )
    return StatisticsOut(
        machine_id=machine_id,
        tag_id=tag_id,
        tag_name=tag["tag_name"],
        display_name=tag["display_name"],
        unit=tag["unit"],
        start_time=start_time,
        end_time=end_time,
        status=compute_status(tag["tag_name"], stats["current"]),
        **stats,
    )
