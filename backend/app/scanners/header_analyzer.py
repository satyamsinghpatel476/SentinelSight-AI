from __future__ import annotations

import re
from dataclasses import dataclass
from http.cookies import SimpleCookie
from urllib.parse import urlsplit

from app.core.enums import FindingSeverity


@dataclass(frozen=True)
class PassiveFinding:
    finding_type: str
    title: str
    description: str
    severity: FindingSeverity
    evidence: str
    remediation: str
    risk_points: int


SESSION_COOKIE_HINTS = ("session", "sid", "auth", "token", "jwt")


def analyze_security_headers(
    final_url: str,
    status_code: int,
    headers: dict[str, str],
    set_cookie_headers: list[str],
) -> list[PassiveFinding]:
    """Run deterministic passive security checks over HTTP response metadata."""

    header_map = {name.lower(): value for name, value in headers.items()}
    findings: list[PassiveFinding] = []
    scheme = urlsplit(final_url).scheme.lower()

    if scheme == "http":
        findings.append(
            finding(
                "http_instead_of_https",
                "Website is served over HTTP",
                "The scanned page was reachable over plaintext HTTP.",
                FindingSeverity.high,
                f"Final URL: {final_url}",
                "Redirect all traffic to HTTPS and enable HSTS after HTTPS is deployed.",
                25,
            )
        )

    if status_code >= 500:
        findings.append(
            finding(
                "http_5xx_response",
                "Server returned an HTTP 5xx response",
                "The target returned a server-side error during the scan.",
                FindingSeverity.high,
                f"HTTP status: {status_code}",
                "Review server logs and fix the failing route before relying on monitoring data.",
                20,
            )
        )

    content_security_policy = header_map.get("content-security-policy")
    if not content_security_policy:
        findings.append(
            finding(
                "missing_content_security_policy",
                "Missing Content-Security-Policy",
                "The response does not declare a Content-Security-Policy header.",
                FindingSeverity.moderate,
                "Content-Security-Policy header not present",
                "Add a restrictive Content-Security-Policy suited to the application.",
                12,
            )
        )

    if scheme == "https" and "strict-transport-security" not in header_map:
        findings.append(
            finding(
                "missing_hsts",
                "Missing Strict-Transport-Security",
                "The HTTPS response does not declare HSTS.",
                FindingSeverity.moderate,
                "Strict-Transport-Security header not present",
                "Add Strict-Transport-Security after validating all subdomains support HTTPS.",
                12,
            )
        )

    if header_map.get("x-content-type-options", "").lower() != "nosniff":
        findings.append(
            finding(
                "missing_x_content_type_options",
                "Missing X-Content-Type-Options",
                "The response does not prevent MIME type sniffing.",
                FindingSeverity.low,
                "X-Content-Type-Options: nosniff not present",
                "Set X-Content-Type-Options to nosniff.",
                6,
            )
        )

    if "x-frame-options" not in header_map and not has_frame_ancestors(
        content_security_policy
    ):
        findings.append(
            finding(
                "missing_clickjacking_protection",
                "Missing clickjacking protection",
                "The response lacks X-Frame-Options and CSP frame-ancestors.",
                FindingSeverity.moderate,
                "No X-Frame-Options header and no CSP frame-ancestors directive",
                "Set frame-ancestors in CSP or add X-Frame-Options DENY/SAMEORIGIN.",
                10,
            )
        )

    if "referrer-policy" not in header_map:
        findings.append(
            finding(
                "missing_referrer_policy",
                "Missing Referrer-Policy",
                "The response does not define how much referrer data browsers may send.",
                FindingSeverity.low,
                "Referrer-Policy header not present",
                "Set Referrer-Policy to strict-origin-when-cross-origin or stricter.",
                5,
            )
        )

    permissions_policy = header_map.get("permissions-policy")
    if not permissions_policy or "*" in permissions_policy:
        findings.append(
            finding(
                "weak_permissions_policy",
                "Weak or missing Permissions-Policy",
                "The response does not limit powerful browser features.",
                FindingSeverity.low,
                f"Permissions-Policy: {permissions_policy or 'not present'}",
                "Declare a Permissions-Policy that disables unused browser capabilities.",
                5,
            )
        )

    findings.extend(analyze_cors(header_map))
    findings.extend(analyze_server_header(header_map))
    findings.extend(analyze_cookies(scheme, set_cookie_headers))
    return findings


def analyze_cors(header_map: dict[str, str]) -> list[PassiveFinding]:
    allow_origin = header_map.get("access-control-allow-origin")
    allow_credentials = header_map.get("access-control-allow-credentials", "").lower()
    if allow_origin == "*" and allow_credentials == "true":
        return [
            finding(
                "unsafe_cors",
                "Unsafe CORS configuration",
                "The response allows any origin while also allowing credentials.",
                FindingSeverity.high,
                "Access-Control-Allow-Origin: * with Access-Control-Allow-Credentials: true",
                "Use an explicit allowlist of trusted origins and avoid wildcard credentials.",
                22,
            )
        ]
    if allow_origin == "*":
        return [
            finding(
                "wildcard_cors",
                "Wildcard CORS origin",
                "The response allows cross-origin reads from any origin.",
                FindingSeverity.low,
                "Access-Control-Allow-Origin: *",
                "Use a narrow origin allowlist when cross-origin reads are required.",
                5,
            )
        ]
    return []


def analyze_server_header(header_map: dict[str, str]) -> list[PassiveFinding]:
    server_header = header_map.get("server")
    if not server_header:
        return []
    if re.search(r"/\d|\d+\.\d+", server_header):
        return [
            finding(
                "server_version_disclosure",
                "Server version disclosure",
                "The Server header appears to expose product version information.",
                FindingSeverity.low,
                f"Server: {server_header}",
                "Configure the web server or reverse proxy to remove detailed version banners.",
                4,
            )
        ]
    return []


def analyze_cookies(
    scheme: str,
    set_cookie_headers: list[str],
) -> list[PassiveFinding]:
    findings: list[PassiveFinding] = []
    for header in set_cookie_headers:
        cookie = SimpleCookie()
        try:
            cookie.load(header)
        except Exception:
            continue
        for morsel in cookie.values():
            name = morsel.key
            if not is_session_like_cookie(name):
                continue
            attrs = {key.lower(): morsel[key] for key in morsel if morsel[key]}
            if scheme == "https" and "secure" not in attrs:
                findings.append(
                    cookie_finding(
                        "session_cookie_missing_secure",
                        "Session-like cookie missing Secure",
                        name,
                        "Set the Secure attribute on session-like cookies served over HTTPS.",
                        10,
                    )
                )
            if "httponly" not in attrs:
                findings.append(
                    cookie_finding(
                        "session_cookie_missing_httponly",
                        "Session-like cookie missing HttpOnly",
                        name,
                        "Set the HttpOnly attribute on session-like cookies.",
                        10,
                    )
                )
            same_site = attrs.get("samesite", "").lower()
            if same_site not in {"lax", "strict"}:
                findings.append(
                    cookie_finding(
                        "weak_or_missing_samesite",
                        "Weak or missing SameSite on session-like cookie",
                        name,
                        "Set SameSite=Lax or SameSite=Strict on session-like cookies.",
                        8,
                    )
                )
    return findings


def is_session_like_cookie(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in SESSION_COOKIE_HINTS)


def has_frame_ancestors(content_security_policy: str | None) -> bool:
    return bool(
        content_security_policy and "frame-ancestors" in content_security_policy.lower()
    )


def finding(
    finding_type: str,
    title: str,
    description: str,
    severity: FindingSeverity,
    evidence: str,
    remediation: str,
    risk_points: int,
) -> PassiveFinding:
    return PassiveFinding(
        finding_type=finding_type,
        title=title,
        description=description,
        severity=severity,
        evidence=evidence,
        remediation=remediation,
        risk_points=risk_points,
    )


def cookie_finding(
    finding_type: str,
    title: str,
    cookie_name: str,
    remediation: str,
    risk_points: int,
) -> PassiveFinding:
    return finding(
        finding_type,
        title,
        "A session-like Set-Cookie header is missing a recommended browser control.",
        FindingSeverity.moderate,
        f"Cookie name: {cookie_name}",
        remediation,
        risk_points,
    )
