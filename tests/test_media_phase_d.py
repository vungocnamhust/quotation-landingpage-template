import asyncio
import io
import os
import socket
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import main
from core.config import settings
from db.base import Base
from repositories import MediaRepository, QuotationRepository
from services.media_service import MediaService, build_preview_bytes, compute_sha256_bytes
from services.storage.local_media_storage import LocalMediaStorage
from services.storage.r2_storage import R2StorageConfigurationError


class FakeStorage:
    def __init__(self, bucket: str = "quotation-v2") -> None:
        self.bucket = bucket
        self.objects: dict[str, dict] = {}

    def upload_bytes(self, key: str, content: bytes, content_type: str) -> str:
        self.objects[key] = {"content": content, "content_type": content_type}
        return self.build_public_url(key)

    def upload_file(self, local_path: str, key: str, content_type: str) -> str:
        with open(local_path, "rb") as file_obj:
            return self.upload_bytes(key, file_obj.read(), content_type)

    def download_bytes(self, key: str) -> bytes:
        return self.objects[key]["content"]

    def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)

    def build_public_url(self, key: str) -> str:
        return f"https://cdn.test/{key}"

    def head_object(self, key: str) -> dict:
        item = self.objects[key]
        return {"ContentLength": len(item["content"]), "ContentType": item["content_type"]}


def _make_png_bytes(size=(1200, 800), color=(24, 99, 170)) -> bytes:
    output = io.BytesIO()
    image = Image.new("RGB", size, color)
    image.save(output, format="PNG")
    return output.getvalue()


def _make_rgba_png_bytes(size=(1800, 1200), color=(24, 99, 170, 160)) -> bytes:
    output = io.BytesIO()
    image = Image.new("RGBA", size, color)
    image.save(output, format="PNG")
    return output.getvalue()


class MediaPhaseDUnitTests(unittest.TestCase):
    def setUp(self):
        self.storage = FakeStorage()
        self.service = MediaService(
            storage=self.storage,
            preview_max_width=480,
            preview_max_height=320,
            preview_quality=82,
        )

    def test_prepare_upload_extracts_metadata_checksum_and_preview(self):
        content = _make_png_bytes(size=(1200, 800))

        prepared = asyncio.run(
            self.service.prepare_upload(
                content=content,
                declared_mime_type="image/png",
            )
        )

        self.assertEqual(prepared.mime_type, "image/png")
        self.assertEqual(prepared.extension, "png")
        self.assertEqual(prepared.width, 1200)
        self.assertEqual(prepared.height, 800)
        self.assertEqual(prepared.checksum_sha256, compute_sha256_bytes(content))
        self.assertTrue(prepared.preview_bytes)

        with Image.open(io.BytesIO(prepared.preview_bytes)) as preview:
            self.assertEqual(preview.format, "JPEG")
            self.assertLessEqual(preview.width, 480)
            self.assertLessEqual(preview.height, 320)

    def test_build_preview_bytes_generates_bounded_jpeg_from_rgba_source(self):
        content = _make_rgba_png_bytes(size=(1800, 1200))

        preview_bytes = build_preview_bytes(
            content,
            max_width=360,
            max_height=240,
            quality=75,
        )

        with Image.open(io.BytesIO(preview_bytes)) as preview:
            self.assertEqual(preview.format, "JPEG")
            self.assertEqual(preview.mode, "RGB")
            self.assertLessEqual(preview.width, 360)
            self.assertLessEqual(preview.height, 240)

    def test_build_storage_keys_generates_expected_r2_paths(self):
        quotation_keys = self.service.build_storage_keys(
            asset_id="med_123",
            extension="png",
            quotation_id="quo_abc",
        )
        shared_keys = self.service.build_storage_keys(
            asset_id="med_456",
            extension="webp",
            quotation_id=None,
        )

        self.assertEqual(
            quotation_keys,
            (
                "quotations/quo_abc/media/original/med_123.png",
                "quotations/quo_abc/media/preview/med_123.jpg",
            ),
        )
        self.assertEqual(
            shared_keys,
            (
                "shared/media/original/med_456.webp",
                "shared/media/preview/med_456.jpg",
            ),
        )

    def test_get_media_service_falls_back_to_local_storage_in_production_without_r2_config(self):
        original_service = main._media_service
        original_access_key = settings.r2_access_key_id
        original_secret_key = settings.r2_secret_access_key
        original_endpoint = settings.r2_endpoint
        original_account_id = settings.r2_account_id
        try:
            main._media_service = None
            object.__setattr__(settings, "r2_access_key_id", "")
            object.__setattr__(settings, "r2_secret_access_key", "")
            object.__setattr__(settings, "r2_endpoint", "")
            object.__setattr__(settings, "r2_account_id", "")
            with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):
                service = main._get_media_service()
            self.assertIsInstance(service.storage, LocalMediaStorage)
        finally:
            main._media_service = original_service
            object.__setattr__(settings, "r2_access_key_id", original_access_key)
            object.__setattr__(settings, "r2_secret_access_key", original_secret_key)
            object.__setattr__(settings, "r2_endpoint", original_endpoint)
            object.__setattr__(settings, "r2_account_id", original_account_id)

    def test_get_media_service_explicit_r2_backend_still_requires_full_r2_config(self):
        original_service = main._media_service
        original_access_key = settings.r2_access_key_id
        original_secret_key = settings.r2_secret_access_key
        original_endpoint = settings.r2_endpoint
        original_account_id = settings.r2_account_id
        try:
            main._media_service = None
            object.__setattr__(settings, "r2_access_key_id", "")
            object.__setattr__(settings, "r2_secret_access_key", "")
            object.__setattr__(settings, "r2_endpoint", "")
            object.__setattr__(settings, "r2_account_id", "")
            with patch.dict(os.environ, {"MEDIA_STORAGE_BACKEND": "r2"}, clear=False):
                with self.assertRaises(R2StorageConfigurationError):
                    main._get_media_service()
        finally:
            main._media_service = original_service
            object.__setattr__(settings, "r2_access_key_id", original_access_key)
            object.__setattr__(settings, "r2_secret_access_key", original_secret_key)
            object.__setattr__(settings, "r2_endpoint", original_endpoint)
            object.__setattr__(settings, "r2_account_id", original_account_id)


class MediaPhaseDRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._init_db())
        cls.storage = FakeStorage()
        cls.media_service = MediaService(storage=cls.storage)
        cls.session_patch = patch.object(main, "_get_db_session_factory", return_value=cls.session_factory)
        cls.media_service_patch = patch.object(main, "_get_media_service", return_value=cls.media_service)
        cls.session_patch.start()
        cls.media_service_patch.start()
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        cls.media_service_patch.stop()
        cls.session_patch.stop()
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.db_file.name)

    @classmethod
    async def _init_db(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    @classmethod
    async def _reset_db(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    @classmethod
    async def _seed_quotation(cls, quotation_id: str):
        async with cls.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            await quotation_repo.create_quotation(
                quotation_id=quotation_id,
                brand_id="vietnam_safar",
                template_name=main.BROCHURE_TEMPLATE_NAME,
                baseline_lang="en",
            )
            await session.commit()

    def setUp(self):
        asyncio.run(self._reset_db())
        self.storage.objects.clear()
        self.temp_sync_root = tempfile.mkdtemp(prefix="media-sync-")
        self.original_media_sync_dir = settings.media_sync_dir
        object.__setattr__(settings, "media_sync_dir", self.temp_sync_root)

    def tearDown(self):
        object.__setattr__(settings, "media_sync_dir", self.original_media_sync_dir)
        shutil.rmtree(self.temp_sync_root, ignore_errors=True)
        shutil.rmtree(os.path.join("published", "quo_media_fallback"), ignore_errors=True)

    def test_media_upload_persists_metadata_and_returns_urls(self):
        asyncio.run(self._seed_quotation("quo_media_upload"))

        response = self.client.post(
            "/api/v2/media/upload",
            files={"file": ("hero.png", _make_png_bytes(), "image/png")},
            data={"quotationId": "quo_media_upload"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["assetId"].startswith("med_"))
        self.assertEqual(payload["quotationId"], "quo_media_upload")
        self.assertEqual(payload["status"], "ready")
        self.assertTrue(payload["originalUrl"].startswith("https://cdn.test/quotations/quo_media_upload/media/original/"))
        self.assertTrue(payload["previewUrl"].startswith("https://cdn.test/quotations/quo_media_upload/media/preview/"))
        self.assertEqual(payload["width"], 1200)
        self.assertEqual(payload["height"], 800)
        self.assertEqual(len(self.storage.objects), 2)

        async def _assert_db():
            async with self.session_factory() as session:
                media_repo = MediaRepository(session)
                assets = await media_repo.list_media_assets(quotation_id="quo_media_upload")
                self.assertEqual(len(assets), 1)
                self.assertEqual(assets[0].mime_type, "image/png")
                self.assertEqual(assets[0].source_type, "editor_upload")

        asyncio.run(_assert_db())

    def test_media_upload_falls_back_to_draft_assets_when_db_is_unavailable_for_file_based_quote(self):
        class BrokenSessionFactory:
            def __call__(self):
                return self

            async def __aenter__(self):
                raise socket.gaierror(8, "nodename nor servname provided, or not known")

            async def __aexit__(self, exc_type, exc, tb):
                return False

        with patch.object(main, "_get_db_session_factory", return_value=BrokenSessionFactory()):
            with patch.object(main, "_load_ctx_data", return_value={"quotation_id": "quo_media_fallback"}):
                response = self.client.post(
                    "/api/v2/media/upload",
                    files={"file": ("hero.png", _make_png_bytes(), "image/png")},
                    data={"quotationId": "quo_media_fallback"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["quotationId"], "quo_media_fallback")
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["storageMode"], "draft_assets")
        self.assertTrue(payload["originalUrl"].startswith("/published/quo_media_fallback/draft_assets/"))
        self.assertEqual(payload["previewUrl"], payload["originalUrl"])
        self.assertEqual(payload["width"], 1200)
        self.assertEqual(payload["height"], 800)

    def test_media_upload_falls_back_to_draft_assets_when_db_dns_probe_returns_oserror_16(self):
        class BrokenSessionFactory:
            def __call__(self):
                return self

            async def __aenter__(self):
                raise OSError(16, "Device or resource busy")

            async def __aexit__(self, exc_type, exc, tb):
                return False

        with patch.object(main, "_get_db_session_factory", return_value=BrokenSessionFactory()):
            with patch.object(main, "_load_ctx_data", return_value={"quotation_id": "quo_media_fallback"}):
                response = self.client.post(
                    "/api/v2/media/upload",
                    files={"file": ("hero.png", _make_png_bytes(), "image/png")},
                    data={"quotationId": "quo_media_fallback"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["quotationId"], "quo_media_fallback")
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["storageMode"], "draft_assets")
        self.assertTrue(payload["originalUrl"].startswith("/published/quo_media_fallback/draft_assets/"))
        self.assertEqual(payload["previewUrl"], payload["originalUrl"])
        self.assertEqual(payload["width"], 1200)
        self.assertEqual(payload["height"], 800)

    def test_list_media_returns_paginated_inventory(self):
        asyncio.run(self._seed_quotation("quo_media_list"))

        for name in ("hero.png", "gallery.png"):
            response = self.client.post(
                "/api/v2/media/upload",
                files={"file": (name, _make_png_bytes(), "image/png")},
                data={"quotationId": "quo_media_list"},
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/v2/media", params={"quotationId": "quo_media_list", "pageSize": 1, "page": 1})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["pageSize"], 1)
        self.assertEqual(payload["total"], 2)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["quotationId"], "quo_media_list")

    def test_select_media_asset_creates_selection(self):
        asyncio.run(self._seed_quotation("quo_media_select"))
        upload_response = self.client.post(
            "/api/v2/media/upload",
            files={"file": ("cover.png", _make_png_bytes(), "image/png")},
            data={"quotationId": "quo_media_select"},
        )
        asset_id = upload_response.json()["assetId"]

        response = self.client.post(
            f"/api/v2/media/{asset_id}/select",
            json={
                "quotationId": "quo_media_select",
                "lang": "en",
                "sectionKey": "hero",
                "slotKey": "cover_image",
                "displayOrder": 0,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

        async def _assert_db():
            async with self.session_factory() as session:
                media_repo = MediaRepository(session)
                selections = await media_repo.list_media_selections(
                    quotation_id="quo_media_select",
                    lang="en",
                    section_key="hero",
                    slot_key="cover_image",
                )
                self.assertEqual(len(selections), 1)
                self.assertEqual(selections[0].asset_id, asset_id)

        asyncio.run(_assert_db())

    def test_select_media_asset_without_lang_uses_shared_selection_bucket(self):
        asyncio.run(self._seed_quotation("quo_media_shared"))
        upload_response = self.client.post(
            "/api/v2/media/upload",
            files={"file": ("cover.png", _make_png_bytes(), "image/png")},
            data={"quotationId": "quo_media_shared"},
        )
        asset_id = upload_response.json()["assetId"]

        response = self.client.post(
            f"/api/v2/media/{asset_id}/select",
            json={
                "quotationId": "quo_media_shared",
                "sectionKey": "hero",
                "slotKey": "cover_image",
                "displayOrder": 0,
            },
        )

        self.assertEqual(response.status_code, 200)

        async def _assert_db():
            async with self.session_factory() as session:
                media_repo = MediaRepository(session)
                selections = await media_repo.list_media_selections(
                    quotation_id="quo_media_shared",
                    lang="all",
                    section_key="hero",
                    slot_key="cover_image",
                )
                self.assertEqual(len(selections), 1)
                self.assertEqual(selections[0].asset_id, asset_id)
                self.assertEqual(selections[0].lang, "all")

        asyncio.run(_assert_db())

    def test_sync_media_folder_uploads_new_files_skips_duplicates_and_reports_failures(self):
        asyncio.run(self._seed_quotation("quo_media_sync"))
        sync_folder = os.path.join(self.temp_sync_root, "hanoi")
        os.makedirs(sync_folder, exist_ok=True)
        with open(os.path.join(sync_folder, "one.png"), "wb") as file_obj:
            file_obj.write(_make_png_bytes())
        with open(os.path.join(sync_folder, "two.png"), "wb") as file_obj:
            file_obj.write(_make_png_bytes())
        with open(os.path.join(sync_folder, "bad.txt"), "w", encoding="utf-8") as file_obj:
            file_obj.write("not an image")

        response = self.client.post(
            "/api/v2/media/sync",
            json={"folder": "hanoi", "recursive": True, "quotationId": "quo_media_sync"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["scanned"], 3)
        self.assertEqual(payload["uploaded"], 1)
        self.assertEqual(payload["skipped"], 1)
        self.assertEqual(payload["failed"], 1)
        self.assertEqual(len(self.storage.objects), 2)

        async def _assert_db():
            async with self.session_factory() as session:
                media_repo = MediaRepository(session)
                assets = await media_repo.list_media_assets(quotation_id="quo_media_sync")
                self.assertEqual(len(assets), 1)
                self.assertEqual(assets[0].source_type, "local_sync")
                self.assertTrue(assets[0].local_path.endswith("one.png") or assets[0].local_path.endswith("two.png"))

        asyncio.run(_assert_db())


if __name__ == "__main__":
    unittest.main()
