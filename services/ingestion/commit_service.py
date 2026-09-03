"""Commit service (15.8 §1.7 Commit, chốt #7) — the ONLY file in ``services/ingestion/``
allowed to import a catalog repository/service. Replays a ``ready`` batch's resolved content
through the real 15.1–15.3 write path — ``SupplierService`` / ``ProductService`` /
``RateService`` — as ``actor=ActorRef("staff", operator_email)``, all inside the caller's
single DB transaction (the router commits once, after this returns).

Nothing here computes a money amount or a date — those already exist as typed values in the
batch's ``payload_json["parsed"]`` tree (``core/rules/ingest_parser.py`` output), stored back
at extraction/resolution time. This module only maps that typed data onto the existing
15.1–15.3 Pydantic create/update schemas and calls the existing public service methods.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef
from core.rules.catalog_vocab import DEFAULT_CHARGE_UNIT_BY_CATEGORY
from db.models.ingestion import IngestionBatch
from repositories.destination_repository import DestinationRepository
from repositories.ingestion_repository import IngestionRepository
from repositories.rate_repository import RateRepository
from schemas.catalog_ingest import CatalogIngestPayload
from schemas.v2.product import ProductCreateSchema, ProductUpdateSchema
from schemas.v2.rate import RateCreateSchema, RatePriceLineCreateSchema, RateSourceCreateSchema, RateSupersedeSchema
from schemas.v2.supplier import SupplierContactSchema, SupplierCreateSchema, SupplierType
from services.outbox_service import OutboxService
from services.product_service import ProductConflictError, ProductService, ProductValidationError
from services.rate_service import RateConflictError, RateService, RateValidationError
from services.supplier_service import SupplierService

DEFAULT_TENANT_ID = "capella"
DEFAULT_SUPPLIER_TYPE: SupplierType = "dmc"
DEFAULT_CURRENCY = "VND"
_ID_TARGET_TYPES = frozenset({"supplier", "product", "rate"})


class CommitError(ValueError):
    """A batch is not in a committable state, or its resolved content is incomplete."""


def apply_edits_overlay(payload_dict: dict[str, Any], edits: dict[str, str]) -> dict[str, Any]:
    """Merge the operator's inline text-edit overlay (Edit endpoint, §1.7) onto a payload dict.

    ``edits`` is a flat ``{target_path: text_value}`` map, same shape used by
    ``resolution_service`` for clarification-answer overlays.
    """
    from services.ingestion.resolution_service import _apply_pointer  # local import: avoid a cycle at module load

    merged = copy.deepcopy(payload_dict)
    for target_path, value in edits.items():
        if not target_path.endswith("_text"):
            continue
        _apply_pointer(merged, target_path, value)
    return merged


def _majority_currency(parsed: dict[str, Any]) -> str:
    counts: dict[str, int] = {}
    for rate_group in parsed.get("rate_groups", []):
        for line in rate_group.get("price_lines", []):
            currency = (line.get("amount") or {}).get("currency")
            if currency:
                counts[currency] = counts.get(currency, 0) + 1
    if not counts:
        return DEFAULT_CURRENCY
    return max(counts, key=lambda k: counts[k])


def _guess_supplier_type(type_hint: str | None) -> SupplierType:
    allowed = set(SupplierType.__args__)
    if type_hint and type_hint.strip().lower() in allowed:
        return type_hint.strip().lower()  # type: ignore[return-value]
    return DEFAULT_SUPPLIER_TYPE


async def _resolve_or_create_supplier(
    session: AsyncSession,
    payload: CatalogIngestPayload,
    parsed: dict[str, Any],
    entry: dict[str, Any] | None,
    *,
    actor: ActorRef,
) -> str | None:
    if payload.supplier is None:
        return None
    service = SupplierService(session)
    action = entry["action"] if entry else "create"
    matched_id = entry.get("matched_id") if entry else None

    if action == "skip_duplicate" and matched_id:
        return matched_id
    if action == "update" and matched_id:
        # H4: never overwrite contact_json here — the ingest payload carries no contact
        # field mapped onto SupplierContactSchema, so calling update_supplier with an EMPTY
        # one would silently wipe the existing supplier's real contact info. "update" for a
        # supplier is a no-op confirmation (the dedupe match itself is the useful signal);
        # commit only ever touches products/rates for this candidate.
        return matched_id
    if action == "create":
        created = await service.create_supplier(
            SupplierCreateSchema(
                name=payload.supplier.name_text,
                supplier_type=_guess_supplier_type(payload.supplier.type_hint),
                default_currency=_majority_currency(parsed),
                contact_json=SupplierContactSchema(),
            ),
            actor=actor,
        )
        return created.id
    raise CommitError(f"supplier resolution action '{action}' is not committable")


async def _resolve_or_create_product(
    session: AsyncSession,
    payload: CatalogIngestPayload,
    entry: dict[str, Any],
    supplier_id: str | None,
    *,
    actor: ActorRef,
) -> str:
    index = int(entry["entity_ref"].strip("/").split("/")[1])
    candidate = payload.products[index]
    if candidate.category_hint is None:
        raise CommitError(f"product[{index}] '{candidate.title_text}' is missing category_hint — cannot commit")

    destination_text = candidate.destination_text or (payload.supplier.destination_text if payload.supplier else None)
    destination = await DestinationRepository(session).resolve(destination_text) if destination_text else None
    if destination is None:
        raise CommitError(f"product[{index}] '{candidate.title_text}' has no resolvable destination — cannot commit")

    unit_hint = candidate.unit_hint
    time_basis_hint = candidate.time_basis_hint
    if unit_hint is None or time_basis_hint is None:
        default_unit, default_time_basis = DEFAULT_CHARGE_UNIT_BY_CATEGORY[candidate.category_hint]
        unit_hint = unit_hint or default_unit
        time_basis_hint = time_basis_hint or default_time_basis

    service = ProductService(session)
    action = entry["action"]
    matched_id = entry.get("matched_id")

    if action == "skip_duplicate" and matched_id:
        return matched_id
    if action == "update" and matched_id:
        updated = await service.update_product(matched_id, ProductUpdateSchema(title=candidate.title_text), actor=actor)
        return updated.id if updated else matched_id
    if action == "create":
        try:
            created = await service.create_product(
                ProductCreateSchema(
                    supplier_id=supplier_id,
                    destination_id=destination.id,
                    category=candidate.category_hint,
                    subcategory=candidate.subcategory_hint,
                    title=candidate.title_text,
                    unit=unit_hint,
                    time_basis=time_basis_hint,
                ),
                actor=actor,
            )
        except (ProductValidationError, ProductConflictError) as exc:
            raise CommitError(str(exc)) from exc
        return created.id
    raise CommitError(f"product[{index}] resolution action '{action}' is not committable")


def _price_lines_for(rate_group_parsed: dict[str, Any], candidate) -> list[RatePriceLineCreateSchema]:
    lines: list[RatePriceLineCreateSchema] = []
    for order, (line, line_parsed) in enumerate(zip(candidate.price_lines, rate_group_parsed.get("price_lines", []))):
        amount = line_parsed.get("amount") or {}
        if amount.get("ambiguous") or amount.get("minor_units") is None:
            raise CommitError(f"rate price line '{line.source_quote}' has no resolved amount — cannot commit")
        if line.price_for_hint is None:
            raise CommitError(f"rate price line '{line.source_quote}' is missing price_for_hint — cannot commit")
        tier = line_parsed.get("tier") or {}
        lines.append(
            RatePriceLineCreateSchema(
                price_for=line.price_for_hint,
                occupancy_basis=line.occupancy_hint or "na",
                unit="room" if line.price_for_hint == "room" else "person",
                tier_min_pax=tier.get("tier_min"),
                tier_max_pax=tier.get("tier_max"),
                amount_minor=amount["minor_units"],
                sort_order=order,
            )
        )
    if not lines:
        raise CommitError("rate group has no committable price lines")
    return lines


async def _commit_rate_group(
    session: AsyncSession,
    payload: CatalogIngestPayload,
    parsed: dict[str, Any],
    entry: dict[str, Any],
    product_ids_by_title: dict[str, str],
    source: RateSourceCreateSchema | None,
    source_id: str | None,
    *,
    actor: ActorRef,
) -> tuple[str | None, str | None]:
    """Returns (rate_id_or_None, source_id_used)."""
    index = int(entry["entity_ref"].strip("/").split("/")[1])
    candidate = payload.rate_groups[index]
    rg_parsed = parsed["rate_groups"][index]
    validity = rg_parsed.get("validity") or {}

    if validity.get("ambiguous") or validity.get("kind") != "date_range":
        raise CommitError(f"rate_group[{index}] validity is not a concrete date range — cannot commit")

    product_id = product_ids_by_title.get(candidate.product_title_text)
    if product_id is None:
        raise CommitError(f"rate_group[{index}] has no resolved product — cannot commit")

    lines = _price_lines_for(rg_parsed, candidate)
    valid_from = date.fromisoformat(validity["date_from"])
    valid_to = date.fromisoformat(validity["date_to"])

    header_kwargs: dict[str, Any] = {
        "rate_basis": candidate.rate_basis_hint or "net",
        "valid_from": valid_from,
        "valid_to": valid_to,
        "lines": lines,
    }
    if source is not None:
        header_kwargs["source"] = source
    elif source_id is not None:
        header_kwargs["source_id"] = source_id

    service = RateService(session)
    action = entry["action"]
    try:
        if action == "skip_duplicate":
            return entry.get("matched_id"), source_id
        if action == "supersede_rate":
            active_rates = await RateRepository(session).list_active_for_product(product_id)
            overlapping = [r for r in active_rates if r.valid_from <= valid_to and valid_from <= r.valid_to]
            if not overlapping:
                raise CommitError(f"rate_group[{index}] proposed supersede_rate but no active rate overlaps it")
            result = await service.supersede(overlapping[0].id, RateSupersedeSchema(**header_kwargs), actor=actor)
        elif action == "create":
            result = await service.create_draft(product_id, RateCreateSchema(product_id=product_id, **header_kwargs), actor=actor)
            if result is not None:
                result = await service.activate(result.id, actor=actor)
        else:
            raise CommitError(f"rate_group[{index}] resolution action '{action}' is not committable")
    except (RateValidationError, RateConflictError) as exc:
        raise CommitError(str(exc)) from exc
    except IntegrityError as exc:
        # Unlike SupplierService/ProductService (Track 1 audit R-M2), RateService does not
        # wrap its own inserts in a savepoint, so a duplicate/conflicting rate can still
        # reach this call as a raw IntegrityError. Converting it here — rather than letting
        # it leak out as an unhandled 500 — relies on commit_batch's own begin_nested() (this
        # function's caller) to roll back to its savepoint; this function must not call
        # session.rollback() itself, which would discard the whole batch's outer transaction.
        raise CommitError(f"rate_group[{index}] conflicts with an existing rate — cannot commit") from exc

    if result is None:
        raise CommitError(f"rate_group[{index}] could not be committed (product not found)")
    return result.id, result.source_id


async def commit_batch(
    session: AsyncSession,
    *,
    batch: IngestionBatch,
    actor: ActorRef,
    expected_revision: int,
    idempotency_key: str,
    acknowledge_unresolved: bool = False,
    tenant_id: str = DEFAULT_TENANT_ID,
) -> IngestionBatch:
    """Replay a ``ready`` (or blocking-free ``draft``) batch into the real catalog, one
    transaction, then record ``rate_sources`` + emit ``catalog.ingestion.committed``.
    """
    if batch.status == "committed":
        return batch  # idempotent replay — nothing new to do
    if batch.status not in ("ready", "draft", "needs_clarification"):
        raise CommitError(f"batch '{batch.id}' is '{batch.status}' and cannot be committed")

    stored = batch.payload_json or {}
    payload_dict = apply_edits_overlay(stored.get("payload", {}), batch.operator_edits_json or {})
    payload = CatalogIngestPayload.model_validate(payload_dict)
    parsed = stored.get("parsed", {})

    if payload.unresolved and not acknowledge_unresolved:
        raise CommitError(f"batch '{batch.id}' has {len(payload.unresolved)} unresolved item(s) that must be acknowledged before commit")

    resolution = batch.resolution_json or {}
    entries = resolution.get("entries", [])
    blocking = [c for c in resolution.get("clarifications", []) if c.get("blocking")]
    if blocking:
        raise CommitError(f"batch '{batch.id}' has {len(blocking)} unanswered blocking clarification(s)")
    if any(e.get("action") == "needs_input" for e in entries):
        raise CommitError(f"batch '{batch.id}' still has entries marked needs_input")

    async with session.begin_nested():
        supplier_entry = next((e for e in entries if e["entity_type"] == "supplier"), None)
        supplier_id = await _resolve_or_create_supplier(session, payload, parsed, supplier_entry, actor=actor)

        product_ids_by_title: dict[str, str] = {}
        created_products: list[str] = []
        for entry in [e for e in entries if e["entity_type"] == "product"]:
            product_id = await _resolve_or_create_product(session, payload, entry, supplier_id, actor=actor)
            index = int(entry["entity_ref"].strip("/").split("/")[1])
            product_ids_by_title[payload.products[index].title_text] = product_id
            created_products.append(product_id)

        rate_source: RateSourceCreateSchema | None = None
        if supplier_id is not None:
            rate_source = RateSourceCreateSchema(
                supplier_id=supplier_id,
                document_type=batch.source_document_type,
                channel=batch.source_channel,
                received_at=datetime.now(timezone.utc),
                notes=f"Ingested via Interactive Ingestion Co-Pilot, batch {batch.id}",
            )

        created_rates: list[str] = []
        reused_source_id: str | None = None
        for entry in [e for e in entries if e["entity_type"] == "rate"]:
            rate_id, used_source_id = await _commit_rate_group(
                session, payload, parsed, entry, product_ids_by_title, rate_source if reused_source_id is None else None, reused_source_id, actor=actor
            )
            if reused_source_id is None:
                reused_source_id = used_source_id
            if rate_id:
                created_rates.append(rate_id)

        commit_result = {
            "supplier_id": supplier_id,
            "product_ids": created_products,
            "rate_ids": created_rates,
            "rate_source_id": reused_source_id,
            "committed_at": datetime.now(timezone.utc).isoformat(),
        }

        await OutboxService(session).emit_event(
            event_type="catalog.ingestion.committed",
            aggregate_type="ingestion_batch",
            aggregate_id=batch.id,
            actor_email=actor.actor_id,
            payload=commit_result,
        )

        repository = IngestionRepository(session)
        return await repository.update_guarded(
            batch,
            expected_revision=expected_revision,
            values={
                "status": "committed",
                "commit_result_json": commit_result,
                "updated_by": actor.serialize(),
            },
        )
