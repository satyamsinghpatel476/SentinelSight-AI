from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from app.core.enums import AIProvider


class AIIncidentAnalysisResponse(BaseModel):
    incident_summary: str = Field(min_length=1, max_length=3000)
    priority_explanation: str = Field(min_length=1, max_length=3000)
    immediate_actions: list[str] = Field(min_length=1, max_length=12)
    long_term_actions: list[str] = Field(min_length=1, max_length=12)
    possible_false_positive_factors: list[str] = Field(min_length=1, max_length=12)
    confidence_note: str = Field(min_length=1, max_length=2000)


@dataclass(frozen=True)
class AIProviderRequest:
    provider: AIProvider
    model: str
    api_key: str
    base_url: str | None
    timeout_seconds: int


@dataclass(frozen=True)
class AIAnalysisPrompt:
    system_prompt: str
    user_prompt: str
    evidence: dict[str, Any]
