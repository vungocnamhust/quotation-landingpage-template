# Sprint 01 — Domain Core and Schema

## Sprint objective & deliverables

Establish immutable, deterministic domain primitives independently of HTTP/UI:

- permanent new-model `sourceFactId` and hotel fact identity;
- Facts-vs-editorial document ownership;
- action-plan persistence based on Alembic 34;
- pure input projection/fingerprint and semantic reconciliation rules.

This sprint must not call an LLM, render Impact Center, or expose new APIs.

## Targeted file manifest

- **[MODIFY]** `quote_document.py`
- **[MODIFY]** `services/skeleton_builder.py`
- **[MODIFY]** `services/facts_contract.py`
- **[MODIFY]** `db/models/quotation.py`
- **[NEW]** `core/rules/content_action_reconciler.py`
- **[NEW]** `core/rules/semantic_identity.py`
- **[NEW]** `alembic/versions/20260824_35_actionable_content_plan.py`
- **[MODIFY]** `tests/test_quote_document_flow.py`
- **[MODIFY]** `tests/test_atomic_content_ownership.py`
- **[NEW]** `tests/test_content_action_reconciler.py`

## Typed interfaces & schemas

```python
ContentAutomationPolicy = Literal["manual", "auto", "bypass"]
ActionState = Literal["pending", "draft_created", "applied", "skipped", "failed"]
SemanticOperation = Literal["added", "removed", "reordered", "semantic_replaced", "changed"]

@dataclass(frozen=True)
class SemanticEntityChange:
    entity_key: str
    operation: SemanticOperation
    old_summary: dict[str, Any] | None
    new_summary: dict[str, Any] | None
    carry_forward_allowed: bool

@dataclass(frozen=True)
class ContentInputProjection:
    scope: str
    entity_key: str
    facts: dict[str, Any]
    facts_hash: str
```

Persist a plan header and action rows. The exact table names may be `quotation_content_action_plans` and `quotation_content_actions`; do not overload the old impact target execution fields.

Required action fields: quotation ID, plan ID, scope, entity key, policy, reason code, input facts hash, predecessor quotation ID, inherited reference status, state, draft ID, applied revision, actor, correlation ID, idempotency key, timestamps. Add unique keys for `(quotation_id, plan_hash)` and `(plan_id, action_key)`.

## Step-by-step task breakdown

1. Add immutable identity helpers.
   - `sourceFactId` is generated only for first new-model creation, then preserved unchanged.
   - Define itinerary semantic signature from destination reference/destination and overnight; date/day number are positional context, not identity.
   - Define hotel identity from stable service-fact ID. Do not use `hotel-{index}` for a new-model identity.

2. Add pure semantic reconciliation.
   - Compare predecessor/current itinerary maps by sourceFactId.
   - Produce added, removed, reordered and semantic-replaced results.
   - Reorder with unchanged signature permits carry-forward; destination/overnight change forbids it.
   - Produce deterministic, human-readable summaries, never raw JSON-only labels.

3. Split document ownership without weakening Facts.
   - Pricing values/options/conditions stay Fact-owned.
   - Add Content-owned pricing editorial fields and make `trip.priceBasis` part of pricing scope.
   - Add hotel editorial introduction separate from factual/default hotel intro; render factual default only when editorial field is empty.
   - Add inclusion/exclusion editorial heading/introduction/context note, while canonical list items remain Facts.
   - Preserve schema compatibility for existing documents through defaults; do not mutate old documents in migration.

4. Extend skeleton projection.
   - Rebuild all Fact-owned values every successor creation.
   - Materialize empty editorial fields/default fallbacks only; never convert an existing Fact string into AI-owned text automatically.
   - Keep MediaDefaultService responsibility outside the skeleton.

5. Add migration 35 from 34.
   - Create action-plan/action tables and indexes.
   - Do not modify legacy quotations or backfill their data.
   - Do not delete migrations 31–34 tables/data. Old new-model impact rows remain readable for compatibility until cutover service is deployed.
   - Add reversible downgrade only for the newly created structures.

## Isolated verification protocol

```bash
PYTHONPATH=. pytest \
  tests/test_quote_document_flow.py \
  tests/test_atomic_content_ownership.py \
  tests/test_content_action_reconciler.py
alembic upgrade head
alembic current
```

Acceptance: Hoi An → Hanoi forbids day carry-forward; Day 6 is added; reorder preserves identity; removal retires identity; schema validation rejects AI candidates targeting Facts paths.
