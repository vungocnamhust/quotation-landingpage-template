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

import db.session as db_session
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

# H2: one RunBudget per DAY, not one shared across the whole run — the drafter prompt expects
# several tool calls per day (accommodation/transport/activities/rate lookups), so a single
# ``len(days) + 2`` budget for the whole run starves every day after the first one or two.
# Matches ``RunBudget``'s own default ceiling (``guardrails.py``).
PER_DAY_TOOL_CALL_BUDGET = 8


class DraftRunError(RuntimeError):
    pass


class DraftValidationError(DraftRunError):
    pass


class DraftConflictError(DraftRunError):
    def __init__(self, message: str, *, current_revision: int) -> None:
        super().__init__(message)
        self.current_revision = current_revision


async def find_existing_run(
    session: AsyncSession,
    *,
    anchor_id: str,
    idempotency_key: str,
    agent_name: str | None = None,
    tenant_id: str = DEFAULT_TENANT_ID,
) -> AiRun | None:
    """H3: ``agent_name`` narrows the lookup to one agent's own runs. The DB unique constraint
    on ``ai_runs`` is ``(tenant_id, anchor_type, anchor_id, idempotency_key)`` — it does NOT
    include ``agent_name`` — so an idempotency key already used by a *different* agent on the
    same anchor is a real collision, not a safe replay: passing ``agent_name=None`` (the
    default) is how callers detect that case before attempting their own insert.
    """
    stmt = select(AiRun).where(
        AiRun.tenant_id == tenant_id,
        AiRun.anchor_type == ANCHOR_TYPE,
        AiRun.anchor_id == anchor_id,
        AiRun.idempotency_key == idempotency_key,
    )
    if agent_name is not None:
        stmt = stmt.where(AiRun.agent_name == agent_name)
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


async def _record_failed_run_isolated(
    *,
    tenant_id: str,
    run_id: str,
    anchor_id: str,
    idempotency_key: str,
    status: str,
    input_ref: dict[str, Any],
    output: dict[str, Any],
    stats: dict[str, Any],
    actor: ActorRef,
) -> None:
    """Best-effort failure-path logging (Track 4 audit H8).

    When ``run_draft`` aborts mid-run — a CAS conflict, or a genuinely unexpected error — the
    caller's request transaction is about to be rolled back. An ``AiRun`` row written through
    that same ``session`` would vanish with it, so a failed run (tokens spent, days already
    drafted) would leave no trace at all. Opening a fresh, independent session here lets the
    run record survive that rollback. Never raises: a failure to log must never mask the
    original error that is about to propagate.
    """
    try:
        session_factory = db_session.get_session_factory()
        async with session_factory() as isolated_session:
            await _insert_run_record(
                isolated_session,
                run_id=run_id,
                anchor_id=anchor_id,
                status=status,
                idempotency_key=idempotency_key,
                input_ref=input_ref,
                output=output,
                stats=stats,
                actor=actor,
                tenant_id=tenant_id,
            )
            await isolated_session.commit()
    except Exception:  # pragma: no cover - best-effort logging must never mask the real error
        pass


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
            # H8: malformed staff-entered supplement JSON must degrade gracefully (skip this
            # supplement, keep the line) rather than crash the whole day's draft.
            try:
                applies_from = date.fromisoformat(supplement["applies_from"])
                applies_to = date.fromisoformat(supplement["applies_to"])
            except (KeyError, TypeError, ValueError):
                continue
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


class _DayPersistResult:
    def __init__(
        self,
        *,
        outcome: DraftDayOutcomeSchema,
        current_revision: int,
        known_workbench: Any,
        new_line_ids: list[str],
        manual_review_delta: int,
    ) -> None:
        self.outcome = outcome
        self.current_revision = current_revision
        self.known_workbench = known_workbench
        self.new_line_ids = new_line_ids
        self.manual_review_delta = manual_review_delta


async def _draft_and_persist_day(
    session: AsyncSession,
    *,
    deps: CatalogReadOnlyDeps,
    costing_service: CostingService,
    product_repository: ProductRepository,
    sheet: CostingSheet,
    trip_profile: TripProfile,
    day_spec: DraftDaySpecSchema,
    run_id: str,
    idempotency_key: str,
    tenant_id: str,
    actor: ActorRef,
    current_revision: int,
    known_workbench: Any,
) -> _DayPersistResult:
    """Draft ONE day and persist its lines. Raises ``DraftConflictError`` on a CAS conflict
    (a hard, whole-run abort by design — the caller does not catch this here); any other
    exception (agent/provider failure, malformed rate data, an unresolvable product) propagates
    to the caller too, which turns it into a ``days_failed`` entry instead of losing the whole
    run (Track 4 audit H8)."""
    day_number = day_spec.day_number
    service_date: date = day_spec.service_date

    day_context = build_day_context(
        trip_profile, day_number=day_number, destination_id=day_spec.destination_id, service_date=service_date.isoformat()
    )
    draft_result: DayDraftResult = await draft_day(deps, day_context)

    lines_created_this_day = 0
    new_line_ids: list[str] = []
    manual_review_delta = 0

    for service in draft_result.services:
        if not deps.allowlist.contains(service.product_id):
            manual_review_delta += 1
            continue

        product = await product_repository.get_by_id(service.product_id, tenant_id=tenant_id)
        if product is None:
            manual_review_delta += 1
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
            manual_review_delta += 1

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
            manual_review_delta += 1
            continue
        except CostingConflictError as err:
            raise DraftConflictError(str(err), current_revision=err.current_revision) from err

        if workbench is None:
            continue
        known_workbench = workbench
        current_revision = workbench.sheet.costing_revision
        new_ids = sorted({item.id for item in workbench.items} - before_ids)
        new_line_ids.extend(new_ids)
        lines_created_this_day += 1

    outcome = DraftDayOutcomeSchema(day_number=day_number, lines_created=lines_created_this_day, draft=draft_result)
    return _DayPersistResult(
        outcome=outcome,
        current_revision=current_revision,
        known_workbench=known_workbench,
        new_line_ids=new_line_ids,
        manual_review_delta=manual_review_delta,
    )


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
    from); 15.7 deliberately does not reach into the facts pipeline to rebuild it (vùng cấm).

    Commits after EACH day (H1/H8): a costing-sheet write takes a DB row lock that is held
    until commit, so holding one open across every remaining day's LLM call would let one
    in-flight draft block every other edit to the sheet for the run's full duration. Committing
    per day releases that lock between LLM calls and means a later day's hard failure (a CAS
    conflict) never rolls back days that already finished — exactly the "keep what's done"
    behavior the spec requires.
    """
    existing = await find_existing_run(
        session, anchor_id=sheet.id, idempotency_key=idempotency_key, agent_name=AGENT_NAME, tenant_id=tenant_id
    )
    if existing is not None:
        return DraftResponseSchema.model_validate(
            {"run_id": existing.id, **existing.output_json, "day_outcomes": existing.output_json.get("day_outcomes", [])}
        )

    # H3: the DB unique constraint on ``ai_runs`` does not include ``agent_name``, so an
    # idempotency key already used by a different agent (e.g. Analyze) on this sheet is not a
    # safe replay for us — proceeding would crash the eventual insert with an opaque
    # IntegrityError. Catch that up front with a clear, actionable error instead.
    other_agent_run = await find_existing_run(session, anchor_id=sheet.id, idempotency_key=idempotency_key, tenant_id=tenant_id)
    if other_agent_run is not None:
        raise DraftValidationError(
            f"Idempotency-Key '{idempotency_key}' was already used by a different operation "
            f"('{other_agent_run.agent_name}') on this sheet — use a new key."
        )

    target_days = [d for d in days if day_numbers_filter is None or d.day_number in day_numbers_filter]
    if not target_days:
        raise DraftValidationError("No matching day_numbers to draft.")

    run_id = generate_id(ID_PREFIX)
    allowlist = AllowlistRecorder()
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
    total_stats = {"calls": 0, "retries": 0, "tokens_in": 0, "tokens_out": 0}

    def _run_input_ref() -> dict[str, Any]:
        return {"day_count": len(target_days), "day_numbers": [d.day_number for d in target_days]}

    def _run_output(status: str) -> dict[str, Any]:
        return {
            "status": status,
            "days_done": days_done,
            "days_failed": days_failed,
            "manual_review_count": manual_review_count,
        }

    try:
        for day_spec in target_days:
            day_number = day_spec.day_number
            # H2: one RunBudget PER DAY — a run-wide budget starves every day after the first
            # one or two, since a realistic day needs several tool calls of its own.
            day_budget = RunBudget(max_calls=PER_DAY_TOOL_CALL_BUDGET)
            deps = CatalogReadOnlyDeps(session=session, tenant_id=tenant_id, allowlist=allowlist, budget=day_budget)

            try:
                result = await _draft_and_persist_day(
                    session,
                    deps=deps,
                    costing_service=costing_service,
                    product_repository=product_repository,
                    sheet=sheet,
                    trip_profile=trip_profile,
                    day_spec=day_spec,
                    run_id=run_id,
                    idempotency_key=idempotency_key,
                    tenant_id=tenant_id,
                    actor=actor,
                    current_revision=current_revision,
                    known_workbench=known_workbench,
                )
            except DraftConflictError:
                raise
            except Exception as exc:  # pragma: no cover - agent/provider/data errors
                days_failed.append(day_number)
                day_outcomes.append(DraftDayOutcomeSchema(day_number=day_number, lines_created=0, error=str(exc)))
            else:
                days_done.append(day_number)
                day_outcomes.append(result.outcome)
                created_line_ids.extend(result.new_line_ids)
                manual_review_count += result.manual_review_delta
                current_revision = result.current_revision
                known_workbench = result.known_workbench
            finally:
                for key, value in day_budget.stats().items():
                    total_stats[key] += value

            await session.commit()
    except DraftConflictError as conflict_err:
        await _record_failed_run_isolated(
            tenant_id=tenant_id,
            run_id=run_id,
            anchor_id=sheet.id,
            idempotency_key=idempotency_key,
            status="partial" if days_done else "failed",
            input_ref=_run_input_ref(),
            output={**_run_output("partial" if days_done else "failed"), "error": str(conflict_err)},
            stats={**total_stats, "days_done": days_done, "days_failed": days_failed},
            actor=actor,
        )
        raise
    except Exception as exc:  # pragma: no cover - genuinely unexpected failure
        await _record_failed_run_isolated(
            tenant_id=tenant_id,
            run_id=run_id,
            anchor_id=sheet.id,
            idempotency_key=idempotency_key,
            status="partial" if days_done else "failed",
            input_ref=_run_input_ref(),
            output={**_run_output("partial" if days_done else "failed"), "error": str(exc)},
            stats={**total_stats, "days_done": days_done, "days_failed": days_failed},
            actor=actor,
        )
        raise

    status = "succeeded" if not days_failed else ("partial" if days_done else "failed")
    output = {**_run_output(status), "created_line_ids": created_line_ids, "day_outcomes": [o.model_dump(mode="json") for o in day_outcomes]}
    await _insert_run_record(
        session,
        run_id=run_id,
        anchor_id=sheet.id,
        status=status,
        idempotency_key=idempotency_key,
        input_ref=_run_input_ref(),
        output={k: v for k, v in output.items() if k != "day_outcomes"},
        stats={**total_stats, "days_done": days_done, "days_failed": days_failed},
        actor=actor,
        tenant_id=tenant_id,
    )
    await session.commit()

    return DraftResponseSchema(
        run_id=run_id,
        status=status,
        days_done=days_done,
        days_failed=days_failed,
        day_outcomes=day_outcomes,
        created_line_ids=created_line_ids,
        manual_review_count=manual_review_count,
    )
