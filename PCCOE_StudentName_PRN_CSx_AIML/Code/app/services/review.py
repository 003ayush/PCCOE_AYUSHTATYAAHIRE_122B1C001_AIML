"""Human-in-the-loop review: approve / edit / reject with audit logging."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.db import AssetRow, AuditLogRow, MitigationRow, RiskRow, ThreatRow, VerificationRow

# Registry of reviewable tables for the generic review endpoint.
REVIEWABLE = {
    "asset": AssetRow,
    "threat": ThreatRow,
    "risk": RiskRow,
    "mitigation": MitigationRow,
    "verification": VerificationRow,
}

# Reviewer decision -> stored status.
DECISIONS = {
    "approve": "approved",
    "reject": "rejected",
    "edit": "pending",
    "flag": "needs_expert_review",
}


def apply_review(
    session: Session,
    item_type: str,
    item_id: str,
    decision: str,
    reviewer: str,
    note: str = "",
    updates: Dict[str, Any] | None = None,
):
    """Apply a review decision, log it to the audit trail, and return the row."""
    model = REVIEWABLE.get(item_type)
    if model is None:
        raise ValueError(f"Unknown item type '{item_type}' (use asset/threat/risk/mitigation/verification)")
    if decision not in DECISIONS:
        raise ValueError(f"Unknown decision '{decision}' (use approve/reject/edit/flag)")
    if not reviewer:
        raise ValueError("Reviewer name is required")
    row = session.get(model, item_id)
    if row is None:
        raise LookupError(f"{item_type} '{item_id}' not found")
    for key, value in (updates or {}).items():  # reviewer edits to fields
        if key in ("id", "status") or not hasattr(row, key):
            raise ValueError(f"Cannot edit field '{key}'")
        setattr(row, key, value)
    row.status = DECISIONS[decision]
    row.reviewer = reviewer
    row.review_note = note
    row.reviewed_at = datetime.now(timezone.utc)
    session.add(
        AuditLogRow(item_type=item_type, item_id=item_id, action=decision, reviewer=reviewer, note=note)
    )
    return row
