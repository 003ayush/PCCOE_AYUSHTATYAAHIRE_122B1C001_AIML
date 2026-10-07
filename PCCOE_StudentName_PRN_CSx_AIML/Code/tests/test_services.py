"""Services: architecture parsing, attack surface, review/audit, traceability."""

import pytest

from app.db import AssetRow, init_db, session_scope
from app.schemas import Architecture, Asset, Mitigation, Risk, ThreatScenario
from app.services.architecture import parse_architecture
from app.services.assets import attack_surface
from app.services.review import apply_review
from app.services.traceability import build_traceability, render_markdown

ARCH = {
    "components": [
        {"id": "C-1", "name": "Modem", "description": "cellular", "trust_boundary": "External Facing"},
        {"id": "C-2", "name": "MCU", "description": "main", "trust_boundary": "Internal"},
    ],
    "interfaces": [
        {"id": "I-1", "name": "OTA", "source": "Cloud (External)", "destination": "C-1",
         "protocol": "TLS", "description": "updates"},
        {"id": "I-2", "name": "Bus", "source": "C-1", "destination": "C-2",
         "protocol": "UART", "description": "internal"},
    ],
}


def test_parse_json_and_xml_and_reject_csv():
    """JSON validates; equivalent XML maps; CSV is refused clearly."""
    arch = parse_architecture(__import__("json").dumps(ARCH), "json")
    assert len(arch.components) == 2
    xml = ("<arch><component id='C-1' name='Modem' description='cellular' trust_boundary='External Facing'/>"
           "<interface id='I-1' name='OTA' source='Cloud' destination='C-1' protocol='TLS' description='u'/>"
           "</arch>")
    assert len(parse_architecture(xml, "xml").components) == 1
    with pytest.raises(ValueError):
        parse_architecture("a,b\n1,2", "csv")
    with pytest.raises(ValueError):
        parse_architecture("{bad", "json")


def test_attack_surface_flags_external_only():
    """Interfaces sourced from outside or from an external-facing component are exposed."""
    exposed = attack_surface(Architecture.model_validate(ARCH))
    assert [e.interface.id for e in exposed] == ["I-1", "I-2"]


def test_catalogue_names_live_and_missing(tmp_path):
    """The 12-name catalogue feeds the analyst prompt; absent file gives []."""
    from app.services.assets import catalogue_names
    assert len(catalogue_names()) == 12
    assert catalogue_names(tmp_path / "absent.json") == []


def test_review_approve_writes_audit():
    """Approving an item flips status and appends an audit row."""
    from app.db import AuditLogRow
    init_db()
    with session_scope() as s:
        s.add(AssetRow(id="A-9", name="FW", description="d"))
    with session_scope() as s:
        row = apply_review(s, "asset", "A-9", "approve", "reviewer1", "looks good")
        assert row.status == "approved" and row.reviewer == "reviewer1"
    with session_scope() as s:
        entries = s.query(AuditLogRow).filter_by(item_id="A-9").all()
        assert len(entries) == 1 and entries[0].action == "approve"


def test_review_rejects_unknown_item_and_bad_field():
    """Missing rows raise LookupError; id/status are not editable."""
    init_db()
    with session_scope() as s:
        with pytest.raises(LookupError):
            apply_review(s, "asset", "NOPE", "approve", "r")
        with pytest.raises(ValueError):
            apply_review(s, "bogus", "A-9", "approve", "r")


def test_traceability_links_and_gaps():
    """Linked chains appear; uncovered assets and missing risks appear as gaps."""
    assets = [Asset(id="A1", name="FW", description="d", source_ids=["THREAT-001"])]
    threats = [ThreatScenario(id="T1", title="t", description="d", stride_category="Tampering",
                              affected_assets=["A1"], source_ids=["THREAT-001"])]
    risks = [Risk(id="R1", threat_id="T1", impact_value=3, feasibility_value=2, risk_value=3)]
    mits = [Mitigation(id="M1", threat_id="T1", description="d", cybersecurity_requirement="req",
                       source_ids=["THREAT-001"])]
    report = build_traceability(assets, threats, risks, mits)
    assert report.links[0].asset_id == "A1" and report.links[0].risk_id == "R1"
    md = render_markdown(report)
    assert "A1" in md and "T1" in md
    lonely = build_traceability(
        [Asset(id="A2", name="x", description="d")], [], [], [])
    kinds = {g.kind for g in lonely.gaps}
    assert {"asset_without_threat", "uncited", "pending_review"} <= kinds
