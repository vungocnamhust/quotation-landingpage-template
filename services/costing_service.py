"""Costing aggregate service — 15.4 §1.7 + 15.5 apply. Orchestrates resolve→snapshot→CAS→totals→attach→apply.

Sheet/line writes never touch facts or the document revision. The single
sanctioned crossing is 15.5's ``apply_pricing``: it writes the target pricing
option via ``api.runtime.apply_pricing_option`` (facts-side CAS) and emits the
``costing.applied`` outbox event. Everything else touches other aggregates only
through read-only repository lookups.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.runtime import apply_pricing_option
from core.kernel import ActorRef, generate_id, validate_currency
from core.rules.costing_rules import ServiceLineInput, summarize
from db.models.costing import CostingSheet
from notification.domain.events import EventType
from repositories.costing_repository import (
    CostingLineDuplicateError,
    CostingRepository,
    CostingRevisionRaceError,
    CostingSheetAlreadyAttachedError,
    CostingSheetSlotTakenError,
)
from repositories.destination_repository import DestinationRepository
from repositories.errors import DocumentRevisionConflictError
from repositories.product_repository import ProductRepository
from repositories.quotation_repository import QuotationRepository
from repositories.quote_request_repository import QuoteRequestRepository
from repositories.rate_repository import RateRepository
from repositories.supplier_repository import SupplierRepository
from schemas.v2.costing import (
    ApplyPricingRequestSchema,
    ApplyPricingResponseSchema,
    AttachQuotationSchema,
    CategoryTotalSchema,
    CostingApplicationResponseSchema,
    CostingDriftSchema,
    CostingSettingsUpdateSchema,
    CostingSheetCreateSchema,
    CostingSheetResponseSchema,
    CostingSummarySchema,
    CostingWorkbenchResponseSchema,
    DayTotalSchema,
    ProductRefSchema,
    ServiceLineResponseSchema,
    ServiceLineWriteSchema,
)
from services.outbox_service import OutboxService

log = logging.getLogger(__name__)

SHEET_ID_PREFIX = "cst"
LINE_ID_PREFIX = "csl"
APPLICATION_ID_PREFIX = "cga"

# Deviation from 15.4-costing.md §1.3: the plan calls for deriving the default
# currency via ``taxonomy_rules.infer_default_currency(brand_id, market)``, but
# that helper does not exist anywhere in the codebase yet. Rather than invent a
# new cross-module coupling for a brainstorm-stage reference, sheets default to
# the tenant's home currency and the sale can override it up front (CS1 still
# locks it once a line exists).
_DEFAULT_SHEET_CURRENCY = "VND"


class CostingValidationError(ValueError):
    """Business-rule violation (maps to 422)."""


class CostingConflictError(ValueError):
    """CAS mismatch or lifecycle conflict (maps to 409)."""

    def __init__(self, message: str, *, current_revision: int) -> None:
        super().__init__(message)
        self.current_revision = current_revision


class CostingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = CostingRepository(session)
        self.product_repository = ProductRepository(session)
        self.supplier_repository = SupplierRepository(session)
        self.rate_repository = RateRepository(session)
        self.destination_repository = DestinationRepository(session)
        self.quote_request_repository = QuoteRequestRepository(session)
        self.quotation_repository = QuotationRepository(session)

    # ------------------------------------------------------------------ reads

    async def find_sheet_for_request(self, request_id: str) -> CostingSheet | None:
        return await self.repository.get_active_sheet_by_request(request_id)

    async def find_sheet_for_quotation(self, quotation_id: str) -> CostingSheet | None:
        return await self.repository.get_sheet_by_quotation(quotation_id)

    async def get_workbench(self, sheet_id: str) -> CostingWorkbenchResponseSchema | None:
        sheet = await self.repository.get_sheet_by_id(sheet_id)
        if sheet is None:
            return None
        return await self._to_workbench(sheet)

    # --------------------------------------------------------------- writes

    async def create_sheet(self, payload: CostingSheetCreateSchema, *, actor: ActorRef) -> CostingSheetResponseSchema:
        if payload.request_id:
            request = await self.quote_request_repository.get_by_id(payload.request_id)
            if request is None:
                raise CostingValidationError(f"quote_request '{payload.request_id}' was not found.")
            existing = await self.repository.get_active_sheet_by_request(payload.request_id)
            if existing is not None:
                raise CostingConflictError(
                    f"quote_request '{payload.request_id}' already has an open costing sheet '{existing.id}'.",
                    current_revision=existing.costing_revision,
                )
        else:
            quotation = await self.quotation_repository.get_quotation_by_id(payload.quotation_id)
            if quotation is None:
                raise CostingValidationError(f"quotation '{payload.quotation_id}' was not found.")
            existing = await self.repository.get_sheet_by_quotation(payload.quotation_id)
            if existing is not None:
                raise CostingConflictError(
                    f"quotation '{payload.quotation_id}' already has a costing sheet '{existing.id}'.",
                    current_revision=existing.costing_revision,
                )

        currency = validate_currency(payload.currency) if payload.currency else _DEFAULT_SHEET_CURRENCY
        values: dict[str, Any] = {
            "quote_request_id": payload.request_id,
            "quotation_id": payload.quotation_id,
            "currency": currency,
            "created_by": actor.serialize(),
            "updated_by": actor.serialize(),
        }
        try:
            sheet = await self.repository.insert_sheet(sheet_id=generate_id(SHEET_ID_PREFIX), values=values)
        except CostingSheetSlotTakenError as err:
            raise CostingConflictError("The costing sheet slot for this anchor was just taken.", current_revision=0) from err
        return CostingSheetResponseSchema.model_validate(sheet)

    async def update_settings(
        self, sheet_id: str, payload: CostingSettingsUpdateSchema, *, actor: ActorRef
    ) -> CostingWorkbenchResponseSchema | None:
        sheet = await self.repository.get_sheet_by_id(sheet_id)
        if sheet is None:
            return None
        self._check_revision(sheet, payload.base_costing_revision)

        values: dict[str, Any] = {"updated_by": actor.serialize()}
        if payload.currency is not None:
            currency = validate_currency(payload.currency)
            if currency != sheet.currency and sheet.lines:
                raise CostingConflictError(
                    "Currency is locked once the sheet has service lines (CS1).",
                    current_revision=sheet.costing_revision,
                )
            values["currency"] = currency
        if payload.markup_rate_bps is not None:
            values["markup_rate_bps"] = payload.markup_rate_bps
        if payload.rounding_increment_minor is not None:
            values["rounding_increment_minor"] = payload.rounding_increment_minor

        try:
            sheet = await self.repository.update_settings(
                sheet, values=values, expected_revision=payload.base_costing_revision
            )
        except CostingRevisionRaceError as err:
            raise await self._conflict_from_race(sheet_id) from err
        return await self._to_workbench(sheet)

    async def attach_quotation(
        self, sheet_id: str, payload: AttachQuotationSchema, *, actor: ActorRef, idempotency_key: str
    ) -> CostingWorkbenchResponseSchema | None:
        sheet = await self.repository.get_sheet_by_id(sheet_id)
        if sheet is None:
            return None

        if sheet.quotation_id == payload.quotation_id and sheet.attach_idempotency_key == idempotency_key:
            return await self._to_workbench(sheet)
        if sheet.quotation_id is not None:
            raise CostingConflictError(
                f"Sheet '{sheet_id}' is already attached to quotation '{sheet.quotation_id}'.",
                current_revision=sheet.costing_revision,
            )

        quotation = await self.quotation_repository.get_quotation_by_id(payload.quotation_id)
        if quotation is None:
            raise CostingValidationError(f"quotation '{payload.quotation_id}' was not found.")
        if sheet.quote_request_id and quotation.source_request_id != sheet.quote_request_id:
            raise CostingValidationError(
                f"quotation '{payload.quotation_id}' was not generated from request '{sheet.quote_request_id}'."
            )
        other_sheet = await self.repository.get_sheet_by_quotation(payload.quotation_id)
        if other_sheet is not None and other_sheet.id != sheet.id:
            raise CostingConflictError(
                f"quotation '{payload.quotation_id}' already has a costing sheet '{other_sheet.id}'.",
                current_revision=sheet.costing_revision,
            )

        try:
            sheet = await self.repository.attach_to_quotation(
                sheet,
                quotation_id=payload.quotation_id,
                idempotency_key=idempotency_key,
                updated_by=actor.serialize(),
            )
        except CostingSheetSlotTakenError as err:
            raise CostingConflictError(
                f"quotation '{payload.quotation_id}' already has a costing sheet.", current_revision=sheet.costing_revision
            ) from err
        except CostingSheetAlreadyAttachedError as err:
            # Concurrent attach won the quotation_id IS NULL guard; re-read for an honest 409.
            current = await self.repository.get_sheet_revision(sheet_id)
            raise CostingConflictError(
                f"Sheet '{sheet_id}' was just attached to another quotation.",
                current_revision=current if current is not None else sheet.costing_revision,
            ) from err
        return await self._to_workbench(sheet)

    async def create_line(
        self, sheet_id: str, payload: ServiceLineWriteSchema, *, actor: ActorRef, idempotency_key: str
    ) -> CostingWorkbenchResponseSchema | None:
        sheet = await self.repository.get_sheet_by_id(sheet_id)
        if sheet is None:
            return None

        existing = await self.repository.get_line_by_idempotency_key(sheet_id, idempotency_key=idempotency_key)
        if existing is not None:
            return await self._to_workbench(sheet)

        self._check_revision(sheet, payload.base_costing_revision)
        values = await self._resolve_line_values(sheet, payload)
        values["idempotency_key"] = idempotency_key
        values["created_by"] = actor.serialize()
        values["updated_by"] = actor.serialize()
        try:
            await self.repository.insert_line(
                sheet,
                line_id=generate_id(LINE_ID_PREFIX),
                values=values,
                expected_revision=payload.base_costing_revision,
            )
        except CostingRevisionRaceError as err:
            raise await self._conflict_from_race(sheet_id) from err
        except CostingLineDuplicateError:
            # The concurrent twin with the same key already landed — replay its result.
            sheet = await self.repository.get_sheet_by_id(sheet_id)
            if sheet is None:
                return None
            return await self._to_workbench(sheet)

        sheet = await self.repository.get_sheet_by_id(sheet_id)
        return await self._to_workbench(sheet)

    async def update_line(
        self, sheet_id: str, line_id: str, payload: ServiceLineWriteSchema, *, actor: ActorRef
    ) -> CostingWorkbenchResponseSchema | None:
        sheet = await self.repository.get_sheet_by_id(sheet_id)
        if sheet is None:
            return None
        self._check_revision(sheet, payload.base_costing_revision)

        line = await self.repository.get_line_by_id(line_id)
        if line is None or line.sheet_id != sheet_id:
            return None
        self._guard_booked_line(line, sheet)

        values = await self._resolve_line_values(sheet, payload)
        values["updated_by"] = actor.serialize()
        try:
            await self.repository.update_line(
                sheet, line, values=values, expected_revision=payload.base_costing_revision
            )
        except CostingRevisionRaceError as err:
            raise await self._conflict_from_race(sheet_id) from err

        sheet = await self.repository.get_sheet_by_id(sheet_id)
        return await self._to_workbench(sheet)

    async def delete_line(
        self, sheet_id: str, line_id: str, *, base_costing_revision: int
    ) -> CostingWorkbenchResponseSchema | None:
        sheet = await self.repository.get_sheet_by_id(sheet_id)
        if sheet is None:
            return None
        self._check_revision(sheet, base_costing_revision)

        line = await self.repository.get_line_by_id(line_id)
        if line is None or line.sheet_id != sheet_id:
            return None
        self._guard_booked_line(line, sheet)

        try:
            await self.repository.delete_line(sheet, line, expected_revision=base_costing_revision)
        except CostingRevisionRaceError as err:
            raise await self._conflict_from_race(sheet_id) from err
        sheet = await self.repository.get_sheet_by_id(sheet_id)
        return await self._to_workbench(sheet)

    async def apply_pricing(
        self,
        sheet_id: str,
        payload: ApplyPricingRequestSchema,
        *,
        actor: ActorRef,
        idempotency_key: str | None = None,
    ) -> ApplyPricingResponseSchema | None:
        sheet = await self.repository.get_sheet_by_id(sheet_id)
        if sheet is None:
            return None

        # Server-authoritative totals off current lines — pure/read-only, safe to
        # compute before any gate. Used both for the replay's cosmetic breakdown
        # and for a fresh apply's real totals below.
        line_inputs = [
            ServiceLineInput(
                line_id=line.id,
                day_number=line.day_number,
                category=line.category,
                unit_cost_minor=line.unit_cost_minor,
                qty_unit=line.qty_unit,
                qty_time=line.qty_time,
                fx_rate_ppm=line.fx_rate_ppm,
                sell_override_minor=line.sell_override_minor,
            )
            for line in sheet.lines
        ]
        summary = summarize(
            line_inputs,
            markup_rate_bps=sheet.markup_rate_bps,
            rounding_increment_minor=sheet.rounding_increment_minor,
        )

        # 16.3 P0 fix (chốt #6): idempotency replay must win over every CAS/
        # validation gate below. Previously the CAS/validation checks ran first,
        # so a retry could get a spurious 409/422 if the sheet moved on for any
        # unrelated reason after the original successful apply. The authoritative
        # fields (application, facts_revision, costing_revision, totals) are read
        # back from the immutable application row, never recomputed from live
        # state — only the by_day/by_category breakdown is a cosmetic refresh.
        if idempotency_key:
            existing_app = await self.repository.get_application_by_idempotency_key(
                sheet_id, idempotency_key=idempotency_key
            )
            if existing_app is not None:
                pricing_opts: list[dict[str, Any]] = []
                req = await self.quotation_repository.get_latest_quotation_request(sheet.quotation_id)
                if req and req.request_json:
                    pricing_opts = (req.request_json.get("pricing_facts") or {}).get("options") or []
                fresh_breakdown = self._build_summary_schema(summary)
                replay_summary = CostingSummarySchema(
                    cost_total_minor=existing_app.cost_total_minor,
                    sell_total_minor=existing_app.sell_total_minor,
                    margin_minor=existing_app.sell_total_minor - existing_app.cost_total_minor,
                    margin_bps=existing_app.margin_bps,
                    by_day=fresh_breakdown.by_day,
                    by_category=fresh_breakdown.by_category,
                )
                return ApplyPricingResponseSchema(
                    application=CostingApplicationResponseSchema.model_validate(existing_app),
                    facts_revision=existing_app.facts_revision_after,
                    costing_revision=existing_app.costing_revision_at_apply,
                    summary=replay_summary,
                    pricing_options=pricing_opts,
                )

        if not sheet.quotation_id:
            raise CostingValidationError("Costing sheet must be attached to a quotation before applying pricing.")

        self._check_revision(sheet, payload.base_costing_revision)

        if not sheet.lines:
            raise CostingValidationError("Cannot apply pricing for a costing sheet with no service lines.")

        if summary.sell_total_minor <= 0:
            raise CostingValidationError("Cannot apply pricing when sell total is less than or equal to zero.")

        try:
            facts_res = await apply_pricing_option(
                session=self.session,
                quotation_id=sheet.quotation_id,
                base_revision=payload.base_revision,
                target_option_id=payload.target_option_id,
                option_label=payload.option_label,
                sell_total_minor=summary.sell_total_minor,
                currency=sheet.currency,
                actor=actor,
                lang=payload.lang,
            )
        except DocumentRevisionConflictError as exc:
            raise CostingConflictError(
                f"Quotation facts revision conflict: {exc}",
                current_revision=exc.current_revision,
            ) from exc

        # 16.3 P1 fix: apply_pricing never bumps costing_sheets itself, so the
        # Python-level `_check_revision` above is only a fast pre-check — a
        # concurrent line/settings write could still commit while the facts
        # write above was in flight. This is the DB-level compare-and-swap
        # that closes that window before anything derived from `summary` is
        # persisted; nothing has committed yet (router commits once, at the
        # end), so a race here rolls the facts write above back too.
        try:
            await self.repository.verify_revision_guarded(sheet.id, expected_revision=payload.base_costing_revision)
        except CostingRevisionRaceError as err:
            raise await self._conflict_from_race(sheet.id) from err

        app_id = generate_id(APPLICATION_ID_PREFIX)
        app_values = {
            "sheet_id": sheet.id,
            "quotation_id": sheet.quotation_id,
            "costing_revision_at_apply": sheet.costing_revision,
            "facts_revision_after": facts_res["new_revision"],
            "target_option_id": facts_res["target_option_id"],
            "sell_total_minor": summary.sell_total_minor,
            "currency": sheet.currency,
            "cost_total_minor": summary.cost_total_minor,
            "margin_bps": summary.margin_bps,
            "idempotency_key": idempotency_key,
            "created_by": actor.serialize(),
        }
        app = await self.repository.insert_application(application_id=app_id, values=app_values)

        outbox = OutboxService(self.session)
        await outbox.emit_event(
            event_type=EventType.COSTING_APPLIED.value,
            aggregate_type="costing_sheet",
            aggregate_id=sheet.id,
            actor_email=actor.actor_id,
            payload={
                "sheet_id": sheet.id,
                "quotation_id": sheet.quotation_id,
                "application_id": app.id,
                "sell_total_minor": summary.sell_total_minor,
                "currency": sheet.currency,
                "margin_bps": summary.margin_bps,
                "cost_total_minor": summary.cost_total_minor,
                "costing_revision_at_apply": sheet.costing_revision,
                "facts_revision_after": facts_res["new_revision"],
                "target_option_id": facts_res["target_option_id"],
                "actor": actor.serialize(),
            },
        )

        summary_schema = self._build_summary_schema(summary)
        return ApplyPricingResponseSchema(
            application=CostingApplicationResponseSchema.model_validate(app),
            facts_revision=facts_res["new_revision"],
            costing_revision=sheet.costing_revision,
            summary=summary_schema,
            pricing_options=facts_res.get("pricing_options", []),
        )

    # ------------------------------------------------------------- helpers

    @staticmethod
    def _build_summary_schema(summary) -> CostingSummarySchema:
        return CostingSummarySchema(
            cost_total_minor=summary.cost_total_minor,
            sell_total_minor=summary.sell_total_minor,
            margin_minor=summary.margin_minor,
            margin_bps=summary.margin_bps,
            by_day=[DayTotalSchema(day_number=d.day_number, cost_minor=d.cost_minor, sell_minor=d.sell_minor) for d in summary.by_day],
            by_category=[
                CategoryTotalSchema(category=c.category, cost_minor=c.cost_minor, sell_minor=c.sell_minor)
                for c in summary.by_category
            ],
        )

    @staticmethod
    def _guard_booked_line(line, sheet: CostingSheet) -> None:
        """15.6 §1.2: a line already handed to Operations is frozen here (409, not 422).

        ``booking_status`` is a read-model mirror of the ``booking_lines.status``
        it was copied into; the source of truth for whether it's bookable lives
        in ``services/booking_service.py``.
        """
        if line.booking_status != "quoted":
            raise CostingConflictError(
                f"Service line '{line.id}' has moved to Operations (booking_status='{line.booking_status}') "
                "and can no longer be edited or deleted from the costing grid.",
                current_revision=sheet.costing_revision,
            )

    async def _conflict_from_race(self, sheet_id: str) -> CostingConflictError:
        """Build the 409 for a lost version-guarded write, with the revision the winner left behind."""
        current = await self.repository.get_sheet_revision(sheet_id)
        return CostingConflictError(
            f"Costing sheet '{sheet_id}' was modified by a concurrent write. Reload and retry.",
            current_revision=current if current is not None else 0,
        )

    @staticmethod
    def _check_revision(sheet: CostingSheet, base_costing_revision: int) -> None:
        if base_costing_revision != sheet.costing_revision:
            raise CostingConflictError(
                f"Costing sheet '{sheet.id}' has moved on: expected revision {base_costing_revision}, "
                f"current is {sheet.costing_revision}.",
                current_revision=sheet.costing_revision,
            )

    async def _resolve_line_values(self, sheet: CostingSheet, payload: ServiceLineWriteSchema) -> dict[str, Any]:
        if payload.product_id:
            values = await self._resolve_catalog_line(payload)
        else:
            values = self._resolve_manual_line(payload)

        cost_currency = values["cost_currency"]
        if cost_currency != sheet.currency and payload.fx_rate_ppm is None:
            raise CostingValidationError(
                f"fx_rate_ppm is required: line currency '{cost_currency}' differs from sheet currency '{sheet.currency}'."
            )
        values["fx_rate_ppm"] = payload.fx_rate_ppm
        values["sell_override_minor"] = payload.sell_override_minor
        values["day_number"] = payload.day_number
        values["service_date"] = payload.service_date
        values["note"] = payload.note
        values["sort_order"] = payload.sort_order
        values["qty_unit"] = payload.qty_unit
        values["qty_time"] = payload.qty_time
        return values

    async def _resolve_catalog_line(self, payload: ServiceLineWriteSchema) -> dict[str, Any]:
        product = await self.product_repository.get_by_id(payload.product_id)
        if product is None:
            raise CostingValidationError(f"product '{payload.product_id}' was not found.")

        rate = await self.rate_repository.get_by_id(payload.rate_id)
        if rate is None or rate.product_id != product.id:
            raise CostingValidationError(f"rate '{payload.rate_id}' was not found for product '{payload.product_id}'.")
        if rate.lifecycle_status != "active":
            raise CostingValidationError(
                {"message": f"rate '{rate.id}' is not active.", "candidates": []},
            )
        if not self._rate_covers_date(rate, payload.service_date):
            raise CostingValidationError(
                {"message": f"rate '{rate.id}' does not cover service_date {payload.service_date}.", "candidates": []},
            )

        price_line = next((line for line in rate.lines if line.id == payload.price_line_id), None)
        if price_line is None:
            raise CostingValidationError(f"price_line '{payload.price_line_id}' was not found on rate '{rate.id}'.")

        return {
            "category": product.category,
            "subcategory": product.subcategory,
            "title": payload.title or product.title,
            "supplier_id": product.supplier_id,
            "product_id": product.id,
            "tariff_id": rate.id,
            "price_line_id": price_line.id,
            "unit": price_line.unit,
            "time_basis": product.time_basis,
            "unit_cost_minor": price_line.amount_minor,
            "cost_currency": rate.currency,
        }

    @staticmethod
    def _resolve_manual_line(payload: ServiceLineWriteSchema) -> dict[str, Any]:
        return {
            "category": payload.category,
            "subcategory": payload.subcategory,
            "title": payload.title,
            "supplier_id": payload.supplier_id,
            "product_id": None,
            "tariff_id": None,
            "price_line_id": None,
            "unit": payload.unit,
            "time_basis": payload.time_basis,
            "unit_cost_minor": payload.unit_cost_minor,
            "cost_currency": validate_currency(payload.cost_currency),
        }

    @staticmethod
    def _rate_covers_date(rate, service_date: date | None) -> bool:
        if service_date is None:
            return True
        if not (rate.valid_from <= service_date <= rate.valid_to):
            return False
        for blackout in rate.blackout_json:
            if date.fromisoformat(blackout["from"]) <= service_date <= date.fromisoformat(blackout["to"]):
                return False
        return True

    async def _to_workbench(self, sheet: CostingSheet) -> CostingWorkbenchResponseSchema:
        lines = sorted(sheet.lines, key=lambda line: (line.day_number is None, line.day_number or 0, line.sort_order))
        line_inputs = [
            ServiceLineInput(
                line_id=line.id,
                day_number=line.day_number,
                category=line.category,
                unit_cost_minor=line.unit_cost_minor,
                qty_unit=line.qty_unit,
                qty_time=line.qty_time,
                fx_rate_ppm=line.fx_rate_ppm,
                sell_override_minor=line.sell_override_minor,
            )
            for line in lines
        ]
        summary = summarize(
            line_inputs, markup_rate_bps=sheet.markup_rate_bps, rounding_increment_minor=sheet.rounding_increment_minor
        )
        totals_by_line = {item.line_id: item for item in summary.lines}

        items: list[ServiceLineResponseSchema] = []
        for line in lines:
            totals = totals_by_line[line.id]
            product_ref = await self._product_ref(line.product_id) if line.product_id else None
            item = ServiceLineResponseSchema.model_validate(line)
            item = item.model_copy(update={"cost_minor": totals.cost_minor, "sell_minor": totals.sell_minor, "product_ref": product_ref})
            items.append(item)

        summary_schema = self._build_summary_schema(summary)

        applications = await self.repository.list_applications_for_sheet(sheet.id)
        app_schemas = [CostingApplicationResponseSchema.model_validate(app) for app in applications]

        drift = None
        if applications and sheet.quotation_id:
            latest_app = applications[0]
            costing_modified = (sheet.costing_revision != latest_app.costing_revision_at_apply)
            commercial_modified = False
            target_label = None
            try:
                quotation_req = await self.quotation_repository.get_latest_quotation_request(sheet.quotation_id)
                if quotation_req and quotation_req.request_json:
                    pricing_facts = quotation_req.request_json.get("pricing_facts") or {}
                    options = pricing_facts.get("options") or []
                    matched = next((opt for opt in options if opt.get("id") == latest_app.target_option_id), None)
                    if matched is None:
                        commercial_modified = True
                    else:
                        target_label = matched.get("label")
                        if (
                            matched.get("group_total_amount_minor") != latest_app.sell_total_minor
                            or matched.get("currency") != latest_app.currency
                        ):
                            commercial_modified = True
            except (KeyError, TypeError, AttributeError) as err:
                # Only a malformed/unexpected pricing_facts shape is safe to
                # degrade from — anything else (a real DB/connection error)
                # should propagate, not silently report "no drift" (16.3 P2 fix).
                log.warning(
                    "Drift detection could not read pricing_facts for quotation '%s': %s",
                    sheet.quotation_id,
                    err,
                )

            drift = CostingDriftSchema(
                has_drift=costing_modified or commercial_modified,
                costing_modified_since_apply=costing_modified,
                commercial_modified_since_apply=commercial_modified,
                last_applied_at=latest_app.created_at,
                last_applied_costing_revision=latest_app.costing_revision_at_apply,
                last_applied_facts_revision=latest_app.facts_revision_after,
                last_applied_sell_total_minor=latest_app.sell_total_minor,
                last_applied_currency=latest_app.currency,
                target_option_id=latest_app.target_option_id,
                target_option_label=target_label,
            )
        elif not applications and sheet.quotation_id:
            drift = CostingDriftSchema(has_drift=False)

        return CostingWorkbenchResponseSchema(
            sheet=CostingSheetResponseSchema.model_validate(sheet),
            items=items,
            summary=summary_schema,
            applications=app_schemas,
            drift=drift,
        )

    async def _product_ref(self, product_id: str) -> ProductRefSchema | None:
        product = await self.product_repository.get_by_id(product_id)
        if product is None:
            return None
        destination = await self.destination_repository.get(product.destination_id)
        return ProductRefSchema(
            property_id=product.property_id,
            destination_id=product.destination_id,
            destination_name=destination.canonical_name if destination else None,
            iata_code=destination.iata_code if destination else None,
        )
