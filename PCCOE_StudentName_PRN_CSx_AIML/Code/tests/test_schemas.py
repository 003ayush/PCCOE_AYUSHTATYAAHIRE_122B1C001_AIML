"""Schema defaults, enums, and architecture validation."""

from app.schemas import (
    ApprovalStatus,
    Architecture,
    Asset,
    FeasibilityRating,
    ImpactRating,
    SecurityProperty,
    StrideCategory,
    ThreatScenario,
)


def test_review_defaults_pending():
    """New suggestions always start pending with no reviewer."""
    a = Asset(id="A1", name="FW", description="d")
    assert a.status == ApprovalStatus.PENDING
    assert a.reviewer is None
    assert a.source_ids == []


def test_security_properties_include_authenticity_and_non_repudiation():
    """Catalogue values (incl. ASSET-05's Non-repudiation) must be accepted."""
    assert SecurityProperty("Authenticity") is SecurityProperty.AUTHENTICITY
    assert SecurityProperty("Non-repudiation") is SecurityProperty.NON_REPUDIATION


def test_llm_output_normalization():
    """Real LLM sloppiness is cleaned, not rejected: case, aliases, word ratings."""
    a = Asset(id="A1", name="FW", description="d",
              security_properties_required=["integrity", "Safety", "nonrepudiation", "bogus"])
    assert a.security_properties_required == [SecurityProperty.INTEGRITY, SecurityProperty.NON_REPUDIATION]
    t = ThreatScenario(id="T", title="t", description="d", stride_category="spoofing",
                       impact={"safety": "high"}, feasibility={"expertise": "2"})
    assert t.stride_category is StrideCategory.SPOOFING
    assert t.impact.safety == ImpactRating.MAJOR and t.feasibility.expertise == FeasibilityRating.MEDIUM


def test_threat_scenario_stride_values():
    """All six STRIDE categories parse."""
    for value in ("Spoofing", "Tampering", "Repudiation", "Information Disclosure",
                  "Denial of Service", "Elevation of Privilege"):
        t = ThreatScenario(id="T", title="t", description="d", stride_category=value)
        assert isinstance(t.stride_category, StrideCategory)


def test_architecture_rejects_bad_shape():
    """Missing components must fail validation with a clear error."""
    try:
        Architecture.model_validate({"interfaces": []})
    except Exception:
        return
    raise AssertionError("expected validation to fail")
