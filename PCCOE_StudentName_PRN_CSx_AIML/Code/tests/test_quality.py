"""Brush-up: verifications, quality metrics, lifecycle staleness."""

from datetime import date

from fastapi.testclient import TestClient

from app.db import MitigationRow, init_db, session_scope
from app.main import app
from app.schemas import Asset, Mitigation, Risk, ThreatScenario, VerificationLink
from app.services.lifecycle import mapping_status
from app.services.traceability import build_traceability, compute_metrics

client = TestClient(app)


def _chain():
    assets = [Asset(id="A1", name="FW", description="d", source_ids=["THREAT-001"])]
    threats = [ThreatScenario(id="T1", title="t", description="d", stride_category="Tampering",
                              affected_assets=["A1"], source_ids=["THREAT-001"])]
    risks = [Risk(id="R1", threat_id="T1", impact_value=3, feasibility_value=2, risk_value=3)]
    mits = [Mitigation(id="M1", threat_id="T1", description="d", cybersecurity_requirement="req",
                       source_ids=["THREAT-001"])]
    return assets, threats, risks, mits


def test_verification_create_review_and_trace():
    """Link a verification, approve it, and see it in the trace chain."""
    init_db()
    with session_scope() as s:
        s.add(MitigationRow(id="M1", threat_id="T1", description="d", cybersecurity_requirement="req"))
    created = client.post("/verifications", json={"id": "VER-M1-1", "mitigation_id": "M1",
                                                  "test_method": "HIL fault injection",
                                                  "reviewer": "qa"}).json()
    assert created["status_detail"] == "planned"
    assert client.post("/verifications", json={"id": "VER-M1-1", "mitigation_id": "M1",
                                               "test_method": "x"}).status_code == 422
    assert client.post("/verifications", json={"id": "VER-X", "mitigation_id": "NOPE",
                                               "test_method": "x"}).status_code == 422
    assert client.post("/review/verification/VER-M1-1",
                       json={"decision": "approve", "reviewer": "qa"}).json()["status"] == "approved"
    assets, threats, risks, mits = _chain()
    vers = [VerificationLink(id="VER-M1-1", mitigation_id="M1", test_method="HIL fault injection")]
    report = build_traceability(assets, threats, risks, mits, vers)
    assert report.links[0].verification_ids == ["VER-M1-1"]
    assert not [g for g in report.gaps if g.kind == "mitigation_without_verification"]


def test_metrics_definitions():
    """Reuse/completion/completeness match their documented definitions."""
    assets, threats, risks, mits = _chain()
    m = compute_metrics(assets, threats, risks, mits, [])
    assert (m.knowledge_reuse_pct, m.review_completion_pct) == (100.0, 0.0)
    assert m.chain_completeness_pct == 100.0
    assert any(g.kind == "mitigation_without_verification" for g in
               build_traceability(assets, threats, risks, mits, []).gaps)
    assert compute_metrics([], [], [], [], []).knowledge_reuse_pct == 0.0


def test_mapping_status_fresh_stale_missing():
    """Fresh mapping passes; old or dateless mappings are stale."""
    assert mapping_status({"mapping_owner": "team", "mapping_review_date": date.today().isoformat()},
                          today=date.today()) == {"owner": "team", "review_date": date.today().isoformat(),
                                                  "stale": False}
    assert mapping_status({"mapping_review_date": "2020-01-01"}, today=date.today())["stale"] is True
    assert mapping_status({}, today=date.today()) == {"owner": "unassigned", "review_date": "missing",
                                                      "stale": True}
