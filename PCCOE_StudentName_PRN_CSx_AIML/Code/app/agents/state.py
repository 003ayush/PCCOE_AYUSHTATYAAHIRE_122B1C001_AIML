"""Graph state for the pipeline (PLAN §5a): one analyst agent + retrieval.

The analyst never touches retrieval: it emits ``knowledge_requests`` and the
deterministic retrieval step answers into ``retrieved_context``. Every
retrieval is logged in ``retrieval_log`` for traceability. Loops are bounded
by ``rounds`` against ``settings.max_knowledge_rounds``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict

# Pipelines the graph can run; routers select one per call.
TaskKind = Literal["threats", "mitigations", "assets", "risk_rationale"]


class KnowledgeRequest(TypedDict):
    """A structured data request from the analyst to the retrieval step."""

    query: str
    filters: Dict[str, Any]
    top_k: int


class RetrievedRecord(TypedDict):
    """One citable library record handed to the analyst."""

    id: str
    text: str
    source: str


class RetrievalLogEntry(TypedDict):
    """Audit trail of a single retrieval: what was asked, what came back."""

    query: str
    filters: Dict[str, Any]
    returned_ids: List[str]


class TaraState(TypedDict, total=False):
    """LangGraph state: inputs, analyst/knowledge exchange, outputs, errors."""

    task: TaskKind
    architecture: Dict[str, Any]
    assets: List[Dict[str, Any]]
    interfaces: List[Dict[str, Any]]
    knowledge_requests: List[KnowledgeRequest]
    retrieved_context: List[RetrievedRecord]
    retrieval_log: List[RetrievalLogEntry]
    drafts: List[Dict[str, Any]]
    errors: List[str]
    rounds: int
