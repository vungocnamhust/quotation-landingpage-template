import asyncio
import os
import tempfile
import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from repositories.travel_designer_repository import TravelDesignerRepository


class TravelDesignerRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._init_db())

    @classmethod
    async def _init_db(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.db_file.name)

    def setUp(self):
        asyncio.run(self._reset_db())

    async def _reset_db(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    def test_email_mapping_is_normalized_and_inactive_profiles_are_excluded(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = TravelDesignerRepository(session)
                profile = await repository.create_profile(
                    profile_id="td_1",
                    email="  Sale@Example.com ",
                    name="Sale One",
                )
                await session.commit()
                self.assertEqual(profile.email, "sale@example.com")
                self.assertIsNotNone(await repository.get_active_by_email("SALE@EXAMPLE.COM"))
                profile.is_active = False
                await session.commit()
                self.assertIsNone(await repository.get_active_by_email("sale@example.com"))
                self.assertEqual(await repository.list_profiles(active_only=True), [])

        asyncio.run(scenario())

    def test_brand_default_requires_active_profile(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = TravelDesignerRepository(session)
                profile = await repository.create_profile(
                    profile_id="td_2",
                    email="designer@example.com",
                    name="Designer",
                )
                await repository.set_brand_default(brand_id="capella", profile_id=profile.id)
                await session.commit()
                default = await repository.get_brand_default("capella")
                self.assertEqual(default.id, profile.id)
                profile.is_active = False
                await session.commit()
                self.assertIsNone(await repository.get_brand_default("capella"))

        asyncio.run(scenario())
