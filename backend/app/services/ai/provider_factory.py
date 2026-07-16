from __future__ import annotations

from app.core.enums import AIProvider
from app.services.ai.base import AIProviderClient, AIProviderError
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider


def create_provider(provider: AIProvider) -> AIProviderClient:
    if provider == AIProvider.gemini:
        return GeminiProvider()
    if provider in {AIProvider.openai, AIProvider.openai_compatible}:
        return OpenAIProvider()
    raise AIProviderError("Unsupported AI provider")
