from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import RiskLevel
from app.scanners.header_analyzer import PassiveFinding


@dataclass(frozen=True)
class RiskResult:
    risk_score: int
    risk_level: RiskLevel
    risk_breakdown: list[dict[str, object]]
    finding_point_contributions: list[int]


def calculate_risk(
    *,
    visual_change_level: str | None,
    visual_change_percent: float | None,
    text_similarity_percent: float | None,
    title_changed: bool | None,
    suspicious_phrases: list[str],
    new_external_script_domains: list[str],
    new_external_iframe_domains: list[str],
    findings: list[PassiveFinding],
) -> RiskResult:
    """Calculate a deterministic, explainable scan risk score."""

    breakdown: list[dict[str, object]] = []
    contributions: list[int] = []
    score = 0
    for item in findings:
        raw_points = max(0, item.risk_points)
        contribution = min(raw_points, max(0, 100 - score))
        contributions.append(contribution)
        if contribution <= 0:
            continue
        score += contribution
        add(breakdown, item.title, contribution, item.evidence)
    return RiskResult(score, risk_level_for_score(score), breakdown, contributions)


def risk_level_for_score(score: int) -> RiskLevel:
    if score >= 75:
        return RiskLevel.critical
    if score >= 50:
        return RiskLevel.high
    if score >= 25:
        return RiskLevel.moderate
    return RiskLevel.low


def add(
    breakdown: list[dict[str, object]], reason: str, points: int, evidence: str
) -> None:
    breakdown.append({"reason": reason, "points": points, "evidence": evidence})
