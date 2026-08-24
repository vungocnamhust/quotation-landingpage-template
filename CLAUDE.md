# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md
@notification/AGENTS.md

Monorepo: travel quotation intake → AI-assisted content drafting → multi-mode
luxury brochure publication (desktop / mobile / PDF), plus an independent
notification microservice.

---

## Skill Routing (do this first)

| Working on | Invoke |
| :-- | :-- |
| FastAPI routes, services, repositories, gates, migrations | `quotation-backend-fastapi` (+ `fastapi`) |
| Anything under `quote-generator/` | `quotation-frontend-nextjs` (routes to the display / typography / prefill / reuse governors) |
| Prompts, content budgets, LLM draft generation | `quotation-ai-content-agent` |
| `notification/` events, workers, retries, review | `notification-core`, `notification-fastapi`, `notification-reliability`, `notification-review` |

`.claude/skills/*` are symlinks into `.agents/skills/*` (shared with Codex/Cursor).
Add a new project skill in `.agents/skills/<name>/SKILL.md` and symlink it into
`.claude/skills/` or Claude Code will not see it.

---

## Commands

### Core Backend — FastAPI, port 8111
```bash
uvicorn main:app --reload --port 8111
alembic upgrade head                      # quotation DB migrations
```

Tests (no pytest.ini — `PYTHONPATH=.` is required):
```bash
PYTHONPATH=. pytest                                   # full suite
PYTHONPATH=. pytest tests/test_facts_resolver.py      # one file
PYTHONPATH=. pytest tests/test_domain_rules.py -k party_label -x -q   # one test
```
Contract suites that must stay green on any API change:
```bash
PYTHONPATH=. pytest tests/test_v2_api_manifest_contract.py tests/test_v2_error_envelope.py \
  tests/test_domain_rules.py tests/test_business_gates.py tests/test_ssot_integrity.py
```

### Frontend — quote-generator, Next.js 16 / React 19, port 8115
```bash
cd quote-generator
npm run dev
npm run lint     # eslint + typography + typography-contract + display-system + colors + v2-runtime-imports
npm test         # node --test over lib/__tests__/*.test.ts
npm run build
node --test --experimental-strip-types lib/__tests__/tripReconciler.test.ts   # single test file
npm run sync:budgets                                  # re-export content budgets from prompts/v1
```
`npm run lint` is a chain — a green eslint alone is **not** a pass.

### Notification Subsystem — FastAPI, port 8116
```bash
uvicorn notification.main:app --reload --port 8116
python -m notification.workers.delivery_worker
alembic -c notification/alembic.ini upgrade head
PYTHONPATH=. pytest tests/test_notification_api.py tests/test_notification_service.py
curl -s http://localhost:8116/health
```

### Docker
```bash
docker compose -f docker-compose.local.yml up -d postgres migrate app
docker compose -f docker-compose.local.yml up -d notification-service notification-worker
docker logs -f quotation-local-notification-service-1
```

---

## Architecture: the parts you cannot infer from one file

### `main.py` is an 11k-line composition root
It owns app wiring, the legacy V1 surface, and shared helpers
(`_v2_error_payload`, `require_owned_quotation`, `_get_db_session_factory`,
`_resolve_v2_facts`, `normalize_legacy_facts_snapshot`, …).
`routers/v2/*` deliberately reach back into it with a function-local
`def _get_helpers(): import main` to dodge circular imports. **Follow that
pattern**; never add a module-level `import main` to a router. New endpoints go
in `routers/v2/<domain>.py`, not in `main.py`.

### Backend layering
`routers/` (parse, auth, respond) → `services/` (business logic, orchestration,
outbox) → `repositories/` (queries only, typed errors in `repositories/errors.py`)
→ `db/models/`. Pure deterministic domain gates live in `core/rules/` and return
`GateResult`/`GateIssue` (`core/rules/base.py`) — no I/O, no session there.
Shared DI aliases live only in `api/dependencies.py`.

### Two frozen API contracts
- **HTTP surface**: `tests/test_v2_api_manifest_contract.py` pins every V2
  operation. Adding/removing/rebinding a route requires an explicit edit there.
- **Error envelope**: everything goes through `main._v2_error_payload`. Codes:
  `VALIDATION_FAILED` (422, `fieldErrors[].path`), `REVIEW_BLOCKED`
  (422, `recovery: "open-blockers"`), `REVISION_CONFLICT` (409, `recovery: "reload"`).

### Optimistic concurrency everywhere documents are edited
Mutating endpoints take `baseRevision`; `DocumentRevisionConflictError` surfaces
as a 409 the frontend must resolve by reloading. No last-write-wins.

### Event boundary
Domain services never send email/SMS/push and never import `notification.workers`.
They write to `outbox_events` in the same transaction via
`services/outbox_service.py`; `services/outbox_relay.py` forwards to the
notification service. Databases `quotation` and `notification` are isolated —
no cross-schema JOINs, separate Alembic trees (`alembic/`, `notification/alembic/`).

### AI content layer (intentionally simple)
`prompts/v1/*.yaml` → `prompts/loader.py` (`PromptLoader` → `PromptBundle`) →
budget limits from `core/rules/content_budgets.py` → typed `_CopyModel` outputs in
`services/section_content_generator.py` via `pydantic_ai.Agent` →
`llm_client.get_model()` (the only provider construction site; DeepSeek-compatible
with an OpenAI fallback). Prompts are YAML data, never inline strings. Invalid
model output raises `ContentGenerationError` and persists nothing.
`prompts/v1/content_budgets.yaml` is the SSOT for copy lengths and is mirrored to
`quote-generator/config/contentBudgets.json` via `npm run sync:budgets`.

### Frontend: two isolated worlds in one app
- **Display** (`components/display/**`, `app/[locale]/q/[slug]`, `app/pdf`):
  consumes only `viewModel + displayConfig + tokens + theme + viewMode + colorScope`.
  Typography exclusively via `typo-*` from `config/typography.ts`.
- **Staff workspace / content studio** (`app/workspace`, `app/content-studio`,
  `components/quotation-workspace`, `components/staff-workspace`).

Never import across that boundary; `npm run lint:display-system` enforces it.

Domain math lives in the 4-layer reconciler stack, never in an event handler:
`lib/rules/*Reconciler.ts` (pure) ↔ `lib/rules/*Adapter.ts` ↔
`lib/prefillEngine.ts` / hooks ↔ React UI (one call per handler). Active
reconcilers: `trip`, `stays`, `pricing`, `party`, `presentation`, `content`,
`workflow` — each with a matching `lib/__tests__/*.test.ts`. Deriving state with
`useEffect` is a defect here.

Next 16 specifics: interception logic is `quote-generator/proxy.ts` (not
`middleware.ts`); `next.config.ts` rewrites `/api/v1/*` to the backend
(`QUOTATION_INTERNAL_API_URL` → `NEXT_PUBLIC_QUOTATION_API_URL` → `localhost:8111`);
heavy client islands (Leaflet map, TipTap, drawers) use `dynamic(..., { ssr: false })`.

### Legacy vs V2
Root-level `generate_*.py`, `quote_document.py`, `quote_generation.py`,
`templates/` + `published/` are the legacy Jinja2 static-HTML path, still reachable
via `/api/v2/legacy-*`. New work targets the V2 React renderer
(`V2_RENDERER_NAME = "quote-generator"`). `templates/prototype_itinerary_imagery*.html`
are the parity reference for brochure fidelity, not live code.

---

## Repo conventions worth knowing

- Python: 4 spaces, full type hints, `Annotated[..., Depends(...)]`,
  `async def` only for genuinely async I/O.
- Facts payloads pass through `services/facts_contract.normalize_legacy_facts_snapshot`
  before Pydantic validation — raw legacy snapshots are not schema-valid.
- Tests named `test_*_contract.py` are frozen contracts; treat a failure there as
  "your change altered a public shape", not "fix the test".
- Guidance is duplicated for other agents in `AGENTS.md`, `quote-generator/AGENTS.md`,
  `notification/AGENTS.md`, and `.cursorrules` — update them together.
