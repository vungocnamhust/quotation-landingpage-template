# 05. Migration And Cutover

## 1. Muc tieu

Chuyen quotation v2 tu mo hinh file/GitHub persistence sang Postgres + R2 ma khong mat du lieu quan trong.

## 2. Du lieu can migrate

Moi quotation v2 hien co co the dang ton tai:

- `published/<quotation_id>/ctx.json`
- `published/<quotation_id>/document.json`
- `published/<quotation_id>/create_request_v2.json`
- `published/<quotation_id>/v*.html`
- `published/<quotation_id>/pdf*.html`
- `published/<quotation_id>/draft_assets/*`

## 3. Du lieu can map vao he moi

### From `ctx.json`

Lay:

- `baseline_lang`
- `template_name`
- `quotation_id`
- `opportunity_id`
- brand info
- available languages
- html sync state neu can

### From `document.json`

Lay:

- canonical document cho editor

### From `create_request_v2.json`

Lay:

- request snapshot

### From `draft_assets/*`

Lay:

- original file -> upload R2
- metadata -> `media_assets`

## 4. Script migration

Tao script:

```text
scripts/migrate_quotation_v2_to_postgres.py
scripts/migrate_media_to_r2.py
```

## 4.1 `migrate_quotation_v2_to_postgres.py`

Flow:

1. Scan thu muc `published/`
2. Tim quotation id co pattern `quo_*`
3. Khong bo qua item chi vi thieu `document.json`: migrate ctx-only item neu
   co du canonical context, va ghi per-item failure ro rang neu khong the map.
4. Load `ctx.json`
5. Load `document.json`
6. Load `create_request_v2.json` neu co
7. Tao row `quotations`
8. Tao row `quotation_requests`
9. Tao row `quotation_documents` current
10. Tao row `quotation_document_revisions` revision 1 voi `change_source=migration`
11. Parse publication file names va tao `quotation_publications` neu can

## 4.2 `migrate_media_to_r2.py`

Flow:

1. Scan `published/<quotation_id>/draft_assets`
2. Upload tung file len R2
3. Tao preview
4. Insert `media_assets`

## 5. Strategy cutover

Khuyen nghi 3 buoc:

### Buoc 1. Import va verify, khong dual-write canonical state

Trong giai doan chuyen doi:

- quotation v2 moi save vao Postgres
- import legacy artifacts vao Postgres/R2 mot lan co bao cao per-item
- co the van ghi file debug local neu can, nhung file local khong duoc coi la
  source of truth

### Buoc 2. Read from Postgres only

Khi migration xong:

- API editor chi doc Postgres
- khong fallback im lang ve `ctx.json`/`document.json`

### Buoc 3. Remove GitHub persistence path

Sau khi VPS da van hanh on dinh:

- bo code publish context/document len GitHub cho quotation v2
- giu legacy path cho v1 neu can tach rieng

## 6. Backward compatibility

Khuyen nghi:

- legacy quotation v1 va itinerary co the tam de nguyen
- quotation v2 route moi dung Postgres/R2

Dieu nay giam risk trong dot refactor dau.

## 7. Feature flag de xuat

Them env:

```env
QUOTATION_V2_STORAGE_BACKEND=postgres
LEGACY_STORAGE_FALLBACK=false
MEDIA_STORAGE_BACKEND=r2
```

Feature flag giup rollback nhanh neu can trong giai doan dau.

## 8. Validation sau migration

Can script verify:

- tong so quotation migrate
- quotation co current document
- publication count dung
- media asset count dung
- cac object R2 ton tai

Checklist verify:

- mo editor duoc voi quotation migrate
- autosave duoc
- publish duoc version moi
- image picker load duoc asset cu

## 9. Cutover order de xuat

1. Deploy schema Postgres + R2 adapter
2. Deploy app version co DB/R2 support nhung chua traffic
3. Chay migration data
4. Verify bang script
5. Bat routing quotation v2 sang API moi
6. Theo doi logs
7. Tat legacy fallback

## 10. Root-cause prevention

Khong chuyen doi nua nua:

- Neu da chot quotation v2 doc tu Postgres thi khong de route nao van tiep tuc cap nhat `ctx.json` roi xem do la ban chinh.

Neu con write file local, ghi ro:

- debug only
- non-canonical

Migration report phai expose item-level reason. Aggregate `migrated=0` khong
du de ket luan migration thanh cong hoac that bai.
