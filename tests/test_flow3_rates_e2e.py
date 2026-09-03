"""Comprehensive E2E Verification Suite for Flow 3 (Rates & Contracts) — Plan 15.3.

Verifies:
1. Rate Creation & Multi-Price Line Entry (Draft, VND, 4 lines with BigInteger minor units, rate_sources provenance)
2. Lifecycle Transition & Immutability (Draft -> Active -> 409 on in-place PUT -> Atomic Supersede -> Superseded + Active)
3. Pure Rate Selection (date matching, blackout, pax tiers, conflict flagging on overlap)
4. Money Kernel & Schema Invariants (Zero float math, No destination columns on rate tables, Pure date comparison)
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from datetime import date
from typing import Any

from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.kernel import ActorRef, validate_amount_minor, validate_currency
from core.rules.rate_selection import (
    BlackoutWindow,
    RateCandidate,
    RatePriceLineCandidate,
    pick_price_line,
    select_rates,
)
from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.outbox import OutboxEvent
from db.models.product import Product
from db.models.rate import Rate, RatePriceLine, RateSource
from db.models.supplier import Supplier
from schemas.v2.product import ProductCreateSchema
from schemas.v2.rate import (
    RateCreateSchema,
    RatePriceLineCreateSchema,
    RateSourceCreateSchema,
    RateSupersedeSchema,
    RateUpdateSchema,
)
from services.product_service import ProductService
from services.rate_service import RateConflictError, RateService, RateValidationError

ACTOR = ActorRef(actor_id="qa-lead@travel.ai", actor_type="staff")


class Flow3RatesE2ETestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.engine.dispose())
        if os.path.exists(cls.db_file.name):
            os.unlink(cls.db_file.name)

    def setUp(self):
        asyncio.run(self._setup_fixtures())

    async def _setup_fixtures(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        async with self.session_factory() as session:
            # 1. Destination
            dest = DestinationCatalog(
                id="dst_danang",
                canonical_name="Da Nang",
                slug="da-nang",
                timezone="Asia/Ho_Chi_Minh",
            )
            session.add(dest)

            # 2. Supplier
            supplier = Supplier(
                id="sup_furama",
                name="Furama Resort Danang",
                name_normalized="furama resort danang",
                supplier_type="direct",
                default_currency="VND",
                payment_terms_json={"deposit_pct": 30, "due_days_before_checkin": 14},
                cancellation_policy_json={"free_cancellation_days": 7, "penalty_pct": 100},
                child_policy_json={"infant_max_age": 2, "child_max_age": 11, "free_child_count": 1},
            )
            session.add(supplier)
            await session.commit()

            # 3. Product
            product_service = ProductService(session)
            product = await product_service.create_product(
                ProductCreateSchema(
                    destination_id="dst_danang",
                    category="accommodation",
                    title="Furama Resort Danang — Ocean Suite",
                    supplier_id="sup_furama",
                    charge_unit="room",
                    time_basis="night",
                    default_min_pax=1,
                    default_max_pax=4,
                ),
                actor=ACTOR,
            )
            self.product_id = product.id
            await session.commit()

    def test_complete_flow3_lifecycle_and_immutability(self):
        """E2E verification of Flow 3: Creation, Activation, 409 Rejection, Supersede, and Audit."""

        async def run_scenario():
            async with self.session_factory() as session:
                service = RateService(session)

                # =========================================================================
                # Step 1: Rate Creation & Multi-Price Line Entry (Draft)
                # =========================================================================
                # 4 price lines in VND:
                # - SGL: 4,500,000 VND
                # - DBL: 5,000,000 VND
                # - EXTRA_BED: 1,200,000 VND
                # - CHILD_WITH_BED: 800,000 VND
                price_lines = [
                    RatePriceLineCreateSchema(
                        price_for="adult",
                        occupancy_basis="sgl",
                        unit="room",
                        amount_minor=4_500_000,
                        sort_order=0,
                        note="Single occupancy",
                    ),
                    RatePriceLineCreateSchema(
                        price_for="adult",
                        occupancy_basis="dbl",
                        unit="room",
                        amount_minor=5_000_000,
                        sort_order=1,
                        note="Double occupancy",
                    ),
                    RatePriceLineCreateSchema(
                        price_for="adult",
                        occupancy_basis="na",
                        unit="person",
                        amount_minor=1_200_000,
                        sort_order=2,
                        note="Extra bed adult",
                    ),
                    RatePriceLineCreateSchema(
                        price_for="child",
                        occupancy_basis="na",
                        unit="person",
                        amount_minor=800_000,
                        sort_order=3,
                        note="Child with extra bed",
                    ),
                ]

                create_payload = RateCreateSchema(
                    product_id=self.product_id,
                    currency="VND",
                    rate_basis="net",
                    valid_from=date(2026, 10, 1),
                    valid_to=date(2026, 12, 31),
                    season_name="Autumn/Winter 2026 High Season",
                    min_pax=1,
                    max_pax=4,
                    tax_included=True,
                    tax_pct=800,  # 8.00% VAT in bps
                    source_reference="Email contract 2026",
                    source=RateSourceCreateSchema(
                        supplier_id="sup_furama",
                        document_type="contract",
                        channel="email",
                        notes="Signed contract via sales manager email",
                    ),
                    lines=price_lines,
                )

                draft_rate = await service.create_draft(self.product_id, create_payload, actor=ACTOR)
                await session.commit()

                self.assertIsNotNone(draft_rate)
                self.assertEqual(draft_rate.lifecycle_status, "draft")
                self.assertEqual(draft_rate.version, 1)
                self.assertEqual(draft_rate.currency, "VND")
                self.assertEqual(draft_rate.valid_from, date(2026, 10, 1))
                self.assertEqual(draft_rate.valid_to, date(2026, 12, 31))
                self.assertEqual(len(draft_rate.lines), 4)
                self.assertIsNotNone(draft_rate.source_id)
                self.assertEqual(draft_rate.source.channel, "email")
                self.assertEqual(draft_rate.source.document_type, "contract")

                # Verify integer minor unit values
                line_map = {(l.price_for, l.occupancy_basis): l.amount_minor for l in draft_rate.lines}
                self.assertEqual(line_map[("adult", "sgl")], 4_500_000)
                self.assertEqual(line_map[("adult", "dbl")], 5_000_000)
                self.assertEqual(line_map[("adult", "na")], 1_200_000)
                self.assertEqual(line_map[("child", "na")], 800_000)

                # Verify policy inheritance from supplier
                self.assertIsNone(draft_rate.payment_terms_json)
                self.assertEqual(draft_rate.resolved_payment_terms_json["deposit_pct"], 30)
                self.assertTrue(draft_rate.inherited_from_supplier["payment_terms"])

                # =========================================================================
                # Step 2: Transition Draft -> Active
                # =========================================================================
                active_rate = await service.activate(draft_rate.id, actor=ACTOR)
                await session.commit()

                self.assertEqual(active_rate.lifecycle_status, "active")
                self.assertEqual(active_rate.version, 1)

                # Verify Outbox Event for activation
                outbox_stmt = select(OutboxEvent).where(
                    OutboxEvent.aggregate_id == active_rate.id,
                    OutboxEvent.event_type == "catalog.rate.activated",
                )
                outbox_res = await session.execute(outbox_stmt)
                event = outbox_res.scalar_one_or_none()
                self.assertIsNotNone(event, "catalog.rate.activated event MUST be emitted to outbox")
                self.assertEqual(event.payload_json["rate_id"], active_rate.id)
                self.assertEqual(event.payload_json["validity"]["valid_from"], "2026-10-01")

                # =========================================================================
                # Step 3: Immutability Verification (E3/R3) — 409 on In-Place PUT
                # =========================================================================
                update_payload = RateUpdateSchema(
                    rate_basis="net",
                    valid_from=date(2026, 10, 1),
                    valid_to=date(2026, 12, 31),
                    season_name="Hacked Season Name",
                    lines=price_lines,
                )
                with self.assertRaises(RateConflictError) as conflict_ctx:
                    await service.update_draft(active_rate.id, update_payload, actor=ACTOR)
                self.assertIn("supersede instead", str(conflict_ctx.exception))

                # Hard delete on active rate MUST also raise 409
                with self.assertRaises(RateConflictError) as delete_ctx:
                    await service.delete_draft(active_rate.id)
                self.assertIn("Only a draft rate can be hard-deleted", str(delete_ctx.exception))

                # =========================================================================
                # Step 4: Atomic Supersede Operation (POST /rates/{id}/supersede)
                # =========================================================================
                # DBL increased to 5,500,000 VND, SGL increased to 4,800,000 VND
                supersede_lines = [
                    RatePriceLineCreateSchema(
                        price_for="adult",
                        occupancy_basis="sgl",
                        unit="room",
                        amount_minor=4_800_000,
                        sort_order=0,
                        note="Single occupancy revised",
                    ),
                    RatePriceLineCreateSchema(
                        price_for="adult",
                        occupancy_basis="dbl",
                        unit="room",
                        amount_minor=5_500_000,
                        sort_order=1,
                        note="Double occupancy revised (+10%)",
                    ),
                    RatePriceLineCreateSchema(
                        price_for="adult",
                        occupancy_basis="na",
                        unit="person",
                        amount_minor=1_200_000,
                        sort_order=2,
                        note="Extra bed adult",
                    ),
                    RatePriceLineCreateSchema(
                        price_for="child",
                        occupancy_basis="na",
                        unit="person",
                        amount_minor=800_000,
                        sort_order=3,
                        note="Child with extra bed",
                    ),
                ]

                supersede_payload = RateSupersedeSchema(
                    currency="VND",
                    rate_basis="net",
                    valid_from=date(2026, 10, 1),
                    valid_to=date(2026, 12, 31),
                    season_name="Autumn/Winter 2026 High Season (Revised Amendment)",
                    min_pax=1,
                    max_pax=4,
                    tax_included=True,
                    tax_pct=800,
                    source_reference="Amendment #01 - Oct 2026",
                    source=RateSourceCreateSchema(
                        supplier_id="sup_furama",
                        document_type="amendment",
                        channel="email",
                        notes="Price adjustment amendment for Q4",
                    ),
                    lines=supersede_lines,
                )

                superseded_v2 = await service.supersede(active_rate.id, supersede_payload, actor=ACTOR)
                await session.commit()

                # Verify V2 properties
                self.assertIsNotNone(superseded_v2)
                self.assertEqual(superseded_v2.lifecycle_status, "active")
                self.assertEqual(superseded_v2.version, 2)
                self.assertEqual(superseded_v2.supersedes_rate_id, active_rate.id)
                self.assertEqual(len(superseded_v2.lines), 4)

                v2_line_map = {(l.price_for, l.occupancy_basis): l.amount_minor for l in superseded_v2.lines}
                self.assertEqual(v2_line_map[("adult", "dbl")], 5_500_000)
                self.assertEqual(v2_line_map[("adult", "sgl")], 4_800_000)

                # =========================================================================
                # Step 5: Verify Old Rate V1 is 100% Frozen in DB (R3 Invariant)
                # =========================================================================
                v1_frozen = await service.get_rate(active_rate.id)
                self.assertIsNotNone(v1_frozen)
                self.assertEqual(v1_frozen.lifecycle_status, "superseded")
                self.assertEqual(v1_frozen.version, 1)
                self.assertEqual(v1_frozen.season_name, "Autumn/Winter 2026 High Season")
                self.assertEqual(len(v1_frozen.lines), 4)

                v1_line_map = {(l.price_for, l.occupancy_basis): l.amount_minor for l in v1_frozen.lines}
                self.assertEqual(v1_line_map[("adult", "dbl")], 5_000_000, "V1 DBL MUST remain 5,000,000 VND")
                self.assertEqual(v1_line_map[("adult", "sgl")], 4_500_000, "V1 SGL MUST remain 4,500,000 VND")

                # Verify Outbox Event for supersede
                outbox_stmt2 = select(OutboxEvent).where(
                    OutboxEvent.aggregate_id == superseded_v2.id,
                    OutboxEvent.event_type == "catalog.rate.superseded",
                )
                outbox_res2 = await session.execute(outbox_stmt2)
                event2 = outbox_res2.scalar_one_or_none()
                self.assertIsNotNone(event2, "catalog.rate.superseded event MUST be emitted to outbox")
                self.assertEqual(event2.payload_json["old_rate_id"], active_rate.id)
                self.assertEqual(event2.payload_json["new_rate_id"], superseded_v2.id)

        asyncio.run(run_scenario())

    def test_pure_rate_selection_rules(self):
        """Verify pure rate selection matching on date, pax, blackout, and overlap conflict detection."""
        candidate_v1 = RateCandidate(
            rate_id="rat_v1",
            lifecycle_status="superseded",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 12, 31),
            min_pax=1,
            max_pax=4,
            lines=(
                RatePriceLineCandidate(price_for="adult", occupancy_basis="sgl", unit="room", amount_minor=4_500_000),
                RatePriceLineCandidate(price_for="adult", occupancy_basis="dbl", unit="room", amount_minor=5_000_000),
                RatePriceLineCandidate(price_for="adult", occupancy_basis="na", unit="person", amount_minor=1_200_000),
                RatePriceLineCandidate(price_for="child", occupancy_basis="na", unit="person", amount_minor=800_000),
            ),
        )

        candidate_v2 = RateCandidate(
            rate_id="rat_v2",
            lifecycle_status="active",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 12, 31),
            min_pax=1,
            max_pax=4,
            blackouts=(BlackoutWindow(from_date=date(2026, 12, 24), to_date=date(2026, 12, 25), reason="Christmas Gala"),),
            lines=(
                RatePriceLineCandidate(price_for="adult", occupancy_basis="sgl", unit="room", amount_minor=4_800_000),
                RatePriceLineCandidate(price_for="adult", occupancy_basis="dbl", unit="room", amount_minor=5_500_000),
                RatePriceLineCandidate(price_for="adult", occupancy_basis="na", unit="person", amount_minor=1_200_000),
                RatePriceLineCandidate(price_for="child", occupancy_basis="na", unit="person", amount_minor=800_000),
            ),
        )

        # 1. Matching valid date: 2026-11-15 (within validity, outside blackout)
        res1 = select_rates([candidate_v1, candidate_v2], service_date=date(2026, 11, 15), pax=2)
        self.assertEqual(len(res1.candidates), 1)
        self.assertEqual(res1.candidates[0].rate_id, "rat_v2")
        self.assertFalse(res1.has_conflict)

        # 2. Blackout date: 2026-12-24 -> excluded
        res_blackout = select_rates([candidate_v1, candidate_v2], service_date=date(2026, 12, 24), pax=2)
        self.assertEqual(len(res_blackout.candidates), 0)

        # 3. Outside validity date: 2027-01-05 -> excluded
        res_outside = select_rates([candidate_v1, candidate_v2], service_date=date(2027, 1, 5), pax=2)
        self.assertEqual(len(res_outside.candidates), 0)

        # 4. Pax count outside max_pax (e.g. 10 pax) -> excluded
        res_pax = select_rates([candidate_v1, candidate_v2], service_date=date(2026, 11, 15), pax=10)
        self.assertEqual(len(res_pax.candidates), 0)

        # 5. Overlap scenario: 2 active rates covering same date
        candidate_promo = RateCandidate(
            rate_id="rat_promo",
            lifecycle_status="active",
            valid_from=date(2026, 11, 1),
            valid_to=date(2026, 11, 30),
            min_pax=1,
            max_pax=4,
        )
        res_conflict = select_rates([candidate_v2, candidate_promo], service_date=date(2026, 11, 15), pax=2)
        self.assertEqual(len(res_conflict.candidates), 2)
        self.assertTrue(res_conflict.has_conflict, "Must flag conflict when >1 active rate matches")

        # 6. Price line picker resolution
        dbl_line = pick_price_line(list(candidate_v2.lines), price_for="adult", occupancy_basis="dbl", pax_count=2)
        self.assertFalse(dbl_line.has_conflict)
        self.assertEqual(dbl_line.candidates[0].amount_minor, 5_500_000)

        sgl_line = pick_price_line(list(candidate_v2.lines), price_for="adult", occupancy_basis="sgl", pax_count=1)
        self.assertFalse(sgl_line.has_conflict)
        self.assertEqual(sgl_line.candidates[0].amount_minor, 4_800_000)

    def test_money_kernel_and_schema_invariants(self):
        """Verify strict integer minor units, no float math, and zero destination columns on rates."""
        # 1. Money validation
        self.assertEqual(validate_amount_minor(5_000_000), 5_000_000)
        with self.assertRaises(ValueError):
            validate_amount_minor(5000000.50)  # Float strictly rejected

        with self.assertRaises(ValueError):
            validate_amount_minor(-100)  # Negative rejected

        with self.assertRaises(ValueError):
            validate_currency("INVALID_CUR")

        # 2. Database column audit on Rate tables
        inspector = inspect(Rate)
        column_names = {c.name for c in inspector.columns}
        self.assertNotIn("destination_id", column_names, "Rate MUST NOT contain destination_id")
        self.assertNotIn("origin_destination_id", column_names, "Rate MUST NOT contain origin_destination_id")

        line_inspector = inspect(RatePriceLine)
        line_cols = {c.name: c.type for c in line_inspector.columns}
        self.assertEqual(line_cols["amount_minor"].python_type, int, "amount_minor must be Integer/BigInteger")


if __name__ == "__main__":
    unittest.main()
