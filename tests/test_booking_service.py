import asyncio
import os
import tempfile
import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.kernel import ActorRef
from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from repositories.quote_request_repository import QuoteRequestRepository
from repositories.quotation_repository import QuotationRepository
from repositories.supplier_repository import SupplierRepository
from schemas.v2.booking import (
    BookingAddLineSchema,
    BookingCancelSchema,
    BookingCreateSchema,
    BookingLineTransitionSchema,
)
from schemas.v2.costing import CostingSheetCreateSchema, ServiceLineCreateSchema
from services.booking_service import BookingConflictError, BookingService
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


class BookingServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
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
            await QuotationRepository(session).create_quotation(
                quotation_id="qtn_bk1", brand_id="brand_capella", template_name="quote-generator", baseline_lang="en"
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
                booking_service = BookingService(session)
                await booking_service.create_booking(
                    BookingCreateSchema(quotation_id="qtn_bk1", deposit_received_at=date(2026, 6, 1)),
                    actor=ACTOR,
                    idempotency_key="create-mirror",
                    today=date(2026, 6, 1),
                )
                await session.commit()

                costing = CostingService(session)
                workbench = await costing.get_workbench(sheet_id)
                self.assertEqual(workbench.items[0].booking_status, "to_request")

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


if __name__ == "__main__":
    unittest.main()
