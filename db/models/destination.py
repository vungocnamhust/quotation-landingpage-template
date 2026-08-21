from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class DestinationCatalog(Base):
    __tablename__ = "destination_catalog"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_destination_catalog_slug"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="ck_destination_catalog_latitude_range"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180", name="ck_destination_catalog_longitude_range"),
        Index("ix_destination_catalog_active_name", "is_active", "canonical_name"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    country_slug: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region_slug: Mapped[str | None] = mapped_column(String(128), nullable=True)
    province_slug: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(8, 5), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(8, 5), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    media_prefix: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    mapping_version: Mapped[str] = mapped_column(String(64), nullable=False, default="resolver-v1", server_default="resolver-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class DestinationAlias(Base):
    __tablename__ = "destination_aliases"
    __table_args__ = (UniqueConstraint("normalized_alias", name="uq_destination_aliases_normalized_alias"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destination_catalog.id", ondelete="CASCADE"), nullable=False, index=True)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
