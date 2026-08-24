# Sprint 03 — API and Transactional Outbox

## Sprint objective & deliverables

Expose thin typed V2 APIs over the new domain services. Enforce authorization, idempotency, optimistic revision conflicts and outbox correctness.

## Targeted file manifest

- **[MODIFY]** `routers/v2/quotation_versions.py`
- **[MODIFY]** `routers/v2/quotation_document.py`
- **[NEW]** `routers/v2/schemas/content_actions.py`
- **[NEW]** `api/dependencies/quotation_version_services.py`
- **[MODIFY]** `repositories/quotation_repository.py`
- **[MODIFY]** `services/outbox_service.py` only if event idempotency support is missing
- **[MODIFY]** `tests/test_v2_api_manifest_contract.py`
- **[NEW]** `tests/test_content_actions_api.py`
- **[MODIFY]** `tests/test_quote_request_revisions.py`

## Typed interfaces & schemas

```python
class CreateQuotationVersionRequest(BaseModel):
    facts: CreateQuoteRequestV1
    baseRevision: int = Field(ge=1)

class ContentActionSelectionRequest(BaseModel):
    planId: str
    actionIds: list[str] = Field(min_length=1)
    baseRevision: int = Field(ge=1)
    writingStyle: Literal["storytelling", "detailed"] = "storytelling"

class ContentActionExecutionResponse(BaseModel):
    planId: str
    state: Literal["draft_created", "applied"]
    draftIds: list[str] = Field(default_factory=list)
    currentRevision: int | None = None
    contentUrl: str

class AcceptChangePlanRequest(BaseModel):
    resolutionNote: str = Field(default="Acknowledged", min_length=1, max_length=1000)
```

Endpoints:

```text
POST /api/v2/quotations/{id}/versions
GET  /api/v2/quotations/{id}/content-actions
POST /api/v2/quotations/{id}/content-actions/accept
POST /api/v2/quotations/{id}/content-actions/generate-drafts
POST /api/v2/quotations/{id}/content-actions/generate-and-apply
```

## Step-by-step task breakdown

1. Move all version creation orchestration out of `quotation_versions.py`.
   - Router validates typed payload, resolves `Annotated` dependencies, maps domain exceptions to typed 404/409/422/503 responses.
   - Do not query repositories from path operations.

2. Replace impact HTTP contract with Action Plan contract.
   - `GET /impacts` may remain a temporary typed alias during migration, but frontend moves to `/content-actions`.
   - Accept is acknowledgment only; it does not select targets, call AI, create draft or mutate the document.

3. Add execution endpoints.
   - `generate-drafts` accepts only selected `auto` actions.
   - `generate-and-apply` accepts only selected `bypass` actions and requires `Idempotency-Key`.
   - Both require correlation header and return retry-safe typed error bodies.

4. Retire unsafe endpoints and coupling.
   - `POST /impacts/generate-selected` returns typed 410/409 with migration guidance and no mutation.
   - Remove “applying draft resolves impact” side effect.
   - Do not invoke `content-drafts/apply-all` from any action endpoint.

5. Emit transactional outbox events in the same database transaction as state change.
   - `quotation.version.created`
   - `quotation.content_plan.created`
   - `quotation.content_plan.accepted`
   - `quotation.content_action.drafts_created`
   - `quotation.content_action.applied`
   - Event payload contains family/version/provenance, plan/action IDs, actor, correlation ID, idempotency key, draft IDs or document revision.

6. Preserve contracts.
   - Legacy quotations return the existing compatibility behavior.
   - Existing content draft create/apply APIs stay valid for normal Content Studio usage.
   - Update OpenAPI/manifest tests before wiring frontend.

## Isolated verification protocol

```bash
PYTHONPATH=. pytest \
  tests/test_content_actions_api.py \
  tests/test_v2_api_manifest_contract.py \
  tests/test_quote_request_revisions.py
```

Acceptance: authorization and revision-conflict paths return structured errors; repeated idempotency key returns same result; a failed bypass has no document revision/outbox applied event.
