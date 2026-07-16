from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.utils.time import utc_now

AUDIT_GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditVerification:
    valid: bool
    records_checked: int
    first_broken_record_id: str | None


def create_audit_log(
    db: Session,
    *,
    organization_id: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    previous = db.scalar(
        select(AuditLog)
        .where(AuditLog.organization_id == organization_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    created_at = utc_now()
    if previous:
        previous_created_at = comparable_datetime(previous.created_at)
        current_created_at = comparable_datetime(created_at)
        if current_created_at <= previous_created_at:
            created_at = (previous_created_at + timedelta(microseconds=1)).replace(
                tzinfo=UTC
            )
    previous_hash = previous.entry_hash if previous else AUDIT_GENESIS_HASH
    entry_hash = calculate_entry_hash(
        previous_hash=previous_hash,
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata or {},
        created_at=created_at,
    )
    entry = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=metadata or {},
        previous_hash=previous_hash,
        entry_hash=entry_hash,
        created_at=created_at,
    )
    db.add(entry)
    db.flush()
    return entry


def verify_audit_chain(
    records: list[AuditLog],
) -> AuditVerification:
    previous_hash = AUDIT_GENESIS_HASH
    checked = 0
    for record in records:
        checked += 1
        if record.previous_hash != previous_hash:
            return AuditVerification(False, checked, record.id)
        expected_hash = calculate_entry_hash(
            previous_hash=record.previous_hash,
            organization_id=record.organization_id,
            user_id=record.user_id,
            action=record.action,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            metadata=record.metadata_json or {},
            created_at=record.created_at,
        )
        if record.entry_hash != expected_hash:
            return AuditVerification(False, checked, record.id)
        previous_hash = record.entry_hash
    return AuditVerification(True, checked, None)


def calculate_entry_hash(
    *,
    previous_hash: str,
    organization_id: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, Any],
    created_at: datetime,
) -> str:
    payload = {
        "organization_id": organization_id,
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "metadata": metadata,
        "created_at": canonical_timestamp(created_at),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(f"{previous_hash}{canonical}".encode()).hexdigest()


def comparable_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def canonical_timestamp(value: datetime) -> str:
    normalized = comparable_datetime(value)
    return f"{normalized.isoformat(timespec='microseconds')}Z"
