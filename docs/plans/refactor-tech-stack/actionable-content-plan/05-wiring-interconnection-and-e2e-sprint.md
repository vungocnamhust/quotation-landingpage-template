# Sprint 05 — Wiring, Interconnection and E2E Acceptance

## Sprint objective & deliverables

Prove the complete production-shaped workflow from immutable predecessor through successor, Actionable Content Plan, draft/bypass execution, revision conflicts, outbox and publication. This sprint is not complete with unit tests alone.

## Targeted file manifest

- **[MODIFY]** `scripts/test_v2_brochure_workflow.py`
- **[NEW]** `scripts/test_actionable_content_plan_e2e.py`
- **[MODIFY]** browser E2E suite location used by the repository
- **[MODIFY]** `tests/test_v2_api_manifest_contract.py`
- **[MODIFY]** `tests/test_quotation_impact_analysis.py` or renamed change-plan suite
- **[NEW]** Compose report artifact under the test output directory only
- **[MODIFY]** deployment/runbook documentation if command names or required migration baseline change

## Typed interfaces & schemas

The E2E report is JSON and includes:

```json
{
  "quotationFamilyId": "…",
  "predecessorId": "…",
  "successorId": "…",
  "planId": "…",
  "selectedAutoActionIds": ["…"],
  "selectedBypassActionIds": ["…"],
  "predecessorDocumentHash": "…",
  "successorDocumentHashes": {"before": "…", "afterBypass": "…"},
  "outboxEventIds": ["…"],
  "requestLogAssertions": []
}
```

## Step-by-step task breakdown

1. Build deterministic API fixture flow.
   - Create a new-model predecessor with Facts, media defaults and reviewed content.
   - Capture predecessor Facts/document hash and current revision.
   - Edit Day 5 Hoi An → Hanoi and add Day 6, then create successor.

2. Assert successor safety before AI.
   - Predecessor remains immutable.
   - Day 1–4 prose hashes remain stable if semantic identity remains stable.
   - Day 5 Hoi An prose/media is not present on Hanoi.
   - Day 6 has no inherited narrative.
   - Media defaults satisfy creation contract independently of content actions.

3. Exercise Actionable Impact Center.
   - Fetch plan and assert human-readable Day 5 replacement/Day 6 addition plus pricing/hotel/inclusion policies where fixture changes them.
   - Accept plan: assert zero provider calls, zero drafts, zero document write.
   - Generate selected auto actions: assert drafts only, no document revision.
   - Apply an explicitly reviewed draft with normal optimistic revision protection.
   - Execute selected bypass actions: assert exactly one document revision and only whitelisted content paths changed.

4. Assert negative paths.
   - stale revision returns 409 and changes nothing;
   - provider timeout returns retryable error and changes nothing;
   - invalid candidate returns 422 and changes nothing;
   - duplicate idempotency key replays result without duplicate draft/document/outbox event;
   - legacy quotation cannot enter action-plan path;
   - no request reaches `batch-generate`, `apply-all`, Fast Track or retired impact execution endpoint.

5. Browser acceptance.
   - Open Impact Center popup, inspect semantic change wording, select actions and confirm bypass dialog.
   - Verify Review Facts and Open Content URLs/deep links and that neither causes an AI request.
   - Verify Content Studio shows the right successor Facts and selected Day scope.
   - Verify no post-plan badge/banner leaks into Design/Review.

6. Publication/PDF/outbox acceptance.
   - Complete required content review where publish gate requires it.
   - Produce public brochure/PDF from successor and verify expected revision/hash.
   - Verify outbox rows/events contain family/version, action IDs, correlation and idempotency metadata.
   - Confirm a legacy quotation remains renderable and unchanged.

## Isolated verification protocol

```bash
PYTHONPATH=. pytest \
  tests/test_quotation_impact_analysis.py \
  tests/test_quote_request_revisions.py \
  tests/test_v2_api_manifest_contract.py \
  tests/test_content_actions_api.py

cd quote-generator
npm run lint
npm run lint:typography
npm run lint:display-system
npm run build

cd ..
PYTHONPATH=. python scripts/test_actionable_content_plan_e2e.py
PYTHONPATH=. python scripts/test_v2_brochure_workflow.py
```

## Release gate

Release only when rebuilt-source Compose images, browser proof, API evidence, PDF/publication output and outbox evidence all pass. Existing-image tests or static lint results do not prove the cross-service flow.
