# 15. Modular Tour Ops — Brainstorm (thay thế Plan 14)

> **Loại tài liệu**: Brainstorm kiến trúc module cho hệ thống quản lý tour lấy cảm hứng Tourplan,
> phiên bản MVP cho agency nhỏ, thiết kế để scale mà không viết lại.
>
> **Quan hệ với Plan 14**: Plan 14 bị **hủy bỏ** vì làm quá nhiều việc cùng lúc
> (catalog 5 bảng + 2 AI agent + pricing engine + grid UI đan xen trong 6 sprint).
> Plan 15 giữ lại các *quyết định dữ liệu đúng* của 14.0 (Supplier≠Property, Product≠Rate,
> Rate≠dòng đã bán, Content≠Contracted service) nhưng đổi hẳn **chiến lược thi công**:
> mỗi module xây độc lập, chạy ổn định standalone (FE + BE + test) rồi mới wiring vào
> quotation workspace. AI drafter là bước CUỐI, không phải bước đầu.

**Một câu**: Xây từng bounded context như một sản phẩm nhỏ hoàn chỉnh — Supplier Registry →
Product Catalog → Rates → Costing tab → Booking board — mỗi bước ship được, dùng được thủ công,
và bước sau chỉ *tham chiếu bằng ID + snapshot* vào bước trước.

---

## 0. Hiện trạng đã xác minh (2026-08-27)

Khảo sát code thực tế (không phải plan docs) cho thấy:

- **Chưa có** bảng supplier / product / rate / service_line / booking nào trong code.
  Migration mới nhất: `20260824_35_actionable_content_plan`. Toàn bộ plan 14 chỉ nằm trên giấy.
- Giá hiện chỉ tồn tại **bên trong facts JSON** của quotation
  (`CreateQuotePricingOptionFact`: minor units, 5 currency, tối đa 3–4 options) — sell-price only,
  không có net cost / margin / supplier rate ở bất kỳ đâu.
- `partner_profiles` là **đại lý nguồn khách** (debtor — tiền chảy VÀO), tuyệt đối không tái dùng
  cho supplier (creditor — tiền chảy RA).
- `accommodation_profiles` là **content/media thuần** (không giá, không supplier) — đúng ranh giới R4.
- Các seam decoupling đã có sẵn:
  - `routers/v2/<domain>.py` + `api/runtime.py` callbacks (không import `main` module-level)
  - `OutboxService.emit_event` (notification đã reserve sẵn `agentic.supplier_quote.received`,
    `agentic.cost_optimization.alert`)
  - `core/rules/service_candidate_rules.py` — Gate 5 placeholder với `ServiceType`,
    `ServiceCandidate`, `ServiceCandidateEvaluator` Protocol: extension point cắt sẵn cho PCM
  - `PublicationJob` là template durable job queue tốt nhất trong repo cho booking ops sau này
- Frontend: workspace stepper là mảng `stages = ["facts","content","design","review"]` trong
  `QuotationWorkspaceClient.tsx:75` — thêm 1 stage mới chỉ ~6 dòng / 2 file.
  `tourComponentsCatalog.ts` đã khai báo sẵn slot `cars` / `experiences` / `tickets`
  (stub rỗng trong `useTourComponentsState.ts:45-47`) — chỗ cắm catalog UI.
  Picker convention thống nhất: `components/<domain>/{XSelect, useXSearch, XManageDrawer, types, index}`.

---

## (a) Danh sách module đề xuất + boundary

### Bản đồ bounded context

```text
┌─ SALES (đã có) ──────────────┐   ┌─ CATALOG (mới, M1–M3) ────────────────┐
│ quote_requests               │   │ suppliers ──< products ──< rates      │
│ partner_profiles (agent/     │   │                 │            └< rate_price_lines
│   debtor — nguồn khách)      │   │                 └→ accommodation_profiles (content only)
│ travel_designer_profiles     │   └────────────────┬──────────────────────┘
└──────────────┬───────────────┘                    │ tham chiếu bằng ID
               │ convert                            │ + SNAPSHOT giá/điều khoản
               ▼                                    ▼
┌─ QUOTATION (đã có) ──────────┐   ┌─ COSTING (mới, M4–M5) ────────────────┐
│ quotations / facts / content │◄──│ service_lines (#L0 — nguyên tử duy    │
│ / design / publication       │   │ nhất) + quotation_costing_settings    │
└──────────────────────────────┘   └────────────────┬──────────────────────┘
                                                    │ copy-on-confirm
                                                    ▼
┌─ OPERATIONS/BOOKING (mới, M6) ───┐   ┌─ FINANCE (tương lai) ─────────────┐
│ bookings ──< booking_lines       │──▶│ payables / receivables            │
│ booking_status lifecycle, ops    │   │ (join key = voucher_ref trên      │
│ board, voucher_ref               │   │  booking_line — đặt sẵn từ M6)    │
└──────────────────────────────────┘   └───────────────────────────────────┘

┌─ INVENTORY/ALLOTMENT (hoãn — MVP free-sell, nhưng giữ chỗ bảng riêng) ───┘
```

### Chi tiết từng module & ranh giới trách nhiệm

| # | Module | Sở hữu | KHÔNG sở hữu | Giao tiếp ra ngoài |
| :-: | :-- | :-- | :-- | :-- |
| M1 | **Supplier Registry** | `suppliers` (creditor): contact, default_currency, payment_terms_json, cancellation_policy_json, preferred_status, quality_tier | Giá (thuộc Rates), content property (thuộc accommodation_profiles), agent (thuộc partner) | CRUD API riêng `/api/v2/suppliers`; module khác chỉ giữ `supplier_id` |
| M2 | **Product Catalog (PCM)** | `products` (service option): category ∈ vocab đóng, unit × time_basis, category_attributes JSONB, dedupe key `(destination, category, title_normalized, supplier)` | Giá (chỉ Rates có tiền), media/content (trỏ `property_id` → accommodation_profiles) | `/api/v2/products`; hiện thực `ServiceCandidateEvaluator` Protocol có sẵn |
| M3 | **Rates & Pricing** | `rates` (season date-range, status confirmed/provisional, immutable-by-supersede) + `rate_price_lines` (đúng 1 amount/dòng: SGL/DBL/adult/child); pure engine trong `core/rules/` | Markup theo quotation (thuộc Costing), quyết định chọn rate nào cho khách (thuộc Costing) | `/api/v2/products/{id}/rates`; không module nào join live vào rates |
| M4 | **Costing** | `service_lines` (#L0): snapshot `unit_price_minor` + điều khoản tại thời điểm draft, `tariff_id` chỉ để truy vết; `quotation_costing_settings` (markup_rate_bps, `costing_revision` CAS riêng) | Sell-price hiển thị brochure (vẫn thuộc pricing_facts của Quotation cho tới bước wiring M5) | `/api/v2/quotations/{id}/service-lines`; FK duy nhất sang quotation là `quotation_id` string |
| M5 | **Wiring Costing → Quotation** | Hàm apply: tổng service_lines + markup → đề xuất `pricing_facts.options[]` (sale bấm Apply, không tự động) | Không ghi đè pricing option sale đã sửa tay | Qua API + facts revision hiện có (`baseRevision`) |
| M6 | **Booking / Operations** | `bookings` + `booking_lines` (copy-on-confirm từ service_lines, đóng băng terms snapshot), lifecycle `to_request → requested → confirmed → delivered/cancelled`, `voucher_ref` | Nội dung brochure, giá bán | Sidebar surface riêng `/workspace/bookings`; sự kiện qua outbox (`booking.line.confirmed`…) |
| M7 | **Finance** (chưa làm) | payables/receivables | — | Chỉ tiêu thụ outbox events + voucher_ref |
| M8 | **Allotment** (hoãn) | bảng riêng `(product_id, date, quantity, release_days)` khi cần | — | Không đụng schema rates/booking khi thêm |

### Quy tắc chống coupling (bất biến)

1. **Tham chiếu = ID, dữ liệu dùng = snapshot.** `service_lines` không bao giờ join live vào
   `rates`; `booking_lines` đóng băng cả điều khoản. Catalog đổi giá → báo giá cũ bất động.
2. **Catalog không biết Quotation tồn tại.** Chiều phụ thuộc một chiều:
   Quotation/Costing → Catalog, không bao giờ ngược lại.
3. **Mỗi module: models riêng (`db/models/<module>.py` + đăng ký `db/base.py`), router riêng,
   repository riêng, migration riêng, thêm operation vào manifest contract test.**
4. **Sự kiện chéo module chỉ qua outbox** — mirror event type vào
   `notification/domain/events.py`.
5. **Revision riêng cho costing** (`costing_revision`), không piggyback
   `quotation_documents.revision` (per-language, contract khác).
6. **FE mirror đúng cấu trúc BE**: mỗi domain một thư mục
   `components/<domain>/` theo convention Select/useSearch/ManageDrawer; toán costing vào cặp
   `costingReconciler.ts` + `costingAdapter.ts` mới (Layer 1/2), KHÔNG mở rộng
   `pricingReconciler.ts` (giữ nguyên bất biến sell-side).

### Đã chốt: KHÔNG database-per-module

M1–M6 dùng chung DB `quotation`, cùng process. DB riêng chỉ dành cho service thật sự tách biệt
(hiện chỉ có `notification/`). Thay cho cách ly vật lý là 4 quy tắc logic:

1. **Ownership tường minh**: mỗi bảng thuộc đúng 1 module (`db/models/<module>.py`);
   chỉ repository của module đó được ghi.
2. **FK ≠ JOIN**: FK chéo module để giữ integrity thì được (vd `products.property_id`),
   nhưng cấm JOIN chéo module trong repository — cần dữ liệu module khác thì gọi hàm public
   của service module đó, hoặc 2 query + ghép ở service layer.
3. **Không import chéo model**: service module A không import SQLAlchemy model của module B —
   chỉ ID và DTO.
4. Side-effect chéo module chỉ qua outbox (§quy tắc 4 ở trên).

Giữ đủ 4 điều này thì tách DB sau (nếu có ngày cần) là việc cơ học.

---

## Shared Kernel — tầng đáy, dưới mọi module

Kernel **không phải module ngang hàng** — nó là tầng thấp nhất, và phần lớn đã tồn tại:
`core/rules/` (pure) + `db/types.py` (`JSON_VARIANT`, `BIGINT_PK_VARIANT`) +
`services/outbox_service.py`. Phần chuẩn hóa mới gom vào `core/kernel/` với quy tắc thép:
**kernel không import bất kỳ module nghiệp vụ nào**.

| # | Thành phần | Quyết định | Ghi chú so với hiện trạng |
| :-: | :-- | :-- | :-- |
| K1 | **Money** | `{amount_minor: BigInteger, currency: char(3)}`, không bao giờ float. Chuẩn hóa từ `core/rules/pricing_rules.py` (`SUPPORTED_CURRENCIES`, `currency_divisor`) → `core/kernel/money.py`; mọi module mới import từ đó | Nợ legacy: `partner_profiles.default_commission_rate` là Float — migrate sang bps integer khi tiện |
| K2 | **FxRate** | Kernel chỉ định nghĩa **kiểu** `{base, quote, rate (int ppm), as_of}` — chưa có bảng lưu tỷ giá (đúng tinh thần hoãn FX table) | FE đã có 3-tier FX fallback riêng |
| K3 | **LocalServiceDate** | Calendar date thuần: ISO `YYYY-MM-DD`, **KHÔNG lưu timezone trên từng ngày**. Timezone là thuộc tính của destination/property nếu sau này cần. `TIMESTAMPTZ` chỉ cho audit fields | Validator dùng `dates_rules.parse_iso_date` sẵn có. Lưu tz per-date = over-engineering, tạo 2 nguồn sự thật |
| K4 | **ActorRef** | `{actor_id, actor_type ∈ staff \| ai_agent \| system \| customer}` — chữ ký ghi của MỌI module mới nhận ActorRef, không nhận user_id/email thô. Khi AI drafter (15.7) bắt đầu ghi, không hàm nào đổi chữ ký | Tương thích outbox hiện tại: serialize xuống `actor_email` + thêm `actor_type` vào payload. Permission/Identity nằm NGOÀI kernel |
| K5 | **Outbox + audit** | Dùng nguyên `OutboxService`/`outbox_relay` sẵn có — không xây outbox thứ hai. Audit = pattern revision-row đã có (supersede của rates chính là audit log giá) + cột `created_by`/`updated_by` nhận ActorRef. KHÔNG bảng audit toàn cục | MVP handler đồng bộ sau commit (đang chạy vậy); đổi sink sang broker sau không sửa tầng tích hợp |
| K6 | **ID generator** | Giữ convention prefix-string (E7: `sup_`, `prd_`, `svl_`…), nhưng generator bên dưới đổi `uuid4().hex` → **UUIDv7 hex** cho bảng mới: sortable, cùng kiểu cột `String(64)`, không breaking. Business code hiển thị (`BK-2026-00123`) là cột riêng, sinh khi confirm (= `voucher_ref` E10) | |
| K7 | **tenant_id** | Bảo hiểm giá rẻ: chỉ thêm vào bảng của **module mới** (default `'capella'`, indexed), không retrofit bảng cũ. Lưu ý `brand_id` là brand bán hàng, KHÔNG phải tenant — không nhầm hai khái niệm | |
| K8 | **Idempotency** | Scope hẹp: chỉ POST tạo dòng tiền (`service-lines`, `bookings`, apply-pricing) nhận header `Idempotency-Key`; lưu theo pattern unique-key của `PublicationJob`. Không store toàn cục cho mọi endpoint | |

---

## (b) Quyết định thiết kế "trả giá trước" (invest early)

Đối chiếu Tourplan NX / Travel Studio / Lemax / OCTO spec:

| # | Quyết định | Hình thức trong repo này | Vì sao không hoãn được |
| :-: | :-- | :-- | :-- |
| E1 | **Tiền = integer minor units + ISO 4217 code, tách cặp cost/sell** | `cost_amount_minor + cost_currency` và `sell_amount_minor + sell_currency` là 2 cặp cột riêng trên rate_price_lines & service_lines; đã có sẵn `currency_divisor`/`SUPPORTED_CURRENCIES` — không tự định nghĩa lại | DMC mua bằng VND, bán bằng USD. Nhét chung 1 currency rồi tách sau = migration đau nhất ngành. OCTO bắt buộc minor units + `currencyPrecision` đúng vì lý do này |
| E2 | **Product ≠ Rate** (R2) | Không bao giờ có cột `price` trên `products` | Mất lịch sử giá, không có mùa vụ, không tái thương lượng — retrofit = rewrite |
| E3 | **Snapshot tại service_line, rate immutable** (R3) | Đổi giá = end-date rate cũ + insert rate mới (`superseded`), không edit in-place | Báo giá/booking cũ tự đổi giá khi NCC gửi bảng giá mới = lỗi chết người với kế toán |
| E4 | **Charge unit 2 chiều: `unit` × `time_basis`** | `unit ∈ {room, person, vehicle, group, ...}` × `time_basis ∈ {night, day, trip}` (Tourplan: "Per Room **Per Night**") — vocab lấy từ 1 SSOT, kèm rule per-room → per-person (half-twin + single supplement) | MVP "giá per item" rồi thêm chiều thời gian sau = migration kinh điển đau đớn nhất |
| E5 | **Rate Header → Price Line, đúng 1 amount/dòng** | SGL/DBL/TWN/TRPL và adult/child là *dòng*, không phải *cột* | Nổ cột (`price_sgl`, `price_dbl`, `price_child_5_11`…) là bẫy không lối ra |
| E6 | **Season = date range trên rate, số kỳ không giới hạn** | `valid_from` / `valid_to` (LOCAL date, xem E8) ngay từ bảng đầu tiên | "Phụ thu Tết +30%" không có chỗ chứa nếu rate là giá phẳng |
| E7 | **ID scheme thống nhất + composite code người đọc được** | PK = prefix string theo convention repo (`sup_`, `prd_`, `rat_`, `svl_`, `bkg_`); products thêm unique `(destination_id, category, title_normalized, supplier_id)`; category vocab là code table đóng | Tourplan sống 30 năm nhờ `LOC+TYPE+SUPPLIER+CODE`; đổi ID scheme sau khi có FK chằng chịt = breaking change lớn nhất có thể |
| E8 | **Ngày dịch vụ = local date, KHÔNG timezone** | Giữ đúng pattern hiện tại: date ISO string / `Date` không tz cho check-in, departure; `DateTime(timezone=True)` chỉ cho audit | Convert đêm khách sạn sang UTC → lệch ngày qua date line. OCTO & GTFS đều model `localDate` |
| E9 | **payment_terms / cancellation_policy có cấu trúc (JSONB) + snapshot cả điều khoản** | Trên `suppliers` (default) và override trên `rates`; `booking_lines` đóng băng snapshot | Là điều kiện duy nhất để sau này sinh payables + penalty tự động; retrofit từ free-text đắt gấp nhiều lần |
| E10 | **`voucher_ref` trên booking_line từ ngày đầu M6** | Cột nullable, sinh khi confirm | Join key duy nhất để Finance đối soát AP; thêm sau = đối soát tay toàn bộ backlog |
| E11 | **`markup_rate_bps` integer per-quotation, không per-line, không float** | `quotation_costing_settings` với CAS `costing_revision` | Float % + per-line markup = không audit được margin |
| E12 | **Sự kiện outbox đặt tên ngay cả khi chưa có consumer** | `catalog.rate.superseded`, `costing.applied`, `booking.line.confirmed`… | Đổi tên event sau khi notification/finance đã subscribe = breaking contract |

### Những thứ ĐƯỢC PHÉP đơn giản hóa (chống over-engineering — bài học plan 14)

- **Allotment**: free-sell. Chỉ cần cam kết *khi làm sẽ là bảng riêng* (M8), không đụng schema khác.
- **FX record/bảng tỷ giá**: FE đã có 3-tier fallback; BE chưa cần bảng FX. Chỉ cần E1 đúng.
- **Markup matrix theo agent tier / price code**: 1 markup per quotation là đủ cho agency nhỏ;
  vì rate đã tách cost/sell (E3+E5), thêm price-code tier sau = thêm cột `price_code` vào
  rate_price_lines, không phá gì.
- **Policies chuẩn hóa 3 bảng**: JSONB trên supplier + override trên rate là đủ (95% đồng nhất).
- **AI drafter / TripAnalyst**: hoãn hoàn toàn sang giai đoạn sau M5 — khi flow thủ công đã chạy,
  AI chỉ là "người gõ nhanh" điền vào cùng API mà sale đang dùng tay. Đây là đảo ngược chiến lược
  so với plan 14 (AI-first) và là lý do chính plan 15 khả thi.
- **Voucher document render**: dùng publication pipeline sẵn có, không bảng voucher riêng.

---

## (c) Rủi ro nếu bỏ qua

| Bỏ qua | Hệ quả cụ thể | Mức |
| :-- | :-- | :-: |
| E1 (tách cost/sell currency) | Không nhập nổi hợp đồng NCC bằng VND khi bán USD; hoặc phải "quy đổi lúc nhập" → mất giá gốc, không tái đối soát với NCC được | 🔴 rewrite |
| E2/E3 (product≠rate, immutable) | Sale sửa giá catalog → mọi báo giá đang mở đổi giá âm thầm; kế toán không khớp được số đã báo khách | 🔴 mất tiền thật |
| E4 (unit × time_basis) | Khách sạn tính per-room-per-night nhưng schema chỉ có qty×price → phải nhét "3 đêm" vào title, pricing engine mù | 🔴 rewrite pricing |
| E5 (price line) | Thêm loại phòng thứ 5 / child band thứ 3 = migration đổi cột trên bảng tiền | 🟠 migration đau |
| E7 (ID scheme) | Đổi từ int/uuid trần sang prefix string sau khi có FK từ service_lines/bookings | 🔴 breaking lớn nhất |
| E8 (local date) | Booking check-in lệch 1 ngày với khách bay qua múi giờ; bug chỉ lộ ra ở production | 🟠 âm thầm, khó debug |
| E9 (structured terms) | Không bao giờ tự động hóa được deposit deadline / phí hủy; ops mãi mãi tra tay PDF | 🟠 chặn Finance |
| E10 (voucher_ref) | Finance module ra đời không có join key → đối soát tay toàn bộ booking cũ | 🟠 nợ vĩnh viễn |
| Quy tắc coupling §a.2 (catalog không biết quotation) | Catalog import quotation model → không bao giờ tách service được, test catalog phải dựng cả quotation fixture | 🟠 tech debt lũy tiến |
| Xây AI trước flow thủ công (lặp lại plan 14) | Không có đường chạy end-to-end để nghiệm thu; mọi bug lẫn lộn giữa AI sai và schema sai | 🔴 chính là lý do plan 14 chết |

---

## Trả lời Q4 — Modular monolith vs microservices

**Modular monolith, dứt khoát.** Repo đã chứng minh pattern này hoạt động: `notification/` là
"microservice trong monorepo" (DB riêng, Alembic tree riêng, giao tiếp outbox) trong khi phần còn
lại là monolith phân lớp. Cho agency nhỏ:

- Mỗi module mới = 1 router prefix (`/api/v2/suppliers`, `/api/v2/products`, …) + services +
  repositories riêng, **cùng process, cùng DB** quotation.
- **API contract là ranh giới tách service tương lai**, không phải network. Điều kiện đủ để sau
  này tách 1 module thành service riêng mà không đổi interface:
  1. Router của module chỉ gọi service của chính nó (không gọi chéo service module khác trực tiếp
     — nếu cần dữ liệu module khác thì gọi qua hàm public của service đó, được inject).
  2. Response schema không leak SQLAlchemy model — luôn qua Pydantic response model.
  3. Không JOIN SQL chéo module trong repository (join bằng 2 query + ghép ở service nếu cần).
  4. Side effect chéo module chỉ qua outbox event.
  Khi đủ 4 điều kiện, "tách service" = chuyển router+service+repo+tables sang process mới và đổi
  in-process call thành HTTP call — URL và payload giữ nguyên.
- Manifest contract test (`test_v2_api_manifest_contract.py`) chính là cơ chế đóng băng interface
  đó — mỗi module mới bắt buộc đăng ký operations vào đây.

## Trả lời Q5 — Case study tham khảo

- **Tourplan NX** (user manuals công khai): Option code `LOC+TYPE+SUPPLIER+CODE`; rate = date
  range → rate set (min/max stay, DOW, status, commissionable) → cost+sell per price code;
  charge unit 2 chiều; allotment = quantity + release days; Creditors/Debtors + voucher-based AP.
- **Travel Studio (Open Destinations)**: Contracting là domain tách khỏi Reservations; yield rules
  chỉnh sell không đụng contracted cost.
- **Lemax**: supplier → catalog → sales → operations → finance (AR/AP module riêng).
- **Kaptio**: Agreement (hợp đồng NCC) là object hạng nhất, itinerary lines kiểu CPQ.
- **OCTO spec** (mở, inspectable — chuẩn đặt tên tốt nhất): Product → Option → Unit;
  Availability tách khỏi Pricing; Booking snapshot; minor units + currencyPrecision bắt buộc.
- Chi tiết + URL nguồn: xem phần research trong lịch sử session này (đã trích Tourplan
  usermanuals, docs.ventrata.com, docs.octo.travel, lemax.net, opendestinations.com).

---

## Lộ trình đề xuất (mỗi bước ship độc lập — KHÔNG phải sprint đan xen)

| Bước | Nội dung | Wiring vào quotation? | Điều kiện xong |
| :-: | :-- | :-: | :-- |
| **[15.1](./15.1-supplier-registry.md)** | Supplier Registry: bảng `suppliers` + CRUD API + FE `components/supplier/` (theo pattern partner) + entry trong Components workspace | ❌ Không | CRUD chạy, test contract, lint xanh — không đụng 1 dòng nào của quotation |
| **[15.2](./15.2-product-catalog.md)** | Product Catalog: `products` + category vocab + API + FE picker/manage; wire vào slot `cars`/`experiences`/`tickets` có sẵn của `tourComponentsCatalog` | ❌ Không | Sale tạo/tìm product thủ công được |
| **[15.2b](./15.2b-destination-standards-and-hierarchy.md)** | Destination Tourism Hub: cây phân cấp + ISO/IATA/timezone + `merged_into_id` redirect + tuyến 2 đầu trên products — chuẩn hóa TRƯỚC khi 15.3 FK bảng giá vào | ❌ Không | Kịch bản sáp nhập chạy E2E, media không gãy link, quotation cũ bất động |
| **[15.3](./15.3-rates.md)** | Rates: `rates` + `rate_price_lines` + supersede flow + UI nhập giá trong product drawer; pure `core/rules/rate_selection.py` | ❌ Không | Nhập bảng giá mùa vụ, đổi giá không phá giá cũ |
| **15.4** | Costing tab: stage `costing` mới trong workspace (seam ~6 dòng/2 file) + `service_lines` + `quotation_costing_settings` + FE `components/quotation-costing/` với `useCostingWorkspace` + `costingReconciler` riêng | 🟡 Chỉ đọc quotation_id | Sale pick product → line snapshot giá → sửa tay được; quotation cũ không ảnh hưởng |
| **15.5** | Apply pricing: nút "Apply to Commercial" tổng lines + markup → đề xuất pricing_facts option | ✅ Có, qua facts API sẵn có | Sale kiểm soát, không auto-overwrite |
| **15.6** | Booking board: `bookings`/`booking_lines` copy-on-confirm + surface `/workspace/bookings` + outbox events + `voucher_ref` | 🟡 Đọc service_lines | Operator theo dõi trạng thái gọi điện/confirm từng dịch vụ |
| **15.7+** | AI drafter (TripAnalyst/ServiceDrafter từ plan 14, thu nhỏ), Finance, Allotment | — | Chỉ bắt đầu khi 15.5 chạy ổn ở production |

Mỗi bước 15.x sẽ có tài liệu thiết kế riêng khi bắt tay làm — tài liệu này chỉ chốt boundary,
invariant và thứ tự.
