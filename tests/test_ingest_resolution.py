import os
import tempfile
import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

from db.base import Base
from db.models.destination import DestinationAlias, DestinationCatalog
from db.models.product import Product
from db.models.rate import Rate, RatePriceLine
from db.models.supplier import Supplier
from schemas.catalog_ingest import (
    CatalogIngestPayload,
    ProductCandidate,
    RateGroupCandidate,
    ResolutionEntry,
    ResolutionPlan,
    SupplierCandidate,
)
from services.ai_platform.guardrails import AllowlistRecorder
from services.ingestion.extraction_service import parse_payload
from services.ingestion.resolution_service import verify_plan
from services.product_service import normalize_product_title


class IngestResolutionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.database_file.close()
        self.engine = make_test_engine(f"sqlite+aiosqlite:///{self.database_file.name}")
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with self.session_factory() as session:
            session.add(DestinationCatalog(id="dst_hanoi", canonical_name="Hanoi", slug="hanoi"))
            await session.flush()
            session.add(DestinationAlias(id="dal_hanoi", destination_id="dst_hanoi", normalized_alias="hanoi"))
            session.add(
                Supplier(
                    id="sup_la_siesta",
                    name="La Siesta Hotel Group",
                    name_normalized="la siesta hotel group",
                    supplier_type="direct",
                    default_currency="USD",
                )
            )
            await session.flush()
            session.add(
                Product(
                    id="prd_deluxe",
                    destination_id="dst_hanoi",
                    category="accommodation",
                    title="La Siesta Old Quarter — Deluxe Room",
                    title_normalized=normalize_product_title("La Siesta Old Quarter — Deluxe Room"),
                    supplier_id="sup_la_siesta",
                    unit="room",
                    time_basis="night",
                )
            )
            await session.flush()
            session.add(
                Rate(
                    id="rat_winter",
                    product_id="prd_deluxe",
                    currency="USD",
                    rate_basis="net",
                    valid_from=date(2026, 1, 1),
                    valid_to=date(2026, 3, 31),
                    season_name="Winter 2026",
                    lifecycle_status="active",
                )
            )
            await session.flush()
            session.add(RatePriceLine(rate_id="rat_winter", price_for="adult", occupancy_basis="na", unit="person", amount_minor=1_000_000))
            await session.commit()

        self.session = self.session_factory()

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()
        os.unlink(self.database_file.name)

    async def test_supplier_create_downgraded_to_needs_input_on_dedupe_match(self):
        payload = CatalogIngestPayload(
            supplier=SupplierCandidate(name_text="La Siesta Hotel Group", source_quote="La Siesta Hotel Group"),
        )
        plan = ResolutionPlan(
            entries=[ResolutionEntry(entity_ref="/supplier", entity_type="supplier", action="create", evidence="looks new")]
        )
        verified = await verify_plan(self.session, "capella", payload, {}, plan, AllowlistRecorder())
        assert verified[0].action == "needs_input"
        assert verified[0].matched_id == "sup_la_siesta"
        assert verified[0].clarifications[0].blocking is True

    async def test_supplier_create_confirmed_when_no_dedupe_match(self):
        payload = CatalogIngestPayload(
            supplier=SupplierCandidate(name_text="Brand New Supplier Co", source_quote="Brand New Supplier Co"),
        )
        plan = ResolutionPlan(
            entries=[ResolutionEntry(entity_ref="/supplier", entity_type="supplier", action="create", evidence="looks new")]
        )
        verified = await verify_plan(self.session, "capella", payload, {}, plan, AllowlistRecorder())
        assert verified[0].action == "create"
        assert verified[0].clarifications == []

    async def test_matched_id_not_in_allowlist_is_stripped(self):
        payload = CatalogIngestPayload(
            supplier=SupplierCandidate(name_text="Brand New Supplier Co", source_quote="Brand New Supplier Co"),
        )
        plan = ResolutionPlan(
            entries=[
                ResolutionEntry(
                    entity_ref="/supplier", entity_type="supplier", action="update", matched_id="sup_invented", evidence="hallucinated"
                )
            ]
        )
        verified = await verify_plan(self.session, "capella", payload, {}, plan, AllowlistRecorder())
        assert verified[0].matched_id is None
        assert verified[0].action == "needs_input"

    async def test_product_missing_category_hint_needs_input(self):
        payload = CatalogIngestPayload(
            products=[ProductCandidate(title_text="New Villa", destination_text="Hanoi", source_quote="New Villa in Hanoi")],
        )
        plan = ResolutionPlan(
            entries=[ResolutionEntry(entity_ref="/products/0", entity_type="product", action="create", evidence="looks new")]
        )
        verified = await verify_plan(self.session, "capella", payload, {}, plan, AllowlistRecorder())
        assert verified[0].action == "needs_input"
        assert "category" in verified[0].evidence.lower()

    async def test_product_unresolvable_destination_needs_input(self):
        payload = CatalogIngestPayload(
            products=[
                ProductCandidate(
                    title_text="New Villa", destination_text="Nowhereland", category_hint="accommodation", source_quote="New Villa"
                )
            ],
        )
        plan = ResolutionPlan(
            entries=[ResolutionEntry(entity_ref="/products/0", entity_type="product", action="create", evidence="looks new")]
        )
        verified = await verify_plan(self.session, "capella", payload, {}, plan, AllowlistRecorder())
        assert verified[0].action == "needs_input"
        assert "destination" in verified[0].evidence.lower()

    async def test_rate_group_season_window_without_year_needs_input(self):
        payload = CatalogIngestPayload(
            rate_groups=[
                RateGroupCandidate(product_title_text="La Siesta Old Quarter — Deluxe Room", validity_text="01/10-30/04", source_quote="01/10-30/04")
            ],
        )
        _, parsed = parse_payload(payload)
        plan = ResolutionPlan(
            entries=[ResolutionEntry(entity_ref="/rate_groups/0", entity_type="rate", action="create", evidence="new season")]
        )
        verified = await verify_plan(self.session, "capella", payload, parsed, plan, AllowlistRecorder())
        assert verified[0].action == "needs_input"
        assert "year" in verified[0].evidence.lower()

    async def test_rate_group_overlap_downgrades_create_to_needs_input(self):
        payload = CatalogIngestPayload(
            supplier=SupplierCandidate(name_text="La Siesta Hotel Group", source_quote="La Siesta Hotel Group"),
            products=[
                ProductCandidate(
                    title_text="La Siesta Old Quarter — Deluxe Room",
                    destination_text="Hanoi",
                    category_hint="accommodation",
                    source_quote="La Siesta Old Quarter Deluxe Room",
                )
            ],
            rate_groups=[
                RateGroupCandidate(
                    product_title_text="La Siesta Old Quarter — Deluxe Room",
                    validity_text="15/02/2026 - 15/03/2026",
                    source_quote="15/02/2026 - 15/03/2026",
                )
            ],
        )
        _, parsed = parse_payload(payload)
        allowlist = AllowlistRecorder()
        allowlist.record(["sup_la_siesta", "prd_deluxe"])
        plan = ResolutionPlan(
            entries=[
                ResolutionEntry(
                    entity_ref="/supplier", entity_type="supplier", action="skip_duplicate", matched_id="sup_la_siesta", evidence="matches existing"
                ),
                ResolutionEntry(
                    entity_ref="/products/0", entity_type="product", action="update", matched_id="prd_deluxe", evidence="matches existing"
                ),
                ResolutionEntry(entity_ref="/rate_groups/0", entity_type="rate", action="create", evidence="new season"),
            ]
        )
        verified = await verify_plan(self.session, "capella", payload, parsed, plan, allowlist)
        rate_entry = next(e for e in verified if e.entity_type == "rate")
        assert rate_entry.action == "needs_input"
        assert "overlap" in rate_entry.evidence.lower()
        assert rate_entry.clarifications[0].options == ["supersede", "different_category"]

    async def test_rate_group_overlap_resolved_by_supersede_override(self):
        payload = CatalogIngestPayload(
            supplier=SupplierCandidate(name_text="La Siesta Hotel Group", source_quote="La Siesta Hotel Group"),
            products=[
                ProductCandidate(
                    title_text="La Siesta Old Quarter — Deluxe Room",
                    destination_text="Hanoi",
                    category_hint="accommodation",
                    source_quote="La Siesta Old Quarter Deluxe Room",
                )
            ],
            rate_groups=[
                RateGroupCandidate(
                    product_title_text="La Siesta Old Quarter — Deluxe Room",
                    validity_text="15/02/2026 - 15/03/2026",
                    source_quote="15/02/2026 - 15/03/2026",
                )
            ],
        )
        _, parsed = parse_payload(payload)
        allowlist = AllowlistRecorder()
        allowlist.record(["sup_la_siesta", "prd_deluxe"])
        plan = ResolutionPlan(
            entries=[
                ResolutionEntry(
                    entity_ref="/supplier", entity_type="supplier", action="skip_duplicate", matched_id="sup_la_siesta", evidence="matches existing"
                ),
                ResolutionEntry(
                    entity_ref="/products/0", entity_type="product", action="update", matched_id="prd_deluxe", evidence="matches existing"
                ),
                ResolutionEntry(entity_ref="/rate_groups/0", entity_type="rate", action="create", evidence="new season"),
            ]
        )
        verified = await verify_plan(
            self.session, "capella", payload, parsed, plan, allowlist, {"rate-0-overlap": "supersede"}
        )
        rate_entry = next(e for e in verified if e.entity_type == "rate")
        assert rate_entry.action == "supersede_rate"
        assert rate_entry.clarifications == []
