from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.enums import ScanStatus, UserRole
from app.models.audit_entry import AuditEntry
from app.models.baseline import Baseline
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.website_asset import WebsiteAsset
from app.scanners.scan_orchestrator import run_scan_background
from app.scanners.screenshot_capture import (
    ScreenshotError,
    screenshot_path_for_filename,
)
from app.schemas.scans import BaselineRead, FindingRead, ScanCreate, ScanRead
from app.security.dependencies import CurrentUser, get_current_user, require_roles
from app.services.rate_limiter import scan_rate_limiter
from app.utils.time import utc_now

router = APIRouter(tags=["scans"])

AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
ScanStarter = Annotated[
    CurrentUser,
    Depends(require_roles(UserRole.administrator, UserRole.security_analyst)),
]

ACTIVE_SCAN_STATUSES = {ScanStatus.queued, ScanStatus.running}


def get_scan_in_current_organization(
    scan_id: str,
    current_user: CurrentUser,
) -> Scan:
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if scan is None or scan.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found",
            )
        return scan


@router.post(
    "/websites/{website_id}/scans",
    response_model=ScanRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_scan(
    website_id: str,
    payload: ScanCreate,
    background_tasks: BackgroundTasks,
    current_user: ScanStarter,
) -> ScanRead:
    with SessionLocal() as db:
        asset = db.get(WebsiteAsset, website_id)
        if asset is None or asset.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website asset not found",
            )
        if not asset.monitoring_enabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Monitoring is disabled for this website",
            )

        active_scan = db.scalar(
            select(Scan).where(
                Scan.organization_id == current_user.organization_id,
                Scan.website_asset_id == asset.id,
                Scan.status.in_(ACTIVE_SCAN_STATUSES),
            )
        )
        if active_scan is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A scan is already active for this website",
            )

        scan_rate_limiter.check_and_record(
            current_user.id, current_user.organization_id
        )
        scan = Scan(
            organization_id=current_user.organization_id,
            website_asset_id=asset.id,
            requested_by=current_user.id,
            scan_type=payload.scan_type,
            status=ScanStatus.queued,
            requested_url=asset.normalized_url,
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        background_tasks.add_task(run_scan_background, scan.id)
        return ScanRead.model_validate(scan)


@router.get("/websites/{website_id}/scans", response_model=list[ScanRead])
async def list_website_scans(
    website_id: str,
    current_user: AuthenticatedUser,
) -> list[ScanRead]:
    with SessionLocal() as db:
        asset = db.get(WebsiteAsset, website_id)
        if asset is None or asset.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website asset not found",
            )
        scans = db.scalars(
            select(Scan)
            .where(
                Scan.organization_id == current_user.organization_id,
                Scan.website_asset_id == asset.id,
            )
            .order_by(Scan.created_at.desc())
        ).all()
        return [ScanRead.model_validate(scan) for scan in scans]


@router.get("/scans/{scan_id}", response_model=ScanRead)
async def get_scan(scan_id: str, current_user: AuthenticatedUser) -> ScanRead:
    scan = get_scan_in_current_organization(scan_id, current_user)
    return ScanRead.model_validate(scan)


@router.get("/scans/{scan_id}/findings", response_model=list[FindingRead])
async def get_scan_findings(
    scan_id: str,
    current_user: AuthenticatedUser,
) -> list[FindingRead]:
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if scan is None or scan.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found",
            )
        findings = db.scalars(
            select(Finding)
            .where(
                Finding.organization_id == current_user.organization_id,
                Finding.scan_id == scan.id,
            )
            .order_by(Finding.risk_points.desc(), Finding.created_at.asc())
        ).all()
        return [FindingRead.model_validate(finding) for finding in findings]


@router.post("/scans/{scan_id}/approve-baseline", response_model=BaselineRead)
async def approve_baseline(
    scan_id: str,
    current_user: ScanStarter,
) -> BaselineRead:
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if scan is None or scan.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found",
            )
        if scan.status != ScanStatus.completed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only completed scans can be approved as a baseline",
            )
        asset = db.get(WebsiteAsset, scan.website_asset_id)
        if asset is None or asset.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website asset not found",
            )

        previous_baselines = db.scalars(
            select(Baseline).where(
                Baseline.organization_id == current_user.organization_id,
                Baseline.website_asset_id == scan.website_asset_id,
                Baseline.is_active.is_(True),
            )
        ).all()
        for baseline in previous_baselines:
            baseline.is_active = False

        baseline = Baseline(
            organization_id=current_user.organization_id,
            website_asset_id=scan.website_asset_id,
            scan_id=scan.id,
            approved_by=current_user.id,
            approved_at=utc_now(),
            is_active=True,
        )
        db.add(baseline)
        db.flush()
        asset.current_baseline_id = baseline.id
        db.add(
            AuditEntry(
                organization_id=current_user.organization_id,
                actor_id=current_user.id,
                action="baseline.approved",
                entity_type="baseline",
                entity_id=baseline.id,
                details={
                    "scan_id": scan.id,
                    "website_asset_id": scan.website_asset_id,
                    "previous_baseline_ids": [
                        previous.id for previous in previous_baselines
                    ],
                },
            )
        )
        db.commit()
        created = db.scalar(
            select(Baseline)
            .options(joinedload(Baseline.scan))
            .where(Baseline.id == baseline.id)
        )
        if created is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Baseline not found",
            )
        return BaselineRead.model_validate(created)


@router.get("/websites/{website_id}/baseline", response_model=BaselineRead | None)
async def get_active_baseline(
    website_id: str,
    current_user: AuthenticatedUser,
) -> BaselineRead | None:
    with SessionLocal() as db:
        asset = db.get(WebsiteAsset, website_id)
        if asset is None or asset.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website asset not found",
            )
        baseline = db.scalar(
            select(Baseline)
            .options(joinedload(Baseline.scan))
            .where(
                Baseline.organization_id == current_user.organization_id,
                Baseline.website_asset_id == asset.id,
                Baseline.is_active.is_(True),
            )
            .order_by(Baseline.approved_at.desc())
        )
        return BaselineRead.model_validate(baseline) if baseline else None


@router.get("/evidence/screenshots/{scan_id}", response_model=None)
async def get_screenshot(
    scan_id: str,
    current_user: AuthenticatedUser,
) -> Response:
    scan = get_scan_in_current_organization(scan_id, current_user)
    if not scan.screenshot_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found",
        )
    try:
        path = screenshot_path_for_filename(get_settings(), scan.screenshot_filename)
    except ScreenshotError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found",
        ) from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found",
        )
    return Response(
        content=path.read_bytes(),
        media_type=scan.screenshot_content_type or "image/png",
    )
