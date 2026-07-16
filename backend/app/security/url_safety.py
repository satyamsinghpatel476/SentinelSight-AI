from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit

from fastapi import HTTPException

from app.security.url_normalization import ALLOWED_SCHEMES, normalize_public_url

METADATA_IPS = {ipaddress.ip_address("169.254.169.254")}
FORBIDDEN_HOSTNAMES = {
    "localhost",
    "metadata",
    "metadata.google.internal",
    "instance-data",
    "169.254.169.254",
}


class UnsafeUrlError(ValueError):
    pass


@dataclass(frozen=True)
class SafeUrl:
    normalized_url: str
    hostname: str
    resolved_ips: tuple[str, ...]


Resolver = Callable[[str], list[ipaddress.IPv4Address | ipaddress.IPv6Address]]


def validate_url_for_scanning(
    raw_url: str, resolver: Resolver | None = None
) -> SafeUrl:
    try:
        normalized_url = normalize_public_url(raw_url)
    except HTTPException as exc:
        raise UnsafeUrlError(str(exc.detail)) from exc
    parsed = urlsplit(normalized_url)
    hostname = normalized_hostname(parsed)
    reject_forbidden_hostname(hostname)

    resolved_ips = resolve_all_ips(hostname) if resolver is None else resolver(hostname)
    if not resolved_ips:
        raise UnsafeUrlError("Hostname did not resolve to any IP address")

    for ip_address in resolved_ips:
        reject_forbidden_ip(ip_address)

    return SafeUrl(
        normalized_url=normalized_url,
        hostname=hostname,
        resolved_ips=tuple(str(ip_address) for ip_address in resolved_ips),
    )


def validate_redirect_target(
    redirect_url: str,
    resolver: Resolver | None = None,
) -> SafeUrl:
    return validate_url_for_scanning(redirect_url, resolver=resolver)


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
