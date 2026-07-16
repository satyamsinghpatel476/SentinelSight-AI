from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import FindingSeverity, IncidentStatus, RiskLevel
from app.models.incident import Incident
from app.models.scan import Scan
from app.services.audit_log import create_audit_log

ACTIVE_INCIDENT_STATUSES = {IncidentStatus.open, IncidentStatus.investigating}


def create_incident_if_needed(
    db: Session,
    *,
    scan: Scan,
) -> Incident | None:
    """Create one automatic incident when comparison evidence crosses a clear threshold."""

    if scan.risk_score is None:
        return None
    threshold = get_settings().incident_risk_threshold
    should_create = (
        scan.risk_score >= threshold
        or bool(scan.suspicious_phrases)
        or (
            scan.visual_change_level == "major"
            and bool(scan.new_external_script_domains)
        )
    )
    if not should_create:
        return None
    existing = db.scalar(select(Incident).where(Incident.scan_id == scan.id))
    if existing is not None:
        return existing

    incident = Incident(
        organization_id=scan.organization_id,
        website_asset_id=scan.website_asset_id,
        scan_id=scan.id,
        title=incident_title(scan),
        description=incident_description(scan),
        severity=severity_for_risk(scan.risk_level),
        risk_score=scan.risk_score,
        risk_breakdown=scan.risk_breakdown,
        status=IncidentStatus.open,
    )
    db.add(incident)
    db.flush()
    create_audit_log(
        db,
        organization_id=scan.organization_id,
        user_id=scan.requested_by,
        action="incident.created",
        resource_type="incident",
        resource_id=incident.id,
        metadata={"scan_id": scan.id, "risk_score": scan.risk_score},
    )
    return incident


def incident_title(scan: Scan) -> str:
    if scan.suspicious_phrases:
        return "Suspicious defacement indicators detected"
    if scan.visual_change_level == "major":
        return "Major website change detected"
    return "High-risk website scan"


def incident_description(scan: Scan) -> str:
    return (
        "SentinelSight created this incident from deterministic scan evidence. "
        "Review the scan findings, screenshots and risk breakdown before taking action."
    )


def severity_for_risk(risk_level: RiskLevel | None) -> FindingSeverity:
    if risk_level == RiskLevel.critical:
        return FindingSeverity.critical
    if risk_level == RiskLevel.high:
        return FindingSeverity.high
    if risk_level == RiskLevel.moderate:
        return FindingSeverity.moderate
    return FindingSeverity.low
