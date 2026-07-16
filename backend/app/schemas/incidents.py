from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import FindingSeverity, IncidentStatus
from app.schemas.scans import FindingRead, ScanRead
from app.schemas.websites import WebsiteAssetRead


class IncidentNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Note content is required")
        return stripped


class IncidentNoteRead(BaseModel):
    id: str
    organization_id: str
    incident_id: str
    user_id: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    resolution_notes: str | None = Field(default=None, max_length=4000)
    assigned_to: str | None = None

    @field_validator("resolution_notes")
    @classmethod
    def normalize_resolution_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class IncidentRead(BaseModel):
    id: str
    organization_id: str
    website_asset_id: str
    scan_id: str
    title: str
    description: str
    severity: FindingSeverity
    risk_score: int
    risk_breakdown: list[dict[str, Any]] | None
    status: IncidentStatus
    assigned_to: str | None
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    website_asset: WebsiteAssetRead | None = None
    scan: ScanRead | None = None
    notes: list[IncidentNoteRead] = Field(default_factory=list)
    findings: list[FindingRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
