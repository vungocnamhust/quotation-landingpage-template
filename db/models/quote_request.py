from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from db.types import BIGINT_PK_VARIANT, JSON_VARIANT


class QuoteRequest(Base):
    __tablename__ = "quote_requests"
    __table_args__ = (
        Index("ix_quote_requests_status_created_at", "status", "created_at"),
        Index("ix_quote_requests_role_created_at", "role", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new", server_default="new")
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_contact: Mapped[str | None] = mapped_column(String(32), nullable=True)

    destinations: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    start_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_dates_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    adults: Mapped[int | None] = mapped_column(Integer, nullable=True, default=2)
    children: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    kid_ages: Mapped[list[int]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    children_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    travel_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    special_requirements: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)

    created_by_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("travel_designer_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_by_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("travel_designer_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    partner_id: Mapped[str | None] = mapped_column(
        ForeignKey("partner_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    linked_quotation_id: Mapped[str | None] = mapped_column(
        ForeignKey("quotations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

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

    revisions: Mapped[list[QuoteRequestRevision]] = relationship(
        "QuoteRequestRevision",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="desc(QuoteRequestRevision.revision)",
    )


class QuoteRequestRevision(Base):
    __tablename__ = "quote_request_revisions"
    __table_args__ = (
        Index("ix_quote_request_revisions_request_rev", "request_id", "revision", unique=True),
        Index("ix_quote_request_revisions_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_VARIANT, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(
        ForeignKey("quote_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_contact: Mapped[str | None] = mapped_column(String(32), nullable=True)

    destinations: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    start_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_dates_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    adults: Mapped[int | None] = mapped_column(Integer, nullable=True, default=2)
    children: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    kid_ages: Mapped[list[int]] = mapped_column(JSON_VARIANT, nullable=False, default=list)
    children_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    travel_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    special_requirements: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    change_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    change_source: Mapped[str] = mapped_column(String(64), nullable=False, default="initial_intake", server_default="initial_intake")

    created_by_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("travel_designer_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    request: Mapped[QuoteRequest] = relationship("QuoteRequest", back_populates="revisions")
