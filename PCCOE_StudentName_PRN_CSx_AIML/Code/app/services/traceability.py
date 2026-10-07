"""Verification links and quality metrics (PROJECT.md steps 21, 11)."""

from __future__ import annotations

from typing import List

from app.schemas import (
    ApprovalStatus,
    Asset,
    Mitigation,
    QualityMetrics,
    Risk,
    ThreatScenario,
    TraceabilityReport,
    TraceGap,
    TraceLink,
    VerificationLink,
)


def _decided(item) -> bool:
    """Approved or rejected counts as reviewed."""
    return item.status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED)


def build_traceability(
    assets: List[Asset],
    threats: List[ThreatScenario],
    risks: List[Risk],
    mitigations: List[Mitigation],
    verifications: List[VerificationLink] | None = None,
) -> TraceabilityReport:
    """Build every asset->threat->risk->mitigations->verifications chain and record all gaps."""
    risk_by_threat = {r.threat_id: r for r in risks}
    mits_by_threat: dict[str, list] = {}
    for m in mitigations:
        mits_by_threat.setdefault(m.threat_id, []).append(m.id)
    vers_by_mit: dict[str, list] = {}
    for v in verifications or []:
        vers_by_mit.setdefault(v.mitigation_id, []).append(v.id)

    links, gaps = [], []
    threatened_assets = set()
    for threat in threats:
        risk = risk_by_threat.get(threat.id)
        if risk is None:
            gaps.append(TraceGap(kind="threat_without_risk", item_id=threat.id))
        mits = mits_by_threat.get(threat.id, [])
        if not mits:
            gaps.append(TraceGap(kind="threat_without_mitigation", item_id=threat.id))
        for asset_id in threat.affected_assets:
            threatened_assets.add(asset_id)
            links.append(
                TraceLink(
                    asset_id=asset_id,
                    threat_id=threat.id,
                    risk_id=risk.id if risk else None,
                    mitigation_ids=mits,
                    verification_ids=[v for m in mits for v in vers_by_mit.get(m, [])],
                )
            )
        if not threat.source_ids:
            gaps.append(TraceGap(kind="uncited", item_id=threat.id, detail="No library source cited"))
        if threat.status in (ApprovalStatus.PENDING, ApprovalStatus.NEEDS_EXPERT_REVIEW):
            gaps.append(TraceGap(kind="pending_review", item_id=threat.id, detail=threat.status.value
                                 if hasattr(threat.status, "value") else str(threat.status)))
    for asset in assets:
        if asset.id not in threatened_assets:
            gaps.append(TraceGap(kind="asset_without_threat", item_id=asset.id))
        if not asset.source_ids:
            gaps.append(TraceGap(kind="uncited", item_id=asset.id, detail="No library source cited"))
        if asset.status in (ApprovalStatus.PENDING, ApprovalStatus.NEEDS_EXPERT_REVIEW):
            gaps.append(TraceGap(kind="pending_review", item_id=asset.id, detail=asset.status.value
                                 if hasattr(asset.status, "value") else str(asset.status)))
    for mit in mitigations:
        if not vers_by_mit.get(mit.id):
            gaps.append(TraceGap(kind="mitigation_without_verification", item_id=mit.id))
    return TraceabilityReport(links=links, gaps=gaps)


def compute_metrics(
    assets: List[Asset],
    threats: List[ThreatScenario],
    risks: List[Risk],
    mitigations: List[Mitigation],
    verifications: List[VerificationLink] | None = None,
) -> QualityMetrics:
    """PROJECT.md §11 metrics: reuse = cited items / all; completion = decided / all;
    completeness = threats with risk + mitigation / all threats."""
    items = [*assets, *threats, *mitigations]
    report = build_traceability(assets, threats, risks, mitigations, verifications)
    complete = sum(1 for t in threats
                   if any(l.threat_id == t.id and l.risk_id and l.mitigation_ids for l in report.links))
    return QualityMetrics(
        total_assets=len(assets),
        total_threats=len(threats),
        total_mitigations=len(mitigations),
        knowledge_reuse_pct=round(100 * sum(1 for i in items if i.source_ids) / len(items), 1) if items else 0.0,
        review_completion_pct=round(100 * sum(1 for i in items if _decided(i)) / len(items), 1) if items else 0.0,
        chain_completeness_pct=round(100 * complete / len(threats), 1) if threats else 0.0,
        open_gaps=len(report.gaps),
    )


def render_markdown(report: TraceabilityReport) -> str:
    """Render the traceability report as Markdown for export."""
    lines = ["# TARA Traceability Report", "", "## Links (asset -> threat -> risk -> mitigations -> verifications)", ""]
    lines += [
        f"- `{lnk.asset_id}` -> `{lnk.threat_id}` -> `{lnk.risk_id or 'no risk'}` -> "
        f"{', '.join(f'`{m}`' for m in lnk.mitigation_ids) or 'no mitigations'} -> "
        f"{', '.join(f'`{v}`' for v in lnk.verification_ids) or 'no verifications'}"
        for lnk in report.links
    ]
    lines += ["", "## Gaps", ""]
    lines += [f"- **{g.kind}**: `{g.item_id}` {g.detail}".rstrip() for g in report.gaps] or ["- None."]
    return "\n".join(lines) + "\n"
