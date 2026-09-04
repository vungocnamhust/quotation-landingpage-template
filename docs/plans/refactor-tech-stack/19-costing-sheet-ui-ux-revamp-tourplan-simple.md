# 19. Costing Sheet UI/UX Revamp — "TourPlan Simple" Day-by-Day Grid, Smart Product Picker & AI Data Flywheel

> **Loại tài liệu**: Đặc tả nâng cấp UI/UX + kiến trúc dữ liệu bổ trợ cho Costing Workbench
> (`/workspace/requests/{id}/costing` và stage `costing` trong Quotation Workspace).
> Viết từ góc nhìn Senior Travel-Tech Product Designer / Lead Fullstack Architect, đối chiếu
> trực tiếp mã nguồn đang chạy (audit ngày 2026-09-04, branch `master`, HEAD `2377328`).
>
> **Quan hệ với các plan trước**: Không mở lại bất kỳ chốt nào của
> [15.4 Costing](./15.4-costing.md), [15.5 Apply Pricing](./15.5-apply-pricing.md),
> [15.7 AI Service Drafter](./15.7-ai-service-drafter.md). Mọi đề xuất ở đây là **additive**:
> thêm cột, thêm bảng, thêm operation, thay lớp React UI — không đổi engine giá, không đổi
> bất biến snapshot/CAS/idempotency/integer-math, không đổi contract error envelope.
>
> **Quan hệ với plan 18**: Plan 18 §3.1 đặt Sale/Travel Designer là nút thắt số 1 ("mất thời
> gian dựng lại từ đầu mỗi báo giá"). Tài liệu này là spec kỹ thuật đầu tiên trả nợ cho
> nhận định đó ở đúng màn hình sale ngồi lâu nhất: bảng dự toán.

**Một câu**: Đưa Costing Sheet từ "một form nhập liệu nằm dưới một cái bảng" thành **ma trận
hành trình Day 1 → Day N** mà sale nhìn một phát thấy toàn bộ chi phí, thêm dịch vụ bằng 2 phím,
sửa giá ngay trên dòng, và mỗi lần chọn sản phẩm là một bản ghi dạy hệ thống chọn nhanh hơn
cho lần sau — trong khi engine tính giá server-authoritative của 15.4 không đổi một dòng.

---

## 0. Tóm tắt điều hành

| # | Kết luận | Bằng chứng / Hệ quả |
| :-: | :-- | :-- |
| 1 | **Engine giá hiện tại đúng và đủ chắc để giữ nguyên** | `core/rules/costing_rules.py` (integer math, markup bps, rounding, fx ppm, override), CAS `costing_revision`, snapshot R3, idempotency K8, apply-pricing 3-trong-1 nguyên tử — audit §1 không tìm thấy lỗi logic tiền. Toàn bộ revamp nằm ở tầng UI + tầng dữ liệu "học" |
| 2 | **UI hiện tại là "form-at-bottom" thuần kỹ thuật, không phải công cụ của Travel Designer** | 8 điểm yếu chí mạng ở §2: mất ngữ cảnh ngày, mắt đảo lên-xuống, dropdown phẳng toàn catalog (không lọc destination dù `ProductSelect` đã hỗ trợ `destinationId`), không có chiều Per Person / Per Group, không thao tác hàng loạt, không nhìn thấy dòng nào kéo tụt margin, không sửa inline (`editLine` có trong hook nhưng không được nối vào UI), đơn vị nhập liệu kỹ thuật (bps, minor units, ppm) |
| 3 | **Bài toán "Select Product" giải bằng ngữ cảnh + xếp hạng, không phải bằng dropdown to hơn** | Smart Product Picker (§3): mọi lần mở picker đều đã biết ngày, điểm đến, pax, hạng tour; catalog được lọc SQL theo `(destination_id, category, active)` rồi xếp hạng theo lịch sử chọn; rate + price line được server tự resolve bằng đúng `rate_selection` mà AI Drafter đang dùng — sale không còn chọn "Rate" rồi "Price line" bằng tay |
| 4 | **Data Flywheel = một bảng append-only + một materialized view + một tool read-only cho AI** | `costing_pick_events` ghi dấu vết mỗi quyết định chọn/đổi/xóa (người lẫn AI); `product_affinity` gộp thành chỉ số ưu tiên theo `(destination, category, tier, pax_bucket, month)`; AI Drafter thêm tool `suggest_products_from_history` đọc view này trước khi search catalog chung. Càng dùng, thứ tự gợi ý càng đúng; AI pre-fill dựa trên chứng cứ thay vì đoán |
| 5 | **Mô hình chi phí bổ sung 3 khái niệm còn thiếu, đều additive** | `pax_basis` (per_person / per_room / per_group) suy từ `unit` + `price_for` và **lưu snapshot** trên line; FOC (`foc_qty`) và Single Supplement (dòng sinh tự động từ `occupancy_basis=sgl` hoặc `supplements_json`) — tất cả vào `costing_rules.py`, FE chỉ hiển thị |
| 6 | **Lộ trình 3 đợt, đợt 1 không cần migration** | Đợt A (UI Day Grid + Picker có ngữ cảnh + inline edit): thuần frontend + 1 endpoint quick-pick tái dùng logic có sẵn. Đợt B (pax basis, FOC, SGL, bundle, copy-day): migration additive. Đợt C (pick events + affinity + AI tool): data flywheel |

---

## PHẦN 1 — BÁO CÁO LOGIC HIỆN TẠI CỦA COSTINGSHEET (AS-IS CODE AUDIT)

### 1.1 Bản đồ file (những gì thực sự chạy)

```text
Frontend (quote-generator/)
  app/workspace/requests/[id]/costing/page.tsx          Host Flow 1 (neo request) — recap + CTA "Tạo báo giá từ dự toán"
  components/quotation-workspace/QuotationWorkspaceClient.tsx   Host Flow 2 (stage "costing", neo quotation)
  components/quotation-costing/
    CostingWorkbench.tsx        Shell: resolve-or-create sheet, render SettingsBar + Table + AddLineFlow
    useCostingWorkspace.ts      Headless hook: SWR find/get + 7 mutation, CAS, 409 recovery, idempotency key
    CostingSettingsBar.tsx      Currency (khóa khi có line) · Markup bps · Round up · Cost/Sell/Margin · AI Draft · Apply
    ServiceLinesTable.tsx       Nhóm theo ngày (groupRowsByDay) — CHỈ những ngày đã có line
    ServiceLineRow.tsx          1 dòng: title/category/qty/cost/sell + nút Delete (+ Swap cho dòng AI)
    AddServiceLineFlow.tsx      Form nhập ở ĐÁY: tab catalog|manual, Day#, Qty×2, Service date, ProductSelect,
                                Rate select, Price line select, FX ppm, Sell override, Note, "+ Add line"
    ApplyPricingButton.tsx / ApplyPricingDialog.tsx / DriftBadge.tsx / AttachRecoveryBanner.tsx   (15.5)
    ai/AIDraftButton.tsx, useAiDrafter.ts, TripProfileReviewDialog.tsx, SwapLineDialog.tsx, deriveDaySpecs.ts (15.7)
  lib/rules/costingReconciler.ts   PURE, display-only: preview cost/sell, groupRowsByDay, splitSellTotalPerPerson
  lib/rules/costingAdapter.ts      Shape mapping: API ↔ rows, draft form ↔ ServiceLineWriteInput
  lib/costingToFactsHandoff.ts     Flow 1 one-shot: sheet → QuotationFacts (stays/destinations/pricing option)
  lib/quotationApi.ts §Costing     9 hàm HTTP + types (ServiceLineProfile, CostingSummary, …)
  components/product/ProductSelect.tsx + useProductSearch.ts   Dropdown product hiện tại (dùng chung với catalog admin)

Backend
  routers/v2/costing.py            9 operations (/api/v2/costing-sheets…) — parse, auth, map lỗi 409/422
  services/costing_service.py      Orchestration: resolve → snapshot → CAS → totals → attach → apply
  core/rules/costing_rules.py      PURE math: line_cost_minor, line_sell_minor, summarize
  core/rules/rate_selection.py     PURE: select_rates (date/blackout/pax), pick_price_line (tier)
  db/models/costing.py             CostingSheet + ServiceLine (1 aggregate)
  db/models/costing_application.py CostingApplication (append-only log của apply)
  schemas/v2/costing.py            Pydantic contract (ServiceLineWriteSchema, CostingWorkbenchResponseSchema, …)
  services/ai_drafter/draft_run_service.py   AI ghi line qua cùng CostingService.create_line (source="ai_draft")
```

> **Đính chính thuật ngữ**: prompt nhắc tới bảng `quotation_costing_settings`. Bảng này **không
> tồn tại** trong code hiện tại — plan 15.4 §1.3 đã thay nó bằng aggregate root `costing_sheets`;
> settings (currency, markup, rounding) là cột trên chính sheet. Mọi phân tích dưới đây dùng
> tên thật `costing_sheets` / `service_lines`.

### 1.2 Data Flow — mở trang costing thì dữ liệu nạp từ đâu

```text
[1] page.tsx (Flow 1)                      [1'] QuotationWorkspaceClient (Flow 2)
    useRequestDetail(id)                        facts resource của quotation (đã có)
      → recap header (tên KH, destinations,       → itinerary_days → aiDrafterDays
        start→end)                                → adultsCount/childrenCount/baseRevision/existingOptions
      → deriveAiDrafterDays(start_date,
        payload_json.itinerary_days)
        (chỉ ngày có destination_ref_id)
    ────────────────────────────────────────────────────────────────────────────────
[2] <CostingWorkbench anchor={{requestId}} | {{quotationId}}>
      useCostingWorkspace(anchor)
        SWR ["costing-sheet-find", kind, id]  → GET /api/v2/costing-sheets?requestId=|quotationId=
            ├─ sheet == null  → render "No costing sheet yet" + nút "Start costing sheet"
            │                     → createSheet() → POST /api/v2/costing-sheets {request_id|quotation_id}
            │                       409 (đã có sheet) → extractSheetIdFromConflict(regex) hoặc find lại → load sheet đó
            └─ sheet != null  → SWR ["costing-workbench", sheetId] → GET /api/v2/costing-sheets/{sheetId}
                                  ⇒ CostingWorkbenchResponse { sheet, items[], summary, applications[], drift }
[3] Mọi mutation (settings / addLine / editLine / removeLine / attach / applyPricing)
      gửi base_costing_revision = workbench.sheet.costing_revision (CAS)
      response = workbench mới → mutateWorkbench(result, {revalidate:false})  (không refetch)
      409 kind="conflict" → mutateWorkbench() reload authoritative + onConflict?() cho host refresh facts
```

**Backend `get_workbench` → `CostingService._to_workbench(sheet)`** (`services/costing_service.py`):

1. Sort lines theo `(day_number is None, day_number, sort_order)` — dòng trip-level (day NULL) xếp cuối.
2. Gọi `costing_rules.summarize(lines, markup_rate_bps, rounding_increment_minor)` → cost/sell từng line
   + `cost_total / sell_total / margin_minor / margin_bps / by_day[] / by_category[]`.
3. Enrich read-time (không JOIN chéo, đọc qua repo public): `product_ref {property_id, destination_id,
   destination_name, iata_code}` từ `ProductRepository.get_by_ids` + `DestinationRepository.get_by_ids`.
4. `rate_snapshot_stale` (R5): rate gốc không còn `active` hoặc `service_date` rơi ngoài validity/blackout
   → cờ **thông tin**, không re-price. *(Cờ này có trong `schemas/v2/costing.py:180` nhưng **không có** trong
   `ServiceLineProfile` phía FE → chưa bao giờ được hiển thị — xem §1.6.)*
5. Drift (15.5): so `sheet.costing_revision` với `costing_revision_at_apply` của application mới nhất, và so
   `group_total_amount_minor/currency` của option đích trong `pricing_facts` hiện tại với số đã áp.

#### Cấu trúc dữ liệu

**`costing_sheets`** (`db/models/costing.py`)

| Cột | Ý nghĩa vận hành |
| :-- | :-- |
| `quote_request_id` / `quotation_id` | Neo. CHECK ít nhất 1 NOT NULL. Partial unique: 1 sheet/quotation; 1 sheet chưa-attach/request |
| `currency` | Tiền tệ **bán** của sheet (sell currency). Default `VND` (deviation có ghi chú trong service: `infer_default_currency` chưa tồn tại). Khóa khi đã có line (CS1 → 409) |
| `markup_rate_bps` | Markup **toàn sheet**, đơn vị basis points (1 000 bps = 10 %). Không có markup per-line |
| `rounding_increment_minor` | Làm tròn **lên** giá bán từng dòng tới bội số này (0 = không làm tròn) |
| `costing_revision` | CAS — bump mỗi write vào sheet hoặc line |
| `attach_idempotency_key` | K8 cho attach |

**`service_lines`**

| Nhóm | Cột | Ghi chú audit |
| :-- | :-- | :-- |
| Vị trí | `day_number` (NULL = cả hành trình), `service_date`, `sort_order` | FE bắt gõ tay cả hai; không có ràng buộc `service_date = start_date + day_number - 1` |
| Định danh | `category`, `subcategory`, `title`, `supplier_id`, `product_id`, `tariff_id` (= rate id, tên wire đóng băng), `price_line_id` | Catalog line: snapshot từ product/rate; manual line: `product_id` NULL |
| Đơn vị | `unit` (room/person/vehicle/group/ticket/flight_seat/visa_case/set), `time_basis` (night/day/trip), `qty_unit`, `qty_time` | **Không có cột pax basis**; `unit` gián tiếp nói "per person" hay "per group" nhưng không nơi nào suy diễn |
| Tiền | `unit_cost_minor` (SNAPSHOT theo `cost_currency`), `cost_currency`, `fx_rate_ppm`, `sell_override_minor` (theo sheet currency) | Tách rõ cost currency vs sell currency (E1). FX gõ tay per line |
| Lifecycle | `booking_status` (quoted…cancelled), `source` (manual/ai_draft), `idempotency_key`, `ai_meta_json {reason, run_id, day_number, flags[]}`, `note` | Line ≠ `quoted` → khóa sửa/xóa (409, 15.6) |

**Frontend `ServiceLineProfile`** = các cột trên + `cost_minor`, `sell_minor` (server tính) + `product_ref`.
**`CostingSummary`** = `{cost_total_minor, sell_total_minor, margin_minor, margin_bps, by_day[], by_category[]}`.

### 1.3 Price Calculation Engine — từ Catalog sang dòng chi phí

#### (a) Đường chọn trên UI hiện tại (`AddServiceLineFlow.tsx`, tab "Pick from catalog")

```text
ProductSelect  ──useProductSearch(query, {active:"true", category: initialCategory})──▶ GET /api/v2/products?active=true&search=…
   │   ⚠ AddServiceLineFlow KHÔNG truyền destinationId, KHÔNG truyền category (initialCategory chỉ có khi Swap)
   │     ⇒ dropdown = toàn bộ catalog active, mọi destination, mọi category, ILIKE trên title_normalized
   ▼
draft.productId  ──SWR ["product-rates", productId, serviceDate]──▶ GET /api/v2/products/{id}/rates?lifecycle=active&on_date=…
   ▼
<select Rate>   (season_name — valid_from..valid_to (currency))
   ▼
<select Price line>  (price_for/occupancy_basis · unit · amount currency)   ← sale phải hiểu "adult/dbl · room"
   ▼
needsFx? (rate.currency ≠ sheet.currency) → <input FX rate ppm> gõ tay (1 000 000 = 1:1)
   ▼
canSubmit = productId && rateId && priceLineId && serviceDate && (!needsFx || fxRatePpm)
   ▼
onAdd(draftToWriteInput(draft))  → useCostingWorkspace.addLine → POST /lines + Idempotency-Key (uuid)
```

Nhận xét quan trọng: `qty_unit`/`qty_time` **mặc định 1/1 và không bao giờ được suy từ pax hay số đêm**.
Sale muốn 2 phòng × 3 đêm phải gõ 2 và 3; muốn vé cho 4 khách phải gõ 4.

#### (b) Server resolve & snapshot (`CostingService._resolve_catalog_line`)

1. Load `product`; load **mọi** rate của product (`lifecycle=None`) để lỗi luôn kèm danh sách candidates (T6).
2. `pax = _authoritative_party_size(sheet)` = `adults + children` lấy từ `quotation_version_facts.customer_facts`
   (neo quotation) hoặc `quote_requests.adults/children` (neo request). Thiếu → 422 "Authoritative Facts must include…".
3. `select_rates(candidates, service_date, pax)` (pure, 15.3): active + `valid_from ≤ date ≤ valid_to` + ngoài blackout
   + `min_pax ≤ pax ≤ max_pax`. Rate sale chọn phải nằm trong tập này, nếu không → 422 `{message, candidates[]}`.
4. `pick_price_line(lines, price_for, occupancy_basis, pax, unit)` → phải **duy nhất** (tier không chồng) → nếu không 422.
5. Snapshot ghi vào line:

```text
category      ← product.category        unit            ← price_line.unit
subcategory   ← product.subcategory     time_basis      ← product.time_basis
title         ← payload.title ?? product.title
supplier_id   ← product.supplier_id     unit_cost_minor ← price_line.amount_minor   (SNAPSHOT, R3)
product_id    ← product.id              cost_currency   ← rate.currency
tariff_id     ← rate.id                 price_line_id   ← price_line.id
```

Sau đó `_resolve_line_values` áp chung: FX bắt buộc khi `cost_currency ≠ sheet.currency` (và **cấm** khi bằng),
rồi copy `sell_override_minor, day_number, service_date, note, sort_order, qty_unit, qty_time` từ payload.

Sửa line (`update_line`): nếu `(product_id, rate_id, price_line_id)` không đổi → giữ nguyên snapshot
(`same_catalog_snapshot`, chỉ sửa qty/ngày/override); đổi cost bằng tay → đi nhánh manual → `tariff_id`/`price_line_id`
bị cắt (giá tay không giả danh giá catalog).

#### (c) Công thức (`core/rules/costing_rules.py`, integer toàn tuyến)

```text
line_cost_minor  = unit_cost_minor × qty_unit × qty_time
                   × (fx_rate_ppm / 1_000_000)  [round half-up, chỉ khi có fx]          → theo sheet.currency

line_sell_minor  = sell_override_minor                                   nếu override ≠ NULL (không re-round)
                 = round_up_to_increment( ceil( cost × (10_000 + markup_rate_bps) / 10_000 ),
                                          rounding_increment_minor )     ngược lại

summary.cost_total  = Σ cost        summary.sell_total = Σ sell
summary.margin_minor = sell_total − cost_total
summary.margin_bps   = round_half_up( margin_minor × 10_000 / sell_total )   (0 nếu sell_total = 0)
by_day[]      = gộp theo day_number (NULL là bucket riêng)
by_category[] = gộp theo category
```

Ví dụ thực (VND, divisor 1): phòng 2 500 000 × 2 phòng × 3 đêm = 15 000 000; markup 1 500 bps →
ceil(15 000 000 × 1,15) = 17 250 000; round up 10 000 → 17 250 000. Override 17 000 000 → sell = 17 000 000,
margin dòng = 2 000 000 (11,8 %).

**Ghi đè & margin**: override là **con số tuyệt đối** theo sheet currency, không phải "% khác". Margin không
lưu trên line; UI hiện tại chỉ hiển thị Cost và Sell từng dòng (`ServiceLineRow`), **không** hiển thị margin
dòng, nên sale không thấy dòng nào đang lỗ.

**FE preview** (`costingReconciler.previewLineSellMinor`) chỉ để vẽ số tạm giữa lúc gõ và lúc server trả;
`resolveLineDisplayTotals` luôn ưu tiên số server (chốt #4, không mirror engine). Hiện tại preview này thậm chí
**chưa được UI dùng** — form add-line không hiện số sell trước khi bấm Add.

### 1.4 Synchronization / Apply Flow — nút bấm thực sự làm gì

#### Flow 1 — "Tạo báo giá từ dự toán" (sheet neo request, one-shot handoff)

```text
page.tsx  push(`/workspace/quotations/new?requestId={id}&costingSheetId={sheetId}`)
  └─ NewQuotationClient
       fetch GET /api/v2/costing-sheets/{sheetId}  (SWR)  — chặn nếu sheet thuộc request khác (costingMismatch)
       initialFacts = buildInitialFactsFromRequest(request)
       facts = buildFactsFromCostingWorkbench(workbench, initialFacts)      ← lib/costingToFactsHandoff.ts (pure)
           1. accommodation lines có product_ref.property_id & day_number:
                for offset in 0..qty_time-1: itinerary[day_number-1+offset] ← {overnight, accommodation_id,
                accommodation_name=title, room_type=subcategory}  CHỈ điền chỗ trống
           2. các line khác có product_ref.destination_name → điền itinerary[day].destination nếu trống
           3. syncHotelsFromItineraryOvernights(facts)   ← prefillEngine (staysReconciler là SSOT cụm đêm)
           4. items>0 && sell_total>0 → pricing_facts.options[0] = {group_total_amount_minor = sell_total,
                currency = sheet.currency}; per_adult/per_child để null cho pricingReconciler suy sau
       sale review màn intake (prefill, sửa được mọi thứ)
       submit → POST /requests/{id}/generate-quotation
       thành công → POST /costing-sheets/{sheetId}/attach-quotation {quotation_id} + Idempotency-Key
           thất bại → lưu ATTACH_RECOVERY_PARAMS vào URL → AttachRecoveryBanner "Thử gắn lại"
```

Sau bước này sheet và facts **sống độc lập** (15.4 chốt #9).

#### Flow 2 — "Áp dụng giá vào báo giá" (sheet đã attach, 15.5)

```text
ApplyPricingButton  enabled ⇔ sheet.quotation_id && summary.sell_total_minor > 0
  └─ ApplyPricingDialog: chọn option đích (radio 1..3 hiện có, hoặc "Tạo gói mới" nếu < MAX_COMMERCIAL_OPTIONS=3)
       + label; preview "Giá hiện tại vs Tổng giá bán mới", delta, margin %, ước tính/khách
       (pricingReconciler.inferOptionRatesFromTotal, childRatio 0.75, display-only); cảnh báo nếu
       drift.commercial_modified_since_apply (option đã bị sửa tay sau lần áp trước)
  └─ onConfirm → CostingWorkbench.handleApplyPricing (throw nếu baseRevision == null — F-25)
       → useCostingWorkspace.applyPricing({base_revision, target_option_id, option_label}, idemKey, onConflict)
       → POST /api/v2/costing-sheets/{id}/apply-pricing
            body {base_revision (facts), base_costing_revision (sheet), target_option_id?, option_label?, lang?}
            header Idempotency-Key
       → GET workbench lại → applyResult(fresh); host onApplyPricingSuccess → refresh facts resource
```

Server `CostingService.apply_pricing` theo đúng thứ tự:

1. `summarize` từ DB (server-authoritative — **không** nhận số từ FE).
2. **Idempotent replay thắng mọi gate**: cùng key → trả lại application cũ (từ row bất biến), nhưng 409 nếu
   cùng key mà khác `base_costing_revision` / `base_revision` / `target_option_id` (key = một operation).
3. 422 nếu chưa attach; CAS sheet; 422 nếu 0 line; 422 nếu `sell_total ≤ 0`.
4. `verify_revision_guarded` — UPDATE có điều kiện giữ row lock `costing_sheets` tới khi commit (R6).
5. `api.runtime.apply_pricing_option(...)` — callback do `main.py` đăng ký, chạy đúng pipeline PUT facts
   (facts-side CAS, `DocumentRevisionConflictError` → 409). Ghi `group_total_amount_minor`, `currency` vào
   **một** option; giữ per-adult/per-child nếu cùng currency.
6. Insert `costing_applications` (snapshot sell/cost/margin/revision) + `OutboxService.emit_event("costing.applied")`.
7. Router `session.commit()` một lần — 3-trong-1 nguyên tử.

### 1.5 Bất biến đã được thi hành (giữ nguyên trong revamp)

| Bất biến | Nơi thi hành | Trạng thái |
| :-- | :-- | :-: |
| Minor units integer, 0 float | `costing_rules.py`, `validate_amount_minor` | ✅ |
| `cost_currency` tách `sheet.currency`; FX ppm snapshot per line | `_resolve_line_values` | ✅ |
| Snapshot R3 (rate supersede → line bất động) | `_resolve_catalog_line` + `same_catalog_snapshot` | ✅ |
| CAS `costing_revision` mọi write | `_check_revision`, repo guarded UPDATE | ✅ |
| Idempotency create-line / attach / apply | unique functional index + replay | ✅ |
| Server-authoritative totals, FE không cộng | `_to_workbench`, `costingReconciler` module doc | ✅ |
| Apply là hành động của sale, có log, có drift | 15.5 | ✅ |
| AI không có đường ghi riêng, output không có tiền | `draft_run_service` → `create_line(source="ai_draft")` | ✅ |

### 1.6 Hạn chế của logic hiện tại (những chỗ đang thiếu)

| # | Thiếu gì | Hệ quả thực địa | Chỗ trong code |
| :-: | :-- | :-- | :-- |
| L1 | **Không có chiều Cost Allocation (pax basis)** | Xe 16 chỗ 3 000 000/ngày và vé Tràng An 250 000/khách đều là "1 line" như nhau; giá/khách chỉ suy được ở dialog Apply bằng chia đều tổng (`inferOptionRatesFromTotal`). Không có "giá mỗi khách của dòng này" | `service_lines` không có `pax_basis`; `ServiceLineRow` không tính per-person |
| L2 | **`qty_unit` không suy từ pax / room config** | Vé, ăn, tour cho 4 khách: sale gõ 4 mỗi lần; phòng 2 DBL + 1 SGL: sale gõ và nhớ | `AddServiceLineFlow` default `qtyUnit: 1`; server không có TripProfile.room_config lúc create_line thủ công |
| L3 | **Không FOC** | Đoàn 16 khách, NCC cho 1 FOC → sale phải tự tính 15 và ghi note | Không cột `foc_qty`; `line_cost_minor` nhân thẳng `qty_unit` |
| L4 | **Không Single Supplement** | Khách lẻ / khách yêu cầu phòng đơn → sale tự thêm 1 line "phụ thu" bằng tay, tự tra `supplements_json` | Rate có `supplements_json` + price line `occupancy_basis=sgl` nhưng costing không dùng |
| L5 | **Không giá trẻ em tự động** | Price line `price_for=child` tồn tại ở 15.3, nhưng mỗi service line chỉ trỏ **một** price line → muốn tính 2 người lớn + 1 trẻ em phải thêm 2 line | `pick_price_line(price_for=…)` 1 lần / line |
| L6 | **Markup chỉ ở cấp sheet, override chỉ là số tuyệt đối** | Không thể "khách sạn markup 12 %, xe markup 25 %"; không có margin từng dòng để thấy dòng nào lỗ | `costing_sheets.markup_rate_bps`; `summarize` không trả margin/line |
| L7 | **Không bulk operations** | 3 đêm cùng khách sạn = `qty_time=3` OK, nhưng "guide 5 ngày liên tiếp" hoặc "copy Day 2 sang Day 3" = 5 POST bằng tay | Router chỉ có create 1 line; không batch, không copy |
| L8 | **Picker không ngữ cảnh** | `ProductSelect` **có** prop `destinationId` nhưng `AddServiceLineFlow` không truyền → toàn catalog phẳng | `AddServiceLineFlow.tsx` (`<ProductSelect category={initialCategory} …>`) |
| L9 | **Ngày trống vô hình** | `groupRowsByDay` chỉ sinh nhóm cho ngày có line; sale không thấy "Day 3 chưa có gì" | `ServiceLinesTable` |
| L10 | **`editLine` chưa nối UI** | Sửa qty/override phải xóa và thêm lại | `useCostingWorkspace.editLine` có, `CostingWorkbench` không dùng |
| L11 | **`rate_snapshot_stale` bị rơi** | Server báo rate hết hiệu lực, FE không có field → không badge | `ServiceLineProfile` thiếu field |
| L12 | **Đơn vị nhập liệu kỹ thuật** | "Markup (bps)" hiện `10` → sale hiểu 10 % nhưng thực tế 0,1 %; "Unit cost (minor)" với USD phải gõ cents; FX "ppm" | `CostingSettingsBar`, `AddServiceLineFlow` manual tab |
| L13 | **Manual tab: `unit`/`time_basis` là text tự do** | Gõ "Room" thay vì "room" → 422 từ server vocab | `AddServiceLineFlow` manual fields |
| L14 | **Không có ký ức chọn** | `ai_runs` log run của AI, nhưng không nơi nào ghi "sale đã chọn product X cho Hanoi/4★/4 pax" | Không bảng pick events |

---

## PHẦN 2 — MỔ XẺ UI/UX HIỆN TẠI (CRITICAL UX REVIEW)

Màn hình hiện tại (theo ảnh chụp + code) từ trên xuống: header request → SettingsBar (Currency / Markup bps /
Round up / Cost·Sell·Margin, nút AI Draft + Apply) → bảng dòng (trống: "No service lines yet — pick a product
or add a manual line below") → **form nhập ở đáy** (Day# · Qty(unit) · Qty(time) · Service date · Product ·
Rate · Price line · Sell override · Note · + Add line).

### 2.1 Tám điểm yếu chí mạng

**W1 — Mất ngữ cảnh chuyến đi (Context Blindness).**
Request đã biết `start_date`, `end_date`, `itinerary_days[].destination_ref_id`, `adults/children`. Vậy mà
form bắt sale gõ `Day #` bằng số, chọn `Service date` bằng date-picker, và tự nhớ "Day 2 là Ninh Bình".
Hai trường này còn có thể mâu thuẫn (Day 3 nhưng date là ngày 1). Cái sale cần nhìn là khung
`Day 1 · 20/12 · Hà Nội`, `Day 2 · 21/12 · Ninh Bình`… và bấm "+" ngay trên ngày đó.

**W2 — Mắt đảo lên-xuống, tay đảo chuột-phím (Form-at-bottom).**
Bảng ở trên, form ở dưới. Thêm 1 dòng: kéo xuống, điền 6–9 ô, bấm Add, kéo lên kiểm tra, kéo xuống điền tiếp.
Với một tour 8 ngày × 4 dịch vụ/ngày = 32 lần đảo. Không có phím tắt, không có focus trả về ô đầu sau khi Add.

**W3 — Dropdown Product nghèo nàn và nguy hiểm.**
Một danh sách phẳng, trộn khách sạn Sapa với xe Sài Gòn với vé Huế, chỉ có search chuỗi. Không lọc theo điểm
đến của ngày, không lọc theo hạng, không nhóm theo category, không "gần đây". Chọn nhầm "Metropole" cho ngày ở
Đà Nẵng là chuyện xảy ra được, và **server không cản** vì `create_line` không đối chiếu `product.destination_id`
với destination của ngày.

**W4 — Sau khi chọn product còn 2 dropdown kỹ thuật nữa: Rate và Price line.**
Sale phải đọc "adult/dbl · room · 2,500,000 VND" và hiểu đó là giá phòng đôi tính theo phòng. 90 % trường hợp
chỉ có 1 rate active và 1–3 price line; server đã có `select_rates` + `pick_price_line` để tự chọn (AI Drafter
đang dùng chính đường này) nhưng UI thủ công không tận dụng.

**W5 — Thiếu chiều phân bổ chi phí (Per Person vs Per Group).**
Không có cột nào nói dòng này chia đầu người hay gánh chung. Không có "giá/khách" từng dòng. Sale bán tour
per-person không thể đọc bảng này ra bảng giá bán.

**W6 — Không thao tác hàng loạt.**
Guide 5 ngày, xe 5 ngày, ăn trưa 5 ngày = 15 lần điền form. Không "copy ngày", không "áp cho các ngày còn lại",
không "Day bundle".

**W7 — Không kiểm soát được biên lợi nhuận theo dòng.**
Chỉ có tổng margin ở SettingsBar. Không cột margin/dòng, không màu cảnh báo, không sort theo margin, không
nhìn thấy override nào đang kéo tụt tổng. Dòng có `sell_override` thấp hơn cost vẫn hiện bình thường.

**W8 — Đơn vị và thao tác sửa mang tư duy backend.**
`Markup (bps)`, `Unit cost (minor)`, `FX rate ppm (1000000 = 1:1)`, `Round up to` — đúng với kernel nhưng sai
với người dùng. Muốn sửa qty phải **xóa dòng và thêm lại** (không có edit inline dù hook đã có `editLine`).
Trạng thái "rate đã hết hiệu lực" server có tính nhưng UI không hiện.

### 2.2 Những gì hiện tại làm ĐÚNG và phải giữ

- Resolve-or-create sheet trong hook, 409 recovery tự động (`extractSheetIdFromConflict`), toast.
- Mọi response mutation là cache mới → không flicker, không refetch thừa.
- Rõ ràng catalog vs manual, FX bắt buộc khi lệch tệ, currency khóa khi có line.
- Apply dialog có diff, cảnh báo drift, tối đa 3 option — giữ nguyên toàn bộ 15.5.
- AI Draft + Needs review + Swap — giữ, chỉ đổi chỗ đứng trong layout mới.
- HelpTooltip + `costingGlossary.ts` — mở rộng, không bỏ.

---

## PHẦN 3 — "SELECT PRODUCT" THÔNG MINH & CƠ CHẾ TÍCH LŨY CHO AI (DATA FLYWHEEL)

Bài toán: *chọn dịch vụ nhanh nhất, không bao giờ list toàn bộ catalog, giảm tối đa điền tay, và càng dùng
hệ thống/AI càng thông minh hơn.*

### 3.1 Nguyên tắc Zero-Typing

| Nguyên tắc | Cụ thể | Nguồn dữ liệu đã có |
| :-- | :-- | :-- |
| **Auto Context** | Bấm "+" trên Day 2 → picker mở với `day_number=2`, `service_date=start_date+1`, `destination_id` = destination của ngày, `origin_destination_id` = destination ngày trước (cho transport) | `quote_requests.start_date`, `payload_json.itinerary_days[].destination_ref_id` (Flow 1); `trip_facts.itinerary[]` (Flow 2); `datesRules.dateForItineraryDay` |
| **Pax Auto-fill** | `qty_unit` điền sẵn theo `pax_basis`: per_person → `adults + children` (tách 2 line adult/child khi rate có `price_for=child`); per_room → tổng `room_config[].count`; per_group → 1 | `quote_requests.adults/children/kid_ages`; `TripProfile.room_config` (15.7) hoặc `rooming_heuristic` fallback |
| **Nights Auto-fill** | Accommodation: `qty_time` = số đêm liên tiếp cùng overnight từ ngày đó (staysReconciler cụm đêm) | `staysRules` đã có |
| **Rate Auto-resolve** | Server tự `select_rates` + `pick_price_line` cho `(product, date, pax, occupancy)`; chỉ hỏi sale khi T6 conflict hoặc nhiều occupancy | `_resolve_price_serverside` (draft_run_service) — tách ra hàm dùng chung |
| **FX Auto-suggest** | Khi `rate.currency ≠ sheet.currency`, gợi ý `fx_rate_ppm` = lần gần nhất sale dùng cho cặp tệ đó trong tenant (vẫn snapshot, vẫn sửa được) | `service_lines.fx_rate_ppm` lịch sử (query đơn giản) |
| **Đơn vị người** | Nhập/hiển thị `%` cho markup, tiền theo major unit có format, FX dạng `1 USD = 25 400 VND` — adapter đổi sang bps/minor/ppm | `moneyFormat.ts`, `costingAdapter.ts` |

### 3.2 Smart Product Picker — thay thế hoàn toàn dropdown phẳng

#### Cấu trúc gọi

```text
PickContext = {
  sheetId, dayNumber, serviceDate, destinationId, originDestinationId,
  pax: {adults, children, infants, kidAges[]}, roomConfig[], qualityTier, market,
  sheetCurrency, alreadyPickedProductIds[]  (mọi line hiện có trên sheet)
}
```

Một endpoint đọc mới, trả về **đã xếp hạng, đã phân nhóm, tối đa ~40 item**, không bao giờ trả toàn catalog:

```text
GET /api/v2/costing-sheets/{sheet_id}/product-suggestions
    ?day_number=2&category=accommodation&q=metro&tier=4
→ {
    context: {destination_id, destination_name, service_date, pax},
    sections: [
      {key:"suggested", title:"Gợi ý cho chặng này",  items:[…≤5, kèm reason: "8/10 tour NB 4★ gần đây"]},
      {key:"recent",    title:"Dùng gần đây",          items:[…≤5]},
      {key:"catalog",   title:"Tại Ninh Bình · 4★",    items:[…≤30, phân trang]}
    ],
    each item: {product_id, title, supplier_name, category, subcategory, tier, unit, time_basis,
                rate_status: "ok" | "missing" | "conflict" | "fx_needed", price_band: "low|mid|high",
                affinity_score, last_picked_at, in_sheet: bool}
  }
```

Quy tắc lọc SQL (không lọc client): `tenant_id` + `is_active` + `category` (từ chip) + `effective_destination_id`
roll-up theo cây 15.2b (Hạ Long ⊂ Quảng Ninh) + với transport: `origin_destination_id` = ngày trước hoặc NULL +
`tier` từ `category_attributes.star_rating` / `quality_tier` (nếu có). Search `q` chạy trên `title_normalized`
(đã bỏ dấu) + alias supplier. `rate_status`/`price_band` tính bằng `rate_selection` với `service_date` + `pax`
(không trả số tiền — chỉ band, giống tool AI `resolve_applicable_rates`).

#### Hành vi UI (chi tiết ở wireframe W2, §4.3)

1. **Category Chips** hàng đầu: `🏨 Lưu trú · 🚗 Vận chuyển · 🎟️ Vé/Tour · 🍽️ Ăn uống · 🚩 Hướng dẫn · ✈ Bay · ⋯`
   — phím `1..7` chọn chip. Chip đầu tiên được **gợi ý theo ngày**: ngày chưa có accommodation → chip Lưu trú
   sáng; ngày có overnight khác ngày trước → chip Vận chuyển sáng.
2. **Ô tìm kiếm** focus sẵn, fuzzy không dấu (`metro` → Metropole; `emer` → Emeralda). Có thể gõ "xe 16"
   → subcategory `van_16_seat`.
3. **Bộ lọc nhanh**: Điểm đến (mặc định khóa theo ngày; bấm để nới ra hub/tỉnh), Hạng `3★ 4★ 5★`, Tier
   `value…ultra_luxury`, toggle "Chỉ có giá cho ngày này".
4. **Danh sách 3 tầng**: Gợi ý → Gần đây → Tất cả tại điểm đến. Mỗi item hiển thị badge rate (`✓ có giá`,
   `⚠ thiếu giá`, `⚠ 2 mùa giá`, `$ khác tệ`) và band giá (`$ $$ $$$`).
5. **Chọn** = `Enter` hoặc click → panel phải hiện "Tóm tắt dòng sẽ tạo": basis, qty đề xuất, đêm, giá net
   resolve được, giá bán dự kiến (preview từ `costingReconciler`, có ghi "tạm tính"). `Enter` lần 2 = tạo dòng.
   `Tab` chỉnh qty. Nếu T6 conflict → panel đổi thành danh sách rate để chọn. Nếu thiếu giá → cho phép
   "Tạo dòng với giá 0 + cờ cần tay" (như AI) hoặc "Nhập giá tay" hoặc "Tạo bảng giá" (mở `RateEditorDrawer`
   hiện có).
6. **Multi-add**: `Shift+Enter` = tạo dòng và giữ picker mở cùng ngữ cảnh (thêm tiếp dịch vụ khác cho ngày đó).
7. **Command Palette toàn cục** `⌘K`: cùng engine, nhưng bước đầu hỏi "ngày nào?" (gõ `d3` hoặc chọn).
8. **Day Bundle**: chip cuối `📦 Gói mẫu` liệt kê bundle của tenant khớp `(destination, tier)` — chọn 1 →
   bung N dòng bằng 1 request batch (§3.4).

#### Server: create-line "quick pick" (tái dùng, không engine mới)

```text
POST /api/v2/costing-sheets/{sheet_id}/lines:quick-pick     (Idempotency-Key)
body {base_costing_revision, day_number, product_id, occupancy_basis?, price_for?, qty_unit?, qty_time?,
      fx_rate_ppm?, sell_override_minor?, note?}
→ server: service_date = start_date + day_number - 1 (khi caller không gửi)
          pax = _authoritative_party_size (đã có)
          (tariff_id, price_line_id, flags) = resolve_price_serverside(...)   ← tách từ draft_run_service ra
                                                                                services/costing_pricing_resolver.py
          nếu flags ∋ rate_conflict → 422 {candidates[]}  (T6 y hệt hiện tại)
          nếu rate_missing → tạo line unit_cost=0 + ai_meta_json.flags=["rate_missing"] (đường AI đang dùng)
          còn lại → CostingService.create_line(payload đầy đủ)  → cùng snapshot, cùng CAS, cùng idempotency
          + ghi costing_pick_events (§3.3)
→ CostingWorkbenchResponse (như mọi write)
```

Endpoint `POST /lines` hiện tại **giữ nguyên** (manual + catalog đầy đủ) cho tab "Nhập tay" và cho tương thích.

### 3.3 Data Flywheel — lưu vết quyết định để AI tự pick và càng dùng càng nhanh

#### (a) Decision Footprint Log — bảng `costing_pick_events` (append-only, K5)

| Cột | Ghi chú |
| :-- | :-- |
| `id` (`cpe_` + uuid7), `tenant_id`, `created_at`, `created_by` (ActorRef: staff / ai_agent) | kernel |
| `sheet_id`, `line_id` (nullable — event `rejected` không có line) | truy vết |
| `event_type` | `picked_suggested` · `picked_search` · `picked_manual` · `ai_draft_created` · `ai_draft_accepted` (giữ qua apply/booking) · `ai_draft_swapped` · `removed` · `bundle_applied` |
| `product_id`, `supplier_id`, `category`, `subcategory` | cái gì được chọn |
| `replaced_product_id` | với `swapped`/`removed`: cái gì bị thay/bỏ |
| **Context snapshot** (denormalize để log tự đứng): `destination_id`, `origin_destination_id`, `day_number`, `day_index_ratio` (day/N: đầu-giữa-cuối tour), `service_month` (1–12), `pax_bucket` (`1-2 / 3-4 / 5-8 / 9-15 / 16+`), `quality_tier`, `archetype`, `market`, `sheet_currency` | key học |
| `suggestion_rank` (vị trí trong danh sách lúc chọn, NULL nếu search/manual), `query_text` (đã normalize) | đo chất lượng gợi ý |
| `run_id` (AI), `idempotency_key` | |

Ghi trong **cùng transaction** với `create_line` / `update_line` / `delete_line` (không outbox — đây không phải
integration event; là dữ liệu nội bộ). Không có cột tiền (Zero-Money Invariant áp cho log này luôn — giá đã
nằm trong `service_lines`).

#### (b) Co-occurrence & Affinity — materialized view `product_affinity`

```sql
-- refresh theo lịch (nightly) hoặc sau N events; đọc bởi picker + AI tool
(tenant_id, destination_id, category, quality_tier, pax_bucket, service_month)  → product_id,
  pick_count_90d, pick_count_all, accept_rate  (= 1 − swapped/removed ÷ picked),
  last_picked_at, avg_rank_when_picked,
  cooccur_json: {product_id_khác: count}   -- cùng sheet, cùng destination cluster
```

**Điểm xếp hạng** (tính lúc GET suggestions, pure Python trong `core/rules/pick_ranking.py`):

```text
score = 3.0·ln(1 + pick_count_90d)
      + 2.0·accept_rate
      + 1.5·recency_decay(last_picked_at, half-life 120 ngày)
      + 2.5·cooccurrence_boost(alreadyPickedProductIds)       -- "80 % tour có Emeralda thì có tour Tràng An"
      + 1.0·[rate_status == ok]  − 2.0·[rate_status == missing]
      + 0.5·[tier khớp chính xác]
      − 1.0·[in_sheet]                                          -- đã có trên sheet thì đẩy xuống
```

Trọng số là hằng số có tên, có test golden; không ML, không training — đủ cho DMC startup (plan 18 §5.6 "Lean AI").

#### (c) AI Pre-fill từ Footprint

- Thêm tool read-only vào `services/ai_platform/toolsets/catalog.py`:
  `suggest_products_from_history(destination_id, category, quality_tier, pax_bucket, service_month, already_picked[])`
  → ≤ 5 `{product_id, title, evidence: "12 lần / 90 ngày, accept 92 %"}` — **không tiền**.
- Prompt `service_drafter.yaml` bổ sung một câu chỉ dẫn: gọi tool lịch sử **trước** `search_*`; nếu có kết
  quả với `accept_rate ≥ 0.8` thì ưu tiên; ghi `selection_reason` nêu bằng chứng. Line tạo ra gắn
  `ai_meta_json.history_backed = true` → UI badge `📈 Theo lịch sử`.
- Chu trình khép kín: sale giữ line AI → `ai_draft_accepted`; swap → `ai_draft_swapped` + `replaced_product_id`
  → lần refresh view kế tiếp, product bị swap tụt điểm, product thay thế lên điểm.

#### (d) KPI & kill criteria (theo tinh thần plan 18 §5.9)

| KPI | Mục tiêu sau 60 ngày dùng thật |
| :-- | :-- |
| Thời gian từ mở sheet → dòng đầu tiên | < 20 giây (hiện ước ~90 giây) |
| Tỷ lệ dòng tạo từ mục "Gợi ý" hoặc "Gần đây" | ≥ 60 % |
| Tỷ lệ dòng AI draft bị swap | < 25 % và giảm theo tháng |
| Số lần gõ phím trung bình / dòng | ≤ 6 |
| Kill: sau 90 ngày tỷ lệ gợi ý được chọn < 30 % | tắt section "Gợi ý", giữ lọc ngữ cảnh |

---

## PHẦN 4 — ĐẶC TẢ "TOURPLAN SIMPLE COSTING SHEET" & WIREFRAME

### 4.1 Kiến trúc bố cục mới (Layout Hierarchy)

```text
┌ Sticky Executive Summary (luôn hiện khi cuộn) ─────────────────────────────────────────┐
│ Net · Sell · Margin % (màu) · /khách · Tệ + FX · Trạng thái drift · [AI Draft] [Áp giá] │
├ Toolbar ───────────────────────────────────────────────────────────────────────────────┤
│ Markup mặc định % · Làm tròn · Chế độ xem [Theo ngày | Theo loại | Margin] · ⌘K · Bộ lọc│
├ Itinerary Timeline Workspace (Day-by-Day Grid) ────────────────────────────────────────┤
│ ┌ Day 1 · Thứ Bảy 20/12 · Hà Nội · 4 khách ────────────────── Net · Sell · Margin ┐   │
│ │  🏨 lưu trú  │ 🚗 vận chuyển │ 🍽️ ăn │ 🎟️ vé │ 🚩 hướng dẫn  (nhóm theo category)   │   │
│ │  dòng inline editable …                                                          │   │
│ │  [+ Thêm dịch vụ  (A)]  [⧉ Sao chép sang ngày sau]  [📦 Gói mẫu]                 │   │
│ └──────────────────────────────────────────────────────────────────────────────────┘   │
│ ┌ Day 2 … ┐  … ┌ Day N … ┐                                                              │
│ ┌ Cả hành trình (visa, vé bay, HDV suốt tuyến, phụ thu) ┐                               │
├ Right rail (≥1280px) / Bottom sheet (mobile) ──────────────────────────────────────────┤
│ Margin Watch: 5 dòng margin thấp nhất · Theo category · Cảnh báo rate stale/thiếu giá   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

Nguyên tắc: **form không còn tồn tại như một khu vực**; mọi nhập liệu xảy ra tại chỗ (inline) hoặc trong
picker modal mở từ đúng ngày. Ngày trống vẫn hiện (khung từ itinerary), ngày có line hiện subtotal.

### 4.2 Wireframe 1 — Toàn cảnh Costing Sheet theo ngày

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ← Về request     Mr. & Mrs. Anderson · HAN → NBI → DAD · 20/12 → 27/12 (8N7Đ) · 2 NL + 2 TE (9, 12)  │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  NET  128.400.000 ₫    SELL  151.500.000 ₫    MARGIN  23.100.000 ₫ (15,2 %) ▲    ≈ 37.875.000 ₫/khách  │
│  Tệ: VND · 1 USD = 25.400 ₫ ·  ● Đã đồng bộ giá 14:02      [✨ AI Draft ▾]  [Áp giá vào báo giá →]     │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  Markup mặc định [ 15 % ]   Làm tròn [ 10.000 ₫ ]   Xem: (● Theo ngày) (○ Theo loại) (○ Margin)  ⌘K    │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌ DAY 1 · T7 20/12 · Hà Nội ──────────────────────────────────── Net 9.150.000 · Sell 10.530.000 ─┐  │
│ │  #  Loại  Dịch vụ · NCC                       Basis      SL        Net/đv     Net      Sell  Mg% │  │
│ │  1  🚗   Đón sân bay HAN → KS · Xe 7 chỗ      Per group  1 xe×1   1.200.000  1.200.000 1.380.000 13│  │
│ │        └ Green Car ·  ✓ giá mùa Đông 25/26                                                        │  │
│ │  2  🏨   Sofitel Legend Metropole · Grand Prem  Per room  2 ph×3đ  7.950.000 47.700.000 54.860.000 13│  │
│ │        └ DBL ×2 · BB ·  ✓ rate 01/11–31/03 · ⚠ 1 SGL supplement chưa áp                          │  │
│ │  3  🍽️   Tối phố cổ · Bún chả Hương Liên      Per person 4 kh×1     250.000  1.000.000  1.200.000 17│  │
│ │  ─────────────────────────────────────────────────────────────────────────────────────────────── │  │
│ │  [+ Thêm dịch vụ  A]   [⧉ Sao chép sang Day 2]   [📦 Gói mẫu Hà Nội 4★]          ▽ thu gọn        │  │
│ └───────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│ ┌ DAY 2 · CN 21/12 · Hà Nội → Ninh Bình ───────────────────────── Net 6.400.000 · Sell 7.540.000 ─┐  │
│ │  4  🚗   Xe 7 chỗ HN → NB (cả ngày)             Per group  1 xe×1   2.200.000  2.200.000 2.530.000 13│  │
│ │  5  🚩   HDV tiếng Anh · Mr. Tuấn               Per group  1 ×1 ng  1.500.000  1.500.000 1.730.000 13│  │
│ │  6  🎟️   Tràng An thuyền + Bái Đính             Per person 4 kh×1     300.000  1.200.000 1.380.000 13│  │
│ │  7  🏨   Emeralda Resort · Deluxe Garden        Per room  2 ph×1đ  ▒▒ thiếu giá 21/12 ▒▒  [Nhập giá] │  │
│ │        └ ✨ AI · "8/10 tour NB 4★ chọn" · ⚠ rate_missing                              [⇄ Đổi]     │  │
│ │  [+ Thêm dịch vụ  A]   [⧉ Sao chép…]                                                             │  │
│ └───────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│ ┌ DAY 3 · T2 22/12 · Ninh Bình ─────────────────────────────────────────── (chưa có dịch vụ) ────┐  │
│ │   Gợi ý: 🏨 Emeralda (đang ở, +1 đêm?)  🚗 Xe cả ngày  🍽️ Ăn trưa dê núi        [+ Thêm dịch vụ A] │  │
│ └───────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│   … DAY 4 → DAY 8 …                                                                                    │
│ ┌ CẢ HÀNH TRÌNH ────────────────────────────────────────────────── Net 12.000.000 · Sell 13.800.000 ┐ │
│ │  21 ✈   Vé bay HAN → DAD · Vietnam Airlines     Per person 4 kh×1   1.900.000  7.600.000  8.740.000 13│ │
│ │  22 📄   E-visa 4 khách                          Per person 4 kh×1   1.100.000  4.400.000  5.060.000 13│ │
│ └───────────────────────────────────────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ▎MARGIN WATCH   ▼ thấp nhất: #2 Metropole 13 % (override) · #7 Emeralda —  · ⚠ 1 dòng thiếu giá      │
│ ▎Theo loại: 🏨 62 % · 🚗 14 % · 🎟️ 8 % · 🍽️ 6 % · 🚩 5 % · ✈ 5 %                                    │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Chú giải hành vi:

- Header ngày lấy từ itinerary (Flow 1: `payload_json.itinerary_days` + `start_date`; Flow 2: `trip_facts.itinerary`).
  Đổi itinerary không tự đổi line (chốt 15.4 §6) — chỉ **cảnh báo** nếu `service_date` của line lệch ngày header.
- `Basis` là pill 3 màu: Per person (xanh), Per room (tím), Per group (cam). `SL` hiển thị `qty_unit đv × qty_time`
  bằng chữ người (kh/ph/xe × đêm/ngày).
- `Mg%` tô màu: ≥ 15 % xanh, 8–15 % vàng, < 8 % đỏ, âm đỏ đậm + icon. Ngưỡng là setting tenant.
- Phím: `A` thêm dịch vụ cho ngày đang focus, `J/K` di chuyển dòng, `E` sửa inline, `D` xóa (confirm),
  `C` copy sang ngày sau, `⌘K` palette, `⌘S` không cần (autosave từng thao tác như hiện tại).

### 4.3 Wireframe 2 — Smart Product Picker (mở từ "+ Thêm dịch vụ" của Day 2)

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  Thêm dịch vụ · DAY 2 · CN 21/12 · Ninh Bình  (từ Hà Nội) · 2 NL + 2 TE · Tier 4★            [Esc ✕] │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  🔍 [ tìm nhanh không dấu… "emer", "xe 16", "tràng an"                                            ]  │
│  (1)🏨 Lưu trú  (2)🚗 Vận chuyển  (3)🎟️ Vé/Tour  (4)🍽️ Ăn uống  (5)🚩 Hướng dẫn  (6)✈ Bay  (7)📦 Gói│
│  Điểm đến: [Ninh Bình ▾ (khóa theo ngày)]  Hạng: [3★] [4★●] [5★]  [☑ chỉ có giá 21/12]              │
├────────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  GỢI Ý CHO CHẶNG NÀY                               │  DÒNG SẼ TẠO                                    │
│  ▸ Emeralda Resort · Deluxe Garden        $$  ✓giá │  🏨 Emeralda Resort · Deluxe Garden             │
│      8/10 tour NB 4★ (90 ngày) · đi cùng Tràng An  │  NCC: Emeralda Ninh Binh                        │
│    Tam Coc Garden · Bungalow              $$$ ✓giá │  ──────────────────────────────────────────     │
│    Ninh Binh Hidden Charm · Superior      $   ✓giá │  Basis  Per room (DBL)     Đêm  [ 1 ] 21→22/12  │
│  DÙNG GẦN ĐÂY                                      │  Phòng  [ 2 ] DBL  +  [ 0 ] SGL   ← room config │
│    Emeralda Resort · Deluxe Garden (3 ngày trước)  │  Trẻ em 2 (9,12) → ⚠ extra bed? [Thêm phụ thu]  │
│    Aravinda Resort · Family (12 ngày trước)        │  ──────────────────────────────────────────     │
│  TẤT CẢ TẠI NINH BÌNH · 4★  (14)                   │  Rate   Mùa Đông 01/11–31/03 · VND  ✓ duy nhất  │
│    Bai Dinh Garden · Deluxe               $   ✓giá │  Net    3.200.000 ₫ /phòng/đêm                  │
│    Hoa Lu Garden · Superior               $   ⚠2 mùa│ Tổng net  6.400.000 ₫                          │
│    Emeralda Resort · Suite                $$$ ✓giá │  Markup 15 % (mặc định) → Sell 7.360.000 ₫ tạm  │
│    …                                       [Tải thêm]│  Ghi chú [                              ]     │
│                                                    │  Chưa có giá? [Nhập giá tay] [Tạo bảng giá]     │
├────────────────────────────────────────────────────┴─────────────────────────────────────────────────┤
│  ↑↓ chọn · Enter thêm · Shift+Enter thêm & tiếp tục · Tab chỉnh số · 1-7 đổi loại · Esc đóng          │
│                                                     [Thêm & tiếp tục  ⇧↵]   [Thêm dịch vụ  ↵]        │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Trạng thái đặc biệt của panel phải:

```text
T6 — 2 mùa giá cùng phủ 21/12                    │  Thiếu giá cho 21/12
 ○ Mùa Đông 01/11–31/03 · VND · 3.200.000        │  Rate gần nhất: Hè 01/04–31/10 (hết hạn)
 ○ Tết 20/12–05/01     · VND · 4.100.000  ← ⚠    │  [Tạo dòng với giá 0 + cờ cần tay]
 Server không tự chọn — sale quyết (chốt 15.3)   │  [Nhập giá tay 3.500.000]  [Tạo bảng giá mới]
```

### 4.4 Wireframe 3 — Inline Editable Service Line (mở rộng dòng #2)

```text
│  2  🏨   Sofitel Legend Metropole · Grand Premium              Per room   2 ph×3đ   7.950.000  47.700.000  54.860.000  13 % ▾ │
│ ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │  Ngày   [Day 1 ▾] 20/12 → 22/12 (3 đêm)      Basis  Per room ▾   Occupancy  DBL ▾   Phòng [ 2 ]   Đêm [ 3 ]          │ │
│ │  Giá net  7.950.000 ₫ /phòng/đêm  (VND · rate "Winter 25/26" · price line adult/dbl/room)   🔒 snapshot 04/09 14:01  │ │
│ │  FX       — (cùng tệ)                                                                                                │ │
│ │  Markup   (○ Mặc định 15 %)  (● Riêng dòng [ 12 ] %)   →  Sell tự tính  53.424.000 ₫                                  │ │
│ │  Sell     (● Ghi đè [ 54.860.000 ] ₫ )   → Margin dòng  7.160.000 ₫ (13,0 %) ▲ so với mặc định −1.440.000            │ │
│ │  Phụ thu  [+ Single supplement 1 SGL × 3 đêm · 1.900.000/đêm]  [+ Extra bed trẻ em ×2]   (từ rate.supplements_json) │ │
│ │  FOC      [ 0 ] phòng miễn phí   (NCC: 1 FOC / 10 phòng)                                                             │ │
│ │  /khách   13.715.000 ₫  (54.860.000 ÷ 4)      Ghi chú [ Late check-out 14:00 đã xin           ]                      │ │
│ │  ⚠ Đổi giá net bằng tay sẽ chuyển dòng sang "giá tay" và bỏ liên kết bảng giá (R3).                                  │ │
│ │                                                  [Xóa dòng]   [Sao chép sang Day 4]   [Hủy Esc]   [Lưu ↵]           │ │
│ └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
```

Quy tắc inline:

- Click vào ô `SL`, `Sell`, `Mg%` ngay trên hàng = sửa nhanh tại chỗ (không cần mở rộng); `Enter` lưu →
  `editLine(lineId, patch)` (hook có sẵn) → server trả workbench mới → số preview bị thay bằng số server.
- Số hiển thị tạm (preview) có viền chấm + tooltip "tạm tính, chờ server" (dùng `resolveLineDisplayTotals`).
- Đổi `Ngày` → `service_date` tự tính lại; nếu ngày mới rơi ngoài validity rate → server trả `rate_snapshot_stale`
  → badge `⚠ giá ngoài hiệu lực` (FE thêm field còn thiếu, L11).
- Line `booking_status ≠ quoted` → toàn bộ hàng khóa, hiện `🔒 đã chuyển Ops`.

### 4.5 Mô hình chi phí — phân định rạch ròi

#### (a) `pax_basis` — suy diễn deterministic, lưu snapshot

```text
pax_basis = per_room    nếu unit == "room"
          = per_person  nếu unit ∈ {"person", "ticket", "flight_seat", "visa_case"}
          = per_group   nếu unit ∈ {"vehicle", "group", "set"}
(hàm pure derive_pax_basis(unit, price_for) trong core/rules/costing_rules.py; mirror TS chỉ để hiển thị)
```

| Basis | `qty_unit` mặc định | Net/khách hiển thị | Ví dụ |
| :-- | :-- | :-- | :-- |
| **Per person** | `adults` (+ dòng `child` riêng nếu rate có `price_for=child`; `infants` = 0 trừ khi có line) | `unit_cost × qty_time` | vé tham quan, bữa ăn, vé bay, visa, tour ghép |
| **Per room** | Σ `room_config[].count` theo `occupancy_basis` (DBL 2, SGL 1 → 2 dòng hoặc 1 dòng + supplement) | `line_cost ÷ pax` | phòng khách sạn, cabin tàu |
| **Per group** | 1 (hoặc số xe theo `seat_capacity ≥ pax`) | `line_cost ÷ pax` (chia đều để ra giá lẻ) | xe, HDV, thuyền riêng, phí tổ chức |

`summary` bổ sung (additive): `per_person_sell_minor[]` theo `price_for` (adult/child) = Σ per_person adult
lines + Σ (per_room + per_group) ÷ pax; con số này thay thế "chia đều tổng" hiện tại trong Apply dialog nhưng
**vẫn chỉ hiển thị** — `pricing_facts` tiếp tục nhận `group_total`, per-adult do sale chốt (15.5 chốt).

#### (b) Single Supplement

- Nguồn: price line `occupancy_basis = sgl` của cùng rate, hoặc `supplements_json[{kind:"single_supplement"}]`.
- Trigger tự động khi `room_config` có SGL, hoặc tổng pax lẻ và không có TRPL/extra bed, hoặc sale bấm
  "+ Single supplement" trên dòng phòng.
- Sinh ra **một service line riêng** `category=accommodation, subcategory=single_supplement, unit=room,
  qty_unit = số SGL, qty_time = số đêm, parent_line_id = dòng phòng` (cột additive `parent_line_id` để UI lồng
  và xóa theo cha). Không nhúng vào cost của dòng cha — giữ 1 line = 1 price line (chốt 15.3 #3).

#### (c) FOC

- Cột additive `foc_qty` (≥ 0, < `qty_unit`) trên `service_lines`; gợi ý từ `rate.supplements_json[{kind:"foc",
  ratio:"1:10"}]` hoặc `supplier.default_foc_policy` (15.1, nếu có).
- `line_cost_minor = unit_cost × (qty_unit − foc_qty) × qty_time` — sửa **một** dòng trong `costing_rules.py`
  với default `foc_qty = 0` → mọi golden test cũ giữ nguyên. Sell vẫn tính trên cost sau FOC (lợi thế FOC đi
  vào margin, sale có thể chuyển thành giảm giá bằng override).

#### (d) Markup per line

- Cột additive `markup_rate_bps_override` (NULL = dùng sheet). `line_sell_minor` chọn `override ?? sheet`.
  Override tuyệt đối (`sell_override_minor`) vẫn thắng cả hai. Thứ tự ưu tiên rõ trong glossary.

### 4.6 Thay đổi dữ liệu & API (tất cả additive)

**Migration `_4x_costing_ux`** (down_revision = head hiện tại lúc implement):

```text
service_lines  + pax_basis String(12) NOT NULL default 'per_group'  (backfill từ unit)
               + price_for String(16) NULL, occupancy_basis String(8) NULL   (snapshot từ price line — hôm nay
                 chỉ có price_line_id, UI phải re-query để biết DBL/SGL)
               + foc_qty Integer NOT NULL default 0
               + markup_rate_bps_override Integer NULL
               + parent_line_id String(64) NULL FK service_lines ondelete CASCADE
costing_sheets + pax_snapshot_json JSON NULL   ({adults, children, infants, room_config[]} lúc tạo/refresh — để
                 picker và FOC/SGL suy qty mà không đọc facts mỗi lần; refresh = nút, không sync ngầm)
costing_pick_events   (bảng mới §3.3a) + index (tenant_id, destination_id, category, created_at), (sheet_id)
product_affinity      (materialized view §3.3b) + job refresh
day_bundles           (tenant_id, name, destination_id, quality_tier, items_json[{product_id, category,
                       qty_rule}], is_active) — sale tạo từ một ngày đang có ("Lưu Day 2 làm gói mẫu")
```

**Operations mới** (vào `tests/test_v2_api_manifest_contract.py`, +6):

| Operation | Method + Path | Ghi chú |
| :-- | :-- | :-- |
| Product suggestions | `GET /costing-sheets/{id}/product-suggestions` | §3.2; read-only; SQL-filtered; ≤ 40 item |
| Quick pick | `POST /costing-sheets/{id}/lines:quick-pick` | §3.2; Idempotency-Key; 422 candidates khi T6 |
| Batch lines | `POST /costing-sheets/{id}/lines:batch` | ≤ 30 dòng, một CAS, một transaction, một Idempotency-Key (all-or-nothing) — dùng cho bundle & copy-day |
| Copy day | `POST /costing-sheets/{id}/days/{n}:copy` `{to_day_numbers[]}` | Server re-resolve rate theo ngày đích (không copy snapshot mù) → mỗi dòng có thể `rate_missing` |
| Refresh pax snapshot | `POST /costing-sheets/{id}/pax-snapshot:refresh` | Đọc facts/request hiện tại → cập nhật `pax_snapshot_json`, bump revision |
| Bundles CRUD | `GET/POST /costing-bundles`, `POST /costing-sheets/{id}/bundles/{bundle_id}:apply` | apply = batch lines |

**`PUT /lines/{id}`** (giữ nguyên path) nhận thêm `foc_qty`, `markup_rate_bps_override`, `pax_basis` (chỉ manual
line được ghi đè; catalog line suy từ unit). **`GET workbench`** trả thêm các cột trên + `rate_snapshot_stale`
(FE thêm field) + `summary.per_person_sell_minor`.

### 4.7 Frontend — cấu trúc component mới (thay lớp UI, giữ hook/adapter/reconciler)

```text
components/quotation-costing/
  CostingWorkbench.tsx            shell (giữ), đổi body: <ExecutiveSummaryBar/> <SheetToolbar/> <DayGrid/> <MarginRail/>
  summary/ExecutiveSummaryBar.tsx sticky; nhận summary + drift + pax; nút AI/Apply chuyển vào đây
  grid/DayGrid.tsx                build khung ngày từ itinerary (props `days: DaySpec[]`) ⨯ lines (groupRowsByDay)
  grid/DayCard.tsx                header ngày, nhóm category, subtotal, action row (A / copy / bundle)
  grid/ServiceLineRow.tsx         hàng compact + quick-edit cells (SL, Sell, Mg%)
  grid/ServiceLineExpanded.tsx    wireframe 3
  grid/TripLevelCard.tsx          bucket day NULL
  picker/SmartProductPicker.tsx   modal (dynamic import, ssr:false) — wireframe 2
  picker/useProductSuggestions.ts headless: SWR GET suggestions theo PickContext, debounce q, keyboard model
  picker/PickPreviewPanel.tsx     "dòng sẽ tạo" + T6 / missing states
  picker/CommandPalette.tsx       ⌘K wrapper hỏi ngày rồi mở picker
  rail/MarginWatch.tsx            top-5 margin thấp, theo category, cảnh báo stale/missing
  bundles/SaveDayAsBundleDialog.tsx, bundles/BundlePickerSection.tsx
  useCostingWorkspace.ts          + quickPick, batchAdd, copyDay, refreshPax (cùng pattern runAction/CAS)
lib/rules/costingReconciler.ts    + derivePaxBasis(unit) [display mirror], perPersonPreview, marginBpsOfLine,
                                  buildDayFrames(itinerary, lines) (pure, test)
lib/rules/costingAdapter.ts       + map các field mới; adapter đơn vị người (percent ↔ bps, major ↔ minor, fxText ↔ ppm)
lib/glossary/costingGlossary.ts   + PAX_BASIS, FOC, SINGLE_SUPPLEMENT, MARKUP_OVERRIDE, SUGGESTED, HISTORY_BACKED
```

Ràng buộc kiến trúc giữ nguyên: mọi tính toán tiền là preview → server thắng; không `useEffect` suy state;
picker tuân 5 Golden Standards (headless hook `useProductSuggestions`, `onChange(id, profile)`, size/variant,
listener chỉ khi mở, phím ↑↓ Enter Esc); typography qua `getTypographyClassName` (workspace, không phải display
system); dynamic import cho modal; `npm run lint` chain xanh.

### 4.8 Lộ trình triển khai

| Đợt | Nội dung | Migration | Exit gate |
| :-- | :-- | :-: | :-- |
| **A — Ngữ cảnh & thao tác** (2 tuần) | DayGrid từ itinerary (ngày trống hiện), ExecutiveSummaryBar sticky, inline edit (nối `editLine`), đơn vị người (%, ₫, FX text), badge `rate_snapshot_stale`, Smart Picker v1 (lọc destination/category/tier + search + preview) trên endpoint `product-suggestions` **chưa có affinity** (section Gợi ý = rỗng, Gần đây = query `service_lines` 90 ngày), `lines:quick-pick` tách `resolve_price_serverside` ra module dùng chung | Không | Thêm 1 dòng catalog ≤ 3 thao tác (A → gõ 4 ký tự → Enter → Enter); sale không gõ ngày/day# nữa; 0 regression contract suites; lint/build xanh; Playwright: 1280/768 |
| **B — Mô hình chi phí** (2 tuần) | `pax_basis`, `price_for/occupancy_basis` snapshot, `foc_qty`, `markup_rate_bps_override`, `parent_line_id`, SGL auto-line, child line auto, `per_person_sell_minor`, batch/copy-day/bundles, `pax_snapshot_json` | `_4x` | Golden test costing_rules cũ nguyên vẹn + test mới FOC/SGL/child/override; copy-day re-resolve rate đúng; Apply dialog hiện /khách từ summary |
| **C — Data Flywheel** (2 tuần) | `costing_pick_events` ghi trong transaction, `product_affinity` + job refresh, `pick_ranking.py`, section Gợi ý sống, tool `suggest_products_from_history` + prompt drafter, badge `history_backed` | `_4y` | Sau 30 ngày dùng thật đo KPI §3.3d; AI draft swap-rate giảm; không có cột tiền trong log (grep test) |

### 4.9 Test matrix

| Lớp | Ca bắt buộc |
| :-- | :-- |
| `test_costing_rules.py` | FOC giảm cost đúng, `foc_qty ≥ qty_unit` → ValueError; markup override per line thắng sheet, sell override thắng cả hai; `derive_pax_basis` mọi unit vocab; per_person_sell tách adult/child; golden cũ không đổi |
| `test_costing_pricing_resolver.py` | Tách từ draft_run_service: rate_missing / rate_conflict / supplement flag / tier; quick-pick 422 candidates; quick-pick tạo line 0-cost + flag khi missing |
| `test_costing_service.py` | batch all-or-nothing (1 dòng lỗi → rollback cả), copy-day re-resolve theo ngày đích, SGL child line có parent, xóa cha xóa con, pick_events ghi cùng transaction và **không** ghi khi write fail |
| `test_product_suggestions_api.py` | Lọc destination roll-up, tier, q không dấu, ≤ 40 item, section ordering, in_sheet flag, không lộ amount |
| `test_pick_ranking.py` | Điểm cooccurrence, recency decay, penalty missing rate, ổn định thứ tự (deterministic) |
| `test_ai_platform_toolset.py` | Tool lịch sử read-only, ≤ 5 item, không tiền |
| FE `costingReconciler.test.ts` | `buildDayFrames` (ngày trống, line lệch ngày → warning, trip-level), `derivePaxBasis`, per-person preview, đơn vị người ↔ kernel round-trip |
| FE `useProductSuggestions.test.ts` | Debounce, keyboard model (↑↓ Enter Shift+Enter Tab 1–7 Esc), cancel request khi đổi chip |
| Playwright | Thêm 3 dòng cho Day 1 bằng bàn phím < 20 giây; inline edit → số server thay preview; 409 giữa 2 tab → reload; responsive 1280/1024/768; dark theme |

### 4.10 Những gì spec này cố tình KHÔNG làm

| Không làm | Vì | Đi đâu |
| :-- | :-- | :-- |
| Tự động đồng bộ line khi itinerary đổi | 15.4 §6 đã chốt (vòng lặp reconcile); chỉ cảnh báo lệch ngày | Nút "Đổi ngày hàng loạt" thủ công ở đợt B |
| ML ranking / embedding | Lean AI (plan 18 §5.6); công thức có tên + test đủ cho quy mô DMC | Xem lại khi > 50k pick events |
| Nhiều phương án giá trên 1 sheet | 15.4 §6 giữ 1 sheet = 1 phương án vốn | quotation version |
| Đổi engine per-adult/per-child ở BE cho `pricing_facts` | 15.5 chốt: `pricingReconciler` phía form là SSOT chia đầu người; `per_person_sell_minor` chỉ hiển thị | — |
| Giao diện kiểu TourPlan cũ (mã 12 ký tự, pop-up lồng) | Trái mục tiêu; mã product chỉ hiện trong tooltip | — |
| Cho AI tự quyết khi T6 conflict / thiếu giá | 15.3/15.7 chốt: người quyết | — |

---

## Phụ lục A — Bản đồ điểm yếu → giải pháp

| Điểm yếu (§2) | Giải pháp (§3/§4) |
| :-- | :-- |
| W1 mất ngữ cảnh | DayGrid từ itinerary; picker mở với PickContext; `service_date` server suy từ `day_number` |
| W2 form-at-bottom | Không còn form; inline row + picker modal mở tại ngày; phím A/E/D/C/⌘K |
| W3 dropdown phẳng | `product-suggestions` lọc SQL theo destination/category/tier + 3 tầng gợi ý |
| W4 dropdown Rate/Price line | Quick-pick server auto-resolve; UI chỉ hỏi khi T6 |
| W5 thiếu pax basis | `pax_basis` snapshot + pill + net/khách + `per_person_sell_minor` |
| W6 không bulk | batch, copy-day, bundle, Shift+Enter |
| W7 margin mù | Mg% màu từng dòng, Margin Watch rail, view "Margin" |
| W8 đơn vị kỹ thuật / không edit | Adapter đơn vị người; inline edit nối `editLine`; badge stale |

## Phụ lục B — Từ điển bổ sung cho `costingGlossary.ts`

| Key | Tiêu đề | Mô tả ngắn |
| :-- | :-- | :-- |
| `PAX_BASIS` | Cơ sở tính (Per person / Per room / Per group) | Dòng này nhân theo khách, theo phòng, hay là chi phí chung của đoàn được chia đều để ra giá lẻ |
| `FOC` | Miễn phí (Free of Charge) | Số đơn vị NCC không tính tiền; chi phí = đơn giá × (số lượng − FOC) |
| `SINGLE_SUPPLEMENT` | Phụ thu phòng đơn | Dòng phụ sinh từ giá SGL của cùng bảng giá, gắn với dòng phòng cha |
| `MARKUP_OVERRIDE` | Markup riêng dòng | Thay markup mặc định của sheet cho riêng dòng này; ghi đè giá bán tuyệt đối vẫn thắng |
| `SUGGESTED` | Gợi ý theo lịch sử | Xếp hạng từ các lần chọn trước cùng điểm đến / hạng / quy mô đoàn |
| `HISTORY_BACKED` | AI chọn theo lịch sử | Dòng AI dựa trên dữ liệu chọn thật của đội, không phải suy đoán |
| `RATE_STALE` | Giá ngoài hiệu lực | Bảng giá gốc đã hết hạn/bị thay; giá dòng vẫn giữ nguyên (snapshot), cần kiểm tra |
