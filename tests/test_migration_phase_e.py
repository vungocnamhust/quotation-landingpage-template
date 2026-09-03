import asyncio
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

import main
from db.base import Base
from db.models.brand import Brand
from quote_document import build_default_sections
from repositories import MediaRepository, PublicationRepository, QuotationDocumentRepository, QuotationRepository
from repositories.travel_designer_repository import TravelDesignerRepository
from scripts.migrate_media_to_r2 import migrate_media_to_r2
from scripts.migrate_quotation_v2_to_postgres import migrate_quotation_v2_to_postgres


def _sample_document(quotation_id: str) -> dict:
    return {
        "meta": {
            "quotationId": quotation_id,
            "lang": "en",
            "brandId": "vietnam_safar",
            "template": main.BROCHURE_TEMPLATE_NAME,
        },
        "trip": {
            "title": "Migrated Journey",
            "lede": "A restored brochure draft.",
        },
        "assets": {
            "hero": {"url": "/assets/vietnam-safar-logo.png", "status": "ready"},
        },
        "narrative": {
            "letterIntro": "Welcome back to the canonical document.",
        },
        "route": {"staySegments": []},
        "itinerary": {"days": []},
        "stays": {"hotels": []},
        "pricing": {"options": []},
        "inclusions": [],
        "exclusions": [],
        "bookingTerms": {"items": []},
        "designer": {"name": "Vietnam Safar"},
        "layout": {"sections": [section.model_dump(mode="json") for section in build_default_sections()]},
    }


def _png_bytes(color: str) -> bytes:
    temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    temp.close()
    try:
        image = Image.new("RGB", (8, 8), color=color)
        image.save(temp.name, format="PNG")
        return Path(temp.name).read_bytes()
    finally:
        os.unlink(temp.name)


class FakeStorage:
    def __init__(self):
        self.bucket = "quotation-v2"
        self.objects: dict[str, bytes] = {}

    def upload_bytes(self, key: str, content: bytes, content_type: str) -> str:
        self.objects[key] = bytes(content)
        return self.build_public_url(key)

    def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)

    def build_public_url(self, key: str) -> str:
        return f"https://cdn.example.test/{key}"


class PhaseEMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = make_test_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._init_db())
        cls.session_patch = patch.object(main, "_get_db_session_factory", return_value=cls.session_factory)
        cls.session_patch.start()
        cls.env_patch = patch.dict(os.environ, {"DMC_GATEWAY_ENABLED": "true"})
        cls.env_patch.start()
        cls.client = TestClient(main.app, headers={"X-DMC-Email": "editor@test.com"})

    @classmethod
    def tearDownClass(cls):
        cls.env_patch.stop()
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
        sample_profile = {
            "palette": {
                "canvas": "#ffffff",
                "paper": "#f8fafc",
                "ink": "#0f172a",
                "mutedInk": "#64748b",
                "accent": "#0369a1",
                "accentAlt": "#0369a1",
                "contrast": "#0f172a",
                "onContrast": "#ffffff",
                "focus": "#0369a1",
            },
            "radii": {
                "card": "12px",
                "button": "8px",
                "frame": "16px",
                "pill": "9999px",
            },
            "themeId": "brochure",
            "layoutVersion": 1,
        }
        async with cls.session_factory() as session:
            session.add(Brand(id="vietnam_safar", display_name="Vietnam Safar", hostname="safar.test", status="active", render_profile=sample_profile))
            session.add(Brand(id="vietnam_safari", display_name="Vietnam Safari", hostname="safari.test", status="active", render_profile=sample_profile))
            await TravelDesignerRepository(session).create_profile(
                profile_id="td_test",
                email="editor@test.com",
                name="Test Editor",
            )
            await session.commit()

    def setUp(self):
        asyncio.run(self._reset_db())
        self.published_root = Path(tempfile.mkdtemp(prefix="phase-e-published-"))

    def tearDown(self):
        shutil.rmtree(self.published_root)

    def test_migrate_quotation_v2_to_postgres_creates_canonical_rows_and_uploads_publications(self):
        quotation_dir = self.published_root / "quo_migrate"
        quotation_dir.mkdir(parents=True)
        (quotation_dir / "ctx.json").write_text(
            json.dumps(
                {
                    "baseline_lang": "en",
                    "template_name": main.BROCHURE_TEMPLATE_NAME,
                    "opportunity_id": "OPP-MIGRATE",
                    "customer_name": "Alex Traveler",
                    "brand": {"id": "vietnam_safar"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (quotation_dir / "document.json").write_text(
            json.dumps(_sample_document("quo_migrate"), ensure_ascii=False),
            encoding="utf-8",
        )
        (quotation_dir / "create_request_v2.json").write_text(
            json.dumps(
                {
                    "brand_id": "vietnam_safar",
                    "opportunity_id": "OPP-MIGRATE",
                    "trip_facts": {"title": "Migrated Journey"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (quotation_dir / "v1.html").write_text("<html><body>v1</body></html>", encoding="utf-8")
        (quotation_dir / "v2_en.html").write_text("<html><body>v2</body></html>", encoding="utf-8")
        (quotation_dir / "pdf.html").write_text("<html><body>pdf v1</body></html>", encoding="utf-8")
        (quotation_dir / "pdf_en.html").write_text("<html><body>pdf en</body></html>", encoding="utf-8")

        storage = FakeStorage()
        summary = asyncio.run(
            migrate_quotation_v2_to_postgres(
                published_root=self.published_root,
                session_factory=self.session_factory,
                upload_publications=True,
                storage=storage,
            )
        )

        self.assertEqual(summary["migrated"], 1)
        self.assertEqual(summary["publicationsCreated"], 2)
        self.assertIn("quotations/quo_migrate/publish/en/v1.html", storage.objects)
        self.assertIn("quotations/quo_migrate/publish/en/v2.html", storage.objects)
        self.assertIn("quotations/quo_migrate/publish/en/v1.pdf", storage.objects)
        self.assertIn("quotations/quo_migrate/publish/en/v2.pdf", storage.objects)

        async def _assert_db():
            async with self.session_factory() as session:
                quotation_repo = QuotationRepository(session)
                document_repo = QuotationDocumentRepository(session)
                publication_repo = PublicationRepository(session)
                quotation = await quotation_repo.get_quotation_by_id("quo_migrate")
                document = await document_repo.get_current_document("quo_migrate", "en")
                revisions = await document_repo.list_document_revisions("quo_migrate", lang="en")
                publications = await publication_repo.list_publications("quo_migrate", lang="en")
                request_snapshot = await quotation_repo.get_latest_quotation_request("quo_migrate")

                self.assertIsNotNone(quotation)
                self.assertEqual(quotation.current_revision, 1)
                self.assertEqual(quotation.current_version, 2)
                self.assertEqual(document.document_json["trip"]["title"], "Migrated Journey")
                self.assertEqual(revisions[0].change_source, "migration")
                self.assertEqual(len(publications), 2)
                self.assertTrue(all(item.pdf_r2_key for item in publications))
                self.assertTrue(all(item.pdf_url for item in publications))
                quotation.designer_profile_id = "td_test"
                quotation.template_name = main.V2_RENDERER_NAME
                quotation.brand_id = "vietnam_safari"
                await session.commit()

        asyncio.run(_assert_db())

        response = self.client.get("/api/v2/quotations/quo_migrate/document")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["document"]["trip"]["title"], "Migrated Journey")
        self.assertEqual(response.json()["currentRevision"], 1)

    def test_migrate_quotation_v2_to_postgres_skips_directories_without_document_json(self):
        quotation_dir = self.published_root / "quo_missing_doc"
        quotation_dir.mkdir(parents=True)
        (quotation_dir / "ctx.json").write_text(json.dumps({"baseline_lang": "en"}), encoding="utf-8")

        summary = asyncio.run(
            migrate_quotation_v2_to_postgres(
                published_root=self.published_root,
                session_factory=self.session_factory,
            )
        )

        self.assertEqual(summary["skippedNoDocument"], 1)
        self.assertEqual(summary["items"][0]["status"], "skipped_no_document")

    def test_migrate_quotation_v2_to_postgres_builds_multilingual_documents_from_ctx_only_fixture(self):
        fixture_id = "quo_3e9bcd4f2f85"
        fixture_root = Path("published") / fixture_id
        quotation_dir = self.published_root / fixture_id
        quotation_dir.mkdir(parents=True)
        for filename in ["ctx.json", "payload.json", "v27.html", "v28_en.html", "v21_vi.html", "pdf.html", "pdf_en.html", "pdf_vi.html"]:
            shutil.copyfile(fixture_root / filename, quotation_dir / filename)

        storage = FakeStorage()
        with patch.object(main, "_load_quotation_manual_override", return_value={}):
            summary = asyncio.run(
                migrate_quotation_v2_to_postgres(
                    published_root=self.published_root,
                    session_factory=self.session_factory,
                    upload_publications=True,
                    storage=storage,
                )
            )

        self.assertEqual(summary["migrated"], 1)
        self.assertEqual(summary["items"][0]["availableLangs"], ["ar", "vi", "en"])
        self.assertEqual(summary["items"][0]["documentsCreated"], 3)
        self.assertEqual(summary["publicationsCreated"], 3)
        self.assertIn("quotations/quo_3e9bcd4f2f85/publish/ar/v27.html", storage.objects)
        self.assertIn("quotations/quo_3e9bcd4f2f85/publish/ar/v27.pdf", storage.objects)
        self.assertIn("quotations/quo_3e9bcd4f2f85/publish/en/v28.html", storage.objects)
        self.assertIn("quotations/quo_3e9bcd4f2f85/publish/en/v28.pdf", storage.objects)
        self.assertIn("quotations/quo_3e9bcd4f2f85/publish/vi/v21.html", storage.objects)
        self.assertIn("quotations/quo_3e9bcd4f2f85/publish/vi/v21.pdf", storage.objects)

        expected_sync = json.loads((fixture_root / "ctx.json").read_text(encoding="utf-8"))["html_sync"]

        async def _assert_db():
            async with self.session_factory() as session:
                quotation_repo = QuotationRepository(session)
                document_repo = QuotationDocumentRepository(session)
                publication_repo = PublicationRepository(session)
                quotation = await quotation_repo.get_quotation_by_id(fixture_id)
                ar_document = await document_repo.get_current_document(fixture_id, "ar")
                en_document = await document_repo.get_current_document(fixture_id, "en")
                vi_document = await document_repo.get_current_document(fixture_id, "vi")
                self.assertIsNotNone(quotation)
                self.assertEqual(quotation.baseline_lang, "ar")
                self.assertEqual(quotation.current_version, 28)
                self.assertEqual(ar_document.html_sync, expected_sync["ar"])
                self.assertEqual(en_document.html_sync, expected_sync["en"])
                self.assertEqual(vi_document.html_sync, expected_sync["vi"])
                self.assertEqual(ar_document.document_json["meta"]["lang"], "ar")
                self.assertEqual(en_document.document_json["meta"]["lang"], "en")
                self.assertEqual(vi_document.document_json["meta"]["lang"], "vi")
                self.assertNotEqual(ar_document.document_json["trip"]["title"], en_document.document_json["trip"]["title"])
                self.assertNotEqual(en_document.document_json["trip"]["title"], vi_document.document_json["trip"]["title"])
                self.assertEqual(en_document.document_json["meta"]["version"], 28)
                self.assertEqual(vi_document.document_json["meta"]["version"], 21)
                publications = await publication_repo.list_publications(fixture_id)
                self.assertEqual(len(publications), 3)
                self.assertTrue(all(item.pdf_r2_key for item in publications))
                self.assertTrue(all(item.pdf_url for item in publications))
                quotation.designer_profile_id = "td_test"
                quotation.template_name = main.V2_RENDERER_NAME
                quotation.brand_id = "vietnam_safari"
                await session.commit()

        asyncio.run(_assert_db())

        for lang in ["ar", "en", "vi"]:
            response = self.client.get(f"/api/v2/quotations/{fixture_id}/document?lang={lang}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["lang"], lang)
            self.assertEqual(response.json()["document"]["meta"]["lang"], lang)

    def test_migrate_media_to_r2_uploads_draft_assets_and_dedupes_by_checksum(self):
        quotation_dir = self.published_root / "quo_media"
        draft_assets_dir = quotation_dir / "draft_assets"
        draft_assets_dir.mkdir(parents=True)
        image_bytes = _png_bytes("red")
        (draft_assets_dir / "cover-1.png").write_bytes(image_bytes)
        (draft_assets_dir / "cover-duplicate.png").write_bytes(image_bytes)

        async def _seed_quotation():
            async with self.session_factory() as session:
                repo = QuotationRepository(session)
                await repo.create_quotation(
                    quotation_id="quo_media",
                    brand_id="vietnam_safar",
                    template_name=main.BROCHURE_TEMPLATE_NAME,
                    baseline_lang="en",
                )
                await session.commit()

        asyncio.run(_seed_quotation())

        storage = FakeStorage()
        summary = asyncio.run(
            migrate_media_to_r2(
                published_root=self.published_root,
                session_factory=self.session_factory,
                storage=storage,
            )
        )

        self.assertEqual(summary["uploaded"], 1)
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(len(storage.objects), 2)

        async def _assert_media():
            async with self.session_factory() as session:
                repo = MediaRepository(session)
                assets = await repo.list_media_assets(quotation_id="quo_media", page_size=10)
                self.assertEqual(len(assets), 1)
                self.assertEqual(assets[0].source_type, "migration_draft_asset")
                self.assertTrue(assets[0].local_path.endswith("cover-duplicate.png") or assets[0].local_path.endswith("cover-1.png"))

        asyncio.run(_assert_media())


if __name__ == "__main__":
    unittest.main()
