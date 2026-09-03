# Audit Implementation — Track 2: Rates & Costing Dual-Track Engine Defect Log

> **Loại tài liệu**: Adversarial code audit của Track 2 (Plans [15.3](./15.3-rates.md) + [15.4](./15.4-costing.md))
> đối chiếu với source code tại HEAD `c0943d7` (2026-09-03). Mọi finding dưới đây đều được
> trace end-to-end qua code thật và — với các finding C/H — được **tái hiện bằng probe test
> chạy trên fixture SQLite của repo** (không sửa app code, không sửa test, không sửa migration).
> Ký hiệu severity: 🔴 C = mất/hỏng dữ liệu tiền hoặc phá bất biến E3/R3/CS1; 🟠 H = bug nghiệp vụ
> hoặc 500 trên đường đi chính; 🟡 M = drift kiến trúc / smell có hậu quả đo được.

---

## 1. Subsystem Scope & Verified Call-Graph Perimeter

### 1.1 Anchor specs & entrypoints đã quét

| Lớp | File | Ghi chú trace |
| :-- | :-- | :-- |
| Spec | `15.3-rates.md`, `15.4-costing.md`, `15-modular-tour-ops-brainstorm.md` | Chốt E3/R3/T6/K1/K3/CS1/CAS/K8 dùng làm oracle |
| Kernel | `core/kernel/money.py` | Re-export SSOT currency; `validate_amount_minor` **không có caller nào ngoài test** (dead API) |
| Pure rules | `core/rules/rate_selection.py`, `core/rules/rate_validation.py`, `core/rules/costing_rules.py` | Xác nhận tz-purity (không `zoneinfo`/`today()`/`now()`), integer-only math |
| Rates | `db/models/rate.py`, `repositories/rate_repository.py`, `services/rate_service.py`, `schemas/v2/rate.py`, `routers/v2/rates.py` | 7 operations, state machine draft→active→superseded |
| Costing | `db/models/costing.py`, `repositories/costing_repository.py`, `services/costing_service.py`, `schemas/v2/costing.py`, `routers/v2/costing.py` | 9 operations (8 của 15.4 + apply-pricing 15.5) |
| Migrations | `20260901_39_rates.py`, `20260902_40_costing.py` (+ `_41`, `_46` additive) | Khớp model 1:1; partial unique index có `sqlite_where` |

### 1.2 Call-path ngoài anchor đã trace (không dừng ở anchor)

| Caller | Điểm chạm Track 2 | Kết luận |
| :-- | :-- | :-- |
| `services/quote_request_service.py::generate_quotation` (~L881) | `CostingRepository.get_active_sheet_by_request` (read-only) | Chỉ đọc để trả `costing_sheet_id`; không ghi |
| `main.py::_apply_costing_pricing_option` (~L3864) qua `api/runtime.apply_pricing_option` | CAS facts phía quotation | Ngoài scope 15.4; đã có `verify_revision_guarded` khép cửa sổ |
| `services/booking_service.py` (15.6) | `costing_rules.line_cost/sell`, `_mirror_service_line_status` ghi thẳng `service_line.booking_status` **không bump `costing_revision`** | Ghi nhận ở §2 M-level (không thuộc 15.4 nhưng chạm bất biến CAS) |
| `services/ai_drafter/draft_run_service.py` (15.7) | `RateRepository.list_by_product` → `select_rates`/`pick_price_line` → `CostingService.create_line` | Đây là **consumer duy nhất** đi qua `rate_selection`; costing service thủ công thì **không** (→ H3) |
| `services/ai_platform/toolsets/catalog.py` | `_rate_candidates_for_product`, `pick_price_line` | Chịu ảnh hưởng M2 (`pick_price_line` bỏ qua `unit`, tier chồng lấn) |
| `services/ingestion/commit_service.py` (15.8) | `RateService.create_draft/activate/supersede` trong 1 transaction | Chịu ảnh hưởng C1 (supersede không có DB guard) |
| Outbox | `catalog.rate.activated`, `catalog.rate.superseded` (rates); `costing.applied` (15.5) | Mirror đủ trong `notification/domain/events.py`; payload superseded chứa **float** (→ M7) |
| Auth | `routers/v2/costing.py::_enforce_quotation_ownership_for_sheet`, `api/dependencies.require_owned_v2_quotation` | Sheet chưa attach = không owner (F-28, deliberate) — ghi nhận, không tính defect |

### 1.3 Bất biến đã xác minh **đúng** (không phải defect — ghi để khỏi audit lại)

- **R3 snapshot**: `_resolve_catalog_line` chép `amount_minor`/`currency` vào `service_lines`; supersede sau đó không đụng line (`test_create_catalog_line_snapshots_cost_and_supersede_does_not_move_it` xanh; probe xác nhận lại).
- **CS1 race currency-vs-line**: `update_settings` và `insert_line` cùng đi qua `_bump_revision_guarded` (`UPDATE … WHERE costing_revision = :expected`, `rowcount != 1 → race`). Hai writer cùng `baseCostingRevision` chỉ 1 thắng → không thể sinh line lệch tệ không có fx. **Cửa sổ CS1 đã đóng bằng CAS SQL.**
- **CAS TOCTOU line-vs-sheet**: `_check_revision` chỉ là pre-check; guarded UPDATE là authority; test 2-session `test_version_guarded_bump_rejects_stale_writer_even_with_stale_identity_map` xanh.
- **Attach**: guard `quotation_id IS NULL` + partial unique `(quotation_id)` → double-attach không thể; `session.refresh` sau attach vẫn trả đủ lines (probe: `items=1 rev=2`).
- **Tz-purity của pure layer**: `rate_selection` không import `zoneinfo`, không gọi `now()/today()`; `rate_service`/`costing_service` cũng không gọi `date.today()`. `service_date` là DATE thuần đi từ `<input type=date>` của FE → không có điểm quy đổi UTC nào trong BE để trôi ngày. (Test biên `18:00Z` theo spec §3 **chưa tồn tại** → nợ test §3.)
- **Integer math**: `costing_rules` không có float; `_round_half_up_div`/`_ceil_div` đúng cho số âm/dương; totals = Σ line totals nên không lệch line-vs-sheet.

### 1.4 Automated test baseline

```
PYTHONPATH=. pytest tests/test_kernel_money.py tests/test_rate_selection.py tests/test_rate_validation.py \
  tests/test_rate_service.py tests/test_rate_api.py tests/test_costing_rules.py tests/test_costing_service.py \
  tests/test_costing_api.py tests/test_flow3_rates_e2e.py tests/test_v2_api_manifest_contract.py -q
→ 87 passed, 26 warnings (duplicate operation-id warnings từ main.py legacy, không liên quan)
```

Probe audit (scratch, ngoài repo, 11 kịch bản): 9 chạy đúng như dự đoán, 2 "fail" là **500 thật**
(IntegrityError và ValueError thoát ra khỏi router) — chính là H1/H4 bên dưới.

---

## 2. Defect Log (BẮT BUỘC trước khi nghiệm thu)

### §2.1 C1 🔴 CRITICAL — Supersede không có DB guard: 2 supersede đồng thời sinh 2 rate `active` v2 cùng cha, nhân đôi price lines (phá E3)

- **Vị trí**: `services/rate_service.py::RateService.supersede` (~dòng 165–227); `repositories/rate_repository.py::set_lifecycle_status` (~dòng 86–92). Cùng lỗi: `RateService.activate` (~dòng 133–163).
- **Cơ chế lỗi**: Kiểm tra trạng thái (`old_rate.lifecycle_status != "active"`) là check trong Python trên object đã load; chuyển trạng thái thực hiện bằng `setattr` + `flush` (UPDATE không có `WHERE lifecycle_status = 'active'`). Không có unique index nào trên `supersedes_rate_id`, không có partial unique `(product_id, version)`. Spec 15.3 §6 thừa nhận không dùng được partial-unique `(product_id) WHERE active` vì cho phép nhiều mùa — nhưng cũng không đặt guard nào khác. Hậu quả: hai request supersede cùng rate (2 tab, hoặc UI + ingestion commit 15.8 `action=supersede_rate` chạy song song) đều pass check, đều insert rate mới `version = old+1`, đều set old → superseded. Kết quả: **2 rate active, cùng version 2, cùng `supersedes_rate_id`**, price lines nhân đôi trên product; `select_rates` sẽ trả `has_conflict=True` vĩnh viễn cho mọi ngày; chuỗi version (audit log K5) gãy — không còn là chain mà là cây. `activate` bị y hệt: 2 activate đồng thời → 2 event `catalog.rate.activated` cho 1 rate.
- **Kịch bản kích hoạt** (đã tái hiện bằng probe 2 session SQLite): Session A `get_by_id(rate)` → active. Session B `supersede(rate)` + commit. Session A `supersede(rate)` + commit → **không lỗi**. `list_active_for_product` trả `[(rat_…7c, v2, parent), (rat_…7d, v2, parent)]`.
- **Fix** (service + repository, không đổi schema): `set_lifecycle_status` phải là CAS SQL theo đúng pattern `CostingRepository._bump_revision_guarded`: `UPDATE rates SET lifecycle_status=:new … WHERE id=:id AND lifecycle_status=:expected_old` với `execution_options(synchronize_session=False)`, `rowcount != 1 → raise RateLifecycleRaceError` → service map sang `RateConflictError` (409). `supersede` gọi guard **trước** khi insert rate mới (đóng old với expected `active`) để thứ tự thất bại rẻ nhất; `activate` guard expected `draft`. Lý do không thêm constraint DB: spec §6 đã loại partial-unique vì multi-season; CAS SQL là đủ và đồng nhất với 15.4/15.9.
- **Test bắt buộc**: `tests/test_rate_service.py::test_concurrent_supersede_second_writer_gets_409` — 2 session, session A đọc rate trước, B supersede+commit, A supersede → `RateConflictError`; assert `list_active_for_product` đúng 1 rate và `version==2`. Thêm `test_concurrent_activate_emits_exactly_one_event` (đếm `outbox_events`).

### §2.2 C2 🔴 CRITICAL — `fx_rate_ppm` được áp dụng cả khi `cost_currency == sheet.currency`: nhân giá vốn im lặng

- **Vị trí**: `services/costing_service.py::_resolve_line_values` (~dòng 521–540), dòng `values["fx_rate_ppm"] = payload.fx_rate_ppm`; engine `core/rules/costing_rules.py::line_cost_minor` (~dòng 78–85).
- **Cơ chế lỗi**: Guard duy nhất là *"lệch tệ mà thiếu fx → 422"*. Chiều ngược lại — *cùng tệ mà có fx* — không bị chặn cũng không bị null-out. `line_cost_minor` áp fx bất kể currency (pure rule không biết currency, đúng thiết kế) nên một line VND trên sheet VND với `fx_rate_ppm=2_000_000` có cost gấp đôi; với `fx_rate_ppm=1` (giá trị nhỏ nhất schema cho phép, `ge=1`) cost bị chia 1.000.000 → **về 0**, sell theo markup cũng về 0, margin sai, apply-pricing (15.5) đẩy số sai vào `pricing_facts`, booking (15.6) snapshot số sai. Không có log, không có flag, response 201 bình thường. Đây là data corruption tiền tệ im lặng — vi phạm tinh thần CS1/E1 (fx chỉ tồn tại để quy đổi ngoại tệ).
- **Kịch bản kích hoạt** (đã tái hiện): sheet VND, manual line `unit_cost_minor=250_000, qty_unit=2, cost_currency="VND", fx_rate_ppm=2_000_000` → `cost_minor = 1_000_000` (đúng phải là 500_000). FE hiện tại gửi fx từ ô nhập tự do; một lần gõ nhầm/paste nhầm là đủ. Ngoài ra `update_settings` **không** động vào fx của line nên nếu sheet đổi tệ (khi rỗng) rồi thêm line cùng tệ với fx cũ dính trong form FE → cùng lỗi.
- **Fix** (service, không đổi schema): trong `_resolve_line_values`, nếu `cost_currency == sheet.currency` và `payload.fx_rate_ppm is not None` → `raise CostingValidationError("fx_rate_ppm must be omitted when line currency equals sheet currency")` (422, tường minh) — **không** silently null-out vì sale cần biết mình vừa gõ sai. Đồng thời thêm `le=` hợp lý cho `fx_rate_ppm` trong `ServiceLineWriteSchema` (ví dụ `le=10**12`) để chặn overflow BigInteger trên Postgres.
- **Test bắt buộc**: `tests/test_costing_service.py::test_fx_rate_rejected_when_line_currency_equals_sheet_currency` (manual + catalog line, create + update) và `tests/test_costing_api.py::test_fx_on_same_currency_returns_422`.

### §2.3 H1 🟠 HIGH — `validate_currency` ném `ValueError` thô, không phải `CostingValidationError` → 500 `INTERNAL_ERROR` trên 3 đường đi

- **Vị trí**: `services/costing_service.py::create_sheet` (~dòng 131), `::update_settings` (~dòng 155), `::_resolve_manual_line` (~dòng 590); kernel `core/kernel/money.py::validate_currency` (~dòng 15–20); router `routers/v2/costing.py` chỉ bắt `CostingValidationError`/`CostingConflictError`.
- **Cơ chế lỗi**: `CostingValidationError(ValueError)` là *con* của `ValueError`, nên `except CostingValidationError` **không** bắt `ValueError` thô từ kernel. `RateService._resolve_currency` đã bọc đúng (`except ValueError → RateValidationError`), costing service thì không — drift giữa 2 service cùng track. Lỗi rơi xuống `generic_exception_handler` → 500 `{"code":"INTERNAL_ERROR","retryable":true,"recovery":"retry"}` — FE sẽ **retry** một input sai. `PUT /settings` còn tệ hơn: router không bắt cả `CostingValidationError`.
- **Kịch bản kích hoạt** (đã tái hiện): `POST /costing-sheets {"request_id":…,"currency":"JPY"}`, `PUT /settings {"currency":"JPY"}`, `POST /lines {"cost_currency":"JPY","fx_rate_ppm":1}` → cả 3 raise `ValueError` xuyên router.
- **Fix** (service + router): thêm helper `_currency(value) -> str` trong `CostingService` bọc `validate_currency` và re-raise `CostingValidationError` (giống rate service). Router `update_costing_settings` thêm `except CostingValidationError → 422`. Tuỳ chọn tốt hơn ở schema: validator Pydantic `field_validator("currency","cost_currency")` gọi `validate_currency` để lỗi thành `VALIDATION_FAILED` với `fieldErrors[].path` đúng envelope.
- **Test bắt buộc**: `tests/test_costing_api.py::test_unsupported_currency_returns_422_on_sheet_settings_and_line` (3 endpoint, assert status 422 và không có `INTERNAL_ERROR`).

### §2.4 H2 🟠 HIGH — `PUT /rates/{id}` (draft) trả về `lines` **cũ** trong response dù DB đã ghi lines mới (identity-map staleness)

- **Vị trí**: `repositories/rate_repository.py::replace_lines` (~dòng 69–77) + `RateService.update_draft` (~dòng 102–121) gọi `get_by_id` sau đó.
- **Cơ chế lỗi**: `replace_lines` xóa bằng Core `DELETE` (không đi qua collection `rate.lines`) và `session.add(RatePriceLine(rate_id=…))` mới **không append vào `rate.lines`**. `get_by_id` sau đó `select(Rate)…selectinload(Rate.lines)` — object `Rate` đã có trong identity map với `lines` đã load, SQLAlchemy không ghi đè collection đã load (không `populate_existing`, không expire), nên `_to_response` serialize `rate.lines` cũ. `create_draft`/`supersede` không dính vì rate mới chưa từng load lines. Hậu quả: FE (RateEditorDrawer) nhận payload "đã lưu" nhưng hiển thị grid cũ → sale tưởng lưu thất bại và lưu lại; mọi consumer trong cùng session (ingestion commit đọc lại rate sau update) thấy dữ liệu sai; và các object `RatePriceLine` cũ vẫn nằm trong `rate.lines` với cascade `delete-orphan` — trạng thái session không nhất quán.
- **Kịch bản kích hoạt** (đã tái hiện qua HTTP): POST draft 1 line `adult=1_000_000`; PUT với 2 lines `adult=1, child=2` → response `lines=[('adult',1000000)]`; GET ngay sau → `[('adult',1),('child',2)]`.
- **Fix** (repository, không đổi schema): `replace_lines` phải thao tác qua ORM collection: `rate.lines.clear()` (delete-orphan lo xóa) rồi `rate.lines.extend(new_lines)`, `flush`; hoặc sau bulk delete gọi `session.expire(rate, ["lines"])` / `session.refresh(rate, ["lines"])` trước khi đọc lại. Ưu tiên cách 1 — đúng "một aggregate" §1.5.
- **Test bắt buộc**: `tests/test_rate_service.py::test_update_draft_response_reflects_replaced_lines` (assert `len(lines)==2` và amounts trong **response** của `update_draft`, không phải trong GET sau đó); `tests/test_rate_api.py::test_put_draft_lines_round_trip`.

### §2.5 H3 🟠 HIGH — Costing thủ công bỏ qua `rate_selection`: `service_date=None` bỏ qua hiệu lực, không kiểm tra pax/tier, `candidates` luôn `[]` (T6 chưa được thực thi)

- **Vị trí**: `services/costing_service.py::_resolve_catalog_line` (~dòng 542–576) và `::_rate_covers_date` (~dòng 594–602).
- **Cơ chế lỗi**: Spec 15.4 §1.6 chốt *"server re-validate rate active + phủ `service_date` qua `rate_selection`… Rate hết hiệu lực/conflict → 422 + candidates"*. Thực tế: (a) `_rate_covers_date` là bản **copy tay** của `select_rates._covers_date` (DRY drift, đã có 2 nơi parse `blackout_json`); (b) `service_date is None → return True` — không có ngày thì **không kiểm tra gì**, rate active nhưng validity đã qua từ 2025 vẫn snapshot được; (c) `min_pax`/`max_pax` của rate và `tier_min/max_pax` của price line **không được kiểm tra** — payload không có khái niệm pax, sale có thể chọn dòng tier 10–20 pax cho đoàn 2 người; (d) `candidates` là hằng `[]` nên contract 422-kèm-candidates mà FE `AddServiceLineFlow` dựa vào để gợi ý rate khác không bao giờ có dữ liệu. Consumer AI (`draft_run_service`) thì đi qua `select_rates`/`pick_price_line` đầy đủ → hai đường đi tạo cùng một `service_line` với 2 mức kiểm tra khác nhau.
- **Kịch bản kích hoạt** (đã tái hiện): catalog line với `service_date=None` → 201, `tariff_id` gán. Với `service_date=2030-01-01` → 422 `{"message":…,"candidates":[]}`.
- **Fix** (service, không đổi schema): `_resolve_catalog_line` build `RateCandidate` từ `rate_repository.list_by_product(product_id, lifecycle="active")` bằng **một** mapper dùng chung với `services/ai_platform/toolsets/catalog._rate_candidates_for_product` (move mapper về `repositories/rate_repository.py` hoặc `services/rate_candidates.py`), gọi `select_rates(candidates, service_date, pax)`; nếu `rate_id` không nằm trong `selection.candidates` → 422 với `candidates=[{rate_id, season, validity}]`; nếu `service_date is None` với dòng catalog → 422 `"service_date is required for a catalog line"` (spec K3: ngày là điều kiện của giá); pax lấy từ `qty_unit` khi `price_for ∈ {adult, child, infant}` hoặc thêm `pax_count: int | None` vào `ServiceLineWriteSchema` (additive, không đổi DB). Xóa `_rate_covers_date`.
- **Test bắt buộc**: `tests/test_costing_service.py::test_catalog_line_requires_service_date`, `::test_catalog_line_rejects_rate_outside_pax_window`, `::test_catalog_line_422_lists_other_active_candidates` (2 rate active, chọn rate không phủ ngày → candidates chứa rate kia).

### §2.6 H4 🟠 HIGH — Rates: payload hợp lệ theo Pydantic nhưng vi phạm unique/FK → `IntegrityError` xuyên router → 500

- **Vị trí**: `schemas/v2/rate.py::RateAggregateBaseSchema` (~dòng 127–166, thiếu validator uniqueness `lines`), `services/rate_service.py::_resolve_source` (~dòng 229–247, không check supplier tồn tại/khớp product), `routers/v2/rates.py` (chỉ bắt `RateValidationError`/`RateConflictError`).
- **Cơ chế lỗi**: (a) Hai lines cùng `(price_for, occupancy_basis, unit, coalesce(tier_min_pax,-1))` → index `uq_rate_price_lines_rate_combo` bắn `IntegrityError` tại `replace_lines.flush` → 500 (đã tái hiện: `sqlite3.IntegrityError: UNIQUE constraint failed`). Xảy ra ở cả create/update/supersede — với supersede là **giữa transaction** sau khi đã insert header mới (rollback đúng nhờ session bị hủy, nhưng client nhận `INTERNAL_ERROR retryable=true`). (b) `source.supplier_id` không tồn tại: SQLite test không bật FK nên probe trả 201 (provenance rác), Postgres sẽ 500 tại `insert_source.flush`. (c) `source.supplier_id` khác `product.supplier_id` → provenance trỏ sai NCC, không ai chặn.
- **Kịch bản kích hoạt**: `POST /products/{id}/rates` với `lines=[{adult,na,person,1},{adult,na,person,2}]` → 500. `source={"supplier_id":"sup_nope"}` → 201 (SQLite) / 500 (Postgres).
- **Fix** (schema + service): validator `model_validator` trên `RateAggregateBaseSchema` kiểm tra tổ hợp unique của `lines` → `ValueError` (422 `VALIDATION_FAILED` đúng envelope). `_resolve_source`: `supplier_repository.get_by_id(source.supplier_id)` → None → `RateValidationError`; nếu product có `supplier_id` và khác → `RateValidationError("source supplier must match product supplier")`. Router thêm `except IntegrityError → 409/422` như lưới cuối (cùng pattern `CostingSheetSlotTakenError`).
- **Test bắt buộc**: `tests/test_rate_api.py::test_duplicate_price_line_combo_returns_422`, `::test_source_with_unknown_supplier_returns_422`, `tests/test_rate_service.py::test_source_supplier_must_match_product_supplier`.

### §2.7 M1 🟡 MEDIUM — Sửa qty của dòng catalog sau khi rate bị supersede → 422 bắt buộc; spec chỉ cắt `tariff_id` khi sửa **cost**

- **Vị trí**: `services/costing_service.py::update_line` (~dòng 274–300) → `_resolve_line_values` → `_resolve_catalog_line` (re-resolve từ rate **live**).
- **Cơ chế lỗi**: `update_line` không phân biệt "sửa qty/note/day" với "đổi rate". Mọi PUT mang `product_id` đều re-resolve từ catalog và **re-snapshot `unit_cost_minor` từ rate live** — đúng khi rate còn active (immutable nên cùng số), nhưng sau supersede → 422 `"rate is not active"`. Đường thoát duy nhất của FE là gửi dạng manual → `tariff_id`/`price_line_id`/`product_id` bị cắt → mất truy vết R3 cho một thao tác chỉ đổi số phòng. Đây là R3 bị áp ngược: snapshot lẽ ra bảo vệ line khỏi rate, giờ rate cũ khoá luôn line.
- **Kịch bản kích hoạt** (đã tái hiện): tạo line từ rate v1 → supersede → PUT cùng `rate_id/price_line_id`, `qty_unit=5` → 422.
- **Fix** (service): trong `update_line`, nếu `payload.rate_id == line.tariff_id and payload.price_line_id == line.price_line_id` → **không re-resolve**; giữ nguyên snapshot cost/tariff, chỉ cập nhật các trường phi-giá (qty, day, date, note, sort, fx, sell_override). Chỉ khi `rate_id` đổi mới đi qua `_resolve_catalog_line` (rate mới phải active — đúng chốt). Khi payload không có `product_id` nhưng `unit_cost_minor` **bằng** snapshot → vẫn cắt tariff theo spec (sale đã chủ động chuyển sang manual).
- **Test bắt buộc**: `tests/test_costing_service.py::test_qty_edit_on_catalog_line_survives_rate_supersede` (assert `tariff_id` giữ nguyên, `unit_cost_minor` giữ nguyên, `cost_minor` đổi theo qty).

### §2.8 M2 🟡 MEDIUM — `pick_price_line` bỏ qua `unit` và chọn first-match khi tier chồng lấn (T6 cấp price line)

- **Vị trí**: `core/rules/rate_selection.py::pick_price_line` (~dòng 85–103); unique index `uq_rate_price_lines_rate_combo` chỉ khoá `tier_min_pax`, không khoá overlap `[tier_min, tier_max]`.
- **Cơ chế lỗi**: Rate có 2 lines `adult/na/person` và `adult/na/group` (hợp lệ theo index vì khác `unit`) → `pick_price_line(lines,"adult","na",pax)` trả dòng đứng trước theo `sort_order`, không xét `unit`. Tier `1–5` và `3–10` cùng tồn tại (index chỉ chặn trùng `tier_min`) → pax 4 khớp cả 2, trả dòng đầu **không cờ conflict** — trái với triết lý T6 ("pure code không bao giờ tự quyết"). Consumer: `draft_run_service._resolve_price_serverside` và `toolsets/catalog.resolve_applicable_rates` → AI drafter chọn giá sai im lặng.
- **Kịch bản kích hoạt**: rate với lines `[{adult,na,person,tier 1–5, 100}, {adult,na,person,tier 3–10, 80}]` → `pick_price_line(…, pax=4)` → dòng 100, không cảnh báo.
- **Fix** (pure rule + rate_validation, không đổi schema): `pick_price_line` nhận thêm `unit: str | None` và trả `PriceLineSelection(candidates, has_conflict)` giống `select_rates`; thêm issue `PRICE_LINE_TIER_OVERLAP` (WARNING) vào `validate_rate_for_activation` khi 2 lines cùng `(price_for, occupancy_basis, unit)` có tier giao nhau. Caller AI: `has_conflict → rate_conflict` flag như hiện có.
- **Test bắt buộc**: `tests/test_rate_selection.py::test_pick_price_line_flags_overlapping_tiers`, `::test_pick_price_line_respects_unit`; `tests/test_rate_validation.py::test_overlapping_tiers_warn`.

### §2.9 M3 🟡 MEDIUM — `markup_rate_bps`/`rounding_increment_minor` không có cận trên → tràn `Integer` Postgres → 500

- **Vị trí**: `schemas/v2/costing.py::CostingSettingsUpdateSchema` (~dòng 40–41, chỉ `ge=0`); `db/models/costing.py::CostingSheet` cột `Integer`.
- **Cơ chế lỗi**: Pydantic `int` không giới hạn; SQLite chấp nhận (probe không lỗi) nên test không bắt được; Postgres `integer` 32-bit → `DataError` → 500. `markup_rate_bps = 10**9` (10.000.000%) cũng vô nghĩa nghiệp vụ nhưng hợp lệ về schema. Tương tự `qty_unit`/`qty_time` không có `le` → `cost_minor` khổng lồ đẩy vào `costing_applications.sell_total_minor` (BigInteger, ok) nhưng `margin_bps` vẫn `Integer`.
- **Kịch bản kích hoạt**: `PUT /settings {"markup_rate_bps": 2**40}` trên Postgres → 500.
- **Fix** (schema): `markup_rate_bps: Field(ge=0, le=100_000)` (1000%), `rounding_increment_minor: Field(ge=0, le=10**9)`, `qty_unit/qty_time: Field(ge=1, le=10_000)`. Không đổi DB.
- **Test bắt buộc**: `tests/test_costing_api.py::test_settings_bounds_return_422`.

### §2.10 M4 🟡 MEDIUM — Repository tự gọi `session.rollback()` (3 chỗ): phá ranh giới transaction của caller

- **Vị trí**: `repositories/costing_repository.py::insert_sheet` (~dòng 129), `::attach_to_quotation` (~dòng 213), `::insert_line` (~dòng 241).
- **Cơ chế lỗi**: Router là nơi duy nhất commit (đúng), nhưng repository lại là nơi rollback (sai tầng). `insert_line` rollback khi trùng idempotency key → mọi thay đổi **chưa commit** của caller trong cùng session bị xoá: `draft_run_service.run_draft` tạo N lines trong 1 session rồi mới `_insert_run_record`; một `CostingLineDuplicateError` ở line k (twin đồng thời) xoá sạch line 1..k-1 rồi service "replay" trả workbench như không có gì → run record ghi `created_line_ids` chứa id không tồn tại. Với router đơn lẻ thì vô hại (session bị hủy sau đó), nên smell này chỉ lộ qua consumer 15.7/15.8.
- **Kịch bản kích hoạt**: `run_draft` 3 ngày; request thứ 2 cùng `idempotency_key` đến khi request 1 đang ở ngày 3 → request 1 mất lines ngày 1–2 nhưng vẫn báo `succeeded`.
- **Fix** (repository + service): dùng `async with self.session.begin_nested()` (SAVEPOINT) quanh `flush` trong 3 hàm; `IntegrityError` → rollback **savepoint** rồi raise typed error. Caller giữ nguyên transaction.
- **Test bắt buộc**: `tests/test_costing_service.py::test_duplicate_line_key_does_not_discard_uncommitted_sibling_lines` (tạo line A chưa commit → insert line B trùng key với line đã commit → assert A vẫn flush được và commit thành công).

### §2.11 M5 🟡 MEDIUM — `list_by_product`: `total` = số item của trang; `on_date` bỏ qua blackout

- **Vị trí**: `repositories/rate_repository.py::list_by_product` (~dòng 25–48) `return items, len(items)`; filter `on_date` chỉ so `valid_from/valid_to`.
- **Cơ chế lỗi**: Contract `{items,total}` §1.6 ngụ ý `total` là tổng thoả filter; với `limit` nhỏ hơn tổng, FE `RatePanel` không thể biết còn trang sau. `on_date` ("lọc rate phủ ngày đó") trả cả rate đang blackout ngày đó → `AddServiceLineFlow` gợi ý rate mà `create_line` sẽ từ chối (H3) — vòng lặp UX. Đã tái hiện: 3 draft, `limit=1` → `total=1`.
- **Fix** (repository): `select(func.count()).select_from(stmt.subquery())` cho total; blackout lọc ở service sau khi load (JSON) hoặc bỏ `on_date` khỏi SQL và dùng `select_rates` — thống nhất với H3.
- **Test bắt buộc**: `tests/test_rate_api.py::test_list_total_counts_beyond_limit`, `::test_on_date_excludes_blackout`.

### §2.12 M6 🟡 MEDIUM — N+1 trong `_to_workbench` (2 query/dòng catalog, trần 500 dòng) và `_to_response` (1 query source/rate)

- **Vị trí**: `services/costing_service.py::_to_workbench` (~dòng 604–689) gọi `_product_ref` (~dòng 691–701) per line: `product_repository.get_by_id` + `destination_repository.get`; `services/rate_service.py::_to_response` gọi `get_source` per rate trong list.
- **Cơ chế lỗi**: Mỗi write (create/update/delete line, settings) trả nguyên workbench → mỗi thao tác grid = 1 + 2N query; sheet 200 dòng = ~400 round-trip cho một lần đổi qty. `session.get` có identity-map cache nên cùng product lặp lại rẻ, nhưng destination/product khác nhau vẫn N. Không sai dữ liệu, nhưng vi phạm ngân sách INP của workbench và là lý do thật để FE "preview" lệch server (chốt #4).
- **Fix** (service): gom `product_id` distinct → `select(Product).where(Product.id.in_(ids))` 1 query; destination tương tự; `_to_response` list: 1 query `RateSource.id.in_(source_ids)`.
- **Test bắt buộc**: `tests/test_costing_service.py::test_workbench_query_count_is_bounded` (dùng `event.listen(engine.sync_engine, "before_cursor_execute")` đếm ≤ 6 query cho 50 lines/10 product).

### §2.13 M7 🟡 MEDIUM — Float trong outbox payload `catalog.rate.superseded`; `validate_amount_minor` là dead API; `expire` không tồn tại

- **Vị trí**: `services/rate_service.py::_line_diff_summary` (~dòng 309–325) `round(((new-old)/old)*100, 2)`; `core/kernel/money.py::validate_amount_minor` (0 caller ngoài test); `RateService` docstring thừa nhận `expire` "out of scope".
- **Cơ chế lỗi**: Chốt #5 (15.4) và K1: "0 phép float", "No float ever crosses this line" — `min_pct`/`max_pct` là float chảy vào `outbox_events.payload_json` → notification 15.6 hiển thị; không phải tiền nhưng là *diff của tiền* và là tiền lệ. `validate_amount_minor` không được `RateService`/`CostingService` gọi (amount chỉ dựa vào Pydantic `ge=0`) → kernel có API không ai dùng, exit gate 15.3 #5 "kernel 3 file" đúng về hình thức, sai về nội dung. State machine §1.5 có `expire` nhưng không có endpoint/service → rate hết hạn giữ `active` vĩnh viễn; `list_by_product(lifecycle="active")` trả rate 2024 cho UI năm 2026 (H3 làm nặng thêm vì costing không lọc ngày khi `service_date=None`).
- **Fix**: `_line_diff_summary` trả `min_delta_bps`/`max_delta_bps` integer (`_round_half_up_div((new-old)*10_000, old)` — tái dùng helper của `costing_rules`, move helper về `core/kernel/money.py`); dùng `validate_amount_minor` trong `_line_values`/`_resolve_manual_line` hoặc xoá khỏi kernel; thêm `expire` như CAS transition (cùng guard C1) hoặc ghi rõ vào 15.3 §5 rằng bỏ.
- **Test bắt buộc**: `tests/test_rate_service.py::test_superseded_event_payload_is_float_free` (walk payload, assert không có `float`); `tests/test_kernel_money.py::test_validate_amount_minor_has_a_production_caller` (grep-style như tz-purity test).

### §2.14 M8 🟡 MEDIUM — Booking mirror ghi `service_lines.booking_status` không bump `costing_revision`

- **Vị trí**: `services/booking_service.py::_mirror_service_line_status` (~dòng 448–452) — ngoài Track 2 nhưng **ghi vào bảng của Track 2** vòng qua `CostingRepository` mà không qua `_bump_revision_guarded`.
- **Cơ chế lỗi**: Chốt #7 15.4: "`costing_revision` bump mỗi write vào sheet HOẶC lines". Booking đổi trạng thái line → FE workbench giữ `baseCostingRevision` cũ vẫn hợp lệ → PUT line đó → `_guard_booked_line` chặn 409 (đúng), nhưng grid không có tín hiệu reload nào, và `drift.costing_modified_since_apply` không phản ánh. Thuộc 15.6 nhưng là backdoor duy nhất còn lại ghi `service_lines` không CAS.
- **Fix**: route qua `CostingRepository.update_line_status(sheet, line, status)` gọi `_bump_revision_guarded` với `expected_revision=sheet.costing_revision` (đọc trong cùng transaction).
- **Test bắt buộc**: `tests/test_booking_service.py::test_handoff_bumps_costing_revision`.

---

## 3. §2.7 Danh sách test nợ theo spec (Bổ sung cùng đợt fix)

| # | Nợ | Spec | Hiện trạng | Test cần thêm |
| :-: | :-- | :-- | :-- | :-- |
| 1 | **Supersede atomicity** — "giả lập fail giữa chừng không để lại 2 active" | 15.3 §3, §6 | Không có test nào inject fail giữa `insert_rate` và `set_lifecycle_status(old)`; probe cho thấy race 2-session sinh 2 active (C1) | `test_rate_service.py::test_supersede_midway_failure_leaves_exactly_one_active` (patch `replace_lines` raise → assert old vẫn `active`, không có rate mới) + test C1 |
| 2 | **Float-free validation** toàn tuyến | 15.4 chốt #5, K1 | `test_costing_rules` chỉ test số; không có test walk output/payload | `test_costing_rules.py::test_summary_dataclasses_contain_only_int`; `test_rate_service.py::test_superseded_event_payload_is_float_free` (M7) |
| 3 | **CAS collision replay** — "2 write đua → 1 thắng 1 409" **và** người thua reload + retry thành công | 15.4 §4 | Có test thua → 409; **không** có test retry với `currentRevision` từ 409 thành công, không có test đua `update_settings` vs `create_line` (CS1) | `test_costing_service.py::test_loser_retries_with_current_revision_and_wins`; `::test_currency_change_races_line_insert_exactly_one_wins` |
| 4 | **Snapshot immutability sau update** | 15.4 §1.6 (R3) | Có test supersede-không-đổi-line; **không** có test PUT line (qty) giữ `unit_cost_minor` sau supersede (M1 chứng minh hiện tại là 422) | `test_qty_edit_on_catalog_line_survives_rate_supersede` (M1) |
| 5 | **Tz mốc `18:00Z`** — service layer quy đúng local date | 15.3 §3, 15.4 §4 | Không tồn tại ở cả `test_rate_service`, `test_costing_service`, `test_flow3` (chỉ set `timezone` trên destination) | `test_costing_service.py::test_service_date_is_local_date_not_utc_instant` — nếu BE nhận ISO datetime từ FE tương lai, phải reject hoặc quy theo `destination.timezone`; hiện tại schema là `date` nên test khoá contract: `service_date` là `date`, không phải `datetime` (assert schema type + 422 khi gửi datetime) |
| 6 | **Rate cho product tuyến A→B không lẫn B→A** | 15.3 §3 (G2) | Có ở `test_flow3_rates_e2e` mức pure; chưa có ở `costing.create_line` | `test_costing_service.py::test_catalog_line_rejects_rate_of_sibling_route_product` |
| 7 | **Idempotent create-line với payload khác** | K8 | Test hiện có replay cùng payload; không có test cùng key khác payload (hiện trả workbench cũ im lặng) | `::test_same_idempotency_key_different_payload_returns_existing_not_new` (khoá hành vi hoặc đổi thành 422) |
| 8 | **Migration `_39`/`_40` up/down trên Postgres** | 15.3 §4, 15.4 §4 | Suite chỉ chạy `Base.metadata.create_all` trên SQLite; partial index/`coalesce` index chưa từng chạy qua alembic trên PG trong CI | Job CI `alembic upgrade head && alembic downgrade 20260830_38 && upgrade head` trên PG service container |
| 9 | **Unique combo lines & FK source** | 15.3 §1.4 | Không có test → H4 lọt | Test H4 |
| 10 | **Bounds schema** | — | Không có | Test M3 |

---

## 4. §2.8 Exit Gate của Track 2

1. **C1, C2, H1, H2, H3, H4 fix** + toàn bộ "Test bắt buộc" của từng mục và 10 test nợ §3 xanh. Thứ tự đề nghị: C1 (CAS lifecycle rates) → H2 (replace_lines qua ORM collection) → C2 + H1 (currency/fx guard, cùng file) → H3 (đưa costing về `rate_selection`, kéo theo M5 `on_date`) → H4 (validator lines + source).
2. **M1–M8 fix** (M1 phụ thuộc H3 — làm ngay sau; M4 độc lập; M6 làm cuối vì chỉ hiệu năng; M8 nằm ở 15.6, có thể tách PR riêng nhưng phải đóng trước khi nghiệm thu Track 2 vì là backdoor ghi `service_lines`).
3. **Toàn bộ test suite + manifest contract xanh; migration không đổi.** Cụ thể:
   - `PYTHONPATH=. pytest` full suite xanh (baseline 87/87 của Track 2 giữ nguyên + test mới).
   - `tests/test_v2_api_manifest_contract.py` **không sửa** — mọi fix trên đều ở service/schema/repository, không thêm/bớt operation; H1 chỉ đổi mã lỗi 500→422 trong envelope hiện có.
   - `alembic/versions/20260901_39_rates.py`, `20260902_40_costing.py` **không đổi một byte** — C1 dùng CAS SQL không cần constraint; H4 dùng validator không cần unique mới; M3 dùng bounds schema không cần đổi kiểu cột.
   - Grep gate giữ nguyên: `core/rules/rate_selection.py` không `zoneinfo|today|now`; `db/models/rate.py`/`schemas/v2/rate.py` không `destination|origin`; kernel vẫn 3 file (`ids.py`, `actor.py`, `money.py`) — nếu M7 move `_round_half_up_div` về kernel thì vẫn nằm trong `money.py`.
   - `cd quote-generator && npm run lint && npm run build` xanh (FE chỉ cần đổi mã lỗi hiển thị cho H1/H3 candidates — không đổi contract type).

---

## 5. Re-review sau commit `8339ed6` ("fix: close track 2 rates and costing audit")

Phương pháp: đọc toàn bộ diff (30 file, +1248/−186), chạy lại 15 suite liên quan (`160 passed`),
chạy lại 11 probe của §1.4 trên tree mới. Kết luận: **C1, C2, H1–H4, M1–M8 đã đóng đúng cách**;
còn lại 5 điểm nhỏ (không blocker) ghi ở §5.2.

### 5.1 Đối chiếu từng finding

| ID | Trạng thái | Bằng chứng |
| :-: | :-- | :-- |
| C1 | ✅ Đóng | `set_lifecycle_status` = `UPDATE … WHERE lifecycle_status = :expected`, `rowcount != 1 → RateLifecycleRaceError → 409`. Supersede claim old→superseded **trước** khi insert new (thứ tự đúng). Probe 2-session giờ ném `RateConflictError`. Test `test_concurrent_supersede_second_writer_gets_conflict`, `test_concurrent_activate_emits_exactly_one_event`, `test_supersede_failure_rolls_back_predecessor_transition` |
| C2 | ✅ Đóng | `_resolve_line_values` chặn `cost_currency == sheet.currency and fx is not None` → 422 tường minh; FE tự null fx khi tệ trùng. Probe: `CostingValidationError: fx_rate_ppm must be omitted…` |
| H1 | ✅ Đóng | `CostingService._currency` bọc kernel → `CostingValidationError`; router settings bắt thêm 422. Probe HTTP: 3/3 endpoint trả 422 `VALIDATION_FAILED` |
| H2 | ✅ Đóng | `replace_lines` nhận `Rate`, `refresh(attribute_names=["lines"])` → `clear()` → flush → `append`. Probe PUT trả đúng 2 lines mới |
| H3 | ✅ Đóng | Schema bắt buộc `service_date` khi có `product_id`; `_resolve_catalog_line` đi qua `select_rates` + `pick_price_line(unit=…)` với pax từ facts/request; `candidates` có dữ liệu thật. Mapper ORM→pure gom về `services/rate_candidates.py` (xóa bản copy trong toolset, giữ alias tương thích) |
| H4 | ✅ Đóng | Validator uniqueness lines ở schema; `_validate_source_supplier` (tồn tại + khớp product); router bắt `IntegrityError` → 422 làm lưới cuối |
| M1 | ✅ Đóng | `same_catalog_snapshot` → `_snapshot_catalog_values(existing_line)` — qty edit giữ nguyên `tariff_id`/`unit_cost_minor` sau supersede (probe + test) |
| M2 | ✅ Đóng | `pick_price_line` trả `PriceLineSelection(candidates, has_conflict)` + tham số `unit`; `PRICE_LINE_TIER_OVERLAP` warning ở activation; 3 caller (costing, draft_run, toolset) cập nhật |
| M3 | ✅ Đóng | `markup_rate_bps le=9_500`, `rounding le=1e9`, `qty le=10_000`, `fx le=1e12` |
| M4 | ✅ Đóng | 3 chỗ `session.rollback()` → `begin_nested()` SAVEPOINT; line pending bị hủy cùng savepoint khi CAS thua (đóng luôn lo ngại "phantom line"). Test `test_duplicate_line_key_does_not_discard_uncommitted_sibling_lines` |
| M5 | ✅ Đóng | `total` đếm sau filter; `on_date` lọc blackout qua pure predicate ở service |
| M6 | ✅ Đóng | `get_by_ids` batch cho product/destination/source; test đếm query `test_workbench_query_count_is_bounded_for_many_catalog_lines` |
| M7 | ✅ Đóng | `_delta_bps` integer half-up; `validate_amount_minor` có caller thật ở cả 2 service; test float-free payload |
| M8 | ✅ Đóng | Booking mirror đi qua `CostingRepository.update_line_booking_status` → `_bump_revision_guarded` |
| Nợ test §3 | ✅ 9/10 | Workflow CI `track2-postgres-migrations.yml` (upgrade head → downgrade `_38` → upgrade + assert index/constraint trên PG16). Nợ #5 (tz `18:00Z`) đóng bằng contract test `service_date` là `date` (từ chối datetime) — chấp nhận được vì BE không có điểm quy đổi instant→date |

### 5.2 Điểm còn lại sau fix (không blocker; xử lý trong đợt dọn kế tiếp)

| # | Mức | Vị trí | Vấn đề | Đề nghị |
| :-: | :-- | :-- | :-- | :-- |
| R1 | 🟡 M | `services/costing_service.py::_authoritative_party_size` (~L639) | Nhánh quotation đọc `get_version_facts` — đúng cho mọi quotation sinh qua `generate_quotation_from_request` (L798) và tạo thủ công (`main.py` L5168), nhưng **working tree chưa commit** đã chuyển các chỗ khác trong cùng file sang `get_current_facts` (có fallback `quotation_requests.request_json`). Hàm này còn kẹt ở `get_version_facts` → khi Track 3 land, quotation legacy chỉ có request row sẽ 422 "Authoritative Facts must include…" trên sheet Flow 2 dù các chỗ khác đọc được | Dùng `get_current_facts` cho nhất quán; test `test_party_size_falls_back_to_request_json_when_no_version_facts` |
| R2 | 🟡 M | `services/costing_service.py::_resolve_catalog_line` (~L557) | `list_by_product(lifecycle="active")` → rate `superseded`/`draft` được chọn trả `"not found"` **không kèm `candidates`**, trong khi spec T6 yêu cầu 422 + candidates cho "rate hết hiệu lực". FE mất gợi ý đúng lúc cần nhất (rate vừa bị supersede giữa chừng thao tác) | Load rate theo id trước (`get_by_id`), nếu tồn tại nhưng không active → 422 với `candidates` từ `select_rates` |
| R3 | 🟢 L | `repositories/rate_repository.py::list_by_product` (~L29) | Tham số `on_date`, `limit` giờ **chết** (không dùng trong SQL) nhưng vẫn trong chữ ký; 4 caller vẫn truyền `limit=50/200` tưởng có hiệu lực. Product nhiều mùa/nhiều version sẽ load toàn bộ lịch sử superseded mỗi lần | Xóa 2 tham số khỏi repo (đổi chữ ký rõ ràng) hoặc áp `limit` khi `lifecycle` đã lọc chặt |
| R4 | 🟢 L | `services/rate_service.py::supersede` + `routers/v2/rates.py::supersede_rate` | Router supersede **không** có `except IntegrityError` như create/update/activate; validator schema đã chặn duplicate lines nên chỉ còn race FK hiếm → 500 | Thêm cùng handler cho đồng nhất |
| R5 | 🟢 L | `services/costing_service.py::_resolve_line_values` nhánh `same_catalog_snapshot` | Đổi `service_date` sang ngày rate không phủ (hoặc blackout) không bị re-validate vì giữ snapshot. Đúng tinh thần R3 (line bất động) nhưng nên có flag hiển thị | Tính `covers_service_date` và trả warning trong response (không chặn) |
| R6 | ℹ️ | Working tree (chưa commit) `apply_pricing` | `verify_revision_guarded` được dời lên **trước** `apply_pricing_option`. Vẫn an toàn trên PG vì UPDATE giữ row lock tới commit (writer đồng thời block rồi thua CAS), nhưng comment giải thích cửa sổ P1 của 16.3 bị xóa | Giữ lại comment 1 dòng nêu lý do row-lock để reviewer sau không dời ngược lại |

### 5.3 Kết luận nghiệm thu

- Exit gate §4 mục 1–3: **đạt** (C/H/M đóng, suite 160/160, manifest contract không đổi, migration `_39`/`_40` không đổi byte nào, kernel vẫn 3 file).
- R1–R6 là nợ nhỏ, không chặn merge Track 2; R1 nên đi cùng commit Track 3 đang mở trên working tree vì cùng file và cùng nguồn facts.
