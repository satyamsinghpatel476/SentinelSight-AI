from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogRead, AuditVerificationRead
from app.security.dependencies import CurrentUser, get_current_user
from app.services.audit_log import verify_audit_chain

router = APIRouter(tags=["audit"])

AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/audit", response_model=list[AuditLogRead])
async def list_audit_logs(current_user: AuthenticatedUser) -> list[AuditLogRead]:
    with SessionLocal() as db:
        records = db.scalars(
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(AuditLog.organization_id == current_user.organization_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        ).all()
        return [audit_log_read(record) for record in records]


@router.get("/audit/verify", response_model=AuditVerificationRead)
async def verify_audit_logs(
    current_user: AuthenticatedUser,
) -> AuditVerificationRead:
    with SessionLocal() as db:
        records = db.scalars(
            select(AuditLog)
            .where(AuditLog.organization_id == current_user.organization_id)
            .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        ).all()
        result = verify_audit_chain(list(records))
        return AuditVerificationRead(
            valid=result.valid,
            records_checked=result.records_checked,
            first_broken_record_id=result.first_broken_record_id,
        )


def audit_log_read(record: AuditLog) -> AuditLogRead:
    return AuditLogRead(
        id=record.id,
        organization_id=record.organization_id,
        user_id=record.user_id,
        user_name=record.user.name if record.user else None,
        user_email=record.user.email if record.user else None,
        action=record.action,
        resource_type=record.resource_type,
        resource_id=record.resource_id,
        metadata_json=record.metadata_json,
        previous_hash=record.previous_hash,
        entry_hash=record.entry_hash,
        created_at=record.created_at,
    )
