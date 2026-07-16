from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RiskLevel, ScanStatus, ScanType
from app.models.base import Base
from app.utils.ids import new_uuid
from app.utils.time import utc_now


class Scan(Base):
    __tablename__ = "scans"

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
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    scan_type: Mapped[ScanType] = mapped_column(
        Enum(
            ScanType,
            values_callable=lambda enum_cls: [
                scan_type.value for scan_type in enum_cls
            ],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=ScanType.comparison,
    )
    status: Mapped[ScanStatus] = mapped_column(
        Enum(
            ScanStatus,
            values_callable=lambda enum_cls: [status.value for status in enum_cls],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=ScanStatus.queued,
        index=True,
    )
    requested_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    final_url: Mapped[str | None] = mapped_column(String(2048))
    http_status: Mapped[int | None] = mapped_column(Integer)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    page_title: Mapped[str | None] = mapped_column(String(512))
    visible_text: Mapped[str | None] = mapped_column(Text)
    visible_text_hash: Mapped[str | None] = mapped_column(String(64))
    html_hash: Mapped[str | None] = mapped_column(String(64))
    response_headers: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    external_script_domains: Mapped[list[str] | None] = mapped_column(JSON)
    external_iframe_domains: Mapped[list[str] | None] = mapped_column(JSON)
    redirect_chain: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    failure_reason: Mapped[str | None] = mapped_column(String(1024))
    screenshot_filename: Mapped[str | None] = mapped_column(String(128))
    screenshot_content_type: Mapped[str | None] = mapped_column(String(64))
    screenshot_width: Mapped[int | None] = mapped_column(Integer)
    screenshot_height: Mapped[int | None] = mapped_column(Integer)
    screenshot_perceptual_hash: Mapped[str | None] = mapped_column(String(64))
    baseline_scan_id: Mapped[str | None] = mapped_column(String(36), index=True)
    title_changed: Mapped[bool | None] = mapped_column(Boolean)
    baseline_title: Mapped[str | None] = mapped_column(String(512))
    current_title: Mapped[str | None] = mapped_column(String(512))
    text_similarity_percent: Mapped[float | None] = mapped_column(Float)
    visual_change_percent: Mapped[float | None] = mapped_column(Float)
    visual_change_level: Mapped[str | None] = mapped_column(String(32))
    perceptual_hash_distance: Mapped[int | None] = mapped_column(Integer)
    difference_image_filename: Mapped[str | None] = mapped_column(String(128))
    difference_image_content_type: Mapped[str | None] = mapped_column(String(64))
    comparison_error: Mapped[str | None] = mapped_column(String(1024))
    baseline_external_script_domains: Mapped[list[str] | None] = mapped_column(JSON)
    current_external_script_domains: Mapped[list[str] | None] = mapped_column(JSON)
    new_external_script_domains: Mapped[list[str] | None] = mapped_column(JSON)
    baseline_external_iframe_domains: Mapped[list[str] | None] = mapped_column(JSON)
    current_external_iframe_domains: Mapped[list[str] | None] = mapped_column(JSON)
    new_external_iframe_domains: Mapped[list[str] | None] = mapped_column(JSON)
    suspicious_phrases: Mapped[list[str] | None] = mapped_column(JSON)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[RiskLevel | None] = mapped_column(
        Enum(
            RiskLevel,
            values_callable=lambda enum_cls: [level.value for level in enum_cls],
            native_enum=False,
            length=32,
        )
    )
    risk_breakdown: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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

    website_asset = relationship("WebsiteAsset")
    requester = relationship("User")
    findings = relationship(
        "Finding", back_populates="scan", cascade="all, delete-orphan"
    )
