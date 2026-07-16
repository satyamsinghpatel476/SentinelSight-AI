from __future__ import annotations

import json
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from app.services.ai.base import AIProviderClient, AIProviderError
from app.services.ai.schemas import (
    AIAnalysisPrompt,
    AIIncidentAnalysisResponse,
    AIProviderRequest,
)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(AIProviderClient):
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
        await self.generate_analysis(request, prompt, max_output_tokens=120)

    async def generate_analysis(
        self,
        request: AIProviderRequest,
        prompt: AIAnalysisPrompt,
        max_output_tokens: int = 900,
    ) -> AIIncidentAnalysisResponse:
        model = request.model.removeprefix("models/")
        model_path = quote(model, safe="")
        payload = {
            "systemInstruction": {"parts": [{"text": prompt.system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": prompt.user_prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    f"{GEMINI_BASE_URL}/models/{model_path}:generateContent",
                    params={"key": request.api_key},
                    json=payload,
                )
            if response.status_code >= 400:
                raise AIProviderError(safe_provider_error(response.status_code))
            content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return parse_analysis_json(str(content))
        except AIProviderError:
            raise
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError(
                "Provider returned an unexpected response shape"
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("Provider request failed safely") from exc


def parse_analysis_json(raw_content: str) -> AIIncidentAnalysisResponse:
    try:
        parsed = json.loads(raw_content)
        return AIIncidentAnalysisResponse.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AIProviderError("Provider returned invalid structured JSON") from exc


def safe_provider_error(status_code: int) -> str:
    if status_code in {400, 404}:
        return "Provider rejected the configured model or request"
    if status_code in {401, 403}:
        return "Provider rejected the API key or authorization"
    if status_code == 429:
        return "Provider rate limit or quota was reached"
    return "Provider returned an error"
