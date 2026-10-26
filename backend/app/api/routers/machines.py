"""Machine endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import MachineOut
from app.services import machine_service

router = APIRouter(prefix="/api/machines", tags=["machines"])


@router.get("", response_model=list[MachineOut], summary="List machines")
def list_machines(db: Session = Depends(get_db)) -> list[MachineOut]:
    return [MachineOut(**m) for m in machine_service.list_machines(db)]


@router.get("/{machine_id}", response_model=MachineOut, summary="Get one machine")
def get_machine(machine_id: int, db: Session = Depends(get_db)) -> MachineOut:
    m = machine_service.get_machine(db, machine_id)
    if m is None:
        raise HTTPException(status_code=404, detail=f"Machine {machine_id} not found")
    return MachineOut(**m)
