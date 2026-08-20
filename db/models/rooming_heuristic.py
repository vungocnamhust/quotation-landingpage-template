from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import JSON_VARIANT


class RoomingHeuristicRule(Base):
    """Dynamic rooming configuration heuristic rules with multilingual suggestion templates."""

    __tablename__ = "rooming_heuristic_rules"
    __table_args__ = (
        Index("ix_rooming_heuristics_priority_active", "priority", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Demographic Conditions
    min_adults: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_adults: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_children: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_children: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_infants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_infants: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Kid Age Filter: 'ANY' | 'ALL_UNDER_12' | 'ANY_12_AND_ABOVE' | 'NO_KIDS'
    kid_age_condition: Mapped[str] = mapped_column(String(32), default="ANY", nullable=False)

    # Suggestions payload: list of dicts with multilingual labels
    # e.g. [{"en": "1 Double + 1 Twin (Connecting)", "vi": "1 Phòng Double + 1 Phòng Twin (Thông nhau)", "ar": "غرفة مزدوجة + غرفة توأم متصلة"}]
    suggestions: Mapped[list[dict[str, Any]]] = mapped_column(JSON_VARIANT, nullable=False, default=list)

    # Minimum estimated rooms formula/constant (e.g., "1", "2", "ceil(adults / 2) + ceil(children / 2)")
    min_rooms_formula: Mapped[str | None] = mapped_column(String(64), nullable=True)

    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
