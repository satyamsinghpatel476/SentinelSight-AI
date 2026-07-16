from __future__ import annotations

from urllib.parse import SplitResult, quote, unquote, urlsplit, urlunsplit

from fastapi import HTTPException, status

ALLOWED_SCHEMES = {"http", "https"}


def normalize_public_url(raw_url: str) -> str:
    """Normalize a user-supplied public URL before storage.

    This is the registration-time validation layer. DNS/IP SSRF checks are added in the scanner
    milestone, but unsafe protocols, malformed hosts and embedded credentials are blocked here.
    """

    candidate = raw_url.strip()
    if not candidate:
        raise invalid_url("URL is required")

    try:
        parsed = urlsplit(candidate)
    except ValueError as exc:
        raise invalid_url("Malformed URL") from exc

    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise invalid_url("Only http and https URLs are supported")

    if parsed.username or parsed.password:
        raise invalid_url("URLs with embedded usernames or passwords are not allowed")

    hostname = normalize_hostname(parsed)
    port = normalize_port(parsed)
    path = quote(unquote(parsed.path or "/"), safe="/:@")
    query = parsed.query
    netloc = f"{hostname}:{port}" if port else hostname

    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_hostname(parsed: SplitResult) -> str:
    hostname = parsed.hostname
    if not hostname:
        raise invalid_url("URL must include a hostname")
    try:
        return hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise invalid_url("Hostname is invalid") from exc


def normalize_port(parsed: SplitResult) -> int | None:
    try:
        port = parsed.port
    except ValueError as exc:
        raise invalid_url("Port is invalid") from exc

    if port is None:
        return None
    if parsed.scheme.lower() == "http" and port == 80:
        return None
    if parsed.scheme.lower() == "https" and port == 443:
        return None
    return port


def invalid_url(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message
    )
