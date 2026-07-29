from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import BIGINT_PK_VARIANT


class QuotationPublication(Base):
    __tablename__ = "quotation_publications"
    __table_args__ = (
        UniqueConstraint("quotation_id", "version", "lang", name="uq_quotation_publications_quotation_version_lang"),
        Index("ix_quotation_publications_quotation_version", "quotation_id", "version"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    quotation_id: Mapped[str] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    lang: Mapped[str] = mapped_column(String(5), nullable=False)
    html_r2_key: Mapped[str] = mapped_column(String(512), nullable=False)
    pdf_r2_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    published_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
