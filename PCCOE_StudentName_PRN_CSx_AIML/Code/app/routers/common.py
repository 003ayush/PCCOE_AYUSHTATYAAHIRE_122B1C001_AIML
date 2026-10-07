"""Shared router helpers: sessions, row <-> schema conversion, persistence."""

from __future__ import annotations

from typing import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import AssetRow, MitigationRow, RiskRow, ThreatRow, VerificationRow, session_scope
from app.schemas import Asset, Mitigation, Risk, ThreatScenario, VerificationLink

ROW_TO_SCHEMA = {AssetRow: Asset, ThreatRow: ThreatScenario, RiskRow: Risk,
                 MitigationRow: Mitigation, VerificationRow: VerificationLink}


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a transactional session."""
    with session_scope() as session:
        yield session


def row_to_schema(row):
    """Convert an ORM row to its Pydantic schema via matching field names."""
    cls = ROW_TO_SCHEMA[type(row)]
    data = {c.key: getattr(row, c.key) for c in row.__table__.columns}
    data["status"] = data.get("status") or "pending"
    return cls.model_validate(data)


def upsert_schemas(session: Session, model, items: list) -> None:
    """Insert suggested items; existing IDs are left untouched (reviewed data wins)."""
    for item in items:
        if session.get(model, item.id) is None:
            payload = item.model_dump(mode="json")
            cols = {c.key for c in model.__table__.columns}
            session.add(model(**{k: v for k, v in payload.items() if k in cols}))
    session.flush()
