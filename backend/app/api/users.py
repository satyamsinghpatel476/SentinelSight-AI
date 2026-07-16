from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import normalize_email
from app.core.database import SessionLocal
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.users import (
    UserCreate,
    UserRead,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
)
from app.security.dependencies import CurrentUser, require_roles
from app.security.passwords import hash_password

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[CurrentUser, Depends(require_roles(UserRole.administrator))]


def get_user_in_current_organization(
    db: Session, user_id: str, current_user: CurrentUser
) -> User:
    user = db.get(User, user_id)
    if user is None or user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("", response_model=list[UserRead])
async def list_users(
    current_user: AdminUser,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[UserRead]:
    with SessionLocal() as db:
        users = db.scalars(
            select(User)
            .where(User.organization_id == current_user.organization_id)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return [UserRead.model_validate(user) for user in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, current_user: AdminUser) -> UserRead:
    with SessionLocal() as db:
        user = User(
            organization_id=current_user.organization_id,
            name=payload.name.strip(),
            email=normalize_email(payload.email),
            password_hash=hash_password(payload.password),
            role=payload.role,
            is_active=payload.is_active,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            ) from exc
        db.refresh(user)
        return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: str, current_user: AdminUser) -> UserRead:
    with SessionLocal() as db:
        user = get_user_in_current_organization(db, user_id, current_user)
        return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: AdminUser,
) -> UserRead:
    with SessionLocal() as db:
        user = get_user_in_current_organization(db, user_id, current_user)
        if payload.name is not None:
            user.name = payload.name.strip()
        if payload.email is not None:
            user.email = normalize_email(payload.email)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            ) from exc
        db.refresh(user)
        return UserRead.model_validate(user)


@router.patch("/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    current_user: AdminUser,
) -> UserRead:
    with SessionLocal() as db:
        user = get_user_in_current_organization(db, user_id, current_user)
        user.role = payload.role
        db.commit()
        db.refresh(user)
        return UserRead.model_validate(user)


@router.patch("/{user_id}/status", response_model=UserRead)
async def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    current_user: AdminUser,
) -> UserRead:
    with SessionLocal() as db:
        user = get_user_in_current_organization(db, user_id, current_user)
        user.is_active = payload.is_active
        db.commit()
        db.refresh(user)
        return UserRead.model_validate(user)
