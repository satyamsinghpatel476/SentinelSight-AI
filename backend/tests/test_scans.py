from __future__ import annotations

import asyncio
import ipaddress
from pathlib import Path

import httpx
import pytest
from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.enums import ScanStatus, ScanType, WebsiteRiskCategory
from app.models.baseline import Baseline
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.website_asset import WebsiteAsset
from app.scanners.header_analyzer import analyze_security_headers
from app.scanners.http_scanner import HttpScanError, HttpScanResult
from app.scanners.scan_orchestrator import run_scan
from app.scanners.screenshot_capture import ScreenshotResult
from app.security.url_safety import (
    UnsafeUrlError,
    UrlSafetyPolicy,
    validate_url_for_scanning,
)
from app.utils.time import utc_now
from sqlalchemy import select

from tests.api_client import with_client
from tests.conftest import SeededUsers

PASSWORD = "Correct Horse Battery Staple!"


async def fake_background_scan(scan_id: str) -> None:
    return None


async def login(client: httpx.AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200


def create_asset(
    *,
    organization_id: str,
    created_by: str,
    normalized_url: str = "https://example.com/",
) -> str:
    with SessionLocal() as db:
        asset = WebsiteAsset(
            organization_id=organization_id,
            name="Example Site",
            url=normalized_url,
            normalized_url=normalized_url,
            authorization_confirmed=True,
            monitoring_enabled=True,
            risk_category=WebsiteRiskCategory.high,
            contact_email="security@example.com",
            created_by=created_by,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset.id


def create_scan(
    *,
    organization_id: str,
    website_asset_id: str,
    requested_by: str,
    status: ScanStatus = ScanStatus.completed,
    scan_type: ScanType = ScanType.baseline,
) -> str:
    with SessionLocal() as db:
        scan = Scan(
            organization_id=organization_id,
            website_asset_id=website_asset_id,
            requested_by=requested_by,
            scan_type=scan_type,
            status=status,
            requested_url="https://example.com/",
            final_url="https://example.com/",
            http_status=200,
            response_time_ms=120,
            page_title="Example",
            visible_text_hash="text-hash",
            html_hash="html-hash",
            response_headers={"Content-Type": "text/html"},
            redirect_chain=[],
            screenshot_filename="evidence.png",
            screenshot_content_type="image/png",
            screenshot_width=1365,
            screenshot_height=768,
            screenshot_perceptual_hash="abcd1234",
            completed_at=utc_now(),
            scanned_at=utc_now(),
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        return scan.id


def test_administrator_can_start_scan(
    seeded_users: SeededUsers, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    monkeypatch.setattr("app.api.scans.run_scan_background", fake_background_scan)

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)
        response = await client.post(
            f"/api/websites/{asset_id}/scans", json={"scan_type": "baseline"}
        )
        assert response.status_code == 202
        assert response.json()["status"] == "queued"

    asyncio.run(with_client(scenario))


def test_analyst_can_start_scan(
    seeded_users: SeededUsers, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    monkeypatch.setattr("app.api.scans.run_scan_background", fake_background_scan)

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.analyst.email)
        response = await client.post(f"/api/websites/{asset_id}/scans", json={})
        assert response.status_code == 202

    asyncio.run(with_client(scenario))


def test_viewer_and_unauthenticated_user_cannot_start_scan(
    seeded_users: SeededUsers, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    monkeypatch.setattr("app.api.scans.run_scan_background", fake_background_scan)

    async def scenario(client: httpx.AsyncClient) -> None:
        unauthenticated = await client.post(f"/api/websites/{asset_id}/scans", json={})
        assert unauthenticated.status_code == 401

        await login(client, seeded_users.viewer.email)
        viewer_response = await client.post(f"/api/websites/{asset_id}/scans", json={})
        assert viewer_response.status_code == 403

    asyncio.run(with_client(scenario))


def test_cross_organization_scan_access_returns_404(seeded_users: SeededUsers) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.organization_b.id,
        created_by=seeded_users.other_admin.id,
        normalized_url="https://other.example.com/",
    )
    scan_id = create_scan(
        organization_id=seeded_users.organization_b.id,
        website_asset_id=asset_id,
        requested_by=seeded_users.other_admin.id,
    )

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)
        scan_response = await client.get(f"/api/scans/{scan_id}")
        findings_response = await client.get(f"/api/scans/{scan_id}/findings")
        assert scan_response.status_code == 404
        assert findings_response.status_code == 404

    asyncio.run(with_client(scenario))


def test_only_one_active_scan_per_website(
    seeded_users: SeededUsers, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    monkeypatch.setattr("app.api.scans.run_scan_background", fake_background_scan)

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)
        first = await client.post(f"/api/websites/{asset_id}/scans", json={})
        second = await client.post(f"/api/websites/{asset_id}/scans", json={})
        assert first.status_code == 202
        assert second.status_code == 409

    asyncio.run(with_client(scenario))


def test_safe_url_validation_blocks_required_forbidden_targets() -> None:
    blocked_urls = [
        "http://localhost",
        "http://127.0.0.1",
        "http://10.0.0.1",
        "http://[::1]",
        "http://169.254.169.254/latest/meta-data",
        "https://user:password@example.com",
        "file:///etc/passwd",
    ]
    for url in blocked_urls:
        with pytest.raises(UnsafeUrlError):
            validate_url_for_scanning(url)


def test_exact_controlled_demo_target_exception_is_narrow() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_url_for_scanning("http://demo-target:9000/")

    policy = UrlSafetyPolicy(
        allow_internal_demo_target=True,
        demo_target_internal_url="http://demo-target:9000",
        is_production=False,
    )

    def resolver(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        assert hostname == "demo-target"
        return [ipaddress.ip_address("172.20.0.5")]

    result = validate_url_for_scanning(
        "http://demo-target:9000/", resolver=resolver, policy=policy
    )
    assert result.demo_target_exception is True

    with pytest.raises(UnsafeUrlError):
        validate_url_for_scanning("http://postgres:5432", policy=policy)
    with pytest.raises(UnsafeUrlError):
        validate_url_for_scanning("http://demo-target:9001", policy=policy)
    with pytest.raises(UnsafeUrlError):
        validate_url_for_scanning(
            "http://10.0.0.5:9000",
            policy=UrlSafetyPolicy(
                allow_internal_demo_target=True,
                demo_target_internal_url="http://10.0.0.5:9000",
                is_production=False,
            ),
        )
    with pytest.raises(UnsafeUrlError):
        validate_url_for_scanning(
            "http://demo-target:9000",
            resolver=resolver,
            policy=UrlSafetyPolicy(
                allow_internal_demo_target=True,
                demo_target_internal_url="http://demo-target:9000",
                is_production=True,
            ),
        )


def test_production_cannot_enable_internal_demo_exception() -> None:
    with pytest.raises(RuntimeError):
        Settings(
            app_env="production",
            app_secret_key="a-strong-production-secret-value",
            cookie_secure=True,
            allow_internal_demo_target=True,
        ).validate_runtime_security()


def test_failed_scan_is_marked_failed(
    seeded_users: SeededUsers, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    scan_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
        status=ScanStatus.queued,
    )

    async def fake_fetch(*args: object, **kwargs: object) -> HttpScanResult:
        raise HttpScanError("mocked safe failure")

    monkeypatch.setattr("app.scanners.scan_orchestrator.fetch_target", fake_fetch)
    asyncio.run(run_scan(scan_id))

    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.failed
        assert scan.failure_reason == "mocked safe failure"


def test_successful_scan_stores_metadata_and_findings(
    seeded_users: SeededUsers, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    scan_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
        status=ScanStatus.queued,
    )

    async def fake_fetch(*args: object, **kwargs: object) -> HttpScanResult:
        html = (
            "<html><head><title>Hello</title><script>bad()</script></head>"
            "<body>Visible text</body></html>"
        )
        return HttpScanResult(
            requested_url="https://example.com/",
            final_url="https://example.com/",
            status_code=200,
            response_time_ms=87,
            html=html,
            response_headers={"Server": "ExampleServer/1.2"},
            header_map={"server": "ExampleServer/1.2"},
            set_cookie_headers=["sessionid=abc; SameSite=Lax"],
            redirect_chain=[],
        )

    async def fake_screenshot(*args: object, **kwargs: object) -> ScreenshotResult:
        return ScreenshotResult(
            filename="safe.png",
            content_type="image/png",
            width=1365,
            height=768,
            perceptual_hash="abc123",
        )

    monkeypatch.setattr("app.scanners.scan_orchestrator.fetch_target", fake_fetch)
    monkeypatch.setattr(
        "app.scanners.scan_orchestrator.capture_screenshot", fake_screenshot
    )
    monkeypatch.setattr(
        "app.scanners.scan_orchestrator.analyze_tls_certificate",
        lambda *args, **kwargs: [],
    )

    asyncio.run(run_scan(scan_id))

    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        assert scan is not None
        assert scan.status == ScanStatus.completed
        assert scan.page_title == "Hello"
        assert scan.visible_text == "Visible text"
        assert scan.html_hash is not None
        assert scan.screenshot_filename == "safe.png"
        findings = db.scalars(select(Finding).where(Finding.scan_id == scan_id)).all()
        finding_types = {finding.finding_type for finding in findings}
        assert "missing_content_security_policy" in finding_types
        assert "server_version_disclosure" in finding_types


def test_passive_findings_are_generated_correctly() -> None:
    findings = analyze_security_headers(
        "https://example.com/",
        503,
        {
            "server": "nginx/1.25.0",
            "access-control-allow-origin": "*",
            "access-control-allow-credentials": "true",
        },
        ["sessionid=abc"],
    )
    finding_types = {finding.finding_type for finding in findings}

    assert "http_5xx_response" in finding_types
    assert "missing_content_security_policy" in finding_types
    assert "missing_hsts" in finding_types
    assert "missing_x_content_type_options" in finding_types
    assert "missing_clickjacking_protection" in finding_types
    assert "missing_referrer_policy" in finding_types
    assert "weak_permissions_policy" in finding_types
    assert "unsafe_cors" in finding_types
    assert "server_version_disclosure" in finding_types
    assert "session_cookie_missing_secure" in finding_types
    assert "session_cookie_missing_httponly" in finding_types
    assert "weak_or_missing_samesite" in finding_types


def test_baseline_approval_and_previous_baseline_deactivation(
    seeded_users: SeededUsers,
) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    first_scan_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
    )
    second_scan_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
        scan_type=ScanType.comparison,
    )

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)
        first = await client.post(f"/api/scans/{first_scan_id}/approve-baseline")
        second = await client.post(f"/api/scans/{second_scan_id}/approve-baseline")
        baseline_response = await client.get(f"/api/websites/{asset_id}/baseline")

        assert first.status_code == 200
        assert second.status_code == 200
        assert baseline_response.status_code == 200
        assert baseline_response.json()["scan_id"] == second_scan_id

    asyncio.run(with_client(scenario))

    with SessionLocal() as db:
        baselines = db.query(Baseline).order_by(Baseline.created_at.asc()).all()
        assert len(baselines) == 2
        assert baselines[0].is_active is False
        assert baselines[1].is_active is True
        asset = db.get(WebsiteAsset, asset_id)
        assert asset is not None
        assert asset.current_baseline_id == baselines[1].id


def test_viewer_cannot_approve_baseline(seeded_users: SeededUsers) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    scan_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
    )

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.viewer.email)
        response = await client.post(f"/api/scans/{scan_id}/approve-baseline")
        assert response.status_code == 403

    asyncio.run(with_client(scenario))


def test_screenshot_endpoint_checks_organization_ownership(
    seeded_users: SeededUsers,
) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.organization_b.id,
        created_by=seeded_users.other_admin.id,
        normalized_url="https://other.example.com/",
    )
    scan_id = create_scan(
        organization_id=seeded_users.organization_b.id,
        website_asset_id=asset_id,
        requested_by=seeded_users.other_admin.id,
    )

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)
        response = await client.get(f"/api/evidence/screenshots/{scan_id}")
        assert response.status_code == 404

    asyncio.run(with_client(scenario))


def test_screenshot_path_traversal_is_impossible(seeded_users: SeededUsers) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    scan_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
    )
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        assert scan is not None
        scan.screenshot_filename = "../secret.png"
        db.commit()

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)
        response = await client.get(f"/api/evidence/screenshots/{scan_id}")
        assert response.status_code == 404

    asyncio.run(with_client(scenario))


def test_screenshot_endpoint_serves_owned_file(
    seeded_users: SeededUsers, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EVIDENCE_STORAGE_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    screenshots = tmp_path / "screenshots"
    screenshots.mkdir()
    (screenshots / "safe.png").write_bytes(b"png")

    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    scan_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
    )
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        assert scan is not None
        scan.screenshot_filename = "safe.png"
        db.commit()

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)
        response = await client.get(f"/api/evidence/screenshots/{scan_id}")
        assert response.status_code == 200
        assert response.content == b"png"

    asyncio.run(with_client(scenario))
    get_settings.cache_clear()
