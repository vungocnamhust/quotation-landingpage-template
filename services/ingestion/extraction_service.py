"""Extraction service (15.8 §1.1/§1.6) — sanitize -> Extractor agent (0 tools) -> deterministic
parse. This is the ONLY place the raw pasted text is ever seen by an LLM; the Extractor agent
has zero tools, so it never gets a chance to *act* on text that reads like an instruction.

Owns the ``ingestion_batches`` staging row through its first snapshot. Never imports a
catalog repository/service (15.8 chốt #1) — the only DB writes here are to
``ingestion_batches``/``ai_runs``.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef, generate_id
from core.rules.ingest_parser import (
    ParsedAmount,
    ParsedCancellationPolicy,
    ParsedPaxTier,
    ParsedValidity,
    parse_amount_text,
    parse_cancellation_policy_text,
    parse_tier_pax_text,
    parse_validity_text,
)
from core.rules.ingest_sanitizer import sanitize_ingest_text, wrap_with_delimiter
from db.models.ingestion import IngestionBatch
from repositories.ingestion_repository import IngestionRepository
from schemas.catalog_ingest import CatalogIngestPayload, UnresolvedItem
from services.ai_platform.guardrails import OutputValidator, RunBudget
from services.ai_platform.runs import record_run
from services.ai_platform.runtime import build_agent

ID_PREFIX = "igb"
DEFAULT_TENANT_ID = "capella"
AGENT_NAME = "ingest_extractor"


class ExtractionError(RuntimeError):
    """The Extractor agent failed to return a valid payload after retries."""


def _quote_verified(source_quote: str | None, sanitized_text: str) -> bool:
    """A source_quote must be a real, verbatim excerpt — never hallucinated."""
    return bool(source_quote) and source_quote.strip() in sanitized_text


async def _run_extractor(sanitized_text: str) -> CatalogIngestPayload:
    agent = build_agent(AGENT_NAME, output_type=CatalogIngestPayload, prompt_file="ingest_extractor", tools=())
    try:
        result = await agent.run(wrap_with_delimiter(sanitized_text))
    except Exception as exc:  # pragma: no cover - network/provider errors
        raise ExtractionError("The Extractor agent did not return a valid payload.") from exc
    return result.output


def verify_source_quotes(payload: CatalogIngestPayload, sanitized_text: str) -> CatalogIngestPayload:
    """Drop any candidate whose ``source_quote`` cannot be found verbatim in the raw text —
    "bỏ dòng, không nổ run" (OutputValidator). Dropped candidates become ``unresolved[]``.
    """
    validator = OutputValidator()
    extra_unresolved: list[UnresolvedItem] = []

    def _keep(item: Any) -> bool:
        if _quote_verified(item.source_quote, sanitized_text):
            return True
        extra_unresolved.append(
            UnresolvedItem(
                description=f"unverifiable candidate: {item.source_quote[:120]!r}",
                reason="source_quote not found verbatim in raw text",
            )
        )
        return False

    products = validator.filter_valid(payload.products, is_valid=_keep, reason="unverified source_quote")
    rate_groups = validator.filter_valid(payload.rate_groups, is_valid=_keep, reason="unverified source_quote")

    supplier = payload.supplier
    if supplier is not None and not _quote_verified(supplier.source_quote, sanitized_text):
        extra_unresolved.append(
            UnresolvedItem(
                description=f"unverifiable supplier candidate: {supplier.source_quote[:120]!r}",
                reason="source_quote not found verbatim in raw text",
            )
        )
        supplier = None

    return payload.model_copy(
        update={
            "products": products,
            "rate_groups": rate_groups,
            "supplier": supplier,
            "unresolved": [*payload.unresolved, *extra_unresolved],
        }
    )


def _amount_dict(amount: ParsedAmount) -> dict[str, Any]:
    return asdict(amount)


def _validity_dict(validity: ParsedValidity) -> dict[str, Any]:
    return asdict(validity)


def _tier_dict(tier: ParsedPaxTier) -> dict[str, Any]:
    return asdict(tier)


def _policy_dict(policy: ParsedCancellationPolicy) -> dict[str, Any]:
    return {
        "tiers": [asdict(t) for t in policy.tiers],
        "no_show_penalty_percent": policy.no_show_penalty_percent,
        "ambiguous": policy.ambiguous,
        "reason": policy.reason,
    }


def parse_payload(payload: CatalogIngestPayload) -> tuple[CatalogIngestPayload, dict[str, Any]]:
    """Deterministically parse every ``*_text`` field (``core/rules/ingest_parser``, pure).

    Returns ``(payload, parsed)`` — ``parsed`` is a JSON-pointer-keyed annotation tree.
    Anything ambiguous is ALSO appended to ``payload.unresolved`` (never silently dropped);
    the LLM never computes any of these values itself (15.8 chốt #3).
    """
    parsed: dict[str, Any] = {"rate_groups": []}
    new_unresolved = list(payload.unresolved)

    for rg_index, rate_group in enumerate(payload.rate_groups):
        rg_path = f"/rate_groups/{rg_index}"
        validity = parse_validity_text(rate_group.validity_text)
        rg_entry: dict[str, Any] = {"validity": _validity_dict(validity)}
        if validity.ambiguous:
            new_unresolved.append(
                UnresolvedItem(
                    description=f"validity_text '{rate_group.validity_text}' is ambiguous ({rg_path})",
                    reason=validity.reason,
                    source_quote=rate_group.source_quote,
                    target_path=f"{rg_path}/validity_text",
                )
            )

        if rate_group.policy_text:
            policy = parse_cancellation_policy_text(rate_group.policy_text)
            rg_entry["cancellation_policy"] = _policy_dict(policy)
            if policy.ambiguous:
                new_unresolved.append(
                    UnresolvedItem(
                        description=f"cancellation policy_text is ambiguous ({rg_path})",
                        reason=policy.reason,
                        source_quote=rate_group.source_quote,
                        target_path=f"{rg_path}/policy_text",
                    )
                )

        line_entries: list[dict[str, Any]] = []
        for pl_index, line in enumerate(rate_group.price_lines):
            amount = parse_amount_text(line.amount_text, line.currency_text)
            line_entry: dict[str, Any] = {"amount": _amount_dict(amount)}
            if line.tier_pax_text:
                tier = parse_tier_pax_text(line.tier_pax_text)
                line_entry["tier"] = _tier_dict(tier)
                if tier.ambiguous:
                    new_unresolved.append(
                        UnresolvedItem(
                            description=f"tier_pax_text '{line.tier_pax_text}' is ambiguous ({rg_path}/price_lines/{pl_index})",
                            reason=tier.reason,
                            source_quote=line.source_quote,
                            target_path=f"{rg_path}/price_lines/{pl_index}/tier_pax_text",
                        )
                    )
            if amount.ambiguous:
                new_unresolved.append(
                    UnresolvedItem(
                        description=f"amount_text '{line.amount_text}' is ambiguous ({rg_path}/price_lines/{pl_index})",
                        reason=amount.reason,
                        source_quote=line.source_quote,
                        target_path=f"{rg_path}/price_lines/{pl_index}/amount_text",
                    )
                )
            line_entries.append(line_entry)
        rg_entry["price_lines"] = line_entries

        supplement_entries: list[dict[str, Any]] = []
        for sp_index, supplement in enumerate(rate_group.supplements):
            amount = parse_amount_text(supplement.amount_text, supplement.currency_text)
            supplement_entries.append({"amount": _amount_dict(amount)})
            if amount.ambiguous:
                new_unresolved.append(
                    UnresolvedItem(
                        description=f"supplement amount_text '{supplement.amount_text}' is ambiguous ({rg_path}/supplements/{sp_index})",
                        reason=amount.reason,
                        source_quote=supplement.source_quote,
                        target_path=f"{rg_path}/supplements/{sp_index}/amount_text",
                    )
                )
        if supplement_entries:
            rg_entry["supplements"] = supplement_entries

        parsed["rate_groups"].append(rg_entry)

    updated_payload = payload.model_copy(update={"unresolved": new_unresolved})
    return updated_payload, parsed


async def create_batch(
    session: AsyncSession,
    *,
    raw_text: str,
    source_channel: str,
    source_document_type: str,
    idempotency_key: str,
    actor: ActorRef,
    tenant_id: str = DEFAULT_TENANT_ID,
) -> tuple[IngestionBatch, CatalogIngestPayload, dict[str, Any], bool]:
    """Sanitize -> Extractor (0 tool) -> parse -> persist the batch's first snapshot.

    Returns ``(batch, payload, parsed, is_replay)`` — ``is_replay`` is true when
    ``idempotency_key`` already matched an existing batch (no new Extractor call was made).
    """
    repository = IngestionRepository(session)
    existing = await repository.get_by_idempotency_key(idempotency_key, tenant_id=tenant_id)
    if existing is not None:
        stored = existing.payload_json or {}
        payload = CatalogIngestPayload.model_validate(stored.get("payload", {}))
        return existing, payload, stored.get("parsed", {}), True

    sanitized = sanitize_ingest_text(raw_text)
    budget = RunBudget(max_calls=0)  # Extractor is 0-tool by architecture
    extracted = await _run_extractor(sanitized)
    verified = verify_source_quotes(extracted, sanitized)
    parsed_payload, parsed = parse_payload(verified)

    needs_clarification = bool(parsed_payload.unresolved) or parsed_payload.covers_multiple_suppliers
    status = "needs_clarification" if needs_clarification else "draft"

    batch = await repository.insert(
        batch_id=generate_id(ID_PREFIX),
        tenant_id=tenant_id,
        values={
            "status": status,
            "raw_text": sanitized,
            "source_channel": source_channel,
            "source_document_type": source_document_type,
            "payload_json": {"payload": parsed_payload.model_dump(mode="json"), "parsed": parsed},
            "conversation_json": [],
            "operator_edits_json": {},
            "idempotency_key": idempotency_key,
            "created_by": actor.serialize(),
            "updated_by": actor.serialize(),
        },
    )
    await record_run(
        session,
        agent_name=AGENT_NAME,
        anchor_type="ingestion_batch",
        anchor_id=batch.id,
        status="succeeded",
        idempotency_key=idempotency_key,
        input_ref={"raw_text_length": len(sanitized), "source_channel": source_channel},
        output={
            "products": len(parsed_payload.products),
            "rate_groups": len(parsed_payload.rate_groups),
            "unresolved": len(parsed_payload.unresolved),
        },
        stats=budget.stats(),
        actor=actor,
        tenant_id=tenant_id,
    )
    return batch, parsed_payload, parsed, False
