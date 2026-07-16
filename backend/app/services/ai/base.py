from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.ai.schemas import (
    AIAnalysisPrompt,
    AIIncidentAnalysisResponse,
    AIProviderRequest,
)


class AIProviderError(RuntimeError):
    def __init__(self, safe_message: str, http_status: int = 502) -> None:
        super().__init__(safe_message)
        self.safe_message = safe_message
        self.http_status = http_status


class AIProviderClient(ABC):
    @abstractmethod
    async def test_connection(self, request: AIProviderRequest) -> None:
        """Make a minimal real request to the configured provider."""

    @abstractmethod
    async def generate_analysis(
        self,
        request: AIProviderRequest,
        prompt: AIAnalysisPrompt,
    ) -> AIIncidentAnalysisResponse:
        """Generate and validate a structured AI incident analysis."""
