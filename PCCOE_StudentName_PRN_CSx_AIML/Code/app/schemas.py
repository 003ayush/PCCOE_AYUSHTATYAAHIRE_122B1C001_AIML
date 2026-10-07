"""Pydantic schemas for the TARA domain.

Every reviewable artefact carries an approval-status mixin so the
human-in-the-loop gate (approve / edit / reject / needs expert review)
is enforced at the schema level.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class SecurityProperty(str, Enum):
    """Security properties a security goal can protect (CIA + authenticity + non-repudiation)."""

    CONFIDENTIALITY = "Confidentiality"
    INTEGRITY = "Integrity"
    AVAILABILITY = "Availability"
    AUTHENTICITY = "Authenticity"
    NON_REPUDIATION = "Non-repudiation"


class StrideCategory(str, Enum):
    """STRIDE threat taxonomy."""

    SPOOFING = "Spoofing"
    TAMPERING = "Tampering"
    REPUDIATION = "Repudiation"
    INFORMATION_DISCLOSURE = "Information Disclosure"
    DENIAL_OF_SERVICE = "Denial of Service"
    ELEVATION_OF_PRIVILEGE = "Elevation of Privilege"


class ApprovalStatus(str, Enum):
    """Lifecycle state of any AI-suggested artefact."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_EXPERT_REVIEW = "needs_expert_review"


class ImpactRating(int, Enum):
    """Impact level per category, 0 (negligible) to 4 (severe)."""

    NEGLIGIBLE = 0
    MINOR = 1
    MODERATE = 2
    MAJOR = 3
    SEVERE = 4


def _normalize_enum(value, enum_cls, aliases=None):
    """Match LLM output loosely: case-insensitive, known aliases, numeric strings.

    Returns the canonical member, or None when nothing matches (caller drops it).
    """
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return enum_cls(value) if value in {m.value for m in enum_cls} else None
    if isinstance(value, str):
        text = value.strip().lower().replace("_", " ").replace("-", " ")
        for member in enum_cls:
            if text == (member.value if isinstance(member.value, str) else str(member.value)).lower():
                return member
        for alias, member in (aliases or {}).items():
            if text == alias:
                return member
    return None


class FeasibilityRating(int, Enum):
    """Attack feasibility level, 0 (very low) to 4 (high)."""

    VERY_LOW = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


class ReviewFields(BaseModel):
    """Approval metadata attached to every reviewable artefact."""

    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer: Optional[str] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class CitationMixin(BaseModel):
    """Traceability to approved library sources; empty means uncited."""

    source_ids: List[str] = Field(default_factory=list)


class Interface(BaseModel):
    """A communication link between two endpoints."""

    id: str
    name: str
    source: str
    destination: str
    protocol: str
    description: str


class Component(BaseModel):
    """An architectural component and the trust boundary it sits in."""

    id: str
    name: str
    description: str
    trust_boundary: str


class Architecture(BaseModel):
    """System architecture: components and their interfaces."""

    components: List[Component]
    interfaces: List[Interface]


class Asset(ReviewFields, CitationMixin):
    """A valuable system asset requiring protection."""

    id: str
    name: str
    description: str
    security_properties_required: List[SecurityProperty] = Field(default_factory=list)

    @field_validator("security_properties_required", mode="before")
    @classmethod
    def _clean_properties(cls, values):
        """Keep what maps to the CIA+A+NR set; drop the rest (e.g. LLM's "safety")."""
        if values is None:
            return []
        cleaned = [
            _normalize_enum(v, SecurityProperty,
                            {"nonrepudiation": SecurityProperty.NON_REPUDIATION,
                             "non repudiation": SecurityProperty.NON_REPUDIATION})
            for v in (values if isinstance(values, list) else [values])
        ]
        return [v for v in cleaned if v is not None]


class ImpactAssessment(BaseModel):
    """Impact across the four ISO/SAE 21434 categories."""

    safety: ImpactRating = ImpactRating.NEGLIGIBLE
    financial: ImpactRating = ImpactRating.NEGLIGIBLE
    operational: ImpactRating = ImpactRating.NEGLIGIBLE
    privacy: ImpactRating = ImpactRating.NEGLIGIBLE

    @field_validator("safety", "financial", "operational", "privacy", mode="before")
    @classmethod
    def _clean_rating(cls, value):
        """Accept ints, numeric strings, and word labels ("high" -> 3)."""
        word_map = {"negligible": 0, "minor": 1, "moderate": 2, "major": 3, "severe": 4,
                    "low": 1, "medium": 2, "high": 3}  # loose LLM synonyms
        if isinstance(value, str):
            text = value.strip().lower()
            if text in word_map:
                return word_map[text]
            return int(text) if text.lstrip("-").isdigit() else 0
        return value if isinstance(value, int) else 0


class FeasibilityAssessment(BaseModel):
    """Attack feasibility from exploitability factors (ISO/SAE 21434)."""

    elapsed_time: FeasibilityRating = FeasibilityRating.VERY_LOW
    expertise: FeasibilityRating = FeasibilityRating.VERY_LOW
    knowledge: FeasibilityRating = FeasibilityRating.VERY_LOW
    window_of_opportunity: FeasibilityRating = FeasibilityRating.VERY_LOW
    equipment: FeasibilityRating = FeasibilityRating.VERY_LOW

    @field_validator("elapsed_time", "expertise", "knowledge", "window_of_opportunity",
                     "equipment", mode="before")
    @classmethod
    def _clean_rating(cls, value):
        """Accept ints, numeric strings, and word labels ("low" -> 1)."""
        word_map = {"very low": 0, "low": 1, "medium": 2, "high": 3, "very high": 4}
        if isinstance(value, str):
            text = value.strip().lower()
            if text in word_map:
                return word_map[text]
            return int(text) if text.lstrip("-").isdigit() else 0
        return value if isinstance(value, int) else 0


class ThreatScenario(ReviewFields, CitationMixin):
    """A concrete threat scenario against one or more assets."""

    id: str
    title: str
    description: str
    stride_category: StrideCategory
    affected_assets: List[str] = Field(default_factory=list)
    impact: ImpactAssessment = Field(default_factory=ImpactAssessment)
    feasibility: FeasibilityAssessment = Field(default_factory=FeasibilityAssessment)

    @field_validator("stride_category", mode="before")
    @classmethod
    def _clean_stride(cls, value):
        """Accept any capitalisation ("spoofing" -> Spoofing); reject the rest loudly."""
        cleaned = _normalize_enum(value, StrideCategory)
        if cleaned is None:
            raise ValueError(f"Unrecognised STRIDE category: {value!r}")
        return cleaned


class Risk(ReviewFields):
    """Risk derived from a threat's impact and feasibility via a configurable matrix."""

    id: str
    threat_id: str
    impact_value: int = Field(default=0, ge=0, le=4)
    feasibility_value: int = Field(default=0, ge=0, le=4)
    risk_value: int = Field(default=0, ge=0, le=5)
    rationale: str = ""
    needs_expert_review: bool = False


class Mitigation(ReviewFields, CitationMixin):
    """A mitigation / cybersecurity requirement addressing a threat."""

    id: str
    threat_id: str
    description: str
    cybersecurity_requirement: str


class AuditEntry(BaseModel):
    """Immutable audit record: who approved/edited/rejected what, when, why."""

    id: Optional[int] = None
    item_type: str
    item_id: str
    action: str  # approved | rejected | edited | created | needs_expert_review
    reviewer: str
    note: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaraReport(BaseModel):
    """Aggregate TARA artefact for one architecture."""

    architecture: Architecture
    assets: List[Asset]
    threats: List[ThreatScenario]
    risks: List[Risk] = Field(default_factory=list)
    mitigations: List[Mitigation]


class ExposedInterface(BaseModel):
    """An interface reachable by an attacker, with the reason why."""

    interface: Interface
    reason: str


class TraceLink(BaseModel):
    """One asset -> threat -> risk -> mitigations -> verifications chain."""

    asset_id: str
    threat_id: str
    risk_id: Optional[str] = None
    mitigation_ids: List[str] = Field(default_factory=list)
    verification_ids: List[str] = Field(default_factory=list)


class TraceGap(BaseModel):
    """A break in the traceability chain needing reviewer attention."""

    kind: str  # asset_without_threat | threat_without_risk | threat_without_mitigation | mitigation_without_verification | uncited | pending_review
    item_id: str
    detail: str = ""


class TraceabilityReport(BaseModel):
    """Full chain links plus every gap found."""

    links: List[TraceLink] = Field(default_factory=list)
    gaps: List[TraceGap] = Field(default_factory=list)


class VerificationStatus(str, Enum):
    """Test execution state of a verification link."""

    PLANNED = "planned"
    PASSED = "passed"
    FAILED = "failed"


class VerificationLink(ReviewFields):
    """A test/verification activity covering a mitigation (PROJECT.md step 21)."""

    id: str
    mitigation_id: str
    test_method: str
    status_detail: VerificationStatus = VerificationStatus.PLANNED
    note: str = ""


class QualityMetrics(BaseModel):
    """PROJECT.md success metrics computed from stored data."""

    total_assets: int = 0
    total_threats: int = 0
    total_mitigations: int = 0
    knowledge_reuse_pct: float = 0.0
    review_completion_pct: float = 0.0
    chain_completeness_pct: float = 0.0
    open_gaps: int = 0
