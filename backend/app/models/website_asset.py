from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import WebsiteRiskCategory
from app.models.base import Base
from app.utils.ids import new_uuid
from app.utils.time import utc_now


class WebsiteAsset(Base):
    __tablename__ = "website_assets"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "normalized_url",
            name="uq_website_assets_organization_normalized_url",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    authorization_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    monitoring_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    risk_category: Mapped[WebsiteRiskCategory] = mapped_column(
        Enum(
            WebsiteRiskCategory,
            values_callable=lambda enum_cls: [category.value for category in enum_cls],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=WebsiteRiskCategory.moderate,
    )
    contact_email: Mapped[str] = mapped_column(String(320), nullable=False)
    current_baseline_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
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

    organization = relationship("Organization")
    creator = relationship("User")
