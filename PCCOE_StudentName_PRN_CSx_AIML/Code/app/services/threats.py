"""Threat-scenario suggestion grounded in retrieved library patterns."""

from __future__ import annotations

import json
from typing import List, TYPE_CHECKING

from app.llm.base import LLMClient
from app.schemas import Asset, Interface, ThreatScenario
from app.services.llm_json import ensure_drafts_or_raise

if TYPE_CHECKING:  # annotation only: at runtime only agents/knowledge.py touches RAGStore
    from app.rag.store import RAGStore


def suggest_threats(
    client: LLMClient,
    rag: RAGStore | None = None,
    assets: List[Asset] | None = None,
    interfaces: List[Interface] | None = None,
    top_k: int = 5,
) -> List[ThreatScenario]:
    """Draft threats via the analyst/knowledge graph (same schema as before)."""
    from app.agents.graph import run_task

    assets, interfaces = assets or [], interfaces or []
    final = run_task(
        "threats",
        client,
        store=rag,
        variables={
            "assets": json.dumps([a.model_dump(mode="json") for a in assets]),
            "interfaces": json.dumps([i.model_dump(mode="json") for i in interfaces]),
        },
        initial_requests=[{
            "query": f"threat scenarios {' '.join(a.name for a in assets)}",
            "filters": {},
            "top_k": top_k,
        }],
    )
    return [ThreatScenario.model_validate(d) for d in ensure_drafts_or_raise(final, "threat")]
