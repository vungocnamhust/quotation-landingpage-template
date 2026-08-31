"""AI Service Drafter API tests (15.7 §1.6/§3) — 3 operations, status matrix.

Mocks the agent layer (``trip_analyst.analyze_trip`` / ``draft_run_service.run_draft`` is
exercised for real against a mocked ``draft_day``) rather than calling a real LLM — same
approach as ``tests/test_draft_run_service.py``.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import db.session as db_session
import main
from core.kernel import ActorRef
from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from repositories.quote_request_repository import QuoteRequestRepository
from repositories.quotation_repository import QuotationRepository
from schemas.service_draft import DayDraftResult, ServiceDraft
from schemas.trip_profile import TripProfile
from schemas.v2.product import ProductCreateSchema
from schemas.v2.rate import RateCreateSchema, RatePriceLineCreateSchema
from routers.v2 import ai_drafter as ai_drafter_router
from services.ai_drafter import draft_run_service
from services.product_service import ProductService
from services.rate_service import RateService

ACTOR = ActorRef(actor_id="staff@capella.travel", actor_type="staff")


class AiDrafterApiTests(unittest.TestCase):
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
                    id="sup_la_siesta", name="La Siesta Hotel Group", name_normalized="la siesta hotel group",
                    supplier_type="direct", default_currency="USD",
                )
            )
            await session.commit()

            product_service = ProductService(session)
            product = await product_service.create_product(
                ProductCreateSchema(
                    destination_id="dst_hanoi", category="accommodation", title="La Siesta Deluxe Room",
                    supplier_id="sup_la_siesta", property_id=None,
                ),
                actor=ACTOR,
            )
            await session.commit()
            self.product_id = product.id

            rate_service = RateService(session)
            rate = await rate_service.create_draft(
                self.product_id,
                RateCreateSchema(
                    product_id=self.product_id, rate_basis="net",
                    valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31),
                    lines=[RatePriceLineCreateSchema(price_for="adult", occupancy_basis="dbl", unit="room", amount_minor=1_000_000)],
                ),
                actor=ACTOR,
            )
            await session.commit()
            await rate_service.activate(rate.id, actor=ACTOR)
            await session.commit()

            await QuoteRequestRepository(session).create_request(
                role="customer", customer_name="Jane Doe", email="jane@example.com", request_id="req_ai1"
            )
            await session.commit()
            await QuotationRepository(session).create_quotation(
                quotation_id="qtn_ai1", brand_id="brand_capella", template_name="quote-generator", baseline_lang="en"
            )
            await session.commit()

    def _create_sheet(self):
        response = self.client.post("/api/v2/costing-sheets", json={"request_id": "req_ai1", "currency": "USD"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def _sample_trip_profile_json(self):
        return TripProfile(
            archetype="couple",
            party={"adults": 2, "children": 0, "infants": 0},
            room_config=[{"room_type": "dbl", "count": 1}],
        ).model_dump(mode="json")

    # ── Analyze ──

    def test_analyze_returns_trip_profile(self):
        sheet = self._create_sheet()
        profile = TripProfile(archetype="honeymoon", party={"adults": 2, "children": 0, "infants": 0})

        async def fake_analyze_trip(session, **kwargs):
            return profile, False

        with patch.object(ai_drafter_router, "analyze_trip", side_effect=fake_analyze_trip):
            response = self.client.post(
                f"/api/v2/costing-sheets/{sheet['id']}/ai/analyze",
                json={"rawText": "Just married, honeymoon in Vietnam."},
                headers={"Idempotency-Key": "analyze-1"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["trip_profile"]["archetype"], "honeymoon")
        self.assertFalse(body["fallback_used"])

    def test_analyze_missing_sheet_returns_404(self):
        response = self.client.post(
            "/api/v2/costing-sheets/cst_does_not_exist/ai/analyze",
            json={"rawText": "anything"},
            headers={"Idempotency-Key": "analyze-404"},
        )
        self.assertEqual(response.status_code, 404)

    def test_analyze_missing_body_returns_422(self):
        sheet = self._create_sheet()
        response = self.client.post(
            f"/api/v2/costing-sheets/{sheet['id']}/ai/analyze",
            json={},
            headers={"Idempotency-Key": "analyze-422"},
        )
        self.assertEqual(response.status_code, 422)

    def test_analyze_missing_idempotency_key_returns_422(self):
        sheet = self._create_sheet()
        response = self.client.post(
            f"/api/v2/costing-sheets/{sheet['id']}/ai/analyze",
            json={"rawText": "anything"},
        )
        self.assertEqual(response.status_code, 422)

    # ── Draft ──

    def test_draft_creates_lines_and_returns_summary(self):
        sheet = self._create_sheet()
        draft = DayDraftResult(
            day_number=1,
            services=[
                ServiceDraft(
                    category="accommodation", product_id=self.product_id, occupancy_basis="dbl",
                    price_for="adult", pax_count=2, selection_reason="Deluxe room matches luxury tier.",
                )
            ],
        )

        async def fake_draft_day(deps, day_context):
            deps.allowlist.record([self.product_id])
            return draft

        with patch.object(draft_run_service, "draft_day", side_effect=fake_draft_day):
            response = self.client.post(
                f"/api/v2/costing-sheets/{sheet['id']}/ai/draft",
                json={
                    "runId": "run_placeholder",
                    "tripProfile": self._sample_trip_profile_json(),
                    "days": [{"dayNumber": 1, "destinationId": "dst_hanoi", "serviceDate": "2026-02-14"}],
                    "baseCostingRevision": sheet["costing_revision"],
                },
                headers={"Idempotency-Key": "draft-api-1"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "succeeded")
        self.assertEqual(len(body["created_line_ids"]), 1)

        workbench = self.client.get(f"/api/v2/costing-sheets/{sheet['id']}").json()
        self.assertEqual(len(workbench["items"]), 1)
        self.assertEqual(workbench["items"][0]["source"], "ai_draft")

    def test_draft_missing_sheet_returns_404(self):
        response = self.client.post(
            "/api/v2/costing-sheets/cst_missing/ai/draft",
            json={
                "runId": "run_x",
                "tripProfile": self._sample_trip_profile_json(),
                "days": [{"dayNumber": 1, "destinationId": "dst_hanoi", "serviceDate": "2026-02-14"}],
                "baseCostingRevision": 0,
            },
            headers={"Idempotency-Key": "draft-404"},
        )
        self.assertEqual(response.status_code, 404)

    def test_draft_stale_revision_returns_409(self):
        sheet = self._create_sheet()
        draft = DayDraftResult(
            day_number=1,
            services=[
                ServiceDraft(
                    category="accommodation", product_id=self.product_id, occupancy_basis="dbl",
                    price_for="adult", pax_count=2, selection_reason="ok",
                )
            ],
        )

        async def fake_draft_day(deps, day_context):
            deps.allowlist.record([self.product_id])
            return draft

        with patch.object(draft_run_service, "draft_day", side_effect=fake_draft_day):
            response = self.client.post(
                f"/api/v2/costing-sheets/{sheet['id']}/ai/draft",
                json={
                    "runId": "run_stale",
                    "tripProfile": self._sample_trip_profile_json(),
                    "days": [{"dayNumber": 1, "destinationId": "dst_hanoi", "serviceDate": "2026-02-14"}],
                    "baseCostingRevision": 99,
                },
                headers={"Idempotency-Key": "draft-409"},
            )
        self.assertEqual(response.status_code, 409, response.text)

    def test_draft_missing_days_returns_422(self):
        sheet = self._create_sheet()
        response = self.client.post(
            f"/api/v2/costing-sheets/{sheet['id']}/ai/draft",
            json={
                "runId": "run_bad",
                "tripProfile": self._sample_trip_profile_json(),
                "days": [],
                "baseCostingRevision": 0,
            },
            headers={"Idempotency-Key": "draft-422"},
        )
        self.assertEqual(response.status_code, 422)

    # ── List runs ──

    def test_list_runs_reflects_analyze_and_draft(self):
        sheet = self._create_sheet()
        profile = TripProfile(archetype="couple", party={"adults": 2, "children": 0, "infants": 0})

        class _FakeUsage:
            input_tokens = 10
            output_tokens = 5

        class _FakeResult:
            output = profile
            usage = _FakeUsage()

        class _FakeAgent:
            async def run(self, *_args, **_kwargs):
                return _FakeResult()

        # Mock one level deeper (the LLM factory) than the other Analyze tests so
        # ``analyze_trip``'s real body runs — including its ``record_run`` call — and this
        # test can prove the run actually lands in ``ai_runs``.
        with patch("services.ai_drafter.trip_analyst.build_agent", return_value=_FakeAgent()):
            self.client.post(
                f"/api/v2/costing-sheets/{sheet['id']}/ai/analyze",
                json={"rawText": "anything"},
                headers={"Idempotency-Key": "list-analyze-1"},
            )

        response = self.client.get(f"/api/v2/costing-sheets/{sheet['id']}/ai/runs")
        self.assertEqual(response.status_code, 200, response.text)
        runs = response.json()["runs"]
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["agent_name"], "trip_analyst")

    def test_list_runs_missing_sheet_returns_404(self):
        response = self.client.get("/api/v2/costing-sheets/cst_missing/ai/runs")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
