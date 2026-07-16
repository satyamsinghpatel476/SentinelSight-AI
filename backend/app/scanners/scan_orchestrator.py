from __future__ import annotations

import threading
from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.enums import ScanStatus, ScanType
from app.models.baseline import Baseline
from app.models.finding import Finding
from app.models.scan import Scan
from app.scanners.comparison_analyzer import ComparisonResult, compare_scan_to_baseline
from app.scanners.content_analyzer import analyze_html_content
from app.scanners.header_analyzer import PassiveFinding, analyze_security_headers
from app.scanners.http_scanner import HttpScanError, fetch_target
from app.scanners.risk_engine import calculate_risk
from app.scanners.screenshot_capture import ScreenshotError, capture_screenshot
from app.scanners.tls_analyzer import analyze_tls_certificate
from app.security.url_safety import UnsafeUrlError, UrlSafetyPolicy
from app.services.audit_log import create_audit_log
from app.services.incidents import create_incident_if_needed
from app.utils.time import utc_now

_scan_semaphore_guard = threading.Lock()
_scan_semaphore: threading.BoundedSemaphore | None = None
_scan_semaphore_size = 0


async def run_scan_background(scan_id: str) -> None:
    """Background-task entry point for a single scan."""

    settings = get_settings()
    semaphore = scan_semaphore(settings.scan_max_concurrent)
    acquired = semaphore.acquire(blocking=False)
    if not acquired:
        fail_scan(scan_id, "Scanner concurrency limit reached")
        return
    try:
        await run_scan(scan_id)
    finally:
        semaphore.release()


async def run_scan(scan_id: str) -> None:
    """Run one passive scan and persist all metadata, findings and evidence."""

    settings = get_settings()
    policy = UrlSafetyPolicy(
        allow_internal_demo_target=settings.allow_internal_demo_target,
        demo_target_internal_url=settings.demo_target_internal_url,
        is_production=settings.is_production,
    )
    scan = mark_scan_running(scan_id)
    if scan is None:
        return

    try:
        http_result = await fetch_target(scan.requested_url, settings, policy)
        content = analyze_html_content(
            http_result.html,
            http_result.final_url,
            settings.scan_visible_text_max_chars,
        )
        screenshot = await capture_screenshot(http_result.final_url, settings, policy)
        findings = [
            *analyze_security_headers(
                http_result.final_url,
                http_result.status_code,
                http_result.header_map,
                http_result.set_cookie_headers,
            ),
            *analyze_tls_certificate(
                http_result.final_url,
                settings.scan_connect_timeout_seconds,
            ),
        ]
        complete_scan(scan_id, http_result, content, screenshot, findings)
    except (UnsafeUrlError, HttpScanError, ScreenshotError, TimeoutError) as exc:
        fail_scan(scan_id, safe_failure_reason(exc))
    except Exception:
        fail_scan(scan_id, "Scan failed while processing the target")


def mark_scan_running(scan_id: str) -> Scan | None:
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if scan is None or scan.status not in {ScanStatus.queued, ScanStatus.running}:
            return None
        scan.status = ScanStatus.running
        scan.started_at = utc_now()
        db.commit()
        db.refresh(scan)
        return scan


def complete_scan(
    scan_id: str,
    http_result: object,
    content: object,
    screenshot: object,
    findings: Iterable[PassiveFinding],
) -> None:
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if scan is None:
            return
        db.execute(delete(Finding).where(Finding.scan_id == scan.id))
        scan.status = ScanStatus.completed
        scan.final_url = http_result.final_url
        scan.http_status = http_result.status_code
        scan.response_time_ms = http_result.response_time_ms
        scan.page_title = content.page_title
        scan.visible_text = content.visible_text
        scan.visible_text_hash = content.visible_text_hash
        scan.html_hash = content.html_hash
        scan.response_headers = http_result.response_headers
        scan.external_script_domains = content.external_script_domains
        scan.external_iframe_domains = content.external_iframe_domains
        scan.redirect_chain = http_result.redirect_chain
        scan.failure_reason = None
        scan.screenshot_filename = screenshot.filename
        scan.screenshot_content_type = screenshot.content_type
        scan.screenshot_width = screenshot.width
        scan.screenshot_height = screenshot.height
        scan.screenshot_perceptual_hash = screenshot.perceptual_hash
        now = utc_now()
        scan.scanned_at = now
        scan.completed_at = now
        all_findings = list(findings)

        baseline = active_baseline_for_scan(db, scan)
        comparison: ComparisonResult | None = None
        if baseline and baseline.scan_id != scan.id:
            baseline_scan = db.get(Scan, baseline.scan_id)
            if baseline_scan is not None:
                scan.scan_type = ScanType.comparison
                comparison = compare_scan_to_baseline(
                    baseline_scan, scan, get_settings()
                )
                apply_comparison_result(scan, comparison)
                all_findings.extend(comparison.findings)
        else:
            scan.scan_type = ScanType.baseline

        all_findings = prioritize_findings(dedupe_findings(all_findings))
        risk = calculate_risk(
            visual_change_level=scan.visual_change_level,
            visual_change_percent=scan.visual_change_percent,
            text_similarity_percent=scan.text_similarity_percent,
            title_changed=scan.title_changed,
            suspicious_phrases=scan.suspicious_phrases or [],
            new_external_script_domains=scan.new_external_script_domains or [],
            new_external_iframe_domains=scan.new_external_iframe_domains or [],
            findings=all_findings,
        )
        scan.risk_score = risk.risk_score
        scan.risk_level = risk.risk_level
        scan.risk_breakdown = risk.risk_breakdown

        for item, risk_points in zip(
            all_findings, risk.finding_point_contributions, strict=True
        ):
            db.add(
                Finding(
                    organization_id=scan.organization_id,
                    website_asset_id=scan.website_asset_id,
                    scan_id=scan.id,
                    finding_type=item.finding_type,
                    title=item.title,
                    description=item.description,
                    severity=item.severity,
                    evidence=item.evidence,
                    remediation=item.remediation,
                    risk_points=risk_points,
                )
            )
        create_audit_log(
            db,
            organization_id=scan.organization_id,
            user_id=scan.requested_by,
            action="scan.completed",
            resource_type="scan",
            resource_id=scan.id,
            metadata={"risk_score": scan.risk_score, "scan_type": scan.scan_type.value},
        )
        if scan.scan_type == ScanType.comparison:
            create_audit_log(
                db,
                organization_id=scan.organization_id,
                user_id=scan.requested_by,
                action="comparison.completed",
                resource_type="scan",
                resource_id=scan.id,
                metadata={
                    "baseline_scan_id": scan.baseline_scan_id,
                    "risk_score": scan.risk_score,
                },
            )
        create_incident_if_needed(db, scan=scan)
        db.commit()


def fail_scan(scan_id: str, reason: str) -> None:
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if scan is None:
            return
        scan.status = ScanStatus.failed
        scan.failure_reason = reason[:1024]
        scan.completed_at = utc_now()
        create_audit_log(
            db,
            organization_id=scan.organization_id,
            user_id=scan.requested_by,
            action="scan.failed",
            resource_type="scan",
            resource_id=scan.id,
            metadata={"reason": scan.failure_reason},
        )
        db.commit()


def safe_failure_reason(exc: BaseException) -> str:
    message = str(exc).strip()
    return message[:1024] if message else "Scan failed safely"


def scan_semaphore(max_concurrent: int) -> threading.BoundedSemaphore:
    global _scan_semaphore, _scan_semaphore_size
    size = max(1, max_concurrent)
    with _scan_semaphore_guard:
        if _scan_semaphore is None or _scan_semaphore_size != size:
            _scan_semaphore = threading.BoundedSemaphore(size)
            _scan_semaphore_size = size
        return _scan_semaphore


def active_baseline_for_scan(db: Session, scan: Scan) -> Baseline | None:
    return db.scalar(
        select(Baseline).where(
            Baseline.organization_id == scan.organization_id,
            Baseline.website_asset_id == scan.website_asset_id,
            Baseline.is_active.is_(True),
        )
    )


def apply_comparison_result(scan: Scan, comparison: ComparisonResult) -> None:
    scan.baseline_scan_id = comparison.baseline_scan_id
    scan.title_changed = comparison.title_changed
    scan.baseline_title = comparison.baseline_title
    scan.current_title = comparison.current_title
    scan.text_similarity_percent = comparison.text_similarity_percent
    scan.comparison_error = comparison.comparison_error
    scan.baseline_external_script_domains = comparison.baseline_external_script_domains
    scan.current_external_script_domains = comparison.current_external_script_domains
    scan.new_external_script_domains = comparison.new_external_script_domains
    scan.baseline_external_iframe_domains = comparison.baseline_external_iframe_domains
    scan.current_external_iframe_domains = comparison.current_external_iframe_domains
    scan.new_external_iframe_domains = comparison.new_external_iframe_domains
    scan.suspicious_phrases = comparison.suspicious_phrases
    if comparison.visual_result is not None:
        scan.visual_change_percent = comparison.visual_result.visual_change_percent
        scan.visual_change_level = comparison.visual_result.visual_change_level
        scan.perceptual_hash_distance = (
            comparison.visual_result.perceptual_hash_distance
        )
        scan.difference_image_filename = (
            comparison.visual_result.difference_image_filename
        )
        scan.difference_image_content_type = (
            comparison.visual_result.difference_image_content_type
        )


def dedupe_findings(findings: list[PassiveFinding]) -> list[PassiveFinding]:
    seen: set[tuple[str, str]] = set()
    deduped: list[PassiveFinding] = []
    for item in findings:
        key = (item.finding_type, item.evidence)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def prioritize_findings(findings: list[PassiveFinding]) -> list[PassiveFinding]:
    """Score higher-impact evidence first so clamping keeps clear causes visible."""

    return sorted(findings, key=lambda item: item.risk_points, reverse=True)
