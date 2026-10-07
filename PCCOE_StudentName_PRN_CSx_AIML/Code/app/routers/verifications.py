"""Verification endpoints: link mitigations to test activities, list them."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import AuditLogRow, MitigationRow, VerificationRow
from app.routers.common import get_session, row_to_schema
from app.schemas import VerificationLink, VerificationStatus
from app.services.review import apply_review

router = APIRouter(prefix="/verifications", tags=["verifications"])


class CreateRequest(BaseModel):
    """A test activity covering one mitigation."""

    id: str
    mitigation_id: str
    test_method: str
    status_detail: VerificationStatus = VerificationStatus.PLANNED
    note: str = ""
    reviewer: str = "anonymous"


@router.post("", response_model=VerificationLink)
def create(body: CreateRequest, session: Session = Depends(get_session)):
    """Record a verification link; the mitigation must exist."""
    if session.get(MitigationRow, body.mitigation_id) is None:
        raise HTTPException(status_code=422, detail=f"mitigation '{body.mitigation_id}' not found")
    if session.get(VerificationRow, body.id) is not None:
        raise HTTPException(status_code=422, detail=f"verification '{body.id}' already exists")
    row = VerificationRow(id=body.id, mitigation_id=body.mitigation_id, test_method=body.test_method,
                          status_detail=body.status_detail.value, note=body.note)
    session.add(row)
    session.add(AuditLogRow(item_type="verification", item_id=body.id, action="created",
                            reviewer=body.reviewer, note=body.test_method))
    session.flush()
    return row_to_schema(row)


@router.get("", response_model=list[VerificationLink])
def list_verifications(session: Session = Depends(get_session)):
    """Return all stored verification links."""
    return [row_to_schema(r) for r in session.query(VerificationRow).all()]
