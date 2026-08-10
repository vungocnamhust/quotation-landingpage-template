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

    def test_non_admin_editor_can_manage_travel_designers(self):
        env = {
            "ENVIRONMENT": "production",
            "QUOTE_AUTH_REQUIRED": "true",
            "DMC_GATEWAY_ENABLED": "true",
        }
        headers = {
            "X-DMC-Email": "editor@example.com",
            "X-DMC-Person-Id": "person-editor",
            "X-DMC-Role": "quotation_editor",  # Standard editor, NOT quote_admin
        }
        with patch.dict(os.environ, env, clear=False):
            # Create
            res_create = self.client.post(
                "/api/v2/travel-designers",
                json={"name": "Editor Created Designer", "email": "editor_td@example.com", "phone": "+84 123"},
                headers=headers,
            )
            self.assertEqual(res_create.status_code, 201)
            td_id = res_create.json()["id"]

            # Update
            res_update = self.client.put(
                f"/api/v2/travel-designers/{td_id}",
                json={"name": "Updated Designer Name", "email": "editor_td@example.com", "phone": "+84 999"},
                headers=headers,
            )
            self.assertEqual(res_update.status_code, 200)
            self.assertEqual(res_update.json()["name"], "Updated Designer Name")

            # Deactivate
            res_status = self.client.patch(
                f"/api/v2/travel-designers/{td_id}/status",
                json={"isActive": False},
                headers=headers,
            )
            self.assertEqual(res_status.status_code, 200)
            self.assertFalse(res_status.json()["isActive"])

            # List inactive designers
            res_list = self.client.get(
                "/api/v2/travel-designers?active=all",
                headers=headers,
            )
            self.assertEqual(res_list.status_code, 200)
            found_ids = [item["id"] for item in res_list.json()["items"]]
            self.assertIn(td_id, found_ids)

    def test_creator_and_assigned_designer_can_both_access_quotation(self):
        env = {
            "ENVIRONMENT": "production",
            "QUOTE_AUTH_REQUIRED": "true",
            "DMC_GATEWAY_ENABLED": "true",
        }
        headers_creator = {
            "X-DMC-Email": "creator@example.com",
            "X-DMC-Role": "quotation_editor",
        }
        headers_assigned = {
            "X-DMC-Email": "assigned@example.com",
            "X-DMC-Role": "quotation_editor",
        }
        headers_other = {
            "X-DMC-Email": "other@example.com",
            "X-DMC-Role": "quotation_editor",
        }
        with patch.dict(os.environ, env, clear=False), \
             patch("main._require_active_v2_brand", return_value=None), \
             patch("main._validate_selected_accommodations", return_value=None):
            # Create profiles for creator and assigned designer
            td_creator = self.client.post("/api/v2/travel-designers", json={"name": "Creator", "email": "creator@example.com"}, headers=headers_creator).json()
            td_assigned = self.client.post("/api/v2/travel-designers", json={"name": "Assigned", "email": "assigned@example.com"}, headers=headers_creator).json()
            self.client.post("/api/v2/travel-designers", json={"name": "Other", "email": "other@example.com"}, headers=headers_creator)

            # Creator creates a quote assigned to Assigned designer
            res_quote = self.client.post(
                "/api/v2/quotations",
                json={
                    "source": {"kind": "manual"},
                    "brand_id": "vietnam_safar",
                    "lang": "en",
                    "presentation_options": {"template_id": "quote-generator", "travel_designer_id": td_assigned["id"]},
                    "trip_facts": {
                        "start_date": "2026-10-01",
                        "end_date": "2026-10-01",
                        "itinerary": [{"day_number": 1, "destination": "Hanoi", "overnight": "Hanoi", "summary": "Arrival", "meals": ["Dinner"], "notes": ["Private arrival"]}],
                    },
                    "customer_facts": {"customer_name": "Dual Access Customer", "nationality": "British", "adults": 2},
                    "service_facts": {"hotels": [{"accommodation_id": "acc_test", "destination": "Hanoi", "name": "Test Hotel", "room_type": "Deluxe", "check_in": "2026-10-01", "check_out": "2026-10-01"}]},
                },
                headers=headers_creator,
            )
            self.assertEqual(res_quote.status_code, 200)
            quote_id = res_quote.json()["quotationId"]

            # 1. Creator can access facts
            res_creator_facts = self.client.get(f"/api/v2/quotations/{quote_id}/facts", headers=headers_creator)
            self.assertEqual(res_creator_facts.status_code, 200)

            # 2. Assigned designer can access facts
            res_assigned_facts = self.client.get(f"/api/v2/quotations/{quote_id}/facts", headers=headers_assigned)
            self.assertEqual(res_assigned_facts.status_code, 200)

            # 3. Third party cannot access (404)
            res_other_facts = self.client.get(f"/api/v2/quotations/{quote_id}/facts", headers=headers_other)
            self.assertEqual(res_other_facts.status_code, 404)

            # 4. Creator workspace listing includes the quote
            res_creator_ws = self.client.get("/api/v2/workspace/quotations", headers=headers_creator)
            self.assertEqual(res_creator_ws.status_code, 200)
            creator_quote_ids = [item["id"] for item in res_creator_ws.json()["items"]]
            self.assertIn(quote_id, creator_quote_ids)

            # 5. Assigned designer workspace listing includes the quote
            res_assigned_ws = self.client.get("/api/v2/workspace/quotations", headers=headers_assigned)
            self.assertEqual(res_assigned_ws.status_code, 200)
            assigned_quote_ids = [item["id"] for item in res_assigned_ws.json()["items"]]
            self.assertIn(quote_id, assigned_quote_ids)


