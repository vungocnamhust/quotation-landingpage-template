"""Resolution service (15.8 §1.1/§1.6) — Resolver Co-Pilot (toolset B) + deterministic
verification + bounded Q&A.

The Resolver agent NEVER sees ``raw_text`` — only the already-parsed ``CatalogIngestPayload``
(15.8 chốt #2; every function here takes a payload, none takes raw text). It proposes; it
never decides — every ``ResolutionEntry`` it returns is re-verified against the real catalog
(dedupe keys, ``DestinationRepository.resolve``, rate-window overlap) before being trusted
(15.8 chốt #5). A ``matched_id`` is only accepted when it was actually seen via a tool call
in this run (the ``AllowlistRecorder``) — the LLM cannot invent an id.
"""
from __future__ import annotations

import copy
import re
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef
from core.rules.catalog_vocab import CATEGORY
from db.models.ingestion import IngestionBatch
from repositories.destination_repository import DestinationRepository
from repositories.ingestion_repository import IngestionRepository
from repositories.product_repository import ProductRepository
from repositories.rate_repository import RateRepository
from repositories.supplier_repository import SupplierRepository
from schemas.catalog_ingest import CatalogIngestPayload, Clarification, ResolutionEntry, ResolutionPlan, UnresolvedItem
from services.ai_platform.deps import CatalogReadOnlyDeps
from services.ai_platform.guardrails import AllowlistRecorder, RunBudget
from services.ai_platform.runs import record_run
from services.ai_platform.runtime import build_agent, run_agent
from services.ai_platform.toolsets.catalog import CATALOG_TOOLSET_B
from services.ingestion.extraction_service import parse_payload
from services.product_service import normalize_product_title
from services.supplier_service import normalize_supplier_name

AGENT_NAME = "ingest_resolver"
MAX_QA_ROUNDS = 2
MAX_TOOL_CALLS = 24
DEFAULT_TENANT_ID = "capella"

_TERMINAL_STATUSES = frozenset({"committed", "rejected", "archived"})


class ResolutionError(RuntimeError):
    pass


class TooManyClarificationRoundsError(ResolutionError):
    def __init__(self) -> None:
        super().__init__(f"This batch has already used its {MAX_QA_ROUNDS} clarification rounds.")


class BatchNotAnswerableError(ResolutionError):
    def __init__(self, batch_id: str, status: str) -> None:
        super().__init__(f"Batch '{batch_id}' is '{status}' and cannot accept new answers.")
        self.batch_id = batch_id
        self.status = status


def _windows_overlap(a_from: date, a_to: date, b_from: date, b_to: date) -> bool:
    return a_from <= b_to and b_from <= a_to


def _index_from_ref(entity_ref: str, collection: str) -> int | None:
    """Extract an index from an ``entity_ref`` the model produced for ``collection``.

    Tolerant of the several reasonable ways a model renders "products, item 0" —
    ``/products/0``, ``products/0``, ``products[0]``, ``products.0`` — rather than
    requiring one exact JSON-pointer string, since LLM output on this point is not fully
    deterministic even with prompt guidance.
    """
    match = re.search(rf"{re.escape(collection)}\D*(\d+)", entity_ref)
    return int(match.group(1)) if match else None


def _apply_pointer(data: dict[str, Any], pointer: str, value: Any) -> None:
    parts = [p for p in pointer.strip("/").split("/") if p]
    if not parts:
        raise ValueError(f"invalid target_path '{pointer}'")
    node: Any = data
    for part in parts[:-1]:
        key: Any = int(part) if part.isdigit() else part
        node = node[key]
    last = parts[-1]
    key = int(last) if last.isdigit() else last
    node[key] = value


async def _run_resolver(
    session: AsyncSession, tenant_id: str, payload: CatalogIngestPayload
) -> tuple[ResolutionPlan, AllowlistRecorder, RunBudget]:
    allowlist = AllowlistRecorder()
    budget = RunBudget(max_calls=MAX_TOOL_CALLS)
    deps = CatalogReadOnlyDeps(session=session, tenant_id=tenant_id, allowlist=allowlist, budget=budget)
    agent = build_agent(
        AGENT_NAME,
        output_type=ResolutionPlan,
        prompt_file="ingest_resolver",
        deps_type=CatalogReadOnlyDeps,
        tools=CATALOG_TOOLSET_B,
    )
    try:
        result = await run_agent(agent, payload.model_dump_json(), deps=deps)
    except Exception as exc:  # pragma: no cover - network/provider errors
        raise ResolutionError("The Resolver agent did not return a valid plan.") from exc
    budget.record_usage(result.usage)
    return result.output, allowlist, budget


async def _verify_supplier_entry(
    session: AsyncSession,
    tenant_id: str,
    payload: CatalogIngestPayload,
    entry: ResolutionEntry,
    allowlist: AllowlistRecorder,
    action_overrides: dict[str, str],
) -> tuple[ResolutionEntry, str | None]:
    """Returns (verified_entry, resolved_supplier_id_or_None) — the id feeds product verification."""
    if payload.supplier is None:
        return entry.model_copy(update={"action": "needs_input", "evidence": "no supplier candidate in payload"}), None

    if entry.matched_id and not allowlist.contains(entry.matched_id):
        entry = entry.model_copy(update={"matched_id": None, "action": "needs_input", "evidence": "matched_id was not seen via a tool call this run"})

    normalized = normalize_supplier_name(payload.supplier.name_text)
    existing = await SupplierRepository(session).get_by_normalized_name(normalized, tenant_id=tenant_id)
    override = action_overrides.get("supplier-dedupe")

    if existing is not None:
        if entry.action == "create":
            if override == "update_existing":
                return entry.model_copy(update={"action": "update", "matched_id": existing.id, "evidence": "operator confirmed: update the existing supplier", "clarifications": []}), existing.id
            if override == "create_new_anyway":
                return entry.model_copy(update={"action": "create", "matched_id": None, "evidence": "operator confirmed: create a new supplier despite the name match", "clarifications": []}), None
            return entry.model_copy(
                update={
                    "action": "needs_input",
                    "matched_id": existing.id,
                    "evidence": f"dedupe key already matches existing supplier '{existing.id}'",
                    "clarifications": [
                        Clarification(
                            id="supplier-dedupe",
                            question=f"'{payload.supplier.name_text}' looks like the existing supplier '{existing.name}'. Update it instead of creating a new one?",
                            blocking=True,
                            target_path="/supplier",
                            options=["update_existing", "create_new_anyway"],
                        )
                    ],
                },
            ), existing.id
        if entry.action == "update" and entry.matched_id != existing.id:
            return entry.model_copy(update={"action": "needs_input", "matched_id": existing.id, "evidence": "matched_id does not match the real dedupe result"}), existing.id
        return entry, existing.id

    if entry.action in ("update", "skip_duplicate"):
        return entry.model_copy(update={"action": "needs_input", "matched_id": None, "evidence": "no existing supplier found for update/skip_duplicate"}), None
    return entry, None


async def _verify_product_entry(
    session: AsyncSession,
    tenant_id: str,
    payload: CatalogIngestPayload,
    entry: ResolutionEntry,
    allowlist: AllowlistRecorder,
    supplier_id: str | None,
    action_overrides: dict[str, str],
) -> tuple[ResolutionEntry, str | None, str | None]:
    """Returns (verified_entry, resolved_product_id_or_None, product_title_text_or_None)."""
    index = _index_from_ref(entry.entity_ref, "products")
    if index is None or index >= len(payload.products):
        return entry.model_copy(update={"action": "needs_input", "evidence": "entity_ref does not point to a real product candidate"}), None, None
    candidate = payload.products[index]

    if entry.matched_id and not allowlist.contains(entry.matched_id):
        entry = entry.model_copy(update={"matched_id": None, "action": "needs_input", "evidence": "matched_id was not seen via a tool call this run"})

    destination_text = candidate.destination_text or (payload.supplier.destination_text if payload.supplier else None)
    destination = await DestinationRepository(session).resolve(destination_text) if destination_text else None
    if destination is None:
        return entry.model_copy(
            update={
                "action": "needs_input",
                "evidence": "destination could not be resolved",
                "clarifications": [
                    Clarification(
                        id=f"product-{index}-destination",
                        question=f"Which destination is '{candidate.title_text}' in?",
                        blocking=True,
                        source_quote=candidate.source_quote,
                        target_path=f"/products/{index}/destination_text",
                    )
                ],
            }
        ), None, candidate.title_text

    if candidate.category_hint is None:
        return entry.model_copy(
            update={
                "action": "needs_input",
                "evidence": "category_hint is missing",
                "clarifications": [
                    Clarification(
                        id=f"product-{index}-category",
                        question=f"What category is '{candidate.title_text}'?",
                        blocking=True,
                        source_quote=candidate.source_quote,
                        target_path=f"/products/{index}/category_hint",
                        options=sorted(CATEGORY),
                    )
                ],
            }
        ), None, candidate.title_text

    title_normalized = normalize_product_title(candidate.title_text)
    conflict = await ProductRepository(session).find_dedupe_conflict(
        tenant_id=tenant_id,
        destination_id=destination.id,
        category=candidate.category_hint,
        title_normalized=title_normalized,
        supplier_id=supplier_id,
    )
    if conflict is not None:
        if entry.action == "create":
            override = action_overrides.get(f"product-{index}-dedupe")
            if override == "update_existing":
                return entry.model_copy(update={"action": "update", "matched_id": conflict.id, "evidence": "operator confirmed: update the existing product", "clarifications": []}), conflict.id, candidate.title_text
            if override == "create_new_anyway":
                return entry.model_copy(update={"action": "create", "matched_id": None, "evidence": "operator confirmed: create a new product despite the title match", "clarifications": []}), None, candidate.title_text
            return entry.model_copy(
                update={
                    "action": "needs_input",
                    "matched_id": conflict.id,
                    "evidence": f"dedupe key already matches existing product '{conflict.id}'",
                    "clarifications": [
                        Clarification(
                            id=f"product-{index}-dedupe",
                            question=f"'{candidate.title_text}' looks like the existing product '{conflict.title}'. Update it instead of creating a new one?",
                            blocking=True,
                            source_quote=candidate.source_quote,
                            target_path=f"/products/{index}",
                            options=["update_existing", "create_new_anyway"],
                        )
                    ],
                }
            ), conflict.id, candidate.title_text
        if entry.action == "update" and entry.matched_id != conflict.id:
            return entry.model_copy(update={"action": "needs_input", "matched_id": conflict.id, "evidence": "matched_id does not match the real dedupe result"}), conflict.id, candidate.title_text
        return entry, conflict.id, candidate.title_text

    if entry.action in ("update", "skip_duplicate"):
        return entry.model_copy(update={"action": "needs_input", "matched_id": None, "evidence": "no existing product found for update/skip_duplicate"}), None, candidate.title_text

    return entry, None, candidate.title_text


async def _verify_rate_entry(
    session: AsyncSession,
    tenant_id: str,
    payload: CatalogIngestPayload,
    parsed: dict[str, Any],
    entry: ResolutionEntry,
    allowlist: AllowlistRecorder,
    product_ids_by_title: dict[str, str],
    action_overrides: dict[str, str],
) -> ResolutionEntry:
    index = _index_from_ref(entry.entity_ref, "rate_groups")
    if index is None or index >= len(payload.rate_groups):
        return entry.model_copy(update={"action": "needs_input", "evidence": "entity_ref does not point to a real rate_group candidate"})
    rate_group = payload.rate_groups[index]
    rg_parsed = (parsed.get("rate_groups") or [{}] * (index + 1))[index] if index < len(parsed.get("rate_groups", [])) else {}
    validity = rg_parsed.get("validity") or {}

    if validity.get("ambiguous"):
        return entry.model_copy(
            update={
                "action": "needs_input",
                "evidence": "validity_text is ambiguous",
                "clarifications": [
                    Clarification(
                        id=f"rate-{index}-validity",
                        question=f"'{rate_group.validity_text}' — what is the exact validity window (with year)?",
                        blocking=True,
                        source_quote=rate_group.source_quote,
                        target_path=f"/rate_groups/{index}/validity_text",
                    )
                ],
            }
        )

    if validity.get("kind") == "season_window":
        return entry.model_copy(
            update={
                "action": "needs_input",
                "evidence": "recurring season window has no year to anchor a concrete rate validity",
                "clarifications": [
                    Clarification(
                        id=f"rate-{index}-year",
                        question=f"'{rate_group.validity_text}' has no year — which year does this season start?",
                        blocking=True,
                        source_quote=rate_group.source_quote,
                        target_path=f"/rate_groups/{index}/validity_text",
                    )
                ],
            }
        )

    product_id = product_ids_by_title.get(rate_group.product_title_text)
    if product_id is None:
        # Product doesn't exist yet in this batch's plan (fresh create) — nothing to overlap-check.
        return entry

    if entry.matched_id and not allowlist.contains(entry.matched_id):
        entry = entry.model_copy(update={"matched_id": None, "action": "needs_input", "evidence": "matched_id was not seen via a tool call this run"})

    new_from = date.fromisoformat(validity["date_from"]) if validity.get("date_from") else None
    new_to = date.fromisoformat(validity["date_to"]) if validity.get("date_to") else None
    if new_from is None or new_to is None:
        return entry

    active_rates = await RateRepository(session).list_active_for_product(product_id, tenant_id=tenant_id)
    overlapping = [r for r in active_rates if _windows_overlap(new_from, new_to, r.valid_from, r.valid_to)]

    if overlapping and entry.action not in ("supersede_rate", "skip_duplicate", "needs_input"):
        override = action_overrides.get(f"rate-{index}-overlap")
        if override == "supersede":
            return entry.model_copy(update={"action": "supersede_rate", "matched_id": product_id, "evidence": "operator confirmed: supersede the overlapping active rate", "clarifications": []})
        if override == "different_category":
            return entry.model_copy(update={"action": entry.action, "evidence": "operator confirmed: different room/category, overlap is expected", "clarifications": []})
        return entry.model_copy(
            update={
                "action": "needs_input",
                "evidence": f"validity overlaps {len(overlapping)} active rate(s) — code re-verified, proposal was '{entry.action}'",
                "clarifications": [
                    Clarification(
                        id=f"rate-{index}-overlap",
                        question=f"'{rate_group.validity_text}' overlaps active rate '{overlapping[0].season_name or overlapping[0].id}'. Supersede it, or is this a different room/category?",
                        blocking=True,
                        source_quote=rate_group.source_quote,
                        target_path=f"/rate_groups/{index}",
                        options=["supersede", "different_category"],
                    )
                ],
            }
        )
    if not overlapping and entry.action == "supersede_rate":
        return entry.model_copy(update={"action": "needs_input", "evidence": "proposed supersede_rate but no active rate actually overlaps this validity window"})
    return entry


async def verify_plan(
    session: AsyncSession,
    tenant_id: str,
    payload: CatalogIngestPayload,
    parsed: dict[str, Any],
    plan: ResolutionPlan,
    allowlist: AllowlistRecorder,
    action_overrides: dict[str, str] | None = None,
) -> list[ResolutionEntry]:
    """Deterministically re-verify every proposed ``ResolutionEntry`` (15.8 chốt #5).

    ``action_overrides`` carries operator answers to whole-entity Clarifications (e.g.
    "update_existing" for a supplier-dedupe question) keyed by clarification id — these are
    NOT applied as payload text edits (they'd corrupt the candidate), they steer the action.
    """
    overrides = action_overrides or {}
    verified: list[ResolutionEntry] = []
    supplier_id: str | None = None
    product_ids_by_title: dict[str, str] = {}

    supplier_entries = [e for e in plan.entries if e.entity_type == "supplier"]
    for entry in supplier_entries:
        verified_entry, supplier_id = await _verify_supplier_entry(session, tenant_id, payload, entry, allowlist, overrides)
        verified.append(verified_entry)

    for entry in [e for e in plan.entries if e.entity_type == "product"]:
        verified_entry, product_id, title = await _verify_product_entry(session, tenant_id, payload, entry, allowlist, supplier_id, overrides)
        if product_id and title:
            product_ids_by_title[title] = product_id
        verified.append(verified_entry)

    for entry in [e for e in plan.entries if e.entity_type == "rate"]:
        verified_entry = await _verify_rate_entry(session, tenant_id, payload, parsed, entry, allowlist, product_ids_by_title, overrides)
        verified.append(verified_entry)

    return verified


def _collect_blocking_clarifications(entries: list[ResolutionEntry]) -> list[Clarification]:
    return [c for entry in entries for c in entry.clarifications if c.blocking]


def _status_from_entries(entries: list[ResolutionEntry], payload: CatalogIngestPayload) -> str:
    if payload.unresolved:
        return "needs_clarification"
    if any(e.action == "needs_input" for e in entries):
        return "needs_clarification"
    return "ready"


async def resolve_round(
    session: AsyncSession,
    *,
    batch: IngestionBatch,
    payload: CatalogIngestPayload,
    parsed: dict[str, Any],
    round_number: int,
    actor: ActorRef,
    tenant_id: str = DEFAULT_TENANT_ID,
    action_overrides: dict[str, str] | None = None,
) -> tuple[list[ResolutionEntry], list[Clarification]]:
    """Run one resolver round on ``payload`` and return (verified_entries, blocking_clarifications)."""
    if payload.covers_multiple_suppliers:
        return [], [
            Clarification(
                id="multi-supplier",
                question="This paste appears to describe more than one supplier — please split it into separate pastes.",
                blocking=True,
                target_path="/covers_multiple_suppliers",
            )
        ]

    plan, allowlist, budget = await _run_resolver(session, tenant_id, payload)
    verified = await verify_plan(session, tenant_id, payload, parsed, plan, allowlist, action_overrides)
    blocking = _collect_blocking_clarifications(verified)

    await record_run(
        session,
        agent_name=AGENT_NAME,
        anchor_type="ingestion_batch",
        anchor_id=batch.id,
        status="succeeded" if not blocking else "partial",
        # keyed by batch_revision (pre-write, monotonically increasing), not round_number —
        # round_number alone collides because run_first_round's initial call and the first
        # answer_clarifications call both compute round 1 (the conversation is still empty
        # going into either), but batch_revision is guaranteed distinct between the two.
        idempotency_key=f"{batch.idempotency_key}:rev{batch.batch_revision}",
        input_ref={"round": round_number, "entities": len(plan.entries)},
        output={"actions": [e.action for e in verified], "blocking_clarifications": len(blocking)},
        stats=budget.stats(),
        actor=actor,
        tenant_id=tenant_id,
    )
    return verified, blocking


async def run_first_round(
    session: AsyncSession,
    *,
    batch: IngestionBatch,
    payload: CatalogIngestPayload,
    parsed: dict[str, Any],
    actor: ActorRef,
    tenant_id: str = DEFAULT_TENANT_ID,
) -> IngestionBatch:
    """Round 1, called synchronously as part of batch creation (15.8 §1.7 Create batch)."""
    repository = IngestionRepository(session)
    unresolved_clarifications = [
        Clarification(
            id=f"unresolved-{i}",
            question=item.description,
            blocking=True,
            source_quote=item.source_quote,
            target_path=item.target_path or "/unresolved",
        )
        for i, item in enumerate(payload.unresolved)
    ]
    if not payload.rate_groups and not payload.products:
        # Nothing resolvable yet (e.g. everything ambiguous at extraction) — skip calling the
        # resolver on an empty payload.
        verified, resolver_blocking = [], []
    else:
        verified, resolver_blocking = await resolve_round(session, batch=batch, payload=payload, parsed=parsed, round_number=1, actor=actor, tenant_id=tenant_id)
    blocking = [*unresolved_clarifications, *resolver_blocking]

    status = "needs_clarification" if (blocking or payload.unresolved) else _status_from_entries(verified, payload)
    return await repository.update_guarded(
        batch,
        expected_revision=batch.batch_revision,
        values={
            "status": status,
            "resolution_json": {
                "entries": [e.model_dump(mode="json") for e in verified],
                "clarifications": [c.model_dump(mode="json") for c in blocking],
            },
            "updated_by": actor.serialize(),
        },
    )


async def answer_clarifications(
    session: AsyncSession,
    *,
    batch: IngestionBatch,
    answers: dict[str, Any],
    actor: ActorRef,
    expected_revision: int,
    tenant_id: str = DEFAULT_TENANT_ID,
) -> IngestionBatch:
    """Apply operator answers at their ``target_path``, re-parse locally, run the next bounded
    resolver round (max 2), and update the batch (15.8 §1.7 Answer)."""
    if batch.status in _TERMINAL_STATUSES:
        raise BatchNotAnswerableError(batch.id, batch.status)

    conversation = list(batch.conversation_json or [])
    round_number = len(conversation) + 1
    if round_number > MAX_QA_ROUNDS:
        raise TooManyClarificationRoundsError()

    stored = batch.payload_json or {}
    payload_dict = copy.deepcopy(stored.get("payload", {}))
    resolution = batch.resolution_json or {}
    outstanding = resolution.get("clarifications", [])

    applied: dict[str, Any] = {}
    edits = copy.deepcopy(batch.operator_edits_json or {})
    action_overrides: dict[str, str] = {}
    for clarification in outstanding:
        cid = clarification["id"]
        if cid not in answers:
            continue
        answer = answers[cid]
        target_path = clarification["target_path"]
        applied[cid] = answer
        if target_path in ("/covers_multiple_suppliers", "/unresolved"):
            continue
        if target_path.endswith("_text"):
            # Leaf text field — overwrite the candidate text and let it re-parse locally.
            _apply_pointer(payload_dict, target_path, answer)
            edits[target_path] = answer
        else:
            # Whole-entity decision (dedupe / overlap) — steers the action, never overwrites payload text.
            action_overrides[cid] = str(answer)

    effective_payload = CatalogIngestPayload.model_validate(payload_dict)
    # Answers can resolve what made an item "unresolved" — re-parse from scratch and let
    # parse_payload rebuild `unresolved[]` deterministically rather than trusting stale flags.
    effective_payload = effective_payload.model_copy(update={"unresolved": []})
    reparsed_payload, parsed = parse_payload(effective_payload)

    verified, resolver_blocking = await resolve_round(
        session,
        batch=batch,
        payload=reparsed_payload,
        parsed=parsed,
        round_number=round_number,
        actor=actor,
        tenant_id=tenant_id,
        action_overrides=action_overrides,
    )
    unresolved_clarifications = [
        Clarification(
            id=f"unresolved-{i}",
            question=item.description,
            blocking=True,
            source_quote=item.source_quote,
            target_path=item.target_path or "/unresolved",
        )
        for i, item in enumerate(reparsed_payload.unresolved)
    ]
    final_round = round_number >= MAX_QA_ROUNDS
    if final_round:
        # Trần hết (2 rounds used) — stop asking. Resolver-raised clarifications (dedupe/
        # overlap) aren't in unresolved[] yet, so fold them in now; parse-ambiguous items are
        # already there.
        for clarification in resolver_blocking:
            reparsed_payload.unresolved.append(
                UnresolvedItem(description=clarification.question, source_quote=clarification.source_quote, reason="unresolved after 2 clarification rounds")
            )
        blocking = []
    else:
        blocking = [*unresolved_clarifications, *resolver_blocking]

    status = "needs_clarification" if (blocking or reparsed_payload.unresolved) else _status_from_entries(verified, reparsed_payload)

    conversation.append(
        {
            "round": round_number,
            "questions": [c["id"] for c in outstanding],
            "answers": applied,
            "answered_by": actor.serialize(),
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )

    repository = IngestionRepository(session)
    return await repository.update_guarded(
        batch,
        expected_revision=expected_revision,
        values={
            "status": status,
            "payload_json": {"payload": reparsed_payload.model_dump(mode="json"), "parsed": parsed},
            "resolution_json": {
                "entries": [e.model_dump(mode="json") for e in verified],
                "clarifications": [c.model_dump(mode="json") for c in blocking],
            },
            "conversation_json": conversation,
            "operator_edits_json": edits,
            "updated_by": actor.serialize(),
        },
    )
