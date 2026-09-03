# Audit Implementation — Track 3: Commercial Wiring & Operations Board Defect Log

> **Loại tài liệu**: Biên bản audit đối kháng (adversarial) của Track 3 — Plan 15.5 (Apply Pricing) và
> Plan 15.6 (Booking Operations) — đối chiếu source code tại `HEAD c0943d7` (2026-09-03).
> Working tree lúc audit đang có edit dở của Track 2 (`repositories/costing_repository.py` chuyển
> `rollback()` → `begin_nested()`, `services/booking_service.py::_mirror_service_line_status` gọi
> `update_line_booking_status`). Các edit đó **không** chạm `apply_pricing`, CAS booking, counter, header
> update — mọi defect dưới đây tái hiện được trên cả HEAD lẫn working tree.
>
> Nguyên tắc: không suy đoán. Mỗi defect C/H đều được kích hoạt bằng probe script chạy trên SQLite
> (cùng engine với test suite) hoặc được chứng minh bằng trace call-graph tới dòng code cụ thể.

---

## 1. Subsystem Scope & Verified Call-Graph Perimeter

### 1.1 Anchor specs
- `docs/plans/refactor-tech-stack/15.5-apply-pricing.md` — chốt #3 (đi qua pipeline facts), #4 (nguyên tử
  3-trong-1), #5 (dual CAS), #6 (Idempotency K8), #9 (chỉ sheet đã neo quotation).
- `docs/plans/refactor-tech-stack/15.6-booking-operations.md` — T3/R3 (frozen terms, copy-on-confirm),
  state machine `to_request → requested → confirmed → delivered | cancelled`, guard "line đã book không sửa/xoá",
  counter `BK-/VC-{YYYY}-{seq}`, urgency theo "today" của destination tz.
- `docs/plans/refactor-tech-stack/15-modular-tour-ops-brainstorm.md` — K5 (audit append-only), K8 (idempotency),
  ranh giới costing ↔ facts.

### 1.2 Entrypoints đã quét (đọc trọn)
| Lớp | File |
| :-- | :-- |
| Commercial apply | `db/models/costing_application.py`, `services/costing_service.py::apply_pricing/_to_workbench/_guard_booked_line`, `schemas/v2/costing.py`, `routers/v2/costing.py` |
| Bookings & ops | `db/models/booking.py`, `repositories/booking_repository.py`, `services/booking_service.py`, `schemas/v2/booking.py`, `routers/v2/bookings.py` |
| Pure rules & bridge | `core/rules/booking_rules.py`, `core/rules/costing_rules.py`, `api/runtime.py`, `services/facts_contract.py` |
| Migrations | `alembic/versions/20260903_41_costing_applications.py`, `alembic/versions/20260904_42_bookings.py` |

### 1.3 Call-path ngoài anchor đã trace end-to-end
- **Facts bridge**: `routers/v2/costing.py::apply_pricing` → `CostingService.apply_pricing` →
  `api.runtime.apply_pricing_option` → `main._apply_costing_pricing_option` (main.py ~3864–4010) →
  `QuotationRepository.get_version_facts / get_latest_quotation_request / create_quotation_request`,
  `QuotationDocumentRepository.save_current_document` (SQL CAS `WHERE revision = :expected`, xác nhận là guard
  DB-level thật), `append_document_revision`, `ContentDraftRepository.mark_stale`. Không có `commit()` bên
  trong callback → 3-trong-1 nằm trong một transaction, commit ở router. **Đạt chốt #4** (probe
  `test_apply_pricing_outbox_failure_rolls_back_everything` xanh).
- **Đường ghi facts của sale** (`routers/v2/quotation_facts.py::put_quotation_facts_v2`) và **đường tạo
  quotation** (`main.py` ~5152–5154, `services/quote_request_service.py` ~780–805,
  `services/quotation_version_application_service.py::create_successor`) — để đối chiếu nguồn facts mà apply
  đọc/ghi (xem C1, C2).
- **Outbox**: `services/outbox_service.py::emit_event` chỉ `add + flush`, không commit. Notification service
  hiện **không có consumer** cho `costing.applied` / `booking.*` ngoài mirror enum trong
  `notification/domain/events.py` (relay forward rồi bỏ qua) — không phải defect Track 3, ghi nhận phạm vi.
- **Finance consumer** của snapshot booking: `services/ap_reconciliation_service.py` (~272–300) dùng
  `booking_line.cancel_penalty_minor` làm `expected_cost_minor` cho invoice line `penalty`;
  `core/rules/finance_rules.py::suggest_penalty_expected`.
- **Counter**: `BookingRepository.next_business_code_sequence` (UPDATE…RETURNING + insert-fallback + `rollback()`).
- **Ownership**: `api/dependencies.py::require_owned_v2_quotation`; router bookings dùng
  `_enforce_quotation_ownership_for_booking` cho detail/mutation, board list không lọc.

### 1.4 Baseline test suite (read-only run)
```
PYTHONPATH=. pytest tests/test_apply_pricing_service.py tests/test_apply_pricing_api.py \
  tests/test_booking_service.py tests/test_booking_api.py tests/test_booking_rules.py \
  tests/test_v2_api_manifest_contract.py tests/test_v2_error_envelope.py -q
→ 54 passed, 25 warnings
```
Suite xanh **không** chứng minh Track 3 chạy được trên dữ liệu thật: fixture của
`test_apply_pricing_service.py::_create_test_quotation` tạo quotation **không có** `quotation_family_id` và
**không có** `quotation_version_facts` — hai thuộc tính mà mọi quotation production đều có (C1, C2).

### 1.5 Probe đã chạy (scratchpad, không ghi vào repo)
| Probe | Kết quả |
| :-- | :-- |
| P1 apply trên quotation có `quotation_family_id` | `CostingConflictError: Facts are immutable for a business quotation version.` |
| P2 apply khi có `quotation_version_facts` + sale đã sửa facts (request row mới) | request mới nhất bị **rewind về V0** (itinerary "Day 1 V0", label "V0 label"), `version_facts` vẫn 240000 trong khi document/request 100000, `drift.has_drift=False` |
| P3 apply 2 lần không Idempotency-Key | 2 application rows, facts revision 2 → 3 |
| P4 2 session confirm cùng line, cùng `base_booking_revision`, key khác | **Cả hai thành công**: VC-2026-0001 và VC-2026-0002, DB giữ VC-0002, 2 event `booking.line.confirmed` với 2 voucher khác nhau |
| P5 `PUT /bookings/{id}` `status=cancelled` rồi `POST /bookings` mới | header cancelled, line vẫn `to_request`, 0 event `booking.cancelled`; create mới → `BookingSlotTakenError` thoát khỏi service (500) |
| P6 line `delivered` + `cancel_booking` + tạo booking mới | line vẫn `delivered` (active theo partial index) → create mới `BookingSlotTakenError` (500), quotation không thể book lại vĩnh viễn |
| P7 `PUT` header `status=active` trên booking đã cancel khi đã có booking active khác | raw `IntegrityError` (500) |
| P8 line không có `service_date` | request_by/penalty_free/balance_due = None, urgency None, không lên board overdue; cancel → penalty **100%** sell |

---

## 2. Defect Log (BẮT BUỘC trước khi nghiệm thu)

### §3.1 C1 🔴 CRITICAL — Apply Pricing chết trên mọi quotation production (guard `quotation_family_id`)
- **Vị trí**: `main.py::_apply_costing_pricing_option` (~dòng 3889–3892); đối chiếu
  `main.py` ~5152 (`quotation_family_id=quotation_id, business_version=1`),
  `services/quote_request_service.py` ~787 (`quotation_family_id=quotation_id`),
  `services/quotation_version_application_service.py` ~130 (successor kế thừa family id).
- **Cơ chế lỗi**: callback facts-apply raise `CostingConflictError("Facts are immutable for a business quotation
  version")` khi `quotation.quotation_family_id` truthy. Cả **ba** đường tạo quotation V2 hiện hành đều gán
  `quotation_family_id` (manual create, handoff từ request, tạo version). Kết quả: `POST
  /costing-sheets/{id}/apply-pricing` trả 409 `REVISION_CONFLICT` recovery `reload` cho **100 %** quotation
  thật — FE reload xong vẫn 409, sale không bao giờ áp được giá. Toàn bộ chuỗi chứng từ `costing_applications`
  + event `costing.applied` (Exit Gate 15.5 #1, #6) là chết trên production. Test suite không bắt vì fixture
  tạo quotation "trần" không family id.
- **Kịch bản kích hoạt**: Probe P1 — tạo quotation theo đúng shape của `main.py:5152` → attach sheet → apply
  với đúng cả hai revision → 409.
- **Fix** (service/callback, không đổi schema): quyết định sản phẩm cần chốt rõ, hai lựa chọn hợp lệ:
  1. (Khuyến nghị) Bản version **draft** (`quotation.status == "draft"`, chưa publish) được coi là mutable
     cho apply: đổi guard thành `if quotation.quotation_family_id and quotation.status != "draft"`; đồng bộ
     cùng guard cho `put_quotation_facts_v2` để hai cửa ghi facts (chốt 15.5 Exit Gate #2) cùng luật.
  2. Nếu giữ "immutable per version": apply phải đi qua
     `QuotationVersionApplicationService.create_successor` (tạo version mới với option đã patch), application
     row ghi `quotation_id` của successor, response trả `quotation_id` mới để FE điều hướng. Sheet phải
     re-attach sang successor (sheet slot partial-unique theo quotation_id).
  Dù chọn hướng nào, fixture test phải tạo quotation **đúng shape production** (family id + version_facts).
- **Test bắt buộc**: `test_apply_pricing_service.py::test_apply_pricing_on_family_quotation_draft_head` —
  quotation có `quotation_family_id`, `business_version=1`, `status="draft"`, có `quotation_version_facts`;
  apply phải 200, tạo application row, bump facts revision. Thêm case `status="published"` → 409 (nếu chọn
  hướng 1). Fixture chung `_create_test_quotation` chuyển sang shape production.

### §3.2 C2 🔴 CRITICAL — Apply đọc facts từ `quotation_version_facts` nhưng ghi vào `quotation_requests` → rewind facts + Facts tab lệch brochure + drift mù
- **Vị trí**: `main.py::_apply_costing_pricing_option` (~3906–3909: `snapshot = version_facts.canonical_facts_json
  if version_facts else request_snapshot.request_json`; ~3990: chỉ `create_quotation_request`, không cập nhật
  version_facts); `services/costing_service.py::_to_workbench` và nhánh replay của `apply_pricing` (đọc drift/
  pricing_options từ `get_latest_quotation_request().request_json`);
  `services/booking_service.py::_snapshot_quotation_facts` (~536) đọc `get_version_facts`.
- **Cơ chế lỗi**: Track 3 dùng **ba** nguồn facts không đồng bộ:
  - apply **đọc** `quotation_version_facts.canonical_facts_json` (snapshot lúc tạo, không bao giờ được cập
    nhật bởi PUT facts lẫn apply);
  - apply **ghi** document + `quotation_requests` row mới;
  - drift/replay **đọc** `quotation_requests` row mới nhất.
  Hệ quả với quotation có version_facts (mọi quotation production, một khi C1 mở):
  (a) mọi chỉnh sửa facts nằm ở request rows (itinerary, label, per-person, conditions…) bị **rewind về
  snapshot lúc tạo** rồi ghi đè lên document — mất dữ liệu thầm lặng, `_preserve_content_owned_values` chỉ
  giữ copy content-owned; (b) `GET /quotations/{id}/facts` (ưu tiên version_facts, `routers/v2/quotation_facts.py:64`)
  vẫn hiện giá cũ trong khi brochure đã đổi — vi phạm 15.5 §2.3 "một sự thật ở cả hai tab"; (c) drift so
  option trong request row (vừa được apply ghi) nên báo `has_drift=False` dù Facts tab và version_facts lệch.
  Booking header snapshot (`party_label_snapshot`, `travel_start/end_date`) cũng lấy từ version_facts → lệch
  ngày/đoàn nếu sale đã đổi facts sau khi tạo.
- **Kịch bản kích hoạt**: Probe P2 — quotation có version_facts (opt_1 = 240000, itinerary "V0") + request
  row mới (sale sửa: 300000, "EDITED") → apply sell 100000 → request mới nhất: itinerary "Day 1 V0", label
  "V0 label", 100000; version_facts: 240000; drift: `has_drift=False`.
- **Fix** (callback + service, không đổi schema): chốt **một** SSOT đọc/ghi cho facts trong callback:
  đọc đúng nguồn mà `GET /facts` trả (`version_facts` nếu có), và sau khi patch **ghi lại cùng nguồn** trong
  cùng transaction: cập nhật `QuotationVersionFacts.canonical_facts_json/resolved_facts_json/facts_hash` (thêm
  `QuotationRepository.update_version_facts`) đồng thời vẫn `create_quotation_request` để giữ lịch sử. Drift
  (`_to_workbench`) và replay đọc từ cùng helper `_load_current_facts(quotation_id)` thay vì
  `get_latest_quotation_request`. Nếu product chốt version_facts là bất biến → bắt buộc đi hướng C1-2
  (successor). `BookingService._snapshot_quotation_facts` dùng cùng helper.
- **Test bắt buộc**: (1) quotation có version_facts + request row đã sửa → apply → itinerary/label/per-person
  của request row **được giữ**, chỉ `group_total/currency/label(option đích)` đổi; (2) sau apply,
  `GET /facts` và document cùng giá; (3) sale sửa tay option qua PUT facts sau apply → drift
  `commercial_modified_since_apply=True` (hiện test drift chỉ chạy trên fixture không version_facts).

### §3.3 C3 🔴 CRITICAL — Booking CAS chỉ ở Python: lost update, hai voucher cho một line, hai event `booking.line.confirmed`
- **Vị trí**: `services/booking_service.py::_check_revision` (~408) so sánh in-memory;
  `repositories/booking_repository.py::update_line/update_header/insert_line/cancel_all_open_lines`
  (`booking.booking_revision += 1` rồi `flush()` — UPDATE không có `WHERE booking_revision = :expected`);
  `transition_line` (~222–259) validate `line.status` in-memory, mint voucher trước khi ghi.
- **Cơ chế lỗi**: khác `CostingRepository._bump_revision_guarded`, booking không có CAS SQL. Hai request
  cùng `base_booking_revision` (hai ops cùng màn hình, hoặc retry với key khác) đều qua `_check_revision`
  trên object đã load, `validate_transition` chạy trên `line.status` cũ, cả hai mint `VC` (counter row lock
  serialize counter nhưng không serialize aggregate), UPDATE cuối ghi đè: voucher/supplier_ref của người sau
  thắng, voucher người trước thành **mồ côi** nhưng đã phát ra outbox → Finance/AP (`get_line_by_voucher_ref`)
  match sai hoặc không match; `confirmed_at`, `deposit_due_date` bị ghi hai lần. Với `cancelled` tương tự:
  hai penalty, hai event `booking.line.cancelled` (double-count penalty trong 15.9). Không phụ thuộc isolation
  level — READ COMMITTED của PG cho phép y hệt.
- **Kịch bản kích hoạt**: Probe P4 — session A và B load booking rev 1, A confirm (key ka) commit, B confirm
  (key kb, base rev 1) → B thành công; DB: `VC-2026-0002`/supplier_ref B; outbox: 2 event với
  `VC-2026-0001` và `VC-2026-0002`.
- **Fix** (repository, không đổi schema): thêm `BookingRepository._bump_revision_guarded(booking,
  expected_revision)` = `UPDATE bookings SET booking_revision = :exp+1, updated_at = now WHERE id = :id AND
  booking_revision = :exp` (`synchronize_session=False`, `rowcount != 1` → `BookingRevisionRaceError` → 409).
  Mọi write path (insert_line, update_line, update_header, cancel_all_open_lines) gọi guard **trước** flush;
  `transition_line` mint voucher **sau** khi guard thành công (row lock giữ tới commit) và re-validate
  `line.status` sau `session.refresh(line)`. Service map `BookingRevisionRaceError` → `BookingConflictError`.
- **Test bắt buộc**: `test_booking_service.py::test_concurrent_confirm_second_writer_gets_409` (hai session,
  cùng base revision, key khác) → đúng 1 voucher, 1 event; `test_concurrent_cancel_single_penalty`; probe
  P4 làm regression.

### §3.4 H1 🟠 HIGH — `PUT /bookings/{id}` cho phép `status=cancelled|active` bypass `cancel_booking`: lines sống mãi, không event, không mirror, và mở slot gây 500
- **Vị trí**: `schemas/v2/booking.py::BookingHeaderUpdateSchema.status` (~33);
  `services/booking_service.py::update_header` (~197–198); `create_booking` (~167–169, vòng `insert_line`
  không bắt `BookingSlotTakenError`); `repositories/booking_repository.py::update_header` (không bắt
  `IntegrityError`).
- **Cơ chế lỗi**: header `status="cancelled"` làm partial index `uq_bookings_quotation_id_active` nhả slot
  trong khi lines vẫn `to_request/requested/confirmed` (active theo `uq_booking_lines_source_service_line_active`),
  `service_lines.booking_status` không được mirror, không `booking.cancelled` → Finance không biết penalty.
  Tạo booking mới cho quotation đó: header insert OK, `insert_line` vỡ unique → repo `rollback()` + raise
  `BookingSlotTakenError` không được catch → 500 (đã tiêu một số `BK` nhưng rollback). `status="active"` hồi
  sinh booking đã cancel khi đã có booking active khác → raw `IntegrityError` 500. `status="completed"` cũng
  không kiểm tra lines đã terminal.
- **Kịch bản kích hoạt**: Probe P5, P7.
- **Fix** (schema request + service, không đổi DB): bỏ `status` khỏi `BookingHeaderUpdateSchema` (hoặc chỉ
  cho `active → completed` khi mọi line ∈ {delivered, cancelled}); `cancelled` chỉ qua `POST /cancel`;
  `create_booking` bắt `BookingSlotTakenError` từ `insert_line` → `BookingConflictError` 409 kèm line/booking
  đang chiếm. Manifest không đổi (không thêm/bớt route).
- **Test bắt buộc**: PUT header `status=cancelled` → 422; `active` trên booking đã cancel → 422/409;
  `completed` khi còn line mở → 422; create booking khi service_line còn active line ở booking khác → 409
  (không 500).

### §3.5 H2 🟠 HIGH — Line `delivered` là "active" theo partial index nhưng `cancel_all_open_lines` bỏ qua → quotation không thể book lại, tạo booking mới 500
- **Vị trí**: `alembic/versions/20260904_42_bookings.py` (partial index `WHERE status != 'cancelled'`);
  `services/booking_service.py::cancel_booking` (~370–376, `_TERMINAL_LINE_STATUSES` bỏ `delivered`);
  `create_booking` (~167) snapshot **mọi** `sheet.lines`.
- **Cơ chế lỗi**: sau `cancel_booking`, line `delivered` giữ nguyên (đúng nghiệp vụ) nhưng vẫn chiếm slot
  `source_service_line_id`. `create_booking` mới snapshot lại toàn bộ sheet, kể cả line đã delivered →
  IntegrityError → 500 vĩnh viễn cho quotation đó (amendment sau khi hủy một phần là kịch bản thật:
  đoàn hủy giữa tour rồi book lại phần còn lại).
- **Kịch bản kích hoạt**: Probe P6.
- **Fix** (service, không đổi index): `create_booking`/`add_line` chỉ snapshot service_lines **không** còn
  active booking_line (query `get_active_line_by_source_service_line` batch); nếu sheet không còn line nào
  bookable → 422 rõ ràng. `service_lines.booking_status` của line delivered giữ `delivered`. Bắt
  `BookingSlotTakenError` → 409 (chung với H1).
- **Test bắt buộc**: delivered → cancel_booking → create_booking mới chỉ chứa line chưa delivered, 200;
  sheet chỉ có line delivered → 422.

### §3.6 H3 🟠 HIGH — Counter `business_code_counters`: `session.rollback()` trong repository phá transaction đang mở, và row lock giữ tới commit serialize toàn bộ ops
- **Vị trí**: `repositories/booking_repository.py::next_business_code_sequence` (~197–219);
  gọi từ `BookingService.create_booking` (~150) và `transition_line` (~243, trước `update_line`).
- **Cơ chế lỗi**: (1) Race tạo counter đầu năm (2 ops đầu tiên của `BK`/`VC` mỗi năm cùng lúc): loser
  `IntegrityError` → `session.rollback()` → **toàn bộ** work trước đó trong transaction bị hủy và mọi
  instance đã load bị expire; lệnh tiếp theo (`line.cancellation_policy_snapshot_json`, `sheet.lines`)
  lazy-load trong async → `MissingGreenlet` → 500 (không phải 409). Trên PG, `UPDATE … RETURNING` giữ row lock
  counter tới commit, nên loser thường **block** rồi mới thấy row → recursion không cần; nhưng khi counter
  chưa tồn tại, hai INSERT đụng unique → path rollback nói trên. (2) Lock counter giữ suốt transaction
  `create_booking` (N lines × 2–3 lookup supplier/rate + snapshot) → mọi confirm/create khác của tenant-năm
  xếp hàng sau transaction dài nhất; timeout pool khi ops cao điểm. Không có duplicate `BK/VC` (UPDATE atomic
  đúng) — mối nguy là 500 + throughput, không phải trùng mã.
- **Kịch bản kích hoạt**: xóa row `business_code_counters` năm hiện tại, bắn 2 `POST /bookings` song song trên
  PG; hoặc mock `flush` raise `IntegrityError` lần đầu → quan sát `MissingGreenlet`.
- **Fix** (repository, không đổi schema): bọc insert-fallback bằng `async with session.begin_nested()`
  (savepoint) như Track 2 M4 đang làm cho costing; thứ tự: `INSERT … ON CONFLICT DO NOTHING` (PG) /
  savepoint-insert (SQLite) rồi `UPDATE … RETURNING`. Mint code **cuối** transaction (ngay trước flush cuối)
  để rút ngắn thời gian giữ lock; `transition_line` mint sau CAS guard (C3).
- **Test bắt buộc**: `test_booking_repository_counter_first_insert_race` (patch flush raise IntegrityError
  một lần) → trả 2 (không 500, transaction còn nguyên: booking đã add vẫn flush được); test song song 20
  confirm trên PG (đánh dấu `integration`) → 20 voucher distinct, liên tục.

### §3.7 H4 🟠 HIGH — `Idempotency-Key` tùy chọn ở apply-pricing: retry tạo 2 application row + bump facts 2 lần
- **Vị trí**: `routers/v2/costing.py::apply_pricing` (`idempotency_key: str | None = Header(None)`);
  `services/costing_service.py::apply_pricing` (`if idempotency_key:` mới tra replay).
- **Cơ chế lỗi**: chốt 15.5 #6 và Exit Gate #3 đòi header bắt buộc. Không header → mỗi retry mạng là một
  apply mới: 2 dòng `costing_applications`, facts revision +2, 2 event `costing.applied`, drift/last_applied
  nhảy. Booking `POST /bookings` và `/transition` cũng nhận `Header(None)`; `create_booking` với key None
  vẫn ghi `idempotency_key=None` → unique index `coalesce(key,'')` biến **mọi** booking không key thành
  đụng nhau (booking thứ hai không key của tenant → `BookingSlotTakenError` với message sai "already has an
  active booking").
- **Kịch bản kích hoạt**: Probe P3 (apply); `POST /bookings` 2 quotation khác nhau không header.
- **Fix** (router/schema): `Idempotency-Key: str = Header(..., min_length=1, max_length=64)` cho apply,
  create booking, transition — 422 khi thiếu (đúng envelope `VALIDATION_FAILED`). Manifest không đổi.
- **Test bắt buộc**: thiếu header → 422 cho cả 3 op; có header replay → 200 cùng body, 1 row.

### §3.8 H5 🟠 HIGH — "today" lấy theo UTC, không theo timezone destination → urgency/penalty/voucher year lệch một ngày
- **Vị trí**: `routers/v2/bookings.py::_today()` (`datetime.now(timezone.utc).date()`), truyền vào mọi
  service call; `BookingService._urgency`, `transition_line` (`today` cho `cancellation_penalty_minor`,
  `compute_deadlines`, `_next_code(..., today.year)`).
- **Cơ chế lỗi**: 15.6 Exit Gate #3 và test matrix "18:00Z" yêu cầu "today" theo tz local (VN = UTC+7). Từ
  17:00Z đến 00:00Z mỗi ngày (giờ làm việc sáng VN), `today` chậm 1 ngày: line `request_by = hôm nay` vẫn
  `due_soon` thay vì `overdue`; `days_remaining` +1 tại biên tier → penalty 25 % thay vì 100 % (hoặc ngược
  lại) — con số này được **freeze** vào `cancel_penalty_minor` và bắn sang Finance; voucher confirm sáng
  1/1 local mang năm cũ.
- **Kịch bản kích hoạt**: freeze clock `2026-07-14T20:00Z` (= 15/7 03:00 ICT), line service_date 15/7,
  tier `0 → 100 %`, tier `14 → 25 %`; cancel → code tính days_remaining = 1 → 25 %, đúng phải là 0 → 100 %.
- **Fix** (router + service, không đổi schema): `_today()` nhận tz từ setting tenant
  (`settings.ops_timezone`, mặc định `Asia/Ho_Chi_Minh`) qua `zoneinfo`; pure rules giữ nguyên nhận `date`.
- **Test bắt buộc**: `test_booking_api.py::test_today_follows_ops_timezone_at_18z` (patch clock 18:00Z →
  board urgency = ngày local); penalty tại biên tier với clock 20:00Z.

### §3.9 M1 🟡 MEDIUM — Line không có `service_date`: vô hình trên board và penalty 100 % khi hủy
- **Vị trí**: `services/booking_service.py::_snapshot_line` (~503–509), `transition_line` (~247, ~256:
  `line.service_date or today`), `cancel_booking` (~372), `_urgency` (~562).
- **Cơ chế lỗi**: `service_date` nullable trên `service_lines` (chỉ bắt buộc cho catalog pick trong edit
  working-tree). Line manual không ngày → không deadline, `request_by_date=None` → urgency None → không bao
  giờ overdue/due_soon; hủy → `service_date := today` → `days_remaining = 0` → tier thấp nhất (thường 100 %)
  → penalty = toàn bộ sell cho dịch vụ chưa biết ngày. Confirm → `deposit_due_date` tính từ `today`.
- **Kịch bản kích hoạt**: Probe P8.
- **Fix** (service): `create_booking`/`add_line` 422 liệt kê line thiếu `service_date` (hoặc derive
  `travel_start_date + day_number - 1` khi có header snapshot); penalty khi không có ngày → `0` + flag
  `PENALTY_DATE_UNKNOWN` trong payload event thay vì 100 %.
- **Test bắt buộc**: line không ngày → create 422 (hoặc derive đúng ngày); không còn nhánh `or today`.

### §3.10 M2 🟡 MEDIUM — `cancel_penalty_minor` tính trên **sell** (giá bán) chứ không phải cost (nợ supplier)
- **Vị trí**: `services/booking_service.py::transition_line` (~255–257), `cancel_booking` (~371–373) truyền
  `line.sell_minor_snapshot`; consumer `services/ap_reconciliation_service.py` (~289–299) dùng làm
  `expected_cost_minor` invoice penalty; 15.9 §"Operating" cộng `cancel_penalty_minor` vào **cost**.
- **Cơ chế lỗi**: cancellation policy là điều khoản supplier → penalty phải trên `line_cost_minor` (đã quy
  về sheet currency qua `fx_rate_ppm_snapshot`). Dùng sell làm AP kỳ vọng trả supplier cao hơn thực (markup
  + rounding), báo cáo margin âm sai. 15.9 có ghi nhận currency (sheet) nhưng không ghi nhận basis sell —
  đây là drift thiết kế đã lan sang Finance.
- **Kịch bản kích hoạt**: line cost 1 000 000, markup 20 % → sell 1 200 000, tier 25 % → penalty ghi
  300 000; supplier invoice 250 000 → variance giả.
- **Fix** (service, pure rule giữ nguyên chữ ký): truyền `line_cost_minor(ServiceLineInput(...snapshot))`
  vào `cancellation_penalty_minor`; nếu cần penalty khách hàng (refund) thì là field khác, tính ở lớp
  commercial, không trộn. Cập nhật 15.9 §1.3 cho nhất quán.
- **Test bắt buộc**: penalty = 25 % × cost (fx-converted), không phải sell; AP suggest = cost-based.

### §3.11 M3 🟡 MEDIUM — Board `GET /bookings` không có ownership filter trong khi detail/mutation có
- **Vị trí**: `routers/v2/bookings.py::list_board` (chỉ `require_editor`),
  `services/booking_service.py::list_board`, `repositories/booking_repository.py::list_board_lines`.
- **Cơ chế lỗi**: mọi editor thấy mọi line (supplier contact snapshot, sell, penalty) của mọi designer;
  `GET /bookings/{id}` lại 403 theo `require_owned_v2_quotation`. Hai chính sách trái ngược trên cùng dữ
  liệu → detail 403 vô nghĩa. Spec 15.6 nói board là của ops (global) — nếu đó là quyết định thì detail
  cũng phải mở cho editor; nếu không, board phải lọc.
- **Fix** (router/service): chốt một chính sách; khuyến nghị board lọc theo `designer_profile_id`/
  `created_by_profile_id` của quotation trừ admin/service (reuse `_is_admin_principal`).
- **Test bắt buộc**: designer B không thấy line của quotation designer A trên board (hoặc detail mở tương
  ứng).

### §3.12 M4 🟡 MEDIUM — State machine & rule gaps: `confirmed_at` không thể fail, `supplier_ref` sửa được sau delivered/cancelled, `update_line_ops` cho line terminal, docstring no-show lệch code
- **Vị trí**: `services/booking_service.py::transition_line` (~227: `confirmed_at = today if to ==
  "confirmed"` — gate `confirmed_at` trong `validate_transition` luôn pass, đồng thời cột ghi `datetime.now(utc)`
  còn deadline tính bằng `today` date), `update_line_ops` (~314–323: chặn `supplier_ref` chỉ khi
  `status == "confirmed"`; `request_by_date/assignee/notes` sửa được trên line delivered/cancelled;
  `None` = "không đổi" nên không thể clear `request_by_date`/`customer_balance_due_date`),
  `core/rules/booking_rules.py::cancellation_penalty_minor` (docstring "on/after service_date" nhưng code
  `days_remaining < 0` → hủy đúng ngày dịch vụ ăn tier thay vì no-show).
- **Fix** (service/pure rule, không đổi schema): `update_line_ops` từ chối mọi field khi status terminal,
  `supplier_ref` chỉ trước `confirmed`; explicit clear qua sentinel (`Optional` + `model_fields_set`);
  quyết định no-show boundary (`<= 0`) và sửa docstring/spec cùng lúc; `transition_line` lưu `confirmed_at`
  và tính deadline từ **cùng** mốc.
- **Test bắt buộc**: ops update trên line cancelled → 422; supplier_ref sau delivered → 422; cancel đúng
  ngày dịch vụ → no-show %.

### §3.13 M5 🟡 MEDIUM — Repository tự `session.rollback()` (insert_booking, insert_line, counter) phá ranh giới transaction của service; lỗi slot thoát thành 500
- **Vị trí**: `repositories/booking_repository.py::insert_booking/insert_line` (`rollback()` trong
  `except IntegrityError`), `next_business_code_sequence`; caller `create_booking` (~167–171) và `add_line`
  (~353) không bắt.
- **Cơ chế lỗi**: cùng smell Track 2 M4 — rollback bên trong repository hủy cả work chưa commit của service
  (header vừa insert, mirror status) và expire identity map, để lại object stale ở tầng trên. Kết hợp H1/H2
  thành 500 thay vì 409.
- **Fix**: `begin_nested()` savepoint như edit đang có ở `costing_repository.py`; service map
  `BookingSlotTakenError` → 409 với thông tin slot; router giữ envelope `REVISION_CONFLICT`/`recovery: reload`.
- **Test bắt buộc**: trùng idempotency-key khác quotation → 409 message đúng ("idempotency key reused"),
  không "already has an active booking".

### §3.14 M6 🟡 MEDIUM — Tạo option mới `opt_{len+1}` có thể trùng id với option đang tồn tại
- **Vị trí**: `main.py::_apply_costing_pricing_option` (~3927: `target_id = f"opt_{len(options) + 1}"`).
- **Cơ chế lỗi**: options là list sale có thể xoá giữa chừng (`["opt_1", "opt_3"]`) → apply tạo `opt_3`
  thứ hai; drift `next(o for o in options if o.id == target)` và FE key theo id trỏ vào option đầu tiên,
  option vừa áp "biến mất" khỏi dialog, application row ghi `target_option_id` mơ hồ.
- **Fix** (callback): sinh id không đụng (`opt_{n}` tăng tới khi không có trong `{o.id}`), hoặc `generate_id("opt")`.
- **Test bắt buộc**: facts có `opt_1, opt_3` → apply `targetOptionId=None` → id mới ≠ `opt_3`, 3 option distinct.

---

## 3. §3.7 Danh sách test nợ theo spec (Bổ sung cùng đợt fix)

| # | Test nợ | Spec | Trạng thái hiện tại |
| :-- | :-- | :-- | :-- |
| 1 | Fixture quotation **đúng shape production** (`quotation_family_id`, `business_version`, `quotation_version_facts`) cho toàn bộ `test_apply_pricing_*` và `test_booking_*` | 15.5 §3 "Hồi quy quotation" | Thiếu → C1, C2 không bị bắt |
| 2 | Atomic 3-trong-1 với fail ở **facts write** (không chỉ outbox): `save_current_document` raise sau khi `verify_revision_guarded` → không application row, không event, sheet `updated_at` không đổi | 15.5 §3 | Chỉ có case outbox fail |
| 3 | Dual CAS **race thật**: hai apply song song cùng cả hai revision, key khác → đúng 1 application, 1 bump facts (hiện chỉ test stale-value, không test concurrent) | 15.5 chốt #5, Exit Gate #3 | Thiếu |
| 4 | Idempotency-Key bắt buộc (422 khi thiếu) cho apply / create booking / transition; replay cùng key + payload khác → 409 | 15.5 #6, 15.6 K8 | Thiếu |
| 5 | Booking CAS DB-level: hai session cùng `base_booking_revision` (confirm/cancel/header/ops) → 1 thắng, 1 → 409, 1 voucher, 1 event | 15.6 §1 (T3), K8 | Thiếu (probe P4 fail) |
| 6 | Booking immutability: mọi FROZEN column (`*_snapshot*`, `sell_minor_snapshot`, `payment_terms_snapshot_json`) không đổi sau: sửa rate/supplier, sửa/xoá service_line (guard), đổi markup/rounding sheet, apply-pricing | 15.6 T3/R3 | Chỉ có case sửa supplier |
| 7 | Guard costing grid: `update_line`/`delete_line` với `booking_status ∈ {to_request, requested, confirmed, delivered, cancelled}` → 409 cho **mọi** trạng thái ≠ quoted; guard chạy trên trạng thái DB mới nhất (booking mirror commit giữa chừng) | 15.6 chốt "line đã book" | Chỉ test delete sau create |
| 8 | Counter concurrency: 20 confirm song song trên PG → 20 `VC` distinct liên tục; first-insert race không 500 (savepoint); mint code sau CAS | 15.6 §1.4 | Thiếu |
| 9 | Header status không bypass cancel (H1); delivered + cancel + re-book (H2) | 15.6 state machine | Thiếu (probe P5/P6/P7 fail) |
| 10 | Timezone: board urgency và penalty tier tại 18:00Z | 15.6 Exit Gate #3 | Thiếu |
| 11 | `service_date=None` line: create 422 / derive; penalty không 100 % mù | 15.6 §1.5 | Thiếu (probe P8) |
| 12 | Penalty basis = cost (fx-converted), AP suggest khớp | 15.6 §1.5, 15.9 §1.3 | Thiếu |
| 13 | Option id sinh mới không trùng (`opt_1, opt_3` → id mới distinct) | 15.5 §1.5 | Thiếu |
| 14 | Facts SSOT sau apply: `GET /facts` == document == drift source; sale sửa tay option qua PUT facts → drift `commercial_modified` | 15.5 §1.3, §2.3 | Test drift hiện chỉ đi qua request rows |
| 15 | Board authz (M3) theo chính sách đã chốt | 15.6 §1.4 | Thiếu |

---

## 4. §3.8 Exit Gate của Track 3

1. **C1, C2, C3 + H1–H5 fix** và toàn bộ test bắt buộc (§3.1–§3.8) + test nợ #1–#10 xanh trên cả SQLite và
   PostgreSQL (case concurrency đánh dấu `integration`, chạy trên PG). Probe P1–P7 chuyển thành regression
   test trong repo và phải xanh.
2. **M1–M6 fix** + test nợ #11–#15 xanh; docstring/spec (`cancellation_penalty_minor` no-show boundary,
   15.6 §1.5 `penalty_free_until` "min" → "max", 15.9 §1.3 penalty basis) cập nhật cùng đợt.
3. Toàn bộ test suite `PYTHONPATH=. pytest` xanh; contract suites (`test_v2_api_manifest_contract.py`,
   `test_v2_error_envelope.py`, `test_domain_rules.py`, `test_business_gates.py`, `test_ssot_integrity.py`)
   xanh; **migration không đổi** (`_41`, `_42` giữ nguyên — mọi fix ở service/repository/schema request/
   callback); `git diff` không chạm `components/display/**`, `prompts/**`, reconciler FE.
4. Chốt quyết định sản phẩm bằng văn bản trong 15.5 (C1 hướng 1 hay 2) và 15.6 (board authz M3) trước khi
   merge — hai điểm này không thể "fix code" mà không có quyết định.

---

## 5. §3.9 Remediation Evidence (closed 2026-09-03)

Fixed against `HEAD 8339ed6` (`fix: close track 2 rates and costing audit`). No migration, model
column/index/constraint, or frontend display/reconciler file was touched.

### Product decisions bound in code
- **C1**: Direction 1. `services/facts_contract.py::classify_facts_mutation(status, source_kind)` — only
  `status != "draft"` locks Facts (`revision_locked`); `quotation_family_id` no longer participates in the
  guard. Both `main.py::_apply_costing_pricing_option` and `routers/v2/quotation_facts.py::put_quotation_facts_v2`
  call the same classifier.
- **M3**: Global Operations Access. `routers/v2/bookings.py` no longer calls
  `require_owned_v2_quotation`/`_enforce_quotation_ownership_for_booking` on any booking route; every route
  still requires `EditorPrincipalDep`. Quotation/costing ownership elsewhere is unchanged.

### Defect → fix map
| Defect | Fix | Key files |
| :-- | :-- | :-- |
| C1 | `classify_facts_mutation` replaces the `quotation_family_id` guard | `services/facts_contract.py`, `main.py`, `routers/v2/quotation_facts.py` |
| C2 | `QuotationRepository.get_current_facts`/`update_version_facts` — apply and `PUT /facts` read and write the same Facts source in one transaction | `repositories/quotation_repository.py`, `main.py`, `routers/v2/quotation_facts.py`, `services/costing_service.py`, `services/booking_service.py::_snapshot_quotation_facts` |
| C3 | `BookingRepository.reserve_revision` — real SQL CAS (`UPDATE … WHERE booking_revision = :expected`) called before every externally-visible booking mutation | `repositories/booking_repository.py`, `services/booking_service.py` |
| H1 | `BookingHeaderUpdateSchema.status` narrowed to `Literal["completed"]`, `extra="forbid"`; completion requires every line terminal | `schemas/v2/booking.py`, `services/booking_service.py::update_header` |
| H2 | `create_booking`/`add_line` exclude service lines with any non-cancelled booking line (including `delivered`) before snapshotting | `repositories/booking_repository.py::list_active_lines_by_source_service_line_ids`, `services/booking_service.py` |
| H3 | Counter insert-race uses `session.begin_nested()` savepoint, never `session.rollback()`; `BK`/`VC` minted only after all upstream lookups resolve, immediately before the write that consumes them | `repositories/booking_repository.py::next_business_code_sequence`, `services/booking_service.py` |
| H4 | `Idempotency-Key` required (`min_length=1, max_length=64`) on apply-pricing, create-booking, transition-line at both the router and the service layer; reused-key-with-different-payload → 409 | `routers/v2/bookings.py`, `routers/v2/costing.py`, `services/costing_service.py`, `services/booking_service.py` |
| H5 | `_today()` resolves via `ZoneInfo(settings.ops_timezone)`, not `datetime.now(timezone.utc).date()` | `routers/v2/bookings.py`, `core/config.py` |
| M1 | Missing `service_date` derives from `travel_start_date + day_number − 1` or 422s at create/add-line; unknown-date cancellation → penalty `0` + `PENALTY_DATE_UNKNOWN` | `services/booking_service.py::_resolved_service_date/_cancellation_penalty` |
| M2 | `cancellation_penalty_minor` now takes FX-converted **cost**, not `sell_minor_snapshot` | `core/rules/booking_rules.py`, `services/booking_service.py::_cost_minor_snapshot`, `docs/.../15.9-tourplan-simplest-finance-and-ops.md` |
| M3 | See product decision above | `routers/v2/bookings.py` |
| M4 | `update_line_ops` rejects terminal-line edits, restricts `supplier_ref` to pre-confirm, uses `model_fields_set` so explicit `null` clears; no-show boundary corrected to `days_remaining <= 0` | `services/booking_service.py`, `core/rules/booking_rules.py` |
| M5 | `insert_booking`/`insert_line`/`update_line` wrap their flush in `session.begin_nested()`; no repository method calls transaction-wide `session.rollback()` | `repositories/booking_repository.py` |
| M6 | New-option id search skips existing ids (`opt_1, opt_3` → next free, not `len(options)+1`) | `main.py::_apply_costing_pricing_option` |

### Residuals closed in this pass
1. `CostingService.apply_pricing` — `idempotency_key` is now a required keyword argument (`str`, no
   default); every direct-service test call was given an explicit key.
2. `BookingService.transition_line` — replay/conflict check now looks up
   `transition_idempotency_key` **tenant-wide** via
   `BookingRepository.get_line_by_transition_idempotency_key`, not only on the requested line; reuse
   against a different line or a different target status → 409.
3. `core/config.py::Settings.__post_init__` validates `ops_timezone` against `zoneinfo.ZoneInfo` at
   process start — an invalid `OPS_TIMEZONE` now fails startup instead of 500ing the first booking
   request of the day.
4. `BookingService.create_booking` resolves every line snapshot (supplier/rate policy lookups) **before**
   minting `BK`, so the counter's row lock no longer spans those lookups.
5. `tests/test_track3_postgres_concurrency.py` gained
   `test_postgres_counter_allocates_twenty_distinct_contiguous_values_under_concurrency` (20 concurrent
   `next_business_code_sequence` calls → dense `1..20`, no duplicate, no crash) and
   `test_postgres_concurrent_apply_pricing_same_revisions_only_one_commits` (two independent PG
   connections apply the same sheet at the same dual-CAS pair → exactly one commits, one
   `costing_applications` row, one `costing.applied` outbox event). Both were run against a real
   disposable PostgreSQL 16 database (`quotation_track3_test`) and passed; fixing them also surfaced and
   fixed a pre-existing bug in the original PG CAS test — `Booking`/`CostingSheet` have only a raw FK
   column, no ORM `relationship()`, so SQLAlchemy's flush-order dependency sort could insert the child
   first, which Postgres (unlike the untested assumption) rejects immediately. Added
   `.github/workflows/track3-postgres-concurrency.yml` (Postgres 16 service container, mirrors
   `track2-postgres-migrations.yml`).
6. This section.

### Verification run (2026-09-03, this pass)
```
PYTHONPATH=. pytest tests/test_facts_contract.py tests/test_put_facts_radical_contract.py \
  tests/test_facts_media_immutable.py tests/test_apply_pricing_service.py tests/test_apply_pricing_api.py \
  tests/test_costing_rules.py tests/test_costing_service.py tests/test_costing_api.py \
  tests/test_booking_rules.py tests/test_booking_service.py tests/test_booking_api.py \
  tests/test_ap_reconciliation_service.py -q
→ 146 passed

PYTHONPATH=. pytest tests/test_v2_api_manifest_contract.py tests/test_v2_error_envelope.py \
  tests/test_domain_rules.py tests/test_business_gates.py tests/test_ssot_integrity.py -q
→ 41 passed

PYTHONPATH=. pytest tests -q --ignore=tests/test_track3_postgres_concurrency.py
→ 1017 passed, 5 failed (all tests/test_ingestion_corpus.py — Track 4 territory, untouched by this
   change, reproduce identically on HEAD 8339ed6 before any Track 3 fix)

TRACK3_POSTGRES_TEST_URL=postgresql+asyncpg://quotation:quotation_local_password@localhost:5433/quotation_track3_test \
PYTHONPATH=. pytest -m integration tests/test_track3_postgres_concurrency.py -v
→ 3 passed (real PostgreSQL 16, disposable database, dropped after the run)

shasum -a 256 alembic/versions/20260903_41_costing_applications.py alembic/versions/20260904_42_bookings.py
→ f87a6c2c9ea0edf25da6a3dc8e1b4bb4e57aeacbe0673662708183097b8a30a6  (_41, matches plan record)
→ 12aa49c9a7cd2f391efdcac901f5491f723465abae6c026e1dff768f80a84687  (_42, matches plan record)

cd quote-generator && npm run lint && npm test
→ lint chain green; 344 passed, 0 failed
```

### Still open (explicit, not silently deferred)
- The 20-confirm stress and the dual-CAS apply race now exist as tests, but no CI run has exercised them
  yet in GitHub Actions — the workflow file is new in this pass and only validated by a local disposable
  Postgres run.
- Transition-key reuse detection (residual 2) is a service-level read guard, not a DB unique constraint —
  `transition_idempotency_key` has no unique index in the frozen `_42` migration. Two truly simultaneous
  requests with the *same* key on *different* lines can both pass the lookup before either commits; the
  booking-revision CAS still prevents a corrupted write, but the reused-key 409 is not itself atomic.
  Documented here rather than fixed silently, since closing it requires either a migration (out of scope,
  frozen) or a `SELECT … FOR UPDATE` serialization point that would reintroduce H3-style lock contention.
