"""Risk assessment: deterministic ISO/SAE 21434 style computation.

Impact value = max of the four impact categories (Safety, Financial,
Operational, Privacy). Feasibility value = max of the attack-potential
factors (conservative). Risk value = lookup in the configurable matrix
(``Model_Prompts_Config/risk_matrix.json``), never LLM-generated.
"""

from __future__ import annotations

import json
from typing import List, TYPE_CHECKING

from app.config import PROMPTS_CONFIG_DIR
from app.schemas import FeasibilityAssessment, ImpactAssessment, Risk, ThreatScenario

if TYPE_CHECKING:  # annotation only: at runtime only agents/knowledge.py touches RAGStore
    from app.llm.base import LLMClient
    from app.rag.store import RAGStore


def load_matrix() -> List[List[int]]:
    """Load the 5x5 impact x feasibility -> risk matrix from config."""
    data = json.loads((PROMPTS_CONFIG_DIR / "risk_matrix.json").read_text(encoding="utf-8"))
    matrix = data["matrix"]
    if len(matrix) != 5 or any(len(row) != 5 for row in matrix):
        raise ValueError("risk_matrix.json must be a 5x5 matrix")
    return matrix


def impact_value(impact: ImpactAssessment) -> int:
    """Worst case across the four impact categories."""
    return max(impact.safety, impact.financial, impact.operational, impact.privacy)


def feasibility_value(feas: FeasibilityAssessment) -> int:
    """Most capable attacker assumption across the five factors."""
    return max(
        feas.elapsed_time, feas.expertise, feas.knowledge, feas.window_of_opportunity, feas.equipment
    )


def risk_value(impact_v: int, feas_v: int, matrix: List[List[int]] | None = None) -> int:
    """Look up the risk value; indices are clamped to 0-4."""
    matrix = matrix or load_matrix()
    return matrix[max(0, min(4, impact_v))][max(0, min(4, feas_v))]


def assess_threat(threat: ThreatScenario, matrix: List[List[int]] | None = None) -> Risk:
    """Build a Risk for one threat; uncited threats propagate expert review."""
    matrix = matrix or load_matrix()
    imp_v, feas_v = impact_value(threat.impact), feasibility_value(threat.feasibility)
    return Risk(
        id=f"RISK-{threat.id}",
        threat_id=threat.id,
        impact_value=imp_v,
        feasibility_value=feas_v,
        risk_value=risk_value(imp_v, feas_v, matrix),
        rationale=f"Impact {imp_v} (max of S/F/O/P) x feasibility {feas_v} (max of 5 factors) via risk_matrix v1.",
        needs_expert_review=getattr(threat.status, "value", threat.status) == "needs_expert_review",
    )


def assess_with_rationale(
    client: LLMClient,
    threats: List[ThreatScenario],
    rag: RAGStore | None = None,
    top_k: int = 5,
) -> List[Risk]:
    """Propose impact/feasibility via the graph, then compute values by matrix.

    The LLM only supplies ratings + rationale; numbers always come from the
    configured matrix, never from the model.
    """
    from app.agents.graph import run_task

    final = run_task(
        "risk_rationale",
        client,
        store=rag,
        variables={"threats": json.dumps([t.model_dump(mode="json") for t in threats])},
        initial_requests=[{
            "query": f"impact feasibility {' '.join(t.title for t in threats)}",
            "filters": {},
            "top_k": top_k,
        }],
    )
    proposed = {d["threat_id"]: d for d in final["drafts"] if isinstance(d.get("threat_id"), str)}
    risks = []
    for threat in threats:
        updated, analyst_note = threat, ""
        if threat.id in proposed:
            draft = proposed[threat.id]
            updated = threat.model_copy(deep=True)
            try:
                updated.impact = ImpactAssessment.model_validate(draft.get("impact", {}))
                updated.feasibility = FeasibilityAssessment.model_validate(draft.get("feasibility", {}))
                analyst_note = str(draft.get("rationale", ""))
            except Exception:
                pass  # malformed proposal -> fall back to the threat's own ratings
        risk = assess_threat(updated)
        if analyst_note:
            risk.rationale = f"Analyst: {analyst_note} Matrix: {risk.rationale}"
        risks.append(risk)
    return risks
