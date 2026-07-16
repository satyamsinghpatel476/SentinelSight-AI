"""website assets

Revision ID: 202607160002
Revises: 202607160001
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607160002"
down_revision: str | None = "202607160001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "website_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=False),
        sa.Column("authorization_confirmed", sa.Boolean(), nullable=False),
        sa.Column("monitoring_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "risk_category",
            sa.Enum(
                "low",
                "moderate",
                "high",
                "critical",
                name="website_risk_category",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("contact_email", sa.String(length=320), nullable=False),
        sa.Column("current_baseline_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "normalized_url",
            name="uq_website_assets_organization_normalized_url",
        ),
    )
    op.create_index(
        op.f("ix_website_assets_organization_id"),
        "website_assets",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_website_assets_organization_id"), table_name="website_assets"
    )
    op.drop_table("website_assets")
