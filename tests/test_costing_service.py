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
from schemas.v2.product import ProductCreateSchema
from schemas.v2.rate import RateCreateSchema, RatePriceLineCreateSchema
from schemas.v2.costing import (
    AttachQuotationSchema,
    CostingSettingsUpdateSchema,
    CostingSheetCreateSchema,
    ServiceLineCreateSchema,
    ServiceLineUpdateSchema,
)
from services.costing_service import CostingConflictError, CostingService, CostingValidationError
from services.product_service import ProductService
from services.rate_service import RateService

ACTOR = ActorRef(actor_id="staff@example.com", actor_type="staff")


class CostingServiceTests(unittest.TestCase):
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
            session.add(DestinationCatalog(id="dst_hanoi", canonical_name="Hanoi", slug="hanoi", iata_code="HAN"))
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

            product_service = ProductService(session)
            product = await product_service.create_product(
                ProductCreateSchema(
                    destination_id="dst_hanoi",
                    category="accommodation",
                    title="La Siesta Old Quarter — Deluxe Room",
                    supplier_id="sup_la_siesta",
                    property_id=None,
                ),
                actor=ACTOR,
            )
            await session.commit()
            self.product_id = product.id

            rate_service = RateService(session)
            rate = await rate_service.create_draft(
                self.product_id,
                RateCreateSchema(
                    product_id=self.product_id,
                    rate_basis="net",
                    valid_from=date(2026, 1, 1),
                    valid_to=date(2026, 12, 31),
                    lines=[
                        RatePriceLineCreateSchema(
                            price_for="room", occupancy_basis="dbl", unit="room", amount_minor=1_000_000
                        )
                    ],
                ),
                actor=ACTOR,
            )
            await session.commit()
            activated = await rate_service.activate(rate.id, actor=ACTOR)
            await session.commit()
            self.rate_id = activated.id
            self.price_line_id = activated.lines[0].id

            await QuoteRequestRepository(session).create_request(
                role="customer", customer_name="Jane Doe", email="jane@example.com", request_id="req_test1"
            )
            await session.commit()

            await QuotationRepository(session).create_quotation(
                quotation_id="qtn_test1",
                brand_id="brand_capella",
                template_name="quote-generator",
                baseline_lang="en",
            )
            await session.commit()

    def _catalog_line_payload(self, base_costing_revision: int, **overrides):
        defaults = dict(
            base_costing_revision=base_costing_revision,
            day_number=1,
            product_id=self.product_id,
            rate_id=self.rate_id,
            price_line_id=self.price_line_id,
            qty_unit=2,
            qty_time=3,
        )
        defaults.update(overrides)
        return ServiceLineCreateSchema(**defaults)

    def _manual_line_payload(self, base_costing_revision: int, **overrides):
        defaults = dict(
            base_costing_revision=base_costing_revision,
            day_number=None,
            category="visa",
            title="E-visa processing",
            unit="person",
            time_basis="trip",
            unit_cost_minor=250_000,
            cost_currency="VND",
            qty_unit=2,
            qty_time=1,
        )
        defaults.update(overrides)
        return ServiceLineCreateSchema(**defaults)

    def test_create_sheet_from_request_then_from_quotation_are_independent_slots(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                sheet_a = await service.create_sheet(
                    CostingSheetCreateSchema(request_id="req_test1"), actor=ACTOR
                )
                await session.commit()
                self.assertTrue(sheet_a.id.startswith("cst_"))
                self.assertEqual(sheet_a.quote_request_id, "req_test1")
                self.assertIsNone(sheet_a.quotation_id)

                sheet_b = await service.create_sheet(
                    CostingSheetCreateSchema(quotation_id="qtn_test1"), actor=ACTOR
                )
                await session.commit()
                self.assertEqual(sheet_b.quotation_id, "qtn_test1")

        asyncio.run(scenario())

    def test_second_unattached_sheet_for_same_request_conflicts(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                await service.create_sheet(CostingSheetCreateSchema(request_id="req_test1"), actor=ACTOR)
                await session.commit()

                with self.assertRaises(CostingConflictError):
                    await service.create_sheet(CostingSheetCreateSchema(request_id="req_test1"), actor=ACTOR)

        asyncio.run(scenario())

    def test_attach_frees_slot_for_a_new_sheet_on_same_request(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                sheet = await service.create_sheet(CostingSheetCreateSchema(request_id="req_test1"), actor=ACTOR)
                await session.commit()

                await QuotationRepository(session).create_quotation(
                    quotation_id="qtn_from_req",
                    brand_id="brand_capella",
                    template_name="quote-generator",
                    baseline_lang="en",
                    source_request_id="req_test1",
                )
                await session.commit()

                workbench = await service.attach_quotation(
                    sheet.id,
                    AttachQuotationSchema(quotation_id="qtn_from_req"),
                    actor=ACTOR,
                    idempotency_key="attach-1",
                )
                await session.commit()
                self.assertEqual(workbench.sheet.quotation_id, "qtn_from_req")

                # slot freed — a brand-new sheet can now open against the same request
                second_sheet = await service.create_sheet(
                    CostingSheetCreateSchema(request_id="req_test1"), actor=ACTOR
                )
                await session.commit()
                self.assertNotEqual(second_sheet.id, sheet.id)

        asyncio.run(scenario())

    def test_attach_retry_with_same_idempotency_key_is_a_no_op(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                sheet = await service.create_sheet(CostingSheetCreateSchema(request_id="req_test1"), actor=ACTOR)
                await session.commit()
                await QuotationRepository(session).create_quotation(
                    quotation_id="qtn_from_req2",
                    brand_id="brand_capella",
                    template_name="quote-generator",
                    baseline_lang="en",
                    source_request_id="req_test1",
                )
                await session.commit()

                first = await service.attach_quotation(
                    sheet.id, AttachQuotationSchema(quotation_id="qtn_from_req2"), actor=ACTOR, idempotency_key="k1"
                )
                await session.commit()
                second = await service.attach_quotation(
                    sheet.id, AttachQuotationSchema(quotation_id="qtn_from_req2"), actor=ACTOR, idempotency_key="k1"
                )
                await session.commit()
                self.assertEqual(first.sheet.costing_revision, second.sheet.costing_revision)

                with self.assertRaises(CostingConflictError):
                    await service.attach_quotation(
                        sheet.id, AttachQuotationSchema(quotation_id="qtn_from_req2"), actor=ACTOR, idempotency_key="k2"
                    )

        asyncio.run(scenario())

    def test_attach_validates_source_request_id_matches(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                sheet = await service.create_sheet(CostingSheetCreateSchema(request_id="req_test1"), actor=ACTOR)
                await session.commit()

                # qtn_test1 has no source_request_id set — mismatch
                with self.assertRaises(CostingValidationError):
                    await service.attach_quotation(
                        sheet.id, AttachQuotationSchema(quotation_id="qtn_test1"), actor=ACTOR, idempotency_key="k2"
                    )

        asyncio.run(scenario())

    def test_create_catalog_line_snapshots_cost_and_supersede_does_not_move_it(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                sheet = await service.create_sheet(
                    CostingSheetCreateSchema(request_id="req_test1", currency="USD"), actor=ACTOR
                )
                await session.commit()

                workbench = await service.create_line(
                    sheet.id, self._catalog_line_payload(sheet.costing_revision), actor=ACTOR, idempotency_key="line-1"
                )
                await session.commit()
                self.assertEqual(len(workbench.items), 1)
                line = workbench.items[0]
                self.assertEqual(line.unit_cost_minor, 1_000_000)
                self.assertEqual(line.tariff_id, self.rate_id)
                self.assertEqual(line.cost_minor, 1_000_000 * 2 * 3)

                # R3: supersede the rate — the already-written line must not move.
                from schemas.v2.rate import RateSupersedeSchema

                rate_service = RateService(session)
                await rate_service.supersede(
                    self.rate_id,
                    RateSupersedeSchema(
                        rate_basis="net",
                        valid_from=date(2027, 1, 1),
                        valid_to=date(2027, 12, 31),
                        lines=[
                            RatePriceLineCreateSchema(
                                price_for="room", occupancy_basis="dbl", unit="room", amount_minor=9_999_999
                            )
                        ],
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                reloaded = await service.get_workbench(sheet.id)
                self.assertEqual(reloaded.items[0].unit_cost_minor, 1_000_000)

        asyncio.run(scenario())

    def test_cas_conflict_on_stale_revision(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                sheet = await service.create_sheet(CostingSheetCreateSchema(request_id="req_test1"), actor=ACTOR)
                await session.commit()

                with self.assertRaises(CostingConflictError):
                    await service.create_line(
                        sheet.id, self._manual_line_payload(sheet.costing_revision + 1), actor=ACTOR, idempotency_key="x"
                    )

        asyncio.run(scenario())

    def test_currency_locked_once_a_line_exists(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                sheet = await service.create_sheet(
                    CostingSheetCreateSchema(request_id="req_test1", currency="VND"), actor=ACTOR
                )
                await session.commit()
                workbench = await service.create_line(
                    sheet.id, self._manual_line_payload(sheet.costing_revision), actor=ACTOR, idempotency_key="m1"
                )
                await session.commit()

                with self.assertRaises(CostingConflictError):
                    await service.update_settings(
                        sheet.id,
                        CostingSettingsUpdateSchema(
                            base_costing_revision=workbench.sheet.costing_revision, currency="USD"
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_fx_rate_required_when_line_currency_differs_from_sheet(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                sheet = await service.create_sheet(
                    CostingSheetCreateSchema(request_id="req_test1", currency="USD"), actor=ACTOR
                )
                await session.commit()

                with self.assertRaises(CostingValidationError):
                    await service.create_line(
                        sheet.id, self._manual_line_payload(sheet.costing_revision), actor=ACTOR, idempotency_key="fx1"
                    )

        asyncio.run(scenario())

    def test_editing_cost_of_catalog_line_cuts_tariff_reference(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                sheet = await service.create_sheet(
                    CostingSheetCreateSchema(request_id="req_test1", currency="USD"), actor=ACTOR
                )
                await session.commit()
                workbench = await service.create_line(
                    sheet.id, self._catalog_line_payload(sheet.costing_revision), actor=ACTOR, idempotency_key="l1"
                )
                await session.commit()
                line_id = workbench.items[0].id

                updated = await service.update_line(
                    sheet.id,
                    line_id,
                    ServiceLineUpdateSchema(
                        base_costing_revision=workbench.sheet.costing_revision,
                        day_number=1,
                        category="accommodation",
                        title="Manual override price",
                        unit="room",
                        time_basis="night",
                        unit_cost_minor=500_000,
                        cost_currency="USD",
                        qty_unit=1,
                        qty_time=1,
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertIsNone(updated.items[0].tariff_id)
                self.assertIsNone(updated.items[0].price_line_id)
                self.assertIsNone(updated.items[0].product_id)

        asyncio.run(scenario())

    def test_create_line_idempotent_retry_does_not_duplicate(self):
        async def scenario():
            async with self.session_factory() as session:
                service = CostingService(session)
                sheet = await service.create_sheet(
                    CostingSheetCreateSchema(request_id="req_test1", currency="USD"), actor=ACTOR
                )
                await session.commit()

                payload = self._catalog_line_payload(sheet.costing_revision)
                first = await service.create_line(sheet.id, payload, actor=ACTOR, idempotency_key="dup-key")
                await session.commit()
                second = await service.create_line(sheet.id, payload, actor=ACTOR, idempotency_key="dup-key")
                await session.commit()

                self.assertEqual(len(first.items), 1)
                self.assertEqual(len(second.items), 1)

        asyncio.run(scenario())

    def test_version_guarded_bump_rejects_stale_writer_even_with_stale_identity_map(self):
        """Plan 16.3 F-01 exit gate: 2 writers on the same base revision → exactly one wins.

        Session A holds an in-memory sheet at revision 0 (identity-map stale), session B
        commits revision 1; A's write must die at the SQL guard, not silently land.
        """

        async def scenario():
            from repositories.costing_repository import CostingRepository, CostingRevisionRaceError

            async with self.session_factory() as session_a:
                service_a = CostingService(session_a)
                sheet = await service_a.create_sheet(
                    CostingSheetCreateSchema(request_id="req_test1", currency="USD"), actor=ACTOR
                )
                await session_a.commit()
                repo_a = CostingRepository(session_a)
                stale_sheet = await repo_a.get_sheet_by_id(sheet.id)
                await session_a.commit()  # release the read transaction, keep the stale object

                async with self.session_factory() as session_b:
                    service_b = CostingService(session_b)
                    await service_b.update_settings(
                        sheet.id,
                        CostingSettingsUpdateSchema(base_costing_revision=0, markup_rate_bps=2_000),
                        actor=ACTOR,
                    )
                    await session_b.commit()

                self.assertEqual(stale_sheet.costing_revision, 0)  # A still believes revision 0
                with self.assertRaises(CostingRevisionRaceError):
                    await repo_a.update_settings(
                        stale_sheet, values={"markup_rate_bps": 3_000}, expected_revision=0
                    )
                await session_a.rollback()

                current = await CostingRepository(session_a).get_sheet_revision(sheet.id)
                self.assertEqual(current, 1)  # B's write survived intact

        asyncio.run(scenario())

    def test_concurrent_attach_loses_to_quotation_id_null_guard(self):
        """Plan 16.3 F-01: attach of one sheet to two quotations — the loser gets a typed error."""

        async def scenario():
            from repositories.costing_repository import (
                CostingRepository,
                CostingSheetAlreadyAttachedError,
            )

            async with self.session_factory() as session_a:
                service_a = CostingService(session_a)
                sheet = await service_a.create_sheet(
                    CostingSheetCreateSchema(request_id="req_test1"), actor=ACTOR
                )
                await session_a.commit()

                for qid in ("qtn_race_1", "qtn_race_2"):
                    await QuotationRepository(session_a).create_quotation(
                        quotation_id=qid,
                        brand_id="brand_capella",
                        template_name="quote-generator",
                        baseline_lang="en",
                        source_request_id="req_test1",
                    )
                await session_a.commit()

                repo_a = CostingRepository(session_a)
                stale_sheet = await repo_a.get_sheet_by_id(sheet.id)
                await session_a.commit()

                async with self.session_factory() as session_b:
                    service_b = CostingService(session_b)
                    await service_b.attach_quotation(
                        sheet.id,
                        AttachQuotationSchema(quotation_id="qtn_race_1"),
                        actor=ACTOR,
                        idempotency_key="attach-winner",
                    )
                    await session_b.commit()

                self.assertIsNone(stale_sheet.quotation_id)  # A still believes unattached
                with self.assertRaises(CostingSheetAlreadyAttachedError):
                    await repo_a.attach_to_quotation(
                        stale_sheet, quotation_id="qtn_race_2", idempotency_key="attach-loser"
                    )
                await session_a.rollback()

                fresh = await CostingRepository(session_a).get_sheet_by_id(sheet.id)
                self.assertEqual(fresh.quotation_id, "qtn_race_1")  # winner untouched

        asyncio.run(scenario())

    def test_check_2_parent_null_is_rejected_by_check_constraint(self):
        async def scenario():
            async with self.session_factory() as session:
                from repositories.costing_repository import CostingRepository

                repo = CostingRepository(session)
                with self.assertRaises(Exception):
                    await repo.insert_sheet(sheet_id="cst_bad", values={"currency": "USD"})

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
