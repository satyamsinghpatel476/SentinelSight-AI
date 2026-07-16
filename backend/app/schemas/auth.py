from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.users import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class AuthResponse(BaseModel):
    user: UserRead


class LogoutResponse(BaseModel):
    status: str
