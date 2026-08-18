from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PartnerProfile(Base):
    __tablename__ = "partner_profiles"
    __table_args__ = (
        UniqueConstraint("email", name="uq_partner_profiles_email"),
        Index("ix_partner_profiles_active_company", "is_active", "company_name"),
        Index("ix_partner_profiles_email", "email"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    market: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tier: Mapped[str | None] = mapped_column(String(32), nullable=True, default="Standard", server_default="Standard")  # Preferred, Standard, VIP
    default_commission_rate: Mapped[float] = mapped_column(Float, nullable=False, default=10.0, server_default="10.0")
    preferred_currency: Mapped[str] = mapped_column(String(16), nullable=False, default="USD", server_default="USD")
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
