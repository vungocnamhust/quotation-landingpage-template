import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

import db.session as db_session
import main
from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from repositories.quotation_repository import QuotationRepository
from repositories.quote_request_repository import QuoteRequestRepository


class ApplyPricingApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.database_file.close()
        cls.engine = make_test_engine(f"sqlite+aiosqlite:///{cls.database_file.name}")
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
            await main._seed_destination_catalog(session)
            session.add(
                Supplier(
                    id="sup_test",
                    name="Test Supplier",
                    name_normalized="test supplier",
                    supplier_type="direct",
                    default_currency="USD",
                )
            )
            await session.commit()

    async def _seed_quotation(self, quotation_id: str = "qtn_api_test") -> str:
        async with self.session_factory() as session:
            quotes = QuotationRepository(session)
            quotation = await quotes.create_quotation(
                quotation_id=quotation_id,
                brand_id="brand_capella",
                template_name="quote-generator",
                baseline_lang="en",
                source_kind="manual",
                status="draft",
                quotation_family_id=quotation_id,
                business_version=1,
            )
            request_json = {
                "source": {"kind": "manual"},
                "brand_id": "brand_capella",
                "lang": "en",
                "trip_facts": {
                    "start_date": "2026-10-01",
                    "end_date": "2026-10-05",
                    "duration_days": 5,
                    "duration_nights": 4,
                    "itinerary": [
                        {"day_number": 1, "title": "Arrival", "destination": "Hanoi"},
                    ],
                },
                "pricing_facts": {
                    "conditions": [],
                    "options": [
                        {
                            "id": "opt_std",
                            "label": "Standard Package",
                            "currency": "USD",
                            "per_traveler_amount_minor": 100000,
                            "group_total_amount_minor": 200000,
                            "per_adult_amount_minor": 100000,
                        }
                    ],
                },
                "customer_facts": {"customer_name": "Alice Wonderland", "adults": 2, "children": 0},
                "service_facts": {"hotels": [], "inclusions": [], "exclusions": []},
                "booking_facts": {"items": []},
                "presentation_options": {"theme_id": "brochure", "renderer": "quote-generator"},
            }
            await quotes.create_quotation_request(quotation_id=quotation.id, request_json=request_json)
            await quotes.create_version_facts(
                quotation_id=quotation.id,
                canonical_facts_json=request_json,
                resolved_facts_json={"factsHash": "before-apply"},
                facts_hash="before-apply",
                source_request_id=None,
                source_request_revision=None,
            )
            await main.QuotationDocumentRepository(session).save_current_document(
                quotation_id=quotation.id,
                lang="en",
                document_json={
                    "quotationId": quotation.id,
                    "revision": 1,
                    "trip": {"title": "Tour", "durationDays": 5, "durationNights": 4},
                    "pricingOptions": [
                        {
                            "id": "opt_std",
                            "label": "Standard Package",
                            "currency": "USD",
                            "groupTotalAmountMinor": 200000,
                            "perTravelerAmountMinor": 100000,
                            "perAdultAmountMinor": 100000,
                        }
                    ],
                    "pricingFacts": {
                        "options": [
                            {
                                "id": "opt_std",
                                "label": "Standard Package",
                                "currency": "USD",
                                "groupTotalAmountMinor": 200000,
                                "perTravelerAmountMinor": 100000,
                                "perAdultAmountMinor": 100000,
                            }
                        ]
                    },
                },
                expected_revision=0,
            )
            await session.commit()
            return quotation.id

    def test_apply_pricing_http_workflow_and_idempotency(self):
        quotation_id = asyncio.run(self._seed_quotation())

        # 1. Create costing sheet
        sheet_res = self.client.post("/api/v2/costing-sheets", json={"quotation_id": quotation_id, "currency": "USD"})
        self.assertEqual(sheet_res.status_code, 201)
        sheet_id = sheet_res.json()["id"]

        # 2. Add a line
        line_res = self.client.post(
            f"/api/v2/costing-sheets/{sheet_id}/lines",
            headers={"Idempotency-Key": "line_http_1"},
            json={
                "base_costing_revision": 0,
                "category": "accommodation",
                "title": "Boutique Hotel",
                "unit": "room",
                "time_basis": "night",
                "unit_cost_minor": 80000,
                "cost_currency": "USD",
                "qty_unit": 1,
                "qty_time": 2,
            },
        )
        self.assertEqual(line_res.status_code, 201)
        # Total cost = 160,000 minor ($1,600)

        # 3. Apply pricing to opt_std
        apply_res = self.client.post(
            f"/api/v2/costing-sheets/{sheet_id}/apply-pricing",
            headers={"Idempotency-Key": "idem_http_1"},
            json={
                "base_revision": 1,
                "base_costing_revision": 1,
                "target_option_id": "opt_std",
                "option_label": "Standard Package (Updated)",
            },
        )
        self.assertEqual(apply_res.status_code, 200)
        apply_data = apply_res.json()
        sell_total = apply_data["application"].get("sell_total_minor") or apply_data["application"].get("sellTotalMinor")
        facts_rev = apply_data.get("facts_revision") or apply_data.get("factsRevision")
        costing_rev = apply_data.get("costing_revision") or apply_data.get("costingRevision")
        self.assertEqual(sell_total, 160000)
        self.assertEqual(facts_rev, 2)
        self.assertEqual(costing_rev, 1)

        # 4. Idempotent replay
        replay_res = self.client.post(
            f"/api/v2/costing-sheets/{sheet_id}/apply-pricing",
            headers={"Idempotency-Key": "idem_http_1"},
            json={
                "base_revision": 1,
                "base_costing_revision": 1,
                "target_option_id": "opt_std",
            },
        )
        self.assertEqual(replay_res.status_code, 200)
        self.assertEqual(replay_res.json()["application"]["id"], apply_data["application"]["id"])

        # 5. Check GET workbench has applications and no drift
        wb_res = self.client.get(f"/api/v2/costing-sheets/{sheet_id}")
        self.assertEqual(wb_res.status_code, 200)
        wb_data = wb_res.json()
        self.assertEqual(len(wb_data["applications"]), 1)
        self.assertFalse(wb_data["drift"]["has_drift"])

    def test_apply_pricing_http_dual_cas_conflicts(self):
        quotation_id = asyncio.run(self._seed_quotation())

        sheet_res = self.client.post("/api/v2/costing-sheets", json={"quotation_id": quotation_id, "currency": "USD"})
        sheet_id = sheet_res.json()["id"]

        self.client.post(
            f"/api/v2/costing-sheets/{sheet_id}/lines",
            headers={"Idempotency-Key": "line_http_conflict"},
            json={
                "base_costing_revision": 0,
                "category": "accommodation",
                "title": "Hotel",
                "unit": "room",
                "time_basis": "night",
                "unit_cost_minor": 80000,
                "cost_currency": "USD",
            },
        )

        # Costing revision mismatch -> 409
        res1 = self.client.post(
            f"/api/v2/costing-sheets/{sheet_id}/apply-pricing",
            headers={"Idempotency-Key": "apply-conflict-costing"},
            json={
                "base_revision": 1,
                "base_costing_revision": 999,
                "target_option_id": "opt_std",
            },
        )
        self.assertEqual(res1.status_code, 409)

        # Facts revision mismatch -> 409
        res2 = self.client.post(
            f"/api/v2/costing-sheets/{sheet_id}/apply-pricing",
            headers={"Idempotency-Key": "apply-conflict-facts"},
            json={
                "base_revision": 999,
                "base_costing_revision": 1,
                "target_option_id": "opt_std",
            },
        )
        self.assertEqual(res2.status_code, 409)

    def test_apply_pricing_http_validation_gates(self):
        async def _create_req():
            async with self.session_factory() as session:
                req_repo = QuoteRequestRepository(session)
                qr = await req_repo.create_request(
                    role="customer", customer_name="Alice", email="alice@example.com", request_id="req_api_1"
                )
                await session.commit()
                return qr.id

        request_id = asyncio.run(_create_req())

        # Unattached sheet
        sheet_res = self.client.post("/api/v2/costing-sheets", json={"request_id": request_id, "currency": "USD"})
        sheet_id = sheet_res.json()["id"]

        res = self.client.post(
            f"/api/v2/costing-sheets/{sheet_id}/apply-pricing",
            headers={"Idempotency-Key": "apply-validation"},
            json={"base_revision": 1, "base_costing_revision": 0},
        )
        self.assertEqual(res.status_code, 422)

    def test_apply_pricing_requires_nonempty_idempotency_key(self):
        quotation_id = asyncio.run(self._seed_quotation())
        sheet = self.client.post("/api/v2/costing-sheets", json={"quotation_id": quotation_id, "currency": "USD"}).json()
        response = self.client.post(
            f"/api/v2/costing-sheets/{sheet['id']}/apply-pricing",
            json={"base_revision": 1, "base_costing_revision": 0, "target_option_id": "opt_std"},
        )
        self.assertEqual(response.status_code, 422, response.text)
