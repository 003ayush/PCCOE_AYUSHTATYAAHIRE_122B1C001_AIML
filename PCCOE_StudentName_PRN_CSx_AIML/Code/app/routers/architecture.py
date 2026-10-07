"""Architecture endpoints: validate uploaded JSON/XML exports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.routers.common import get_session
from app.schemas import Architecture
from app.services.architecture import parse_architecture

router = APIRouter(prefix="/architecture", tags=["architecture"])


class ValidateRequest(BaseModel):
    """Upload payload: raw file content plus its format."""

    content: str
    format: str = "json"


@router.post("/validate", response_model=Architecture)
def validate_architecture(body: ValidateRequest, session: Session = Depends(get_session)):
    """Validate an architecture export; errors name the exact problem."""
    _ = session  # accepted for a uniform signature; nothing persisted here
    try:
        return parse_architecture(body.content, body.format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
