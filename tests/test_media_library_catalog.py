import asyncio
import os
import tempfile
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from repositories.destination_repository import DestinationRepository
from repositories.media_library_repository import MediaLibraryRepository
from services.media_library_service import (
    MediaLibraryService,
    catalogue_metadata_for_key,
    is_allowed_prefix,
    is_media_key,
    province_slug_hint_for_key,
)
from services.storage.r2_storage import R2Storage


class FakeS3Client:
    def __init__(self, pages: list[dict]):
        self._pages = pages
        self.calls: list[dict] = []

    def list_objects_v2(self, **kwargs):
        self.calls.append(kwargs)
        return self._pages[len(self.calls) - 1]


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

    def test_catalogue_metadata_for_accommodation_key_uses_the_confirmed_grammar(self):
        metadata = catalogue_metadata_for_key("accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors/a.jpg")
        self.assertEqual(metadata, {"media_kind": "accommodation", "subject_type": "accommodation", "accommodation_slug": "metropole-hanoi", "accommodation_kind": "hotel"})
        # R4/R6: every key is a real MediaLibraryObject column — no asset_category
        # or province_slug (those aren't stored columns) can leak in here.
        self.assertNotIn("asset_category", metadata)
        self.assertNotIn("province_slug", metadata)
        self.assertNotIn("destination_id", metadata)

    def test_catalogue_metadata_for_destination_key_excludes_preview_subject(self):
        metadata = catalogue_metadata_for_key("shared/media/vietnam/north/ha-noi/hero.jpg")
        self.assertEqual(metadata["media_kind"], "destination")
        self.assertEqual(metadata["subject_id"], "ha-noi")

    def test_catalogue_metadata_for_team_key(self):
        metadata = catalogue_metadata_for_key("team/nam/avatar.jpg")
        self.assertEqual(metadata, {"media_kind": "team", "subject_type": "travel_designer", "subject_id": "nam"})

    def test_province_slug_hint_survives_a_preview_segment_shifting_the_tail(self):
        # R6: parse_accommodation_key uses root-relative offsets, so an
        # unexpected /preview/ segment before the filename can never shift
        # which segment is read as the province (dormant today only because
        # is_media_key already filters preview objects out upstream).
        self.assertEqual(
            province_slug_hint_for_key("accommodations/vietnam/north/ha-noi/metropole-hanoi/exteriors/preview/a.jpg"),
            "ha-noi",
        )

    def test_province_slug_hint_for_destination_key_excludes_preview(self):
        self.assertIsNone(province_slug_hint_for_key("shared/media/vietnam/north/preview/hero.jpg"))

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

    def test_r2_storage_list_objects_wraps_list_objects_v2(self):
        fake_client = FakeS3Client([{"Contents": [], "IsTruncated": False}])
        storage = R2Storage(bucket="bucket", endpoint="https://example.com", client=fake_client)

        response = storage.list_objects(prefix="library/media/", continuation_token=None)

        self.assertEqual(response, {"Contents": [], "IsTruncated": False})
        self.assertEqual(fake_client.calls, [{"Bucket": "bucket", "Prefix": "library/media/", "MaxKeys": 1000}])

    def test_r2_storage_list_objects_forwards_continuation_token_when_present(self):
        fake_client = FakeS3Client([{"Contents": [], "IsTruncated": False}])
        storage = R2Storage(bucket="bucket", endpoint="https://example.com", client=fake_client)

        storage.list_objects(prefix="library/media/", continuation_token="tok_1")

        self.assertEqual(fake_client.calls, [{"Bucket": "bucket", "Prefix": "library/media/", "MaxKeys": 1000, "ContinuationToken": "tok_1"}])

    def test_index_prefix_completes_a_paginated_sync_run_without_attributeerror(self):
        # Regression test: MediaLibraryService._index_prefix calls
        # self.storage.list_objects(...), which used to be missing from
        # R2Storage entirely and would raise AttributeError, marking every
        # real sync run "failed".
        fake_client = FakeS3Client(
            [
                {
                    "Contents": [{"Key": "library/media/vietnam/hanoi.jpg", "Size": 10, "ETag": '"a"'}],
                    "IsTruncated": True,
                    "NextContinuationToken": "tok_1",
                },
                {
                    "Contents": [{"Key": "library/media/laos/luang.jpg", "Size": 20, "ETag": '"b"'}],
                    "IsTruncated": False,
                },
            ]
        )
        storage = R2Storage(bucket="bucket", endpoint="https://example.com", client=fake_client)

        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite://")
            sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            try:
                async with engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)

                service = MediaLibraryService(storage=storage, session_factory=sessions)
                async with sessions() as session:
                    await MediaLibraryRepository(session).create_sync_run(run_id="run_paginated", prefixes=["library/media"])
                    await session.commit()

                await service._index_prefix("run_paginated", "library/media")

                async with sessions() as session:
                    run = await MediaLibraryRepository(session).get_sync_run("run_paginated")
                    self.assertEqual(run.scanned_count, 2)
                    self.assertEqual(run.indexed_count, 2)
                    children = await MediaLibraryRepository(session).list_children(prefix="library/media/vietnam")
                    self.assertEqual(children[0].r2_key, "library/media/vietnam/hanoi.jpg")
            finally:
                await engine.dispose()

        asyncio.run(scenario())
        self.assertEqual(len(fake_client.calls), 2)
        self.assertNotIn("ContinuationToken", fake_client.calls[0])
        self.assertEqual(fake_client.calls[1]["ContinuationToken"], "tok_1")
