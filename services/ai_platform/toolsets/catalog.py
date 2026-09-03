"""Toolset nhóm B (15.8 §1.5) — read-only catalog lookup tools for the Resolver Co-Pilot.

Each tool wraps a real repository call — no invented SQL, no new query surface. ``tenant_id``
always comes from ``deps.tenant_id`` (set by the caller), never from the LLM. Every id
returned is recorded in ``deps.allowlist`` so a later ``matched_id`` proposal can be checked
against ids the agent actually saw. No tool here ever returns a money amount.

Toolset nhóm A (drafter search tools) is 15.7's job to add to this same file — 15.8
deliberately does not build ahead of what it does not use.
"""
from __future__ import annotations

from datetime import date

from pydantic_ai import RunContext

from core.rules.rate_selection import pick_price_line, select_rates
from services.ai_platform.deps import CatalogReadOnlyDeps
from services.product_service import normalize_product_title
from services.supplier_service import normalize_supplier_name
from services.rate_candidates import rate_candidates_from_rows


def _budget_exhausted_notice() -> list[dict]:
    """Returned instead of a real result once the run's tool-call budget is used up.

    Deliberately a normal (non-exception) tool result: raising here would abort the whole
    agent run via pydantic_ai's tool-error handling. Returning this lets the model see it
    has run out of lookups and finalize its best answer (propose ``needs_input`` for
    anything still unconfirmed) instead of crashing the batch.
    """
    return [{"note": "Tool-call budget exhausted for this run — stop searching and finalize your ResolutionPlan now."}]


async def find_supplier(ctx: RunContext[CatalogReadOnlyDeps], name_text: str) -> list[dict]:
    """Fuzzy-match suppliers by name. Returns up to 3 candidates, never a money field."""
    if not ctx.deps.budget.has_budget():
        return _budget_exhausted_notice()
    ctx.deps.budget.record_call()
    normalized = normalize_supplier_name(name_text)
    suppliers, _total = await ctx.deps.supplier_repository.list(
        tenant_id=ctx.deps.tenant_id, active_only=None, search=normalized, limit=3
    )
    candidates = suppliers[:3]
    ctx.deps.allowlist.record(s.id for s in candidates)
    return [
        {"supplier_id": s.id, "name": s.name, "destination": s.city or s.country, "is_active": s.is_active}
        for s in candidates
    ]


async def find_products(
    ctx: RunContext[CatalogReadOnlyDeps],
    supplier_id: str | None = None,
    destination_id: str | None = None,
    category: str | None = None,
    title_text: str | None = None,
) -> list[dict]:
    """Look up products by supplier/destination/category/fuzzy title. Up to 8 candidates."""
    if not ctx.deps.budget.has_budget():
        return _budget_exhausted_notice()
    ctx.deps.budget.record_call()
    search = normalize_product_title(title_text) if title_text else ""
    products, _total = await ctx.deps.product_repository.list(
        tenant_id=ctx.deps.tenant_id,
        active_only=None,
        category=category,
        destination_id=destination_id,
        supplier_id=supplier_id,
        search=search,
        limit=8,
    )
    candidates = products[:8]
    ctx.deps.allowlist.record(p.id for p in candidates)
    return [
        {
            "product_id": p.id,
            "title": p.title,
            "category": p.category,
            "subcategory": p.subcategory,
            "supplier_id": p.supplier_id,
            "is_active": p.is_active,
        }
        for p in candidates
    ]


async def find_active_rates(
    ctx: RunContext[CatalogReadOnlyDeps],
    product_id: str,
    window_from: str | None = None,
    window_to: str | None = None,
) -> list[dict]:
    """Look up active rates for a product, optionally overlapping [window_from, window_to].

    Never returns a price — only season/validity/lifecycle, up to 5 candidates.
    """
    if not ctx.deps.budget.has_budget():
        return _budget_exhausted_notice()
    ctx.deps.budget.record_call()
    rates, _total = await ctx.deps.rate_repository.list_by_product(
        product_id, tenant_id=ctx.deps.tenant_id, lifecycle="active"
    )
    if window_from and window_to:
        try:
            start, end = date.fromisoformat(window_from), date.fromisoformat(window_to)
        except ValueError:
            start = end = None
        if start is not None and end is not None:
            rates = [r for r in rates if r.valid_from <= end and start <= r.valid_to]
    candidates = rates[:5]
    ctx.deps.allowlist.record(r.id for r in candidates)
    return [
        {
            "tariff_id": r.id,
            "season": r.season_name,
            "validity": {"valid_from": r.valid_from.isoformat(), "valid_to": r.valid_to.isoformat()},
            "lifecycle": r.lifecycle_status,
        }
        for r in candidates
    ]


CATALOG_TOOLSET_B = [find_supplier, find_products, find_active_rates]


# ── Toolset nhóm A (15.7 §1.4) — Service Drafter search tools ──


async def search_accommodations(
    ctx: RunContext[CatalogReadOnlyDeps],
    destination_id: str,
    quality_tier: str | None = None,
    room_config: str | None = None,
    meal_plan: str | None = None,
) -> list[dict]:
    """Search accommodation products for a destination. Up to 8 candidates, never a money field.

    ``destination_id`` is resolved through the 15.2b merge chain (``effective_destination_id``)
    before querying so a merged-away destination id still finds products.
    """
    if not ctx.deps.budget.has_budget():
        return _budget_exhausted_notice()
    ctx.deps.budget.record_call()
    effective_id = await ctx.deps.destination_repository.effective_destination_id(destination_id)
    products, _total = await ctx.deps.product_repository.list(
        tenant_id=ctx.deps.tenant_id, active_only=True, category="accommodation", destination_id=effective_id, limit=8
    )
    candidates = list(products)
    if quality_tier:
        tiered = [p for p in candidates if p.category_attributes.get("quality_tier") == quality_tier]
        candidates = tiered or candidates
    if meal_plan:
        with_meal = [p for p in candidates if p.category_attributes.get("meal_plan") == meal_plan]
        candidates = with_meal or candidates
    candidates = candidates[:8]
    ctx.deps.allowlist.record(p.id for p in candidates)
    return [
        {
            "product_id": p.id,
            "title": p.title,
            "property_id": p.property_id,
            "tier": p.category_attributes.get("quality_tier"),
            "room_types": p.category_attributes.get("room_types", []),
        }
        for p in candidates
    ]


async def search_transport(
    ctx: RunContext[CatalogReadOnlyDeps],
    route_from: str,
    route_to: str,
    pax: int,
    comfort: str | None = None,
) -> list[dict]:
    """Search transportation products for a route. Up to 8 candidates, never a money field."""
    if not ctx.deps.budget.has_budget():
        return _budget_exhausted_notice()
    ctx.deps.budget.record_call()
    origin_id = await ctx.deps.destination_repository.effective_destination_id(route_from)
    arrival_id = await ctx.deps.destination_repository.effective_destination_id(route_to)
    products, _total = await ctx.deps.product_repository.list(
        tenant_id=ctx.deps.tenant_id, active_only=True, category="transportation", destination_id=arrival_id, limit=8
    )
    candidates = [p for p in products if (p.origin_destination_id or arrival_id) == origin_id or p.origin_destination_id == origin_id]
    # Capacity is a hard constraint, unlike the soft preference filters below — a vehicle that
    # cannot seat the party is never an acceptable candidate, so no "fall back to unfiltered".
    candidates = [p for p in candidates if int(p.category_attributes.get("seat_capacity") or 0) >= pax]
    if comfort:
        comfy = [p for p in candidates if p.category_attributes.get("comfort") == comfort]
        candidates = comfy or candidates
    candidates = candidates[:8]
    ctx.deps.allowlist.record(p.id for p in candidates)
    return [
        {
            "product_id": p.id,
            "title": p.title,
            "subcategory": p.subcategory,
            "seat_capacity": p.category_attributes.get("seat_capacity"),
        }
        for p in candidates
    ]


async def search_activities_and_dining(
    ctx: RunContext[CatalogReadOnlyDeps],
    destination_id: str,
    tags: list[str] | None = None,
    pace: str | None = None,
    mobility: str | None = None,
) -> list[dict]:
    """Search experience/meal/ticket products for a destination. Up to 8 candidates, never a
    money field. ``mobility`` filters out candidates whose ``physical_level`` exceeds it."""
    if not ctx.deps.budget.has_budget():
        return _budget_exhausted_notice()
    ctx.deps.budget.record_call()
    effective_id = await ctx.deps.destination_repository.effective_destination_id(destination_id)
    candidates: list = []
    for category in ("experience", "meal", "ticket"):
        products, _total = await ctx.deps.product_repository.list(
            tenant_id=ctx.deps.tenant_id, active_only=True, category=category, destination_id=effective_id, limit=8
        )
        candidates.extend(products)
    if mobility and mobility != "full":
        candidates = [p for p in candidates if p.category_attributes.get("physical_level", "full") in ("low", mobility)] or candidates
    if tags:
        tagged = [p for p in candidates if set(p.category_attributes.get("tags", [])) & set(tags)]
        candidates = tagged or candidates
    candidates = candidates[:8]
    ctx.deps.allowlist.record(p.id for p in candidates)
    return [
        {"product_id": p.id, "title": p.title, "category": p.category, "subcategory": p.subcategory}
        for p in candidates
    ]


def _rate_candidates_for_product(rate_rows):
    """Compatibility export for existing callers during the mapper migration."""
    return rate_candidates_from_rows(rate_rows)


async def resolve_applicable_rates(
    ctx: RunContext[CatalogReadOnlyDeps],
    product_id: str,
    service_date: str,
    occupancy: str,
    pax: int,
) -> dict:
    """Wrap ``rate_selection.select_rates`` + ``pick_price_line`` (15.3, pure) so the drafter
    can see whether a product is bookable on a date WITHOUT ever seeing an amount.

    Returns ``price_band`` (low/mid/high, server-computed by relative amount rank among the
    product's own price lines) instead of a real number, so the model can reason about relative
    budget fit without any path to a hallucinated price.
    """
    if not ctx.deps.budget.has_budget():
        return {"note": "Tool-call budget exhausted for this run — stop searching and finalize your ServiceDraft now."}
    ctx.deps.budget.record_call()
    try:
        local_date = date.fromisoformat(service_date)
    except ValueError:
        return {"tariff_id": None, "price_line_id": None, "has_conflict": False, "rate_missing": True, "price_band": None}

    rate_rows, _total = await ctx.deps.rate_repository.list_by_product(
        product_id, tenant_id=ctx.deps.tenant_id, lifecycle="active"
    )
    candidates = rate_candidates_from_rows(rate_rows)
    selection = select_rates(candidates, local_date, pax)

    if not selection.candidates:
        return {"tariff_id": None, "price_line_id": None, "has_conflict": False, "rate_missing": True, "price_band": None}
    if selection.has_conflict:
        ctx.deps.allowlist.record(c.rate_id for c in selection.candidates)
        return {"tariff_id": None, "price_line_id": None, "has_conflict": True, "rate_missing": False, "price_band": None}

    chosen = selection.candidates[0]
    line_selection = pick_price_line(list(chosen.lines), "adult", occupancy, pax)
    if not line_selection.candidates or line_selection.has_conflict:
        return {"tariff_id": chosen.rate_id, "price_line_id": None, "has_conflict": False, "rate_missing": True, "price_band": None}
    line = line_selection.candidates[0]

    all_amounts = sorted(price_line.amount_minor for price_line in chosen.lines) or [line.amount_minor]
    rank = all_amounts.index(line.amount_minor) / max(1, len(all_amounts) - 1)
    price_band = "low" if rank < 0.34 else "high" if rank > 0.66 else "mid"

    ctx.deps.allowlist.record([chosen.rate_id])
    return {
        "tariff_id": chosen.rate_id,
        "price_line_id": None,
        "has_conflict": False,
        "rate_missing": False,
        "price_band": price_band,
    }


CATALOG_TOOLSET_A = [search_accommodations, search_transport, search_activities_and_dining, resolve_applicable_rates]
