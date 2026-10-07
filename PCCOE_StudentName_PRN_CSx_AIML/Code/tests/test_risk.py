"""Risk matrix: shape, lookup, aggregation, and threat assessment."""

from app.schemas import FeasibilityAssessment, ImpactAssessment, ThreatScenario
from app.services.risk import assess_threat, feasibility_value, impact_value, load_matrix, risk_value


def test_matrix_is_5x5_within_range():
    """Config matrix must be 5x5 with risk values 0-5."""
    m = load_matrix()
    assert len(m) == 5 and all(len(row) == 5 for row in m)
    assert all(0 <= v <= 5 for row in m for v in row)


def test_impact_takes_max_category():
    """Impact value is the worst of Safety/Financial/Operational/Privacy."""
    imp = ImpactAssessment(safety=2, financial=4, operational=1, privacy=0)
    assert impact_value(imp) == 4


def test_risk_corners_and_clamping():
    """Negligible x very-low is 0; severe x very-high is maximal; out-of-range clamps."""
    m = load_matrix()
    assert risk_value(0, 0, m) == 0
    assert risk_value(4, 4, m) == max(v for row in m for v in row)
    assert risk_value(99, -1, m) == risk_value(4, 0, m)


def test_assess_threat_propagates_expert_review():
    """Uncited threats produce risks flagged for expert review."""
    t = ThreatScenario(
        id="T1", title="t", description="d", stride_category="Tampering",
        impact=ImpactAssessment(safety=3), feasibility=FeasibilityAssessment(expertise=2),
    )
    t.status = "needs_expert_review"  # plain string on purpose: service must tolerate both str and enum
    r = assess_threat(t)
    assert r.threat_id == "T1"
    assert r.impact_value == 3 and r.feasibility_value == 2
    assert r.needs_expert_review is True
