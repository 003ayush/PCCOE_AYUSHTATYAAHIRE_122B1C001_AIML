"""Graph wiring: knowledge -> analyst -> (needs_more ? knowledge : validate) -> END.

Loop bound: the analyst routes back to knowledge only while requests remain
AND ``rounds < settings.max_knowledge_rounds``. Reaching validation with
requests still pending records an exhaustion error so reviewers know the
output may be incomplete. Human approval stays outside the graph.
"""

from __future__ import annotations

from typing import Dict

from langgraph.graph import END, START, StateGraph

from app.agents.analyst import build_analyst_node
from app.agents.knowledge import build_knowledge_node
from app.agents.state import TaraState, TaskKind
from app.config import settings
from app.llm.base import LLMClient
from app.schemas import Asset, Mitigation, ThreatScenario
from app.services.llm_json import flag_uncited

# Task -> Pydantic model for the validation node (risk rationale is untyped dicts).
TASK_MODELS = {"threats": ThreatScenario, "mitigations": Mitigation, "assets": Asset}


def validate_node(state: TaraState) -> Dict:
    """Pydantic-check drafts, flag uncited ones, drop invalid ones loudly."""
    task, errors = state["task"], list(state.get("errors", []))
    requests = state.get("knowledge_requests", [])
    if requests:  # loop budget ran out with questions still open
        errors.append("knowledge round budget exhausted; output needs expert review")
    clean = []
    for draft in state.get("drafts", []):
        if task == "risk_rationale":
            if isinstance(draft, dict) and isinstance(draft.get("threat_id"), str):
                clean.append(draft)
            else:
                errors.append(f"dropped invalid rationale draft: {draft!r}"[:200])
            continue
        try:
            clean.append(flag_uncited(TASK_MODELS[task].model_validate(draft)).model_dump(mode="json"))
        except Exception as exc:
            errors.append(f"dropped invalid draft: {exc}"[:200])
    return {"drafts": clean, "errors": errors, "knowledge_requests": []}


def _route(state: TaraState) -> str:
    """Back to knowledge only with pending requests inside the round budget."""
    if state.get("knowledge_requests") and state.get("rounds", 0) < settings.max_knowledge_rounds:
        return "knowledge"
    return "validate"


def run_task(task: TaskKind, client: LLMClient, store=None, variables: Dict | None = None,
             initial_requests=None, seed: Dict | None = None) -> TaraState:
    """Build the graph for one task and invoke it; return the final state."""
    builder = StateGraph(TaraState)
    builder.add_node("knowledge", build_knowledge_node(store, client))
    builder.add_node("analyst", build_analyst_node(client, task, variables))
    builder.add_node("validate", validate_node)
    builder.add_edge(START, "knowledge")
    builder.add_edge("knowledge", "analyst")
    builder.add_conditional_edges("analyst", _route, {"knowledge": "knowledge", "validate": "validate"})
    builder.add_edge("validate", END)
    state: TaraState = {"task": task, "rounds": 0,
                        "knowledge_requests": list(initial_requests or []),
                        "retrieved_context": [], "retrieval_log": [],
                        "drafts": [], "errors": []}
    if seed:
        state.update(seed)
    return builder.compile().invoke(state)
