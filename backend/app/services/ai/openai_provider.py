from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from app.core.enums import AIProvider
from app.services.ai.base import AIProviderClient, AIProviderError
from app.services.ai.schemas import (
    AIAnalysisPrompt,
    AIIncidentAnalysisResponse,
    AIProviderRequest,
)

OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAIProvider(AIProviderClient):
    async def test_connection(self, request: AIProviderRequest) -> None:
        prompt = AIAnalysisPrompt(
            system_prompt="Return JSON only.",
            user_prompt=(
                "Return this JSON exactly: "
                '{"incident_summary":"ok","priority_explanation":"ok",'
                '"immediate_actions":["ok"],"long_term_actions":["ok"],'
                '"possible_false_positive_factors":["ok"],"confidence_note":"ok"}'
            ),
            evidence={},
        )
        await self.generate_analysis(request, prompt, max_tokens=120)

    async def generate_analysis(
        self,
        request: AIProviderRequest,
        prompt: AIAnalysisPrompt,
        max_tokens: int = 900,
    ) -> AIIncidentAnalysisResponse:
        base_url = provider_base_url(request)
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {request.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
            if response.status_code >= 400:
                raise AIProviderError(safe_provider_error(response.status_code))
            content = response.json()["choices"][0]["message"]["content"]
            return parse_analysis_json(str(content))
        except AIProviderError:
            raise
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError(
                "Provider returned an unexpected response shape"
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("Provider request failed safely") from exc


def provider_base_url(request: AIProviderRequest) -> str:
    if request.provider == AIProvider.openai:
        return OPENAI_DEFAULT_BASE_URL
    if not request.base_url:
        raise AIProviderError("OpenAI-compatible provider requires a base URL")
    return request.base_url.rstrip("/")


def parse_analysis_json(raw_content: str) -> AIIncidentAnalysisResponse:
    try:
        parsed = json.loads(raw_content)
        return AIIncidentAnalysisResponse.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AIProviderError("Provider returned invalid structured JSON") from exc


def safe_provider_error(status_code: int) -> str:
    if status_code in {401, 403}:
        return "Provider rejected the API key or authorization"
    if status_code == 404:
        return "Provider model or endpoint was not found"
    if status_code == 429:
        return "Provider rate limit or quota was reached"
    return "Provider returned an error"
