"""Threat endpoints: suggest scenarios for assets, list stored ones."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import ThreatRow
from app.llm import get_llm_client
from app.routers.common import get_session, row_to_schema, upsert_schemas
from app.schemas import Asset, Interface, ThreatScenario
from app.services.threats import suggest_threats

if TYPE_CHECKING:  # annotation only; stores are built inside agents/knowledge.py
    from app.rag.store import RAGStore  # noqa: F401

router = APIRouter(prefix="/threats", tags=["threats"])


class SuggestRequest(BaseModel):
    """Assets and interfaces to draft threats against."""

    assets: list[Asset]
    interfaces: list[Interface] = []
    top_k: int = 5


@router.post("/suggest", response_model=list[ThreatScenario])
def suggest(body: SuggestRequest, session: Session = Depends(get_session)):
    """Draft threat scenarios via LLM + library context and persist new ones."""
    try:
        threats = suggest_threats(get_llm_client(), None, body.assets, body.interfaces, body.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    upsert_schemas(session, ThreatRow, threats)
    return threats


@router.get("", response_model=list[ThreatScenario])
def list_threats(session: Session = Depends(get_session)):
    """Return all stored threat scenarios."""
    return [row_to_schema(r) for r in session.query(ThreatRow).all()]
