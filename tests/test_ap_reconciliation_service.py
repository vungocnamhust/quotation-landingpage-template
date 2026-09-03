import asyncio
import os
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

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
from repositories.supplier_invoice_repository import SupplierInvoiceRevisionRaceError
from services.ap_reconciliation_service import ApReconciliationService, APConflictError, APValidationError
from services.booking_service import BookingService
from services.costing_service import CostingService

ACTOR = ActorRef(actor_id="finance@example.com", actor_type="staff")


class ApReconciliationServiceTests(unittest.TestCase):
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
        self,
        session,
        *,
        quotation_id="qtn_ap1",
        sheet_currency="USD",
        cost_currency="USD",
        unit_cost_minor=1_000_000,
        qty_unit=2,
        qty_time=1,
        cancel=False,
        idem_suffix="",
    ) -> BookingLine:
        """Real chain: costing sheet -> line -> booking -> requested -> confirmed (mints voucher_ref)."""
        costing = CostingService(session)
        sheet = await costing.create_sheet(CostingSheetCreateSchema(quotation_id=quotation_id, currency=sheet_currency), actor=ACTOR)
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
                cost_currency=cost_currency,
                qty_unit=qty_unit,
                qty_time=qty_time,
            ),
            actor=ACTOR,
            idempotency_key=f"line-1{idem_suffix}",
        )
        await session.commit()

        booking_service = BookingService(session)
        detail = await booking_service.create_booking(
            BookingCreateSchema(quotation_id=quotation_id, deposit_received_at=date(2026, 6, 1)),
            actor=ACTOR,
            idempotency_key=f"create-1{idem_suffix}",
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
            idempotency_key=f"t-requested{idem_suffix}",
            today=date(2026, 6, 1),
        )
        await session.commit()
        detail = await booking_service.transition_line(
            booking_id,
            line_id,
            BookingLineTransitionSchema(base_booking_revision=detail.booking.booking_revision, to="confirmed"),
            actor=ACTOR,
            idempotency_key=f"t-confirmed{idem_suffix}",
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
                idempotency_key=f"t-cancelled{idem_suffix}",
                today=date(2026, 6, 1),
            )
            await session.commit()

        result = await session.execute(select(BookingLine).where(BookingLine.id == line_id))
        return result.scalar_one()

    async def _approved_invoice(
        self, ap: ApReconciliationService, booking_line: BookingLine, session, *, currency="USD", gross_total_minor=2_000_000, idem=""
    ):
        """Create -> record -> line -> auto-match -> approve, in one shot (shared fixture for §12 tests)."""
        invoice = await ap.create_invoice(
            SupplierInvoiceCreateSchema(
                supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency=currency, gross_total_minor=gross_total_minor
            ),
            actor=ACTOR,
            idempotency_key=f"inv-approved{idem}",
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
                lines=[SupplierInvoiceLineWriteSchema(line_type="service", description="Room", amount_minor=gross_total_minor)],
            ),
            actor=ACTOR,
        )
        await session.commit()
        invoice = await ap.match_line(
            invoice.id,
            invoice.lines[0].id,
            MatchLineRequestSchema(base_invoice_revision=invoice.invoice_revision, mode="auto", voucher_ref=booking_line.voucher_ref),
            actor=ACTOR,
        )
        await session.commit()
        invoice = await ap.approve(invoice.id, ApproveInvoiceRequestSchema(base_invoice_revision=invoice.invoice_revision), actor=ACTOR)
        await session.commit()
        return invoice

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


    # ------------------------------------------------------------------- §12 audit fixes

    def test_c1_cross_supplier_allocation_is_rejected(self):
        """§12.1 C1 — a payment cannot allocate to an invoice belonging to another supplier."""

        async def scenario():
            async with self.session_factory() as session:
                session.add(
                    Supplier(
                        id="sup_other",
                        name="Other Supplier Co",
                        name_normalized="other supplier co",
                        supplier_type="direct",
                        default_currency="USD",
                        credit_terms_days=30,
                    )
                )
                await session.commit()

                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await self._approved_invoice(ap, booking_line, session)

                with self.assertRaises(APValidationError) as ctx:
                    await ap.record_payment(
                        RecordPaymentRequestSchema(
                            supplier_id="sup_other",
                            paid_at=date(2026, 6, 25),
                            currency="USD",
                            amount_minor=2_000_000,
                            method="bank_transfer",
                            allocations=[PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=2_000_000)],
                        ),
                        actor=ACTOR,
                        idempotency_key="c1-cross-supplier",
                    )
                message = str(ctx.exception)
                self.assertIn("sup_la_siesta", message)
                self.assertIn("sup_other", message)

        asyncio.run(scenario())

    def test_h1_reversal_happy_path_and_gate(self):
        """§12.2 H1 — a valid reversal still goes through the (mirrored) gate."""

        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await self._approved_invoice(ap, booking_line, session)

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
                    idempotency_key="h1-forward",
                )
                await session.commit()
                self.assertEqual(payment.amount_minor, 2_000_000)

                reversal = await ap.record_payment(
                    RecordPaymentRequestSchema(
                        supplier_id="sup_la_siesta",
                        paid_at=date(2026, 6, 26),
                        currency="USD",
                        amount_minor=-2_000_000,
                        method="bank_transfer",
                        reference="UNC-REVERSE-1",
                        notes="Wrong invoice, reversing",
                        allocations=[PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=-2_000_000)],
                    ),
                    actor=ACTOR,
                    idempotency_key="h1-reversal",
                )
                await session.commit()
                self.assertEqual(reversal.amount_minor, -2_000_000)

                # Reversing again exceeds what's now paid (0) -> blocked, not silently allowed.
                with self.assertRaises(APValidationError):
                    await ap.record_payment(
                        RecordPaymentRequestSchema(
                            supplier_id="sup_la_siesta",
                            paid_at=date(2026, 6, 27),
                            currency="USD",
                            amount_minor=-1,
                            method="bank_transfer",
                            reference="UNC-REVERSE-2",
                            notes="Should be blocked",
                            allocations=[PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=-1)],
                        ),
                        actor=ACTOR,
                        idempotency_key="h1-reversal-2",
                    )

        asyncio.run(scenario())

    def test_h1_reversal_requires_reference_and_notes(self):
        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await self._approved_invoice(ap, booking_line, session)
                await ap.record_payment(
                    RecordPaymentRequestSchema(
                        supplier_id="sup_la_siesta",
                        paid_at=date(2026, 6, 25),
                        currency="USD",
                        amount_minor=2_000_000,
                        method="bank_transfer",
                        allocations=[PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=2_000_000)],
                    ),
                    actor=ACTOR,
                    idempotency_key="h1-forward-2",
                )
                await session.commit()

                with self.assertRaises(APValidationError):
                    await ap.record_payment(
                        RecordPaymentRequestSchema(
                            supplier_id="sup_la_siesta",
                            paid_at=date(2026, 6, 26),
                            currency="USD",
                            amount_minor=-100,
                            method="bank_transfer",
                            allocations=[PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=-100)],
                        ),
                        actor=ACTOR,
                        idempotency_key="h1-no-ref",
                    )

        asyncio.run(scenario())

    def test_h2_mixed_sign_allocation_is_blocked_both_directions(self):
        """§12.3 H2 — a positive payment can't sneak a negative allocation past the sum check,
        and a negative (reversal) payment can't sneak a positive one."""

        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await self._approved_invoice(ap, booking_line, session)

                with self.assertRaises(APValidationError):
                    await ap.record_payment(
                        RecordPaymentRequestSchema(
                            supplier_id="sup_la_siesta",
                            paid_at=date(2026, 6, 25),
                            currency="USD",
                            amount_minor=100,
                            method="bank_transfer",
                            allocations=[
                                PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=150),
                                PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=-50),
                            ],
                        ),
                        actor=ACTOR,
                        idempotency_key="h2-positive-mixed",
                    )

                await ap.record_payment(
                    RecordPaymentRequestSchema(
                        supplier_id="sup_la_siesta",
                        paid_at=date(2026, 6, 25),
                        currency="USD",
                        amount_minor=2_000_000,
                        method="bank_transfer",
                        allocations=[PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=2_000_000)],
                    ),
                    actor=ACTOR,
                    idempotency_key="h2-fund-forward",
                )
                await session.commit()

                with self.assertRaises(APValidationError):
                    await ap.record_payment(
                        RecordPaymentRequestSchema(
                            supplier_id="sup_la_siesta",
                            paid_at=date(2026, 6, 26),
                            currency="USD",
                            amount_minor=-100,
                            method="bank_transfer",
                            reference="UNC-1",
                            notes="mixed",
                            allocations=[
                                PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=-150),
                                PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=50),
                            ],
                        ),
                        actor=ACTOR,
                        idempotency_key="h2-negative-mixed",
                    )

        asyncio.run(scenario())

    def test_h2_schema_rejects_zero_allocation(self):
        with self.assertRaises(Exception):
            PaymentAllocationInputSchema(invoice_id="inv_1", amount_minor=0)

    def test_h3_unresolved_sheet_currency_fails_explicit(self):
        """§12.4 H3 — no live booking/sheet to resolve -> SHEET_CURRENCY_UNRESOLVED, not a
        silent fallback that disables the F2 guard."""

        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session, cancel=True)
                self.assertIsNotNone(booking_line.cancel_penalty_minor)
                ap = ApReconciliationService(session)

                # Delete the booking's costing sheet out from under the booking line — the
                # simplest way to force `_sheet_currency_for_booking_line` to legitimately fail.
                sheet = await ap.costing_repository.get_sheet_by_id(
                    (await ap.booking_repository.get_booking_by_id(booking_line.booking_id)).sheet_id
                )

                invoice = await ap.create_invoice(
                    SupplierInvoiceCreateSchema(
                        supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency="USD", gross_total_minor=100_000
                    ),
                    actor=ACTOR,
                    idempotency_key="h3-inv",
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
                        lines=[SupplierInvoiceLineWriteSchema(line_type="penalty", description="Cancellation fee", amount_minor=100_000)],
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                async def _resolve_none(_booking_line):
                    return None

                with patch.object(ap, "_sheet_currency_for_booking_line", side_effect=_resolve_none):
                    invoice = await ap.match_line(
                        invoice.id,
                        invoice.lines[0].id,
                        MatchLineRequestSchema(
                            base_invoice_revision=invoice.invoice_revision, mode="manual", voucher_ref=booking_line.voucher_ref
                        ),
                        actor=ACTOR,
                    )
                await session.commit()
                matched_line = invoice.lines[0]
                self.assertEqual(matched_line.match_status, "manual_matched")
                self.assertIsNone(matched_line.expected_cost_minor)
                self.assertIn("SHEET_CURRENCY_UNRESOLVED", matched_line.match_issues_json)
                self.assertIsNotNone(sheet)  # sheet genuinely existed; the patch simulated the lookup failing

        asyncio.run(scenario())

    def test_h4_multi_sheet_currency_payment_is_rejected(self):
        """§12.5 H4 — one payment can't allocate across invoices whose bookings sit on
        different sheet currencies."""

        async def scenario():
            async with self.session_factory() as session:
                await QuotationRepository(session).create_quotation(
                    quotation_id="qtn_ap2", brand_id="brand_capella", template_name="quote-generator", baseline_lang="en"
                )
                await session.commit()

                booking_line_usd = await self._confirmed_booking_line(
                    session, quotation_id="qtn_ap1", sheet_currency="USD", cost_currency="USD", idem_suffix="-usd"
                )
                booking_line_vnd = await self._confirmed_booking_line(
                    session, quotation_id="qtn_ap2", sheet_currency="VND", cost_currency="VND", idem_suffix="-vnd"
                )

                ap = ApReconciliationService(session)
                invoice_usd = await self._approved_invoice(ap, booking_line_usd, session, currency="USD", idem="-usd")
                invoice_vnd = await self._approved_invoice(ap, booking_line_vnd, session, currency="VND", idem="-vnd")

                with self.assertRaises(APValidationError) as ctx:
                    await ap.record_payment(
                        RecordPaymentRequestSchema(
                            supplier_id="sup_la_siesta",
                            paid_at=date(2026, 6, 25),
                            currency="USD",
                            amount_minor=4_000_000,
                            method="bank_transfer",
                            allocations=[
                                PaymentAllocationInputSchema(invoice_id=invoice_usd.id, amount_minor=2_000_000),
                                PaymentAllocationInputSchema(invoice_id=invoice_vnd.id, amount_minor=2_000_000),
                            ],
                        ),
                        actor=ACTOR,
                        idempotency_key="h4-multi-sheet",
                    )
                detail = ctx.exception.args[0]
                self.assertEqual(detail["code"], "FX_MULTI_SHEET_CURRENCY")

        asyncio.run(scenario())

    def test_h4_fx_variance_is_computed_for_single_sheet_currency(self):
        """§12.5 H4 — with one sheet currency, fx_variance_sheet_minor is computed and
        returned on the allocation (identity ppm both sides -> zero variance here)."""

        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await self._approved_invoice(ap, booking_line, session)

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
                    idempotency_key="h4-fx-variance",
                )
                self.assertEqual(len(payment.allocations), 1)
                self.assertEqual(payment.allocations[0].fx_variance_sheet_minor, 0)

        asyncio.run(scenario())

    def test_m1_create_invoice_race_replays_the_winner(self):
        """§12.6 M1 — the loser of an idempotency-key race re-fetches and replays the row that
        actually landed, instead of surfacing a spurious 409."""

        async def scenario():
            payload = SupplierInvoiceCreateSchema(
                supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency="USD", gross_total_minor=5_000
            )
            async with self.session_factory() as session1, self.session_factory() as session2:
                ap1 = ApReconciliationService(session1)
                ap2 = ApReconciliationService(session2)

                # Both sessions miss the early idempotency-key lookup (neither has committed yet).
                winner = await ap1.create_invoice(payload, actor=ACTOR, idempotency_key="m1-race")
                await session1.commit()

                # session2 still holds a pre-commit view; force its *first* idempotency-key
                # lookup to miss (simulating arriving just before session1's commit was
                # visible), then let every later call through to the real repository so the
                # except-block's fallback re-fetch actually sees the winner.
                real_lookup = ap2.repository.get_invoice_by_idempotency_key
                call_count = {"n": 0}

                async def flaky_lookup(key, **kwargs):
                    call_count["n"] += 1
                    if call_count["n"] == 1:
                        return None
                    return await real_lookup(key, **kwargs)

                with patch.object(ap2.repository, "get_invoice_by_idempotency_key", side_effect=flaky_lookup):
                    loser_result = await ap2.create_invoice(payload, actor=ACTOR, idempotency_key="m1-race")

                self.assertEqual(loser_result.id, winner.id)

        asyncio.run(scenario())

    def test_m2_mark_paid_race_surfaces_as_conflict(self):
        """§12.6 M2 — a lost revision race while deriving 'paid' status becomes a 409, not an
        unhandled 500 (and rolls the whole payment back, since nothing has committed yet)."""

        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await self._approved_invoice(ap, booking_line, session)

                real_update_header = ap.repository.update_header

                async def flaky_update_header(inv, *, values, expected_revision):
                    if values.get("status") == "paid":
                        raise SupplierInvoiceRevisionRaceError(inv.id, expected_revision)
                    return await real_update_header(inv, values=values, expected_revision=expected_revision)

                with patch.object(ap.repository, "update_header", side_effect=flaky_update_header):
                    with self.assertRaises(APConflictError):
                        await ap.record_payment(
                            RecordPaymentRequestSchema(
                                supplier_id="sup_la_siesta",
                                paid_at=date(2026, 6, 25),
                                currency="USD",
                                amount_minor=2_000_000,
                                method="bank_transfer",
                                allocations=[PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=2_000_000)],
                            ),
                            actor=ACTOR,
                            idempotency_key="m2-race",
                        )

                # Nothing committed -> rolling back discards the flushed-but-uncommitted
                # payment insert; a plain retry (same Idempotency-Key) would re-run cleanly
                # from scratch instead of double-paying.
                await session.rollback()
                self.assertIsNone(await ap.repository.get_payment_by_idempotency_key("m2-race"))

        asyncio.run(scenario())

    def test_m3_currency_locked_after_line_matched(self):
        """§12.6 M3 — currency can't change once a line has been matched/waived/disputed
        (CS1 precedent)."""

        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await ap.create_invoice(
                    SupplierInvoiceCreateSchema(
                        supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency="USD", gross_total_minor=2_000_000
                    ),
                    actor=ACTOR,
                    idempotency_key="m3-inv",
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
                invoice = await ap.match_line(
                    invoice.id,
                    invoice.lines[0].id,
                    MatchLineRequestSchema(base_invoice_revision=invoice.invoice_revision, mode="auto", voucher_ref=booking_line.voucher_ref),
                    actor=ACTOR,
                )
                await session.commit()

                with self.assertRaises(APConflictError):
                    await ap.update_header(
                        invoice.id,
                        SupplierInvoiceUpdateSchema(base_invoice_revision=invoice.invoice_revision, currency="VND"),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    # ------------------------------------------------------------------- §12.7 test debt

    def test_line_mutation_blocked_after_approve(self):
        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await self._approved_invoice(ap, booking_line, session)

                with self.assertRaises(APValidationError):
                    await ap.line_action(
                        invoice.id,
                        invoice.lines[0].id,
                        "unmatch",
                        LineActionRequestSchema(base_invoice_revision=invoice.invoice_revision),
                        actor=ACTOR,
                    )
                with self.assertRaises(APValidationError):
                    await ap.match_line(
                        invoice.id,
                        invoice.lines[0].id,
                        MatchLineRequestSchema(base_invoice_revision=invoice.invoice_revision, mode="manual", voucher_ref="VC-0000-0000"),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_snapshot_is_immobile_after_supplier_policy_changes(self):
        """Supersede: editing the supplier's live data after match must not move the invoice
        line's already-snapshotted expected/variance."""

        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await ap.create_invoice(
                    SupplierInvoiceCreateSchema(
                        supplier_id="sup_la_siesta", invoice_date=date(2026, 6, 20), currency="USD", gross_total_minor=2_000_000
                    ),
                    actor=ACTOR,
                    idempotency_key="supersede-inv",
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
                invoice = await ap.match_line(
                    invoice.id,
                    invoice.lines[0].id,
                    MatchLineRequestSchema(base_invoice_revision=invoice.invoice_revision, mode="auto", voucher_ref=booking_line.voucher_ref),
                    actor=ACTOR,
                )
                await session.commit()
                snapshot_expected = invoice.lines[0].expected_cost_minor
                snapshot_variance = invoice.lines[0].variance_minor

                supplier = await ap.supplier_repository.get_by_id("sup_la_siesta")
                supplier.credit_terms_days = 999
                supplier.default_currency = "VND"
                await session.commit()

                reloaded = await ap.get_invoice(invoice.id)
                self.assertEqual(reloaded.lines[0].expected_cost_minor, snapshot_expected)
                self.assertEqual(reloaded.lines[0].variance_minor, snapshot_variance)

        asyncio.run(scenario())

    def test_get_line_by_voucher_ref_is_read_only(self):
        """§9 exception (`booking_service.get_line_by_voucher_ref`) must never flush/commit —
        booking_lines stay byte-identical, and no explicit commit happens inside the call
        (verified by never calling `session.commit()` around it, only reading before/after)."""

        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                before = await self._snapshot_booking_lines(session)

                found = await BookingService(session).get_line_by_voucher_ref(booking_line.voucher_ref)
                self.assertIsNotNone(found)
                self.assertEqual(found.id, booking_line.id)

                missing = await BookingService(session).get_line_by_voucher_ref("VC-0000-9999")
                self.assertIsNone(missing)

                after = await self._snapshot_booking_lines(session)
                self.assertEqual(before, after)

        asyncio.run(scenario())

    def test_payment_idempotency_replay_returns_identical_response(self):
        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await self._approved_invoice(ap, booking_line, session)

                payload = RecordPaymentRequestSchema(
                    supplier_id="sup_la_siesta",
                    paid_at=date(2026, 6, 25),
                    currency="USD",
                    amount_minor=2_000_000,
                    method="bank_transfer",
                    allocations=[PaymentAllocationInputSchema(invoice_id=invoice.id, amount_minor=2_000_000)],
                )
                first = await ap.record_payment(payload, actor=ACTOR, idempotency_key="replay-key")
                await session.commit()
                second = await ap.record_payment(payload, actor=ACTOR, idempotency_key="replay-key")
                await session.commit()

                self.assertEqual(first.id, second.id)
                self.assertEqual(first.payment_code, second.payment_code)

        asyncio.run(scenario())

    def test_payment_atomicity_zero_rows_on_bad_allocation(self):
        """Atomicity: if any allocation fails its FK constraint, the whole insert (payment +
        every allocation) rolls back — zero rows, not a partial write."""

        async def scenario():
            async with self.session_factory() as session:
                booking_line = await self._confirmed_booking_line(session)
                ap = ApReconciliationService(session)
                invoice = await self._approved_invoice(ap, booking_line, session)

                from repositories.supplier_invoice_repository import ApPaymentDuplicateError

                # SQLite doesn't enforce FK constraints by default in this test harness, so
                # force the IntegrityError via a NOT NULL violation instead (still exercises
                # the same rollback path in `insert_payment_with_allocations`).
                with self.assertRaises(ApPaymentDuplicateError):
                    await ap.repository.insert_payment_with_allocations(
                        payment_id="apy_atomic_test",
                        payment_values={
                            "supplier_id": "sup_la_siesta",
                            "payment_code": "PV-9999-9999",
                            "paid_at": date(2026, 6, 25),
                            "currency": "USD",
                            "amount_minor": 2_000_000,
                            "fx_rate_ppm": None,
                            "method": "bank_transfer",
                            "reference": None,
                            "idempotency_key": None,
                            "notes": None,
                            "created_by": ACTOR.serialize(),
                        },
                        allocations=[
                            {"invoice_id": invoice.id, "amount_minor": 1_000_000},
                            {"invoice_id": invoice.id, "amount_minor": None},
                        ],
                    )

                from db.models.supplier_invoice import ApPayment

                result = await session.execute(select(ApPayment).where(ApPayment.id == "apy_atomic_test"))
                self.assertIsNone(result.scalar_one_or_none())

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
