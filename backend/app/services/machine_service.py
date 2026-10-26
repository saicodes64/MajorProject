"""Machine data-access / business logic.

All SQL lives here (and in the other services), never in the route handlers.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


# Scalar subqueries keep tag_count / latest timestamp cheap: the max(timestamp)
# subquery is served by the (machine_id, timestamp DESC) index. We deliberately
# avoid joining machines against the 22.7M-row readings table directly, which
# would explode into a huge intermediate result.
_MACHINE_SELECT = """
    SELECT m.id, m.machine_code, m.name, m.machine_type, m.location,
           m.description, m.created_at,
           (SELECT count(*) FROM tags t WHERE t.machine_id = m.id) AS tag_count,
           (SELECT max(sr.timestamp) FROM sensor_readings sr
             WHERE sr.machine_id = m.id) AS latest_data_timestamp
    FROM machines m
"""


def list_machines(db: Session) -> list[dict]:
    """Return all machines with their tag count and latest data timestamp."""
    rows = db.execute(text(_MACHINE_SELECT + " ORDER BY m.id")).mappings()
    return [dict(r) for r in rows]


def get_machine(db: Session, machine_id: int) -> dict | None:
    row = (
        db.execute(text(_MACHINE_SELECT + " WHERE m.id = :mid"), {"mid": machine_id})
        .mappings()
        .first()
    )
    return dict(row) if row else None
