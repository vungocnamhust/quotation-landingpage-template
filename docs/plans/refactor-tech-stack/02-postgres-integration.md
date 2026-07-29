# 02. Postgres Integration

## 1. Muc tieu

Tich hop Postgres vao FastAPI de:

- luu quotation v2 metadata
- luu document editor autosave
- luu revision history
- luu media metadata
- luu publication state

## 2. Dependencies can them

Them vao `requirements.txt`:

```text
SQLAlchemy>=2.0
asyncpg>=0.29
alembic>=1.13
psycopg[binary]>=3.2
boto3>=1.35
Pillow>=10.4
python-multipart>=0.0.9
```

Giai thich:

- `SQLAlchemy 2.x`: ORM va async engine
- `asyncpg`: driver runtime cho app
- `alembic`: migration schema
- `psycopg`: thuan tien cho migration/tooling neu can
- `python-multipart`: upload file FastAPI

## 3. Database config

Them env:

```env
DATABASE_URL=postgresql+asyncpg://quotation:quotation_password@postgres:5432/quotation
DATABASE_URL_SYNC=postgresql+psycopg://quotation:quotation_password@postgres:5432/quotation
DB_ECHO=false
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

## 4. Session layer

Tao:

- `db/base.py`
- `db/session.py`

### `db/base.py`

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

### `db/session.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

## 5. Data model chi tiet

## 5.1 `quotations`

Bang tong cua quotation.

Fields:

- `id`: string, PK, vd `quo_xxx`
- `opportunity_id`: nullable string, index
- `brand_id`: string
- `status`: string
- `baseline_lang`: string(5)
- `current_revision`: int
- `current_version`: int
- `template_name`: string
- `customer_name`: nullable string
- `title`: nullable string
- `created_at`: timestamptz
- `updated_at`: timestamptz

Status de xuat:

- `draft`
- `published`
- `archived`

## 5.2 `quotation_requests`

Snapshot request tao quotation.

Fields:

- `id`: bigserial PK
- `quotation_id`: FK -> quotations.id
- `request_json`: jsonb
- `created_at`: timestamptz

## 5.3 `quotation_documents`

Noi luu canonical document cua editor.

Fields:

- `id`: bigserial PK
- `quotation_id`: FK
- `lang`: string(5)
- `revision`: int
- `document_json`: jsonb
- `html_sync`: jsonb nullable
- `generation_status`: jsonb nullable
- `is_current`: bool
- `created_at`: timestamptz
- `updated_at`: timestamptz

Rules:

- Moi lan autosave tao `revision` moi hoac update current revision tuy chien luoc.
- Khuyen nghi:
  - update current row cho autosave binh thuong
  - ghi snapshot revision rieng khi publish hoac manual checkpoint

Neu can don gian phase 1:

- Giữ 1 row current
- Luu lich su trong `quotation_document_revisions`

## 5.4 `quotation_document_revisions`

Fields:

- `id`: bigserial PK
- `quotation_id`: FK
- `lang`: string(5)
- `revision`: int
- `document_json`: jsonb
- `change_source`: string
- `created_at`: timestamptz

`change_source`:

- `create`
- `autosave`
- `regenerate_narrative`
- `publish`
- `migration`

## 5.5 `quotation_publications`

Fields:

- `id`: bigserial PK
- `quotation_id`: FK
- `version`: int
- `lang`: string(5)
- `html_r2_key`: string
- `pdf_r2_key`: string nullable
- `published_url`: string nullable
- `pdf_url`: string nullable
- `created_at`: timestamptz

Constraint:

- unique `(quotation_id, version, lang)`

## 5.6 `media_assets`

Fields:

- `id`: uuid/string PK
- `quotation_id`: nullable FK
- `source_type`: string
- `bucket`: string
- `r2_key`: string unique
- `preview_r2_key`: string nullable
- `original_filename`: string
- `mime_type`: string
- `size_bytes`: bigint
- `checksum_sha256`: string
- `width`: int nullable
- `height`: int nullable
- `local_path`: string nullable
- `status`: string
- `metadata_json`: jsonb
- `created_at`: timestamptz
- `updated_at`: timestamptz

`source_type`:

- `editor_upload`
- `vps_sync`
- `migration`

`status`:

- `ready`
- `processing`
- `failed`
- `deleted`

## 5.7 `media_selections`

Map asset vao quotation section/block.

Fields:

- `id`: bigserial PK
- `quotation_id`: FK
- `asset_id`: FK -> media_assets.id
- `lang`: string(5) nullable
- `section_key`: string
- `slot_key`: string
- `display_order`: int
- `created_at`: timestamptz

Constraint:

- unique `(quotation_id, lang, section_key, slot_key, display_order)`

## 6. Index can tao

- `quotations(opportunity_id)`
- `quotations(status, updated_at desc)`
- `quotation_documents(quotation_id, lang, is_current)`
- `quotation_document_revisions(quotation_id, lang, revision desc)`
- `quotation_publications(quotation_id, version desc)`
- `media_assets(quotation_id, created_at desc)`
- `media_assets(status, created_at desc)`
- `media_assets(checksum_sha256)`
- `media_selections(quotation_id, section_key, slot_key)`

## 7. SQLAlchemy model strategy

Khuyen nghi:

- `db/models/quotation.py`
- `db/models/media.py`
- `db/models/publication.py`

Dung:

- `Mapped[...]`
- `mapped_column(...)`
- `JSONB` cho document va metadata
- `Enum` chi khi team chap nhan migration phuc tap hon

Phase 1 nen dung `String` cho status/source_type de doi schema nhanh hon.

## 8. Alembic

Khoi tao:

```bash
alembic init alembic
```

Canh chinh:

- `alembic.ini`
- `alembic/env.py`
- import metadata tu `Base.metadata`
- doc `DATABASE_URL_SYNC`

Migration dau tien:

- tao toan bo bang o tren
- tao index
- tao constraint unique

Ten migration de xuat:

`20260729_01_create_quotation_v2_storage`

## 9. Repository layer

Khong de route thao tac thang SQLAlchemy query lan lon.

Can co:

- `QuotationRepository`
- `QuotationDocumentRepository`
- `MediaRepository`
- `PublicationRepository`

Method toi thieu:

- `create_quotation(...)`
- `get_quotation_by_id(...)`
- `save_current_document(...)`
- `append_document_revision(...)`
- `list_publications(...)`
- `create_media_asset(...)`
- `list_media_assets(...)`
- `upsert_media_selection(...)`

## 10. Service layer

Can co:

- `QuotationService`
- `EditorDocumentService`
- `MediaService`
- `PublicationService`

Rule:

- Route chi validate request/response
- Service xu ly business flow
- Repository xu ly persistence

## 11. Autosave va optimistic locking

Can co `revision` trong request autosave.

Luon check:

- client gui `base_revision`
- server so sanh voi `current_revision`

Neu khac:

- tra `409 conflict`
- response kem `current_revision` va `current_document`

Khong duoc overwrite im lang.

## 12. Mapping tu code hien tai

Du lieu dang nam o:

- `ctx["createQuoteRequestV1"]`
- `ctx["template_name"]`
- document draft trong `document.json`
- lang trong `baseline_lang`
- publication version trong published HTML naming

Mapping moi:

- `ctx["createQuoteRequestV1"]` -> `quotation_requests.request_json`
- `document.json` -> `quotation_documents.document_json`
- `ctx["baseline_lang"]` -> `quotations.baseline_lang`
- publish `vN_lang.html` -> `quotation_publications`

