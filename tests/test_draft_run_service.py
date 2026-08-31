"""Draft Run orchestration tests (15.7 §3) — zero-money introspection, server-side rate
resolution (rate_missing/rate_conflict never auto-picked), writes only through
``costing_service.create_line``, partial-run behaviour, idempotent replay.
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import os
import tempfile
import unittest
from datetime import date
from unittest import mock

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.kernel import ActorRef
from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from schemas import service_draft as service_draft_module
from schemas.service_draft import DayDraftResult, ServiceDraft
from schemas.trip_profile import PartyComposition, RoomAllocation, TripProfile
from schemas.v2.ai_drafter import DraftDaySpecSchema
from schemas.v2.costing import CostingSheetCreateSchema
from schemas.v2.product import ProductCreateSchema
from schemas.v2.rate import RateCreateSchema, RatePriceLineCreateSchema
from services.ai_drafter import draft_run_service
from services.ai_drafter.draft_run_service import DraftConflictError, run_draft
from services.costing_service import CostingService
from services.product_service import ProductService
from services.rate_service import RateService

ACTOR = ActorRef(actor_id="staff@capella.travel", actor_type="staff")


def _sample_trip_profile() -> TripProfile:
    return TripProfile(
        archetype="couple",
        party=PartyComposition(adults=2, children=0, infants=0),
        room_config=[RoomAllocation(room_type="dbl", count=1)],
        quality_tier="luxury",
    )


class DraftRunServiceTests(unittest.TestCase):
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
                )
            )
            await session.commit()

            product_service = ProductService(session)
            self.product = await product_service.create_product(
                ProductCreateSchema(
                    destination_id="dst_hanoi", category="accommodation", title="La Siesta Deluxe Room",
                    supplier_id="sup_la_siesta", property_id=None,
                ),
                actor=ACTOR,
            )
            await session.commit()

            self.no_rate_product = await product_service.create_product(
                ProductCreateSchema(
                    destination_id="dst_hanoi", category="experience", title="Sunset Cruise",
                    supplier_id="sup_la_siesta", property_id=None,
                ),
                actor=ACTOR,
            )
            await session.commit()

            rate_service = RateService(session)
            rate = await rate_service.create_draft(
                self.product.id,
                RateCreateSchema(
                    product_id=self.product.id,
                    rate_basis="net",
                    valid_from=date(2026, 1, 1),
                    valid_to=date(2026, 12, 31),
                    lines=[RatePriceLineCreateSchema(price_for="adult", occupancy_basis="dbl", unit="room", amount_minor=1_000_000)],
                ),
                actor=ACTOR,
            )
            await session.commit()
            activated = await rate_service.activate(rate.id, actor=ACTOR)
            await session.commit()
            self.rate_id = activated.id

            from repositories.quote_request_repository import QuoteRequestRepository

            await QuoteRequestRepository(session).create_request(
                role="customer", customer_name="Jane Doe", email="jane@example.com", request_id="req_draft1"
            )
            await session.commit()

            costing = CostingService(session)
            sheet = await costing.create_sheet(CostingSheetCreateSchema(request_id="req_draft1", currency="USD"), actor=ACTOR)
            await session.commit()
            self.sheet_id = sheet.id

    def _days(self, *day_numbers):
        return [
            DraftDaySpecSchema(day_number=n, destination_id="dst_hanoi", service_date=date(2026, 2, 10 + n))
            for n in day_numbers
        ]

    def test_zero_money_introspection_on_service_draft_schema(self):
        """chốt #1 — grep the ACTUAL schema source, not just field names, so a renamed-but-
        still-monetary field would still be caught."""
        source = inspect.getsource(service_draft_module)
        tree = ast.parse(source)
        field_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        field_names.append(stmt.target.id)
        # "price_for" is the PRICE_FOR vocabulary field (who a rate line applies to — adult/
        # child/room/...), not an amount — the one documented exception to the coarse
        # "_minor|price|amount" grep the plan calls for (15.7-ai-service-drafter.md chốt #1).
        allowed_exceptions = {"price_for"}
        forbidden_substrings = ("_minor", "price", "amount")
        offending = [
            name
            for name in field_names
            if name not in allowed_exceptions and any(s in name.lower() for s in forbidden_substrings)
        ]
        self.assertEqual(offending, [], f"ServiceDraft/DayDraftResult must never carry a money field, found: {offending}")

    def test_successful_resolution_writes_catalog_line_via_costing_service(self):
        draft = DayDraftResult(
            day_number=1,
            services=[
                ServiceDraft(
                    category="accommodation", product_id=self.product.id, occupancy_basis="dbl",
                    price_for="adult", pax_count=2, selection_reason="Luxury tier match, dbl room per room_config.",
                )
            ],
        )

        async def scenario():
            async with self.session_factory() as session:
                sheet = await self._get_sheet(session)

                async def fake_draft_day(deps, day_context):
                    deps.allowlist.record([self.product.id])
                    return draft

                with mock.patch.object(draft_run_service, "draft_day", side_effect=fake_draft_day):
                    result = await run_draft(
                        session, sheet=sheet, trip_profile=_sample_trip_profile(), days=self._days(1),
                        day_numbers_filter=None, base_costing_revision=0, actor=ACTOR, idempotency_key="draft-1",
                    )
                await session.commit()
                return result

        result = asyncio.run(scenario())
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.days_done, [1])
        self.assertEqual(len(result.created_line_ids), 1)
        self.assertEqual(result.manual_review_count, 0)

        async def verify():
            async with self.session_factory() as session:
                workbench = await CostingService(session).get_workbench(self.sheet_id)
                line = workbench.items[0]
                self.assertEqual(line.source, "ai_draft")
                self.assertEqual(line.product_id, self.product.id)
                self.assertEqual(line.tariff_id, self.rate_id)
                self.assertGreater(line.unit_cost_minor, 0)
                self.assertIsNotNone(line.ai_meta_json)
                self.assertIn("reason", line.ai_meta_json)
                self.assertEqual(line.ai_meta_json["day_number"], 1)
                self.assertEqual(line.booking_status, "quoted")  # same default a human line gets — no special-casing

        asyncio.run(verify())

    def test_rate_missing_creates_zero_cost_manual_line_with_flag(self):
        draft = DayDraftResult(
            day_number=1,
            services=[
                ServiceDraft(
                    category="experience", product_id=self.no_rate_product.id, occupancy_basis="na",
                    price_for="adult", pax_count=2, selection_reason="Sunset cruise matches romantic pace.",
                )
            ],
        )

        async def scenario():
            async with self.session_factory() as session:
                sheet = await self._get_sheet(session)

                async def fake_draft_day(deps, day_context):
                    deps.allowlist.record([self.no_rate_product.id])
                    return draft

                with mock.patch.object(draft_run_service, "draft_day", side_effect=fake_draft_day):
                    result = await run_draft(
                        session, sheet=sheet, trip_profile=_sample_trip_profile(), days=self._days(1),
                        day_numbers_filter=None, base_costing_revision=0, actor=ACTOR, idempotency_key="draft-missing",
                    )
                await session.commit()
                return result

        result = asyncio.run(scenario())
        self.assertEqual(result.manual_review_count, 1)
        self.assertEqual(len(result.created_line_ids), 1)

        async def verify():
            async with self.session_factory() as session:
                workbench = await CostingService(session).get_workbench(self.sheet_id)
                line = workbench.items[0]
                self.assertEqual(line.unit_cost_minor, 0)
                self.assertIsNone(line.product_id)  # manual branch — no rate to snapshot from
                self.assertIn("rate_missing", line.ai_meta_json["flags"])
                self.assertIn("needs_manual", line.ai_meta_json["flags"])
                self.assertEqual(line.ai_meta_json["suggested_product_id"], self.no_rate_product.id)

        asyncio.run(verify())

    def test_rate_conflict_never_auto_picks_a_winner(self):
        async def add_conflicting_rate():
            async with self.session_factory() as session:
                rate_service = RateService(session)
                rate = await rate_service.create_draft(
                    self.product.id,
                    RateCreateSchema(
                        product_id=self.product.id, rate_basis="net",
                        valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31),
                        lines=[RatePriceLineCreateSchema(price_for="adult", occupancy_basis="dbl", unit="room", amount_minor=800_000)],
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                await rate_service.activate(rate.id, actor=ACTOR)
                await session.commit()

        asyncio.run(add_conflicting_rate())

        draft = DayDraftResult(
            day_number=1,
            services=[
                ServiceDraft(
                    category="accommodation", product_id=self.product.id, occupancy_basis="dbl",
                    price_for="adult", pax_count=2, selection_reason="Best deluxe match.",
                )
            ],
        )

        async def scenario():
            async with self.session_factory() as session:
                sheet = await self._get_sheet(session)

                async def fake_draft_day(deps, day_context):
                    deps.allowlist.record([self.product.id])
                    return draft

                with mock.patch.object(draft_run_service, "draft_day", side_effect=fake_draft_day):
                    result = await run_draft(
                        session, sheet=sheet, trip_profile=_sample_trip_profile(), days=self._days(1),
                        day_numbers_filter=None, base_costing_revision=0, actor=ACTOR, idempotency_key="draft-conflict",
                    )
                await session.commit()
                return result

        result = asyncio.run(scenario())
        self.assertEqual(result.manual_review_count, 1)

        async def verify():
            async with self.session_factory() as session:
                workbench = await CostingService(session).get_workbench(self.sheet_id)
                line = workbench.items[0]
                self.assertEqual(line.unit_cost_minor, 0)
                self.assertIsNone(line.tariff_id)
                self.assertIn("rate_conflict", line.ai_meta_json["flags"])

        asyncio.run(verify())

    def test_hallucinated_product_id_outside_allowlist_is_dropped(self):
        draft = DayDraftResult(
            day_number=1,
            services=[
                ServiceDraft(
                    category="accommodation", product_id="prd_never_seen", occupancy_basis="dbl",
                    price_for="adult", pax_count=2, selection_reason="fabricated",
                )
            ],
        )

        async def scenario():
            async with self.session_factory() as session:
                sheet = await self._get_sheet(session)

                async def fake_draft_day(deps, day_context):
                    return draft  # deliberately never records "prd_never_seen" in the allowlist

                with mock.patch.object(draft_run_service, "draft_day", side_effect=fake_draft_day):
                    result = await run_draft(
                        session, sheet=sheet, trip_profile=_sample_trip_profile(), days=self._days(1),
                        day_numbers_filter=None, base_costing_revision=0, actor=ACTOR, idempotency_key="draft-hallucinate",
                    )
                await session.commit()
                return result

        result = asyncio.run(scenario())
        self.assertEqual(result.created_line_ids, [])
        self.assertEqual(result.manual_review_count, 1)

    def test_partial_run_keeps_days_already_done(self):
        good_draft = DayDraftResult(
            day_number=1,
            services=[
                ServiceDraft(
                    category="accommodation", product_id=self.product.id, occupancy_basis="dbl",
                    price_for="adult", pax_count=2, selection_reason="ok",
                )
            ],
        )

        async def scenario():
            async with self.session_factory() as session:
                sheet = await self._get_sheet(session)
                calls = {"n": 0}

                async def fake_draft_day(deps, day_context):
                    calls["n"] += 1
                    if day_context.day_number == 2:
                        raise RuntimeError("provider timeout on day 2")
                    deps.allowlist.record([self.product.id])
                    return good_draft

                with mock.patch.object(draft_run_service, "draft_day", side_effect=fake_draft_day):
                    result = await run_draft(
                        session, sheet=sheet, trip_profile=_sample_trip_profile(), days=self._days(1, 2),
                        day_numbers_filter=None, base_costing_revision=0, actor=ACTOR, idempotency_key="draft-partial",
                    )
                await session.commit()
                return result

        result = asyncio.run(scenario())
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.days_done, [1])
        self.assertEqual(result.days_failed, [2])
        self.assertEqual(len(result.created_line_ids), 1)

    def test_skipped_day_reason_is_not_silent(self):
        empty_draft = DayDraftResult(day_number=1, services=[], skipped_reasons=["no luxury-tier accommodation found for dst_hanoi"])

        async def scenario():
            async with self.session_factory() as session:
                sheet = await self._get_sheet(session)

                async def fake_draft_day(deps, day_context):
                    return empty_draft

                with mock.patch.object(draft_run_service, "draft_day", side_effect=fake_draft_day):
                    result = await run_draft(
                        session, sheet=sheet, trip_profile=_sample_trip_profile(), days=self._days(1),
                        day_numbers_filter=None, base_costing_revision=0, actor=ACTOR, idempotency_key="draft-skip",
                    )
                return result

        result = asyncio.run(scenario())
        self.assertEqual(result.days_done, [1])
        self.assertEqual(result.day_outcomes[0].draft.skipped_reasons, ["no luxury-tier accommodation found for dst_hanoi"])

    def test_idempotent_draft_replays_without_duplicating_lines(self):
        draft = DayDraftResult(
            day_number=1,
            services=[
                ServiceDraft(
                    category="accommodation", product_id=self.product.id, occupancy_basis="dbl",
                    price_for="adult", pax_count=2, selection_reason="ok",
                )
            ],
        )

        async def scenario():
            async with self.session_factory() as session:
                sheet = await self._get_sheet(session)

                async def fake_draft_day(deps, day_context):
                    deps.allowlist.record([self.product.id])
                    return draft

                with mock.patch.object(draft_run_service, "draft_day", side_effect=fake_draft_day) as mocked:
                    first = await run_draft(
                        session, sheet=sheet, trip_profile=_sample_trip_profile(), days=self._days(1),
                        day_numbers_filter=None, base_costing_revision=0, actor=ACTOR, idempotency_key="draft-replay",
                    )
                    await session.commit()
                    second = await run_draft(
                        session, sheet=sheet, trip_profile=_sample_trip_profile(), days=self._days(1),
                        day_numbers_filter=None, base_costing_revision=0, actor=ACTOR, idempotency_key="draft-replay",
                    )
                return first, second, mocked.call_count

        first, second, call_count = asyncio.run(scenario())
        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual(call_count, 1, "the second call must replay, not call the drafter again")

        async def verify():
            async with self.session_factory() as session:
                workbench = await CostingService(session).get_workbench(self.sheet_id)
                self.assertEqual(len(workbench.items), 1)

        asyncio.run(verify())

    def test_revision_race_surfaces_as_conflict(self):
        draft = DayDraftResult(
            day_number=1,
            services=[
                ServiceDraft(
                    category="accommodation", product_id=self.product.id, occupancy_basis="dbl",
                    price_for="adult", pax_count=2, selection_reason="ok",
                )
            ],
        )

        async def scenario():
            async with self.session_factory() as session:
                sheet = await self._get_sheet(session)

                async def fake_draft_day(deps, day_context):
                    deps.allowlist.record([self.product.id])
                    return draft

                with mock.patch.object(draft_run_service, "draft_day", side_effect=fake_draft_day):
                    with self.assertRaises(DraftConflictError):
                        await run_draft(
                            session, sheet=sheet, trip_profile=_sample_trip_profile(), days=self._days(1),
                            day_numbers_filter=None, base_costing_revision=99, actor=ACTOR, idempotency_key="draft-race",
                        )

        asyncio.run(scenario())

    async def _get_sheet(self, session):
        from repositories.costing_repository import CostingRepository

        return await CostingRepository(session).get_sheet_by_id(self.sheet_id)


if __name__ == "__main__":
    unittest.main()
