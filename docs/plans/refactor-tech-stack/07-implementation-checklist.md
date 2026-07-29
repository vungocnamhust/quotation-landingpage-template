# 07. Implementation Checklist

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

- [ ] Them dependencies SQLAlchemy, asyncpg, alembic, boto3, Pillow, python-multipart
- [ ] Tao `config` cho DB va R2 env vars
- [ ] Tao `db/base.py`
- [ ] Tao `db/session.py`
- [ ] Init Alembic
- [ ] Tao migration schema ban dau

## Phase B. Database models and repositories

- [ ] Tao model `quotations`
- [ ] Tao model `quotation_requests`
- [ ] Tao model `quotation_documents`
- [ ] Tao model `quotation_document_revisions`
- [ ] Tao model `quotation_publications`
- [ ] Tao model `media_assets`
- [ ] Tao model `media_selections`
- [ ] Tao repositories cho quotation/document/media/publication

## Phase C. Quotation v2 persistence

- [x] Refactor `POST /api/v2/quotations` de ghi Postgres
- [x] Refactor `GET /api/v2/quotations/{id}/document` de doc Postgres
- [x] Refactor `PUT /api/v2/quotations/{id}/document` de autosave Postgres
- [x] Them optimistic locking bang `baseRevision`
- [x] Refactor `POST /api/v2/quotations/{id}/publish` de doc canonical document tu Postgres

## Phase D. R2 media

- [ ] Tao `R2Storage` adapter
- [ ] Tao helper tinh checksum
- [ ] Tao helper doc image size
- [ ] Tao helper tao thumbnail preview
- [ ] Implement `POST /api/v2/media/upload`
- [ ] Implement `GET /api/v2/media`
- [ ] Implement `POST /api/v2/media/{asset_id}/select`
- [ ] Implement `POST /api/v2/media/sync`

## Phase E. Migration

- [ ] Viet script migrate quotation v2 tu `published/`
- [ ] Viet script migrate media len R2
- [ ] Test migration tren du lieu mau
- [ ] Verify editor mo duoc quotation da migrate

## Phase F. Docker Compose

- [ ] Tao `docker/app/Dockerfile`
- [ ] Tao `docker/nginx/default.conf`
- [ ] Tao `docker-compose.yml`
- [ ] Tao health endpoints
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
