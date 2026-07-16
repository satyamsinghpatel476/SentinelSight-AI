"""comparison incidents audit

Revision ID: 202607160004
Revises: 202607160003
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607160004"
down_revision: str | None = "202607160003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("baseline_scan_id", sa.String(length=36)))
    op.add_column("scans", sa.Column("title_changed", sa.Boolean()))
    op.add_column("scans", sa.Column("baseline_title", sa.String(length=512)))
    op.add_column("scans", sa.Column("current_title", sa.String(length=512)))
    op.add_column("scans", sa.Column("text_similarity_percent", sa.Float()))
    op.add_column("scans", sa.Column("visual_change_percent", sa.Float()))
    op.add_column("scans", sa.Column("visual_change_level", sa.String(length=32)))
    op.add_column("scans", sa.Column("perceptual_hash_distance", sa.Integer()))
    op.add_column(
        "scans", sa.Column("difference_image_filename", sa.String(length=128))
    )
    op.add_column(
        "scans", sa.Column("difference_image_content_type", sa.String(length=64))
    )
    op.add_column("scans", sa.Column("comparison_error", sa.String(length=1024)))
    op.add_column("scans", sa.Column("baseline_external_script_domains", sa.JSON()))
    op.add_column("scans", sa.Column("current_external_script_domains", sa.JSON()))
    op.add_column("scans", sa.Column("new_external_script_domains", sa.JSON()))
    op.add_column("scans", sa.Column("baseline_external_iframe_domains", sa.JSON()))
    op.add_column("scans", sa.Column("current_external_iframe_domains", sa.JSON()))
    op.add_column("scans", sa.Column("new_external_iframe_domains", sa.JSON()))
    op.add_column("scans", sa.Column("suspicious_phrases", sa.JSON()))
    op.add_column("scans", sa.Column("risk_score", sa.Integer()))
    op.add_column(
        "scans",
        sa.Column(
            "risk_level",
            sa.Enum(
                "low",
                "moderate",
                "high",
                "critical",
                name="risk_level",
                native_enum=False,
                length=32,
            ),
        ),
    )
    op.add_column("scans", sa.Column("risk_breakdown", sa.JSON()))
    op.create_index(op.f("ix_scans_baseline_scan_id"), "scans", ["baseline_scan_id"])

    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("website_asset_id", sa.String(length=36), nullable=False),
        sa.Column("scan_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "low",
                "moderate",
                "high",
                "critical",
                name="incident_severity",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_breakdown", sa.JSON()),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "investigating",
                "resolved",
                "false_positive",
                name="incident_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("assigned_to", sa.String(length=36)),
        sa.Column("resolution_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["website_asset_id"], ["website_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_id"),
    )
    op.create_index(
        op.f("ix_incidents_organization_id"), "incidents", ["organization_id"]
    )
    op.create_index(op.f("ix_incidents_scan_id"), "incidents", ["scan_id"], unique=True)
    op.create_index(op.f("ix_incidents_status"), "incidents", ["status"])
    op.create_index(
        op.f("ix_incidents_website_asset_id"), "incidents", ["website_asset_id"]
    )

    op.create_table(
        "incident_notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_incident_notes_incident_id"), "incident_notes", ["incident_id"]
    )
    op.create_index(
        op.f("ix_incident_notes_organization_id"),
        "incident_notes",
        ["organization_id"],
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("entry_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"])
    op.create_index(
        op.f("ix_audit_logs_organization_id"), "audit_logs", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_organization_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(
        op.f("ix_incident_notes_organization_id"), table_name="incident_notes"
    )
    op.drop_index(op.f("ix_incident_notes_incident_id"), table_name="incident_notes")
    op.drop_table("incident_notes")
    op.drop_index(op.f("ix_incidents_website_asset_id"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_status"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_scan_id"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_organization_id"), table_name="incidents")
    op.drop_table("incidents")
    op.drop_index(op.f("ix_scans_baseline_scan_id"), table_name="scans")
    for column_name in [
        "risk_breakdown",
        "risk_level",
        "risk_score",
        "suspicious_phrases",
        "new_external_iframe_domains",
        "current_external_iframe_domains",
        "baseline_external_iframe_domains",
        "new_external_script_domains",
        "current_external_script_domains",
        "baseline_external_script_domains",
        "comparison_error",
        "difference_image_content_type",
        "difference_image_filename",
        "perceptual_hash_distance",
        "visual_change_level",
        "visual_change_percent",
        "text_similarity_percent",
        "current_title",
        "baseline_title",
        "title_changed",
        "baseline_scan_id",
    ]:
        op.drop_column("scans", column_name)
