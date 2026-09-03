import tempfile
import unittest
from datetime import date

from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.product import Product
from db.models.rate import Rate, RatePriceLine
from db.models.supplier import Supplier
from services.ai_platform.deps import CatalogReadOnlyDeps
from services.ai_platform.guardrails import AllowlistRecorder, RunBudget
from services.ai_platform.runtime import run_agent
from services.ai_platform.toolsets.catalog import (
    find_active_rates,
    find_products,
    find_supplier,
    resolve_applicable_rates,
    search_accommodations,
    search_activities_and_dining,
    search_transport,
)


class _FakeRunContext:
    """Duck-types pydantic_ai's RunContext[T] — the tools only ever read ``ctx.deps``."""

    def __init__(self, deps: CatalogReadOnlyDeps) -> None:
        self.deps = deps


class CatalogToolsetTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.database_file.close()
        self.engine = make_test_engine(f"sqlite+aiosqlite:///{self.database_file.name}")
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with self.session_factory() as session:
            session.add(DestinationCatalog(id="dst_hanoi", canonical_name="Hanoi", slug="hanoi"))
            session.add(DestinationCatalog(id="dst_halong", canonical_name="Ha Long", slug="ha-long"))
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
                    title_normalized="la siesta old quarter deluxe room",
                    supplier_id="sup_la_siesta",
                    unit="room",
                    time_basis="night",
                    category_attributes={"quality_tier": "luxury"},
                )
            )
            session.add(
                Product(
                    id="prd_van_16",
                    destination_id="dst_halong",
                    origin_destination_id="dst_hanoi",
                    category="transportation",
                    subcategory="van_16_seat",
                    title="Hanoi -> Ha Long private van",
                    title_normalized="hanoi ha long private van",
                    unit="vehicle",
                    time_basis="day",
                    category_attributes={"seat_capacity": 16},
                )
            )
            session.add(
                Product(
                    id="prd_food_tour",
                    destination_id="dst_hanoi",
                    category="experience",
                    subcategory="food_tour",
                    title="Old Quarter Street Food Tour",
                    title_normalized="old quarter street food tour",
                    unit="person",
                    time_basis="trip",
                    category_attributes={"physical_level": "low"},
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
        results = await find_products(_FakeRunContext(deps), category="flights")
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

    # ── C3: pydantic_ai's default parallel tool-call execution must never touch the
    # shared AsyncSession concurrently (crash / session poisoning risk). ──

    async def test_run_agent_serializes_concurrent_tool_calls_on_shared_session(self):
        """A single model turn that emits two tool calls (routine for a real drafter/resolver
        turn) must not crash the shared ``AsyncSession`` when run through ``runtime.run_agent``.
        """
        deps = self._deps()
        call_count = {"n": 0}

        def _respond(messages, info: AgentInfo) -> ModelResponse:
            call_count["n"] += 1
            if call_count["n"] == 1:
                return ModelResponse(
                    parts=[
                        ToolCallPart(tool_name="find_supplier", args={"name_text": "La Siesta"}, tool_call_id="call_1"),
                        ToolCallPart(tool_name="find_products", args={"category": "accommodation"}, tool_call_id="call_2"),
                    ]
                )
            return ModelResponse(parts=[TextPart(content="done")])

        agent = Agent(
            model=FunctionModel(_respond),
            output_type=str,
            deps_type=CatalogReadOnlyDeps,
            tools=[find_supplier, find_products],
        )

        result = await run_agent(agent, "draft this day", deps=deps)

        assert result.output == "done"
        assert deps.budget.calls == 2
        assert deps.allowlist.contains("sup_la_siesta")
        assert deps.allowlist.contains("prd_deluxe")

    async def test_bare_agent_run_would_crash_on_the_same_concurrent_turn(self):
        """Documents the bug ``run_agent`` fixes: without forcing sequential tool execution,
        pydantic_ai's default parallel scheduling crashes the shared ``AsyncSession``. If this
        stops raising, pydantic_ai's default execution mode changed and ``run_agent``'s
        sequential guard may no longer be necessary — investigate before deleting it.
        """
        from sqlalchemy.exc import InvalidRequestError

        deps = self._deps()

        def _respond(messages, info: AgentInfo) -> ModelResponse:
            return ModelResponse(
                parts=[
                    ToolCallPart(tool_name="find_supplier", args={"name_text": "La Siesta"}, tool_call_id="call_1"),
                    ToolCallPart(tool_name="find_products", args={"category": "accommodation"}, tool_call_id="call_2"),
                ]
            )

        agent = Agent(
            model=FunctionModel(_respond),
            output_type=str,
            deps_type=CatalogReadOnlyDeps,
            tools=[find_supplier, find_products],
        )

        with self.assertRaises(InvalidRequestError):
            await agent.run("draft this day", deps=deps)

    def test_deps_has_no_write_method(self):
        """H7: read-only 'by construction' — recurse one attribute-hop deep, since a facade
        that itself exposes a full read/write repository (or the raw session) would pass a
        shallow ``dir(deps)`` check while still handing tools a write path."""
        forbidden = {"insert", "update", "delete", "create", "commit", "flush", "add", "execute", "session"}
        deps = CatalogReadOnlyDeps(session=None, tenant_id="capella", allowlist=AllowlistRecorder(), budget=RunBudget())

        def _own_attrs(obj) -> list[str]:
            return [name for name in dir(obj) if not name.startswith("_")]

        top_level = _own_attrs(deps)
        assert not any(any(word in name.lower() for word in forbidden) for name in top_level), top_level

        for attr_name in top_level:
            value = getattr(deps, attr_name)
            if not hasattr(value, "__class__") or isinstance(value, (str, int, float, bool, type(None))):
                continue
            nested_attrs = _own_attrs(value)
            assert not any(any(word in name.lower() for word in forbidden) for name in nested_attrs), (
                attr_name,
                nested_attrs,
            )

    # ── Toolset nhóm A (15.7) ──

    async def test_search_accommodations_filters_by_destination_and_tier(self):
        deps = self._deps()
        results = await search_accommodations(_FakeRunContext(deps), "dst_hanoi", quality_tier="luxury")
        assert len(results) == 1
        assert results[0]["product_id"] == "prd_deluxe"
        assert deps.allowlist.contains("prd_deluxe")
        assert all("amount" not in r and "price" not in r for r in results)

    async def test_search_accommodations_never_returns_money_field(self):
        deps = self._deps()
        results = await search_accommodations(_FakeRunContext(deps), "dst_hanoi")
        assert results and all("amount" not in r and "price" not in r and "cost" not in r for r in results)

    async def test_search_transport_filters_by_route_and_capacity(self):
        deps = self._deps()
        results = await search_transport(_FakeRunContext(deps), route_from="dst_hanoi", route_to="dst_halong", pax=8)
        assert len(results) == 1
        assert results[0]["product_id"] == "prd_van_16"
        assert deps.allowlist.contains("prd_van_16")

    async def test_search_transport_excludes_undersized_vehicles(self):
        deps = self._deps()
        results = await search_transport(_FakeRunContext(deps), route_from="dst_hanoi", route_to="dst_halong", pax=20)
        assert results == []

    async def test_search_activities_and_dining_filters_by_mobility(self):
        deps = self._deps()
        results = await search_activities_and_dining(_FakeRunContext(deps), "dst_hanoi", mobility="limited")
        assert any(r["product_id"] == "prd_food_tour" for r in results)
        assert deps.allowlist.contains("prd_food_tour")

    async def test_resolve_applicable_rates_never_returns_amount(self):
        deps = self._deps()
        result = await resolve_applicable_rates(
            _FakeRunContext(deps), "prd_deluxe", service_date="2026-02-14", occupancy="na", pax=1
        )
        assert "amount" not in result and "amount_minor" not in result and "price" not in result
        assert result["tariff_id"] == "rat_winter"
        assert result["rate_missing"] is False
        assert result["has_conflict"] is False
        assert result["price_band"] in ("low", "mid", "high")
        assert deps.allowlist.contains("rat_winter")

    async def test_resolve_applicable_rates_flags_rate_missing(self):
        deps = self._deps()
        result = await resolve_applicable_rates(
            _FakeRunContext(deps), "prd_deluxe", service_date="2027-01-01", occupancy="na", pax=1
        )
        assert result["rate_missing"] is True
        assert result["tariff_id"] is None

    async def test_resolve_applicable_rates_flags_conflict_without_picking_a_winner(self):
        async with self.session_factory() as session:
            session.add(
                Rate(
                    id="rat_promo",
                    product_id="prd_deluxe",
                    currency="USD",
                    rate_basis="net",
                    valid_from=date(2026, 1, 1),
                    valid_to=date(2026, 3, 31),
                    season_name="Promo",
                    lifecycle_status="active",
                )
            )
            session.add(RatePriceLine(rate_id="rat_promo", price_for="adult", occupancy_basis="na", unit="person", amount_minor=500_000))
            await session.commit()

        deps = self._deps()
        result = await resolve_applicable_rates(
            _FakeRunContext(deps), "prd_deluxe", service_date="2026-02-14", occupancy="na", pax=1
        )
        assert result["has_conflict"] is True
        assert result["tariff_id"] is None
        assert result["price_line_id"] is None
