from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    administrator = "administrator"
    security_analyst = "security_analyst"
    viewer = "viewer"


class WebsiteRiskCategory(StrEnum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class ScanStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ScanType(StrEnum):
    baseline = "baseline"
    comparison = "comparison"


class FindingSeverity(StrEnum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"
