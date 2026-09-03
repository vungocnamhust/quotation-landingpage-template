import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

import main
from db.base import Base
from repositories.quotation_repository import QuotationRepository
from repositories.travel_designer_repository import TravelDesignerRepository


class WorkspaceOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.file.close()
        cls.engine = make_test_engine(f"sqlite+aiosqlite:///{cls.file.name}")
        cls.sessions = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._init())
        cls.session_patch = patch.object(main, "_get_db_session_factory", return_value=cls.sessions)
        cls.session_patch.start()
        cls.env_patch = patch.dict(os.environ, {"DMC_GATEWAY_ENABLED": "true"})
        cls.env_patch.start()
        cls.client = TestClient(main.app)

    @classmethod
    async def _init(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    @classmethod
    def tearDownClass(cls):
        cls.env_patch.stop()
        cls.session_patch.stop()
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.file.name)

    def setUp(self):
        asyncio.run(self._seed())

    async def _seed(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as session:
            designers = TravelDesignerRepository(session)
            first = await designers.create_profile(profile_id="td_first", email="first@example.com", name="First")
            second = await designers.create_profile(profile_id="td_second", email="second@example.com", name="Second")
            quotes = QuotationRepository(session)
            await quotes.create_quotation(quotation_id="quo_first", brand_id="brand", template_name="quote-generator", baseline_lang="en", title="First journey", customer_name="Client", designer_profile_id=first.id, created_by_profile_id=first.id)
            await quotes.create_quotation(quotation_id="quo_second", brand_id="brand", template_name="quote-generator", baseline_lang="en", title="Second journey", designer_profile_id=second.id, created_by_profile_id=second.id)
            await quotes.create_quotation(quotation_id="quo_shared", brand_id="brand", template_name="quote-generator", baseline_lang="en", title="Shared journey", designer_profile_id=second.id, created_by_profile_id=first.id)
            await quotes.create_quotation(quotation_id="quo_unassigned", brand_id="brand", template_name="quote-generator", baseline_lang="en", title="Unassigned")
            await session.commit()

    def test_list_and_overview_are_editor_accessible_after_reassignment_policy(self):
        headers = {"X-DMC-Email": "first@example.com"}
        listed = self.client.get("/api/v2/workspace/quotations", headers=headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual({item["id"] for item in listed.json()["items"]}, {"quo_first", "quo_second", "quo_shared", "quo_unassigned"})
        # Foreign quote returns 403 Forbidden
        self.assertEqual(self.client.get("/api/v2/workspace/quotations/quo_second/overview", headers=headers).status_code, 403)
        # Unassigned quote is accessible to authenticated staff
        self.assertEqual(self.client.get("/api/v2/workspace/quotations/quo_unassigned/overview", headers=headers).status_code, 200)

    def test_list_exposes_fail_closed_workflow_lane_and_keeps_cursor_contract(self):
        headers = {"X-DMC-Email": "first@example.com"}
        first = self.client.get("/api/v2/workspace/quotations?workflowLane=facts&limit=1", headers=headers)
        self.assertEqual(first.status_code, 200)
        payload = first.json()
        self.assertEqual(len(payload["items"]), 1)
        item = payload["items"][0]
        self.assertEqual(item["workflowLane"], "facts")
        self.assertEqual(item["workflow"], {
            "facts": {"ready": False},
            "content": {"ready": False},
            "design": {"ready": False},
            "review": {"ready": False},
        })
        self.assertEqual(item["commercial"], {
            "label": None,
            "currency": None,
            "groupTotalAmountMinor": None,
        })
        self.assertIsNotNone(payload["nextCursor"])

        second = self.client.get(
            f"/api/v2/workspace/quotations?workflowLane=facts&limit=1&cursor={payload['nextCursor']}",
            headers=headers,
        )
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(second.json()["items"][0]["id"], item["id"])
        legacy = self.client.get("/api/v2/workspace/quotations?status=draft", headers=headers)
        self.assertEqual(legacy.status_code, 200)
        self.assertTrue(all(row["status"] == "draft" for row in legacy.json()["items"]))

    def test_creator_and_assigned_designer_both_have_access(self):
        # First designer is the creator of quo_shared
        headers_first = {"X-DMC-Email": "first@example.com"}
        resp_first = self.client.get("/api/v2/workspace/quotations/quo_shared/overview", headers=headers_first)
        self.assertEqual(resp_first.status_code, 200)

        # Second designer is the assigned designer of quo_shared
        headers_second = {"X-DMC-Email": "second@example.com"}
        resp_second = self.client.get("/api/v2/workspace/quotations/quo_shared/overview", headers=headers_second)
        self.assertEqual(resp_second.status_code, 200)

    def test_admin_role_can_access_any_quotation(self):
        headers = {"X-DMC-Email": "admin@example.com", "X-DMC-Role": "quote_admin"}
        # Admin can access second designer's quotation
        resp = self.client.get("/api/v2/workspace/quotations/quo_second/overview", headers=headers)
        self.assertEqual(resp.status_code, 200)

    def test_local_bypass_can_access_any_quotation(self):
        with patch.dict(os.environ, {"DMC_GATEWAY_ENABLED": "false", "ENVIRONMENT": "local"}):
            # Local request without headers
            resp = self.client.get("/api/v2/workspace/quotations/quo_second/overview")
            self.assertEqual(resp.status_code, 200)

    def test_nonexistent_quotation_returns_404(self):
        headers = {"X-DMC-Email": "first@example.com"}
        resp = self.client.get("/api/v2/workspace/quotations/quo_nonexistent/overview", headers=headers)
        self.assertEqual(resp.status_code, 404)

    def test_missing_profile_is_forbidden(self):
        response = self.client.get("/api/v2/workspace/me", headers={"X-DMC-Email": "missing@example.com"})
        self.assertEqual(response.status_code, 403)
