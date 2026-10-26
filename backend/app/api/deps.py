"""FastAPI dependencies."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session, closed when the request finishes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
