import asyncio
import os
import tempfile
import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

from core.kernel import ActorRef
from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from repositories.quote_request_repository import QuoteRequestRepository
from repositories.quotation_repository import QuotationRepository
from repositories.booking_repository import BookingRepository, BookingSlotTakenError
from repositories.supplier_repository import SupplierRepository
from schemas.v2.booking import (
    BookingAddLineSchema,
    BookingCancelSchema,
    BookingCreateSchema,
    BookingHeaderUpdateSchema,
    BookingLineOpsUpdateSchema,
    BookingLineTransitionSchema,
)
from schemas.v2.costing import CostingSheetCreateSchema, ServiceLineCreateSchema
from services.booking_service import BookingConflictError, BookingService, BookingValidationError
from services.costing_service import CostingConflictError, CostingService

ACTOR = ActorRef(actor_id="ops@example.com", actor_type="staff")

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
BOOKING_FIXTURE_RESOLVED_FACTS = {"partyLabel": "Jane Doe", "factsHash": "booking-fixture-v1"}


class BookingServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = make_test_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.db_file.name)

    def setUp(self):
        asyncio.run(self._reset_db())

    async def _reset_db(self):
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
                    contact_json={"phone": "+84-000", "zalo": "lasiesta"},
                    payment_terms_json=PAYMENT_TERMS,
                    cancellation_policy_json=CANCELLATION_POLICY,
                )
            )
            await session.commit()
            await QuoteRequestRepository(session).create_request(
                role="customer", customer_name="Jane Doe", email="jane@example.com", request_id="req_bk1"
            )
            await session.commit()
            quotation_repository = QuotationRepository(session)
            quotation = await quotation_repository.create_quotation(
                quotation_id="qtn_bk1",
                brand_id="brand_capella",
                template_name="quote-generator",
                baseline_lang="en",
                source_kind="manual",
                status="draft",
                quotation_family_id="qtn_bk1",
                business_version=1,
            )
            await quotation_repository.create_quotation_request(
                quotation_id=quotation.id, request_json=BOOKING_FIXTURE_FACTS
            )
            await quotation_repository.create_version_facts(
                quotation_id=quotation.id,
                canonical_facts_json=BOOKING_FIXTURE_FACTS,
                resolved_facts_json=BOOKING_FIXTURE_RESOLVED_FACTS,
                facts_hash="booking-fixture-v1",
                source_request_id=None,
                source_request_revision=None,
            )
            await session.commit()

    async def _make_sheet_with_line(self, session, *, quotation_id="qtn_bk1", service_date=date(2026, 7, 15)):
        costing = CostingService(session)
        sheet = await costing.create_sheet(CostingSheetCreateSchema(quotation_id=quotation_id, currency="USD"), actor=ACTOR)
        await session.commit()
        workbench = await costing.create_line(
            sheet.id,
            ServiceLineCreateSchema(
                base_costing_revision=sheet.costing_revision,
                day_number=1,
                service_date=service_date,
                category="accommodation",
                title="La Siesta — Deluxe Room",
                supplier_id="sup_la_siesta",
                unit="room",
                time_basis="night",
                unit_cost_minor=1_000_000,
                cost_currency="USD",
                qty_unit=2,
                qty_time=1,
            ),
            actor=ACTOR,
            idempotency_key="line-1",
        )
        await session.commit()
        return sheet.id, workbench.items[0].id

    def test_create_booking_snapshots_frozen_terms_and_supplier_edits_do_not_move_it(self):
        async def scenario():
            async with self.session_factory() as session:
                sheet_id, line_id = await self._make_sheet_with_line(session)
                booking_service = BookingService(session)
                detail = await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="create-1",
                    today=date(2026, 6, 1),
                )
                await session.commit()

                self.assertTrue(detail.booking.id.startswith("bkg_"))
                self.assertEqual(detail.booking.booking_code, "BK-2026-0001")
                self.assertEqual(len(detail.lines), 1)
                line = detail.lines[0]
                self.assertEqual(line.status, "to_request")
                self.assertEqual(line.sell_minor_snapshot, 2_000_000)
                self.assertEqual(line.cancellation_policy_snapshot_json.tiers[0].penalty_percent, 25)
                # T3: penalty_free_until = service_date(7/15) - 14 - 1 = 6/30
                self.assertEqual(line.penalty_free_until, date(2026, 6, 30))
                self.assertEqual(line.balance_due_date, date(2026, 7, 5))

                # R3/T3: mutate the supplier's live policy after booking — frozen line must not move.
                supplier = await SupplierRepository(session).get_by_id("sup_la_siesta")
                supplier.cancellation_policy_json = {"tiers": [{"days_before_service_min": 0, "penalty_percent": 100}]}
                await session.commit()

                reloaded = await booking_service.get_detail(detail.booking.id, today=date(2026, 6, 1))
                self.assertEqual(reloaded.lines[0].penalty_free_until, date(2026, 6, 30))

        asyncio.run(scenario())

    def test_create_booking_mirrors_service_line_booking_status(self):
        async def scenario():
            async with self.session_factory() as session:
                sheet_id, line_id = await self._make_sheet_with_line(session)
                costing = CostingService(session)
                before = await costing.get_workbench(sheet_id)
                booking_service = BookingService(session)
                await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="create-mirror",
                    today=date(2026, 6, 1),
                )
                await session.commit()

                workbench = await costing.get_workbench(sheet_id)
                self.assertEqual(workbench.items[0].booking_status, "to_request")
                self.assertEqual(workbench.sheet.costing_revision, before.sheet.costing_revision + 1)

        asyncio.run(scenario())

    def test_second_active_booking_for_same_quotation_conflicts_until_first_is_cancelled(self):
        async def scenario():
            async with self.session_factory() as session:
                await self._make_sheet_with_line(session)
                booking_service = BookingService(session)
                first = await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="c1",
                    today=date(2026, 6, 1),
                )
                await session.commit()

                with self.assertRaises(BookingConflictError):
                    await booking_service.create_booking(
                        BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 2)),
                        actor=ACTOR,
                        idempotency_key="c2",
                        today=date(2026, 6, 2),
                    )

                await booking_service.cancel_booking(
                    first.booking.id,
                    BookingCancelSchema(base_booking_revision=first.booking.booking_revision, reason="customer cancelled trip"),
                    actor=ACTOR,
                    today=date(2026, 6, 2),
                )
                await session.commit()

                second = await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 3)),
                    actor=ACTOR,
                    idempotency_key="c3",
                    today=date(2026, 6, 3),
                )
                await session.commit()
                self.assertNotEqual(second.booking.id, first.booking.id)

        asyncio.run(scenario())

    def test_create_booking_idempotent_retry_returns_same_booking(self):
        async def scenario():
            async with self.session_factory() as session:
                await self._make_sheet_with_line(session)
                booking_service = BookingService(session)
                payload = BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1))
                first = await booking_service.create_booking(payload, actor=ACTOR, idempotency_key="dup", today=date(2026, 6, 1))
                await session.commit()
                second = await booking_service.create_booking(payload, actor=ACTOR, idempotency_key="dup", today=date(2026, 6, 1))
                await session.commit()
                self.assertEqual(first.booking.id, second.booking.id)

        asyncio.run(scenario())

    def test_booking_reused_idempotency_key_with_different_payload_conflicts(self):
        async def scenario():
            async with self.session_factory() as session:
                await self._make_sheet_with_line(session)
                service = BookingService(session)
                await service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="booking-idempotency-conflict",
                    today=date(2026, 6, 1),
                )
                await session.commit()
                with self.assertRaises(BookingConflictError):
                    await service.create_booking(
                        BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 2)),
                        actor=ACTOR,
                        idempotency_key="booking-idempotency-conflict",
                        today=date(2026, 6, 2),
                    )

        asyncio.run(scenario())

    def test_transition_to_confirmed_generates_voucher_and_is_idempotent(self):
        async def scenario():
            async with self.session_factory() as session:
                await self._make_sheet_with_line(session)
                booking_service = BookingService(session)
                detail = await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="c-confirm",
                    today=date(2026, 6, 1),
                )
                await session.commit()
                booking_id = detail.booking.id
                line_id = detail.lines[0].id

                requested = await booking_service.transition_line(
                    booking_id,
                    line_id,
                    BookingLineTransitionSchema(base_booking_revision=detail.booking.booking_revision, to="requested"),
                    actor=ACTOR,
                    idempotency_key="t1",
                    today=date(2026, 6, 2),
                )
                await session.commit()

                confirmed = await booking_service.transition_line(
                    booking_id,
                    line_id,
                    BookingLineTransitionSchema(
                        base_booking_revision=requested.booking.booking_revision, to="confirmed", supplier_ref="CONF-123"
                    ),
                    actor=ACTOR,
                    idempotency_key="t2",
                    today=date(2026, 6, 3),
                )
                await session.commit()
                self.assertIsNotNone(confirmed.lines[0].voucher_ref)
                self.assertTrue(confirmed.lines[0].voucher_ref.startswith("VC-2026-"))
                first_voucher = confirmed.lines[0].voucher_ref

                # idempotent retry with the same key must not mint a second voucher
                retried = await booking_service.transition_line(
                    booking_id,
                    line_id,
                    BookingLineTransitionSchema(
                        base_booking_revision=requested.booking.booking_revision, to="confirmed", supplier_ref="CONF-123"
                    ),
                    actor=ACTOR,
                    idempotency_key="t2",
                    today=date(2026, 6, 3),
                )
                self.assertEqual(retried.lines[0].voucher_ref, first_voucher)

                with self.assertRaises(BookingConflictError):
                    await booking_service.transition_line(
                        booking_id,
                        line_id,
                        BookingLineTransitionSchema(
                            base_booking_revision=confirmed.booking.booking_revision,
                            to="delivered",
                        ),
                        actor=ACTOR,
                        idempotency_key="t2",
                        today=date(2026, 6, 3),
                    )

        asyncio.run(scenario())

    def test_cancel_line_computes_penalty_from_frozen_tiers(self):
        async def scenario():
            async with self.session_factory() as session:
                await self._make_sheet_with_line(session, service_date=date(2026, 7, 15))
                booking_service = BookingService(session)
                detail = await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="c-cancel",
                    today=date(2026, 6, 1),
                )
                await session.commit()
                # cancel on 7/10 -> 5 days remaining -> the 0-day tier does not qualify,
                # the 14-day tier does (5 <= 14) -> 25%.
                cancelled = await booking_service.transition_line(
                    detail.booking.id,
                    detail.lines[0].id,
                    BookingLineTransitionSchema(
                        base_booking_revision=detail.booking.booking_revision, to="cancelled", cancel_reason="hotel overbooked"
                    ),
                    actor=ACTOR,
                    idempotency_key="cancel-1",
                    today=date(2026, 7, 10),
                )
                self.assertEqual(cancelled.lines[0].cancel_penalty_minor, 500_000)

        asyncio.run(scenario())

    def test_booking_rejects_manual_service_line_without_a_date(self):
        async def scenario():
            async with self.session_factory() as session:
                sheet_id, _ = await self._make_sheet_with_line(session)
                costing = CostingService(session)
                sheet = await costing.get_workbench(sheet_id)
                await costing.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=sheet.sheet.costing_revision,
                        day_number=None,
                        category="transportation",
                        title="Undated transfer",
                        unit="vehicle",
                        time_basis="trip",
                        unit_cost_minor=100_000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="undated-line",
                )
                with self.assertRaises(BookingValidationError) as raised:
                    await BookingService(session).create_booking(
                        BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                        actor=ACTOR,
                        idempotency_key="undated-booking",
                        today=date(2026, 6, 1),
                    )
                self.assertIn("Every booking line requires a service date", str(raised.exception))

        asyncio.run(scenario())

    def test_cancellation_penalty_uses_frozen_cost_not_sell(self):
        async def scenario():
            async with self.session_factory() as session:
                sheet_id, line_id = await self._make_sheet_with_line(session, service_date=date(2026, 7, 15))
                line = await CostingService(session).repository.get_line_by_id(line_id)
                assert line is not None
                line.sell_override_minor = 2_400_000  # 20% commercial markup over the 2_000_000 cost.
                await session.commit()
                service = BookingService(session)
                detail = await service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="cost-penalty",
                    today=date(2026, 6, 1),
                )
                cancelled = await service.transition_line(
                    detail.booking.id,
                    detail.lines[0].id,
                    BookingLineTransitionSchema(
                        base_booking_revision=detail.booking.booking_revision,
                        to="cancelled",
                        cancel_reason="supplier cancellation",
                    ),
                    actor=ACTOR,
                    idempotency_key="cost-penalty-cancel",
                    today=date(2026, 7, 10),
                )
                self.assertEqual(cancelled.lines[0].sell_minor_snapshot, 2_400_000)
                self.assertEqual(cancelled.lines[0].cancel_penalty_minor, 500_000)

        asyncio.run(scenario())

    def test_terminal_line_rejects_ops_edits_and_preconfirm_fields_can_clear(self):
        async def scenario():
            async with self.session_factory() as session:
                await self._make_sheet_with_line(session)
                service = BookingService(session)
                detail = await service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="ops-terminal",
                    today=date(2026, 6, 1),
                )
                cleared = await service.update_line_ops(
                    detail.booking.id,
                    detail.lines[0].id,
                    BookingLineOpsUpdateSchema(
                        base_booking_revision=detail.booking.booking_revision,
                        request_by_date=None,
                        notes=None,
                    ),
                    actor=ACTOR,
                    today=date(2026, 6, 1),
                )
                self.assertIsNone(cleared.lines[0].request_by_date)
                cancelled = await service.transition_line(
                    detail.booking.id,
                    detail.lines[0].id,
                    BookingLineTransitionSchema(
                        base_booking_revision=cleared.booking.booking_revision,
                        to="cancelled",
                        cancel_reason="cancel for terminal edit test",
                    ),
                    actor=ACTOR,
                    idempotency_key="ops-terminal-cancel",
                    today=date(2026, 6, 2),
                )
                with self.assertRaises(BookingValidationError):
                    await service.update_line_ops(
                        detail.booking.id,
                        detail.lines[0].id,
                        BookingLineOpsUpdateSchema(
                            base_booking_revision=cancelled.booking.booking_revision,
                            notes="must fail",
                        ),
                        actor=ACTOR,
                        today=date(2026, 6, 2),
                    )

        asyncio.run(scenario())

    def test_add_line_amendment_and_conflict_when_already_booked(self):
        async def scenario():
            async with self.session_factory() as session:
                sheet_id, line_id = await self._make_sheet_with_line(session)

                booking_service = BookingService(session)
                detail = await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="c-amend",
                    today=date(2026, 6, 1),
                )
                await session.commit()
                self.assertEqual(len(detail.lines), 1)

                # customer changes their mind after the booking was created — a new
                # service_line lands on the same sheet, then gets added as an amendment.
                costing = CostingService(session)
                sheet = await costing.get_workbench(sheet_id)
                second_service_line = await costing.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=sheet.sheet.costing_revision,
                        day_number=2,
                        service_date=date(2026, 7, 16),
                        category="transportation",
                        title="Airport transfer",
                        unit="vehicle",
                        time_basis="trip",
                        unit_cost_minor=200_000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="line-2",
                )
                await session.commit()
                new_service_line_id = second_service_line.items[1].id

                amended = await booking_service.add_line(
                    detail.booking.id,
                    BookingAddLineSchema(base_booking_revision=detail.booking.booking_revision, service_line_id=new_service_line_id),
                    actor=ACTOR,
                    today=date(2026, 6, 2),
                )
                await session.commit()
                self.assertEqual(len(amended.lines), 2)

                with self.assertRaises(BookingConflictError):
                    await booking_service.add_line(
                        detail.booking.id,
                        BookingAddLineSchema(
                            base_booking_revision=amended.booking.booking_revision, service_line_id=new_service_line_id
                        ),
                        actor=ACTOR,
                        today=date(2026, 6, 2),
                    )

        asyncio.run(scenario())

    def test_costing_line_already_booked_cannot_be_deleted(self):
        async def scenario():
            async with self.session_factory() as session:
                sheet_id, line_id = await self._make_sheet_with_line(session)
                booking_service = BookingService(session)
                await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="c-guard",
                    today=date(2026, 6, 1),
                )
                await session.commit()

                costing = CostingService(session)
                with self.assertRaises(CostingConflictError):
                    await costing.delete_line(sheet_id, line_id, base_costing_revision=1)

        asyncio.run(scenario())

    def test_header_cas_conflict_on_stale_revision(self):
        async def scenario():
            async with self.session_factory() as session:
                await self._make_sheet_with_line(session)
                booking_service = BookingService(session)
                detail = await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="c-cas",
                    today=date(2026, 6, 1),
                )
                await session.commit()

                from schemas.v2.booking import BookingHeaderUpdateSchema

                with self.assertRaises(BookingConflictError):
                    await booking_service.update_header(
                        detail.booking.id,
                        BookingHeaderUpdateSchema(base_booking_revision=detail.booking.booking_revision + 1, notes="x"),
                        actor=ACTOR,
                        today=date(2026, 6, 2),
                    )

        asyncio.run(scenario())

    def test_completed_header_requires_every_line_to_be_terminal(self):
        async def scenario():
            async with self.session_factory() as session:
                await self._make_sheet_with_line(session)
                service = BookingService(session)
                detail = await service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR, idempotency_key="completed-gate", today=date(2026, 6, 1),
                )
                with self.assertRaises(BookingValidationError):
                    await service.update_header(
                        detail.booking.id,
                        BookingHeaderUpdateSchema(base_booking_revision=detail.booking.booking_revision, status="completed"),
                        actor=ACTOR, today=date(2026, 6, 1),
                    )

        asyncio.run(scenario())

    def test_slot_collision_uses_savepoint_and_outer_transaction_survives(self):
        async def scenario():
            async with self.session_factory() as session:
                await self._make_sheet_with_line(session)
                service = BookingService(session)
                detail = await service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR, idempotency_key="savepoint-booking", today=date(2026, 6, 1),
                )
                repository = BookingRepository(session)
                existing_line = await repository.get_line_by_id(detail.lines[0].id)
                assert existing_line is not None
                duplicate_values = {
                    "source_service_line_id": existing_line.source_service_line_id,
                    "supplier_id_snapshot": existing_line.supplier_id_snapshot,
                    "supplier_name_snapshot": existing_line.supplier_name_snapshot,
                    "supplier_contact_snapshot_json": existing_line.supplier_contact_snapshot_json,
                    "title_snapshot": existing_line.title_snapshot,
                    "category": existing_line.category,
                    "service_date": existing_line.service_date,
                    "unit": existing_line.unit,
                    "time_basis": existing_line.time_basis,
                    "qty_unit": existing_line.qty_unit,
                    "qty_time": existing_line.qty_time,
                    "unit_cost_minor_snapshot": existing_line.unit_cost_minor_snapshot,
                    "cost_currency_snapshot": existing_line.cost_currency_snapshot,
                    "fx_rate_ppm_snapshot": existing_line.fx_rate_ppm_snapshot,
                    "sell_minor_snapshot": existing_line.sell_minor_snapshot,
                    "status": "to_request",
                }
                booking = await repository.get_booking_by_id(detail.booking.id)
                assert booking is not None
                with self.assertRaises(BookingSlotTakenError):
                    await repository.insert_line(booking, line_id="bkl_duplicate_slot", values=duplicate_values)
                await repository.update_header(booking, values={"notes": "outer transaction survived"})
                await session.commit()
                reloaded = await service.get_detail(detail.booking.id, today=date(2026, 6, 1))
                assert reloaded is not None
                self.assertEqual(reloaded.booking.notes, "outer transaction survived")

        asyncio.run(scenario())

    def test_rebooking_excludes_delivered_lines_and_recopies_cancelled_lines(self):
        async def scenario():
            async with self.session_factory() as session:
                sheet_id, _ = await self._make_sheet_with_line(session)
                costing = CostingService(session)
                sheet = await costing.get_workbench(sheet_id)
                await costing.create_line(
                    sheet_id,
                    ServiceLineCreateSchema(
                        base_costing_revision=sheet.sheet.costing_revision,
                        day_number=2,
                        service_date=date(2026, 7, 16),
                        category="transportation",
                        title="Airport transfer",
                        unit="vehicle",
                        time_basis="trip",
                        unit_cost_minor=200_000,
                        cost_currency="USD",
                    ),
                    actor=ACTOR,
                    idempotency_key="rebook-line-2",
                )
                service = BookingService(session)
                first = await service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR, idempotency_key="rebook-first", today=date(2026, 6, 1),
                )
                revision = first.booking.booking_revision
                delivered_line_id = first.lines[0].id
                for index, target in enumerate(("requested", "confirmed", "delivered")):
                    transitioned = await service.transition_line(
                        first.booking.id,
                        delivered_line_id,
                        BookingLineTransitionSchema(base_booking_revision=revision, to=target),
                        actor=ACTOR, idempotency_key=f"rebook-transition-{index}", today=date(2026, 6, 2 + index),
                    )
                    revision = transitioned.booking.booking_revision
                await service.cancel_booking(
                    first.booking.id,
                    BookingCancelSchema(base_booking_revision=revision, reason="rebook remaining services"),
                    actor=ACTOR, today=date(2026, 6, 6),
                )
                await session.commit()
                second = await service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 7)),
                    actor=ACTOR, idempotency_key="rebook-second", today=date(2026, 6, 7),
                )
                self.assertEqual(len(second.lines), 1)
                self.assertNotEqual(second.lines[0].source_service_line_id, first.lines[0].source_service_line_id)

        asyncio.run(scenario())

    def test_finance_readiness_events_are_self_standing_and_bulk_cancel_respects_terminal_lines(self):
        """Mốc A (Finance readiness audit 2026-08-31):

        - booking.line.confirmed / .delivered payloads must let a future Finance consumer
          originate a payable without joining back (supplier, cost total, currency, voucher).
        - Header-level cancel must compute per-line penalties from FROZEN policy, skip
          delivered lines (terminal), and emit booking.cancelled with a penalty summary.
        """

        async def scenario():
            from sqlalchemy import select

            from db.models.outbox import OutboxEvent
            from schemas.v2.booking import BookingCancelSchema
            from schemas.v2.costing import ServiceLineCreateSchema as LineSchema

            async with self.session_factory() as session:
                sheet_id, _ = await self._make_sheet_with_line(session)
                costing = CostingService(session)
                sheet = await costing.get_workbench(sheet_id)
                await costing.create_line(
                    sheet_id,
                    LineSchema(
                        base_costing_revision=sheet.sheet.costing_revision,
                        day_number=2,
                        service_date=date(2026, 7, 16),
                        category="transportation",
                        title="Xe 16 chỗ HN-HL",
                        supplier_id="sup_la_siesta",
                        unit="vehicle",
                        time_basis="day",
                        unit_cost_minor=500_000,
                        cost_currency="USD",
                        qty_unit=1,
                        qty_time=1,
                    ),
                    actor=ACTOR,
                    idempotency_key="line-2",
                )
                await session.commit()

                booking_service = BookingService(session)
                detail = await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="c-fin",
                    today=date(2026, 6, 1),
                )
                await session.commit()
                booking_id = detail.booking.id
                line_a, line_b = detail.lines[0].id, detail.lines[1].id

                # Line A: to_request → requested → confirmed → delivered
                revision = detail.booking.booking_revision
                for idx, target in enumerate(("requested", "confirmed", "delivered")):
                    result = await booking_service.transition_line(
                        booking_id,
                        line_a,
                        BookingLineTransitionSchema(base_booking_revision=revision, to=target),
                        actor=ACTOR,
                        idempotency_key=f"fin-t{idx}",
                        today=date(2026, 6, 2 + idx),
                    )
                    await session.commit()
                    revision = result.booking.booking_revision

                events = (await session.execute(select(OutboxEvent))).scalars().all()
                confirmed = next(e for e in events if e.event_type == "booking.line.confirmed")
                delivered = next(e for e in events if e.event_type == "booking.line.delivered")
                for payload in (confirmed.payload_json, delivered.payload_json):
                    # Arrange/Assert: self-standing payable payload — no join-back needed.
                    self.assertEqual(payload["supplier_id"], "sup_la_siesta")
                    self.assertEqual(payload["cost_total_minor"], 2_000_000)  # 2 rooms × 1_000_000
                    self.assertEqual(payload["cost_currency"], "USD")
                    self.assertEqual(payload["quotation_id"], "qtn_bk1")
                    self.assertTrue(payload["booking_code"].startswith("BK-"))
                self.assertTrue(delivered.payload_json["voucher_ref"].startswith("VC-"))

                # Bulk cancel on 2026-07-06: line B serves 2026-07-16 → 10 days remaining,
                # inside the 14-day tier → 25% penalty.
                cancelled_detail = await booking_service.cancel_booking(
                    booking_id,
                    BookingCancelSchema(base_booking_revision=revision, reason="Khách hủy đoàn"),
                    actor=ACTOR,
                    today=date(2026, 7, 6),
                )
                await session.commit()

                by_id = {line.id: line for line in cancelled_detail.lines}
                self.assertEqual(by_id[line_a].status, "delivered")  # terminal — untouched
                self.assertEqual(by_id[line_b].status, "cancelled")
                self.assertEqual(by_id[line_b].cancel_penalty_minor, 125_000)  # 25% × 500_000

                events = (await session.execute(select(OutboxEvent))).scalars().all()
                header_event = next(e for e in events if e.event_type == "booking.cancelled")
                self.assertEqual(header_event.payload_json["penalty_total_minor"], 125_000)
                self.assertEqual(len(header_event.payload_json["lines"]), 1)  # delivered line excluded

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
