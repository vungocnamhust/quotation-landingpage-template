import asyncio
import os
import tempfile
import unittest
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.kernel import ActorRef
from db.base import Base
from db.models.booking import BookingLine
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from repositories.quote_request_repository import QuoteRequestRepository
from repositories.quotation_repository import QuotationRepository
from schemas.v2.booking import BookingCreateSchema, BookingLineTransitionSchema
from schemas.v2.costing import CostingSheetCreateSchema, ServiceLineCreateSchema
from schemas.v2.finance_ap import (
    LineActionRequestSchema,
    MatchLineRequestSchema,
    PaymentAllocationInputSchema,
    RecordPaymentRequestSchema,
    SupplierInvoiceCreateSchema,
    SupplierInvoiceLineWriteSchema,
    SupplierInvoiceLinesUpsertSchema,
    SupplierInvoiceUpdateSchema,
    ApproveInvoiceRequestSchema,
)
from services.ap_reconciliation_service import ApReconciliationService, APConflictError, APValidationError
from services.booking_service import BookingService
from services.costing_service import CostingService

ACTOR = ActorRef(actor_id="finance@example.com", actor_type="staff")


class ApReconciliationServiceTests(unittest.TestCase):
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
                    credit_terms_days=30,
                )
            )
            await session.commit()
            await QuoteRequestRepository(session).create_request(
                role="customer", customer_name="Jane Doe", email="jane@example.com", request_id="req_ap1"
            )
            await session.commit()
            await QuotationRepository(session).create_quotation(
                quotation_id="qtn_ap1", brand_id="brand_capella", template_name="quote-generator", baseline_lang="en"
            )
            await session.commit()

    async def _confirmed_booking_line(
        self, session, *, unit_cost_minor=1_000_000, qty_unit=2, qty_time=1, cancel=False
    ) -> BookingLine:
        """Real chain: costing sheet -> line -> booking -> requested -> confirmed (mints voucher_ref)."""
        costing = CostingService(session)
        sheet = await costing.create_sheet(CostingSheetCreateSchema(quotation_id="qtn_ap1", currency="USD"), actor=ACTOR)
        await session.commit()
        await costing.create_line(
            sheet.id,
            ServiceLineCreateSchema(
                base_costing_revision=sheet.costing_revision,
                day_number=1,
                service_date=date(2026, 7, 15),
                category="accommodation",
                title="La Siesta — Deluxe Room",
                supplier_id="sup_la_siesta",
                unit="room",
                time_basis="night",
                unit_cost_minor=unit_cost_minor,
                cost_currency="USD",
                qty_unit=qty_unit,
                qty_time=qty_time,
            ),
            actor=ACTOR,
            idempotency_key="line-1",
        )
        await session.commit()

        booking_service = BookingService(session)
        detail = await booking_service.create_booking(
            BookingCreateSchema(quotation_id="qtn_ap1", deposit_received_at=date(2026, 6, 1)),
            actor=ACTOR,
            idempotency_key="create-1",
            today=date(2026, 6, 1),
        )
        await session.commit()
        booking_id = detail.booking.id
        line_id = detail.lines[0].id
        revision = detail.booking.booking_revision

        detail = await booking_service.transition_line(
            booking_id,
            line_id,
            BookingLineTransitionSchema(base_booking_revision=revision, to="requested"),
            actor=ACTOR,
            idempotency_key="t-requested",
            today=date(2026, 6, 1),
        )
        await session.commit()
        detail = await booking_service.transition_line(
            booking_id,
            line_id,
            BookingLineTransitionSchema(base_booking_revision=detail.booking.booking_revision, to="confirmed"),
            actor=ACTOR,
            idempotency_key="t-confirmed",
            today=date(2026, 6, 1),
        )
        await session.commit()

        if cancel:
            detail = await booking_service.transition_line(
                booking_id,
                line_id,
                BookingLineTransitionSchema(
                    base_booking_revision=detail.booking.booking_revision, to="cancelled", cancel_reason="Client changed plans"
                ),
                actor=ACTOR,
                idempotency_key="t-cancelled",
                today=date(2026, 6, 1),
            )
            await session.commit()

        result = await session.execute(select(BookingLine).where(BookingLine.id == line_id))
        return result.scalar_one()

    async def _snapshot_booking_lines(self, session) -> list[dict]:
        result = await session.execute(select(BookingLine))
        return [
            {c.name: getattr(row, c.name) for c in BookingLine.__table__.columns}
            for row in result.scalars().all()
        ]

    # --------------------------------------------------------------- happy path

    def test_full_flow_exact_auto_match_through_paid(self):
        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                before = await self._snapshot_booking_lines(session)

                ap = ApReconciliationService(session)
                invoice = await ap.create_invoice(
                    SupplierInvoiceCreateSchema(
                        supplier_id="sup_la_siesta",
                        invoice_date=date(2026, 6, 20),
                        currency="USD",
                        gross_total_minor=2_000_000,
                    ),
                    actor=ACTOR,
                    idempotency_key="inv-1",
                )
                await session.commit()
                self.assertEqual(invoice.status, "draft")

                invoice = await ap.update_header(
                    invoice.id,
                    SupplierInvoiceUpdateSchema(base_invoice_revision=invoice.invoice_revision, action="record"),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(invoice.status, "received")

                invoice = await ap.upsert_lines(
                    invoice.id,
                    SupplierInvoiceLinesUpsertSchema(
                        base_invoice_revision=invoice.invoice_revision,
                        lines=[
                            SupplierInvoiceLineWriteSchema(
                                line_type="service", description="Room x2 nights", amount_minor=2_000_000
                            )
                        ],
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                line = invoice.lines[0]

                invoice = await ap.match_line(
                    invoice.id,
                    line.id,
                    MatchLineRequestSchema(
                        base_invoice_revision=invoice.invoice_revision, mode="auto", voucher_ref=booking_line.voucher_ref
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(invoice.status, "matched")
                self.assertEqual(invoice.lines[0].match_status, "auto_matched")
                self.assertEqual(invoice.lines[0].variance_minor, 0)

                invoice = await ap.approve(
                    invoice.id, ApproveInvoiceRequestSchema(base_invoice_revision=invoice.invoice_revision), actor=ACTOR
                )
                await session.commit()
                self.assertEqual(invoice.status, "approved")

                payment = await ap.record_payment(
                    RecordPaymentRequestSchema(
                        supplier_id="sup_la_siesta",
                        paid_at=date(2026, 6, 25),
                        currency="USD",
                        amount_minor=2_000_000,
                        method="bank_transfer",
                        allocations=[PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=2_000_000)],
                    ),
                    actor=ACTOR,
                    idempotency_key="pay-1",
                )
                await session.commit()
                self.assertTrue(payment.payment_code.startswith("PV-"))

                final_invoice = await ap.get_invoice(invoice.id)
                self.assertEqual(final_invoice.status, "paid")
                self.assertEqual(final_invoice.balance_minor, 0)

                after = await self._snapshot_booking_lines(session)
                self.assertEqual(before, after)  # zero-touch (chốt #1)

        asyncio.run(scenario())

    def test_create_invoice_is_idempotent(self):
        async def scenario():
            async with self.session_factory() as session:
                ap = ApReconciliationService(session)
                payload = SupplierInvoiceCreateSchema(
                    supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency="USD", gross_total_minor=1_000
                )
                first = await ap.create_invoice(payload, actor=ACTOR, idempotency_key="dup-key")
                await session.commit()
                second = await ap.create_invoice(payload, actor=ACTOR, idempotency_key="dup-key")
                await session.commit()
                self.assertEqual(first.id, second.id)

        asyncio.run(scenario())

    def test_double_billing_is_blocked_by_constraint(self):
        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)

                async def _received_invoice_with_line(idem: str) -> tuple:
                    invoice = await ap.create_invoice(
                        SupplierInvoiceCreateSchema(
                            supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency="USD", gross_total_minor=2_000_000
                        ),
                        actor=ACTOR,
                        idempotency_key=idem,
                    )
                    await session.commit()
                    invoice = await ap.update_header(
                        invoice.id, SupplierInvoiceUpdateSchema(base_invoice_revision=invoice.invoice_revision, action="record"), actor=ACTOR
                    )
                    await session.commit()
                    invoice = await ap.upsert_lines(
                        invoice.id,
                        SupplierInvoiceLinesUpsertSchema(
                            base_invoice_revision=invoice.invoice_revision,
                            lines=[SupplierInvoiceLineWriteSchema(line_type="service", description="Room", amount_minor=2_000_000)],
                        ),
                        actor=ACTOR,
                    )
                    await session.commit()
                    return invoice, invoice.lines[0]

                invoice_a, line_a = await _received_invoice_with_line("dbA")
                invoice_b, line_b = await _received_invoice_with_line("dbB")

                invoice_a = await ap.match_line(
                    invoice_a.id,
                    line_a.id,
                    MatchLineRequestSchema(base_invoice_revision=invoice_a.invoice_revision, mode="auto", voucher_ref=booking_line.voucher_ref),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(invoice_a.lines[0].match_status, "auto_matched")

            # Fresh session for the conflicting attempt — mirrors one-session-per-request in prod,
            # and keeps the IntegrityError's rollback from leaking into the first session's state.
            async with self.session_factory() as session2:
                ap2 = ApReconciliationService(session2)
                with self.assertRaises(APConflictError):
                    await ap2.match_line(
                        invoice_b.id,
                        line_b.id,
                        MatchLineRequestSchema(
                            base_invoice_revision=invoice_b.invoice_revision, mode="manual", voucher_ref=booking_line.voucher_ref
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_stale_revision_raises_conflict(self):
        async def scenario():
            async with self.session_factory() as session:
                ap = ApReconciliationService(session)
                invoice = await ap.create_invoice(
                    SupplierInvoiceCreateSchema(
                        supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency="USD", gross_total_minor=1_000
                    ),
                    actor=ACTOR,
                    idempotency_key=None,
                )
                await session.commit()
                with self.assertRaises(APConflictError):
                    await ap.update_header(
                        invoice.id,
                        SupplierInvoiceUpdateSchema(base_invoice_revision=invoice.invoice_revision + 1, action="record"),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_dispute_propagates_to_invoice_and_resolves_back(self):
        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await ap.create_invoice(
                    SupplierInvoiceCreateSchema(
                        supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency="USD", gross_total_minor=2_000_000
                    ),
                    actor=ACTOR,
                    idempotency_key=None,
                )
                await session.commit()
                invoice = await ap.update_header(
                    invoice.id, SupplierInvoiceUpdateSchema(base_invoice_revision=invoice.invoice_revision, action="record"), actor=ACTOR
                )
                await session.commit()
                invoice = await ap.upsert_lines(
                    invoice.id,
                    SupplierInvoiceLinesUpsertSchema(
                        base_invoice_revision=invoice.invoice_revision,
                        lines=[SupplierInvoiceLineWriteSchema(line_type="service", description="Room", amount_minor=2_000_000)],
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                line = invoice.lines[0]

                invoice = await ap.match_line(
                    invoice.id,
                    line.id,
                    MatchLineRequestSchema(base_invoice_revision=invoice.invoice_revision, mode="auto", voucher_ref=booking_line.voucher_ref),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(invoice.status, "matched")

                invoice = await ap.line_action(
                    invoice.id,
                    invoice.lines[0].id,
                    "dispute",
                    LineActionRequestSchema(base_invoice_revision=invoice.invoice_revision, note="Price looks wrong"),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(invoice.status, "disputed")
                self.assertEqual(invoice.lines[0].match_status, "disputed")

                invoice = await ap.line_action(
                    invoice.id,
                    invoice.lines[0].id,
                    "waive",
                    LineActionRequestSchema(base_invoice_revision=invoice.invoice_revision, note="Confirmed correct, waiving"),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(invoice.status, "matched")

                with self.assertRaises(APValidationError):
                    await ap.line_action(
                        invoice.id,
                        invoice.lines[0].id,
                        "waive",
                        LineActionRequestSchema(base_invoice_revision=invoice.invoice_revision, note=None),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_approve_blocked_while_unmatched(self):
        async def scenario():
            async with self.session_factory() as session:
                ap = ApReconciliationService(session)
                invoice = await ap.create_invoice(
                    SupplierInvoiceCreateSchema(
                        supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency="USD", gross_total_minor=2_000_000
                    ),
                    actor=ACTOR,
                    idempotency_key=None,
                )
                await session.commit()
                invoice = await ap.update_header(
                    invoice.id, SupplierInvoiceUpdateSchema(base_invoice_revision=invoice.invoice_revision, action="record"), actor=ACTOR
                )
                await session.commit()
                invoice = await ap.upsert_lines(
                    invoice.id,
                    SupplierInvoiceLinesUpsertSchema(
                        base_invoice_revision=invoice.invoice_revision,
                        lines=[SupplierInvoiceLineWriteSchema(line_type="service", description="Room", amount_minor=2_000_000)],
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                with self.assertRaises(APValidationError):
                    await ap.approve(invoice.id, ApproveInvoiceRequestSchema(base_invoice_revision=invoice.invoice_revision), actor=ACTOR)

        asyncio.run(scenario())

    def test_penalty_currency_guard_blocks_when_mismatched(self):
        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session, cancel=True)
                self.assertIsNotNone(booking_line.cancel_penalty_minor)
                ap = ApReconciliationService(session)
                invoice = await ap.create_invoice(
                    SupplierInvoiceCreateSchema(
                        supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency="VND", gross_total_minor=100_000
                    ),
                    actor=ACTOR,
                    idempotency_key=None,
                )
                await session.commit()
                invoice = await ap.update_header(
                    invoice.id, SupplierInvoiceUpdateSchema(base_invoice_revision=invoice.invoice_revision, action="record"), actor=ACTOR
                )
                await session.commit()
                invoice = await ap.upsert_lines(
                    invoice.id,
                    SupplierInvoiceLinesUpsertSchema(
                        base_invoice_revision=invoice.invoice_revision,
                        lines=[
                            SupplierInvoiceLineWriteSchema(line_type="penalty", description="Cancellation fee", amount_minor=100_000)
                        ],
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                line = invoice.lines[0]

                # Sheet currency is USD (booking's costing sheet), invoice currency is VND -> guard fires.
                invoice = await ap.match_line(
                    invoice.id,
                    line.id,
                    MatchLineRequestSchema(
                        base_invoice_revision=invoice.invoice_revision, mode="manual", voucher_ref=booking_line.voucher_ref
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                matched_line = invoice.lines[0]
                self.assertEqual(matched_line.match_status, "manual_matched")
                self.assertIsNone(matched_line.expected_cost_minor)
                self.assertIn("PENALTY_CURRENCY_UNCOMPARABLE", matched_line.match_issues_json)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
