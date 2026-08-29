import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import db.session as db_session
import main
from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from repositories.quote_request_repository import QuoteRequestRepository
from repositories.quotation_repository import QuotationRepository


class CostingApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.database_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.database_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._create_schema())
        cls.session_patch = patch.object(db_session, "get_session_factory", return_value=cls.session_factory)
        cls.session_patch.start()
        cls.main_session_patch = patch.object(main, "_get_db_session_factory", return_value=cls.session_factory)
        cls.main_session_patch.start()
        cls.auth_patch = patch.dict(
            os.environ, {"DMC_GATEWAY_ENABLED": "false", "QUOTE_AUTH_REQUIRED": "false", "ENVIRONMENT": "local"}
        )
        cls.auth_patch.start()
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        cls.auth_patch.stop()
        cls.main_session_patch.stop()
        cls.session_patch.stop()
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.database_file.name)

    @classmethod
    async def _create_schema(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    def setUp(self):
        asyncio.run(self._reset_tables())

    async def _reset_tables(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        async with self.session_factory() as session:
            session.add(DestinationCatalog(id="dst_hanoi", canonical_name="Hanoi", slug="hanoi"))
            session.add(
                Supplier(
                    id="sup_la_siesta",
                    name="La Siesta Hotel Group",
                    name_normalized="la siesta hotel group",
                    supplier_type="direct",
                    default_currency="USD",
                )
            )
            await session.commit()
            await QuoteRequestRepository(session).create_request(
                role="customer", customer_name="Jane Doe", email="jane@example.com", request_id="req_api1"
            )
            await session.commit()
            await QuotationRepository(session).create_quotation(
                quotation_id="qtn_api1",
                brand_id="brand_capella",
                template_name="quote-generator",
                baseline_lang="en",
            )
            await session.commit()

    def _create_sheet(self, **overrides):
        payload = {"request_id": "req_api1", "currency": "USD"}
        payload.update(overrides)
        response = self.client.post("/api/v2/costing-sheets", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_create_and_find_sheet_by_request_id(self):
        sheet = self._create_sheet()
        response = self.client.get("/api/v2/costing-sheets", params={"requestId": "req_api1"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["sheet"]["id"], sheet["id"])

    def test_find_returns_empty_sheet_when_none_exists(self):
        response = self.client.get("/api/v2/costing-sheets", params={"requestId": "req_api1"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()["sheet"])

    def test_find_requires_exactly_one_query_param(self):
        response = self.client.get("/api/v2/costing-sheets")
        self.assertEqual(response.status_code, 422)
        response = self.client.get(
            "/api/v2/costing-sheets", params={"requestId": "req_api1", "quotationId": "qtn_api1"}
        )
        self.assertEqual(response.status_code, 422)

    def test_create_sheet_conflict_returns_409_envelope(self):
        self._create_sheet()
        response = self.client.post("/api/v2/costing-sheets", json={"request_id": "req_api1", "currency": "USD"})
        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body["error"]["code"], "REVISION_CONFLICT")

    def test_get_workbench_404_for_unknown_sheet(self):
        response = self.client.get("/api/v2/costing-sheets/cst_does_not_exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "RESOURCE_NOT_FOUND")

    def test_create_manual_line_and_settings_round_trip(self):
        sheet = self._create_sheet()
        response = self.client.post(
            f"/api/v2/costing-sheets/{sheet['id']}/lines",
            headers={"Idempotency-Key": "line-key-1"},
            json={
                "base_costing_revision": sheet["costing_revision"],
                "category": "visa",
                "title": "E-visa",
                "unit": "person",
                "time_basis": "trip",
                "unit_cost_minor": 250_000,
                "cost_currency": "USD",
                "qty_unit": 2,
                "qty_time": 1,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["summary"]["cost_total_minor"], 500_000)

        settings_response = self.client.put(
            f"/api/v2/costing-sheets/{sheet['id']}/settings",
            json={"base_costing_revision": body["sheet"]["costing_revision"], "markup_rate_bps": 1000},
        )
        self.assertEqual(settings_response.status_code, 200, settings_response.text)
        self.assertEqual(settings_response.json()["sheet"]["markup_rate_bps"], 1000)

    def test_stale_revision_returns_409(self):
        sheet = self._create_sheet()
        response = self.client.post(
            f"/api/v2/costing-sheets/{sheet['id']}/lines",
            headers={"Idempotency-Key": "line-key-2"},
            json={
                "base_costing_revision": sheet["costing_revision"] + 5,
                "category": "visa",
                "title": "E-visa",
                "unit": "person",
                "time_basis": "trip",
                "unit_cost_minor": 100,
                "cost_currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "REVISION_CONFLICT")

    def test_attach_quotation_flow(self):
        sheet = self._create_sheet()
        response = self.client.post(
            f"/api/v2/costing-sheets/{sheet['id']}/attach-quotation",
            headers={"Idempotency-Key": "attach-key-1"},
            json={"quotation_id": "qtn_api1"},
        )
        self.assertEqual(response.status_code, 422, response.text)  # source_request_id mismatch

        await_response = self.client.post(
            "/api/v2/costing-sheets", json={"quotation_id": "qtn_api1", "currency": "USD"}
        )
        self.assertEqual(await_response.status_code, 201, await_response.text)
        find_response = self.client.get("/api/v2/costing-sheets", params={"quotationId": "qtn_api1"})
        self.assertEqual(find_response.json()["sheet"]["quotation_id"], "qtn_api1")


class ApplyPricingResponseShapeTests(unittest.TestCase):
    def test_apply_pricing_response_serializes_snake_case(self):
        """Plan 16.3 F-15/D7: the wire shape is snake_case like every other costing response."""
        from datetime import datetime, timezone

        from schemas.v2.costing import (
            ApplyPricingResponseSchema,
            CostingApplicationResponseSchema,
            CostingSummarySchema,
        )

        payload = ApplyPricingResponseSchema(
            application=CostingApplicationResponseSchema(
                id="cga_1",
                sheet_id="cst_1",
                quotation_id="qtn_1",
                costing_revision_at_apply=2,
                facts_revision_after=5,
                target_option_id="opt-standard",
                sell_total_minor=1_200_000,
                currency="USD",
                cost_total_minor=1_000_000,
                margin_bps=1_667,
                created_at=datetime.now(timezone.utc),
            ),
            facts_revision=5,
            costing_revision=2,
            summary=CostingSummarySchema(
                cost_total_minor=1_000_000,
                sell_total_minor=1_200_000,
                margin_minor=200_000,
                margin_bps=1_667,
                by_day=[],
                by_category=[],
            ),
            pricing_options=[],
        ).model_dump(by_alias=True)

        self.assertIn("facts_revision", payload)
        self.assertIn("costing_revision", payload)
        self.assertIn("pricing_options", payload)
        self.assertNotIn("factsRevision", payload)
        self.assertNotIn("costingRevision", payload)
        self.assertNotIn("pricingOptions", payload)


if __name__ == "__main__":
    unittest.main()
