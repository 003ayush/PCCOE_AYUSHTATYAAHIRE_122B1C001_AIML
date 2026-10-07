"""Asset and attack-surface analysis services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, TYPE_CHECKING

from app.config import INPUT_DATA_DIR
from app.llm.base import LLMClient
from app.schemas import Architecture, Asset, ExposedInterface
from app.services.llm_json import ensure_drafts_or_raise

if TYPE_CHECKING:  # annotation only: at runtime only agents/knowledge.py touches RAGStore
    from app.rag.store import RAGStore

# Trust boundaries treated as attacker-reachable from outside the item.
EXTERNAL_BOUNDARIES = {"External Facing"}


def catalogue_names(path=None) -> List[str]:
    """Approved catalogue names for the analyst prompt; empty when absent."""
    import json as _json

    path = path or INPUT_DATA_DIR / "asset_catalogue.json"
    try:
        return [a["name"] for a in _json.loads(Path(path).read_text(encoding="utf-8")) if a.get("name")]
    except (OSError, ValueError, AttributeError):
        return []


def suggest_assets(
    client: LLMClient, rag: RAGStore | None = None, architecture: Architecture | None = None, top_k: int = 5
) -> List[Asset]:
    """Propose assets via the analyst/knowledge graph (same schema as before)."""
    from app.agents.graph import run_task

    final = run_task(
        "assets",
        client,
        store=rag,
        variables={
            "architecture": architecture.model_dump_json() if architecture else "{}",
            "catalogue": json.dumps(catalogue_names()),
        },
        initial_requests=[{
            "query": f"vehicle assets {' '.join(c.name for c in architecture.components)}" if architecture else "vehicle assets",
            "filters": {},
            "top_k": top_k,
        }],
    )
    return [Asset.model_validate(d) for d in ensure_drafts_or_raise(final, "asset")]


def attack_surface(architecture: Architecture) -> List[ExposedInterface]:
    """List interfaces touching an external boundary (deterministic, no LLM)."""
    external_ids = {c.id for c in architecture.components if c.trust_boundary in EXTERNAL_BOUNDARIES}
    out = []
    for iface in architecture.interfaces:
        if iface.source in external_ids or "external" in iface.source.lower():
            out.append(ExposedInterface(interface=iface, reason=f"Source '{iface.source}' is outside the trust boundary"))
        elif iface.destination in external_ids:
            out.append(ExposedInterface(interface=iface, reason=f"Destination '{iface.destination}' is externally reachable"))
    return out


def trust_boundaries(architecture: Architecture) -> List[dict]:
    """Group component names by trust boundary, external-facing first."""
    groups: dict[str, list] = {}
    for comp in architecture.components:
        groups.setdefault(comp.trust_boundary, []).append(comp.name)
    ordered = sorted(groups, key=lambda b: (b not in EXTERNAL_BOUNDARIES, b))
    return [{"boundary": b, "components": groups[b]} for b in ordered]


def data_flows(architecture: Architecture) -> List[dict]:
    """Flatten interfaces into numbered source -> destination flows."""
    return [
        {"id": iface.id, "flow": f"{iface.source} → {iface.destination}", "protocol": iface.protocol}
        for iface in architecture.interfaces
    ]
