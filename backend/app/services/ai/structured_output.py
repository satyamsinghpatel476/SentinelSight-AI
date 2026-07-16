from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.services.ai.base import AIProviderError

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


def json_schema_for_model(model: type[BaseModel]) -> dict[str, Any]:
    """Return a Gemini-safe JSON Schema generated from a Pydantic model."""

    schema = normalize_json_schema(model.model_json_schema())
    if schema.get("type") == "object" and isinstance(schema.get("properties"), dict):
        schema["required"] = list(schema["properties"])
        schema["additionalProperties"] = False
    return schema


def validate_structured_response(
    response: object,
    model: type[ResponseModel],
) -> ResponseModel:
    """Validate a parsed object or JSON text against the expected Pydantic model."""

    try:
        if isinstance(response, str):
            parsed = json.loads(strip_single_json_fence(response))
        else:
            parsed = response
        return model.model_validate(parsed)
    except (json.JSONDecodeError, TypeError, ValidationError) as exc:
        raise AIProviderError("Provider returned invalid structured JSON") from exc


def strip_single_json_fence(raw_content: str) -> str:
    """Defensively accept one surrounding ```json fence without extracting prose."""

    stripped = raw_content.strip()
    lower = stripped.lower()
    if not lower.startswith("```json") or not stripped.endswith("```"):
        return stripped

    first_newline = stripped.find("\n")
    if first_newline == -1:
        return stripped
    inner = stripped[first_newline + 1 : -3].strip()
    if "```" in inner:
        return stripped
    return inner


def normalize_json_schema(value: object) -> object:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key in UNSUPPORTED_SCHEMA_KEYS:
                continue
            if key == "const":
                normalized["enum"] = [item]
                continue
            if key in {"anyOf", "oneOf"}:
                collapsed = collapse_nullable_union(item)
                if collapsed is not None:
                    normalized.update(normalize_json_schema(collapsed))
                continue
            normalized[key] = normalize_json_schema(item)
        if normalized.get("type") == "object" and isinstance(
            normalized.get("properties"), dict
        ):
            normalized["required"] = list(normalized["properties"])
            normalized["additionalProperties"] = False
        return normalized
    if isinstance(value, list):
        return [normalize_json_schema(item) for item in value]
    return value


def collapse_nullable_union(value: object) -> dict[str, Any] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    non_null = [
        item
        for item in value
        if not (isinstance(item, dict) and item.get("type") == "null")
    ]
    if len(non_null) != 1 or not isinstance(non_null[0], dict):
        return None
    return non_null[0]


UNSUPPORTED_SCHEMA_KEYS = {
    "$defs",
    "$schema",
    "default",
    "examples",
    "format",
    "maxItems",
    "maxLength",
    "minItems",
    "minLength",
    "pattern",
    "readOnly",
    "title",
    "writeOnly",
}
