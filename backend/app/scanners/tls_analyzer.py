from __future__ import annotations

import socket
import ssl
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from cryptography import x509

from app.core.enums import FindingSeverity
from app.scanners.header_analyzer import PassiveFinding, finding


def analyze_tls_certificate(
    final_url: str,
    timeout_seconds: int,
    now: datetime | None = None,
) -> list[PassiveFinding]:
    """Inspect HTTPS certificate validity without active vulnerability probing."""

    parsed = urlsplit(final_url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return []

    current_time = now or datetime.now(UTC)
    try:
        expires_at = fetch_certificate_expiry(
            parsed.hostname,
            parsed.port or 443,
            timeout_seconds,
        )
    except (OSError, ssl.SSLError, ValueError):
        return [
            finding(
                "tls_certificate_unavailable",
                "TLS certificate could not be inspected",
                (
                    "The scanner could not read the HTTPS certificate. This is "
                    "informational unless other evidence indicates a TLS weakness."
                ),
                FindingSeverity.low,
                f"Host: {parsed.hostname}",
                "Verify network reachability before treating this as a TLS issue.",
                0,
            )
        ]

    if expires_at <= current_time:
        return [
            finding(
                "tls_certificate_expired",
                "TLS certificate expired",
                "The HTTPS certificate is past its validity period.",
                FindingSeverity.critical,
                f"Certificate expired at {expires_at.isoformat()}",
                "Renew and deploy a valid TLS certificate.",
                35,
            )
        ]
    if expires_at <= current_time + timedelta(days=30):
        return [
            finding(
                "tls_certificate_expiring_soon",
                "TLS certificate expires within 30 days",
                "The HTTPS certificate is close to expiration.",
                FindingSeverity.moderate,
                f"Certificate expires at {expires_at.isoformat()}",
                "Renew the certificate before it expires.",
                12,
            )
        ]
    return []


def fetch_certificate_expiry(
    hostname: str,
    port: int,
    timeout_seconds: int,
) -> datetime:
    context = ssl.create_default_context()
    with (
        socket.create_connection((hostname, port), timeout=timeout_seconds) as sock,
        context.wrap_socket(sock, server_hostname=hostname) as tls_sock,
    ):
        der_certificate = tls_sock.getpeercert(binary_form=True)
    if der_certificate is None:
        raise ValueError("Certificate not available")
    certificate = x509.load_der_x509_certificate(der_certificate)
    return certificate.not_valid_after_utc
