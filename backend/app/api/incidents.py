from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.core.enums import IncidentStatus, UserRole
from app.models.finding import Finding
from app.models.incident import Incident
from app.models.incident_note import IncidentNote
from app.models.user import User
from app.schemas.incidents import IncidentNoteCreate, IncidentRead, IncidentUpdate
from app.schemas.scans import FindingRead, ScanRead
from app.schemas.websites import WebsiteAssetRead
from app.security.dependencies import CurrentUser, get_current_user, require_roles
from app.services.audit_log import create_audit_log
from app.utils.time import utc_now

router = APIRouter(tags=["incidents"])

AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
IncidentManager = Annotated[
    CurrentUser,
    Depends(require_roles(UserRole.administrator, UserRole.security_analyst)),
]

ALLOWED_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.open: {IncidentStatus.investigating, IncidentStatus.false_positive},
    IncidentStatus.investigating: {
        IncidentStatus.resolved,
        IncidentStatus.false_positive,
    },
    IncidentStatus.resolved: {IncidentStatus.investigating},
    IncidentStatus.false_positive: {IncidentStatus.investigating},
}


@router.get("/incidents", response_model=list[IncidentRead])
async def list_incidents(current_user: AuthenticatedUser) -> list[IncidentRead]:
    with SessionLocal() as db:
        incidents = db.scalars(
            select(Incident)
            .options(
                selectinload(Incident.website_asset),
                selectinload(Incident.scan),
                selectinload(Incident.notes),
            )
            .where(Incident.organization_id == current_user.organization_id)
            .order_by(Incident.created_at.desc())
        ).all()
        return [incident_to_read(db, incident) for incident in incidents]


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
async def get_incident(
    incident_id: str,
    current_user: AuthenticatedUser,
) -> IncidentRead:
    with SessionLocal() as db:
        incident = get_incident_for_user(db, incident_id, current_user)
        return incident_to_read(db, incident)


@router.patch("/incidents/{incident_id}", response_model=IncidentRead)
async def update_incident(
    incident_id: str,
    payload: IncidentUpdate,
    current_user: IncidentManager,
) -> IncidentRead:
    with SessionLocal() as db:
        incident = get_incident_for_user(db, incident_id, current_user)
        changed_status = False
        old_status = incident.status

        if payload.assigned_to is not None:
            assignee = db.get(User, payload.assigned_to)
            if (
                assignee is None
                or assignee.organization_id != current_user.organization_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assignee not found",
                )
            incident.assigned_to = assignee.id

        if payload.resolution_notes is not None:
            incident.resolution_notes = payload.resolution_notes

        if payload.status is not None and payload.status != incident.status:
            validate_transition(incident.status, payload.status)
            incident.status = payload.status
            changed_status = True
            if payload.status in {
                IncidentStatus.resolved,
                IncidentStatus.false_positive,
            }:
                incident.resolved_at = utc_now()
            elif payload.status == IncidentStatus.investigating:
                incident.resolved_at = None

        db.flush()
        if changed_status:
            action = action_for_status(incident.status, old_status)
            create_audit_log(
                db,
                organization_id=current_user.organization_id,
                user_id=current_user.id,
                action=action,
                resource_type="incident",
                resource_id=incident.id,
                metadata={
                    "from": old_status.value,
                    "to": incident.status.value,
                    "scan_id": incident.scan_id,
                },
            )
        elif payload.resolution_notes is not None or payload.assigned_to is not None:
            create_audit_log(
                db,
                organization_id=current_user.organization_id,
                user_id=current_user.id,
                action="incident.updated",
                resource_type="incident",
                resource_id=incident.id,
                metadata={"scan_id": incident.scan_id},
            )
        db.commit()
        refreshed = get_incident_for_user(db, incident_id, current_user)
        return incident_to_read(db, refreshed)


@router.post("/incidents/{incident_id}/notes", response_model=IncidentRead)
async def add_incident_note(
    incident_id: str,
    payload: IncidentNoteCreate,
    current_user: IncidentManager,
) -> IncidentRead:
    with SessionLocal() as db:
        incident = get_incident_for_user(db, incident_id, current_user)
        note = IncidentNote(
            organization_id=current_user.organization_id,
            incident_id=incident.id,
            user_id=current_user.id,
            content=payload.content,
        )
        db.add(note)
        db.flush()
        create_audit_log(
            db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            action="incident.note_added",
            resource_type="incident",
            resource_id=incident.id,
            metadata={"note_id": note.id, "scan_id": incident.scan_id},
        )
        db.commit()
        refreshed = get_incident_for_user(db, incident_id, current_user)
        return incident_to_read(db, refreshed)


def get_incident_for_user(
    db,
    incident_id: str,
    current_user: CurrentUser,
) -> Incident:
    incident = db.scalar(
        select(Incident)
        .options(
            selectinload(Incident.website_asset),
            selectinload(Incident.scan),
            selectinload(Incident.notes),
        )
        .where(
            Incident.id == incident_id,
            Incident.organization_id == current_user.organization_id,
        )
    )
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )
    return incident


def incident_to_read(db, incident: Incident) -> IncidentRead:
    findings = db.scalars(
        select(Finding)
        .where(
            Finding.organization_id == incident.organization_id,
            Finding.scan_id == incident.scan_id,
        )
        .order_by(Finding.risk_points.desc(), Finding.created_at.asc())
    ).all()
    return IncidentRead(
        id=incident.id,
        organization_id=incident.organization_id,
        website_asset_id=incident.website_asset_id,
        scan_id=incident.scan_id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity,
        risk_score=incident.risk_score,
        risk_breakdown=incident.risk_breakdown,
        status=incident.status,
        assigned_to=incident.assigned_to,
        resolution_notes=incident.resolution_notes,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        website_asset=(
            WebsiteAssetRead.model_validate(incident.website_asset)
            if incident.website_asset
            else None
        ),
        scan=ScanRead.model_validate(incident.scan) if incident.scan else None,
        notes=list(incident.notes),
        findings=[FindingRead.model_validate(finding) for finding in findings],
    )


def validate_transition(current: IncidentStatus, desired: IncidentStatus) -> None:
    if desired not in ALLOWED_TRANSITIONS[current]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot change incident from {current.value} to {desired.value}",
        )


def action_for_status(
    new_status: IncidentStatus,
    old_status: IncidentStatus,
) -> str:
    if new_status == IncidentStatus.resolved:
        return "incident.resolved"
    if new_status == IncidentStatus.false_positive:
        return "incident.false_positive"
    if old_status in {IncidentStatus.resolved, IncidentStatus.false_positive}:
        return "incident.reopened"
    return "incident.status_changed"
