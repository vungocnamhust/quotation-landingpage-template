import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

import db.session as db_session
import main
from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from repositories.quote_request_repository import QuoteRequestRepository
from repositories.quotation_repository import QuotationRepository

CANCELLATION_POLICY = {
    "tiers": [
        {"days_before_service_min": 14, "penalty_percent": 25},
        {"days_before_service_min": 0, "penalty_percent": 100},
    ],
    "no_show_penalty_percent": 100,
}
PAYMENT_TERMS = {"balance_due_days_before_service": 10, "deposit_due_days_after_confirm": 3}
BOOKING_FIXTURE_FACTS = {
    "source": {"kind": "manual"},
    "brand_id": "brand_capella",
    "lang": "en",
    "trip_facts": {
        "start_date": "2026-07-15",
        "end_date": "2026-07-20",
        "duration_days": 6,
        "duration_nights": 5,
        "itinerary": [],
    },
    "customer_facts": {"customer_name": "Jane Doe", "adults": 2, "children": 0},
    "pricing_facts": {"conditions": [], "options": []},
    "service_facts": {"hotels": [], "inclusions": [], "exclusions": []},
    "booking_facts": {"items": []},
    "presentation_options": {"theme_id": "brochure", "renderer": "quote-generator"},
}
BOOKING_FIXTURE_RESOLVED_FACTS = {"partyLabel": "Jane Doe", "factsHash": "booking-api-fixture-v1"}


class BookingApiTests(unittest.TestCase):
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
            session.add(DestinationCatalog(id="dst_hanoi", canonical_name="Hanoi", slug="hanoi"))
            session.add(
                Supplier(
                    id="sup_la_siesta",
                    name="La Siesta Hotel Group",
                    name_normalized="la siesta hotel group",
                    supplier_type="direct",
                    default_currency="USD",
                    payment_terms_json=PAYMENT_TERMS,
                    cancellation_policy_json=CANCELLATION_POLICY,
                )
            )
            await session.commit()
            await QuoteRequestRepository(session).create_request(
                role="customer", customer_name="Jane Doe", email="jane@example.com", request_id="req_bkapi1"
            )
            await session.commit()
            quotation_repository = QuotationRepository(session)
            quotation = await quotation_repository.create_quotation(
                quotation_id="qtn_bkapi1",
                brand_id="brand_capella",
                template_name="quote-generator",
                baseline_lang="en",
                source_kind="manual",
                status="draft",
                quotation_family_id="qtn_bkapi1",
                business_version=1,
            )
            await quotation_repository.create_quotation_request(
                quotation_id=quotation.id, request_json=BOOKING_FIXTURE_FACTS
            )
            await quotation_repository.create_version_facts(
                quotation_id=quotation.id,
                canonical_facts_json=BOOKING_FIXTURE_FACTS,
                resolved_facts_json=BOOKING_FIXTURE_RESOLVED_FACTS,
                facts_hash="booking-api-fixture-v1",
                source_request_id=None,
                source_request_revision=None,
            )
            await session.commit()

    def _create_sheet_with_line(self):
        sheet = self.client.post(
            "/api/v2/costing-sheets", json={"quotation_id": "qtn_bkapi1", "currency": "USD"}
        ).json()
        line_payload = {
            "base_costing_revision": sheet["costing_revision"],
            "day_number": 1,
            "service_date": "2026-07-15",
            "category": "accommodation",
            "title": "La Siesta — Deluxe Room",
            "supplier_id": "sup_la_siesta",
            "unit": "room",
            "time_basis": "night",
            "unit_cost_minor": 1_000_000,
            "cost_currency": "USD",
            "qty_unit": 2,
            "qty_time": 1,
        }
        response = self.client.post(
            f"/api/v2/costing-sheets/{sheet['id']}/lines", json=line_payload, headers={"Idempotency-Key": "line-api-1"}
        )
        self.assertEqual(response.status_code, 201, response.text)
        return sheet["id"]

    def _create_booking(self, idempotency_key="create-api-1"):
        response = self.client.post(
            "/api/v2/bookings",
            json={"quotation_id": "qtn_bkapi1", "deposit_received_at": "2026-06-01"},
            headers={"Idempotency-Key": idempotency_key},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_create_booking_snapshots_lines_and_appears_on_board(self):
        self._create_sheet_with_line()
        detail = self._create_booking()
        self.assertTrue(detail["booking"]["booking_code"].startswith("BK-"))
        self.assertEqual(len(detail["lines"]), 1)
        self.assertEqual(detail["lines"][0]["status"], "to_request")

        board = self.client.get("/api/v2/bookings", params={"quotationId": "qtn_bkapi1"})
        self.assertEqual(board.status_code, 200, board.text)
        self.assertEqual(len(board.json()["items"]), 1)

    def test_get_booking_404_for_unknown_id(self):
        response = self.client.get("/api/v2/bookings/bkg_does_not_exist")
        self.assertEqual(response.status_code, 404)

    def test_second_booking_for_same_quotation_is_409(self):
        self._create_sheet_with_line()
        self._create_booking(idempotency_key="dup-a")
        response = self.client.post(
            "/api/v2/bookings",
            json={"quotation_id": "qtn_bkapi1", "deposit_received_at": "2026-06-02"},
            headers={"Idempotency-Key": "dup-b"},
        )
        self.assertEqual(response.status_code, 409, response.text)

    def test_full_operator_flow_transition_confirm_and_cancel_line(self):
        self._create_sheet_with_line()
        detail = self._create_booking()
        booking_id = detail["booking"]["id"]
        line_id = detail["lines"][0]["id"]

        requested = self.client.post(
            f"/api/v2/bookings/{booking_id}/lines/{line_id}/transition",
            json={"base_booking_revision": detail["booking"]["booking_revision"], "to": "requested"},
            headers={"Idempotency-Key": "tr-1"},
        )
        self.assertEqual(requested.status_code, 200, requested.text)

        confirmed = self.client.post(
            f"/api/v2/bookings/{booking_id}/lines/{line_id}/transition",
            json={
                "base_booking_revision": requested.json()["booking"]["booking_revision"],
                "to": "confirmed",
                "supplier_ref": "CONF-987",
            },
            headers={"Idempotency-Key": "tr-2"},
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertTrue(confirmed.json()["lines"][0]["voucher_ref"].startswith("VC-"))

    def test_transition_conflict_on_stale_revision(self):
        self._create_sheet_with_line()
        detail = self._create_booking()
        booking_id = detail["booking"]["id"]
        line_id = detail["lines"][0]["id"]

        response = self.client.post(
            f"/api/v2/bookings/{booking_id}/lines/{line_id}/transition",
            json={"base_booking_revision": detail["booking"]["booking_revision"] + 1, "to": "requested"},
            headers={"Idempotency-Key": "tr-stale"},
        )
        self.assertEqual(response.status_code, 409, response.text)

    def test_cancel_booking_cancels_all_open_lines(self):
        self._create_sheet_with_line()
        detail = self._create_booking()
        booking_id = detail["booking"]["id"]

        response = self.client.post(
            f"/api/v2/bookings/{booking_id}/cancel",
            json={"base_booking_revision": detail["booking"]["booking_revision"], "reason": "customer cancelled trip"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["booking"]["status"], "cancelled")
        self.assertTrue(all(line["status"] == "cancelled" for line in body["lines"]))

    def test_ops_update_rejects_frozen_field(self):
        self._create_sheet_with_line()
        detail = self._create_booking()
        booking_id = detail["booking"]["id"]
        line_id = detail["lines"][0]["id"]

        response = self.client.put(
            f"/api/v2/bookings/{booking_id}/lines/{line_id}",
            json={"base_booking_revision": detail["booking"]["booking_revision"], "unit_cost_minor_snapshot": 1},
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_header_status_cannot_bypass_cancel_or_active(self):
        self._create_sheet_with_line()
        detail = self._create_booking()
        for forbidden_status in ("active", "cancelled"):
            response = self.client.put(
                f"/api/v2/bookings/{detail['booking']['id']}",
                json={"base_booking_revision": detail["booking"]["booking_revision"], "status": forbidden_status},
            )
            self.assertEqual(response.status_code, 422, response.text)

    def test_create_and_transition_require_nonempty_idempotency_key(self):
        self._create_sheet_with_line()
        missing_create = self.client.post(
            "/api/v2/bookings", json={"quotation_id": "qtn_bkapi1", "deposit_received_at": "2026-06-01"}
        )
        self.assertEqual(missing_create.status_code, 422, missing_create.text)
        detail = self._create_booking()
        missing_transition = self.client.post(
            f"/api/v2/bookings/{detail['booking']['id']}/lines/{detail['lines'][0]['id']}/transition",
            json={"base_booking_revision": detail["booking"]["booking_revision"], "to": "requested"},
        )
        self.assertEqual(missing_transition.status_code, 422, missing_transition.text)

    def test_today_uses_configured_ops_timezone_at_18z(self):
        from routers.v2.bookings import _today

        self.assertEqual(_today(datetime(2026, 7, 14, 18, tzinfo=timezone.utc)).isoformat(), "2026-07-15")

    def test_booking_routes_do_not_reapply_quotation_ownership(self):
        import inspect
        import routers.v2.bookings as booking_routes

        self.assertNotIn("require_owned_v2_quotation", inspect.getsource(booking_routes))


if __name__ == "__main__":
    unittest.main()
