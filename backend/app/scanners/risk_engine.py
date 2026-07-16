from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import RiskLevel
from app.scanners.header_analyzer import PassiveFinding


@dataclass(frozen=True)
class RiskResult:
    risk_score: int
    risk_level: RiskLevel
    risk_breakdown: list[dict[str, object]]


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
    if visual_change_level == "major":
        add(
            breakdown,
            "Major visual change",
            35,
            f"{visual_change_percent:.2f}% meaningful screenshot change",
        )
    elif visual_change_level == "moderate":
        add(
            breakdown,
            "Moderate visual change",
            20,
            f"{visual_change_percent:.2f}% meaningful screenshot change",
        )

    for phrase in suspicious_phrases:
        add(breakdown, "Suspicious defacement phrase", 25, f"Detected phrase: {phrase}")

    if text_similarity_percent is not None:
        if text_similarity_percent < 50:
            add(
                breakdown,
                "Visible-text similarity below 50 percent",
                15,
                f"Similarity: {text_similarity_percent:.2f}%",
            )
        elif text_similarity_percent < 75:
            add(
                breakdown,
                "Visible-text similarity below 75 percent",
                8,
                f"Similarity: {text_similarity_percent:.2f}%",
            )

    if new_external_script_domains:
        add(
            breakdown,
            "New external script domain",
            15,
            ", ".join(new_external_script_domains),
        )
    if new_external_iframe_domains:
        add(
            breakdown,
            "New iframe domain",
            12,
            ", ".join(new_external_iframe_domains),
        )
    if title_changed:
        add(
            breakdown,
            "Page title changed significantly",
            8,
            "Current title differs from baseline",
        )

    finding_types = {finding.finding_type for finding in findings}
    passive_weights = {
        "http_instead_of_https": ("HTTP instead of HTTPS", 10),
        "missing_content_security_policy": ("Missing Content-Security-Policy", 8),
        "missing_hsts": ("Missing Strict-Transport-Security on HTTPS", 8),
        "missing_x_content_type_options": ("Missing X-Content-Type-Options", 5),
        "missing_clickjacking_protection": ("Missing clickjacking protection", 10),
        "weak_permissions_policy": ("Missing Permissions-Policy", 5),
        "server_version_disclosure": ("Server-version disclosure", 3),
        "http_5xx_response": ("HTTP 5xx", 12),
    }
    for finding_type, (reason, points) in passive_weights.items():
        if finding_type in finding_types:
            add(breakdown, reason, points, finding_type)

    score = min(100, sum(int(item["points"]) for item in breakdown))
    return RiskResult(score, risk_level_for_score(score), breakdown)


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
