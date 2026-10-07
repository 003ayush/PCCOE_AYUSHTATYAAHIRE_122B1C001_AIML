"""Report endpoints: traceability chains, gaps, and Markdown export."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db import AssetRow, MitigationRow, RiskRow, ThreatRow, VerificationRow
from app.routers.common import get_session, row_to_schema
from app.schemas import QualityMetrics, TraceabilityReport
from app.services.traceability import build_traceability, compute_metrics, render_markdown

router = APIRouter(prefix="/report", tags=["report"])


def _all(session):
    """Load every reviewable table as schemas."""
    return (
        [row_to_schema(r) for r in session.query(AssetRow).all()],
        [row_to_schema(r) for r in session.query(ThreatRow).all()],
        [row_to_schema(r) for r in session.query(RiskRow).all()],
        [row_to_schema(r) for r in session.query(MitigationRow).all()],
        [row_to_schema(r) for r in session.query(VerificationRow).all()],
    )


@router.get("/traceability", response_model=TraceabilityReport)
def traceability(session: Session = Depends(get_session)):
    """Asset -> threat -> risk -> mitigation -> verification links plus every gap."""
    assets, threats, risks, mitigations, verifications = _all(session)
    return build_traceability(assets, threats, risks, mitigations, verifications)


@router.get("/metrics", response_model=QualityMetrics)
def metrics(session: Session = Depends(get_session)):
    """PROJECT.md §11 quality metrics computed from stored data."""
    return compute_metrics(*_all(session))


@router.get("/export")
def export_markdown(session: Session = Depends(get_session)):
    """Download the traceability report as Markdown."""
    report = traceability(session)
    return Response(content=render_markdown(report), media_type="text/markdown")
