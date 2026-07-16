from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx

from app.core.config import Settings
from app.security.url_safety import (
    UnsafeUrlError,
    UrlSafetyPolicy,
    validate_redirect_target,
    validate_url_for_scanning,
)


class HttpScanError(RuntimeError):
    pass


@dataclass(frozen=True)
class RedirectHop:
    source_url: str
    status_code: int
    location: str


@dataclass(frozen=True)
class HttpScanResult:
    requested_url: str
    final_url: str
    status_code: int
    response_time_ms: int
    html: str
    response_headers: dict[str, Any]
    header_map: dict[str, str]
    set_cookie_headers: list[str]
    redirect_chain: list[dict[str, Any]]


async def fetch_target(
    raw_url: str,
    settings: Settings,
    policy: UrlSafetyPolicy | None = None,
) -> HttpScanResult:
    """Fetch a target page with SSRF validation, redirect checks and size limits."""

    policy = policy or UrlSafetyPolicy(
        allow_internal_demo_target=settings.allow_internal_demo_target,
        demo_target_internal_url=settings.demo_target_internal_url,
        is_production=settings.is_production,
    )
    safe_url = validate_url_for_scanning(raw_url, policy=policy)
    return await asyncio.wait_for(
        _fetch_validated_url(safe_url.normalized_url, settings, policy),
        timeout=settings.scan_total_timeout_seconds,
    )


async def _fetch_validated_url(
    start_url: str,
    settings: Settings,
    policy: UrlSafetyPolicy,
) -> HttpScanResult:
    redirect_chain: list[RedirectHop] = []
    current_url = start_url
    started = time.perf_counter()
    timeout = httpx.Timeout(
        connect=settings.scan_connect_timeout_seconds,
        read=settings.scan_read_timeout_seconds,
        write=settings.scan_read_timeout_seconds,
        pool=settings.scan_connect_timeout_seconds,
    )
    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=timeout,
        headers={"User-Agent": "SentinelSightAI/0.1 passive-monitor"},
    ) as client:
        for _ in range(settings.scan_max_redirects + 1):
            request = client.build_request("GET", current_url)
            response = await client.send(request, stream=True)
            if is_redirect(response.status_code):
                location = response.headers.get("location")
                await response.aclose()
                if not location:
                    raise HttpScanError("Redirect response did not include Location")
                if len(redirect_chain) >= settings.scan_max_redirects:
                    raise HttpScanError("Maximum redirect count exceeded")
                next_url = urljoin(current_url, location)
                try:
                    safe_redirect = validate_redirect_target(next_url, policy=policy)
                except UnsafeUrlError as exc:
                    raise HttpScanError(
                        f"Unsafe redirect target blocked: {exc}"
                    ) from exc
                redirect_chain.append(
                    RedirectHop(
                        source_url=current_url,
                        status_code=response.status_code,
                        location=safe_redirect.normalized_url,
                    )
                )
                current_url = safe_redirect.normalized_url
                continue

            body = await read_limited_body(response, settings.scan_max_response_bytes)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            headers, header_map, set_cookie_headers = sanitize_response_headers(
                response.headers
            )
            return HttpScanResult(
                requested_url=start_url,
                final_url=str(response.url),
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                html=decode_body(body, response),
                response_headers=headers,
                header_map=header_map,
                set_cookie_headers=set_cookie_headers,
                redirect_chain=[hop.__dict__ for hop in redirect_chain],
            )
    raise HttpScanError("Unable to complete HTTP request")


async def read_limited_body(response: httpx.Response, max_bytes: int) -> bytes:
    data = bytearray()
    async for chunk in response.aiter_bytes():
        data.extend(chunk)
        if len(data) > max_bytes:
            await response.aclose()
            raise HttpScanError("Response body exceeded the configured size limit")
    await response.aclose()
    return bytes(data)


def is_redirect(status_code: int) -> bool:
    return status_code in {301, 302, 303, 307, 308}


def decode_body(body: bytes, response: httpx.Response) -> str:
    encoding = response.encoding or "utf-8"
    return body.decode(encoding, errors="replace")


def sanitize_response_headers(
    headers: httpx.Headers,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    stored: dict[str, Any] = {}
    header_map: dict[str, str] = {}
    for name, value in headers.items():
        canonical_name = canonical_header_name(name)
        if name.lower() == "set-cookie":
            continue
        trimmed = value[:1000]
        stored[canonical_name] = trimmed
        header_map[name.lower()] = trimmed

    set_cookie_headers = headers.get_list("set-cookie")
    if set_cookie_headers:
        stored["Set-Cookie"] = [
            summarize_set_cookie(value) for value in set_cookie_headers
        ]
    return stored, header_map, set_cookie_headers


def summarize_set_cookie(header_value: str) -> str:
    parts = [part.strip() for part in header_value.split(";") if part.strip()]
    if not parts:
        return "redacted"
    cookie_name = parts[0].split("=", 1)[0]
    attributes = [
        part
        for part in parts[1:]
        if "=" not in part or not part.lower().startswith("expires=")
    ]
    return "; ".join([f"{cookie_name}=redacted", *attributes])[:1000]


def canonical_header_name(name: str) -> str:
    return "-".join(part.capitalize() for part in name.split("-"))
