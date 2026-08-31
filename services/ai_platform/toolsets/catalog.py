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

from services.ai_platform.deps import CatalogReadOnlyDeps
from services.product_service import normalize_product_title
from services.supplier_service import normalize_supplier_name


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
        product_id, tenant_id=ctx.deps.tenant_id, lifecycle="active", limit=50
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
