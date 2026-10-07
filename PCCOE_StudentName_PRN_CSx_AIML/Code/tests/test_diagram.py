"""Step-1 dashboard helpers: trust boundaries, data flows, SVG diagram."""

import json
from pathlib import Path

from app.schemas import Architecture
from app.services.assets import data_flows, trust_boundaries
from ui.diagram import render_architecture_svg

ARCH = json.loads(
    (Path(__file__).resolve().parents[2] / "Input_Data" / "tcu_architecture.json").read_text(encoding="utf-8")
)


def test_trust_boundaries_group_and_order():
    """External-facing boundary first; every component appears exactly once."""
    groups = trust_boundaries(Architecture.model_validate(ARCH))
    assert groups[0]["boundary"] == "External Facing"
    names = [n for g in groups for n in g["components"]]
    assert sorted(names) == sorted(c["name"] for c in ARCH["components"])


def test_data_flows_mirror_interfaces():
    """One flow per interface, readable as source -> destination."""
    flows = data_flows(Architecture.model_validate(ARCH))
    assert len(flows) == len(ARCH["interfaces"])
    assert all("→" in f["flow"] for f in flows)


def test_diagram_contains_all_components_and_legend():
    """SVG names every component and ships the edge-colour legend."""
    svg = render_architecture_svg(Architecture.model_validate(ARCH))
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    for comp in ARCH["components"]:
        assert comp["name"][:22] in svg
    for label in ("External", "Vehicle internal", "Diagnostic/service"):
        assert label in svg
    assert svg.count("<path d=") >= len(ARCH["interfaces"])
