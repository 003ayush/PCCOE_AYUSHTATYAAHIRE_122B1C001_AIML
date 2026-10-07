"""Mitigation drafting grounded in retrieved standard mitigations."""

from __future__ import annotations

import json
from typing import List, TYPE_CHECKING

from app.llm.base import LLMClient
from app.schemas import Mitigation, Risk, ThreatScenario
from app.services.llm_json import ensure_drafts_or_raise

if TYPE_CHECKING:  # annotation only: at runtime only agents/knowledge.py touches RAGStore
    from app.rag.store import RAGStore


def suggest_mitigations(
    client: LLMClient,
    rag: RAGStore | None = None,
    threats: List[ThreatScenario] | None = None,
    risks: List[Risk] | None = None,
    top_k: int = 5,
) -> List[Mitigation]:
    """Draft mitigations via the analyst/knowledge graph (same schema as before)."""
    from app.agents.graph import run_task

    threats, risks = threats or [], risks or []
    risk_by_threat = {r.threat_id: r.risk_value for r in risks}
    final = run_task(
        "mitigations",
        client,
        store=rag,
        variables={"threats": json.dumps(
            [{**t.model_dump(mode="json"), "risk_value": risk_by_threat.get(t.id)} for t in threats])},
        initial_requests=[{
            "query": f"mitigations cybersecurity requirements {' '.join(t.title for t in threats)}",
            "filters": {},
            "top_k": top_k,
        }],
    )
    return [Mitigation.model_validate(d) for d in ensure_drafts_or_raise(final, "mitigation")]
