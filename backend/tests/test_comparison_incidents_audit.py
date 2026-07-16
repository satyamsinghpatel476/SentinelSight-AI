from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.enums import (
    FindingSeverity,
    IncidentStatus,
    RiskLevel,
    ScanStatus,
    ScanType,
)
from app.models.audit_log import AuditLog
from app.models.baseline import Baseline
from app.models.incident import Incident
from app.models.scan import Scan
from app.scanners.comparison_analyzer import (
    compare_scan_to_baseline,
    detect_suspicious_phrases,
    text_similarity,
)
from app.scanners.header_analyzer import finding
from app.scanners.http_scanner import HttpScanResult
from app.scanners.risk_engine import calculate_risk, risk_level_for_score
from app.scanners.scan_orchestrator import run_scan
from app.scanners.screenshot_capture import ScreenshotResult
from app.scanners.tls_analyzer import analyze_tls_certificate
from app.scanners.visual_comparison import compare_screenshots
from app.services.audit_log import create_audit_log, verify_audit_chain
from app.services.incidents import create_incident_if_needed
from PIL import Image
from sqlalchemy import select

from tests.api_client import with_client
from tests.conftest import SeededUsers
from tests.test_scans import create_asset, create_scan, login


def test_text_similarity_calculation() -> None:
    assert text_similarity("same content", "same content", 200) == 100.0
    assert (
        text_similarity("northstar banking portal", "Hacked by Demo Attacker", 200) < 50
    )


def test_suspicious_phrase_detection_is_case_insensitive() -> None:
    phrases = detect_suspicious_phrases("Welcome. HACKED BY Demo Attacker.")
    assert phrases == ["hacked by"]


def test_new_script_domain_detection(seeded_users: SeededUsers) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    baseline_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
    )
    current_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
        scan_type=ScanType.comparison,
    )
    with SessionLocal() as db:
        baseline = db.get(Scan, baseline_id)
        current = db.get(Scan, current_id)
        assert baseline is not None
        assert current is not None
        baseline.external_script_domains = ["cdn.example"]
        current.external_script_domains = ["cdn.example", "demo-unknown-script.invalid"]
        result = compare_scan_to_baseline(baseline, current, Settings())

    assert result.new_external_script_domains == ["demo-unknown-script.invalid"]
    assert "new_external_script_domain" in {
        item.finding_type for item in result.findings
    }


def test_visual_change_calculation(tmp_path: Path) -> None:
    screenshots = tmp_path / "screenshots"
    screenshots.mkdir()
    Image.new("RGB", (16, 16), (255, 255, 255)).save(screenshots / "baseline.png")
    Image.new("RGB", (16, 16), (127, 0, 0)).save(screenshots / "current.png")

    result = compare_screenshots(
        "baseline.png",
        "current.png",
        Settings(
            evidence_storage_dir=str(tmp_path),
            visual_minor_threshold=5,
            visual_moderate_threshold=15,
            visual_major_threshold=35,
        ),
    )

    assert result.visual_change_percent >= 90
    assert result.visual_change_level == "major"
    assert (tmp_path / "differences" / result.difference_image_filename).exists()


def test_risk_engine_breakdown_clamp_and_levels() -> None:
    result = calculate_risk(
        visual_change_level="major",
        visual_change_percent=42.8,
        text_similarity_percent=20,
        title_changed=True,
        suspicious_phrases=["hacked by", "site defaced"],
        new_external_script_domains=["demo-unknown-script.invalid"],
        new_external_iframe_domains=["frames.example"],
        findings=[
            finding(
                "visual_change",
                "Major visual change",
                "Screenshot differs",
                FindingSeverity.high,
                "42.80% meaningful screenshot change",
                "Review highlighted difference.",
                35,
            ),
            finding(
                "suspicious_defacement_phrase",
                "Suspicious defacement phrase detected",
                "Phrase found",
                FindingSeverity.high,
                "Detected phrase: hacked by",
                "Review deployment history.",
                25,
            ),
            finding(
                "visible_text_changed",
                "Visible page text changed",
                "Text changed",
                FindingSeverity.high,
                "Similarity: 20.00%",
                "Review content changes.",
                15,
            ),
            finding(
                "new_external_script_domain",
                "New external JavaScript domain detected",
                "Script domain found",
                FindingSeverity.high,
                "demo-unknown-script.invalid",
                "Review introduced script.",
                15,
            ),
            finding(
                "new_external_iframe_domain",
                "New external iframe domain detected",
                "Iframe domain found",
                FindingSeverity.moderate,
                "frames.example",
                "Review introduced iframe.",
                12,
            ),
            finding(
                "missing_content_security_policy",
                "Missing CSP",
                "No CSP",
                FindingSeverity.moderate,
                "missing",
                "add CSP",
                8,
            ),
        ],
    )

    assert result.risk_score == 100
    assert result.risk_level == RiskLevel.critical
    assert sum(result.finding_point_contributions) == result.risk_score
    assert result.finding_point_contributions[-1] == 0
    assert any(
        item["reason"] == "Major visual change" for item in result.risk_breakdown
    )
    assert risk_level_for_score(24) == RiskLevel.low
    assert risk_level_for_score(25) == RiskLevel.moderate
    assert risk_level_for_score(50) == RiskLevel.high
    assert risk_level_for_score(75) == RiskLevel.critical


def test_tls_inspection_failure_is_informational(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_expiry(*args: object, **kwargs: object):
        raise OSError("network blocked")

    monkeypatch.setattr(
        "app.scanners.tls_analyzer.fetch_certificate_expiry", fake_expiry
    )
    findings = analyze_tls_certificate("https://example.com/", 1)
    assert len(findings) == 1
    assert findings[0].finding_type == "tls_certificate_unavailable"
    assert findings[0].risk_points == 0


def test_baseline_comparison_uses_active_baseline(
    seeded_users: SeededUsers,
    monkeypatch,
) -> None:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    baseline_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
    )
    current_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
        status=ScanStatus.queued,
    )
    with SessionLocal() as db:
        baseline = db.get(Scan, baseline_id)
        assert baseline is not None
        baseline.visible_text = "Banking services for growing communities"
        baseline.external_script_domains = []
        db.add(
            Baseline(
                organization_id=seeded_users.admin.organization_id,
                website_asset_id=asset_id,
                scan_id=baseline_id,
                approved_by=seeded_users.admin.id,
                is_active=True,
            )
        )
        db.commit()

    async def fake_fetch(*args: object, **kwargs: object) -> HttpScanResult:
        html = """
        <html>
          <head>
            <title>Hacked by Demo Attacker</title>
            <script src="https://demo-unknown-script.invalid/app.js"></script>
          </head>
          <body>Hacked by Demo Attacker. Site defaced demonstration.</body>
        </html>
        """
        return HttpScanResult(
            requested_url="https://example.com/",
            final_url="https://example.com/",
            status_code=200,
            response_time_ms=50,
            html=html,
            response_headers={"X-Content-Type-Options": "nosniff"},
            header_map={"x-content-type-options": "nosniff"},
            set_cookie_headers=[],
            redirect_chain=[],
        )

    async def fake_screenshot(*args: object, **kwargs: object) -> ScreenshotResult:
        return ScreenshotResult(
            filename="current.png",
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

    asyncio.run(run_scan(current_id))

    with SessionLocal() as db:
        scan = db.get(Scan, current_id)
        incident = db.scalar(select(Incident).where(Incident.scan_id == current_id))
        assert scan is not None
        assert scan.scan_type == ScanType.comparison
        assert scan.baseline_scan_id == baseline_id
        assert scan.text_similarity_percent is not None
        assert scan.text_similarity_percent < 50
        assert scan.suspicious_phrases == ["hacked by", "site defaced"]
        assert scan.new_external_script_domains == ["demo-unknown-script.invalid"]
        assert incident is not None


def test_high_risk_comparison_creates_incident(seeded_users: SeededUsers) -> None:
    scan_id = high_risk_scan(seeded_users)

    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        assert scan is not None
        incident = create_incident_if_needed(db, scan=scan)
        db.commit()

    assert incident is not None
    assert incident.status == IncidentStatus.open


def test_low_risk_scan_does_not_create_unnecessary_incident(
    seeded_users: SeededUsers,
) -> None:
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
        scan.risk_score = 12
        scan.risk_level = RiskLevel.low
        incident = create_incident_if_needed(db, scan=scan)
        db.commit()

    assert incident is None


def test_viewer_cannot_change_incident(seeded_users: SeededUsers) -> None:
    incident_id = create_high_risk_incident(seeded_users)

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.viewer.email)
        response = await client.patch(
            f"/api/incidents/{incident_id}", json={"status": "investigating"}
        )
        assert response.status_code == 403

    asyncio.run(with_client(scenario))


def test_cross_organization_incident_access_returns_404(
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
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        assert scan is not None
        scan.risk_score = 80
        scan.risk_level = RiskLevel.critical
        incident = create_incident_if_needed(db, scan=scan)
        db.commit()
        assert incident is not None
        incident_id = incident.id

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)
        response = await client.get(f"/api/incidents/{incident_id}")
        assert response.status_code == 404

    asyncio.run(with_client(scenario))


def test_incident_note_and_status_workflow(seeded_users: SeededUsers) -> None:
    incident_id = create_high_risk_incident(seeded_users)

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.analyst.email)
        note = await client.post(
            f"/api/incidents/{incident_id}/notes",
            json={"content": "Checked deployment history."},
        )
        investigating = await client.patch(
            f"/api/incidents/{incident_id}",
            json={"status": "investigating"},
        )
        resolved = await client.patch(
            f"/api/incidents/{incident_id}",
            json={
                "status": "resolved",
                "resolution_notes": "Restored expected demo page.",
            },
        )
        assert note.status_code == 200
        assert investigating.status_code == 200
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"
        assert resolved.json()["resolution_notes"] == "Restored expected demo page."

    asyncio.run(with_client(scenario))


def test_difference_image_endpoint_enforces_organization_scope(
    seeded_users: SeededUsers,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVIDENCE_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    differences = tmp_path / "differences"
    differences.mkdir()
    (differences / "diff.png").write_bytes(b"diff")

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
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        assert scan is not None
        scan.difference_image_filename = "diff.png"
        scan.difference_image_content_type = "image/png"
        db.commit()

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)
        response = await client.get(f"/api/evidence/differences/{scan_id}")
        assert response.status_code == 404

    asyncio.run(with_client(scenario))
    get_settings.cache_clear()


def test_difference_path_traversal_is_impossible(
    seeded_users: SeededUsers,
) -> None:
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
        scan.difference_image_filename = "../diff.png"
        db.commit()

    async def scenario(client: httpx.AsyncClient) -> None:
        await login(client, seeded_users.admin.email)
        response = await client.get(f"/api/evidence/differences/{scan_id}")
        assert response.status_code == 404

    asyncio.run(with_client(scenario))


def test_audit_chain_valid_state_passes(seeded_users: SeededUsers) -> None:
    with SessionLocal() as db:
        first = create_audit_log(
            db,
            organization_id=seeded_users.admin.organization_id,
            user_id=seeded_users.admin.id,
            action="test.first",
            resource_type="scan",
            resource_id="one",
            metadata={"order": 1},
        )
        second = create_audit_log(
            db,
            organization_id=seeded_users.admin.organization_id,
            user_id=seeded_users.admin.id,
            action="test.second",
            resource_type="scan",
            resource_id="two",
            metadata={"order": 2},
        )
        db.commit()
        records = db.scalars(
            select(AuditLog).order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        ).all()

    result = verify_audit_chain(list(records))
    assert result.valid is True
    assert result.records_checked == 2
    assert first.previous_hash == "0" * 64
    assert second.previous_hash == first.entry_hash


def test_modified_audit_data_fails_verification(seeded_users: SeededUsers) -> None:
    with SessionLocal() as db:
        create_audit_log(
            db,
            organization_id=seeded_users.admin.organization_id,
            user_id=seeded_users.admin.id,
            action="test.first",
            resource_type="scan",
            resource_id="one",
            metadata={"order": 1},
        )
        db.commit()
        record = db.scalar(select(AuditLog))
        assert record is not None
        record.action = "test.tampered"
        db.commit()
        records = db.scalars(
            select(AuditLog).order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        ).all()

    result = verify_audit_chain(list(records))
    assert result.valid is False
    assert result.first_broken_record_id == records[0].id


def test_ai_disabled_by_default_does_not_fabricate_output() -> None:
    settings = Settings()
    assert settings.ai_enabled is False
    assert settings.ai_api_key == ""


def high_risk_scan(seeded_users: SeededUsers) -> str:
    asset_id = create_asset(
        organization_id=seeded_users.admin.organization_id,
        created_by=seeded_users.admin.id,
    )
    scan_id = create_scan(
        organization_id=seeded_users.admin.organization_id,
        website_asset_id=asset_id,
        requested_by=seeded_users.admin.id,
        scan_type=ScanType.comparison,
    )
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        assert scan is not None
        scan.risk_score = 82
        scan.risk_level = RiskLevel.critical
        scan.suspicious_phrases = ["hacked by"]
        scan.visual_change_level = "major"
        scan.new_external_script_domains = ["demo-unknown-script.invalid"]
        db.commit()
    return scan_id


def create_high_risk_incident(seeded_users: SeededUsers) -> str:
    scan_id = high_risk_scan(seeded_users)
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        assert scan is not None
        incident = create_incident_if_needed(db, scan=scan)
        db.commit()
        assert incident is not None
        return incident.id
