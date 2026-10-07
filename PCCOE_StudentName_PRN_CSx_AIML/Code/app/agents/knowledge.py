"""Deterministic retrieval step: the ONLY module allowed to touch ``RAGStore``.

This is not an LLM agent — it runs no model calls by default (direct
retrieval + exact-match filters). An optional LLM query-rewrite sits behind
``KNOWLEDGE_LLM_REWRITE``. A request with no matches yields an explicit
``NO_MATCH`` record so downstream output is flagged, never silently invented.
"""

from __future__ import annotations

from typing import Dict, List

from app.config import settings
from app.llm.base import LLMClient
from app.rag.store import RAGStore
from app.agents.state import RetrievedRecord, RetrievalLogEntry, TaraState

# Sentinel telling the analyst (and the validator) that nothing matched.
NO_MATCH_ID = "NO_MATCH"


def _apply_filters(records: List[Dict], filters: Dict) -> List[Dict]:
    """Exact-match metadata filters; list fields match on membership."""
    out = records
    for key, want in (filters or {}).items():
        if key == "stride_category":  # already applied inside retrieve()
            continue
        out = [r for r in out if (want in r.get(key, []) if isinstance(r.get(key), list) else r.get(key) == want)]
    return out


def build_knowledge_node(store: RAGStore | None = None, llm_client: LLMClient | None = None):
    """Create the graph node with its dependencies injected (tests pass fakes)."""
    store = store or RAGStore()

    def maybe_rewrite(query: str) -> str:
        """Rewrite the query via LLM only when the config flag is on."""
        if not (settings.knowledge_llm_rewrite and llm_client):
            return query
        from app.services.prompts import load_prompt, render

        _, system, tmpl = load_prompt("knowledge_rewrite")
        try:
            return llm_client.complete(render(tmpl, query=query), system).strip() or query
        except Exception:
            return query  # rewrite is best-effort; never fail retrieval

    def knowledge_node(state: TaraState) -> Dict:
        """Serve every pending request; consume them; bump the round count."""
        requests = state.get("knowledge_requests", [])
        context: List[RetrievedRecord] = list(state.get("retrieved_context", []))
        log: List[RetrievalLogEntry] = list(state.get("retrieval_log", []))
        errors: List[str] = list(state.get("errors", []))
        for req in requests:
            query = maybe_rewrite(req.get("query", ""))
            filters = req.get("filters", {})
            top_k = req.get("top_k", 5)
            try:
                hits = _apply_filters(
                    store.retrieve(query, top_k=top_k, category=filters.get("stride_category")),
                    filters,
                )
            except Exception as exc:
                errors.append(f"retrieval failed for {query!r}: {exc}")
                hits = []
            if not hits:
                context.append({"id": NO_MATCH_ID,
                                "text": f"No library records matched query {query!r}.",
                                "source": ""})
            for hit in hits:
                context.append({"id": hit["id"], "text": hit.get("text", ""),
                                "source": hit["id"]})
            log.append({"query": query, "filters": filters,
                        "returned_ids": [h["id"] for h in hits]})
        return {"retrieved_context": context, "retrieval_log": log,
                "knowledge_requests": [], "errors": errors,
                "rounds": state.get("rounds", 0) + 1}

    return knowledge_node
