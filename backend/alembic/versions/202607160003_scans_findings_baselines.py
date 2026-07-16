"""scans findings baselines

Revision ID: 202607160003
Revises: 202607160002
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607160003"
down_revision: str | None = "202607160002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("website_asset_id", sa.String(length=36), nullable=False),
        sa.Column("requested_by", sa.String(length=36), nullable=False),
        sa.Column(
            "scan_type",
            sa.Enum(
                "baseline",
                "comparison",
                name="scan_type",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "completed",
                "failed",
                name="scan_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("requested_url", sa.String(length=2048), nullable=False),
        sa.Column("final_url", sa.String(length=2048), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("page_title", sa.String(length=512), nullable=True),
        sa.Column("visible_text", sa.Text(), nullable=True),
        sa.Column("visible_text_hash", sa.String(length=64), nullable=True),
        sa.Column("html_hash", sa.String(length=64), nullable=True),
        sa.Column("response_headers", sa.JSON(), nullable=True),
        sa.Column("external_script_domains", sa.JSON(), nullable=True),
        sa.Column("external_iframe_domains", sa.JSON(), nullable=True),
        sa.Column("redirect_chain", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.String(length=1024), nullable=True),
        sa.Column("screenshot_filename", sa.String(length=128), nullable=True),
        sa.Column("screenshot_content_type", sa.String(length=64), nullable=True),
        sa.Column("screenshot_width", sa.Integer(), nullable=True),
        sa.Column("screenshot_height", sa.Integer(), nullable=True),
        sa.Column("screenshot_perceptual_hash", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["website_asset_id"], ["website_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scans_organization_id"), "scans", ["organization_id"])
    op.create_index(op.f("ix_scans_status"), "scans", ["status"])
    op.create_index(op.f("ix_scans_website_asset_id"), "scans", ["website_asset_id"])

    op.create_table(
        "findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("website_asset_id", sa.String(length=36), nullable=False),
        sa.Column("scan_id", sa.String(length=36), nullable=False),
        sa.Column("finding_type", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "low",
                "moderate",
                "high",
                "critical",
                name="finding_severity",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column("risk_points", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["website_asset_id"], ["website_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_findings_organization_id"), "findings", ["organization_id"]
    )
    op.create_index(op.f("ix_findings_scan_id"), "findings", ["scan_id"])
    op.create_index(
        op.f("ix_findings_website_asset_id"), "findings", ["website_asset_id"]
    )

    op.create_table(
        "baselines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("website_asset_id", sa.String(length=36), nullable=False),
        sa.Column("scan_id", sa.String(length=36), nullable=False),
        sa.Column("approved_by", sa.String(length=36), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["website_asset_id"], ["website_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_baselines_organization_id"), "baselines", ["organization_id"]
    )
    op.create_index(op.f("ix_baselines_scan_id"), "baselines", ["scan_id"])
    op.create_index(
        op.f("ix_baselines_website_asset_id"), "baselines", ["website_asset_id"]
    )

    op.create_table(
        "audit_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_entries_organization_id"), "audit_entries", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_entries_organization_id"), table_name="audit_entries")
    op.drop_table("audit_entries")
    op.drop_index(op.f("ix_baselines_website_asset_id"), table_name="baselines")
    op.drop_index(op.f("ix_baselines_scan_id"), table_name="baselines")
    op.drop_index(op.f("ix_baselines_organization_id"), table_name="baselines")
    op.drop_table("baselines")
    op.drop_index(op.f("ix_findings_website_asset_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_scan_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_organization_id"), table_name="findings")
    op.drop_table("findings")
    op.drop_index(op.f("ix_scans_website_asset_id"), table_name="scans")
    op.drop_index(op.f("ix_scans_status"), table_name="scans")
    op.drop_index(op.f("ix_scans_organization_id"), table_name="scans")
    op.drop_table("scans")
