"""ai configuration analysis

Revision ID: 202607160005
Revises: 202607160004
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607160005"
down_revision: str | None = "202607160004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_configurations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column(
            "provider",
            sa.Enum(
                "gemini",
                "openai",
                "openai_compatible",
                name="ai_provider",
                native_enum=False,
                length=32,
            ),
        ),
        sa.Column("model", sa.String(length=255)),
        sa.Column("encrypted_api_key", sa.Text()),
        sa.Column("api_key_last_four", sa.String(length=8)),
        sa.Column("base_url", sa.String(length=1024)),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("updated_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id"),
    )
    op.create_index(
        op.f("ix_ai_configurations_organization_id"),
        "ai_configurations",
        ["organization_id"],
        unique=True,
    )

    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("scan_id", sa.String(length=36)),
        sa.Column("incident_id", sa.String(length=36)),
        sa.Column("requested_by", sa.String(length=36), nullable=False),
        sa.Column(
            "provider",
            sa.Enum(
                "gemini",
                "openai",
                "openai_compatible",
                name="ai_analysis_provider",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("incident_summary", sa.Text()),
        sa.Column("priority_explanation", sa.Text()),
        sa.Column("immediate_actions_json", sa.JSON()),
        sa.Column("long_term_actions_json", sa.JSON()),
        sa.Column("false_positive_factors_json", sa.JSON()),
        sa.Column("confidence_note", sa.Text()),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "completed",
                "failed",
                name="ai_analysis_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(length=1024)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_analyses_incident_id"), "ai_analyses", ["incident_id"])
    op.create_index(
        op.f("ix_ai_analyses_organization_id"), "ai_analyses", ["organization_id"]
    )
    op.create_index(op.f("ix_ai_analyses_scan_id"), "ai_analyses", ["scan_id"])
    op.create_index(op.f("ix_ai_analyses_status"), "ai_analyses", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_analyses_status"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_scan_id"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_organization_id"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_incident_id"), table_name="ai_analyses")
    op.drop_table("ai_analyses")
    op.drop_index(
        op.f("ix_ai_configurations_organization_id"),
        table_name="ai_configurations",
    )
    op.drop_table("ai_configurations")
