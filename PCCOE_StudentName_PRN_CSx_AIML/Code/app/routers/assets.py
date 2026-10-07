"""Asset endpoints: suggest from architecture, list stored suggestions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import AssetRow
from app.llm import get_llm_client
from app.routers.common import get_session, row_to_schema, upsert_schemas
from app.schemas import Architecture, Asset, ExposedInterface
from app.services.assets import attack_surface, suggest_assets

if TYPE_CHECKING:  # annotation only; stores are built inside agents/knowledge.py
    from app.rag.store import RAGStore  # noqa: F401

router = APIRouter(prefix="/assets", tags=["assets"])


class SuggestRequest(BaseModel):
    """Architecture to analyse plus retrieval depth."""

    architecture: Architecture
    top_k: int = 5


class AttackSurfaceRequest(BaseModel):
    """Architecture whose exposed interfaces should be listed."""

    architecture: Architecture


@router.post("/suggest", response_model=list[Asset])
def suggest(body: SuggestRequest, session: Session = Depends(get_session)):
    """Suggest assets via LLM + library context and persist new ones."""
    try:
        assets = suggest_assets(get_llm_client(), None, body.architecture, body.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    upsert_schemas(session, AssetRow, assets)
    return assets


@router.get("", response_model=list[Asset])
def list_assets(session: Session = Depends(get_session)):
    """Return all stored asset suggestions."""
    return [row_to_schema(r) for r in session.query(AssetRow).all()]


@router.post("/attack-surface", response_model=list[ExposedInterface])
def get_attack_surface(body: AttackSurfaceRequest):
    """List attacker-reachable interfaces (deterministic, no LLM call)."""
    return attack_surface(body.architecture)
