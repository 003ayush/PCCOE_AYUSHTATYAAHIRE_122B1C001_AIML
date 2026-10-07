"""Knowledge lifecycle (PROJECT.md: ownership, review dates, staleness).

Threat records carry whose mapping this is and when it was last reviewed
(fields written by ``scripts/build_threat_library.py``). Anything older
than ``max_age_days`` is reported stale so reviewers re-validate it.
"""

from __future__ import annotations

from datetime import date
from typing import Dict


def mapping_status(record: Dict, today: date | None = None, max_age_days: int = 365) -> Dict:
    """Summarise mapping ownership and staleness for one library record."""
    today = today or date.today()
    review_date = str(record.get("mapping_review_date", ""))
    try:
        age = (today - date.fromisoformat(review_date)).days
    except ValueError:
        age = None  # missing or malformed date is itself a finding
    return {
        "owner": record.get("mapping_owner", "unassigned"),
        "review_date": review_date or "missing",
        "stale": age is None or age > max_age_days,
    }
