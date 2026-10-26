"""Tag endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import TagOut
from app.services import tag_service

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagOut], summary="List tags")
def list_tags(
    machine_id: int | None = Query(None, description="Filter tags by machine id."),
    db: Session = Depends(get_db),
) -> list[TagOut]:
    return [TagOut(**t) for t in tag_service.list_tags(db, machine_id)]


@router.get("/{tag_id}", response_model=TagOut, summary="Get one tag")
def get_tag(tag_id: int, db: Session = Depends(get_db)) -> TagOut:
    t = tag_service.get_tag(db, tag_id)
    if t is None:
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")
    return TagOut(**t)
