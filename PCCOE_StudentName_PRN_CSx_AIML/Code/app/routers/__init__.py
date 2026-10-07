"""TARA Assistant API: typed endpoints over the analysis pipeline."""

from __future__ import annotations

from fastapi import APIRouter

from app.routers import architecture, assets, mitigations, report, review, risks, threats, verifications

router = APIRouter()
router.include_router(architecture.router)
router.include_router(assets.router)
router.include_router(threats.router)
router.include_router(risks.router)
router.include_router(mitigations.router)
router.include_router(verifications.router)
router.include_router(review.router)
router.include_router(report.router)

__all__ = ["router"]
