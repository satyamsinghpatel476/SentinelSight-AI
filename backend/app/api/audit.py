from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

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
            .where(AuditLog.organization_id == current_user.organization_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        ).all()
        return [AuditLogRead.model_validate(record) for record in records]


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
