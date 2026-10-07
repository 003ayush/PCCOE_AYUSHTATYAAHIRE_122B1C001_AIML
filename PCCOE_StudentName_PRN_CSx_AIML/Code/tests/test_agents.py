"""Agentic pipeline: knowledge isolation, loop cap, no-match, mock end-to-end."""

import ast
import json
from pathlib import Path

from app.agents.graph import run_task
from app.agents.knowledge import NO_MATCH_ID, build_knowledge_node
from app.agents.state import TaraState
from app.config import settings
from app.llm.mock import MockLLMClient
from app.schemas import ThreatScenario
from app.services.risk import assess_with_rationale


class _FakeStore:
    """Deterministic stand-in for RAGStore (no embeddings, no chroma)."""

    def __init__(self, records):
        self._records = records

    def retrieve(self, query, top_k=5, category=None):
        hits = [r for r in self._records
                if category is None or r.get("stride_category") == category]
        return hits[:top_k]


class _ScriptedLLM:
    """Replays canned JSON strings in order, then repeats the last."""

    name = "scripted"

    def __init__(self, *replies):
        self._replies = list(replies)

    def complete(self, prompt, system=""):
        if len(self._replies) > 1:
            return self._replies.pop(0)
        return self._replies[0]


LIB = [
    {"id": "THREAT-A", "text": "spoofed backend server", "stride_category": "Spoofing",
     "typical_assets": ["Firmware Update Package"]},
    {"id": "THREAT-B", "text": "firmware tampering in transit", "stride_category": "Tampering",
     "typical_assets": ["Firmware Update Package"]},
]


def _state(**over):
    base: TaraState = {"task": "threats", "rounds": 0, "knowledge_requests": [],
                       "retrieved_context": [], "retrieval_log": [], "drafts": [], "errors": []}
    base.update(over)
    return base


def test_only_knowledge_imports_ragstore():
    """DoD: separation of knowledge and reasoning, checked structurally.

    Only runtime imports count: the rag package itself and TYPE_CHECKING
    annotations (used for signatures, never executed) are excluded.
    """
    root = Path(__file__).resolve().parents[1] / "app"

    class Visitor(ast.NodeVisitor):
        """Collect module-level app.rag imports (deferred function-level
        imports are lazy wiring, not reasoning access)."""

        def __init__(self, filename):
            self.filename = filename
            self.guarded = 0
            self.func_depth = 0
            self.hits = []

        def visit_If(self, node):
            guarded = "TYPE_CHECKING" in ast.unparse(node.test)
            self.guarded += guarded
            self.generic_visit(node)
            self.guarded -= guarded

        def visit_FunctionDef(self, node):
            self.func_depth += 1
            self.generic_visit(node)
            self.func_depth -= 1

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ImportFrom(self, node):
            if (self.guarded == 0 and self.func_depth == 0
                    and (node.module or "").startswith("app.rag")):
                self.hits.append(self.filename)

    offenders = []
    for path in sorted(root.rglob("*.py")):
        if (root / "rag") in path.parents:
            continue  # the retrieval implementation itself
        visitor = Visitor(path.name)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
        offenders.extend(visitor.hits)
    assert offenders == ["knowledge.py"], f"RAG touched outside knowledge.py: {offenders}"


def test_knowledge_serves_filtered_requests_and_logs():
    """Filters narrow results; every retrieval is logged with returned IDs."""
    node = build_knowledge_node(_FakeStore(LIB))
    out = node(_state(knowledge_requests=[
        {"query": "spoofing", "filters": {"stride_category": "Spoofing"}, "top_k": 5}]))
    assert [r["id"] for r in out["retrieved_context"]] == ["THREAT-A"]
    assert out["retrieval_log"][0]["returned_ids"] == ["THREAT-A"]
    assert out["knowledge_requests"] == [] and out["rounds"] == 1


def test_knowledge_list_filter_and_no_match():
    """List metadata matches on membership; empty results give NO_MATCH."""
    node = build_knowledge_node(_FakeStore(LIB))
    out = node(_state(knowledge_requests=[
        {"query": "x", "filters": {"typical_assets": "Firmware Update Package"}, "top_k": 5},
        {"query": "nothing matches this", "filters": {"stride_category": "Repudiation"}, "top_k": 5}]))
    ids = [r["id"] for r in out["retrieved_context"]]
    assert "THREAT-A" in ids and "THREAT-B" in ids and NO_MATCH_ID in ids


def test_graph_mock_end_to_end_same_schema():
    """Threat task through the graph with mock LLM returns valid schemas (empty, as before)."""
    final = run_task("threats", MockLLMClient(), store=_FakeStore(LIB),
                     variables={"assets": "[]", "interfaces": "[]"},
                     initial_requests=[{"query": "threats", "filters": {}, "top_k": 5}])
    assert final["drafts"] == []
    assert final["retrieval_log"] and not final["errors"]


def test_graph_scripted_threat_roundtrip():
    """A scripted analyst producing one threat yields a valid ThreatScenario."""
    draft = {"id": "T-9", "title": "OTA spoof", "description": "fake backend",
             "stride_category": "Spoofing", "affected_assets": ["A1"], "source_ids": ["THREAT-A"]}
    llm = _ScriptedLLM(json.dumps({"items": [draft]}))
    final = run_task("threats", llm, store=_FakeStore(LIB),
                     variables={"assets": "[]", "interfaces": "[]"},
                     initial_requests=[{"query": "spoofing", "filters": {}, "top_k": 5}])
    assert ThreatScenario.model_validate(final["drafts"][0]).id == "T-9"


def test_loop_cap_with_always_hungry_analyst():
    """An analyst that always wants more data is stopped at the round budget."""
    hungry = _ScriptedLLM(json.dumps({"data_requests": [{"query": "more", "filters": {}, "top_k": 1}]}))
    final = run_task("threats", hungry, store=_FakeStore(LIB),
                     variables={"assets": "[]", "interfaces": "[]"},
                     initial_requests=[{"query": "start", "filters": {}, "top_k": 1}])
    assert final["rounds"] <= settings.max_knowledge_rounds
    assert any("budget exhausted" in e for e in final["errors"])


def test_risk_rationale_falls_back_to_matrix():
    """Mock analyst proposes nothing; values still come from the matrix."""
    from app.schemas import FeasibilityAssessment, ImpactAssessment, ThreatScenario as TS
    t = TS(id="T1", title="t", description="d", stride_category="Tampering",
           impact=ImpactAssessment(safety=3), feasibility=FeasibilityAssessment(expertise=2))
    (risk,) = assess_with_rationale(MockLLMClient(), [t], rag=_FakeStore(LIB))
    assert (risk.impact_value, risk.feasibility_value, risk.risk_value) == (3, 2, 3)
