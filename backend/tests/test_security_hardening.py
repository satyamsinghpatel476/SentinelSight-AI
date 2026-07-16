from __future__ import annotations

import asyncio
import ipaddress

import httpx
import pytest
from app.core.config import Settings
from app.security.url_safety import (
    UnsafeUrlError,
    validate_redirect_target,
    validate_url_for_scanning,
)
from app.services.rate_limiter import LoginRateLimiter

from tests.api_client import with_client
from tests.conftest import SeededUsers

PASSWORD = "Correct Horse Battery Staple!"


def safe_resolver(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    assert hostname == "example.com"
    return [ipaddress.ip_address("93.184.216.34")]


def resolver_to_private_ip(
    hostname: str,
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    assert hostname == "example.com"
    return [ipaddress.ip_address("10.0.0.2")]


def test_production_rejects_weak_secret_and_insecure_cookie() -> None:
    with pytest.raises(RuntimeError):
        Settings(
            app_env="production",
            app_secret_key="change-me",
            cookie_secure=True,
        ).validate_runtime_security()

    with pytest.raises(RuntimeError):
        Settings(
            app_env="production",
            app_secret_key="a-strong-production-secret-value",
            cookie_secure=False,
        ).validate_runtime_security()


def test_production_accepts_strong_secret_and_secure_cookie() -> None:
    Settings(
        app_env="production",
        app_secret_key="a-strong-production-secret-value",
        cookie_secure=True,
    ).validate_runtime_security()


def test_csrf_origin_guard_blocks_cross_origin_cookie_request(
    seeded_users: SeededUsers,
) -> None:
    async def scenario(client: httpx.AsyncClient) -> None:
        login_response = await client.post(
            "/api/auth/login",
            json={"email": seeded_users.admin.email, "password": PASSWORD},
        )
        assert login_response.status_code == 200

        response = await client.post(
            "/api/websites",
            headers={"Origin": "http://evil.example"},
            json={
                "name": "Blocked CSRF",
                "url": "https://example.com",
                "contact_email": "security@example.com",
                "risk_category": "moderate",
                "monitoring_enabled": True,
                "authorization_confirmed": True,
            },
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"] == "Cross-origin state-changing request blocked"
        )

    asyncio.run(with_client(scenario))


def test_login_rate_limiter_prunes_when_key_cap_is_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGIN_RATE_LIMIT_MAX_KEYS", "1")
    from app.core.config import get_settings

    get_settings.cache_clear()
    limiter = LoginRateLimiter()
    limiter.record_failure("first")
    limiter.check("second")

    assert "first" not in limiter._attempts
    assert "second" in limiter._attempts
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost",
        "http://127.0.0.1",
        "http://0.0.0.0",
        "http://10.0.0.1",
        "http://[::1]",
        "http://[fe80::1]",
        "http://169.254.169.254/latest/meta-data",
        "ftp://example.com",
        "https://user:password@example.com",
        "http://metadata.google.internal",
        "http://internal-service",
    ],
)
def test_scanner_url_safety_blocks_forbidden_targets(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        validate_url_for_scanning(url)


def test_scanner_url_safety_allows_safe_public_target() -> None:
    result = validate_url_for_scanning(
        "https://Example.com:443/", resolver=safe_resolver
    )

    assert result.normalized_url == "https://example.com/"
    assert result.resolved_ips == ("93.184.216.34",)


def test_scanner_url_safety_blocks_dns_rebinding_to_private_ip() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_url_for_scanning(
            "https://example.com", resolver=resolver_to_private_ip
        )


def test_scanner_url_safety_validates_redirect_targets() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_redirect_target("http://127.0.0.1/admin")
