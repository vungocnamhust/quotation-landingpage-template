import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import main
from db.base import Base
from repositories.quotation_repository import QuotationDocumentRepository, QuotationRepository
from repositories.travel_designer_repository import TravelDesignerRepository


class TravelDesignerAssignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._init_db())
        cls.session_patch = patch.object(main, "_get_db_session_factory", return_value=cls.session_factory)
        cls.session_patch.start()
        cls.client = TestClient(main.app)

    @classmethod
    async def _init_db(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    @classmethod
    def tearDownClass(cls):
        cls.session_patch.stop()
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.db_file.name)

    def setUp(self):
        asyncio.run(self._reset_db())

    async def _reset_db(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    def test_snapshot_preserves_editorial_copy_and_clear_only_removes_profile_values(self):
        document = {
            "designer": {
                "profileId": "td_old",
                "name": "Old designer",
                "email": "old@example.com",
                "phone": "000",
                "image": {"assetId": "med_old", "url": "old.jpg", "status": "ready"},
                "kicker": "Your Journey Designer",
                "quote": "A manual editorial note.",
                "experience": "15 years in Southeast Asia.",
            }
        }
        main._apply_travel_designer_snapshot(
            document,
            {
                "id": "td_new",
                "name": "New Designer",
                "email": "new@example.com",
                "phone": "+84 1",
                "imageAssetId": "med_new",
                "imageUrl": "new.jpg",
            },
        )
        self.assertEqual(document["designer"]["profileId"], "td_new")
        self.assertEqual(document["designer"]["image"]["assetId"], "med_new")
        self.assertEqual(document["designer"]["quote"], "A manual editorial note.")

        main._apply_travel_designer_snapshot(document, None)
        self.assertNotIn("profileId", document["designer"])
        self.assertNotIn("name", document["designer"])
        self.assertNotIn("image", document["designer"])
        self.assertEqual(document["designer"]["kicker"], "Your Journey Designer")
        self.assertEqual(document["designer"]["experience"], "15 years in Southeast Asia.")

    def test_quote_relationship_and_current_document_listing(self):
        async def scenario():
            async with self.session_factory() as session:
                designers = TravelDesignerRepository(session)
                profile = await designers.create_profile(
                    profile_id="td_assignment",
                    email="designer@example.com",
                    name="Designer",
                )
                quotations = QuotationRepository(session)
                quote = await quotations.create_quotation(
                    quotation_id="quo_assignment",
                    brand_id="capella",
                    template_name="vietnam_luxury_brosure.html",
                    baseline_lang="en",
                    designer_profile_id=profile.id,
                )
                documents = QuotationDocumentRepository(session)
                await documents.save_current_document(
                    quotation_id=quote.id,
                    lang="en",
                    document_json={"meta": {"quotationId": quote.id}},
                    expected_revision=0,
                )
                await documents.save_current_document(
                    quotation_id=quote.id,
                    lang="vi",
                    document_json={"meta": {"quotationId": quote.id}},
                    expected_revision=0,
                )
                await session.commit()

                self.assertEqual((await quotations.get_quotation_by_id(quote.id)).designer_profile_id, profile.id)
                self.assertEqual([item.lang for item in await documents.list_current_documents(quote.id)], ["en", "vi"])

        asyncio.run(scenario())

    def test_profile_crud_api_lists_active_profiles_and_soft_deactivates(self):
        created = self.client.post(
            "/api/v2/travel-designers",
            json={"name": "Workspace Designer", "email": "WORKSPACE@EXAMPLE.COM", "phone": "+84 9"},
        )
        self.assertEqual(created.status_code, 201)
        profile = created.json()
        self.assertEqual(profile["email"], "workspace@example.com")

        duplicate = self.client.post(
            "/api/v2/travel-designers",
            json={"name": "Duplicate", "email": " workspace@example.com "},
        )
        self.assertEqual(duplicate.status_code, 409)

        listed = self.client.get("/api/v2/travel-designers?active=true&search=workspace")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item["id"] for item in listed.json()["items"]], [profile["id"]])

        default = self.client.put(
            "/api/v2/brands/vietnam_safar/travel-designer-default",
            json={"designerProfileId": profile["id"]},
        )
        self.assertEqual(default.status_code, 200)

        disabled = self.client.patch(
            f"/api/v2/travel-designers/{profile['id']}/status",
            json={"isActive": False},
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.json()["isActive"])
        self.assertEqual(self.client.get("/api/v2/travel-designers?active=true").json()["items"], [])
