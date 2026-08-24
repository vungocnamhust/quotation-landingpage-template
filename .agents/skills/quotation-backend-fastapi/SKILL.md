---
name: quotation-backend-fastapi
description: Govern Core Backend (FastAPI, port 8111) work in this repo. Use when adding or changing API endpoints, Pydantic request/response models, services, repositories, business gates, alembic migrations, publication/outbox flows, or when touching main.py or routers/v2/*. Enforces the router->service->repository layering, the frozen V2 HTTP manifest, the V2 error envelope, optimistic revision concurrency, and the outbox boundary.
---

# Quotation Backend (FastAPI) Governor

Entry skill for every Core Backend change. Compose with `fastapi` for framework
idioms and `notification-*` skills when the change touches events or delivery.

## Read First

- `AGENTS.md` sections 2, 3 (cross-subsystem invariants + Python standards).
- `api/dependencies.py` — the only sanctioned place for shared DI aliases.
- `tests/test_v2_api_manifest_contract.py` — the frozen HTTP surface.
- `tests/test_v2_error_envelope.py` — the error contract.
- `core/rules/base.py` — `GateIssue` / `GateResult` / `BusinessGate` protocol.
- The matching `repositories/*_repository.py` before writing any query.

## Ground Truth About This Codebase

- `main.py` is an ~11k-line composition root and helper module. `routers/v2/*`
  intentionally reach back into it via a local `def _get_helpers(): import main`
  to avoid circular imports. Follow that existing pattern; do not invent a
  second helper-injection mechanism, and do not `import main` at module top level.
- New endpoints belong in a `routers/v2/<domain>.py` `APIRouter(prefix=..., tags=[...])`,
  not in `main.py`. Extracting existing endpoints out of `main.py` is welcome, but
  it must be behaviour-neutral: the manifest test must stay green untouched.
- Two Alembic trees exist: `alembic/` (quotation DB) and `notification/alembic/`
  (notification DB). Never cross them, never JOIN across the two databases.

## Workflow

1. Classify the change: `route` | `schema` | `service` | `repository` | `rule/gate` | `migration`.
2. Layer discipline:
   - Router: parse/validate, auth via `Depends`, call service, shape response. No SQL, no business math.
   - Service (`services/`): business logic, derivation, orchestration, outbox writes.
   - Repository (`repositories/`): queries only; raise typed errors from `repositories/errors.py`.
   - Rule (`core/rules/`): pure, deterministic, returns `GateResult`; no I/O, no session.
3. Auth: use the existing aliases (`EditorPrincipalDep`, `EditorOrServicePrincipalDep`,
   `QuoteAdminPrincipalDep`) or `Depends(require_editor)`. Never hand-roll a principal check.
4. Async policy: `async def` only when the body awaits real async I/O (SQLAlchemy async
   session, httpx). Use plain `def` for Jinja2 rendering, file work, and sync SQLAlchemy —
   FastAPI threadpools it.
5. Mutating document endpoints MUST take `baseRevision` and surface
   `DocumentRevisionConflictError` as the 409 `REVISION_CONFLICT` envelope
   (`recovery: "reload"`). Do not silently last-write-win.
6. Errors: shape everything through `main._v2_error_payload`. Codes in use:
   `VALIDATION_FAILED` (422 + `fieldErrors[].path`), `REVIEW_BLOCKED`
   (422 + `recovery: "open-blockers"`), `REVISION_CONFLICT` (409). Adding a new
   code requires updating `tests/test_v2_error_envelope.py` in the same change.
7. Notifications/email/push: write to `outbox_events` via `services/outbox_service.py`.
   Never import `notification.workers` or send directly from a domain service.
8. Adding/removing/rebinding any HTTP operation is a deliberate API change:
   update `EXPECTED_V2_OPERATIONS` in `tests/test_v2_api_manifest_contract.py`
   explicitly and say so in the commit message.

## Pydantic Rules

- Full type hints on every parameter and return (`-> ResponseModel`).
- No `...` (Ellipsis) as the default for a required field; no hand-rolled `RootModel`.
- Declare the return type or `response_model` on every path operation.
- Request models live next to their router (small, endpoint-shaped) or in
  `schemas/v2/` when shared. Facts payloads normalize through
  `services/facts_contract.normalize_legacy_facts_snapshot` before validation —
  legacy snapshots are not directly schema-valid.

## Post-Edit Gate

```bash
PYTHONPATH=. pytest tests/test_v2_api_manifest_contract.py tests/test_v2_error_envelope.py tests/test_domain_rules.py tests/test_business_gates.py
```

Then run the suites matching the touched area (e.g. `tests/test_facts_resolver.py`,
`tests/test_quote_request_service.py`, `tests/test_repositories.py`,
`tests/test_publication_runtime.py`). Report failures; do not declare done on a partial pass.

## Hard Guardrails

- No business logic in routers; no SQL outside repositories; no I/O in `core/rules/`.
- No direct notification dispatch from domain services.
- No cross-database reads between `quotation` and `notification`.
- No new module-level `import main` in a router.
- No incidental HTTP surface change without a manifest-test edit.
