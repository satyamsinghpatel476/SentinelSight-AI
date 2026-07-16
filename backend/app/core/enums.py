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


class RiskLevel(StrEnum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class IncidentStatus(StrEnum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    false_positive = "false_positive"


class AIProvider(StrEnum):
    gemini = "gemini"
    openai = "openai"
    openai_compatible = "openai_compatible"


class AIAnalysisStatus(StrEnum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
