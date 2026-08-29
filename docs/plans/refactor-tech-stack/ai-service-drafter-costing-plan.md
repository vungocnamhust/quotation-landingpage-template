# Plan: AI Service Drafter & Costing Engine

**Generated**: 2026-08-24
**Estimated Complexity**: High
**Nhân lực**: 2 dev song song — `[BE]` backend · `[FE]` frontend
**Quan hệ tài liệu**: [14-…-costing.md](./14-ai-service-drafter-and-costing.md) là spec kiến trúc · [14.1](./14.1-sprint-1-pricing-core.md)–[14.6](./14.6-sprint-6-apply-pricing-and-e2e.md) là chi tiết từng sprint · **file này là plan thực thi cấp task**.

---

## Overview

Tự động hoá bước `NewQuotation → phân bổ dịch vụ → giá vốn` cho 10 danh mục, bằng **Hybrid Pipeline**:

```
QuoteRequest (ngữ nghĩa, thưa)
  → ① TripAnalyst      AI, 1 call/trip   → TripProfile (cấu trúc, đặc)
  → ② ParamResolver    pure code + YAML  → BaseParams
  → ③ ServiceDrafter   AI, 1 call/ngày   → ServiceDraft[] (KHÔNG có tiền)
  → ④ Pricing          pure code + CS1   → ServiceLine[] + summary
  → ⑤ Grid HITL        sale gõ giá       → apply → pricing_facts.options[]
```

**Nguyên tắc bất di dịch**: LLM *reason & match*, pure code *compute*. YAML chỉ sở hữu công thức qty/params; markup là snapshot CS1 per quotation, không live từ YAML.

### Chốt kiến trúc (không mở lại)

| # | Chốt |
| :-: | :-- |
| 1 | Pydantic AI — dùng `llm_client.get_model()`, không tạo provider mới |
| 2 | Unified model — 1 schema, 1 bảng, 1 agent class cho cả 10 category |
| 3 | Chỉ 1 main option, không sinh alternates |
| 4 | Không blocking khi draft — Apply gate = `sell_total > 0`; publish còn cần coverage gate |
| 5 | Công thức qty/params sửa được không deploy — `formulas.yaml` + `param_rules.yaml`; markup không thuộc YAML |
| 6 | Server-authoritative — **không** mirror pricing sang TS |
| 7 | Không rule hậu kiểm chống trùng — đưa dữ kiện vào day context |
| 8 | Tool filter ở SQL, trả ≤ 8 dòng, không trả giá tuyệt đối |
| 9 | Tách `TripProfile` — 1 điểm điều khiển cho tính chất chuyến đi |
| 10 | Markup per quotation — CS1 `markup_rate_bps`, integer snapshot; không per-line, không live YAML |

### Chốt vận hành (từ clarify)

| Chốt | Hệ quả lên plan |
| :-- | :-- |
| **Playwright tối thiểu, không hoãn hết** | 3 spec chạm tiền / mất dữ liệu là **chặn merge** (task 6.6); 4 spec còn lại vào backlog vì đã có backend E2E hoặc SQL assert. Luật phân tầng: [14.6 §6](./14.6-sprint-6-apply-pricing-and-e2e.md) |
| **2 dev BE + FE** | **Contract-first**: Task 1.1 đóng băng API contract trước mọi thứ. Mỗi task gắn `[BE]`/`[FE]` + đánh dấu `∥` khi chạy song song được |
| **CI gate ở sprint 1** | Task 1.2–1.3 dựng pytest config + CI workflow **trước** khi viết logic |

### Chốt phát sinh từ rà gotchas (Phase 4)

| Chốt | Hệ quả lên plan |
| :-- | :-- |
| **`pax` chia giá bán lấy từ `pricing_facts`**, không từ `TripProfile` | Giữ nguyên hệ cũ, khớp `inferOptionRatesFromTotal`. `TripProfile.total_pax` chỉ dùng cho **giá vốn**. Lệch ⇒ cảnh báo UI, không tự sửa |
| **`costing_revision` quotation-wide** | CS1 CAS mọi mutation costing. Không dùng `quotation_documents.revision` theo lang; `:apply-pricing` ghi document kèm applied-costing snapshot |
| **`qty_override` là cột riêng** | Sale sửa `qty` trực tiếp ⇒ ghi `qty_override`, thắng công thức. `params_source` không dùng cho `qty` |
| **Mock FE bằng fixture module** | `NEXT_PUBLIC_SERVICE_FIXTURE=1`, **không** thêm MSW |
| **`ParamContext` ở sprint 2–3** | Dựng từ facts + `rooming_heuristic_service` — chính là hàm fallback task 4.3, dùng sớm hơn |

---

## Prerequisites

| Hạng mục | Trạng thái | Việc cần làm |
| :-- | :-- | :-- |
| `pydantic-ai>=2.0.0` | ✅ có trong `requirements.txt` | — |
| `simpleeval` | ❌ | Thêm (task 1.2) |
| `pytest-cov` | ❌ | Thêm (task 1.2) |
| `pytest.ini` / marker `llm` | ❌ chưa có file config nào | Tạo (task 1.3) |
| CI chạy pytest | ❌ chỉ có `build-quote-generator.yml` | Tạo workflow (task 1.4) |
| Playwright | ⚠️ | **3 spec bắt buộc** ở sprint 6 (ranh giới 10, 14, 18); 4 spec còn lại backlog |
| `DEEPSEEK_API_KEY` hoặc `OPENAI_API_KEY` | cần cho sprint 4–5 | Xác nhận có trong `.env` |
| Postgres local | ✅ `docker compose -f docker-compose.local.yml up -d postgres` | — |
| Tái dùng sẵn có | `rooming_heuristic_service` · `party_rules` · `staysReconciler` · `pricingReconciler.inferOptionRatesFromTotal` · `PromptLoader` · `_get_helpers()` · `outbox_service` | — |

---

## Sprint 1: Nền móng — Contract, CI, Pricing Core

**Goal**: API contract đóng băng để 2 track chạy song song · CI có lưới an toàn · engine tính tiền pure chạy được trong REPL.

**Demo/Validation**:
```bash
PYTHONPATH=. pytest tests/test_service_pricing.py tests/test_param_resolver.py -v
PYTHONPATH=. pytest --cov=core.rules.service_pricing --cov=core.rules.param_resolver --cov-report=term-missing
python -c "from core.rules.service_pricing import apply_markup; print(apply_markup(100000, 2000))"   # 120000
```
- CI đỏ khi cố tình làm hỏng 1 test, xanh khi sửa lại
- `docs/plans/refactor-tech-stack/api-contract-service-lines.md` được cả 2 dev ký nhận

### Task 1.1 `[BE+FE]` Đóng băng API contract
- **Location**: `docs/plans/refactor-tech-stack/api-contract-service-lines.md`
- **Description**: Viết contract đầy đủ cho 7 endpoint (4 CRUD lines · 2 trip-profile · 1 apply-pricing) + shape `ServiceLine`, `PricingSummary`, `TripProfile`, SSE event. Ghi rõ mã lỗi 409/422 theo `_v2_error_payload`.
- **Dependencies**: —
- **Acceptance Criteria**:
  - Mỗi endpoint có method, path, request body, response body, mã lỗi
  - `PATCH lines` nhận **mảng** ngay từ đầu (sprint 3 cần batch)
  - `summary` liệt kê đủ `markupRateBps`, `costingRevision`, `qtyFallbackCount`, `costingSettingsMissing`
  - SSE có 4 event: `skeleton` · `day` · `error` · `done`
- **Validation**: Cả 2 dev đọc và xác nhận không cần hỏi thêm. Đây là điều kiện để track FE bắt đầu.

### Task 1.2 `[BE]` Thêm dependency
- **Location**: `requirements.txt`
- **Description**: `+ simpleeval`, `+ pytest-cov`. Pin version.
- **Dependencies**: —
- **Acceptance Criteria**: `pip install -r requirements.txt` sạch; `python -c "import simpleeval"` chạy
- **Validation**: `PYTHONPATH=. pytest` full suite vẫn xanh (không regression)

### Task 1.3 `[BE]` Tạo `pytest.ini` + marker `llm`
- **Location**: `pytest.ini`
- **Description**: Đăng ký marker `llm`. **Giữ nguyên** yêu cầu `PYTHONPATH=.` (không thêm `pythonpath=` để tránh đổi cách cả team đang chạy — CLAUDE.md ghi rõ điều này).
```ini
[pytest]
markers =
    llm: gọi LLM thật, cần API key, không chạy trong CI
```
- **Dependencies**: 1.2
- **Acceptance Criteria**: `pytest -m "not llm"` lọc đúng; không warning `PytestUnknownMarkWarning`
- **Validation**: `PYTHONPATH=. pytest -m "not llm" --collect-only | tail -1`

### Task 1.4 `[BE]` CI workflow chạy pytest + lint
- **Location**: `.github/workflows/test-backend.yml`
- **Description**: Job chạy `PYTHONPATH=. pytest -m "not llm"`. Job thứ hai chạy `cd quote-generator && npm run lint` (đủ 6 bước, không chỉ eslint).
- **Dependencies**: 1.3
- **Acceptance Criteria**:
  - Push commit làm hỏng 1 test ⇒ CI đỏ
  - Test có `@pytest.mark.llm` **không** chạy trong CI
  - Lint job chạy `npm run lint` chứ không phải `eslint`
- **Validation**: 1 commit cố tình hỏng + 1 commit sửa lại

### Task 1.5 `[BE]` `pricing/formulas.yaml`
- **Location**: `pricing/formulas.yaml`
- **Description**: 14 entry `qty` + `rounding` (xem [14.1 §3.1](./14.1-sprint-1-pricing-core.md))
- **Dependencies**: —
- **Acceptance Criteria**: Có `flat: "1"` làm escape hatch; `per_person_to` phủ đủ 5 currency của `SUPPORTED_CURRENCIES`
- **Validation**: `yaml.safe_load` không lỗi

### Task 1.6 `[BE]` `core/rules/formula_config.py`
- **Location**: `core/rules/formula_config.py`
- **Description**: Load + validate 2 YAML, cache theo mtime. Expression > 200 ký tự ⇒ log warning + bỏ qua entry.
- **Dependencies**: 1.5
- **Acceptance Criteria**: ≤ 80 dòng; không I/O ngoài đọc file; reload khi file đổi
- **Validation**: Test sửa file ⇒ lần load sau thấy giá trị mới

### Task 1.7 `[BE]` `resolve_qty` + `apply_markup`
- **Location**: `core/rules/service_pricing.py`
- **Description**: Hai hàm pure. `resolve_qty` **không bao giờ raise** — mọi nhánh trả `(int, bool)`. `apply_markup(net, markup_rate_bps)` dùng `net * (10_000 + bps) / 10_000`.
- **Dependencies**: 1.6
- **Acceptance Criteria**:
  - `apply_markup(1000, 2000) == 1200`
  - Core nhận integer bps; API boundary reject ngoài `[0, 9500]`
  - `resolve_qty` với unit lạ / thiếu biến / chia 0 ⇒ `(1, True)`
  - Costing core chỉ có markup formula; contract test chặn GP-style formula
- **Validation**: `tests/test_service_pricing.py` (12 test, xem [14.1 §5](./14.1-sprint-1-pricing-core.md)) + contract gate xanh

### Task 1.8 `[BE]` `price_lines` + `summary`
- **Location**: `core/rules/service_pricing.py`
- **Description**: Thứ tự bất biến: `qty → net → sell (làm tròn TỪNG DÒNG) → Σ → per_person`.
- **Dependencies**: 1.7
- **Acceptance Criteria**: `Σ line.sell == summary.sell_total`; gọi 2 lần cùng input ⇒ output identical
- **Validation**: `test_line_rounding_sums_to_total`, `test_pricing_is_pure`

### Task 1.9 `[BE]` `pricing/param_rules.yaml`
- **Location**: `pricing/param_rules.yaml`
- **Description**: Tầng B — `rooms`/`vehicles`/`guides`/`boats`/`sessions` + `archetype_overrides` (xem [14 §6.3](./14-ai-service-drafter-and-costing.md))
- **Dependencies**: 1.6
- **Acceptance Criteria**: `mobility_level == "limited"` ⇒ `seats >= 16`; `honeymoon` ⇒ `rooms == 1`
- **Validation**: `test_param_rules_yaml_evaluates` với 5 profile giả

### Task 1.10 `[BE]` `param_resolver.py` — merge 3 tầng
- **Location**: `core/rules/param_resolver.py`
- **Description**: `AUTO_OWNED` · `auto_params` · `base_params_from_rules` · `merge_params`. Định nghĩa `ParamContext` Protocol để sprint 4 cho `TripProfile` thoả (sprint 1 dùng dataclass tối giản).
- **Dependencies**: 1.9
- **Acceptance Criteria**:
  - Tầng A ghi đè **cuối cùng**: AI trả `nights=99` ⇒ params cuối là số thật
  - `params_source` phủ đủ mọi key trong `params`
  - `pax` lấy từ `room_config`, không từ `QuoteRequest.adults`
- **Validation**: `tests/test_param_resolver.py` (8 test)

### Task 1.11 `[FE]` `lib/types/service.ts` ∥
- **Location**: `quote-generator/lib/types/service.ts`
- **Description**: Type từ contract task 1.1. **Chỉ type + format**, không hàm tính.
- **Dependencies**: 1.1
- **Acceptance Criteria**: ≤ 90 dòng; không có hàm nào nhận `net`/`sell` rồi trả số
- **Validation**: `tsc --noEmit`

### Task 1.12 `[FE]` Lint gate chặn tính giá ở FE ∥
- **Location**: `quote-generator/scripts/lint-no-fe-pricing.mjs` · `package.json`
- **Description**: Chặn biểu thức số học trên identifier khớp `/(net|sell|total|price|minor)/i` trong `components/quotation-workspace/services/**` và `lib/hooks/useServiceLines.ts`. Nối vào chain `npm run lint`.
- **Dependencies**: 1.11
- **Acceptance Criteria**: File vi phạm cố ý ⇒ exit code ≠ 0 kèm đường dẫn + số dòng
- **Validation**: Tạo file vi phạm tạm, chạy, xoá

---

## Sprint 2: Persistence & API

**Goal**: Lưu và sửa được `service_lines` qua API. Engine sprint 1 chạy trên dữ liệu thật. FE dựng grid trên mock song song.

**Demo/Validation**:
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
PYTHONPATH=. pytest tests/test_service_line_api.py -v
# curl: POST 12 dòng → PATCH 12 giá → GET ⇒ sellTotal khớp tính tay
```

### Task 2.1 `[BE]` Model `ServiceLine`
- **Location**: `db/models/service_line.py` · `db/models/quotation_costing_settings.py`
- **Description**: `ServiceLine` dùng `JSON_VARIANT`, **không** markup per-line; CS1 mới là aggregate 1–1 gồm `quotation_id`, `markup_rate_bps`, `currency`, `costing_revision`, `updated_at`.
  - `costing_revision: int` ở CS1 — CAS quotation-wide, độc lập với `quotation_documents.revision`.
  - `qty_override: int | null` — sale sửa `qty` trực tiếp. Có giá trị ⇒ **thắng** công thức, bỏ qua `resolve_qty`.
- **Dependencies**: 1.8
- **Acceptance Criteria**:
  - FK `quotations.id` CASCADE; index line (`quotation_id, day, sort_order`) và CS1 có đúng một row / quotation
  - `markup_rate` per-line, `net_minor`, `sell_minor` **không tồn tại**; CS1 có `markup_rate_bps`
  - `qty_override` nullable, default `NULL`
- **Validation**: Review model + `test_qty_override_wins_over_formula`

### Task 2.2 `[BE]` Migration
- **Location**: `alembic/versions/20260824_36_service_lines.py`
- **Description**: Theo convention `YYYYMMDD_NN_slug`
- **Dependencies**: 2.1
- **Acceptance Criteria**: up → down → up sạch, không lỗi
- **Validation**: Chạy 3 lệnh alembic

### Task 2.3 `[BE]` Repository
- **Location**: `repositories/service_line_repository.py`
- **Description**: **Chỉ query**. `list_by_quotation` · `bulk_upsert` · `delete`. Lỗi typed vào `repositories/errors.py`.
- **Dependencies**: 2.2
- **Acceptance Criteria**: Không import `core.rules`, không tính toán
- **Validation**: Test repo với session thật

### Task 2.4 `[BE]` `service_line_service.py`
- **Location**: `services/service_line_service.py`
- **Description**: Nơi **duy nhất** chạm session. Draft/recalculate mới `merge_params` → `resolve_qty` (bỏ qua nếu có `qty_override`) và persist qty/params/formula version; GET chỉ `price_lines` từ snapshot + CS1.
  - `markupRateBps` đọc từ CS1; legacy thiếu row ⇒ 0 bps + `costingSettingsMissing: true`
  - **`paxBillable` đọc từ `pricing_facts.adults + children`**, KHÔNG từ `TripProfile.total_pax`
  - Lệch giữa hai nguồn ⇒ `paxMismatch: {profile: 6, facts: 4}` trong summary, UI cảnh báo, **không tự sửa**
  - `baseRevision` so với `CS1.costing_revision`, không phải document revision
- **Dependencies**: 2.3
- **Acceptance Criteria**: `core/rules/*` vẫn pure (không session lọt vào)
- **Validation**: `test_markup_from_costing_settings` · `test_legacy_missing_settings_defaults_zero` · `test_yaml_change_does_not_reprice_snapshot` · `test_pax_billable_from_facts_not_profile` · `test_pax_mismatch_reported`

### Task 2.5 `[BE]` Router 4 endpoint
- **Location**: `routers/v2/services.py` · `routers/v2/schemas/service_line.py`
- **Description**: GET · POST · PATCH (mảng) · DELETE. `def _get_helpers(): import main` **function-scope**.
- **Dependencies**: 2.4
- **Acceptance Criteria**:
  - Gate `no-main-import` exit 0: `if grep -Rn '^import main' routers/v2/services.py; then exit 1; fi`
  - 409 khi lệch `baseRevision` (so với `CS1.costing_revision`), kèm `recovery: "reload"`
  - PATCH/POST/DELETE **không** bump `quotation_documents.revision`
  - 401/403 đúng theo `require_owned_quotation`
- **Validation**: `tests/test_service_line_api.py` (14 test, xem [14.2 §5](./14.2-sprint-2-persistence-and-api.md))

### Task 2.6 `[BE]` Cập nhật manifest contract
- **Location**: `tests/test_v2_api_manifest_contract.py`
- **Description**: Thêm 4 operation. Đây là frozen contract — sửa phải chủ ý.
- **Dependencies**: 2.5
- **Acceptance Criteria**: Test xanh; không operation nào bị xoá nhầm
- **Validation**: `PYTHONPATH=. pytest tests/test_v2_api_manifest_contract.py tests/test_v2_error_envelope.py`

### Task 2.7 `[FE]` `useServiceLines` trên mock ∥
- **Location**: `quote-generator/lib/hooks/useServiceLines.ts`
- **Description**: Fetch · optimistic local cho ô đang gõ · debounce 300ms gom batch · 409 ⇒ `conflict = true`. Chạy trên fixture module (`NEXT_PUBLIC_SERVICE_FIXTURE=1`) theo contract 1.1 — **không** thêm MSW.
- **Dependencies**: 1.11, 1.1
- **Acceptance Criteria**:
  - 5 lần `patchLine` trong 300ms ⇒ **1** fetch
  - 409 ⇒ `conflict = true`, `lines` **không** bị ghi đè
  - `summary` lấy nguyên từ response, không tự tính
- **Validation**: `lib/__tests__/useServiceLines.test.ts` (3 test)

### Task 2.8 `[FE]` `ServiceLineRow` + `ServiceLinesTable` ∥
- **Location**: `components/quotation-workspace/services/`
- **Description**: Grid gom theo `day`, nhóm `TOÀN TRIP` (`day === null`) luôn cuối. `ServiceLineRow` bọc `memo`.
- **Dependencies**: 2.7
- **Acceptance Criteria**: `key={line.id}` · chỉ `typo-*` · chỉ design token · ba trạng thái `priceSource` hiển thị đúng
- **Validation**: `npm run lint` (đủ 6 bước + `lint-no-fe-pricing`)

---

## Sprint 3: 🎯 Grid thủ công dùng được thật

**Goal**: Sale mở tab **Dịch vụ & Giá vốn**, tự thêm dòng, gõ giá, thấy tổng đúng. **Không cần AI.** Nếu 3 sprint sau hoãn vô thời hạn, sản phẩm vẫn thay được Excel.

**Demo/Validation**:
- Tạo quotation mới → thêm 12 dòng bằng tay → gõ 12 giá → tổng khớp giá trị tính tay
- React DevTools Profiler: sửa 1 ô trong 70 dòng ⇒ **1** row re-render
- Mở 2 tab cùng sửa ⇒ tab sau hiện banner, chữ đang gõ **không mất**

### Task 3.0 `[BE]` `ParamContext` từ facts (chưa có TripProfile)
- **Location**: `services/service_line_service.py`
- **Description**: Sprint 2–3 chưa có `TripProfile`. Dựng `ParamContext` từ `quotation facts` + `rooming_heuristic_service` — **chính là hàm fallback của task 4.3**, chỉ dùng sớm hơn. Sprint 4 thay bằng `TripProfile` thật, giữ nguyên Protocol.
- **Dependencies**: 2.4
- **Acceptance Criteria**: `rooms` suy từ `rooming_heuristic_service`; `pax` từ facts; sprint 4 thay nguồn **không sửa** `param_resolver`
- **Validation**: `test_param_context_from_facts` · sprint 4 chạy lại test này với `TripProfile` vẫn xanh

### Task 3.1 `[FE]` Nối hook vào API thật
- **Location**: `lib/hooks/useServiceLines.ts`
- **Description**: Bỏ mock, trỏ vào endpoint sprint 2. Đây là **điểm đồng bộ BE↔FE đầu tiên**.
- **Dependencies**: 2.5, 2.7
- **Acceptance Criteria**: Không còn tham chiếu mock; 409 thật từ server xử lý đúng
- **Validation**: Thao tác tay + network log

### Task 3.2 `[FE]` `ServiceLinesSummaryBar`
- **Location**: `components/quotation-workspace/services/ServiceLinesSummaryBar.tsx`
- **Description**: NET · BÁN · Target GP · đếm `⬤ chưa giá` và `◐ SL fallback` · filter *Chỉ hiện dòng chưa có giá*
- **Dependencies**: 3.1
- **Acceptance Criteria**: Ô phái sinh hiện `…` khi `pending`; số đếm khớp `summary` từ server
- **Validation**: Screenshot 2 trạng thái

### Task 3.3 `[FE]` Thêm tab vào workspace
- **Location**: `components/quotation-workspace/QuotationWorkspaceClient.tsx`
- **Description**: +1 tab. Dùng `dynamic(..., { ssr: false })` nếu bundle vượt ngưỡng.
- **Dependencies**: 3.2
- **Acceptance Criteria**: Tab hiện; `npm run build` không tăng bundle route khác
- **Validation**: `npm run build` + so bundle size

### Task 3.4 `[FE]` Form thêm dòng
- **Location**: `components/quotation-workspace/services/AddServiceLineForm.tsx`
- **Description**: Chọn `category` + `unit` (dropdown lấy từ API trả `formulas.yaml:qty` keys) + gõ `title`.
- **Dependencies**: 3.3
- **Acceptance Criteria**: Thêm `unit` mới vào YAML ⇒ dropdown tự có, **không sửa FE**
- **Validation**: Thêm entry vào YAML, reload, kiểm dropdown

### Task 3.5 `[BE]` Endpoint trả danh mục `unit`
- **Location**: `routers/v2/services.py`
- **Description**: `GET /api/v2/service-units` trả keys + biến mỗi unit cần. Cập nhật manifest.
- **Dependencies**: 2.6
- **Acceptance Criteria**: Response render được dropdown mà FE không hardcode
- **Validation**: `test_service_units_reflects_yaml`

### Task 3.6 `[FE+BE]` Kiểm thử thủ công có checklist
- **Location**: `docs/plans/refactor-tech-stack/manual-checklist-sprint3.md`
- **Description**: 4 kịch bản ở [14.3 §5](./14.3-sprint-3-grid-ui-manual.md), ghi bằng chứng screenshot.
- **Dependencies**: 3.4, 3.5
- **Acceptance Criteria**: 4/4 PASS kèm ảnh
- **Validation**: File checklist có tick + ảnh đính kèm

---

## Sprint 4: TripAnalyst

**Goal**: `QuoteRequest` ngữ nghĩa → `TripProfile` cấu trúc. Sale sửa 1 chip ⇒ toàn bộ dòng tính lại.

**Demo/Validation**:
- Quotation có `special_requirements` nhắc ông bà ⇒ `pax = 6` dù form ghi `adults: 2`
- Đổi `archetype` trên UI ⇒ mọi dòng Accommodation đổi `qty`

### Task 4.1 `[BE]` Schema `TripProfile`
- **Location**: `schemas/trip_profile.py`
- **Description**: `TripProfile` + `RoomAllocation`, `extra="forbid"`, không trường tiền. Thoả `ParamContext` Protocol của task 1.10.
- **Dependencies**: 1.10
- **Acceptance Criteria**: `test_schema_has_no_money_field` xanh; `budget` **không** có trong schema
- **Validation**: `tests/test_trip_profile_contract.py` (3 test)

### Task 4.2 `[BE]` Prompt `trip_analyst.yaml`
- **Location**: `prompts/v1/trip_analyst.yaml`
- **Description**: Nêu rõ "trường số adults/children thường thiếu — nếu văn xuôi nhắc người không có trong số đếm, tính họ vào `room_config`".
- **Dependencies**: 4.1
- **Acceptance Criteria**: `PromptLoader.build_prompt_bundle("trip_analyst")` load được
- **Validation**: Test load

### Task 4.3 `[BE]` Agent + fallback
- **Location**: `services/trip_analyst.py`
- **Description**: `Agent(model=llm_client.get_model(), output_type=TripProfile, ...)`. Lỗi ⇒ `fallback_profile()` dựng từ `rooming_heuristic_service`, `confidence = 0`.
- **Dependencies**: 4.2
- **Acceptance Criteria**: Analyst raise ⇒ vẫn trả profile, **không** chặn luồng
- **Validation**: `test_analyst_failure_falls_back`

### Task 4.4 `[BE]` 10 fixture ngữ nghĩa
- **Location**: `tests/fixtures/quote_requests/*.json` · `tests/test_trip_analyst.py`
- **Description**: 10 ca ở [14.4 §5](./14.4-sprint-4-trip-analyst.md), đánh dấu `@pytest.mark.llm`.
- **Dependencies**: 4.3
- **Acceptance Criteria**: ≥ 8/10 PASS khi chạy tay với LLM thật; CI dùng mock chỉ kiểm shape
- **Validation**: `PYTHONPATH=. pytest tests/test_trip_analyst.py -m llm -v`

### Task 4.5 `[BE]` 2 endpoint trip-profile
- **Location**: `routers/v2/services.py`
- **Description**: `POST :analyze` ghi vào `document_json.trip_profile`. `PATCH` sửa ⇒ **recompute toàn bộ** `service_lines`.
- **Dependencies**: 4.3, 2.4
- **Acceptance Criteria**: `PATCH` đổi `room_config` 3→2 phòng ⇒ mọi dòng `per_room_per_night` giảm `qty`
- **Validation**: `test_patch_recomputes_all_lines`

### Task 4.6 `[BE]` Cập nhật manifest
- **Location**: `tests/test_v2_api_manifest_contract.py`
- **Dependencies**: 4.5
- **Validation**: Test xanh

### Task 4.7 `[FE]` `TripProfileCard` ∥
- **Location**: `components/quotation-workspace/services/TripProfileCard.tsx`
- **Description**: Chips sửa được · `room_config` sửa được · 3 cảnh báo (`unknowns`, `confidence` thấp, lệch pax vs form).
- **Dependencies**: 1.1, 3.3
- **Acceptance Criteria**: Sửa chip ⇒ PATCH ⇒ grid cập nhật; chỉ `typo-*`
- **Validation**: Thao tác tay + `npm run lint`

---

## Sprint 5: ServiceDrafter

**Goal**: AI điền 5/6 cột toàn tour. Cột giá vẫn do sale gõ.

**Demo/Validation**:
- `:draft` tour 8 ngày: skeleton hiện ngay, nhóm ngày điền dần
- Ngày ngủ cruise **không** có dòng Meal/Transport
- `SELECT * FROM service_lines WHERE unit_price_minor > 0` trả **0 dòng**
- `DRAFTER_MODE=off` vẫn dùng được grid

### Task 5.1 `[BE]` Schema `ServiceDraft`
- **Location**: `schemas/service_draft.py`
- **Description**: 8 field, `extra="forbid"`, không trường tiền.
- **Dependencies**: 4.1
- **Acceptance Criteria**: `test_schema_has_no_money_field` + `test_ai_params_filtered_by_auto_owned` xanh
- **Validation**: `tests/test_service_draft_contract.py` (4 test)

### Task 5.2 `[BE]` Migration cột POI cho destination
- **Location**: `alembic/versions/…_37_destination_poi.py` · `db/models/destination.py`
- **Description**: `+poi_json` (POI + cường độ vận động + số bậc thang + thời lượng), `+visa_policy_json`, `+season_note`. Seed vài destination chính.
- **Dependencies**: —  ∥ (chạy song song 5.1)
- **Acceptance Criteria**: up → down → up sạch; ≥ 3 destination có POI
- **Validation**: Alembic + query

### Task 5.3 `[BE]` Tool `get_destination_brief`
- **Location**: `services/drafter_tools.py` · `repositories/destination_brief_repository.py`
- **Description**: Filter POI theo `mobility_level` + `interests` **ở SQL**. Trả ≤ 8 dòng, **không** giá.
- **Dependencies**: 5.2
- **Acceptance Criteria**: `mobility_level="limited"` ⇒ POI `steps > 50` bị loại; response không có key nào chứa giá
- **Validation**: `tests/test_drafter_tools.py` (5 test)

### Task 5.4 `[BE]` Tool `find_similar_past_days`
- **Location**: `services/drafter_tools.py` · `repositories/service_history_repository.py`
- **Description**: Query `service_lines` + `quotations` theo destination + archetype + style, trả tần suất.
- **Dependencies**: 5.3
- **Acceptance Criteria**: Không có lịch sử ⇒ `[]`, **không raise**
- **Validation**: `test_similar_days_empty_is_valid`

### Task 5.5 `[BE]` Prompt `service_drafter.yaml`
- **Location**: `prompts/v1/service_drafter.yaml`
- **Description**: `unit_catalog` render từ `formulas.yaml`, `base_params` render từ `param_rules.yaml` — prompt **tự đồng bộ** khi YAML đổi.
- **Dependencies**: 5.1
- **Acceptance Criteria**: `test_prompt_renders_all_units` — mọi key trong `qty` xuất hiện trong prompt
- **Validation**: Test

### Task 5.6 `[BE]` Agent per-day + fan-out
- **Location**: `services/service_drafter.py`
- **Description**: `asyncio.gather(..., return_exceptions=True)` cho N ngày + 1 trip-level. Guard: `max_tool_calls=6`, `timeout=25s`, `on_error="skip_day"`. `DRAFTER_MODE=off` ⇒ skeleton rỗng, không gọi LLM.
- **Dependencies**: 5.4, 5.5
- **Acceptance Criteria**:
  - 1 ngày lỗi ⇒ các ngày khác vẫn có dòng
  - Trip-level dedupe theo `(category, title)`
  - Draft override `params` mà `note` rỗng ⇒ bị loại + log
- **Validation**: `tests/test_service_drafter.py` (7 test)

### Task 5.7 `[BE]` Day context giàu dữ kiện
- **Location**: `services/service_drafter.py`
- **Description**: Context chứa `overnight_type`, `meals_already_covered`, `transport_already_covered`, `previous_day_stay_includes` — lấy từ `staysReconciler`. **Không** viết rule hậu kiểm.
- **Dependencies**: 5.6
- **Acceptance Criteria**: `test_cruise_day_has_no_meal_or_transport` · `test_bb_hotel_suppresses_next_breakfast` xanh
- **Validation**: Test + query DB sau draft thật

### Task 5.8 `[BE]` Endpoint `:draft` SSE
- **Location**: `routers/v2/services.py`
- **Description**: 4 event `skeleton` · `day` · `error` · `done`. Cập nhật manifest.
- **Dependencies**: 5.7
- **Acceptance Criteria**: `skeleton` phát **trước** dòng đầu tiên; mỗi `day` là đơn vị độc lập
- **Validation**: `curl -N` xem stream

### Task 5.9 `[FE]` Grid tiêu thụ SSE ∥
- **Location**: `lib/hooks/useServiceLines.ts` · `ServiceLinesTable.tsx`
- **Description**: Render khung ngày từ `skeleton`, gộp từng `day`, event `error` ⇒ nhóm rỗng + nút *Soạn lại ngày này*.
- **Dependencies**: 5.8, 3.1
- **Acceptance Criteria**: 3 test SSE ở [14.5 §5](./14.5-sprint-5-service-drafter.md) xanh
- **Validation**: `npm test` + screenshot 2 mốc thời gian

---

## Sprint 6: Apply Pricing & E2E nghiệm thu

**Goal**: Nối giá vốn vào giá bán. Nghiệm thu toàn luồng.
**⚠️ Sprint chạm tiền thật. Không merge nếu bất kỳ ranh giới nào chưa PASS.**

**Demo/Validation**: Bảng 21 ranh giới ở [14.6 §5.2](./14.6-sprint-6-apply-pricing-and-e2e.md), mỗi dòng kèm bằng chứng.

### Task 6.1 `[BE]` `service_pricing_application.py`
- **Location**: `services/service_pricing_application.py`
- **Description**: `Σ net → apply_markup(CS1.markup_rate_bps) → sell_total → CanonicalPricingOption id="opt-from-services"`. Gọi `inferOptionRatesFromTotal` để chia perAdult/perChild — **không viết lại phép chia**; lưu applied costing revision/rate/total/timestamp.
- **Dependencies**: 2.4, 5.9
- **Acceptance Criteria**:
  - Hai option sale tự nhập **còn nguyên**
  - `perAdultMinor` khớp kết quả gọi `inferOptionRatesFromTotal` trực tiếp
  - `net=1000, markup_rate_bps=2000 ⇒ sell=1200`
  - `adults`/`children` truyền vào `inferOptionRatesFromTotal` lấy từ **`pricing_facts`**, không từ `TripProfile`
- **Validation**: `tests/test_apply_pricing.py` (8 test)

### Task 6.2 `[BE]` Endpoint `:apply-pricing`
- **Location**: `routers/v2/services.py`
- **Description**: Apply gate `sell_total > 0`, bằng 0 ⇒ `422 VALIDATION_FAILED` + `fieldErrors[0].path = "serviceLines"`. Publication gate riêng dùng `GateResult`/`GateIssue`: sell total và coverage tối thiểu đều phải đạt; catalog rỗng + một giá manual không mặc định đủ publish. Cập nhật manifest.
- **Dependencies**: 6.1
- **Acceptance Criteria**: PATCH line/rate ⇒ `pricing_facts` **không** đổi, managed option `stale=true`; mutation pricing quotation published phải tạo business successor
- **Validation**: `test_apply_is_explicit_not_automatic`

### Task 6.3 `[FE]` Nút **Áp giá**
- **Location**: `ServiceLinesSummaryBar.tsx`
- **Description**: Disabled khi `sellTotalMinor === 0`. Confirm dialog nêu rõ sẽ ghi vào bảng giá bán.
- **Dependencies**: 6.2
- **Acceptance Criteria**: Enabled ngay khi gõ ≥ 1 giá
- **Validation**: Screenshot 2 trạng thái

### Task 6.4 `[BE]` E2E backend
- **Location**: `tests/test_service_drafter_e2e.py`
- **Description**: Một test chạy trọn kịch bản [14.6 §5.1](./14.6-sprint-6-apply-pricing-and-e2e.md) với **mock LLM trả fixture cố định**, assert ranh giới 2, 4, 6, 7, 8, 9, 11, 12, 15, 16.
- **Dependencies**: 6.2
- **Acceptance Criteria**: 10 ranh giới assert trong 1 test, chạy được trong CI
- **Validation**: `PYTHONPATH=. pytest tests/test_service_drafter_e2e.py -v`

### Task 6.5 `[FE+BE]` Checklist E2E thủ công 21 ranh giới
- **Location**: `docs/plans/refactor-tech-stack/e2e-acceptance-sprint6.md`
- **Description**: 21 ranh giới, mỗi dòng ghi bằng chứng (response body / SQL output / Playwright report / screenshot / timing). Ranh giới **10, 14, 18 lấy bằng chứng từ Playwright** (task 6.6); ranh giới 17 lấy từ gate `display-drift` (task 6.6b); 1, 3, 5, 13, 21 kiểm bằng tay.
- **Dependencies**: 6.4, 6.3, 6.6, 6.6b
- **Acceptance Criteria**:
  - **21/21 PASS** kèm bằng chứng
  - 3 ngưỡng chất lượng [§5.3](./14.6-sprint-6-apply-pricing-and-e2e.md) đạt trên 10 tour thật
  - Dừng ở ranh giới hỏng đầu tiên, không chạy tiếp
- **Validation**: File checklist tick đủ

### Task 6.6 `[FE]` Playwright — 3 spec chặn merge
- **Location**: `quote-generator/e2e/service-drafter.spec.ts` · `quote-generator/playwright.config.ts`
- **Description**: Dựng `@playwright/test` và viết **3 spec** ứng với ranh giới chỉ quan sát được trong trình duyệt **và** chạm tiền / mất dữ liệu:
  `typing price updates totals` (10) · `apply button disabled until price entered` (14) · `conflict shows reload banner` (18).
  Luật phân tầng đầy đủ: [14.6 §6](./14.6-sprint-6-apply-pricing-and-e2e.md).
- **Dependencies**: 6.3
- **Acceptance Criteria**:
  - 3 spec xanh **trong CI**, không phải chạy tay
  - Spec 18 assert **chữ đang gõ còn nguyên** sau 409, không chỉ assert banner xuất hiện
  - 4 spec ⚪ còn lại có issue backlog mở, ghi rõ ranh giới nào đang dựa vào kiểm thủ công
- **Validation**: `npx playwright test e2e/service-drafter.spec.ts -g "typing price updates totals|apply button disabled|conflict shows reload banner"`

### Task 6.6b `[BE]` Script CI gate
- **Location**: `scripts/ci-gates-sprint6.sh`
- **Description**: Ba gate `no-main-import` · `display-drift` · `single-markup` viết dưới dạng lệnh có exit code, nội dung ở [14.6 §6.1](./14.6-sprint-6-apply-pricing-and-e2e.md). Gắn vào CI job, không để dạng "chạy tay rồi đọc output".
- **Dependencies**: 6.2
- **Acceptance Criteria**: Cố tình thêm `import main` module-level ⇒ CI đỏ; sửa 1 file trong `quote-generator/components/display/` ⇒ CI đỏ
- **Validation**: `bash scripts/ci-gates-sprint6.sh` exit 0 trên nhánh sạch, exit 1 khi inject vi phạm

### Task 6.7 `[BE+FE]` Đồng bộ tài liệu agent
- **Location**: `AGENTS.md` · `quote-generator/AGENTS.md` · `.cursorrules` · `CLAUDE.md`
- **Description**: Thêm mục về `service_lines`, 2 file YAML, ranh giới "không tính giá ở FE", reconciler mới nếu có.
- **Dependencies**: 6.5
- **Acceptance Criteria**: 4 file cập nhật **cùng commit** — repo yêu cầu duplicate guidance phải đồng bộ
- **Validation**: `git diff --stat` cho 4 file

---

## Testing Strategy

| Tầng | Công cụ | Chạy khi | Nội dung |
| :-- | :-- | :-- | :-- |
| Unit — pure rules | pytest | CI mỗi push | `service_pricing` · `param_resolver` — **coverage 100%** |
| Contract — schema LLM | pytest | CI | Không trường tiền · `extra="forbid"` · `AUTO_OWNED` lọc |
| Contract — HTTP | pytest | CI | `test_v2_api_manifest_contract` · `test_v2_error_envelope` |
| Integration — API | pytest + Postgres | CI | 4 CRUD · 2 profile · 1 apply · 409 · 422 |
| E2E — backend | pytest + mock LLM | CI | 1 test phủ 10 ranh giới |
| E2E — UI | **thủ công có checklist** | Trước merge sprint 6 | 9 ranh giới còn lại, kèm screenshot |
| LLM chất lượng | pytest `-m llm` | **Chạy tay**, cần API key | 10 fixture ngữ nghĩa + 10 tour thật |
| FE unit | `node --test` | CI | format · hook debounce · SSE gộp |
| Lint | `npm run lint` (6 bước) + `lint-no-fe-pricing` | CI | Typography · display isolation · colors · **không tính giá FE** |

**CI gate — lệnh có exit code, không phải lệnh để người đọc output:**

> Exit code đo thật trong bash — chi tiết ở [14.6 §6.1](./14.6-sprint-6-apply-pricing-and-e2e.md):
> `grep … # phải rỗng` trả **`0` khi tìm thấy vi phạm** ⇒ CI xanh đúng lúc lỗi lọt, và trả `1` khi
> sạch ⇒ CI đỏ oan dưới `set -e`. `git diff --stat -- <path đúng>` trả `0` **dù có drift** ⇒ không chặn.
> `components/display/` còn không tồn tại ở repo root (thật ra là `quote-generator/components/display/`,
> `git` trả `128`), nên gate cũ chưa từng kiểm cái gì.

```bash
PYTHONPATH=. pytest tests/test_service_pricing.py   # contract markup formula
bash scripts/ci-gates-sprint6.sh                    # task 6.6b — 3 gate ở 14.6 §6.1
```

Nội dung `scripts/ci-gates-sprint6.sh` (SSoT: [14.6 §6.1](./14.6-sprint-6-apply-pricing-and-e2e.md)):

```bash
set -euo pipefail
if grep -Rn '^import main' routers/v2/services.py; then
  echo "FAIL[no-main-import]"; exit 1; fi
if ! git diff --quiet "${CI_BASE_REF:-origin/main}"...HEAD -- quote-generator/components/display/; then
  echo "FAIL[display-drift]"; exit 1; fi
count=$(grep -Rn --include='*.py' 'apply_markup(' services/ | grep -vc 'test' || true)
[ "$count" -eq 1 ] || { echo "FAIL[single-markup]: $count != 1"; exit 1; }
```

---

## Potential Risks & Gotchas

| # | Rủi ro | Mức | Sprint | Khắc chế |
| :-: | :-- | :-: | :-: | :-- |
| 1 | **GP vs markup** — dùng nhầm công thức sai tiền mọi quotation | 🔴 | 1, 6 | Trong costing core chỉ tồn tại `apply_markup`; bps snapshot 2000 trên net 1000 phải ra 1200. Grep gate trong CI |
| 2 | **`TripProfile` sai ⇒ 70 dòng lệch** | 🔴 | 4 | Cũng là single point of *fix*: sale sửa 1 chip. `reasoning`/`confidence`/`unknowns` hiển thị |
| 3 | **LLM bịa giá** | 🔴 | 4, 5 | 2 lớp: `extra="forbid"` + tool không trả `unit_price` |
| 4 | **Áp giá tự động đổi quotation đã gửi khách** | 🔴 | 6 | Thao tác chủ động + `test_apply_is_explicit_not_automatic` |
| 5 | Dev "tối ưu" bằng cách tính tổng ở FE ⇒ `formulas.yaml` mất vị thế nguồn duy nhất | 🟠 | 3 | `lint-no-fe-pricing` (task 1.12) chạy trong CI |
| 6 | AI ghi đè biến tầng A | 🟠 | 5 | `AUTO_OWNED` lọc ở `merge_params` (task 1.10) |
| 7 | Trip-level nhân N lần | 🟠 | 5 | Pass riêng `day=null` + dedupe `(category, title)` |
| 8 | Ghi đè option sale tự nhập | 🟠 | 6 | Chỉ đụng id `"opt-from-services"` |
| 9 | **Contract drift giữa 2 track** | 🟠 | 1–3 | Task 1.1 đóng băng contract trước; điểm đồng bộ ở task 3.1 |
| 10 | `qty_fallback` im lặng ⇒ `qty=1` sai mà không ai biết | 🟠 | 1, 3 | Cờ boolean + `◐` trên ô + **đếm dồn lên header** |
| 11 | Test LLM flaky làm đỏ CI | 🟡 | 4, 5 | `@pytest.mark.llm` tách khỏi CI (task 1.3) |
| 12 | **Regression UI không ai bắt** ở luồng chạm tiền | 🟠 | 6 | 3 spec Playwright **chặn merge** (task 6.6) phủ ranh giới 10/14/18. 4 ranh giới còn lại đã có backend E2E hoặc SQL assert; phần thuần thị giác mới là rủi ro chấp nhận, kèm issue backlog |
| 13 | `simpleeval` eval expression độc | 🟡 | 1 | Expression chỉ từ file repo, không từ user/LLM · whitelist names · giới hạn 200 ký tự |
| 14 | Grid 70 dòng lag | 🟡 | 3 | `memo` + `key={line.id}` + debounce 300ms + Profiler gate |
| 15 | Prompt lệch config khi thêm `unit` | 🟡 | 5 | `unit_catalog` render từ YAML + `test_prompt_renders_all_units` |
| 16 | Frozen contract vỡ do dời route | 🟡 | 2, 4, 5, 6 | Cập nhật manifest **cùng commit** với route |
| 17 | Tài liệu agent lệch nhau | 🟡 | 6 | Sửa 4 file cùng lúc (task 6.7) |
| 18 | **Lệch pax giữa `TripProfile` (6) và `pricing_facts` (4)** ⇒ giá vốn tính cho 6, per-person chia cho 4 | 🟠 | 2, 6 | `paxMismatch` trong summary + cảnh báo UI. Hệ **không tự sửa** form — sale quyết |
| 19 | Revision theo document language gây nhầm 409 | 🟡 | 2 | Contract task 1.1 dùng một CS1 `costing_revision` cho mọi costing mutation; không dùng document revision |

---

## Rollback Plan

| Mức | Tình huống | Cách lùi |
| :-- | :-- | :-- |
| **Feature flag** | AI cho kết quả tệ | `DRAFTER_MODE=off` ⇒ grid mở với skeleton rỗng, sale làm tay. Không cần deploy |
| **Sprint 6** | Áp giá sai số | Revert managed option về applied-costing snapshot trước. Published quotation không sửa: tạo business successor; hai option sale nhập còn nguyên |
| **Sprint 5** | ServiceDrafter hỏng | Tắt endpoint `:draft` qua router. Sprint 3–4 vẫn chạy: sale nhập tay + có `TripProfile` |
| **Sprint 4** | TripAnalyst hỏng | Fallback `rooming_heuristic_service` đã dựng sẵn (task 4.3), tự kích hoạt |
| **Sprint 3** | Grid hỏng | Ẩn tab. Quotation không phụ thuộc `service_lines` |
| **Sprint 2** | Schema sai | `alembic downgrade -1`. Bảng `service_lines` độc lập, không FK ngược vào bảng khác |
| **Sprint 1** | Công thức qty sai | Sửa YAML chỉ cho draft/recalculate mới; quotation line snapshot cũ không đổi. Markup sửa qua CS1, không YAML |

**Điểm không lùi được**: sau task 6.2, nếu sale đã bấm Áp giá và gửi quotation cho khách. Vì vậy task 6.5 (21 ranh giới) là điều kiện merge cứng, không phải khuyến nghị.
