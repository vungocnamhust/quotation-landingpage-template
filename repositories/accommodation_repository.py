from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.accommodation import AccommodationProfile


class AccommodationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_profile(self, profile_id: str) -> AccommodationProfile | None:
        return await self.session.get(AccommodationProfile, profile_id)

    async def list_profiles(self, *, active_only: bool | None = True, search: str = "", destination_id: str | None = None, limit: int = 100) -> list[AccommodationProfile]:
        statement = select(AccommodationProfile).order_by(AccommodationProfile.name.asc(), AccommodationProfile.id.asc())
        if active_only is True:
            statement = statement.where(AccommodationProfile.is_active.is_(True))
        elif active_only is False:
            statement = statement.where(AccommodationProfile.is_active.is_(False))
        if destination_id:
            statement = statement.where(AccommodationProfile.destination_id == destination_id)
        if search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.where(or_(AccommodationProfile.name.ilike(pattern), AccommodationProfile.display_city.ilike(pattern)))
        result = await self.session.scalars(statement.limit(max(1, min(limit, 200))))
        return list(result.all())

    async def create_profile(self, **values: object) -> AccommodationProfile:
        profile = AccommodationProfile(**values)
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def update_profile(self, profile: AccommodationProfile, **values: object) -> AccommodationProfile:
        for key, value in values.items():
            setattr(profile, key, value)
        await self.session.flush()
        return profile

    async def set_status(self, profile: AccommodationProfile, *, is_active: bool) -> AccommodationProfile:
        profile.is_active = is_active
        await self.session.flush()
        return profile
