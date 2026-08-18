import asyncio
import os
import tempfile
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from repositories.accommodation_repository import AccommodationRepository
from repositories.destination_repository import DestinationRepository
from services.media_locations import accommodation_asset_location, accommodation_location


class AccommodationRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.file.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.file.name}")
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(self._create())

    def tearDown(self):
        asyncio.run(self.engine.dispose())
        os.unlink(self.file.name)

    async def _create(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.factory() as session:
            destination = await DestinationRepository(session).upsert(destination_id="dst_hanoi", canonical_name="Hanoi", slug="hanoi", aliases=["Hanoi"], country_slug="vietnam", region_slug="north", province_slug="hanoi")
            location = accommodation_location(destination, "Example Hotel", "hotel")
            await AccommodationRepository(session).create_profile(id="acc_example", destination_id=destination.id, storage_slug=location.accommodation_slug, asset_prefix=location.leaf_prefix, name="Example Hotel", room_type="Deluxe", intro="", phone="", display_city="Hanoi", display_date=None, hotel_asset=None, room_asset=None)
            await session.commit()

    def test_profile_uses_destination_taxonomy_prefix(self):
        async def assertion():
            async with self.factory() as session:
                profile = await AccommodationRepository(session).get_profile("acc_example")
                self.assertEqual(profile.asset_prefix, "accommodations/vietnam/north/hanoi/hanoi/example-hotel")
        asyncio.run(assertion())

    def test_deactivated_profile_is_not_returned_as_active(self):
        async def assertion():
            async with self.factory() as session:
                repository = AccommodationRepository(session)
                profile = await repository.get_profile("acc_example")
                await repository.set_status(profile, is_active=False)
                await session.commit()
                self.assertEqual(await repository.list_profiles(active_only=True), [])
        asyncio.run(assertion())

    def test_asset_category_uses_persisted_profile_root(self):
        location = accommodation_asset_location(
            asset_prefix="accommodations/vietnam/north/hanoi/hanoi/example-hotel",
            profile_id="acc_example",
            destination_id="dst_hanoi",
            accommodation_slug="example-hotel",
            asset_category="exteriors",
        )
        self.assertEqual(location.leaf_prefix, "accommodations/vietnam/north/hanoi/hanoi/example-hotel/exteriors")
        self.assertEqual(location.subject_id, "acc_example")
