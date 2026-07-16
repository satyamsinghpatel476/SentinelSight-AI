from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import WebsiteRiskCategory


class WebsiteAssetRead(BaseModel):
    id: str
    organization_id: str
    name: str
    url: str
    normalized_url: str
    authorization_confirmed: bool
    monitoring_enabled: bool
    risk_category: WebsiteRiskCategory
    contact_email: EmailStr
    current_baseline_id: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebsiteAssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    contact_email: EmailStr
    risk_category: WebsiteRiskCategory = WebsiteRiskCategory.moderate
    monitoring_enabled: bool = True
    authorization_confirmed: bool


class WebsiteAssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    contact_email: EmailStr | None = None
    risk_category: WebsiteRiskCategory | None = None
    monitoring_enabled: bool | None = None
    authorization_confirmed: bool | None = None
