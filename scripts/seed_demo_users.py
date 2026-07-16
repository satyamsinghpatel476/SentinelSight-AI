from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.enums import UserRole  # noqa: E402
from app.models import Base, Organization, User  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402

DEMO_ORGANIZATION_NAME = "SentinelSight Demo Organization"
PLACEHOLDER_PASSWORDS = {"", "change-me", "password", "password123"}


def env(name: str) -> str:
    return os.getenv(name, "").strip()


def create_or_update_user(
    *,
    email: str,
    password: str,
    name: str,
    role: UserRole,
    organization_id: str,
) -> str:
    if not email:
        return f"skipped {name}: email environment variable is not set"
    if password in PLACEHOLDER_PASSWORDS:
        return f"skipped {email}: set a non-placeholder password in the environment"

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email.lower()))
        if existing is not None:
            existing.name = name
            existing.role = role
            existing.organization_id = organization_id
            existing.is_active = True
            existing.password_hash = hash_password(password)
            db.commit()
            return f"updated {email}"

        user = User(
            organization_id=organization_id,
            name=name,
            email=email.lower(),
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        return f"created {email}"


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        organization = db.scalar(
            select(Organization).where(Organization.name == DEMO_ORGANIZATION_NAME)
        )
        if organization is None:
            organization = Organization(name=DEMO_ORGANIZATION_NAME)
            db.add(organization)
            db.commit()
            db.refresh(organization)
        organization_id = organization.id

    results = [
        create_or_update_user(
            email=env("DEMO_ADMIN_EMAIL"),
            password=env("DEMO_ADMIN_PASSWORD"),
            name="Demo Administrator",
            role=UserRole.administrator,
            organization_id=organization_id,
        ),
        create_or_update_user(
            email=env("DEMO_ANALYST_EMAIL"),
            password=env("DEMO_ANALYST_PASSWORD"),
            name="Demo Security Analyst",
            role=UserRole.security_analyst,
            organization_id=organization_id,
        ),
        create_or_update_user(
            email=env("DEMO_VIEWER_EMAIL"),
            password=env("DEMO_VIEWER_PASSWORD"),
            name="Demo Viewer",
            role=UserRole.viewer,
            organization_id=organization_id,
        ),
    ]

    for result in results:
        print(result)


if __name__ == "__main__":
    main()
