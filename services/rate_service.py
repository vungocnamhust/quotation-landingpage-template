"""Rate aggregate service — 15.3 §1.5. Rate + lines[] + source is one aggregate;

create/update take the whole thing in one payload. Vòng đời (state machine, not
a DB constraint): draft --activate--> active --supersede--> superseded (terminal).
draft --expire--> expired is not implemented here (manual future op, out of scope §5).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef, generate_id, validate_currency
from core.rules.rate_validation import (
    BlackoutInput,
    OverlapCandidate,
    PriceLineInput,
    RateValidationContext,
    SupplementInput,
    validate_rate_for_activation,
)
from db.models.rate import Rate, RatePriceLine
from repositories.product_repository import ProductRepository
from repositories.rate_repository import RateRepository
from repositories.supplier_repository import SupplierRepository
from schemas.v2.rate import (
    RateCreateSchema,
    RateResponseSchema,
    RateSupersedeSchema,
    RateUpdateSchema,
)
from services.outbox_service import OutboxService

ID_PREFIX = "rat"
SOURCE_ID_PREFIX = "rsc"


class RateValidationError(ValueError):
    """Business-rule violation (maps to 422)."""


class RateConflictError(ValueError):
    """Lifecycle state conflict — e.g. PUT on a non-draft rate (maps to 409)."""


class RateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = RateRepository(session)
        self.product_repository = ProductRepository(session)
        self.supplier_repository = SupplierRepository(session)

    # ------------------------------------------------------------------ reads

    async def list_rates_for_product(
        self,
        product_id: str,
        *,
        lifecycle: str | None = "active",
        on_date: date | None = None,
        limit: int = 100,
    ) -> tuple[list[RateResponseSchema], int] | None:
        product = await self.product_repository.get_by_id(product_id)
        if product is None:
            return None
        rates, total = await self.repository.list_by_product(product_id, lifecycle=lifecycle, on_date=on_date, limit=limit)
        supplier = await self._supplier_for_product(product)
        items = [await self._to_response(rate, supplier=supplier) for rate in rates]
        return items, total

    async def get_rate(self, rate_id: str) -> RateResponseSchema | None:
        rate = await self.repository.get_by_id(rate_id)
        if rate is None:
            return None
        product = await self.product_repository.get_by_id(rate.product_id)
        supplier = await self._supplier_for_product(product) if product else None
        return await self._to_response(rate, supplier=supplier)

    # --------------------------------------------------------------- writes

    async def create_draft(
        self, product_id: str, payload: RateCreateSchema, *, actor: ActorRef
    ) -> RateResponseSchema | None:
        product = await self.product_repository.get_by_id(product_id)
        if product is None:
            return None
        supplier = await self._supplier_for_product(product)
        currency = await self._resolve_currency(payload.currency, supplier)
        source_id = await self._resolve_source(payload, actor=actor)

        values = self._header_values(payload, currency=currency, source_id=source_id)
        values["product_id"] = product_id
        values["created_by"] = actor.serialize()
        values["updated_by"] = actor.serialize()

        rate = await self.repository.insert_rate(rate_id=generate_id(ID_PREFIX), values=values)
        await self.repository.replace_lines(rate.id, lines=self._line_values(payload.lines, actor=actor))
        rate = await self.repository.get_by_id(rate.id)
        return await self._to_response(rate, supplier=supplier)

    async def update_draft(
        self, rate_id: str, payload: RateUpdateSchema, *, actor: ActorRef
    ) -> RateResponseSchema | None:
        rate = await self.repository.get_by_id(rate_id)
        if rate is None:
            return None
        if rate.lifecycle_status != "draft":
            raise RateConflictError("Rate is not a draft; use supersede instead of editing an active rate.")

        product = await self.product_repository.get_by_id(rate.product_id)
        supplier = await self._supplier_for_product(product) if product else None
        currency = await self._resolve_currency(payload.currency, supplier)
        source_id = await self._resolve_source(payload, actor=actor)

        values = self._header_values(payload, currency=currency, source_id=source_id)
        values["updated_by"] = actor.serialize()

        rate = await self.repository.update_header(rate, values=values)
        await self.repository.replace_lines(rate.id, lines=self._line_values(payload.lines, actor=actor))
        rate = await self.repository.get_by_id(rate.id)
        return await self._to_response(rate, supplier=supplier)

    async def delete_draft(self, rate_id: str) -> bool | None:
        rate = await self.repository.get_by_id(rate_id)
        if rate is None:
            return None
        if rate.lifecycle_status != "draft":
            raise RateConflictError("Only a draft rate can be hard-deleted.")
        await self.repository.delete_draft(rate)
        return True

    async def activate(self, rate_id: str, *, actor: ActorRef) -> RateResponseSchema | None:
        rate = await self.repository.get_by_id(rate_id)
        if rate is None:
            return None
        if rate.lifecycle_status != "draft":
            raise RateConflictError("Only a draft rate can be activated.")

        siblings = await self.repository.list_active_for_product(rate.product_id, exclude_rate_id=rate.id)
        gate_result = validate_rate_for_activation(self._build_validation_context(rate, siblings))
        if not gate_result.passed:
            raise RateValidationError("; ".join(issue.message for issue in gate_result.errors))

        flags = [issue.code for issue in gate_result.warnings]
        rate = await self.repository.set_lifecycle_status(rate, lifecycle_status="active", validation_flags=flags)

        product = await self.product_repository.get_by_id(rate.product_id)
        await OutboxService(self.session).emit_event(
            event_type="catalog.rate.activated",
            aggregate_type="rate",
            aggregate_id=rate.id,
            actor_email=actor.actor_id,
            payload={
                "rate_id": rate.id,
                "product_id": rate.product_id,
                "supplier_id": product.supplier_id if product else None,
                "season": rate.season_name,
                "validity": {"valid_from": rate.valid_from.isoformat(), "valid_to": rate.valid_to.isoformat()},
            },
        )
        supplier = await self._supplier_for_product(product) if product else None
        return await self._to_response(rate, supplier=supplier)

    async def supersede(
        self, rate_id: str, payload: RateSupersedeSchema, *, actor: ActorRef
    ) -> RateResponseSchema | None:
        old_rate = await self.repository.get_by_id(rate_id)
        if old_rate is None:
            return None
        if old_rate.lifecycle_status != "active":
            raise RateConflictError("Only an active rate can be superseded.")

        product = await self.product_repository.get_by_id(old_rate.product_id)
        supplier = await self._supplier_for_product(product) if product else None
        currency = await self._resolve_currency(payload.currency, supplier)
        source_id = await self._resolve_source(payload, actor=actor)

        values = self._header_values(payload, currency=currency, source_id=source_id)
        values["product_id"] = old_rate.product_id
        values["version"] = old_rate.version + 1
        values["supersedes_rate_id"] = old_rate.id
        values["created_by"] = actor.serialize()
        values["updated_by"] = actor.serialize()

        new_rate = await self.repository.insert_rate(rate_id=generate_id(ID_PREFIX), values=values)
        await self.repository.replace_lines(new_rate.id, lines=self._line_values(payload.lines, actor=actor))
        new_rate = await self.repository.get_by_id(new_rate.id)

        siblings = await self.repository.list_active_for_product(old_rate.product_id, exclude_rate_id=old_rate.id)
        gate_result = validate_rate_for_activation(self._build_validation_context(new_rate, siblings))
        if not gate_result.passed:
            raise RateValidationError("; ".join(issue.message for issue in gate_result.errors))
        flags = [issue.code for issue in gate_result.warnings]
        new_rate = await self.repository.set_lifecycle_status(new_rate, lifecycle_status="active", validation_flags=flags)

        old_rate = await self.repository.set_lifecycle_status(old_rate, lifecycle_status="superseded")

        await OutboxService(self.session).emit_event(
            event_type="catalog.rate.superseded",
            aggregate_type="rate",
            aggregate_id=new_rate.id,
            actor_email=actor.actor_id,
            payload={
                "old_rate_id": old_rate.id,
                "new_rate_id": new_rate.id,
                "product_id": old_rate.product_id,
                "diff": self._line_diff_summary(old_rate.lines, new_rate.lines),
            },
        )
        return await self._to_response(new_rate, supplier=supplier)

    # ------------------------------------------------------------- helpers

    async def _supplier_for_product(self, product) -> Any | None:
        if product is None or product.supplier_id is None:
            return None
        return await self.supplier_repository.get_by_id(product.supplier_id)

    async def _resolve_currency(self, currency: str | None, supplier) -> str:
        candidate = currency or (supplier.default_currency if supplier else None)
        if not candidate:
            raise RateValidationError("currency is required when the product has no supplier default_currency.")
        try:
            return validate_currency(candidate)
        except ValueError as err:
            raise RateValidationError(str(err)) from err

    async def _resolve_source(self, payload, *, actor: ActorRef) -> str | None:
        if payload.source is not None:
            source = await self.repository.insert_source(
                source_id=generate_id(SOURCE_ID_PREFIX),
                values={
                    **payload.source.model_dump(),
                    "created_by": actor.serialize(),
                    "updated_by": actor.serialize(),
                },
            )
            return source.id
        if payload.source_id is not None:
            existing = await self.repository.get_source(payload.source_id)
            if existing is None:
                raise RateValidationError(f"rate_source '{payload.source_id}' was not found.")
            return existing.id
        return None

    @staticmethod
    def _header_values(payload, *, currency: str, source_id: str | None) -> dict[str, Any]:
        return {
            "currency": currency,
            "rate_basis": payload.rate_basis,
            "commission_pct": payload.commission_pct,
            "valid_from": payload.valid_from,
            "valid_to": payload.valid_to,
            "season_name": payload.season_name,
            "blackout_json": [b.model_dump(mode="json", by_alias=True) for b in payload.blackout_json],
            "min_pax": payload.min_pax,
            "max_pax": payload.max_pax,
            "tax_included": payload.tax_included,
            "tax_pct": payload.tax_pct,
            "supplements_json": [s.model_dump(mode="json") for s in payload.supplements_json],
            "inclusions_json": list(payload.inclusions_json),
            "exclusions_json": list(payload.exclusions_json),
            "payment_terms_json": payload.payment_terms_json.model_dump(mode="json") if payload.payment_terms_json else None,
            "cancellation_policy_json": payload.cancellation_policy_json.model_dump(mode="json")
            if payload.cancellation_policy_json
            else None,
            "child_policy_json": payload.child_policy_json.model_dump(mode="json") if payload.child_policy_json else None,
            "source_id": source_id,
            "source_reference": payload.source_reference,
        }

    @staticmethod
    def _line_values(lines, *, actor: ActorRef) -> list[dict[str, Any]]:
        return [
            {
                **line.model_dump(mode="json"),
                "created_by": actor.serialize(),
                "updated_by": actor.serialize(),
            }
            for line in lines
        ]

    @staticmethod
    def _build_validation_context(rate: Rate, siblings: list[Rate]) -> RateValidationContext:
        return RateValidationContext(
            valid_from=rate.valid_from,
            valid_to=rate.valid_to,
            rate_basis=rate.rate_basis,
            commission_pct=rate.commission_pct,
            lines=tuple(PriceLineInput(amount_minor=line.amount_minor) for line in rate.lines),
            blackouts=tuple(
                BlackoutInput(from_date=date.fromisoformat(b["from"]), to_date=date.fromisoformat(b["to"]))
                for b in rate.blackout_json
            ),
            supplements=tuple(
                SupplementInput(
                    applies_from=date.fromisoformat(s["applies_from"]), applies_to=date.fromisoformat(s["applies_to"])
                )
                for s in rate.supplements_json
            ),
            other_active_rates=tuple(
                OverlapCandidate(rate_id=sibling.id, valid_from=sibling.valid_from, valid_to=sibling.valid_to)
                for sibling in siblings
            ),
        )

    @staticmethod
    def _line_diff_summary(old_lines: list[RatePriceLine], new_lines: list[RatePriceLine]) -> dict[str, Any]:
        old_amounts = [line.amount_minor for line in old_lines]
        new_amounts = [line.amount_minor for line in new_lines]

        def _pct_delta(old_value: int | None, new_value: int | None) -> float | None:
            if not old_value or new_value is None:
                return None
            return round(((new_value - old_value) / old_value) * 100, 2)

        old_min, old_max = (min(old_amounts), max(old_amounts)) if old_amounts else (None, None)
        new_min, new_max = (min(new_amounts), max(new_amounts)) if new_amounts else (None, None)
        return {
            "min_pct": _pct_delta(old_min, new_min),
            "max_pct": _pct_delta(old_max, new_max),
        }

    async def _to_response(self, rate: Rate, *, supplier) -> RateResponseSchema:
        source = await self.repository.get_source(rate.source_id) if rate.source_id else None

        resolved_payment_terms, inherited_payment_terms = self._resolve_policy(
            rate.payment_terms_json, supplier.payment_terms_json if supplier else None
        )
        resolved_cancellation_policy, inherited_cancellation_policy = self._resolve_policy(
            rate.cancellation_policy_json, supplier.cancellation_policy_json if supplier else None
        )
        resolved_child_policy, inherited_child_policy = self._resolve_policy(
            rate.child_policy_json, supplier.child_policy_json if supplier else None
        )

        values = {
            "id": rate.id,
            "product_id": rate.product_id,
            "currency": rate.currency,
            "rate_basis": rate.rate_basis,
            "commission_pct": rate.commission_pct,
            "valid_from": rate.valid_from,
            "valid_to": rate.valid_to,
            "season_name": rate.season_name,
            "blackout_json": rate.blackout_json,
            "min_pax": rate.min_pax,
            "max_pax": rate.max_pax,
            "tax_included": rate.tax_included,
            "tax_pct": rate.tax_pct,
            "supplements_json": rate.supplements_json,
            "inclusions_json": rate.inclusions_json,
            "exclusions_json": rate.exclusions_json,
            "payment_terms_json": rate.payment_terms_json,
            "cancellation_policy_json": rate.cancellation_policy_json,
            "child_policy_json": rate.child_policy_json,
            "version": rate.version,
            "supersedes_rate_id": rate.supersedes_rate_id,
            "lifecycle_status": rate.lifecycle_status,
            "review_status": rate.review_status,
            "validation_flags_json": rate.validation_flags_json,
            "source_id": rate.source_id,
            "source_reference": rate.source_reference,
            "created_at": rate.created_at,
            "updated_at": rate.updated_at,
            "lines": sorted(rate.lines, key=lambda line: line.sort_order),
            "source": source,
            "resolved_payment_terms_json": resolved_payment_terms,
            "resolved_cancellation_policy_json": resolved_cancellation_policy,
            "resolved_child_policy_json": resolved_child_policy,
            "inherited_from_supplier": {
                "payment_terms": inherited_payment_terms,
                "cancellation_policy": inherited_cancellation_policy,
                "child_policy": inherited_child_policy,
            },
        }
        return RateResponseSchema.model_validate(values)

    @staticmethod
    def _resolve_policy(rate_value: dict | None, supplier_value: dict | None) -> tuple[dict | None, bool]:
        if rate_value is not None:
            return rate_value, False
        return supplier_value, supplier_value is not None
