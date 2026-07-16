from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit

from fastapi import HTTPException

from app.core.config import get_settings
from app.security.url_normalization import ALLOWED_SCHEMES, normalize_public_url

METADATA_IPS = {ipaddress.ip_address("169.254.169.254")}
FORBIDDEN_HOSTNAMES = {
    "localhost",
    "metadata",
    "metadata.google.internal",
    "instance-data",
    "169.254.169.254",
}
CONTROLLED_DEMO_TARGET_HOSTNAME = "demo-target"


class UnsafeUrlError(ValueError):
    pass


@dataclass(frozen=True)
class SafeUrl:
    normalized_url: str
    hostname: str
    resolved_ips: tuple[str, ...]
    demo_target_exception: bool = False


@dataclass(frozen=True)
class UrlSafetyPolicy:
    allow_internal_demo_target: bool = False
    demo_target_internal_url: str = "http://demo-target:9000"
    is_production: bool = False


Resolver = Callable[[str], list[ipaddress.IPv4Address | ipaddress.IPv6Address]]


def current_url_safety_policy() -> UrlSafetyPolicy:
    settings = get_settings()
    return UrlSafetyPolicy(
        allow_internal_demo_target=settings.allow_internal_demo_target,
        demo_target_internal_url=settings.demo_target_internal_url,
        is_production=settings.is_production,
    )


def validate_url_for_scanning(
    raw_url: str,
    resolver: Resolver | None = None,
    policy: UrlSafetyPolicy | None = None,
) -> SafeUrl:
    policy = policy or current_url_safety_policy()
    if policy.is_production and policy.allow_internal_demo_target:
        raise UnsafeUrlError(
            "Internal demo target exception is not allowed in production"
        )

    try:
        normalized_url = normalize_public_url(raw_url)
    except HTTPException as exc:
        raise UnsafeUrlError(str(exc.detail)) from exc
    parsed = urlsplit(normalized_url)
    hostname = normalized_hostname(parsed)
    demo_exception = is_exact_demo_target(parsed, policy)
    if not demo_exception:
        reject_forbidden_hostname(hostname)

    resolved_ips = resolve_all_ips(hostname) if resolver is None else resolver(hostname)
    if not resolved_ips:
        raise UnsafeUrlError("Hostname did not resolve to any IP address")

    for ip_address in resolved_ips:
        if not demo_exception:
            reject_forbidden_ip(ip_address)

    return SafeUrl(
        normalized_url=normalized_url,
        hostname=hostname,
        resolved_ips=tuple(str(ip_address) for ip_address in resolved_ips),
        demo_target_exception=demo_exception,
    )


def validate_redirect_target(
    redirect_url: str,
    resolver: Resolver | None = None,
    policy: UrlSafetyPolicy | None = None,
) -> SafeUrl:
    return validate_url_for_scanning(redirect_url, resolver=resolver, policy=policy)


def resolve_all_ips(
    hostname: str,
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    direct_ip = parse_ip(hostname)
    if direct_ip is not None:
        return [direct_ip]

    try:
        records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError("Hostname could not be resolved") from exc

    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for record in records:
        raw_ip = record[4][0]
        parsed_ip = parse_ip(raw_ip)
        if parsed_ip is not None and parsed_ip not in addresses:
            addresses.append(parsed_ip)
    return addresses


def normalized_hostname(parsed: SplitResult) -> str:
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError("Only http and https URLs are supported")
    if parsed.username or parsed.password:
        raise UnsafeUrlError(
            "URLs with embedded usernames or passwords are not allowed"
        )
    if not parsed.hostname:
        raise UnsafeUrlError("URL must include a hostname")
    try:
        return parsed.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise UnsafeUrlError("Hostname is invalid") from exc


def reject_forbidden_hostname(hostname: str) -> None:
    if hostname in FORBIDDEN_HOSTNAMES:
        raise UnsafeUrlError("Hostname is reserved for local or metadata access")
    if parse_ip(hostname) is None and "." not in hostname:
        raise UnsafeUrlError("Internal-only hostnames are not allowed")


def is_exact_demo_target(parsed: SplitResult, policy: UrlSafetyPolicy) -> bool:
    if not policy.allow_internal_demo_target:
        return False
    configured = urlsplit(policy.demo_target_internal_url)
    if configured.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError("Configured demo target URL must use http or https")
    configured_hostname = normalized_hostname(configured)
    if configured_hostname != CONTROLLED_DEMO_TARGET_HOSTNAME:
        raise UnsafeUrlError(
            "Configured demo target URL must use the controlled demo-target hostname"
        )
    try:
        parsed_port = parsed.port or default_port(parsed.scheme)
        configured_port = configured.port or default_port(configured.scheme)
    except ValueError as exc:
        raise UnsafeUrlError("Configured demo target port is invalid") from exc
    return (
        parsed.scheme.lower() == configured.scheme.lower()
        and normalized_hostname(parsed) == configured_hostname
        and parsed_port == configured_port
    )


def default_port(scheme: str) -> int:
    return 443 if scheme.lower() == "https" else 80


def reject_forbidden_ip(
    ip_address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> None:
    if ip_address in METADATA_IPS:
        raise UnsafeUrlError("Cloud metadata addresses are not allowed")
    if (
        ip_address.is_private
        or ip_address.is_loopback
        or ip_address.is_link_local
        or ip_address.is_multicast
        or ip_address.is_reserved
        or ip_address.is_unspecified
    ):
        raise UnsafeUrlError("Private, local, reserved or otherwise unsafe IP address")


def parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None
