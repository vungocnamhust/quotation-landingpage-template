import tempfile
import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.product import Product
from db.models.rate import Rate, RatePriceLine
from db.models.supplier import Supplier
from services.ai_platform.deps import CatalogReadOnlyDeps
from services.ai_platform.guardrails import AllowlistRecorder, RunBudget
from services.ai_platform.toolsets.catalog import find_active_rates, find_products, find_supplier


class _FakeRunContext:
    """Duck-types pydantic_ai's RunContext[T] — the tools only ever read ``ctx.deps``."""

    def __init__(self, deps: CatalogReadOnlyDeps) -> None:
        self.deps = deps


class CatalogToolsetTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.database_file.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.database_file.name}")
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as connection:
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
            session.add(
                Product(
                    id="prd_deluxe",
                    destination_id="dst_hanoi",
                    category="accommodation",
                    title="La Siesta Old Quarter — Deluxe Room",
                    title_normalized="la siesta old quarter deluxe room",
                    supplier_id="sup_la_siesta",
                    unit="room",
                    time_basis="night",
                )
            )
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
            session.add(RatePriceLine(rate_id="rat_winter", price_for="adult", occupancy_basis="na", unit="person", amount_minor=1_000_000))
            await session.commit()

        self.session = self.session_factory()

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()
        import os

        os.unlink(self.database_file.name)

    def _deps(self) -> CatalogReadOnlyDeps:
        return CatalogReadOnlyDeps(session=self.session, tenant_id="capella", allowlist=AllowlistRecorder(), budget=RunBudget(max_calls=10))

    async def test_find_supplier_matches_and_records_allowlist(self):
        deps = self._deps()
        results = await find_supplier(_FakeRunContext(deps), "La Siesta")
        assert len(results) == 1
        assert results[0]["supplier_id"] == "sup_la_siesta"
        assert deps.allowlist.contains("sup_la_siesta")

    async def test_find_supplier_never_returns_money_field(self):
        deps = self._deps()
        results = await find_supplier(_FakeRunContext(deps), "La Siesta")
        assert all("amount" not in r and "price" not in r for r in results)

    async def test_find_products_filters_by_category(self):
        deps = self._deps()
        results = await find_products(_FakeRunContext(deps), category="transportation")
        assert results == []
        results = await find_products(_FakeRunContext(deps), category="accommodation")
        assert len(results) == 1
        assert deps.allowlist.contains("prd_deluxe")

    async def test_find_active_rates_never_returns_amount(self):
        deps = self._deps()
        results = await find_active_rates(_FakeRunContext(deps), "prd_deluxe")
        assert len(results) == 1
        assert "amount_minor" not in results[0]
        assert "amount" not in results[0]
        assert results[0]["tariff_id"] == "rat_winter"
        assert deps.allowlist.contains("rat_winter")

    async def test_find_active_rates_filters_by_window_overlap(self):
        deps = self._deps()
        no_overlap = await find_active_rates(_FakeRunContext(deps), "prd_deluxe", window_from="2026-06-01", window_to="2026-08-31")
        assert no_overlap == []
        overlap = await find_active_rates(_FakeRunContext(deps), "prd_deluxe", window_from="2026-02-01", window_to="2026-02-28")
        assert len(overlap) == 1

    async def test_budget_is_incremented_per_call(self):
        deps = self._deps()
        await find_supplier(_FakeRunContext(deps), "La Siesta")
        await find_products(_FakeRunContext(deps), category="accommodation")
        assert deps.budget.calls == 2

    def test_deps_has_no_write_method(self):
        forbidden = {"insert", "update", "delete", "create", "commit"}
        deps = CatalogReadOnlyDeps(session=None, tenant_id="capella", allowlist=AllowlistRecorder(), budget=RunBudget())
        own_attrs = [name for name in dir(deps) if not name.startswith("_")]
        assert not any(any(word in name.lower() for word in forbidden) for name in own_attrs), own_attrs
