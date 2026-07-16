from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FindingSeverity, IncidentStatus
from app.models.base import Base
from app.utils.ids import new_uuid
from app.utils.time import utc_now


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    website_asset_id: Mapped[str] = mapped_column(
        ForeignKey("website_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(
            FindingSeverity,
            values_callable=lambda enum_cls: [severity.value for severity in enum_cls],
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_breakdown: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(
            IncidentStatus,
            values_callable=lambda enum_cls: [status.value for status in enum_cls],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=IncidentStatus.open,
        index=True,
    )
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    website_asset = relationship("WebsiteAsset")
    scan = relationship("Scan")
    assignee = relationship("User")
    notes = relationship(
        "IncidentNote", back_populates="incident", cascade="all, delete-orphan"
    )
