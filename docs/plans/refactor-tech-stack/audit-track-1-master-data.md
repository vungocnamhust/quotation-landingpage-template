# Audit Implementation — Track 1: Master Data & Catalog Architecture Defect Log

> Ngày audit: 2026-09-01. Phương pháp: 3 lượt review đối kháng độc lập theo domain (suppliers /
> products / destinations+kernel) + **mọi finding CRITICAL/HIGH đều được xác minh lại tận mắt**
> bằng đọc code hoặc thực thi probe (không dựa vào lời kể của agent). Không sửa bất kỳ code,
> test hay migration nào trong quá trình audit.

## 1. Subsystem Scope & Verified Call-Graph Perimeter

**Anchor specs**: `15.1-supplier-registry.md` · `15.2-product-catalog.md` ·
`15.2b-destination-standards-and-hierarchy.md` · `15-modular-tour-ops-brainstorm.md` (kernel K1–K8, vùng cấm).

**Entrypoints đã quét toàn văn**: `db/models/{supplier,product,destination}.py` ·
`repositories/{supplier,product,destination}_repository.py` · `services/{supplier,product}_service.py` ·
`schemas/v2/{supplier,product}.py` · `routers/v2/{suppliers,products,destinations}.py` ·
`core/kernel/{ids,actor,money,__init__}.py` · `core/rules/{catalog_vocab,destination_rules,service_candidate_rules}.py` ·
`alembic/versions/20260827_36_*`, `20260828_37_*`, `20260830_38_*` · `destination_catalog_seed.py` ·
`services/media_locations.py`.

**Call-path ngoài anchor đã truy vết**: `main.py` (`include_router` ×3; `_serialize_destination`,
`_save_destination` ~8120–8175 gồm slug-chain freeze 8167, `_merge_destination` 8193,
`_seed_destination_catalog` 7235, generic exception handler 1217–1227) · `api/dependencies.py`
(`EditorPrincipalDep`, `DbSessionDep`) · `db/session.py::get_db` (không `PRAGMA foreign_keys`) ·
`core/auth.py` (`require_editor` / `require_quote_admin`) · `repositories/media_library_repository.py::has_media_for_destination` ·
FE: `quote-generator/components/destination/{DestinationSelect.tsx,useDestinationSearch.ts,types.ts}`,
`components/product/{ProductManageDrawer.tsx,types.ts}`.

**Baseline test suite** (read-only run):
`test_supplier_{service,api}` · `test_product_{service,api}` · `test_catalog_vocab` · `test_kernel_ids` ·
`test_destination_{catalog_crud,rules,fuzzy_matching,hierarchy,merge}` · `test_v2_api_manifest_contract` ·
`test_ssot_integrity` → **94 passed, 0 failed**. Kết luận nền: suite xanh **không** phản ánh các
defect dưới đây vì (a) SQLite trong test không bật FK enforcement (H2), (b) không có test đua
concurrency, (c) không có test cross-process cho id generator.

**Đã xác minh ĐÚNG spec (không phải defect)** — ghi để tránh false lead: zero-money R2 sạch trên cả
supplier/product (model + schema); unique functional index products khớp 100% model ↔ migration `_38`
(kể cả `coalesce(origin_destination_id,'')`, drop/recreate quanh `batch_alter_table` đúng cho SQLite);
policy JSONB có sub-model Pydantic + invariant validators (tiers không chồng, bands không chồng) áp
**cả** create lẫn PUT (`exclude_unset=True`); không `commit()` trong repository nào; ActorRef ghi trên
mọi write path; slug-chain R2 freeze có thật (`main.py:8167`) và `media_locations.py` không đổi kể từ
15.2b; hierarchy validator (rank, cycle depth 6, merged không làm parent, self-parent) chạy cả create
lẫn update; 2 bản seed `seed_destination_catalog` **chưa** drift (đã diff); `ServiceType` đồng bộ
10 category có `assert` runtime; FE `product/types.ts` mirror vocab khớp 1-1; `supplier_product_name`
immutable đúng; dedupe pre-check dùng đúng key với DB index (gồm origin); `internal_notes` /
`bank_details_ref` không rò ra public schema.

---

## 2. Defect Log (BẮT BUỘC trước khi nghiệm thu)

### §1.1 C1 🔴 CRITICAL — Destination đã merge có thể được kích hoạt lại, hồi sinh bản trùng và tách rời `is_active` khỏi `merged_into_id`
- **Vị trí**: `routers/v2/destinations.py::update_destination_status` (~dòng 168–183) và
  `repositories/destination_repository.py::set_status` (~dòng 194–197); gốc rễ:
  `search()` (~216–219) và cả 3 tầng `resolve()` (~381, ~398, ~420) chỉ lọc `is_active`, **không** lọc `merged_into_id IS NULL`.
- **Cơ chế lỗi**: `merge(A→B)` set `A.is_active=False, A.merged_into_id=B`. `PATCH /status {isActive:true}`
  chỉ kiểm tra tọa độ, không kiểm `merged_into_id` → A trở thành `is_active=True` **và**
  `merged_into_id=B` cùng lúc — trạng thái không có CHECK constraint nào chặn. Hệ quả: A xuất hiện
  lại trong dropdown cạnh chính B; alias của A bị skip lúc merge (do đụng unique toàn cục) giờ
  resolve thẳng về A (bypass redirect); `effective_destination_id(A)` vẫn trả B → cùng một id cho
  hai "sự thật" khác nhau tùy code path — đúng loại drift mà 15.2b sinh ra để chặn.
- **Kịch bản kích hoạt**: merge `dst_ha-tay → dst_ha-noi`, rồi admin bấm "Activate" trên Hà Tây
  trong admin drawer (row còn tọa độ cũ) → 200 OK.
- **Fix** (service/router, không đổi schema): `set_status`/router từ chối `isActive=True` khi
  `merged_into_id IS NOT NULL` → 422 "cannot reactivate a merged destination"; đồng thời thêm predicate
  `merged_into_id.is_(None)` tường minh vào `search()` và cả 3 tầng `resolve()` để không dựa vào
  `is_active` làm proxy. (Tùy chọn hardening sau: CHECK `NOT (is_active AND merged_into_id IS NOT NULL)` — là
  đổi schema, để change request riêng.)
- **Test bắt buộc**: merge A→B → PATCH status A active → 422; dựng tay row `is_active=True, merged_into_id=B`
  → `search()` và `resolve()` (3 tầng) không bao giờ trả A.

### §1.2 H1 🟠 HIGH — Dedupe không fold `đ/Đ`: "Đông Á" ≠ "Dong A" lọt trùng ở cả supplier lẫn product
- **Vị trí**: `services/supplier_service.py::normalize_supplier_name` (~19–24);
  `services/product_service.py::normalize_product_title` (~28–33).
- **Cơ chế lỗi**: normalize dùng NFD + bỏ `Mn`. `Đ` (U+0110)/`đ` (U+0111) **không có** canonical
  decomposition → không bị strip. Probe thực thi: `'khach san đong a' ≠ 'khach san dong a'`,
  `'xe 16 cho đa nang' ≠ 'xe 16 cho da nang'`. `core/rules/destination_rules.remove_diacritics` xử lý
  đ/Đ đúng — nhưng supplier/product không dùng nó (bản copy thứ 3, thứ 4 của thuật toán).
- **Kịch bản kích hoạt**: tạo supplier "Khách sạn Đông Á" rồi "Khach san Dong A" → 2 row, unique
  `(tenant_id, name_normalized)` không bắt. Đây là chữ cái phổ biến nhất trong tên riêng Việt Nam.
- **Fix**: hợp nhất thành **một** helper pure `core/rules/text_normalize.py::normalize_name` (đúng lời hẹn
  15.2 §1.2 "không copy-paste thành 2 bản") tái dùng `remove_diacritics` của `destination_rules`;
  supplier/product import từ đó. Cần script backfill `name_normalized`/`title_normalized` một lần
  (data migration, không đổi schema) + rà trùng sau backfill.
- **Test bắt buộc**: golden `("Đông Á","Dong A")`, `("Hạ Long","Ha Long")`, `("  Đà  Nẵng ","da nang")` cho
  cả 2 module; test chống drift: `normalize_supplier_name is normalize_product_title` (cùng object).

### §1.3 H2 🟠 HIGH — Không kiểm tra tồn tại `destination_id` / `origin_destination_id` / `supplier_id`; SQLite chạy với FK enforcement TẮT → test suite mù FK, Postgres trả 500
- **Vị trí**: `services/product_service.py::create_product/update_product` (~72–154; chỉ validate
  `property_id`); `db/session.py::get_db` (~35–38, không `PRAGMA foreign_keys=ON`); tương tự
  `supplier_service.create_supplier` không kiểm `destination_id`.
- **Cơ chế lỗi**: trên SQLite (toàn bộ test suite + dev local) FK khai báo trong model là **inert** →
  `ProductCreateSchema(destination_id="dst_does_not_exist", ...)` persist thành công với FK treo (agent
  đã reproduce live). Trên Postgres cùng call → `IntegrityError` không ai catch → generic handler
  `main.py:1217` trả **500 `INTERNAL_ERROR`, `retryable: true`** — sai sự thật (retry mãi vẫn lỗi).
- **Kịch bản kích hoạt**: client gửi id destination cũ (cache stale sau merge) hoặc typo → SQLite: dữ
  liệu rác; PG: 500 thay vì 422.
- **Fix**: (a) service kiểm tồn tại qua hàm public `DestinationRepository.get` / `SupplierRepository.get_by_id`
  → `ProductValidationError` 422 (giữ đúng luật "không JOIN chéo module"); (b) **systemic**: bật
  `PRAGMA foreign_keys=ON` cho engine SQLite qua event listener `connect` trong `db/session.py` — ảnh
  hưởng toàn repo, chạy lại toàn bộ suite để lộ các FK treo tiềm ẩn ở module khác (ticket riêng).
- **Test bắt buộc**: id không tồn tại cho 3 FK → 422 (không 500); sau khi bật PRAGMA, test cố insert FK
  treo trực tiếp qua repository phải nhận `IntegrityError` trên SQLite.

### §1.4 H3 🟠 HIGH — Race dedupe / mọi `IntegrityError` → 500 "retryable" thay vì 409 (supplier & product)
- **Vị trí**: `services/supplier_service.py` (~58–71 create, ~84–90 rename), `routers/v2/suppliers.py` (chỉ
  catch `ValueError`); `services/product_service.py` + `routers/v2/products.py` (~56–64, ~87–97: chỉ
  catch `ProductConflictError`/`ProductValidationError`). Không có `except IntegrityError` ở bất kỳ tầng nào
  (grep 2 repository: rỗng), trong khi `main.py:8015, 9206` đã có pattern đúng.
- **Cơ chế lỗi**: check-then-insert (TOCTOU). Hai request cùng dedupe key song song đều qua pre-check,
  request 2 đụng unique index tại `flush()` → `IntegrityError` → 500 + session ở trạng thái lỗi.
- **Kịch bản kích hoạt**: double-submit form / 2 tab / seeding 15.8b chạy song song.
- **Fix**: wrap insert/update trong service: `except IntegrityError: await session.rollback(); raise
  <Conflict>Error` → 409 (mirror `main.py:9206`). Áp cho cả supplier lẫn product.
- **Test bắt buộc**: 2 create cùng key qua `asyncio.gather` → đúng một 201 + một 409, session vẫn dùng
  được cho request kế tiếp.

### §1.5 H4 🟠 HIGH — Pagination `total` bị cắt theo `limit` (supplier & product)
- **Vị trí**: `repositories/supplier_repository.py::list` (~46–49) và `repositories/product_repository.py::list`
  (~46–49): `stmt.limit(...)` rồi `return items, len(items)`.
- **Cơ chế lỗi**: `total` = số dòng của trang, không phải `COUNT(*)` theo filter → FE pager thấy đúng 1 trang.
- **Kịch bản kích hoạt**: 250 supplier active, `GET /api/v2/suppliers?limit=100` → `total: 100`.
- **Fix**: query `select(func.count()).select_from(...)` cùng filter (không limit) trả làm `total`.
- **Test bắt buộc**: seed > limit → `total` = số khớp thật; cả 2 module.

### §1.6 H5 🟠 HIGH — Search dùng term thô ILIKE lên cột đã normalize → gõ tiếng Việt có dấu không ra kết quả (supplier & product)
- **Vị trí**: `supplier_repository.py::list` (~37–45: `pattern=f"%{term}%"` lên `name_normalized`);
  `product_repository.py::list` (~43–45).
- **Cơ chế lỗi**: cột chứa `"diem den a dong"` (đã bỏ dấu), term `"Điểm"` không match dưới ILIKE
  (không Unicode folding). Đúng use case Vietnamese staff gõ tên hiển thị → 0 kết quả.
- **Kịch bản kích hoạt**: tạo "Điểm Đến Á Đông", search `?search=Điểm` → rỗng.
- **Fix**: normalize term bằng helper chung (H1) trước ILIKE (`%{normalize(term)}%`); spec 15.1 còn hứa
  search theo `contact_json.person` — hiện không có (M1).
- **Test bắt buộc**: round-trip có dấu → tìm thấy; cả 2 module.

### §1.7 H6 🟠 HIGH — `subcategory_note` chỉ validate trên payload: từ chối sai partial update **và** để lại note mồ côi (vi phạm 15.2 §1.5 rule 3)
- **Vị trí**: `schemas/v2/product.py::ProductUpdateSchema._validate_boundaries` (~97–106);
  `services/product_service.py::update_product` (~104–154) — `grep subcategory_note` = 0 lần ở service.
- **Cơ chế lỗi**: (a) PUT chỉ gửi `{subcategory_note}` cho product đang `other_*` → 422 sai vì
  `self.subcategory is None` trong payload; (b) PUT đổi `subcategory` từ `other_*` sang `hotel` mà không
  gửi note → note cũ **tồn tại** với combo không hợp lệ (agent reproduce live: `subcategory="hotel"`,
  `subcategory_note="Floating bungalow"`).
- **Fix**: chuyển validation vào service trên **merged state** (existing + updates) — cùng pattern
  `_validate_subcategory/_validate_property/_validate_origin` đã làm đúng; khi subcategory rời `other_*`
  → auto-clear note (hoặc 422 tường minh). Schema chỉ giữ check hình thức.
- **Test bắt buộc**: 2 ca trên; combo persisted luôn hợp lệ sau mọi PUT.

### §1.8 H7 🟠 HIGH — `core/kernel/ids.py` không phải uuid7: id = `ms_timestamp<<16 | counter process-local`, không randomness → trùng PK xuyên process là tất định, id đoán được
- **Vị trí**: `core/kernel/ids.py` (~14–35; docstring tự khai "no uuid7 dependency").
- **Cơ chế lỗi**: probe 2 process: `sup_01a06566caf30000`/`...0001` vs `sup_01a06566cb150000`/`...0001` —
  counter reset về `0000` mỗi process; hai process rơi cùng millisecond ⇒ **id giống hệt** (hàm tất định
  theo (ms, counter)). Bối cảnh thật: `uvicorn --workers N`, app + outbox worker container, seeding
  15.8b chạy song song, redeploy burst. Hệ quả: PK collision → `IntegrityError` → 500 trên **một row
  không liên quan** (không phải business conflict); ids đoán được (enumeration). Ảnh hưởng **mọi**
  module 15.x dùng `generate_id` (supplier→AP). Spec K6/15.1 §1.3 nói uuid7 — spec đang sai với thực tế.
- **Fix** (kernel — là ngoại lệ được phép vì đây là bug kernel, không phải feature): implement RFC 9562
  UUIDv7 thuần Python (48-bit ms + 74-bit `secrets.randbits`) — không cần dependency; giữ prefix + hex
  length hiện có để không breaking; hoặc tối thiểu trộn `secrets.randbits(16)`/PID vào low bits. Cập
  nhật spec K6 cho khớp.
- **Test bắt buộc**: cross-process (2 subprocess, ép cùng timestamp qua monkeypatch `time.time_ns`) → không
  trùng; sortable vẫn giữ; `test_kernel_ids` hiện tại chỉ single-process — không đủ.

### §1.9 M1 🟡 MEDIUM — Search supplier thiếu `contact_json.person` mà spec §1.5 hứa
- **Vị trí**: `supplier_repository.py::list` (~40–45) chỉ OR `name_normalized`, `legal_name`.
- **Fix**: thêm điều kiện JSON `person` (cần fallback SQLite/PG cho JSON_VARIANT — hoặc post-filter Python).
- **Test**: search theo tên người liên hệ ra đúng supplier.

### §1.10 M2 🟡 MEDIUM — Supplier map **mọi** `ValueError` → 409, kể cả "Unsupported currency" (phải 422)
- **Vị trí**: `services/supplier_service.py:106` raise `ValueError`; `routers/v2/suppliers.py:57,88` catch → 409.
- **Fix**: tách typed errors `SupplierConflictError`/`SupplierValidationError` như product đã làm; 422 cho validation.
- **Test**: currency `XYZ` → 422 (create + update).

### §1.11 M3 🟡 MEDIUM — `title` toàn khoảng trắng qua schema, persist thành `""` và phá dedupe
- **Vị trí**: `schemas/v2/product.py:52` (`min_length=1` trước strip); service strip sau (~95, ~130).
- **Fix**: `field_validator` strip rồi kiểm rỗng → 422; áp cho supplier `name` tương tự.
- **Test**: `"   "` → 422 create + update.

### §1.12 M4 🟡 MEDIUM — `origin_destination_id == destination_id` không bị chặn
- **Vị trí**: `services/product_service.py::_validate_origin` (~179–184).
- **Fix**: thêm `origin == destination → ProductValidationError`.
- **Test**: "Hà Nội → Hà Nội" → 422.

### §1.13 M5 🟡 MEDIUM — FE `DestinationSelect` không nhận/forward `types`/`parentId` → §5.3 (chọn theo cây, origin/destination picker thu hẹp) chưa wiring
- **Vị trí**: `components/destination/DestinationSelect.tsx` (gọi `useDestinationSearch(query)` không options);
  `types.ts::DestinationSelectProps` không có 2 prop; `ProductManageDrawer.tsx:360,379,400` không thể truyền.
  Hook đã hỗ trợ (`useDestinationSearch.ts:21–34`). Backend default loại country/region nên dropdown
  itinerary vẫn an toàn.
- **Fix**: thêm `types?`/`parentId?` vào props, forward vào hook; drawer truyền `types=["province","city","sub_zone"]`.
- **Test**: FE test props plumbing; kiểm tay origin picker không hiện country.

### §1.14 M6 🟡 MEDIUM — Vòng lặp chống cycle trong `merge()` là dead code; chain depth 3 không bao giờ đạt được
- **Vị trí**: `destination_repository.py` (~311–316 đã từ chối target đã merge → loop ~318–325 luôn break vòng 1).
- **Cơ chế**: không khai thác được hôm nay, nhưng che giấu thật nếu sau này nới luật re-merge; `test_destination_merge`
  chỉ test `effective_destination_id` với row chèn tay, chưa test chain qua chính `merge()`.
- **Fix**: xóa loop + constant, HOẶC cố ý hỗ trợ re-target rồi test depth thật. Quyết định tường minh, không để lửng.

### §1.15 M7 🟡 MEDIUM — Thuật toán normalize tồn tại 4 bản (supplier, product, destination-repo, destination_rules) với ngữ nghĩa khác nhau
- **Vị trí**: 4 hàm liệt kê ở H1; `repositories/destination_repository.py::normalize_destination` (casefold + `-`→space,
  **không** bỏ dấu) khác `destination_rules.normalize_destination_text` (bỏ dấu) → tầng 1 và tầng 2 của
  `resolve()` dùng 2 chuẩn hóa khác nhau (pre-existing, không phải Track 1 mới tạo — ghi để có chủ đích).
- **Fix**: hợp nhất theo H1; destination alias giữ ngữ nghĩa riêng nếu cố ý — thì ghi docstring lý do.

### §1.16 M8 🟡 MEDIUM — `PATCH /status` nhận `dict[str, bool]` thô (supplier & product), lệch contract error envelope
- **Vị trí**: `routers/v2/suppliers.py` (~92–101), `routers/v2/products.py` (~100–116).
- **Fix**: `StatusUpdateSchema(is_active: bool = Field(alias="isActive"))` → `fieldErrors[].path` chuẩn.

### §1.17 M9 🟡 MEDIUM — Seed destination vẫn duplicate nguyên văn ở 2 nơi (`repositories/destination_repository.py:463`, `main.py:7235`) và chạy gần như mỗi request
- Đã diff: **chưa** drift sau 15.2b, nhưng là nợ đã ghi ở 15.2b §2.1 — mỗi lần thêm cột là 2 chỗ sửa; seeding per-request là hazard hiệu năng/đua write khi nhiều worker.
- **Fix**: `main._seed_destination_catalog` gọi thẳng hàm repository; cân nhắc seed một lần lúc startup/migration.

### §1.18 L1 🟢 LOW — ILIKE không escape `%`/`_` (3 repository) · L2: `actor_id` fallback `"unknown"` khi principal không có email (`routers/v2/suppliers.py:21`, products tương tự) — mất attribution K4 âm thầm · L3: `countryCode` chỉ uppercase, không kiểm ISO 3166 · L4: `category_attributes` key snake_case (15.2 §1.5 rule 6) không enforce regex · L5: `core/kernel/money.py` import `core.rules.pricing_rules` — vi phạm chữ "kernel không import business module" nhưng là **ngoại lệ đã khai báo** ở 15.3 chốt #5 (ghi để spec K1 nói rõ) · L6: `principal: EditorPrincipalDep = None` default None trong signature router (smell, không lỗi).

---

## 3. §1.7 Danh sách test nợ theo spec (Bổ sung cùng đợt fix)

- **Concurrency**: 2 create cùng dedupe key song song (supplier, product) → 201 + 409, không 500 (H3).
- **Cross-process id**: 2 subprocess ép cùng `time_ns` → id khác nhau (H7); giữ test sortable.
- **FK tồn tại**: 3 FK của product + `suppliers.destination_id` trỏ id không tồn tại → 422 trên cả SQLite (sau PRAGMA) lẫn PG (H2).
- **Circular / merged redirect**: merge A→B rồi PATCH status A → 422 (C1); row `is_active=True + merged_into_id` không bao giờ lộ qua `search`/`resolve` 3 tầng; chain merge qua chính `merge()` API (M6); alias-collision skip đúng và không để partial state.
- **Dedupe golden `đ/Đ`** cho cả 2 module + test "cùng một hàm normalize" (H1/M7).
- **Pagination** `total` > limit (H4) · **search có dấu** round-trip (H5) · search `contact_json.person` (M1) · wildcard `%`/`_` (L1).
- **subcategory_note**: PUT chỉ note với `other_*` đang có → 200; đổi subcategory rời `other_*` → note bị clear/422 (H6).
- **Validation edge**: title whitespace (M3); origin == destination (M4); currency lạ → 422 không 409 (M2); nested dict/list trong `category_attributes` → 422.
- **Idempotency replay**: Track 1 không có POST tiền nên không có Idempotency-Key theo spec — ghi nhận đúng, không nợ.
- **HTTP-layer**: `POST .../merge` qua router + auth `require_quote_admin` (hiện chỉ test gọi `main._merge_destination` trực tiếp); media slug-chain freeze 422 qua PUT (spec 15.2b §7 bắt buộc, hiện **không có** test nào); `GET /destinations` mặc định loại `country/region`; `parentId` filter.
- **Migration** up/down PG + SQLite cho `_36/_37/_38` không có trong suite tự động (chỉ thủ công theo exit gate).

## 4. §1.8 Exit Gate của Track 1

1. **C1 + H1→H7 fix** + toàn bộ test bắt buộc trong từng mục §1.1–§1.8 và test nợ §3 xanh. Riêng H1 kèm
   backfill `name_normalized`/`title_normalized` và báo cáo số cặp trùng phát hiện sau backfill; H7 kèm
   cập nhật spec K6 (15-modular §Shared Kernel) cho khớp thực tế.
2. **M1→M9 fix** (hoặc ticket riêng có lý do — mặc định fix cùng đợt; M6 và M9 cần **quyết định** tường
   minh ghi vào doc, không để dead code/duplicate lửng). L1–L6 tùy chọn, khuyến nghị làm L1/L2 vì rẻ.
3. Toàn bộ suite Track 1 + `test_v2_api_manifest_contract` + `test_ssot_integrity` xanh; **migration không
   đổi** (mọi fix ở service/schema/pure-rules/kernel-ids; nếu quyết định thêm CHECK constraint cho C1 thì
   là migration additive riêng, review lại trước); `PRAGMA foreign_keys=ON` bật xong phải chạy **toàn bộ**
   suite repo (không chỉ Track 1) và xử lý mọi FK treo lộ ra trước khi coi Track 1 đóng.

---

## 5. Re-review sau đợt fix (2026-09-03) — commit `3946aaf` (+ phần product/destination repo đã vào `8339ed6`)

> Phương pháp: đối chiếu từng finding §2 với code HEAD, chạy lại suite Track 1 (**122 passed**, tăng từ 94),
> chạy **toàn bộ** suite backend (641 passed / **1 failed**, xem §5.4), `npm run lint` chain FE xanh, và
> thực thi probe độc lập cho những fix dễ "đóng hụt" (FK enforcement, merged-destination, id collision).
> Không sửa code/test/migration trong lượt re-review.

### 5.1 Đã đóng và xác minh ✅

| ID | Xác minh |
| :-- | :-- |
| C1 | `set_status` từ chối reactivate khi `merged_into_id` (→ `DestinationReactivationError` → 422); `search()` + 3 tầng `resolve()` có predicate `merged_into_id.is_(None)` tường minh; test merge/crud có ca này. PUT `_save_destination` không chạm `is_active` → không có đường vòng. |
| H1/M7 | `core/rules/text_normalize.normalize_name` (đ/Đ-aware, tái dùng `remove_diacritics`); `normalize_supplier_name is normalize_product_title is normalize_name`; `normalize_destination` giữ ngữ nghĩa riêng **có docstring lý do** (đúng yêu cầu M7). Backfill script `scripts/backfill_name_normalization.py` (report-only, không auto-merge) — commit ghi 0 collision trên dev DB. |
| H3 | `except IntegrityError → rollback → *ConflictError` ở create/update cả 2 module; test race (mock pre-check stale) cho **cả** supplier lẫn product, kèm kiểm tra session còn dùng được. |
| H4 | `COUNT(*)` trên subquery cùng filter, cả 2 repo; test `total > limit`. |
| H5/L1 | term đi qua `normalize_name` trước ILIKE, escape `%`/`_`/`\`; `legal_name` và `contact_json.person` (M1) dùng raw term — hợp lý vì 2 cột này không normalize. |
| H6 | Validate trên merged state; chọn **422** (không auto-clear) khi rời `other_*` mà còn note — chấp nhận được, có 3 test (note-only PUT → 200; rời other_* giữ note → 422; rời + clear → 200). |
| M2/M3/M4/M8 | Typed `SupplierValidationError`/`SupplierConflictError`; blank name/title → 422 ở schema; origin == destination → 422; `*StatusUpdateSchema(is_active alias isActive)`. |
| M5 | `DestinationSelect` nhận/forward `types`/`parentId`; `ProductManageDrawer` truyền `ORIGIN_DESTINATION_PICKER_TYPES = province/city/sub_zone` ở 3 picker; `npm run lint` chain xanh. |
| M6 | Loop dead-code xóa, **quyết định ghi tường minh** trong comment (không hỗ trợ re-target). |
| M9 (½) | `main._seed_destination_catalog` gọi thẳng hàm repository — hết duplicate. |

### 5.2 Defect còn lại / mới lộ ra (BẮT BUỘC trước khi đóng Track 1)

#### §5.2.1 R-C1 🔴 CRITICAL (MỚI, có sẵn từ 15.2b) — `DestinationRepository.create()` INSERT alias **trước** catalog row → `POST /api/v2/destinations` thất bại bằng FK violation trên Postgres
- **Vị trí**: `repositories/destination_repository.py::create` (~134–176): `session.add(item)` rồi `session.add(DestinationAlias(...))` ×N rồi **một** `flush()`.
- **Cơ chế**: `DestinationCatalog` ↔ `DestinationAlias` **không có `relationship()`** → unit-of-work không biết phụ thuộc và sắp mapper theo `_sort_key` = `module.ClassName` → `DestinationAlias` < `DestinationCatalog` theo bảng chữ cái → alias luôn được INSERT trước. Tất định (đã chạy 8 `PYTHONHASHSEED` khác nhau: 8/8 FAIL). `aliases` luôn ≥ 2 phần tử (canonical name + slug) nên **mọi** lần tạo đều dính.
- **Bằng chứng**: (a) SQLite + `PRAGMA foreign_keys=ON`: `IntegrityError: FOREIGN KEY constraint failed` tại `INSERT INTO destination_aliases`, không có `INSERT INTO destination_catalog` nào trước đó trong log engine; (b) **Postgres thật** (container `app`, flush rồi rollback, không ghi): `asyncpg.ForeignKeyViolationError` trên `destination_aliases`; (c) checkout `643405e` (commit 15.2b) chạy cùng probe → **FAIL** → lỗi có sẵn, không phải regression của đợt fix.
- **Vì sao chưa ai thấy**: `test_destination_catalog_crud` POST qua API nhưng chạy trên engine SQLite riêng **không bật FK** (chính là H2); seed dùng `upsert()` và *tình cờ* sống sót vì `upsert` gọi `session.scalar(select(DestinationAlias)...)` giữa hai lần `add` → **autoflush** đẩy catalog row xuống trước. `update()`/`merge()` thao tác trên row đã tồn tại nên không dính. Audit gốc §1 cũng bỏ sót vì cùng chạy trên suite FK-blind — đây là minh chứng tại sao exit gate #3 (chạy suite với FK bật) không được phép bỏ.
- **Fix** (repo, không đổi schema): `await self.session.flush()` ngay sau `self.session.add(item)` trước khi thêm alias (rẻ nhất, mirror hành vi autoflush của `upsert`), **hoặc** khai báo `relationship("DestinationAlias", cascade=...)` để UOW tự sắp thứ tự. Rà cùng pattern cho mọi repo có bảng con không `relationship()` (grep `session.add(` liên tiếp 2 model khác bảng trước 1 `flush()`).
- **Test bắt buộc**: POST destination (có alias) trên engine SQLite **có PRAGMA** → 201; và một lượt PG thủ công theo exit gate.

#### §5.2.2 R-H1 🟠 HIGH — H2 "systemic" chỉ đóng một nửa: PRAGMA chỉ nằm trong `db/session.get_session_factory`; ~30 file test tự `create_async_engine` → suite vẫn FK-blind, exit gate #3 **chưa** được thực thi
- **Bằng chứng**: `grep -l create_async_engine tests/` = 30 file; chỉ `tests/test_db_session_foreign_keys.py` đi qua `get_session_factory`. R-C1 lọt qua `test_destination_catalog_crud` là hệ quả trực tiếp.
- **Fix**: tách listener thành hàm public `db/session.py::install_sqlite_foreign_keys(engine)` và gọi trong **một** helper test dùng chung (`tests/_db.py::make_test_engine()`), thay thế 30 chỗ tạo engine; sau đó chạy toàn bộ suite và xử lý mọi FK treo lộ ra (kỳ vọng ≥1: R-C1).
- **Test bắt buộc**: meta-test khẳng định mọi engine test có `PRAGMA foreign_keys = 1`.

#### §5.2.3 R-H2 🟠 HIGH — FK "tồn tại" ≠ "còn sống": `_validate_destination_exists` dùng `DestinationRepository.get()` (= `session.get`, không lọc) → product/supplier vẫn gắn được vào destination **đã merge** hoặc **inactive**
- **Vị trí**: `services/product_service.py:241`, `services/supplier_service.py:127`.
- **Cơ chế**: đúng kịch bản kích hoạt của H2 gốc ("client gửi id destination cũ, cache stale sau merge") giờ trả **201** thay vì 422; `merge()` cố ý không repoint FK (test `test_merge_does_not_repoint_product_foreign_keys`) nên product mới tạo trỏ vào hub chết, không bao giờ xuất hiện dưới `resolve()`/`search()`.
- **Fix**: sau `get()`, từ chối khi `merged_into_id IS NOT NULL` (422, message kèm `effective_destination_id` để FE tự sửa) và khi `is_active=False`; áp cho `destination_id`, `origin_destination_id` (product) và `destination_id` (supplier).
- **Test bắt buộc**: merge A→B → create product/supplier với `destination_id=A` → 422; A inactive → 422; B → 201.

#### §5.2.4 R-M1 🟡 MEDIUM — H7 chỉ giảm xác suất, không loại bỏ; spec K6 vẫn nói UUIDv7 (exit gate #1 yêu cầu cập nhật — **chưa làm**)
- **Thực tế**: id = 48-bit ms + 16-bit counter seed ngẫu nhiên **một lần mỗi process**, sau đó tuần tự. Trong cùng 1 ms: 2 process trùng với xác suất 2⁻¹⁶/cặp; mô phỏng 20k lượt: 4 worker × 10 id/ms ≈ 0.14 %, 8 worker × 50 id/ms ≈ **4 %** mỗi ms có tải chung (seeding 15.8b song song, bulk import). Trong một process id vẫn đoán được (+1). Test cross-process hiện có chỉ chứng minh "2 process seed khác nhau không trùng", không chứng minh xác suất.
- **Fix**: quyết định tường minh một trong hai và ghi vào 15-modular §K6: (a) UUIDv7 thật (48-bit ms + 74-bit random, 32 hex) — đổi độ dài id, `String(64)` vẫn đủ, sửa test length; hoặc (b) giữ 16 hex nhưng chấp nhận rủi ro có số liệu trên và ghi rõ giới hạn "không chạy > N worker ghi đồng thời". Không để spec nói uuid7 khi code không phải uuid7.

#### §5.2.5 R-M2 🟡 MEDIUM — `await self.session.rollback()` bên trong service (H3) kết thúc transaction của **caller**
- **Vị trí**: 4 chỗ trong `supplier_service.py` / `product_service.py`.
- **Cơ chế**: 15.8 `services/ingestion/commit_service.py` gọi `create_supplier` rồi `create_product` trong **cùng** transaction; khi product đụng unique → service rollback → supplier vừa tạo biến mất; hôm nay vẫn an toàn vì router ingestion map `CommitError` → HTTP lỗi **không** commit (test `test_commit_mid_failure_rolls_back_all_writes`). Nhưng bất kỳ caller tương lai nào `except *ConflictError: continue` sẽ mất dữ liệu âm thầm.
- **Fix**: dùng `begin_nested()` (SAVEPOINT) quanh insert/update như `BookingRepository.insert_*` đã làm, rollback chỉ savepoint; service không được gọi `session.rollback()`.

#### §5.2.6 R-M3 🟡 MEDIUM — M9 nửa còn lại: seed vẫn chạy ở 6 call site trong `main.py` gần như mỗi request; chưa có quyết định ghi lại.

#### §5.2.7 L (tùy chọn) — L2 (`actor_id="unknown"`), L3, L4, L6 chưa động; test race dùng `AsyncMock` cho pre-check thay vì concurrency thật (chấp nhận được, ghi nhận).

### 5.3 Hygiene lịch sử
- Fix H4/H5 cho `product_repository.py` và C1/M6/M7 cho `destination_repository.py` nằm trong commit `8339ed6` ("close track 2 rates and costing audit") chứ không phải `3946aaf` như message mô tả — không sai code, nhưng bisect sau này sẽ lệch.

### 5.4 Trạng thái suite
- Track 1 (14 file): **122 passed**. FE `npm run lint` chain: xanh.
- Toàn bộ backend (`pytest tests`, bỏ `test_track3_postgres_concurrency.py` cần PG): **641 passed, 1 failed** —
  `tests/test_ingestion_corpus.py::test_corpus_case_matches_manifest_expectations[hotel_seasonal_01.txt]`
  (supplier không được extract). Thuộc Track 4 (commit `74c6411`), `ingest_parser` không import `text_normalize`
  → **không** do đợt fix Track 1, nhưng suite đỏ thì không được nghiệm thu bất kỳ track nào.

### 5.5 Exit gate Track 1 (cập nhật)
1. **R-C1** fix + test qua engine có PRAGMA + 1 lượt PG thủ công `POST /api/v2/destinations` → 201.
2. **R-H1** helper engine test dùng chung có FK bật → chạy **toàn bộ** suite, xử lý mọi FK treo lộ ra.
3. **R-H2** liveness check cho 3 FK; **R-M1** quyết định + cập nhật §K6; **R-M2** SAVEPOINT thay `session.rollback()`; **R-M3** quyết định seed.
4. Sửa `test_ingestion_corpus[hotel_seasonal_01]` (Track 4) để suite xanh toàn bộ; migration **không đổi** (mọi fix ở repo/service/test).
