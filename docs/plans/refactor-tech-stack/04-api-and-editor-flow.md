# 04. API And Editor Flow

## 1. Muc tieu

Tai lieu nay chot API contract va editor flow sau refactor, de frontend/backend implement dong bo.

## 2. Quotation flow tong quan

### Tao quotation v2

1. Client goi `POST /api/v2/quotations`
2. Backend sinh `quotation_id`
3. Generate initial document
4. Ghi `quotations`
5. Ghi `quotation_requests`
6. Ghi `quotation_documents` current
7. Ghi `quotation_document_revisions` revision 1
8. Render preview neu can
9. Tra ve quotation metadata + document

### Mo editor

1. Client goi `GET /api/v2/quotations/{quotation_id}/document?lang=en`
2. Backend doc current document tu Postgres
3. Backend tra document + revision + section registry

### Autosave

1. Client debounce 2-5 giay
2. Goi `PUT /api/v2/quotations/{quotation_id}/document`
3. Gui `baseRevision`
4. Backend lock/check current revision
5. Save document moi
6. Tra revision moi

### Publish

1. Client goi `POST /api/v2/quotations/{quotation_id}/publish`
2. Backend doc current document tu Postgres
3. Render HTML/PDF
4. Upload artifacts len R2
5. Insert `quotation_publications`
6. Update `quotations.current_version` va `status`
7. Tra publication metadata

## 3. API contract chi tiet

## 3.1 `POST /api/v2/quotations`

Request:

- giu lai schema `CreateQuoteRequestV1` hien tai toi da co the

Response de xuat:

```json
{
  "quotationId": "quo_abc123",
  "status": "draft",
  "baselineLang": "en",
  "currentRevision": 1,
  "currentVersion": 0,
  "document": {},
  "documentVersion": 1
}
```

Luu y:

- `currentVersion = 0` nghia la chua publish
- `currentRevision = 1` la revision editor dau tien

## 3.2 `GET /api/v2/quotations/{quotation_id}/document`

Response:

```json
{
  "quotationId": "quo_abc123",
  "lang": "en",
  "currentRevision": 3,
  "documentVersion": 1,
  "document": {},
  "sectionRegistry": {}
}
```

## 3.3 `PUT /api/v2/quotations/{quotation_id}/document`

Request:

```json
{
  "baseRevision": 3,
  "document": {}
}
```

Response:

```json
{
  "ok": true,
  "quotationId": "quo_abc123",
  "currentRevision": 4,
  "documentVersion": 1,
  "document": {}
}
```

Conflict response:

```json
{
  "detail": "Revision conflict",
  "currentRevision": 5,
  "document": {}
}
```

Status code: `409`

## 3.4 `POST /api/v2/quotations/{quotation_id}/publish`

Request:

```json
{
  "lang": "en"
}
```

Response:

```json
{
  "quotationId": "quo_abc123",
  "status": "published",
  "version": 1,
  "lang": "en",
  "publishedUrl": "https://app.example.com/quotations/quo_abc123",
  "htmlUrl": "https://cdn.example.com/quotations/quo_abc123/publish/en/v1.html",
  "pdfUrl": "https://cdn.example.com/quotations/quo_abc123/publish/en/v1.pdf"
}
```

## 3.5 `POST /api/v2/media/upload`

Request:

- multipart form
- fields:
  - `file`
  - `quotationId` optional

Response:

```json
{
  "assetId": "med_abc123",
  "quotationId": "quo_abc123",
  "status": "ready",
  "originalUrl": "https://cdn.example.com/...",
  "previewUrl": "https://cdn.example.com/...",
  "width": 2400,
  "height": 1600
}
```

## 3.6 `GET /api/v2/media`

Phuc vu gallery picker.

Response:

```json
{
  "items": [],
  "page": 1,
  "pageSize": 24,
  "total": 120
}
```

## 3.7 `POST /api/v2/media/sync`

Request:

```json
{
  "folder": "",
  "recursive": true,
  "quotationId": null
}
```

Response:

```json
{
  "scanned": 0,
  "uploaded": 0,
  "skipped": 0,
  "failed": 0,
  "items": []
}
```

## 3.8 `POST /api/v2/media/{asset_id}/select`

Request:

```json
{
  "quotationId": "quo_abc123",
  "lang": "en",
  "sectionKey": "hero",
  "slotKey": "cover_image",
  "displayOrder": 0
}
```

Response:

```json
{
  "ok": true
}
```

## 4. Editor integration rule

## 4.1 Autosave strategy

- debounce: `2000-5000 ms`
- autosave khi:
  - field change
  - image selection change
  - section reorder
- khong autosave tung keypress neu dang typing lien tuc

## 4.2 Save state

Frontend nen co:

- `idle`
- `saving`
- `saved`
- `conflict`
- `error`

## 4.3 Image picker flow

1. User mo gallery
2. Frontend goi `GET /api/v2/media`
3. User upload anh moi hoac chon anh co san
4. Neu upload:
   - goi `POST /api/v2/media/upload`
5. Neu chon:
   - goi `POST /api/v2/media/{asset_id}/select`
6. Cap nhat document local
7. Autosave document

## 4.4 Publish button

Frontend khong duoc gui raw HTML la source of truth nua.

Publish flow moi:

- frontend gui request publish tu document state
- backend doc canonical document tu Postgres
- backend tu render

Dieu nay can loai bo phu thuoc vao flow publish bang edited HTML thu cong cho quotation v2.

## 5. Mapping tu code hien tai sang flow moi

Code hien tai co hai flow:

- draft document flow
- raw HTML publish flow

Sau refactor, quotation v2 chi giu:

- draft document flow
- publish from canonical document

Khong tiep tuc support:

- v2 raw HTML as canonical publish input

## 6. Error handling

Code response de xuat:

- `400`: invalid payload
- `404`: quotation/media khong ton tai
- `409`: revision conflict
- `413`: file qua lon
- `415`: unsupported media type
- `422`: validation error
- `500`: unexpected app error
- `502`: loi upload/object storage dependency

## 7. Audit fields

Neu co auth user trong phase nay, nen bo sung:

- `created_by`
- `updated_by`
- `published_by`

Neu chua co auth:

- tam thoi de nullable
- khong block implementation

