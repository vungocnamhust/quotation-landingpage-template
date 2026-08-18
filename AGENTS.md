# Repository Guidelines

## Project Structure & Module Organization
- `main.py` is the FastAPI entrypoint for quotation APIs and publishing flows.
- Core backend modules live in `core/`, `services/`, `repositories/`, `routers/`, `db/`, and `alembic/`.
- Public brochure templates and generated artifacts live in `templates/`, `assets/`, and `published/`.
- Python tests live in `tests/` and usually mirror the backend feature they cover.
- The Next.js display app lives in `quote-generator/` with App Router code in `quote-generator/app/`, UI in `quote-generator/components/`, display contracts in `quote-generator/display/`, and semantic tokens in `quote-generator/config/`.

## Build, Test, and Development Commands
- Backend install: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Backend dev server: `uvicorn main:app --reload --port 8111`
- Backend tests: `python -m pytest tests`
- Frontend install: `cd quote-generator && npm install`
- Frontend dev server: `cd quote-generator && npm run dev` (runs on `http://localhost:8115`)
- Frontend quality gates: `cd quote-generator && npm run lint` and `npm run build`

## Coding Style & Naming Conventions
- Use 4 spaces in Python and follow type-hinted, small-function FastAPI patterns.
- Use TypeScript in `quote-generator/`; keep components server-first unless interaction is required.
- Prefer direct imports over barrels in the display system.
- Typography must come from `quote-generator/config/typography.ts` via `typo-*` classes; do not hardcode `text-*`, `tracking-*`, or `font-*` in brochure UI.
- Prefill & Data Derivation Engine: Follow the 3-Layered Architecture (`factsTypes.ts` schema -> `prefillRules.ts` pure business rules -> `prefillEngine.ts` single-pass facade updaters). Call atomic facade updaters in React components (`setFacts(current => updateCustomerName(current, value))`) rather than executing multi-step inline state patches. Use `getDefaultMealsForLang(lang)` for localized default meals (EN, VI, AR).
- File naming: React components in `PascalCase.tsx`, utilities in `camelCase.ts`, tests as `test_<feature>.py`.

## Testing Guidelines
- Backend tests use `pytest`/`unittest` style under `tests/`.
- Add regression tests whenever changing quotation mapping, publishing, PDF sync, or migration behavior.
- Frontend changes must pass `npm run lint`, `npm run lint:typography`, `npm run lint:display-system`, and `npm run build`.
- For brochure rendering changes, verify with a real quotation or prototype-backed route, not only isolated mocks.

## Commit & Pull Request Guidelines
- Follow the repo’s existing imperative style: `Publish quotation ...`, `Update PDF view ...`, `Upload brochure asset ...`.
- Keep commits scoped to one concern; mention quotation ID or version when changing published artifacts.
- PRs should include: summary, impacted paths, test evidence, and screenshots for UI/display changes.

## Security & Configuration Tips
- Keep secrets in local `.env` files; never commit credentials or private customer data.
- Treat `published/` as user-facing output: only edit or commit generated quotation artifacts intentionally.

## Quote Generator Skills
- Prefer the repo-local skills in `./.agents/skills/` whenever a task touches `quote-generator/`.
- Use `react-component-reuse-governor` when creating new inputs, selectors, pickers, refactoring duplicated UI logic, or standardizing reusable React components across forms and workspaces.
- Use `quote-generator-display-governor` first for display-system changes.
- Use `quote-generator-prefill-governor` for prefill, default value assignment, duration/date calculations, party labels, or hotel/pricing data derivations.
- Use `quote-generator-typography-ssot` for any typography, button text, nav text, CTA, or print text changes.
- Use `quote-generator-section-builder` when adding or refactoring sections, layouts, or section-facing components.
- Use `quote-generator-parity-review` for prototype drift, parity audits, and responsive/PDF comparison work.
