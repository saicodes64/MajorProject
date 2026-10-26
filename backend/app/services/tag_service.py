"""Tag data-access / business logic."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_tags(db: Session, machine_id: int | None = None) -> list[dict]:
    """Return tags, optionally filtered by machine."""
    sql = """
        SELECT id, machine_id, tag_name, display_name, data_type, unit,
               description, created_at
        FROM tags
    """
    params: dict = {}
    if machine_id is not None:
        sql += " WHERE machine_id = :mid"
        params["mid"] = machine_id
    sql += " ORDER BY id"
    rows = db.execute(text(sql), params).mappings()
    return [dict(r) for r in rows]


def get_tag(db: Session, tag_id: int) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id, machine_id, tag_name, display_name, data_type, unit,
                   description, created_at
            FROM tags WHERE id = :tid
            """
        ),
        {"tid": tag_id},
    ).mappings().first()
    return dict(row) if row else None
