"""Analyst agent: the single component with LLM access.

Wraps the v2 prompt templates around our ``LLMClient`` (this node IS the
Phase 9 LLMClient graph wrapper: no LangChain chat model, so provider
fallback and the mock provider keep working). Emits either ``drafts`` or
follow-up ``knowledge_requests`` — it never retrieves anything itself.
"""

from __future__ import annotations

import json
from typing import Dict, List

from app.agents.state import TaraState, TaskKind
from app.llm.base import LLMClient
from app.services.llm_json import complete_json
from app.services.prompts import load_prompt, render

# Task -> v2 template name.
TASK_TEMPLATES: Dict[TaskKind, str] = {
    "threats": "threat_scenario",
    "mitigations": "mitigation",
    "assets": "asset_extraction",
    "risk_rationale": "risk_assessment",
}


def _normalise_requests(raw: object) -> List[Dict]:
    """Coerce analyst data_requests to KnowledgeRequest dicts with defaults."""
    out = []
    for req in raw if isinstance(raw, list) else []:
        if not isinstance(req, dict) or not req.get("query"):
            continue
        out.append({"query": str(req["query"]),
                    "filters": req.get("filters", {}) or {},
                    "top_k": int(req.get("top_k", 5))})
    return out


def build_analyst_node(client: LLMClient, task: TaskKind, variables: Dict | None = None):
    """Create the analyst node: render v2 prompt, call LLM, split drafts/requests."""
    _, system, user_tmpl = load_prompt(TASK_TEMPLATES[task], version=2)
    variables = variables or {}

    def analyst_node(state: TaraState) -> Dict:
        """Run one analyst pass over the current retrieved context."""
        context = [r for r in state.get("retrieved_context", [])]
        prompt = render(user_tmpl, context=json.dumps(context), **variables)
        try:
            parsed = complete_json(client, prompt, system)
        except Exception as exc:  # noqa: BLE001 - provider/SDK errors degrade to logged errors
            return {"errors": [*state.get("errors", []), f"analyst LLM failed: {exc}"]}
        if isinstance(parsed, dict) and parsed.get("data_requests"):
            extra = _normalise_requests(parsed["data_requests"])
            return {"knowledge_requests": [*state.get("knowledge_requests", []), *extra]}
        items = parsed if isinstance(parsed, list) else parsed.get("items", [])
        if not isinstance(items, list):
            return {"errors": [*state.get("errors", []), f"unexpected analyst output: {parsed!r}"[:200]]}
        return {"drafts": items}

    return analyst_node
