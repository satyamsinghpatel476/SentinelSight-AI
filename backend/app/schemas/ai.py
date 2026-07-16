from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import AIAnalysisStatus, AIProvider


class AIConfigurationRead(BaseModel):
    provider: AIProvider | None
    model: str | None
    base_url: str | None
    is_enabled: bool
    timeout_seconds: int
    has_api_key: bool
    api_key_last_four: str | None


class AIStatusRead(BaseModel):
    is_configured: bool
    provider: AIProvider | None
    model: str | None
    is_enabled: bool
    has_api_key: bool


class AIConfigurationUpdate(BaseModel):
    provider: AIProvider | None = None
    model: str | None = Field(default=None, max_length=255)
    api_key: str | None = Field(default=None, max_length=4096)
    base_url: str | None = Field(default=None, max_length=1024)
    is_enabled: bool = False
    timeout_seconds: int = Field(default=20, ge=1, le=120)

    @field_validator("model", "api_key", "base_url")
    @classmethod
    def strip_blank_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class AIConnectionTestRead(BaseModel):
    success: bool
    message: str
    provider: AIProvider | None
    model: str | None


class AIAnalysisRead(BaseModel):
    id: str
    organization_id: str
    scan_id: str | None
    incident_id: str | None
    requested_by: str
    provider: AIProvider
    model: str
    prompt_version: str
    incident_summary: str | None
    priority_explanation: str | None
    immediate_actions: list[str] | None = Field(
        validation_alias="immediate_actions_json",
        serialization_alias="immediate_actions",
    )
    long_term_actions: list[str] | None = Field(
        validation_alias="long_term_actions_json",
        serialization_alias="long_term_actions",
    )
    possible_false_positive_factors: list[str] | None = Field(
        validation_alias="false_positive_factors_json",
        serialization_alias="possible_false_positive_factors",
    )
    confidence_note: str | None
    status: AIAnalysisStatus
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
