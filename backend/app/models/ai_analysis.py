from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AIAnalysisStatus, AIProvider
from app.models.base import Base
from app.utils.ids import new_uuid
from app.utils.time import utc_now


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_id: Mapped[str | None] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"),
        index=True,
    )
    incident_id: Mapped[str | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        index=True,
    )
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider: Mapped[AIProvider] = mapped_column(
        Enum(
            AIProvider,
            values_callable=lambda enum_cls: [provider.value for provider in enum_cls],
            native_enum=False,
            length=32,
        ),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    incident_summary: Mapped[str | None] = mapped_column(Text)
    priority_explanation: Mapped[str | None] = mapped_column(Text)
    immediate_actions_json: Mapped[list[str] | None] = mapped_column(JSON)
    long_term_actions_json: Mapped[list[str] | None] = mapped_column(JSON)
    false_positive_factors_json: Mapped[list[str] | None] = mapped_column(JSON)
    confidence_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[AIAnalysisStatus] = mapped_column(
        Enum(
            AIAnalysisStatus,
            values_callable=lambda enum_cls: [status.value for status in enum_cls],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=AIAnalysisStatus.pending,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization = relationship("Organization")
    scan = relationship("Scan")
    incident = relationship("Incident")
    requester = relationship("User")
