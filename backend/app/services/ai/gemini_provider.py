from __future__ import annotations

import json
import logging
import re
from urllib.parse import quote

import httpx

from app.services.ai.base import AIProviderClient, AIProviderError
from app.services.ai.schemas import (
    AIAnalysisPrompt,
    AIConnectionTestResponse,
    AIIncidentAnalysisResponse,
    AIProviderRequest,
)
from app.services.ai.structured_output import (
    json_schema_for_model,
    validate_structured_response,
)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
logger = logging.getLogger(__name__)


class GeminiProvider(AIProviderClient):
    async def test_connection(self, request: AIProviderRequest) -> None:
        prompt = AIAnalysisPrompt(
            system_prompt="",
            user_prompt="Return a successful connection confirmation matching the supplied schema.",
            evidence={},
        )
        response = await self.generate_structured_response(
            request,
            prompt,
            AIConnectionTestResponse,
            max_output_tokens=80,
        )
        if response.status != "ok":
            raise AIProviderError("Provider returned invalid structured JSON")

    async def generate_analysis(
        self,
        request: AIProviderRequest,
        prompt: AIAnalysisPrompt,
        max_output_tokens: int = 900,
    ) -> AIIncidentAnalysisResponse:
        return await self.generate_structured_response(
            request,
            prompt,
            AIIncidentAnalysisResponse,
            max_output_tokens=max_output_tokens,
        )

    async def generate_structured_response(
        self,
        request: AIProviderRequest,
        prompt: AIAnalysisPrompt,
        response_model: type[AIConnectionTestResponse | AIIncidentAnalysisResponse],
        max_output_tokens: int,
    ) -> AIConnectionTestResponse | AIIncidentAnalysisResponse:
        model = request.model.removeprefix("models/")
        model_path = quote(model, safe="")
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt.user_prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
                "responseJsonSchema": json_schema_for_model(response_model),
            },
        }
        if prompt.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": prompt.system_prompt}]}
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    f"{GEMINI_BASE_URL}/models/{model_path}:generateContent",
                    headers={"x-goog-api-key": request.api_key},
                    json=payload,
                )
            if response.status_code >= 400:
                error_code, error_message = provider_error_details(response)
                logger.warning(
                    "Gemini provider request failed: status=%s code=%s message=%s",
                    response.status_code,
                    error_code or "unknown",
                    error_message or "unavailable",
                )
                raise AIProviderError(
                    safe_provider_error(
                        response.status_code,
                        error_code=error_code,
                        error_message=error_message,
                    )
                )
            content = structured_response_content(response.json())
            return validate_structured_response(content, response_model)
        except AIProviderError:
            raise
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError(
                "Provider returned an unexpected response shape"
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("Provider request failed safely") from exc


def structured_response_content(response_body: dict[str, object]) -> object:
    part = response_body["candidates"][0]["content"]["parts"][0]
    if not isinstance(part, dict):
        raise TypeError("Gemini response part is not an object")
    if "parsed" in part:
        return part["parsed"]
    if "text" in part:
        return part["text"]
    return part


def provider_error_details(response: httpx.Response) -> tuple[str | None, str | None]:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return None, sanitize_provider_message(response.text)
    if not isinstance(payload, dict):
        return None, None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None, None
    code = error.get("status") or error.get("code")
    message = error.get("message")
    return (
        str(code) if code is not None else None,
        sanitize_provider_message(str(message)) if message else None,
    )


def safe_provider_error(
    status_code: int,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
) -> str:
    code = (error_code or "").upper()
    message = (error_message or "").lower()
    if status_code == 401 or (
        "api key" in message and ("invalid" in message or "not valid" in message)
    ):
        return "Provider API key is invalid"
    if status_code == 403 or code == "PERMISSION_DENIED":
        return "Provider permission denied for this key or model"
    if status_code == 429:
        return "Provider quota was exceeded"
    if status_code == 404 or code == "NOT_FOUND":
        return "Configured Gemini model is unavailable"
    if status_code == 400:
        if "model" in message and (
            "not found" in message
            or "unavailable" in message
            or "unsupported" in message
        ):
            return "Configured Gemini model is unavailable"
        return "Gemini rejected the structured-output schema or request"
    return "Provider returned an error"


def sanitize_provider_message(message: str) -> str:
    collapsed = " ".join(message.split())
    without_keys = re.sub(r"AIza[0-9A-Za-z_-]+", "[redacted]", collapsed)
    without_key_params = re.sub(
        r"(?i)(key|api_key|x-goog-api-key)=([^&\s]+)",
        r"\1=[redacted]",
        without_keys,
    )
    return without_key_params[:300]
