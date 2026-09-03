"""PostgreSQL-only Track 3 concurrency acceptance.

The unit suites deliberately use SQLite for speed. This module exercises the
database-level CAS against two independent PostgreSQL sessions; it is skipped
unless the disposable Track 3 database URL is explicitly supplied.
"""
from __future__ import annotations

import asyncio
import os
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

import db.session as db_session
import main
from core.kernel import ActorRef
from db.base import Base
from db.models.booking import Booking
from db.models.costing import CostingSheet
from db.models.costing_application import CostingApplication
from db.models.outbox import OutboxEvent
from db.models.supplier import Supplier
from repositories.booking_repository import BookingRepository, BookingRevisionRaceError
from repositories.quotation_repository import QuotationRepository
from schemas.v2.costing import ApplyPricingRequestSchema, CostingSheetCreateSchema, ServiceLineCreateSchema
from services.costing_service import CostingConflictError, CostingService


pytestmark = pytest.mark.integration

_ACTOR = ActorRef(actor_id="pg-tester@example.com", actor_type="staff")

_APPLY_PRICING_REQUEST_JSON = {
    "source": {"kind": "manual"},
    "brand_id": "luxury",
    "lang": "en",
    "trip_facts": {
        "start_date": "2026-10-01",
        "end_date": "2026-10-05",
        "duration_days": 5,
        "duration_nights": 4,
        "itinerary": [{"day_number": 1, "title": "Arrival in Hanoi", "destination": "Hanoi"}],
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
    "customer_facts": {"customer_name": "Jane Doe", "adults": 2, "children": 0},
    "service_facts": {"hotels": [], "inclusions": [], "exclusions": []},
    "booking_facts": {"items": []},
    "presentation_options": {"theme_id": "brochure", "renderer": "quote-generator"},
}


async def _seed_apply_pricing_fixture(session: AsyncSession, *, quotation_id: str) -> str:
    """Build one draft quotation with an attached, single-line costing sheet.

    Mirrors ``tests/test_apply_pricing_service.py::_create_test_quotation`` —
    minimal enough to exercise the real ``_apply_costing_pricing_option``
    callback, not a stand-in for it.
    """
    from repositories.quotation_repository import QuotationDocumentRepository

    quotes = QuotationRepository(session)
    quotation = await quotes.create_quotation(
        quotation_id=quotation_id,
        title="PG Concurrency Tour",
        customer_name="Jane Doe",
        brand_id="luxury",
        template_name="quote-generator",
        baseline_lang="en",
        source_kind="manual",
        status="draft",
        quotation_family_id=quotation_id,
        business_version=1,
    )
    await quotes.create_quotation_request(quotation_id=quotation.id, request_json=_APPLY_PRICING_REQUEST_JSON)
    await quotes.create_version_facts(
        quotation_id=quotation.id,
        canonical_facts_json=_APPLY_PRICING_REQUEST_JSON,
        resolved_facts_json={"factsHash": "before-apply"},
        facts_hash="before-apply",
        source_request_id=None,
        source_request_revision=None,
    )
    await QuotationDocumentRepository(session).save_current_document(
        quotation_id=quotation.id,
        lang="en",
        document_json={
            "quotationId": quotation.id,
            "revision": 1,
            "trip": {"title": "PG Concurrency Tour", "durationDays": 5, "durationNights": 4},
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

    costing = CostingService(session)
    sheet = await costing.create_sheet(CostingSheetCreateSchema(quotation_id=quotation.id, currency="USD"), actor=_ACTOR)
    await costing.create_line(
        sheet.id,
        ServiceLineCreateSchema(
            base_costing_revision=0,
            category="accommodation",
            title="Hanoi Hotel",
            unit="room",
            time_basis="night",
            unit_cost_minor=50000,
            cost_currency="USD",
        ),
        actor=_ACTOR,
        idempotency_key="pg-apply-fixture-line",
    )
    await session.commit()
    return sheet.id


def _postgres_url() -> str:
    url = os.environ.get("TRACK3_POSTGRES_TEST_URL")
    if not url:
        pytest.skip("TRACK3_POSTGRES_TEST_URL is required for PostgreSQL concurrency acceptance")
    if not url.startswith("postgresql+asyncpg://"):
        pytest.fail("TRACK3_POSTGRES_TEST_URL must use the postgresql+asyncpg dialect")
    return url


def test_postgres_stale_booking_revision_cas_allows_exactly_one_writer() -> None:
    """Two stale ORM sessions must not both advance ``booking_revision``."""

    async def scenario() -> None:
        engine = make_test_engine(_postgres_url())
        sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
                await connection.run_sync(Base.metadata.create_all)

            async with sessions() as setup:
                quotations = QuotationRepository(setup)
                quotation = await quotations.create_quotation(
                    quotation_id="qtn_pg_cas",
                    brand_id="brand_capella",
                    template_name="quote-generator",
                    baseline_lang="en",
                    quotation_family_id="qtn_pg_cas",
                    business_version=1,
                )
                setup.add(CostingSheet(id="cst_pg_cas", quotation_id=quotation.id, currency="USD"))
                # No ORM `relationship()` connects Booking.sheet_id to CostingSheet —
                # only a raw FK column — so SQLAlchemy's flush-order dependency sort
                # cannot see the dependency and may insert Booking first. SQLite's
                # deferred-enough per-statement FK check tolerated that; Postgres
                # enforces it immediately, so the sheet must be flushed before the
                # dependent Booking row is added.
                await setup.flush()
                setup.add(
                    Booking(
                        id="bkg_pg_cas",
                        quotation_id=quotation.id,
                        sheet_id="cst_pg_cas",
                        booking_code="BK-2026-0001",
                        deposit_received_at=date(2026, 6, 1),
                    )
                )
                await setup.commit()

            async with sessions() as first, sessions() as second:
                first_repo = BookingRepository(first)
                second_repo = BookingRepository(second)
                first_booking = await first_repo.get_booking_by_id("bkg_pg_cas")
                second_booking = await second_repo.get_booking_by_id("bkg_pg_cas")
                assert first_booking is not None and second_booking is not None
                assert first_booking.booking_revision == second_booking.booking_revision == 0

                await first_repo.reserve_revision(first_booking, expected_revision=0)
                await first.commit()
                with pytest.raises(BookingRevisionRaceError):
                    await second_repo.reserve_revision(second_booking, expected_revision=0)
                await second.rollback()

            async with sessions() as verify:
                revision = await BookingRepository(verify).get_booking_revision("bkg_pg_cas")
                assert revision == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_postgres_counter_allocates_twenty_distinct_contiguous_values_under_concurrency() -> None:
    """H3: the counter's first-insert race must resolve via savepoint, never a
    transaction-wide ``session.rollback()`` — and the resulting sequence must be
    dense (1..20), proving no value is skipped or duplicated under real
    concurrent connections racing to create the year's counter row."""

    async def scenario() -> None:
        engine = make_test_engine(_postgres_url())
        sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
                await connection.run_sync(Base.metadata.create_all)

            async def _mint() -> int:
                async with sessions() as session:
                    value = await BookingRepository(session).next_business_code_sequence(code_type="VC", year=2026)
                    await session.commit()
                    return value

            results = await asyncio.gather(*(_mint() for _ in range(20)))
            assert sorted(results) == list(range(1, 21))
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_postgres_concurrent_apply_pricing_same_revisions_only_one_commits() -> None:
    """Dual-CAS acceptance (15.5 chốt #5, Exit Gate #3): two independent
    PostgreSQL connections applying the same sheet at the same
    (``baseRevision``, ``baseCostingRevision``) pair must not both commit — the
    loser observes a real row-lock wait on ``costing_sheets`` from
    ``verify_revision_guarded``, not a race that both sides win under
    READ COMMITTED. Exactly one ``costing_applications`` row and one
    ``costing.applied`` outbox event survive."""

    async def scenario() -> None:
        engine = make_test_engine(_postgres_url())
        sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        session_factory_patch = patch.object(db_session, "get_session_factory", return_value=sessions)
        main_session_factory_patch = patch.object(main, "_get_db_session_factory", return_value=sessions)
        session_factory_patch.start()
        main_session_factory_patch.start()
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
                await connection.run_sync(Base.metadata.create_all)

            async with sessions() as setup:
                await main._seed_destination_catalog(setup)
                setup.add(
                    Supplier(
                        id="sup_pg_apply",
                        name="PG Test Supplier",
                        name_normalized="pg test supplier",
                        supplier_type="direct",
                        default_currency="USD",
                    )
                )
                await setup.commit()
                sheet_id = await _seed_apply_pricing_fixture(setup, quotation_id="qtn_pg_apply")

            async def _apply(idempotency_key: str) -> str | None:
                async with sessions() as session:
                    try:
                        await CostingService(session).apply_pricing(
                            sheet_id,
                            ApplyPricingRequestSchema(base_revision=1, base_costing_revision=1, target_option_id="opt_1"),
                            actor=_ACTOR,
                            idempotency_key=idempotency_key,
                        )
                        await session.commit()
                        return None
                    except CostingConflictError as err:
                        await session.rollback()
                        return str(err)

            outcomes = await asyncio.gather(
                _apply("pg-apply-race-a"), _apply("pg-apply-race-b"), return_exceptions=False
            )
            assert sorted(outcome is None for outcome in outcomes) == [False, True]

            async with sessions() as verify:
                apps = (
                    await verify.execute(select(CostingApplication).where(CostingApplication.sheet_id == sheet_id))
                ).scalars().all()
                assert len(apps) == 1

                events = (
                    await verify.execute(select(OutboxEvent).where(OutboxEvent.event_type == "costing.applied"))
                ).scalars().all()
                assert len(events) == 1
        finally:
            main_session_factory_patch.stop()
            session_factory_patch.stop()
            await engine.dispose()

    asyncio.run(scenario())
