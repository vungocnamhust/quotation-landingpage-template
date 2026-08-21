# Refactor Tech Stack Plan

> **Status update — 2026-08-06.** This folder is now an implementation
> record as well as the target plan. The one-VPS modular monolith decision is
> unchanged: Postgres is canonical editor state, R2 is canonical binary and
> publication-artifact storage. Do not read the early Phase A/B/D/E/F checkboxes
> as proof that work is absent; see `07-implementation-checklist.md` and
> `12-v2-brochure-workflow-gate.md` for verified work versus deployment gates.

Tai lieu nay mo ta chi tiet ke hoach refactor `Create quotation V2` sang mo hinh:

- `1 VPS`
- `Docker Compose`
- `FastAPI + Postgres`
- `Cloudflare R2`
- `Editor autosave vao Postgres`
- `Media upload/select/sync qua R2`

Muc tieu la de team co the doc theo thu tu va implement truc tiep, khong can tu suy dien them ve kien truc tong the.

## Thu tu doc va implement

1. [01-target-architecture.md](/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/docs/plans/refactor-tech-stack/01-target-architecture.md)
2. [02-postgres-integration.md](/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/docs/plans/refactor-tech-stack/02-postgres-integration.md)
3. [03-r2-media-management.md](/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/docs/plans/refactor-tech-stack/03-r2-media-management.md)
4. [04-api-and-editor-flow.md](/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/docs/plans/refactor-tech-stack/04-api-and-editor-flow.md)
5. [05-migration-and-cutover.md](/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/docs/plans/refactor-tech-stack/05-migration-and-cutover.md)
6. [06-docker-compose-and-ops.md](/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/docs/plans/refactor-tech-stack/06-docker-compose-and-ops.md)
7. [07-implementation-checklist.md](/Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/docs/plans/refactor-tech-stack/07-implementation-checklist.md)
8. [08-quotation-content-studio-contract.md](./08-quotation-content-studio-contract.md)
9. [09-media-library-and-option-catalog.md](./09-media-library-and-option-catalog.md)
10. [10-quotations-new-ui-ux.md](./10-quotations-new-ui-ux.md)
11. [11-r2-media-file-contract.md](./11-r2-media-file-contract.md)
12. [12-v2-brochure-workflow-gate.md](./12-v2-brochure-workflow-gate.md)
13. [13-systemic-color-architecture-and-brand-theming.md](./13-systemic-color-architecture-and-brand-theming.md)

## Scope chot

- Bo Vercel/GitHub persistence khoi duong luu tru chinh cho quotation v2.
- Giữ `FastAPI` la app backend chinh.
- Them `Postgres` lam source of truth cho quotation/editor state.
- Them `Cloudflare R2` lam source of truth cho media va artifact object.
- Deploy bang `docker compose` tren 1 VPS.

## Ket qua mong muon sau refactor

- Editor save/load du lieu tu Postgres.
- Upload image tu editor len R2 va luu metadata vao Postgres.
- Co API dong bo danh sach image local tren VPS len R2, kem thumbnail preview.
- Publish quotation v2 doc du lieu tu Postgres, render HTML/PDF, day artifact len R2.
- He thong chay on dinh tren 1 VPS bang Docker Compose va co healthcheck, migration, backup co ban.

## Nguyen tac implement

- Khong tiep tuc dung `published/<id>/ctx.json` va `document.json` lam source of truth cho quotation v2.
- Khong dung GitHub commit lam co che persistence production nua.
- Local disk chi la cache hoac inbox sync, khong phai storage canon.
- Canonical state cua editor phai nam o Postgres.
- Canonical binary object phai nam o R2.

## Cap nhat implementation va boundary hien tai

- V2 document, revision history, publication records, Content Studio
  candidates, fact sources, Travel Designer profile/assignment va Media Library
  catalog da co Postgres/Alembic ownership.
- Media Library (`/api/v2/media-library/*`) la write path moi cho R2 taxonomy
  va searchable option catalog. `/api/v2/media/*` va `media_assets` la legacy
  compatibility path; khong mo rong path cu cho feature moi.
- Publish V2 upload HTML immutable va `current` alias len R2. PDF render on
  demand tu immutable document revision va khong co R2 key.
- Quote Generator la display/editor client; public brochure UI phai consume
  resolved `PageViewModel + theme + view mode + color scope`, khong tu doc raw
  brand data hay editor state.
- Legacy V1 van duoc giu rieng. V1 `brochureDraft`/published HTML precedence
  khong duoc tro thanh fallback im lang cua V2.
