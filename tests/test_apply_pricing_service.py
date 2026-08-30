import asyncio
import os
import tempfile
import unittest
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import db.session as db_session
import main
from core.kernel import ActorRef
from db.base import Base
from db.models.costing import CostingSheet
from db.models.costing_application import CostingApplication
from db.models.destination import DestinationCatalog
from db.models.outbox import OutboxEvent
from db.models.supplier import Supplier
from repositories.quotation_repository import QuotationRepository
from repositories.quote_request_repository import QuoteRequestRepository
from schemas.v2.costing import (
    ApplyPricingRequestSchema,
    CostingSheetCreateSchema,
    ServiceLineCreateSchema,
)
from services.costing_service import CostingConflictError, CostingService, CostingValidationError

from unittest.mock import patch

ACTOR = ActorRef(actor_id="tester@example.com", actor_type="staff")


class ApplyPricingServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        cls.session_patch = patch.object(db_session, "get_session_factory", return_value=cls.session_factory)
        cls.session_patch.start()
        cls.main_session_patch = patch.object(main, "_get_db_session_factory", return_value=cls.session_factory)
        cls.main_session_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.main_session_patch.stop()
        cls.session_patch.stop()
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.db_file.name)

    def setUp(self):
        asyncio.run(self._reset_db())

    async def _reset_db(self):
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

    async def _create_test_quotation(self, session: AsyncSession, quotation_id: str = "qtn_test1") -> str:
        quotes = QuotationRepository(session)
        quotation = await quotes.create_quotation(
            quotation_id=quotation_id,
            title="Vietnam Safar Tour",
            customer_name="John Doe",
            brand_id="luxury",
            template_name="quote-generator",
            baseline_lang="en",
            source_kind="manual",
        )
        request_json = {
            "source": {"kind": "manual"},
            "brand_id": "luxury",
            "lang": "en",
            "trip_facts": {
                "start_date": "2026-10-01",
                "end_date": "2026-10-05",
                "duration_days": 5,
                "duration_nights": 4,
                "itinerary": [
                    {"day_number": 1, "title": "Arrival in Hanoi", "destination": "Hanoi"},
                    {"day_number": 2, "title": "City Tour", "destination": "Hanoi"},
                    {"day_number": 3, "title": "Street Food Tour", "destination": "Hanoi"},
                    {"day_number": 4, "title": "Free Day", "destination": "Hanoi"},
                    {"day_number": 5, "title": "Departure", "destination": "Hanoi"},
                ],
            },
            "pricing_facts": {
                "conditions": ["Standard conditions"],
                "options": [
                    {
                        "id": "opt_1",
                        "label": "Standard Luxury",
                        "currency": "USD",
                        "per_traveler_amount_minor": 120000,
                        "group_total_amount_minor": 240000,
                        "per_adult_amount_minor": 120000,
                    }
                ],
            },
            "customer_facts": {"customer_name": "John Doe", "adults": 2, "children": 0},
            "service_facts": {"hotels": [], "inclusions": [], "exclusions": []},
            "booking_facts": {"items": []},
            "presentation_options": {"theme_id": "brochure", "renderer": "quote-generator"},
        }
        await quotes.create_quotation_request(quotation_id=quotation.id, request_json=request_json)
        await main.QuotationDocumentRepository(session).save_current_document(
            quotation_id=quotation.id,
            lang="en",
            document_json={
                "quotationId": quotation.id,
                "revision": 1,
                "trip": {"title": "Vietnam Safar Tour", "durationDays": 5, "durationNights": 4},
                "pricingOptions": [
                    {
                        "id": "opt_1",
                        "label": "Standard Luxury",
                        "currency": "USD",
                        "groupTotalAmountMinor": 240000,
                        "perTravelerAmountMinor": 120000,
                        "perAdultAmountMinor": 120000,
                    }
                ],
                "pricingFacts": {
                    "options": [
                        {
                            "id": "opt_1",
                            "label": "Standard Luxury",
                            "currency": "USD",
                            "groupTotalAmountMinor": 240000,
                            "perTravelerAmountMinor": 120000,
                            "perAdultAmountMinor": 120000,
                        }
                    ]
                },
            },
            expected_revision=0,
        )
        await session.commit()
        return quotation.id

    def test_apply_pricing_3_in_1_atomicity(self):
        async def _run():
            async with self.session_factory() as session:
                quotation_id = await self._create_test_quotation(session)
                service = CostingService(session)

                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"),
                    actor=ACTOR,
                )
                sheet_id = sheet_resp.id

                # Add 2 service lines: $500 and $550 = $1,050 cost.
                # Sheet default markup 0 -> $1050 sell.
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="accommodation",
                        title="Hanoi Hotel",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=50000,
                        cost_currency="USD",
                        qty_unit=1,
                        qty_time=1,
                    ),
                    actor=ACTOR,
                    idempotency_key="line_1",
                )
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=1,
                        category="transportation",
                        title="Airport Transfer",
                        unit="vehicle",
                        time_basis="trip",
                        unit_cost_minor=55000,
                        cost_currency="USD",
                        qty_unit=1,
                        qty_time=1,
                    ),
                    actor=ACTOR,
                    idempotency_key="line_2",
                )

                # Total cost = 105000 minor ($1,050), sell = 105000 minor ($1,050)
                # Apply to option 'opt_1' (which previously was $2,400 group total)
                apply_req = ApplyPricingRequestSchema(
                    base_revision=1,
                    base_costing_revision=2,
                    target_option_id="opt_1",
                    option_label="Updated Costing Option",
                    lang="en",
                )
                resp = await service.apply_pricing(sheet_id, apply_req, actor=ACTOR)
                await session.commit()

                self.assertIsNotNone(resp)
                self.assertEqual(resp.application.sell_total_minor, 105000)
                self.assertEqual(resp.application.cost_total_minor, 105000)
                self.assertEqual(resp.application.target_option_id, "opt_1")
                self.assertEqual(resp.facts_revision, 2)
                self.assertEqual(resp.costing_revision, 2)

                # Invariant a: Check facts updated
                quotes = QuotationRepository(session)
                req = await quotes.get_latest_quotation_request(quotation_id)
                opt = req.request_json["pricing_facts"]["options"][0]
                self.assertEqual(opt["group_total_amount_minor"], 105000)
                # 15.5 §1.5(3): currency unchanged (USD -> USD) — the backend must
                # preserve the sale's existing per-person split (120000), never
                # recompute it (the old bug produced 105000 // adults = 52500).
                self.assertEqual(opt["per_adult_amount_minor"], 120000)
                self.assertEqual(opt["label"], "Updated Costing Option")

                # Invariant b: Check costing_applications row
                app_rows = (
                    await session.execute(
                        select(CostingApplication).where(CostingApplication.sheet_id == sheet_id)
                    )
                ).scalars().all()
                self.assertEqual(len(app_rows), 1)
                self.assertEqual(app_rows[0].sell_total_minor, 105000)
                self.assertEqual(app_rows[0].cost_total_minor, 105000)
                self.assertEqual(app_rows[0].facts_revision_after, 2)
                self.assertEqual(app_rows[0].costing_revision_at_apply, 2)

                # Invariant c: Check outbox event
                outbox_events = (
                    await session.execute(
                        select(OutboxEvent).where(OutboxEvent.aggregate_id == sheet_id)
                    )
                ).scalars().all()
                self.assertEqual(len(outbox_events), 1)
                self.assertEqual(outbox_events[0].event_type, "costing.applied")
                self.assertEqual(outbox_events[0].payload_json["sell_total_minor"], 105000)

        asyncio.run(_run())

    def test_apply_pricing_outbox_failure_rolls_back_everything(self):
        """§3 required case: a failure at the outbox step must leave facts
        UNCHANGED and produce NO application row — never a half-applied state
        where facts moved but there's no audit log, or vice versa."""

        async def _run():
            async with self.session_factory() as session:
                quotation_id = await self._create_test_quotation(session)
                service = CostingService(session)

                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"),
                    actor=ACTOR,
                )
                sheet_id = sheet_resp.id
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="accommodation",
                        title="Hanoi Hotel",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=50000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_1",
                )

                with patch(
                    "services.costing_service.OutboxService.emit_event",
                    side_effect=RuntimeError("outbox unavailable"),
                ):
                    with self.assertRaises(RuntimeError):
                        await service.apply_pricing(
                            sheet_id,
                            ApplyPricingRequestSchema(
                                base_revision=1,
                                base_costing_revision=1,
                                target_option_id="opt_1",
                            ),
                            actor=ACTOR,
                        )
                await session.rollback()

                apps = (
                    await session.execute(
                        select(CostingApplication).where(CostingApplication.sheet_id == sheet_id)
                    )
                ).scalars().all()
                self.assertEqual(len(apps), 0)

                outbox_events = (
                    await session.execute(select(OutboxEvent).where(OutboxEvent.aggregate_id == sheet_id))
                ).scalars().all()
                self.assertEqual(len(outbox_events), 0)

                quotes = QuotationRepository(session)
                req = await quotes.get_latest_quotation_request(quotation_id)
                opt = req.request_json["pricing_facts"]["options"][0]
                self.assertEqual(opt["group_total_amount_minor"], 240000)
                self.assertEqual(opt["per_adult_amount_minor"], 120000)

        asyncio.run(_run())

    def test_apply_pricing_clears_per_person_split_when_currency_changes(self):
        """15.5 §1.5(3): the backend never invents a per-person split — it only
        preserves the sale's existing one when the currency is unchanged, and
        clears it (never recomputes) when the target option's currency changes
        so the FE reconciler re-derives it from scratch."""

        async def _run():
            async with self.session_factory() as session:
                quotation_id = await self._create_test_quotation(session)
                service = CostingService(session)

                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="EUR"),
                    actor=ACTOR,
                )
                sheet_id = sheet_resp.id
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="accommodation",
                        title="Hanoi Hotel",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=50000,
                        cost_currency="EUR",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_1",
                )

                # opt_1 starts as USD/120000-per-adult (see _create_test_quotation);
                # applying an EUR sheet onto it changes the option's currency.
                apply_req = ApplyPricingRequestSchema(
                    base_revision=1,
                    base_costing_revision=1,
                    target_option_id="opt_1",
                )
                resp = await service.apply_pricing(sheet_id, apply_req, actor=ACTOR)
                await session.commit()

                self.assertIsNotNone(resp)
                quotes = QuotationRepository(session)
                req = await quotes.get_latest_quotation_request(quotation_id)
                opt = req.request_json["pricing_facts"]["options"][0]
                self.assertEqual(opt["currency"], "EUR")
                self.assertEqual(opt["group_total_amount_minor"], 50000)
                self.assertIsNone(opt.get("per_adult_amount_minor"))
                self.assertIsNone(opt.get("per_traveler_amount_minor"))
                self.assertIsNone(opt.get("per_child_amount_minor"))

        asyncio.run(_run())

    def test_apply_pricing_dual_cas_concurrency(self):
        async def _run():
            async with self.session_factory() as session:
                quotation_id = await self._create_test_quotation(session)
                service = CostingService(session)

                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"),
                    actor=ACTOR,
                )
                sheet_id = sheet_resp.id
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="accommodation",
                        title="Hanoi Hotel",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=50000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_1",
                )

                # Case 1: Stale costing revision (passed 999 instead of 1)
                with self.assertRaises(CostingConflictError):
                    await service.apply_pricing(
                        sheet_id,
                        ApplyPricingRequestSchema(
                            base_revision=1,
                            base_costing_revision=999,
                            target_option_id="opt_1",
                        ),
                        actor=ACTOR,
                    )

                # Case 2: Stale facts revision (passed 999 instead of 1)
                with self.assertRaises(CostingConflictError):
                    await service.apply_pricing(
                        sheet_id,
                        ApplyPricingRequestSchema(
                            base_revision=999,
                            base_costing_revision=1,
                            target_option_id="opt_1",
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(_run())

    def test_apply_pricing_rejects_line_edit_that_lands_mid_flight(self):
        """16.3 P1 fix: apply_pricing doesn't itself touch costing_sheets, so the
        Python-level pre-check at the top is only a fast check — this proves the
        DB-level guard added right before insert_application actually catches a
        concurrent write that commits *during* the facts write, and that nothing
        (including the facts change) is left persisted."""

        async def _run():
            async with self.session_factory() as session:
                quotation_id = await self._create_test_quotation(session)
                service = CostingService(session)

                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"),
                    actor=ACTOR,
                )
                sheet_id = sheet_resp.id
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="accommodation",
                        title="Hanoi Hotel",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=50000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_1",
                )

                from api.runtime import apply_pricing_option as real_apply_pricing_option

                async def _apply_then_concurrent_write(**kwargs):
                    # Simulate another transaction committing a line edit while
                    # this facts write was in flight — same session stands in
                    # for "another connection already committed" since SQLite
                    # can't run two real concurrent transactions in-process.
                    result = await real_apply_pricing_option(**kwargs)
                    await session.execute(
                        select(CostingSheet).where(CostingSheet.id == sheet_id)
                    )
                    from sqlalchemy import update as sa_update

                    await session.execute(
                        sa_update(CostingSheet)
                        .where(CostingSheet.id == sheet_id)
                        .values(costing_revision=CostingSheet.costing_revision + 1)
                    )
                    return result

                with patch(
                    "services.costing_service.apply_pricing_option",
                    side_effect=_apply_then_concurrent_write,
                ):
                    with self.assertRaises(CostingConflictError):
                        await service.apply_pricing(
                            sheet_id,
                            ApplyPricingRequestSchema(
                                base_revision=1,
                                base_costing_revision=1,
                                target_option_id="opt_1",
                            ),
                            actor=ACTOR,
                        )
                await session.rollback()

                # Nothing persisted: no application row, facts option untouched.
                apps = (
                    await session.execute(
                        select(CostingApplication).where(CostingApplication.sheet_id == sheet_id)
                    )
                ).scalars().all()
                self.assertEqual(len(apps), 0)

                quotes = QuotationRepository(session)
                req = await quotes.get_latest_quotation_request(quotation_id)
                opt = req.request_json["pricing_facts"]["options"][0]
                self.assertEqual(opt["group_total_amount_minor"], 240000)

        asyncio.run(_run())

    def test_apply_pricing_idempotency_replay(self):
        async def _run():
            async with self.session_factory() as session:
                quotation_id = await self._create_test_quotation(session)
                service = CostingService(session)

                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"),
                    actor=ACTOR,
                )
                sheet_id = sheet_resp.id
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="accommodation",
                        title="Hanoi Hotel",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=50000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_1",
                )

                apply_req = ApplyPricingRequestSchema(
                    base_revision=1,
                    base_costing_revision=1,
                    target_option_id="opt_1",
                )
                resp1 = await service.apply_pricing(
                    sheet_id, apply_req, actor=ACTOR, idempotency_key="idem_key_123"
                )
                await session.commit()

                # Replay identical apply request with same idempotency key
                resp2 = await service.apply_pricing(
                    sheet_id, apply_req, actor=ACTOR, idempotency_key="idem_key_123"
                )
                await session.commit()

                self.assertEqual(resp1.application.id, resp2.application.id)
                self.assertEqual(resp1.facts_revision, resp2.facts_revision)

                # Exactly 1 application row in DB
                apps = (
                    await session.execute(
                        select(CostingApplication).where(CostingApplication.sheet_id == sheet_id)
                    )
                ).scalars().all()
                self.assertEqual(len(apps), 1)

        asyncio.run(_run())

    def test_apply_pricing_idempotency_replay_wins_over_stale_revision(self):
        """16.3 P0 fix (chốt #6): a same-key retry must replay, not 409, even
        when the sheet's costing_revision moved on for an unrelated reason
        after the original successful apply."""

        async def _run():
            async with self.session_factory() as session:
                quotation_id = await self._create_test_quotation(session)
                service = CostingService(session)

                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"),
                    actor=ACTOR,
                )
                sheet_id = sheet_resp.id
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="accommodation",
                        title="Hanoi Hotel",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=50000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_1",
                )

                apply_req = ApplyPricingRequestSchema(
                    base_revision=1,
                    base_costing_revision=1,
                    target_option_id="opt_1",
                )
                resp1 = await service.apply_pricing(
                    sheet_id, apply_req, actor=ACTOR, idempotency_key="idem_key_stale"
                )
                await session.commit()

                # Sheet moves on for an unrelated reason (a second line) — the
                # client's stale base_costing_revision=1 would now 409 on a
                # fresh call, but this is the SAME idempotency key retrying.
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=1,
                        category="transportation",
                        title="Airport Transfer",
                        unit="vehicle",
                        time_basis="trip",
                        unit_cost_minor=20000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_2",
                )
                await session.commit()

                # Same request object (still base_costing_revision=1, now stale)
                # + same idempotency key must replay, not raise 409.
                resp2 = await service.apply_pricing(
                    sheet_id, apply_req, actor=ACTOR, idempotency_key="idem_key_stale"
                )
                await session.commit()

                self.assertEqual(resp1.application.id, resp2.application.id)
                self.assertEqual(resp2.facts_revision, resp1.facts_revision)
                self.assertEqual(resp2.costing_revision, resp1.costing_revision)
                self.assertEqual(resp2.summary.sell_total_minor, resp1.summary.sell_total_minor)

                apps = (
                    await session.execute(
                        select(CostingApplication).where(CostingApplication.sheet_id == sheet_id)
                    )
                ).scalars().all()
                self.assertEqual(len(apps), 1)

        asyncio.run(_run())

    def test_apply_pricing_drift_detection_flow(self):
        async def _run():
            async with self.session_factory() as session:
                quotation_id = await self._create_test_quotation(session)
                service = CostingService(session)

                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"),
                    actor=ACTOR,
                )
                sheet_id = sheet_resp.id
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="accommodation",
                        title="Hanoi Hotel",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=50000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_1",
                )

                # Initial apply
                await service.apply_pricing(
                    sheet_id,
                    ApplyPricingRequestSchema(
                        base_revision=1,
                        base_costing_revision=1,
                        target_option_id="opt_1",
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                # Check workbench immediately after apply: no drift
                wb = await service.get_workbench(sheet_id)
                self.assertIsNotNone(wb.drift)
                self.assertFalse(wb.drift.has_drift)
                self.assertFalse(wb.drift.costing_modified_since_apply)

                # Step: add a new line to costing sheet ($100 surcharge)
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=1,
                        category="experience",
                        title="City Tour Surcharge",
                        unit="person",
                        time_basis="trip",
                        unit_cost_minor=10000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_surcharge",
                )
                await session.commit()

                # Invariant 4: Facts are NOT auto-overwritten
                quotes = QuotationRepository(session)
                req = await quotes.get_latest_quotation_request(quotation_id)
                opt = req.request_json["pricing_facts"]["options"][0]
                self.assertEqual(opt["group_total_amount_minor"], 50000)

                # Invariant 4: Costing tab displays drift badge
                wb_after_drift = await service.get_workbench(sheet_id)
                self.assertTrue(wb_after_drift.drift.has_drift)
                self.assertTrue(wb_after_drift.drift.costing_modified_since_apply)
                self.assertEqual(wb_after_drift.drift.last_applied_sell_total_minor, 50000)

                # Re-apply to option 1 with new total ($600)
                reapply_resp = await service.apply_pricing(
                    sheet_id,
                    ApplyPricingRequestSchema(
                        base_revision=2,
                        base_costing_revision=2,
                        target_option_id="opt_1",
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(reapply_resp.application.sell_total_minor, 60000)

                # Check drift is resolved
                wb_reapplied = await service.get_workbench(sheet_id)
                self.assertFalse(wb_reapplied.drift.has_drift)
                self.assertEqual(len(wb_reapplied.applications), 2)

        asyncio.run(_run())

    def test_apply_pricing_validation_gates(self):
        async def _run():
            async with self.session_factory() as session:
                req_repo = QuoteRequestRepository(session)
                qr = await req_repo.create_request(
                    role="customer", customer_name="Jane Doe", email="jane@example.com", request_id="req_test1"
                )
                service = CostingService(session)

                # Sheet attached to request only (quotation_id is None)
                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(request_id=qr.id, currency="USD"),
                    actor=ACTOR,
                )
                with self.assertRaises(CostingValidationError):
                    await service.apply_pricing(
                        sheet_resp.id,
                        ApplyPricingRequestSchema(base_revision=1, base_costing_revision=0),
                        actor=ACTOR,
                    )

                # Empty sheet attached to quotation
                quotation_id = await self._create_test_quotation(session)
                empty_sheet = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"),
                    actor=ACTOR,
                )
                with self.assertRaises(CostingValidationError):
                    await service.apply_pricing(
                        empty_sheet.id,
                        ApplyPricingRequestSchema(base_revision=1, base_costing_revision=0),
                        actor=ACTOR,
                    )

                # Same sheet, now with a line that nets to a zero sell total
                # (only one sheet is allowed per quotation).
                await service.create_line(
                    empty_sheet.id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="visa",
                        title="Complimentary visa assistance",
                        unit="person",
                        time_basis="trip",
                        unit_cost_minor=0,
                        cost_currency="USD",
                        sell_override_minor=0,
                    ),
                    actor=ACTOR,
                    idempotency_key="zero_line",
                )
                with self.assertRaises(CostingValidationError):
                    await service.apply_pricing(
                        empty_sheet.id,
                        ApplyPricingRequestSchema(base_revision=1, base_costing_revision=1, target_option_id="opt_1"),
                        actor=ACTOR,
                    )

        asyncio.run(_run())

    def test_apply_pricing_rejects_when_both_revisions_are_stale(self):
        """§3 required case: facts AND costing revision both stale at once still
        409s cleanly (the costing check wins, since it runs first) — not a 500,
        not a partial write."""

        async def _run():
            async with self.session_factory() as session:
                quotation_id = await self._create_test_quotation(session)
                service = CostingService(session)

                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"),
                    actor=ACTOR,
                )
                sheet_id = sheet_resp.id
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="accommodation",
                        title="Hanoi Hotel",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=50000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_1",
                )

                with self.assertRaises(CostingConflictError):
                    await service.apply_pricing(
                        sheet_id,
                        ApplyPricingRequestSchema(
                            base_revision=999,
                            base_costing_revision=999,
                            target_option_id="opt_1",
                        ),
                        actor=ACTOR,
                    )

                apps = (
                    await session.execute(
                        select(CostingApplication).where(CostingApplication.sheet_id == sheet_id)
                    )
                ).scalars().all()
                self.assertEqual(len(apps), 0)

        asyncio.run(_run())

    def test_apply_pricing_creates_new_option_and_rejects_a_fourth(self):
        """15.4 §6 / 15.5 §1.4: target_option_id=None creates a new commercial
        option, up to MAX_COMMERCIAL_OPTIONS (3) — the 4th attempt 409s."""

        async def _run():
            async with self.session_factory() as session:
                quotation_id = await self._create_test_quotation(session)  # ships with 1 option (opt_1)
                service = CostingService(session)

                sheet_resp = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"),
                    actor=ACTOR,
                )
                sheet_id = sheet_resp.id
                await service.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=0,
                        category="accommodation",
                        title="Hanoi Hotel",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=50000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line_1",
                )

                # opt_1 already exists -> this creates opt_2.
                resp2 = await service.apply_pricing(
                    sheet_id,
                    ApplyPricingRequestSchema(base_revision=1, base_costing_revision=1, target_option_id=None, option_label="Deluxe"),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(resp2.application.target_option_id, "opt_2")

                # -> opt_3.
                resp3 = await service.apply_pricing(
                    sheet_id,
                    ApplyPricingRequestSchema(base_revision=resp2.facts_revision, base_costing_revision=1, target_option_id=None, option_label="Premium"),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(resp3.application.target_option_id, "opt_3")

                quotes = QuotationRepository(session)
                req = await quotes.get_latest_quotation_request(quotation_id)
                self.assertEqual(len(req.request_json["pricing_facts"]["options"]), 3)

                # A 4th new option is over MAX_COMMERCIAL_OPTIONS -> 409, no new row.
                with self.assertRaises(CostingConflictError):
                    await service.apply_pricing(
                        sheet_id,
                        ApplyPricingRequestSchema(
                            base_revision=resp3.facts_revision, base_costing_revision=1, target_option_id=None, option_label="Ultra"
                        ),
                        actor=ACTOR,
                    )

                apps = (
                    await session.execute(
                        select(CostingApplication).where(CostingApplication.sheet_id == sheet_id)
                    )
                ).scalars().all()
                self.assertEqual(len(apps), 2)

        asyncio.run(_run())
