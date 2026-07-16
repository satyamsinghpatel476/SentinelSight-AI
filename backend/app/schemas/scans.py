from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import FindingSeverity, ScanStatus, ScanType


class ScanCreate(BaseModel):
    scan_type: ScanType = ScanType.comparison


class ScanRead(BaseModel):
    id: str
    organization_id: str
    website_asset_id: str
    requested_by: str
    scan_type: ScanType
    status: ScanStatus
    requested_url: str
    final_url: str | None
    http_status: int | None
    response_time_ms: int | None
    page_title: str | None
    visible_text_hash: str | None
    html_hash: str | None
    response_headers: dict[str, Any] | None
    external_script_domains: list[str] | None
    external_iframe_domains: list[str] | None
    redirect_chain: list[dict[str, Any]] | None
    failure_reason: str | None
    screenshot_filename: str | None
    screenshot_content_type: str | None
    screenshot_width: int | None
    screenshot_height: int | None
    screenshot_perceptual_hash: str | None
    started_at: datetime | None
    completed_at: datetime | None
    scanned_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingRead(BaseModel):
    id: str
    organization_id: str
    website_asset_id: str
    scan_id: str
    type: str = Field(validation_alias="finding_type", serialization_alias="type")
    title: str
    description: str
    severity: FindingSeverity
    evidence: str
    remediation: str
    risk_points: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BaselineRead(BaseModel):
    id: str
    organization_id: str
    website_asset_id: str
    scan_id: str
    approved_by: str
    approved_at: datetime
    is_active: bool
    created_at: datetime
    scan: ScanRead

    model_config = ConfigDict(from_attributes=True)
