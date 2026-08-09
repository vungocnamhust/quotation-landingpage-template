# 07. Implementation Checklist

> **Status snapshot — 2026-08-06.** This checklist originally described work
> before implementation. Checked items are present in the repository and have
> focused automated coverage where noted; unchecked deployment/manual gates are
> intentionally not claimed complete.

## 1. Definition of done

Chi coi la hoan thanh khi tat ca muc sau deu dung:

- quotation v2 create/save/load dung Postgres
- editor autosave dung Postgres
- image upload len R2 va co preview
- gallery API tra danh sach image inventory
- local media sync API day file tren VPS len R2
- publish v2 doc document tu Postgres va tao publication record
- app chay duoc tren 1 VPS bang Docker Compose

## 2. Checklist theo phase

## Phase A. Foundation

- [x] Them dependencies SQLAlchemy, asyncpg, alembic, boto3, Pillow, python-multipart
- [x] Tao `config` cho DB va R2 env vars
- [x] Tao `db/base.py`
- [x] Tao `db/session.py`
- [x] Init Alembic
- [x] Tao migration schema ban dau

## Phase B. Database models and repositories

- [x] Tao model `quotations`
- [x] Tao model `quotation_requests`
- [x] Tao model `quotation_documents`
- [x] Tao model `quotation_document_revisions`
- [x] Tao model `quotation_publications`
- [x] Tao model `media_assets`
- [x] Tao model `media_selections`
- [x] Tao repositories cho quotation/document/media/publication

## Phase C. Quotation v2 persistence

- [x] Refactor `POST /api/v2/quotations` de ghi Postgres
- [x] Refactor `GET /api/v2/quotations/{id}/document` de doc Postgres
- [x] Refactor `PUT /api/v2/quotations/{id}/document` de autosave Postgres
- [x] Them optimistic locking bang `baseRevision`
- [x] Refactor `POST /api/v2/quotations/{id}/publish` de doc canonical document tu Postgres

## Phase D. R2 media

- [x] Tao `R2Storage` adapter
- [x] Tao helper tinh checksum
- [x] Tao helper doc image size
- [x] Tao helper tao thumbnail preview
- [x] Implement Media Library upload/list/select/sync write path
- [ ] Verify legacy `/api/v2/media/*` compatibility endpoints against isolated R2

## Phase E. Migration

- [x] Viet script migrate quotation v2 tu `published/`
- [x] Viet script migrate media len R2
- [x] Test migration tren fixture ctx-only va production-shaped
- [ ] Verify editor mo duoc quotation da migrate

## Phase F. Docker Compose

- [x] Tao `docker/app/Dockerfile`
- [x] Tao `docker/nginx/default.conf`
- [x] Tao compose manifests local/production
- [x] Tao health endpoints
- [ ] Tao `.env.production.example`
- [ ] Deploy thu tren local bang Docker Compose

## Phase G. Cutover

- [ ] Chay migration tren VPS
- [ ] Deploy app moi
- [ ] Test create quotation moi
- [ ] Test autosave
- [ ] Test upload/select image
- [ ] Test media sync tu folder local
- [ ] Test publish
- [ ] Tat legacy fallback cho quotation v2

## 3. File-level implementation map

## Files moi can them

- [ ] `db/base.py`
- [ ] `db/session.py`
- [ ] `db/models/quotation.py`
- [ ] `db/models/media.py`
- [ ] `db/models/publication.py`
- [ ] `repositories/quotation_repository.py`
- [ ] `repositories/media_repository.py`
- [ ] `services/storage/r2_storage.py`
- [ ] `services/media_service.py`
- [ ] `services/quotation_service.py`
- [ ] `alembic/*`
- [ ] `docker-compose.yml`
- [ ] `docker/app/Dockerfile`
- [ ] `docker/nginx/default.conf`
- [ ] `scripts/migrate_quotation_v2_to_postgres.py`
- [ ] `scripts/migrate_media_to_r2.py`

## Files cu can refactor

- [ ] `main.py`
- [ ] `requirements.txt`
- [ ] `.env.example`
- [ ] `Dockerfile` hoac thay bang Dockerfile moi

## 4. Testing checklist

## Unit tests

- [ ] repository create/get quotation
- [ ] document save with revision
- [ ] revision conflict
- [ ] media upload metadata
- [ ] thumbnail generation
- [ ] R2 key generation

## Integration tests

- [x] create quotation -> returns document
- [x] get document -> returns current revision
- [x] save document -> increments revision
- [x] publish -> creates publication row
- [ ] media upload -> uploads original + preview
- [ ] media sync -> scans local folder and upserts metadata

## Manual tests

- [ ] editor open/save
- [ ] upload 1 JPG
- [ ] upload 1 PNG
- [ ] select image in hero slot
- [ ] publish English version
- [ ] publish Vietnamese version
- [ ] migrate 1 quotation cu

## 5. Risks canh bao

- [ ] `main.py` hien tai qua lon, refactor truc tiep de bi conflict
- [ ] legacy v1 va itinerary co the dang dung chung helper voi v2
- [ ] upload va publish neu khong tach service se tiep tuc lam route rat lon
- [ ] migration du lieu cu co the gap quotation thieu `document.json`

## 6. Quyet dinh kien truc da chot

- [x] 1 VPS
- [x] Docker Compose
- [x] Postgres la source of truth cho editor
- [x] R2 la source of truth cho media object
- [x] Editor publish tu canonical document, khong publish tu raw HTML lam source of truth
- [x] Local VPS folder chi la noi sync/caching

## 7. Thu tu implement khuyen nghi

1. Database va Alembic
2. Quotation persistence
3. Media upload va R2
4. Media sync API
5. Publish flow moi
6. Migration script
7. Docker Compose deployment
