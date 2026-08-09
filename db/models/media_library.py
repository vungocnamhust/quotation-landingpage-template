from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import BIGINT_PK_VARIANT, JSON_VARIANT


class MediaLibrarySyncRun(Base):
    __tablename__ = "media_library_sync_runs"
    __table_args__ = (Index("ix_media_library_sync_runs_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", server_default="queued")
    prefixes: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    scanned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    indexed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    preview_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cursor: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class MediaLibraryObject(Base):
    __tablename__ = "media_library_objects"
    __table_args__ = (
        Index("ix_media_library_objects_parent_active", "parent_prefix", "is_active", "file_name"),
        Index("ix_media_library_objects_run", "last_seen_run_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    r2_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    parent_prefix: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    media_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    destination_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accommodation_slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accommodation_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="r2_sync", server_default="r2_sync")
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preview_r2_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preview_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    preview_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_seen_run_id: Mapped[str | None] = mapped_column(ForeignKey("media_library_sync_runs.id", ondelete="SET NULL"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
