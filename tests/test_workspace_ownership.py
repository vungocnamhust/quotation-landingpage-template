import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import main
from db.base import Base
from repositories.quotation_repository import QuotationRepository
from repositories.travel_designer_repository import TravelDesignerRepository


class WorkspaceOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.file.name}")
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
            await quotes.create_quotation(quotation_id="quo_first", brand_id="brand", template_name="quote-generator", baseline_lang="en", title="First journey", customer_name="Client", designer_profile_id=first.id)
            await quotes.create_quotation(quotation_id="quo_second", brand_id="brand", template_name="quote-generator", baseline_lang="en", title="Second journey", designer_profile_id=second.id)
            await quotes.create_quotation(quotation_id="quo_unassigned", brand_id="brand", template_name="quote-generator", baseline_lang="en", title="Unassigned")
            await session.commit()

    def test_list_and_overview_are_editor_accessible_after_reassignment_policy(self):
        headers = {"X-DMC-Email": "first@example.com"}
        listed = self.client.get("/api/v2/workspace/quotations", headers=headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual({item["id"] for item in listed.json()["items"]}, {"quo_first", "quo_second", "quo_unassigned"})
        self.assertEqual(self.client.get("/api/v2/workspace/quotations/quo_second/overview", headers=headers).status_code, 404)
        self.assertEqual(self.client.get("/api/v2/workspace/quotations/quo_unassigned/overview", headers=headers).status_code, 404)

    def test_missing_profile_is_forbidden(self):
        response = self.client.get("/api/v2/workspace/me", headers={"X-DMC-Email": "missing@example.com"})
        self.assertEqual(response.status_code, 403)
