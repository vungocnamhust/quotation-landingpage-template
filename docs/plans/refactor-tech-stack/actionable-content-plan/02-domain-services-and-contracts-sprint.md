# Sprint 02 — Domain Services and Content Contracts

## Sprint objective & deliverables

Build independently testable services that create a successor, compute an actionable plan, carry content safely, construct prompt context, and execute draft/bypass actions. No router orchestration is permitted.

## Targeted file manifest

- **[NEW]** `services/quotation_version_factory.py`
- **[NEW]** `services/semantic_content_carry_forward_service.py`
- **[NEW]** `services/quotation_change_plan_service.py`
- **[NEW]** `services/content_action_execution_service.py`
- **[NEW]** `services/inherited_content_context_service.py`
- **[MODIFY]** `services/content_registry.py`
- **[MODIFY]** `services/content_draft_service.py`
- **[MODIFY]** `services/section_content_generator.py`
- **[MODIFY]** `services/skeleton_builder.py`
- **[MODIFY]** `repositories/quotation_repository.py`
- **[DELETE]** `services/quotation_impact_analysis.py` after compatibility adapter removal
- **[NEW]** `tests/test_quotation_version_factory.py`
- **[NEW]** `tests/test_content_action_execution_service.py`
- **[MODIFY]** `tests/test_quotation_impact_analysis.py` to test change-plan behavior or rename it

## Typed interfaces & schemas

```python
@dataclass(frozen=True)
class ContentScopeSpec:
    scope: str
    owner: Literal["content", "fact"]
    automation_policy: ContentAutomationPolicy
    canonical_targets: tuple[str, ...]
    authoritative_fact_paths: tuple[str, ...]
    build_prompt_context: Callable[[CreateQuoteRequestV1, str], dict[str, Any]]
    entity_binding: Literal["quotation", "itinerary_day", "hotel"]

@dataclass(frozen=True)
class CreateSuccessorCommand:
    predecessor_id: str
    facts: CreateQuoteRequestV1
    base_document_revision: int
    actor_profile_id: str | None
    correlation_id: str

@dataclass(frozen=True)
class ExecuteContentActionsCommand:
    quotation_id: str
    plan_id: str
    action_ids: tuple[str, ...]
    expected_document_revision: int
    writing_style: Literal["storytelling", "detailed"]
    idempotency_key: str
    correlation_id: str
```

## Step-by-step task breakdown

1. Reduce registry duplication.
   - Replace `fact_allowlist`/`fact_used`/manually-built batch snapshots with one scope-owned prompt context builder.
   - Keep no impact-specific deep links, role or treatment fields in the registry.
   - Define scope policy: itinerary/hero/overview/route/hotel editorial/pricing editorial normally `auto`; inclusion legal list `manual`; bypass only explicit editorial whitelist.

2. Implement `SemanticContentCarryForwardService`.
   - Carry only eligible content-owned document paths.
   - Match day prose by sourceFactId plus semantic signature.
   - Preserve unrelated presentation overrides but do not treat Design as an action target.
   - Never carry Hanoi-incompatible Hoi An prose/media override.

3. Implement `QuotationVersionFactory`.
   - Own one transaction: canonicalize Facts, validate, resolve, build skeleton, call MediaDefaultService, carry safe Content, persist successor/Facts/document/revision, create plan, emit outbox.
   - Keep template rejection until a real template renderer registry exists.
   - Do not import `main.py`; dependencies are injected at composition root.

4. Implement `QuotationChangePlanService`.
   - Consume semantic changes and scope input projections.
   - Create action rows only for Content scopes whose input projection changed or whose entity was added/replaced.
   - Add manual informational actions for commercial/legal copy; never create Design action rows.
   - Record preserved and retired entities as audit summaries, not AI tasks.

5. Implement inherited context contract.
   - For a valid unchanged/reordered day, send predecessor prose as `eligible` reference.
   - For added/replaced/removed day, send no prose (`unavailable`/`retired`).
   - Global scopes receive only a safe style/reference policy; when route, party, brand or language changes, do not make old factual prose visible or authoritative.
   - Store reference status/hash in draft metadata.

6. Implement execution service.
   - `auto`: obtain/validate all selected candidates, then persist drafts atomically; no document write.
   - `bypass`: generate outside transaction, validate all candidates, then in one transaction lock/check revision, merge only whitelisted paths, append one document revision and mark actions applied.
   - A provider error, candidate validation error, authorization error or revision conflict produces zero partial document updates.
   - Fix the undefined `day` variable and sourceFactId mapping in batch generation while replacing batch snapshot duplication.

## Isolated verification protocol

```bash
PYTHONPATH=. pytest \
  tests/test_quotation_version_factory.py \
  tests/test_content_action_execution_service.py \
  tests/test_quote_request_revisions.py \
  tests/test_quotation_impact_analysis.py
```

Acceptance: all tests run without FastAPI test client; no service imports `main.py`; predecessor document remains byte-identical; bypass failure leaves current revision unchanged.
