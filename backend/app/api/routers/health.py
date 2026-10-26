"""Health endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import HealthOut
from app.services import health_service

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthOut, summary="API & database health")
def health(db: Session = Depends(get_db)) -> HealthOut:
    """Report API/DB connectivity, TimescaleDB status, total readings and the
    latest data timestamp (used by the frontend to anchor relative time ranges)."""
    return HealthOut(**health_service.check_health(db))
