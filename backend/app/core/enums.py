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
