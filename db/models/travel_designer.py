from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class TravelDesignerProfile(Base):
    __tablename__ = "travel_designer_profiles"
    __table_args__ = (
        UniqueConstraint("email", name="uq_travel_designer_profiles_email"),
        Index("ix_travel_designer_profiles_active_email", "is_active", "email"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    # Kept as an id without an FK to avoid a media_assets ↔ quotations cycle;
    # profile image ownership is validated by the API before assignment.
    image_asset_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    storage_slug: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    image_r2_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class TravelDesignerBrandDefault(Base):
    __tablename__ = "travel_designer_brand_defaults"

    brand_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    designer_profile_id: Mapped[str] = mapped_column(
        ForeignKey("travel_designer_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
