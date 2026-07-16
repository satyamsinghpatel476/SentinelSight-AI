from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    id: str
    organization_id: str
    user_id: str
    user_name: str | None = None
    user_email: str | None = None
    action: str
    resource_type: str
    resource_id: str
    metadata_json: dict[str, Any] | None
    previous_hash: str
    entry_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditVerificationRead(BaseModel):
    valid: bool
    records_checked: int
    first_broken_record_id: str | None
