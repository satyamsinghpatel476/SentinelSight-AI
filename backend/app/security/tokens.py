from __future__ import annotations

from datetime import timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.enums import UserRole
from app.utils.time import utc_now

AUTH_COOKIE_NAME = "sentinelsight_access"
TOKEN_ALGORITHM = "HS256"


def create_access_token(
    *,
    user_id: str,
    organization_id: str,
    role: UserRole,
) -> str:
    settings = get_settings()
    issued_at = utc_now()
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "organization_id": organization_id,
        "role": role.value,
        "type": "access",
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=TOKEN_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.app_secret_key, algorithms=[TOKEN_ALGORITHM]
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        ) from exc

    if payload.get("type") != "access" or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    return payload
