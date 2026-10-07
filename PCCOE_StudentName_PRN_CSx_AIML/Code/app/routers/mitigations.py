"""Mitigation endpoints: draft requirements for threats, list stored ones."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import MitigationRow
from app.llm import get_llm_client
from app.routers.common import get_session, row_to_schema, upsert_schemas
from app.schemas import Mitigation, Risk, ThreatScenario
from app.services.mitigations import suggest_mitigations

if TYPE_CHECKING:  # annotation only; stores are built inside agents/knowledge.py
    from app.rag.store import RAGStore  # noqa: F401

router = APIRouter(prefix="/mitigations", tags=["mitigations"])


class SuggestRequest(BaseModel):
    """Threats (with their risk ratings) to draft mitigations for."""

    threats: list[ThreatScenario]
    risks: list[Risk] = []
    top_k: int = 5


@router.post("/suggest", response_model=list[Mitigation])
def suggest(body: SuggestRequest, session: Session = Depends(get_session)):
    """Draft mitigations via LLM + standard-micigation context and persist new ones."""
    try:
        mits = suggest_mitigations(get_llm_client(), None, body.threats, body.risks, body.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    upsert_schemas(session, MitigationRow, mits)
    return mits


@router.get("", response_model=list[Mitigation])
def list_mitigations(session: Session = Depends(get_session)):
    """Return all stored mitigations."""
    return [row_to_schema(r) for r in session.query(MitigationRow).all()]
