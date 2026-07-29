from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import BIGINT_PK_VARIANT, JSON_VARIANT


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        Index("ix_media_assets_quotation_created_at", "quotation_id", "created_at"),
        Index("ix_media_assets_status_created_at", "status", "created_at"),
        Index("ix_media_assets_checksum_sha256", "checksum_sha256"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    quotation_id: Mapped[str | None] = mapped_column(
        ForeignKey("quotations.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    r2_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    preview_r2_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    local_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready", server_default="ready")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MediaSelection(Base):
    __tablename__ = "media_selections"
    __table_args__ = (
        Index(
            "uq_media_selections_shared_slot_order",
            "quotation_id",
            "section_key",
            "slot_key",
            "display_order",
            unique=True,
            sqlite_where=text("lang IS NULL"),
            postgresql_where=text("lang IS NULL"),
        ),
        Index(
            "uq_media_selections_lang_slot_order",
            "quotation_id",
            "lang",
            "section_key",
            "slot_key",
            "display_order",
            unique=True,
            sqlite_where=text("lang IS NOT NULL"),
            postgresql_where=text("lang IS NOT NULL"),
        ),
        Index("ix_media_selections_quotation_section_slot", "quotation_id", "section_key", "slot_key"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    quotation_id: Mapped[str] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    lang: Mapped[str | None] = mapped_column(String(5), nullable=True)
    section_key: Mapped[str] = mapped_column(String(128), nullable=False)
    slot_key: Mapped[str] = mapped_column(String(128), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
