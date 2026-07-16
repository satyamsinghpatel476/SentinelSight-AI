from __future__ import annotations

from app.security.url_safety import SafeUrl, UrlSafetyPolicy, validate_url_for_scanning


def validate_scan_url(raw_url: str, policy: UrlSafetyPolicy | None = None) -> SafeUrl:
    """Validate a target immediately before scanner network access."""

    return validate_url_for_scanning(raw_url, policy=policy)
