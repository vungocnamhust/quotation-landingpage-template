from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.brand import Brand


class BrandRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, brand_id: str) -> Brand | None:
        return await self.session.get(Brand, brand_id)

    async def get_active(self, brand_id: str) -> Brand | None:
        return await self.session.scalar(select(Brand).where(Brand.id == brand_id, Brand.status == "active"))

    async def get_active_by_hostname(self, hostname: str) -> Brand | None:
        return await self.session.scalar(
            select(Brand).where(Brand.hostname == hostname.lower().rstrip("."), Brand.status == "active")
        )

    async def list_active(self) -> list[Brand]:
        result = await self.session.scalars(select(Brand).where(Brand.status == "active").order_by(Brand.display_name))
        return list(result.all())
