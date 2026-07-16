from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.database import SessionLocal
from app.core.enums import UserRole
from app.models.user import User
from app.security.tokens import AUTH_COOKIE_NAME, decode_access_token


@dataclass(frozen=True)
class CurrentUser:
    id: str
    organization_id: str
    name: str
    email: str
    role: UserRole
    is_active: bool


async def get_current_user(request: Request) -> CurrentUser:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = decode_access_token(token)
    with SessionLocal() as db:
        user = db.get(User, payload["sub"])
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return CurrentUser(
            id=user.id,
            organization_id=user.organization_id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        )


def require_roles(
    *allowed_roles: UserRole,
) -> Callable[[Annotated[CurrentUser, Depends(get_current_user)]], CurrentUser]:
    async def dependency(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission",
            )
        return current_user

    return dependency
