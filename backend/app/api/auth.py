from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, LogoutResponse
from app.schemas.users import UserRead
from app.security.dependencies import CurrentUser, get_current_user
from app.security.passwords import verify_password
from app.security.tokens import AUTH_COOKIE_NAME, create_access_token
from app.services.rate_limiter import login_rate_limiter
from app.utils.time import utc_now

router = APIRouter(prefix="/auth", tags=["authentication"])


def normalize_email(email: str) -> str:
    return email.strip().lower()


def login_rate_limit_key(request: Request, email: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{normalize_email(email)}"


def set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
) -> AuthResponse:
    email = normalize_email(payload.email)
    rate_limit_key = login_rate_limit_key(request, email)
    login_rate_limiter.check(rate_limit_key)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None or not verify_password(payload.password, user.password_hash):
            login_rate_limiter.record_failure(rate_limit_key)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            login_rate_limiter.record_failure(rate_limit_key)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        user.last_login_at = utc_now()
        db.commit()
        db.refresh(user)

        token = create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
        )
        set_auth_cookie(response, token)
        login_rate_limiter.reset(rate_limit_key)
        return AuthResponse(user=UserRead.model_validate(user))


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response) -> LogoutResponse:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite=get_settings().cookie_samesite,
    )
    return LogoutResponse(status="logged_out")


@router.get("/me", response_model=UserRead)
async def me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> UserRead:
    with SessionLocal() as db:
        user = db.get(User, current_user.id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return UserRead.model_validate(user)
