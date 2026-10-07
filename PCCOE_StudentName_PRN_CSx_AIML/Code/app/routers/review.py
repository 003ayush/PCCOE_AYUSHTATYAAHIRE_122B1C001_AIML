"""Review endpoint: approve / edit / reject / flag any item, with audit logging."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import AuditLogRow
from app.routers.common import get_session, row_to_schema
from app.schemas import AuditEntry
from app.services.review import DECISIONS, REVIEWABLE, apply_review

router = APIRouter(prefix="/review", tags=["review"])


class ReviewRequest(BaseModel):
    """Reviewer decision on one item; updates only used with decision 'edit'."""

    decision: str
    reviewer: str
    note: str = ""
    updates: dict = {}


@router.post("/{item_type}/{item_id}")
def review(item_type: str, item_id: str, body: ReviewRequest, session: Session = Depends(get_session)):
    """Apply a decision and return the updated item."""
    if item_type not in REVIEWABLE:
        raise HTTPException(status_code=404, detail=f"Unknown item type '{item_type}'")
    try:
        row = apply_review(session, item_type, item_id, body.decision, body.reviewer, body.note, body.updates)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return row_to_schema(row)


@router.get("/decisions", response_model=list[str])
def list_decisions():
    """Valid decision names for the review endpoint."""
    return sorted(DECISIONS)


@router.get("/audit", response_model=list[AuditEntry])
def list_audit(session: Session = Depends(get_session)):
    """Full audit trail, newest last."""
    return [
        AuditEntry.model_validate(
            {c.key: getattr(r, c.key) for c in r.__table__.columns}
        )
        for r in session.query(AuditLogRow).order_by(AuditLogRow.id).all()
    ]
