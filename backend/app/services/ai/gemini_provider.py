from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

from app.services.ai.base import AIProviderClient, AIProviderError
from app.services.ai.schemas import (
    AIAnalysisPrompt,
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
            user_prompt="Reply with exactly OK.",
            evidence={},
        )
        await self.generate_text(
            request,
            prompt,
            max_output_tokens=256,
            thinking_level="minimal",
        )

    async def generate_analysis(
        self,
        request: AIProviderRequest,
        prompt: AIAnalysisPrompt,
        max_output_tokens: int = 2048,
    ) -> AIIncidentAnalysisResponse:
        text = await self.generate_text(
            request,
            prompt,
            max_output_tokens=max_output_tokens,
            response_schema=json_schema_for_model(AIIncidentAnalysisResponse),
            thinking_level="minimal",
        )
        return validate_structured_response(text, AIIncidentAnalysisResponse)

    async def generate_text(
        self,
        request: AIProviderRequest,
        prompt: AIAnalysisPrompt,
        max_output_tokens: int,
        response_schema: dict[str, Any] | None = None,
        thinking_level: str | None = None,
    ) -> str:
        model = request.model.removeprefix("models/")
        model_path = quote(model, safe="")
        generation_config: dict[str, object] = {
            "maxOutputTokens": max_output_tokens,
        }
        if thinking_level is not None:
            generation_config["thinkingConfig"] = {"thinkingLevel": thinking_level}
        if response_schema is not None:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseJsonSchema"] = response_schema

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt.user_prompt}]}],
            "generationConfig": generation_config,
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
                error = safe_provider_error(
                    response.status_code,
                    error_code=error_code,
                    error_message=error_message,
                )
                logger.warning(
                    (
                        "Gemini provider request failed: provider=gemini "
                        "model=%s upstream_status=%s finish_reason=%s "
                        "candidate_count=%s usable_text_parts=%s error_code=%s "
                        "safe_error_category=%s message=%s"
                    ),
                    model,
                    response.status_code,
                    "none",
                    0,
                    0,
                    error_code or "unknown",
                    error.safe_message,
                    error_message or "unavailable",
                )
                raise error
            response_body = response.json()
            try:
                text = extract_gemini_text(response_body)
            except AIProviderError as exc:
                log_gemini_response_diagnostics(
                    request=request,
                    response_body=response_body,
                    upstream_status=response.status_code,
                    safe_error_category=exc.safe_message,
                )
                raise
            log_gemini_response_diagnostics(
                request=request,
                response_body=response_body,
                upstream_status=response.status_code,
                safe_error_category=None,
            )
            return text
        except AIProviderError:
            raise
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError(
                "Provider returned an unexpected response shape",
                http_status=502,
            ) from exc
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                "Provider request timed out", http_status=504
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                "Provider request failed safely",
                http_status=502,
            ) from exc


def extract_gemini_text(response_body: dict[str, Any]) -> str:
    texts: list[str] = []
    candidates = response_body.get("candidates", [])
    if isinstance(candidates, list):
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content") or {}
            if not isinstance(content, dict):
                continue
            parts = content.get("parts", [])
            if not isinstance(parts, list):
                continue
            for part in parts:
                if not isinstance(part, dict):
                    continue
                if part.get("thought") is True:
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())

    if texts:
        return "\n".join(texts)

    prompt_feedback = response_body.get("promptFeedback") or {}
    block_reason = (
        prompt_feedback.get("blockReason")
        if isinstance(prompt_feedback, dict)
        else None
    )
    finish_reasons = gemini_finish_reasons(response_body)

    if block_reason:
        error = AIProviderError(
            f"Gemini blocked the request: {block_reason}",
            http_status=502,
        )
        raise error

    if finish_reasons:
        raise AIProviderError(
            "Gemini returned no text. Finish reason: " + ", ".join(finish_reasons),
            http_status=502,
        )

    raise AIProviderError("Gemini returned no usable text content", http_status=502)


def gemini_finish_reasons(response_body: dict[str, Any]) -> list[str]:
    candidates = response_body.get("candidates", [])
    if not isinstance(candidates, list):
        return []
    reasons: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        reason = candidate.get("finishReason")
        if reason:
            reasons.append(str(reason))
    return reasons


def gemini_diagnostic_counts(response_body: dict[str, Any]) -> tuple[int, int]:
    candidates = response_body.get("candidates", [])
    if not isinstance(candidates, list):
        return 0, 0
    usable_text_parts = 0
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") or {}
        if not isinstance(content, dict):
            continue
        parts = content.get("parts", [])
        if not isinstance(parts, list):
            continue
        for part in parts:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                usable_text_parts += 1
    return len(candidates), usable_text_parts


def log_gemini_response_diagnostics(
    *,
    request: AIProviderRequest,
    response_body: dict[str, Any],
    upstream_status: int,
    safe_error_category: str | None,
) -> None:
    candidate_count, usable_text_parts = gemini_diagnostic_counts(response_body)
    finish_reasons = gemini_finish_reasons(response_body)
    log = logger.warning if safe_error_category else logger.info
    log(
        (
            "Gemini provider response: provider=%s model=%s upstream_status=%s "
            "finish_reason=%s candidate_count=%s usable_text_parts=%s "
            "safe_error_category=%s"
        ),
        request.provider.value,
        request.model,
        upstream_status,
        ",".join(finish_reasons) if finish_reasons else "none",
        candidate_count,
        usable_text_parts,
        safe_error_category or "none",
    )


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
) -> AIProviderError:
    code = (error_code or "").upper()
    message = (error_message or "").lower()
    if status_code == 401 or (
        "api key" in message and ("invalid" in message or "not valid" in message)
    ):
        return AIProviderError("Provider API key is invalid", http_status=401)
    if status_code == 403 or code == "PERMISSION_DENIED":
        return AIProviderError(
            "Provider permission denied for this key or model",
            http_status=403,
        )
    if status_code == 429:
        return AIProviderError("Provider quota was exceeded", http_status=429)
    if status_code == 404 or code == "NOT_FOUND":
        return AIProviderError(
            "Configured Gemini model is unavailable",
            http_status=400,
        )
    if status_code == 400:
        if "model" in message and (
            "not found" in message
            or "unavailable" in message
            or "unsupported" in message
        ):
            return AIProviderError(
                "Configured Gemini model is unavailable",
                http_status=400,
            )
        return AIProviderError(
            "Gemini rejected the structured-output schema or request",
            http_status=400,
        )
    return AIProviderError("Provider returned an error", http_status=502)


def sanitize_provider_message(message: str) -> str:
    collapsed = " ".join(message.split())
    without_keys = re.sub(r"AIza[0-9A-Za-z_-]+", "[redacted]", collapsed)
    without_key_params = re.sub(
        r"(?i)(key|api_key|x-goog-api-key)=([^&\s]+)",
        r"\1=[redacted]",
        without_keys,
    )
    return without_key_params[:300]
