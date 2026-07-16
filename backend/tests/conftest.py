from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

import pytest
from app.core.database import SessionLocal
from app.core.enums import UserRole
from app.models import Base, Organization, User
from app.security.passwords import hash_password
from app.services.rate_limiter import login_rate_limiter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture(autouse=True)
def isolated_database() -> Generator[None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    previous_bind = SessionLocal.kw.get("bind")
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(bind=engine)
    login_rate_limiter.clear()

    try:
        yield
    finally:
        Base.metadata.drop_all(bind=engine)
        SessionLocal.configure(bind=previous_bind)
        login_rate_limiter.clear()


@dataclass(frozen=True)
class SeededUsers:
    organization_a: Organization
    organization_b: Organization
    admin: User
    analyst: User
    viewer: User
    inactive: User
    other_admin: User


def create_user(
    db: Session,
    *,
    organization_id: str,
    email: str,
    role: UserRole,
    is_active: bool = True,
) -> User:
    user = User(
        organization_id=organization_id,
        name=email.split("@")[0].replace(".", " ").title(),
        email=email,
        password_hash=hash_password("Correct Horse Battery Staple!"),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    return user


@pytest.fixture
def seeded_users() -> SeededUsers:
    with SessionLocal() as db:
        organization_a = Organization(name="Organization A")
        organization_b = Organization(name="Organization B")
        db.add_all([organization_a, organization_b])
        db.flush()

        admin = create_user(
            db,
            organization_id=organization_a.id,
            email="admin@example.com",
            role=UserRole.administrator,
        )
        analyst = create_user(
            db,
            organization_id=organization_a.id,
            email="analyst@example.com",
            role=UserRole.security_analyst,
        )
        viewer = create_user(
            db,
            organization_id=organization_a.id,
            email="viewer@example.com",
            role=UserRole.viewer,
        )
        inactive = create_user(
            db,
            organization_id=organization_a.id,
            email="inactive@example.com",
            role=UserRole.viewer,
            is_active=False,
        )
        other_admin = create_user(
            db,
            organization_id=organization_b.id,
            email="other-admin@example.com",
            role=UserRole.administrator,
        )
        db.commit()
        for item in [
            organization_a,
            organization_b,
            admin,
            analyst,
            viewer,
            inactive,
            other_admin,
        ]:
            db.refresh(item)
        return SeededUsers(
            organization_a=organization_a,
            organization_b=organization_b,
            admin=admin,
            analyst=analyst,
            viewer=viewer,
            inactive=inactive,
            other_admin=other_admin,
        )
