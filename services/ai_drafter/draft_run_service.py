"""Draft Run orchestration (15.7 §1.1/§1.6/§1.7) — TripAnalyst (human-reviewed) ->
per-day ServiceDrafter -> independent server-side rate resolution -> ``costing_service.create_line``.

Nguyên tắc tối thượng: AI has no direct write path. Every line lands through the exact same
``CostingService.create_line`` a human uses — same CAS, same idempotency, same validators. This
module never trusts an agent's own ``tariff_id``/``price_line_id`` hint for money: it always
re-resolves price from scratch via ``core.rules.rate_selection`` (chốt #1/#2).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef, generate_id
from core.rules.rate_selection import pick_price_line, select_rates
from db.models.ai_run import AiRun
from db.models.costing import CostingSheet
from repositories.product_repository import ProductRepository
from repositories.rate_repository import RateRepository
from services.rate_candidates import rate_candidates_from_rows
from schemas.service_draft import DayDraftResult
from schemas.trip_profile import TripProfile
from schemas.v2.ai_drafter import DraftDayOutcomeSchema, DraftDaySpecSchema, DraftResponseSchema
from schemas.v2.costing import ServiceLineWriteSchema
from services.ai_drafter.service_drafter import build_day_context, draft_day
from services.ai_platform.deps import CatalogReadOnlyDeps
from services.ai_platform.guardrails import AllowlistRecorder, RunBudget
from services.costing_service import CostingConflictError, CostingService, CostingValidationError

AGENT_NAME = "service_drafter"
DEFAULT_TENANT_ID = "capella"
ANCHOR_TYPE = "costing_sheet"
ID_PREFIX = "air"


class DraftRunError(RuntimeError):
    pass


class DraftValidationError(DraftRunError):
    pass


class DraftConflictError(DraftRunError):
    def __init__(self, message: str, *, current_revision: int) -> None:
        super().__init__(message)
        self.current_revision = current_revision


async def find_existing_run(
    session: AsyncSession, *, anchor_id: str, idempotency_key: str, tenant_id: str = DEFAULT_TENANT_ID
) -> AiRun | None:
    stmt = select(AiRun).where(
        AiRun.tenant_id == tenant_id,
        AiRun.anchor_type == ANCHOR_TYPE,
        AiRun.anchor_id == anchor_id,
        AiRun.idempotency_key == idempotency_key,
    )
    return await session.scalar(stmt)


async def list_runs(session: AsyncSession, *, sheet_id: str, tenant_id: str = DEFAULT_TENANT_ID) -> list[AiRun]:
    stmt = (
        select(AiRun)
        .where(AiRun.tenant_id == tenant_id, AiRun.anchor_type == ANCHOR_TYPE, AiRun.anchor_id == sheet_id)
        .order_by(AiRun.created_at.desc())
    )
    result = await session.scalars(stmt)
    return list(result.all())


async def _insert_run_record(
    session: AsyncSession,
    *,
    run_id: str,
    anchor_id: str,
    status: str,
    idempotency_key: str,
    input_ref: dict[str, Any],
    output: dict[str, Any],
    stats: dict[str, Any],
    actor: ActorRef,
    tenant_id: str,
) -> AiRun:
    """Mirrors ``services.ai_platform.runs.record_run`` but accepts a pre-chosen id so the
    run's own id can be embedded into each line's ``ai_meta_json`` before the row exists —
    ``runs.py`` itself is never modified (15.7 §1.2 boundary)."""
    run = AiRun(
        id=run_id,
        tenant_id=tenant_id,
        agent_name=AGENT_NAME,
        anchor_type=ANCHOR_TYPE,
        anchor_id=anchor_id,
        status=status,
        idempotency_key=idempotency_key,
        input_ref_json=input_ref,
        output_json=output,
        stats_json=stats,
        created_by=actor.serialize(),
        updated_by=actor.serialize(),
    )
    session.add(run)
    await session.flush()
    return run


async def _resolve_price_serverside(
    session: AsyncSession,
    tenant_id: str,
    *,
    product_id: str,
    service_date: date,
    occupancy_basis: str,
    price_for: str,
    pax_count: int,
) -> tuple[str | None, int | None, set[str]]:
    """Returns ``(tariff_id, price_line_id, flags)``. Never trusts anything from the LLM —
    re-derives everything from ``rate_selection`` against rates freshly loaded from the DB."""
    rate_rows, _total = await RateRepository(session).list_by_product(
        product_id, tenant_id=tenant_id, lifecycle="active"
    )
    candidates = rate_candidates_from_rows(rate_rows)
    selection = select_rates(candidates, service_date, pax_count)

    if not selection.candidates:
        return None, None, {"rate_missing"}
    if selection.has_conflict:
        return None, None, {"rate_conflict"}

    chosen = selection.candidates[0]
    line_selection = pick_price_line(list(chosen.lines), price_for, occupancy_basis, pax_count)
    if not line_selection.candidates:
        return chosen.rate_id, None, {"rate_missing"}
    if line_selection.has_conflict:
        return chosen.rate_id, None, {"rate_conflict"}
    price_line = line_selection.candidates[0]

    raw_rate = next((r for r in rate_rows if r.id == chosen.rate_id), None)
    flags: set[str] = set()
    if raw_rate is not None:
        for supplement in raw_rate.supplements_json or []:
            applies_from = date.fromisoformat(supplement["applies_from"])
            applies_to = date.fromisoformat(supplement["applies_to"])
            if applies_from <= service_date <= applies_to:
                flags.add("has_supplement_in_range")
                break

    orm_line = next(
        (
            line
            for line in raw_rate.lines
            if line.price_for == price_line.price_for
            and line.occupancy_basis == price_line.occupancy_basis
            and line.unit == price_line.unit
            and line.tier_min_pax == price_line.tier_min_pax
        ),
        None,
    ) if raw_rate is not None else None
    price_line_id = orm_line.id if orm_line is not None else None
    if price_line_id is None:
        return chosen.rate_id, None, {"rate_missing", *flags}
    return chosen.rate_id, price_line_id, flags


async def run_draft(
    session: AsyncSession,
    *,
    sheet: CostingSheet,
    trip_profile: TripProfile,
    days: list[DraftDaySpecSchema],
    day_numbers_filter: list[int] | None,
    base_costing_revision: int,
    actor: ActorRef,
    idempotency_key: str,
    tenant_id: str = DEFAULT_TENANT_ID,
) -> DraftResponseSchema:
    """``days`` — ``[{day_number, destination_id, service_date}]`` supplied by the caller
    (the frontend already has the itinerary from the display/workspace view this dialog opens
    from); 15.7 deliberately does not reach into the facts pipeline to rebuild it (vùng cấm)."""
    existing = await find_existing_run(session, anchor_id=sheet.id, idempotency_key=idempotency_key, tenant_id=tenant_id)
    if existing is not None:
        return DraftResponseSchema.model_validate(
            {"run_id": existing.id, **existing.output_json, "day_outcomes": existing.output_json.get("day_outcomes", [])}
        )

    target_days = [d for d in days if day_numbers_filter is None or d.day_number in day_numbers_filter]
    if not target_days:
        raise DraftValidationError("No matching day_numbers to draft.")

    run_id = generate_id(ID_PREFIX)
    allowlist = AllowlistRecorder()
    budget = RunBudget(max_calls=len(target_days) + 2)
    deps = CatalogReadOnlyDeps(session=session, tenant_id=tenant_id, allowlist=allowlist, budget=budget)
    costing_service = CostingService(session)
    product_repository = ProductRepository(session)

    current_revision = base_costing_revision
    known_workbench = await costing_service.get_workbench(sheet.id)
    if known_workbench is None:
        raise DraftValidationError(f"Costing sheet '{sheet.id}' was not found.")
    day_outcomes: list[DraftDayOutcomeSchema] = []
    days_done: list[int] = []
    days_failed: list[int] = []
    created_line_ids: list[str] = []
    manual_review_count = 0

    for day_spec in target_days:
        day_number = day_spec.day_number
        destination_id = day_spec.destination_id
        service_date: date = day_spec.service_date

        try:
            day_context = build_day_context(
                trip_profile, day_number=day_number, destination_id=destination_id, service_date=service_date.isoformat()
            )
            draft_result: DayDraftResult = await draft_day(deps, day_context)
        except Exception as exc:  # pragma: no cover - network/provider errors
            days_failed.append(day_number)
            day_outcomes.append(DraftDayOutcomeSchema(day_number=day_number, lines_created=0, error=str(exc)))
            continue

        lines_created_this_day = 0
        for service in draft_result.services:
            if not allowlist.contains(service.product_id):
                manual_review_count += 1
                continue

            product = await product_repository.get_by_id(service.product_id, tenant_id=tenant_id)
            if product is None:
                manual_review_count += 1
                continue

            tariff_id, price_line_id, resolved_flags = await _resolve_price_serverside(
                session,
                tenant_id,
                product_id=product.id,
                service_date=service_date,
                occupancy_basis=service.occupancy_basis,
                price_for=service.price_for,
                pax_count=service.pax_count,
            )
            flags = sorted({*service.flags, *resolved_flags})
            needs_manual = bool({"rate_missing", "rate_conflict"} & set(flags))
            if needs_manual and "needs_manual" not in flags:
                flags.append("needs_manual")
            if needs_manual:
                manual_review_count += 1

            ai_meta = {
                "reason": service.selection_reason,
                "run_id": run_id,
                "day_number": day_number,
                "flags": flags,
            }
            if needs_manual:
                ai_meta["suggested_product_id"] = product.id

            if tariff_id and price_line_id is not None:
                payload = ServiceLineWriteSchema(
                    base_costing_revision=current_revision,
                    day_number=day_number,
                    service_date=service_date,
                    product_id=product.id,
                    rate_id=tariff_id,
                    price_line_id=price_line_id,
                    qty_unit=service.qty_unit,
                    qty_time=service.qty_time,
                )
            else:
                payload = ServiceLineWriteSchema(
                    base_costing_revision=current_revision,
                    day_number=day_number,
                    service_date=service_date,
                    category=product.category,
                    subcategory=product.subcategory,
                    title=product.title,
                    supplier_id=product.supplier_id,
                    unit=product.unit,
                    time_basis=product.time_basis,
                    qty_unit=service.qty_unit,
                    qty_time=service.qty_time,
                    unit_cost_minor=0,
                    cost_currency=sheet.currency,
                )

            line_idempotency_key = f"{idempotency_key}:d{day_number}:{service.product_id}:{lines_created_this_day}"
            before_ids = {item.id for item in known_workbench.items}
            try:
                workbench = await costing_service.create_line(
                    sheet.id,
                    payload,
                    actor=actor,
                    idempotency_key=line_idempotency_key,
                    source="ai_draft",
                    ai_meta_json=ai_meta,
                )
            except CostingValidationError:
                manual_review_count += 1
                continue
            except CostingConflictError as err:
                raise DraftConflictError(str(err), current_revision=err.current_revision) from err

            if workbench is None:
                continue
            known_workbench = workbench
            current_revision = workbench.sheet.costing_revision
            new_ids = {item.id for item in workbench.items} - before_ids
            created_line_ids.extend(sorted(new_ids))
            lines_created_this_day += 1

        days_done.append(day_number)
        day_outcomes.append(DraftDayOutcomeSchema(day_number=day_number, lines_created=lines_created_this_day, draft=draft_result))

    status = "succeeded" if not days_failed else ("partial" if days_done else "failed")
    output = {
        "status": status,
        "days_done": days_done,
        "days_failed": days_failed,
        "created_line_ids": created_line_ids,
        "manual_review_count": manual_review_count,
        "day_outcomes": [outcome.model_dump(mode="json") for outcome in day_outcomes],
    }
    await _insert_run_record(
        session,
        run_id=run_id,
        anchor_id=sheet.id,
        status=status,
        idempotency_key=idempotency_key,
        input_ref={"day_count": len(target_days), "day_numbers": [d.day_number for d in target_days]},
        output={k: v for k, v in output.items() if k != "day_outcomes"},
        stats={**budget.stats(), "days_done": days_done, "days_failed": days_failed},
        actor=actor,
        tenant_id=tenant_id,
    )

    return DraftResponseSchema(
        run_id=run_id,
        status=status,
        days_done=days_done,
        days_failed=days_failed,
        day_outcomes=day_outcomes,
        created_line_ids=created_line_ids,
        manual_review_count=manual_review_count,
    )
