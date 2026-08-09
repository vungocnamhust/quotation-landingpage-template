import asyncio
import os
import tempfile
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from repositories.destination_repository import DestinationRepository
from repositories.media_library_repository import MediaLibraryRepository
from services.media_library_service import is_allowed_prefix, is_media_key


class MediaLibraryCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.sessions = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._init())

    @classmethod
    async def _init(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.db_file.name)

    def test_r2_prefix_and_image_filter_are_constrained(self):
        self.assertTrue(is_allowed_prefix("library/media/vietnam", ("library/media",)))
        self.assertFalse(is_allowed_prefix("published/quo_1", ("library/media",)))
        self.assertTrue(is_media_key("library/media/hanoi/hero.jpg"))
        self.assertFalse(is_media_key("published/quo_1/v1.html"))
        self.assertFalse(is_media_key("library/media/preview/hero.jpg"))

    def test_media_index_returns_direct_children_and_destination_alias_resolves(self):
        async def scenario():
            async with self.sessions() as session:
                media = MediaLibraryRepository(session)
                await media.create_sync_run(run_id="run_1", prefixes=["library/media"])
                self.assertEqual((await media.get_active_sync_run()).id, "run_1")
                await media.upsert_object(run_id="run_1", bucket="bucket", r2_key="library/media/vietnam/hanoi.jpg", parent_prefix="library/media/vietnam", file_name="hanoi.jpg", content_type="image/jpeg", size_bytes=10, etag="a", source_modified_at=None)
                await media.upsert_object(run_id="run_1", bucket="bucket", r2_key="library/media/laos/luang.jpg", parent_prefix="library/media/laos", file_name="luang.jpg", content_type="image/jpeg", size_bytes=10, etag="b", source_modified_at=None)
                await session.commit()
                self.assertEqual(await media.list_child_prefixes(prefix="library/media"), ["library/media/laos", "library/media/vietnam"])
                self.assertEqual((await media.list_children(prefix="library/media/vietnam"))[0].r2_key, "library/media/vietnam/hanoi.jpg")
                destinations = DestinationRepository(session)
                await destinations.upsert(destination_id="dst_hanoi", canonical_name="Hanoi", slug="ha-noi", aliases=["Ha Noi", "Hà Nội"])
                await session.commit()
                resolved = await destinations.resolve("ha noi")
                self.assertIsNotNone(resolved)
                self.assertEqual(resolved.canonical_name, "Hanoi")

        asyncio.run(scenario())
