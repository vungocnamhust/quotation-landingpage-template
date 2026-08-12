from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.travel_style import TravelStyleTag


class TravelStyleRepository:
    """Repository layer for travel style tag queries and persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active_tags(self) -> Sequence[TravelStyleTag]:
        """Fetch all active travel style tags ordered by category and display_order."""
        stmt = (
            select(TravelStyleTag)
            .where(TravelStyleTag.is_active.is_(True))
            .order_by(TravelStyleTag.category.asc(), TravelStyleTag.display_order.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, tag_id: str) -> TravelStyleTag | None:
        """Get tag by ID."""
        return await self.session.get(TravelStyleTag, tag_id)
