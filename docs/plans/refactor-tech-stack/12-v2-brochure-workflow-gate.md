# V2 brochure workflow integration gate

Compose acceptance uses PostgreSQL, MinIO, Alembic, FastAPI, worker and Next
services for every tier. The cost is controlled by choosing a tier, not by
replacing those boundaries with mocks. The disposable Compose stack remains
running until an explicit `down`.

```bash
# Fast API/database contract. No LLM, publication, browser or PDF.
scripts/run_compose_e2e.sh smoke

# Smoke plus one real Hero generation, typed PATCH/Apply/reload and expected 409.
scripts/run_compose_e2e.sh workflow

# Only when preparing a release: all required content scopes and worker publish.
scripts/run_compose_e2e.sh full

# Browser, public SSR, real PDF parse and 1440/980/mobile screenshots.
# Reuses the release above; it never generates content itself.
scripts/run_compose_e2e.sh browser-pdf artifacts/e2e/full-report.json

# Explicit cleanup only when the disposable database is no longer needed.
scripts/run_compose_e2e.sh down
```

Each tier writes a small JSON report under `artifacts/e2e`. The full report is
the handoff to `browser-pdf`; it contains quotation/revision/release IDs but
never provider credentials or one-shot instruction text. Any unexpected HTTP
status, migration error, invalid candidate, worker error, screenshot failure
or PDF failure stops that tier immediately.

Images use pinned local `:dev` tags. Builds are opt-in and targeted, for
example `scripts/run_compose_e2e.sh workflow --build app`; repeat `--build`
for each service that actually changed. Do not use whole-stack
`--force-recreate`. A Next change requires `--build quote-generator --build
nginx`; an API-only change requires only `--build app --build migrate` when
the migration image also needs the source change.

The app must have valid LLM credentials for `workflow` and `full`; a fallback
candidate is a failure. Credentials stay in the FastAPI Compose service. The
runner sends editor APIs with `X-DMC-Email`; release verification alone uses
`X-Quote-Service-Token`.
