from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AccommodationProfile(Base):
    __tablename__ = "accommodation_profiles"
    __table_args__ = (
        UniqueConstraint("destination_id", "storage_slug", name="uq_accommodation_profiles_destination_storage_slug"),
        Index("ix_accommodation_profiles_active_name", "is_active", "name"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destination_catalog.id", ondelete="RESTRICT"), nullable=False, index=True)
    storage_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_prefix: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    room_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intro: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_date: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hotel_asset: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    room_asset: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
