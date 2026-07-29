# Refactor Tech Stack Plan

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

