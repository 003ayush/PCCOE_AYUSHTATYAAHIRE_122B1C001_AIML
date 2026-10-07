"""Risk endpoints: assess threats via the configured matrix, list stored risks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import RiskRow
from app.llm import get_llm_client
from app.routers.common import get_session, row_to_schema, upsert_schemas
from app.schemas import Risk, ThreatScenario
from app.services.risk import assess_threat, assess_with_rationale

router = APIRouter(prefix="/risks", tags=["risks"])


class AssessRequest(BaseModel):
    """Threats to rate; set rationale=true for analyst-proposed ratings (values still by matrix)."""

    threats: list[ThreatScenario]
    rationale: bool = False


@router.post("/assess", response_model=list[Risk])
def assess(body: AssessRequest, session: Session = Depends(get_session)):
    """Compute risks (matrix lookup, no LLM call) and persist new ones."""
    try:
        risks = (assess_with_rationale(get_llm_client(), body.threats)
                 if body.rationale else [assess_threat(t) for t in body.threats])
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    upsert_schemas(session, RiskRow, risks)
    return risks


@router.get("", response_model=list[Risk])
def list_risks(session: Session = Depends(get_session)):
    """Return all stored risk ratings."""
    return [row_to_schema(r) for r in session.query(RiskRow).all()]
