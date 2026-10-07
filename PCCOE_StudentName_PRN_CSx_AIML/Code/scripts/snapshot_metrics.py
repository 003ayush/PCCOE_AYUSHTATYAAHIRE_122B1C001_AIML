"""Snapshot PROJECT.md §11 quality metrics into Evaluation_Results/.

Reads the configured SQLite database (default: a fresh look at the live DB),
computes metrics from stored review data, and writes metrics.json. Run after
a review session: venv\\Scripts\\python Code\\scripts\\snapshot_metrics.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import AssetRow, MitigationRow, RiskRow, ThreatRow, VerificationRow, init_db, session_scope  # noqa: E402
from app.routers.common import row_to_schema  # noqa: E402
from app.services.traceability import compute_metrics  # noqa: E402

PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # Code/scripts -> package root
OUT = PACKAGE_ROOT / "Evaluation_Results" / "metrics.json"


def main() -> None:
    """Compute metrics from the live DB and write the snapshot file."""
    init_db()
    with session_scope() as session:
        snapshot = compute_metrics(
            [row_to_schema(r) for r in session.query(AssetRow).all()],
            [row_to_schema(r) for r in session.query(ThreatRow).all()],
            [row_to_schema(r) for r in session.query(RiskRow).all()],
            [row_to_schema(r) for r in session.query(MitigationRow).all()],
            [row_to_schema(r) for r in session.query(VerificationRow).all()],
        ).model_dump()
    snapshot["snapshot_at"] = datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({snapshot['total_threats']} threats)")


if __name__ == "__main__":
    main()
