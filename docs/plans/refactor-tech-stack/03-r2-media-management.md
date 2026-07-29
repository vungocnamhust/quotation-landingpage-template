# 03. R2 Media Management

## 1. Muc tieu

Tich hop Cloudflare R2 de:

- luu original image
- luu thumbnail preview
- luu published artifacts neu can
- ho tro editor upload image
- ho tro API dong bo image tu local VPS len R2

## 2. Nguyen tac

- Binary object chi luu o R2
- Metadata nghiep vu chi luu o Postgres
- Local path tren VPS chi la nguon sync hoac cache
- Thumbnail preview duoc tao boi backend, khong de editor tu tuong tac truc tiep voi original lon

## 3. Env vars

```env
R2_ACCOUNT_ID=xxxxxxxxxxxxxxxx
R2_ACCESS_KEY_ID=xxxxxxxxxxxxxxxx
R2_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxx
R2_BUCKET=quotation-v2
R2_REGION=auto
R2_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
R2_PUBLIC_BASE_URL=https://cdn.example.com
MEDIA_SYNC_DIR=/data/media-sync/inbox
MEDIA_CACHE_DIR=/data/media-sync/cache
MEDIA_PREVIEW_MAX_WIDTH=480
MEDIA_PREVIEW_MAX_HEIGHT=320
MEDIA_PREVIEW_QUALITY=82
```

## 4. R2 key convention

Quy uoc key de tranh lon xon:

```text
quotations/{quotation_id}/media/original/{asset_id}.{ext}
quotations/{quotation_id}/media/preview/{asset_id}.jpg
quotations/{quotation_id}/publish/{lang}/v{version}.html
quotations/{quotation_id}/publish/{lang}/v{version}.pdf
shared/media/original/{asset_id}.{ext}
shared/media/preview/{asset_id}.jpg
```

Rule:

- Asset gan voi quotation cu the thi uu tien nam duoi `quotations/{quotation_id}/...`
- Asset dung chung thi nam duoi `shared/...`

## 5. Storage adapter

Tao `services/storage/r2_storage.py`

Methods toi thieu:

- `upload_bytes(key: str, content: bytes, content_type: str) -> str`
- `upload_file(local_path: str, key: str, content_type: str) -> str`
- `download_bytes(key: str) -> bytes`
- `delete_object(key: str) -> None`
- `build_public_url(key: str) -> str`
- `head_object(key: str) -> dict`

Dung `boto3.client("s3", endpoint_url=...)`.

## 6. Upload flow tu editor

Flow:

1. Editor goi `POST /api/v2/media/upload`
2. Backend nhan `UploadFile`
3. Validate mime/size
4. Tinh `sha256`
5. Doc kich thuoc anh
6. Upload original len R2
7. Tao thumbnail preview JPG
8. Upload preview len R2
9. Ghi metadata vao Postgres
10. Tra response cho editor

## 7. Validation upload

Can hard rule:

- MIME cho phep:
  - `image/jpeg`
  - `image/png`
  - `image/webp`
- max upload size:
  - phase 1: `15 MB`
- filename khong duoc dung lam key canonical
- luon sinh `asset_id` moi

Can reject:

- file rong
- mime khong hop le
- noi dung khong doc duoc bang Pillow

## 8. Thumbnail policy

Preview khong can giong 1:1 original.

De xuat:

- resize fit trong khung `480x320`
- format JPG
- quality `82`
- strip metadata khong can thiet

Response gallery can tra:

- `original_url`
- `preview_url`
- `width`
- `height`

Editor gallery chi nen show `preview_url`.

## 9. API dong bo local VPS -> R2

Muc tieu: cho phep bo phan van hanh copy image vao mot folder tren VPS, sau do backend sync len R2 va cap nhat metadata.

### Folder convention

```text
/data/media-sync/inbox/
  hanoi/
  halong/
  sapa/
  misc/
```

Hoac don gian:

```text
/data/media-sync/inbox/<any nested folders>
```

### `POST /api/v2/media/sync`

Request:

```json
{
  "folder": "hanoi",
  "recursive": true,
  "quotationId": null
}
```

Backend se:

1. Resolve folder trong `MEDIA_SYNC_DIR`
2. Scan file image hop le
3. Tinh checksum
4. Check Postgres xem checksum da ton tai chua
5. Neu chua co:
   - upload original
   - tao preview
   - upload preview
   - insert metadata
6. Neu da co:
   - bo qua hoac update `local_path` neu can
7. Tra summary

Response:

```json
{
  "scanned": 42,
  "uploaded": 30,
  "skipped": 12,
  "failed": 0,
  "items": []
}
```

## 10. API list image inventory

### `GET /api/v2/media`

Query params de xuat:

- `quotationId`
- `sourceType`
- `status`
- `search`
- `page`
- `pageSize`

Response item:

```json
{
  "id": "med_xxx",
  "quotationId": "quo_xxx",
  "status": "ready",
  "sourceType": "editor_upload",
  "originalFilename": "halong-bay.jpg",
  "mimeType": "image/jpeg",
  "sizeBytes": 2381231,
  "width": 2400,
  "height": 1600,
  "localPath": "/data/media-sync/inbox/halong/halong-bay.jpg",
  "r2Key": "quotations/quo_xxx/media/original/med_xxx.jpg",
  "previewR2Key": "quotations/quo_xxx/media/preview/med_xxx.jpg",
  "originalUrl": "https://cdn.example.com/...",
  "previewUrl": "https://cdn.example.com/...",
  "createdAt": "2026-07-29T15:00:00Z"
}
```

Day la API "select images" cho editor.

## 11. API gan asset vao editor

### `POST /api/v2/media/{asset_id}/select`

Request:

```json
{
  "quotationId": "quo_xxx",
  "lang": "en",
  "sectionKey": "hero",
  "slotKey": "cover_image",
  "displayOrder": 0
}
```

Tac dung:

- khong copy file
- chi tao relation metadata trong `media_selections`

## 12. Publish artifact len R2

Khi publish quotation:

- HTML render xong -> upload `html`
- PDF render xong -> upload `pdf`
- ghi `quotation_publications`

Neu can public permalink:

- co the dung direct R2 public URL hoac custom domain `cdn.example.com`
- trang public `/quotations/{id}` van do FastAPI/Nginx phuc vu, nhung artifact archive nen nam tren R2

## 13. Bao mat

- R2 credentials chi nam trong env tren VPS
- Khong expose private endpoint/truy cap key ra frontend
- Frontend luon upload qua backend phase 1
- Chua dung signed URL neu chua can; direct backend upload de de kiem soat

## 14. Logging va quan sat

Can log:

- upload bat dau/ket thuc
- asset id
- quotation id
- checksum
- R2 key
- error category

Khong log:

- secret key
- binary data

