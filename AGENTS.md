# Master Guidelines & Vibe Coding Rules for AI Agents

> **Dành cho AI Assistants (Cursor, Windsurf, Claude Code, Antigravity, Codex)**: Đây là tài liệu quy chuẩn tối thượng (Single Source of Truth) định hình toàn bộ kiến trúc, hợp đồng dữ liệu và phong cách lập trình cho repository này. Mọi thay đổi code đều **BẮT BUỘC** tuân thủ tuyệt đối các quy tắc dưới đây.

---

## 🏛️ 1. Bản Đồ Tư Duy Kiến Trúc (Architecture Mental Model)

Repository là một hệ thống **Monorepo** gồm 3 trụ cột cốt lõi:
1. **Core Backend (Python / FastAPI — Port 8111)**:
   - Điểm khởi chạy `main.py` và các API routers trong `routers/`.
   - Nghiệp vụ phân tách theo mô hình: **Router** $\to$ **Service** $\to$ **Repository** $\to$ **Database** (`db/`, `alembic/`).
   - Động cơ sinh tài liệu & xuất bản: `quote_document.py`, `quote_generation.py`, `templates/`, `published/`.
2. **Frontend App (`quote-generator` / Next.js 14+ App Router — Port 8115)**:
   - Tầng xem brochure công khai: Server Component (RSC), render siêu tốc, hỗ trợ 3 chế độ `desktop`, `mobile`, `pdf`.
   - Tầng nghiệp vụ nhân viên: `workspace/` (Quotation Intake, Facts Form, Commercial Panels) và `content-studio/`.
3. **Notification Subsystem (`notification/` — Port 8116)**:
   - Microservice độc lập xử lý thu nạp sự kiện (Event Ingestion), phân phối thông báo đa kênh, Background Delivery Worker và Real-time Server-Sent Events (SSE).
   - Chi tiết quy tắc nghiệp vụ chuyên sâu: **Tham chiếu trực tiếp [`notification/AGENTS.md`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/notification/AGENTS.md)**.

---

## 🔒 2. Ranh Giới Bất Biến Liên Subsystem (Cross-Subsystem Invariants)

- **Domain Event & Outbox Pattern**: Các domain services ở Core Backend **KHÔNG ĐƯỢC** gửi trực tiếp Email/SMS/Push hoặc import trực tiếp worker. Bắt buộc ghi nhận sự kiện vào `outbox_events` table qua `services/outbox_service.py` để `services/outbox_relay.py` tiếp vận sang Notification Service.
- **Database & Schema Isolation**: Database `notification` độc lập hoàn toàn với database `quotation`. Không thực hiện JOIN chéo schema giữa 2 cơ sở dữ liệu.
- **Docker DNS & Connection String SSOT**: Trong môi trường Docker đa mạng (`quotation_net`, `dmc-network`), các connection string **BẮT BUỘC** dùng host `quotation-local-postgres-1:5432` và dynamic password `${POSTGRES_PASSWORD:-quotation_local_password}`.

---

## 🐍 3. Chuẩn Mực Backend (FastAPI & Python Guidelines)

Tuân thủ nghiêm ngặt kỹ năng `fastapi` và các chuẩn mực Python hiện đại:

- **Style & Format**: 4 spaces, type hints đầy đủ cho 100% tham số và giá trị trả về (`-> ReturnType`).
- **Dependency Injection**: Luôn dùng cú pháp `Annotated[..., Depends(...)]`.
  ```python
  from typing import Annotated
  from fastapi import Depends, APIRouter
  
  CurrentUserDep = Annotated[User, Depends(get_current_user)]
  
  @router.get("/me")
  def get_me(user: CurrentUserDep) -> UserResponse:
      return user
  ```
- **Async vs Sync Path Operations**:
  - Chỉ dùng `async def` khi bên trong gọi các thư viện thực sự hỗ trợ `async/await` không gây block.
  - Mặc định dùng `def` thông thường cho các tác vụ I/O blocking (SQLAlchemy sync, xử lý file, Jinja2 template rendering). FastAPI sẽ tự động chạy trong threadpool để không block Event Loop.
- **Pydantic Validation**:
  - Không dùng `...` (Ellipsis) làm giá trị mặc định cho trường bắt buộc.
  - Không dùng `RootModel` tự chế khi có thể dùng kiểu chuẩn `Annotated[list[T], Field(...)]`.
  - Luôn định nghĩa `response_model` hoặc kiểu trả về hàm rõ ràng để Pydantic serialize dữ liệu qua Rust core tối ưu tốc độ.
- **Phân tách tầng trách nhiệm**:
  - Router (`routers/`): Chỉ nhận request, validate qua Pydantic, gọi Service và trả response.
  - Service (`services/`): Chứa toàn bộ business logic, tính toán giá, sinh mã slug, render template.
  - Repository (`repositories/`): Chỉ thực thi truy vấn database.

---

## ⚛️ 4. 4 Hợp Đồng Bất Biến Frontend (`quote-generator`)

Khi làm việc trong thư mục `quote-generator/`, AI **TUYỆT ĐỐI KHÔNG ĐƯỢC VI PHẠM** 4 hợp đồng cốt lõi sau:

### 📜 Contract 1: 5-Layer Display System SSOT
Hệ thống brochure hiển thị công khai tuân theo 5 tầng nghiêm ngặt:
$$\text{Theme Tokens} \longrightarrow \text{View Modes} \longrightarrow \text{Layout System} \longrightarrow \text{Component System} \longrightarrow \text{Section ViewModel}$$
- **Atoms** (`components/display/atoms.tsx`): Badge, PriceTag, Markdown Text, Pill.
- **Molecules** (`components/display/molecules.tsx`): HotelCard, DayTimelineCard, CostSummary.
- **Sections** (`components/display/sections.tsx`): HeroSection, ItinerarySection, PricingSection, v.v.
- **Ranh giới cô lập**: Tuyệt đối **KHÔNG** import các component chỉnh sửa (`workspace/`, `content-studio/`, editor tools) vào tầng `display/` hoặc ngược lại.

### 📜 Contract 2: 4-Layer Bidirectional Reconciler & Canonical Adapter Engine
$$\text{Layer 1: Pure Reconcilers} \longleftrightarrow \text{Layer 2: Canonical Adapters} \longleftrightarrow \text{Layer 3: Facade Updaters} \longleftrightarrow \text{Layer 4: React UI}$$

Mọi logic nghiệp vụ tính toán có ràng buộc liên đới (Domain Invariants) **BẮT BUỘC** tuân thủ mô hình 4 tầng khép kín:
- **Tầng 1 (Pure Domain Reconcilers - `lib/rules/*Reconciler.ts`)**: Hàm thuần túy, 0 React dependencies, 100% deterministic. Quản lý 4 Domain Reconcilers cốt lõi:
  1. **`TemporalTripReconciler`** (`tripReconciler.ts`): Tự động đồng bộ `startDate` $\longleftrightarrow$ `endDate` $\longleftrightarrow$ `duration` $\longleftrightarrow$ `itineraryDays` qua 4 atomic operations (`addDay`, `removeDay`, `setStartDate`, `setEndDate`, `updateDay`).
  2. **`StaysReconciler`** (`staysRules.ts`): Tự động gom cụm/phân tách khách sạn lưu trú theo chuỗi ngày có cùng điểm ngủ đêm `overnight`.
  3. **`PricingReconciler`** (`pricingRules.ts`): Suy luận 2 chiều giữa đơn giá khách lẻ (`per_person_rate`) và tổng gói (`total_price`).
  4. **`PartyReconciler`** (`partyRules.ts`): Suy luận nhãn đoàn `party_label` và `greeting_name` từ tên khách và số lượng `adults`/`children`.
- **Tầng 2 (Canonical Adapters - `lib/rules/*Adapter.ts`)**: Cầu nối chuyển đổi dữ liệu 2 chiều không làm xáo trộn Schema gốc:
  - `tripAdapter.fromQuoteRequest()` $\longleftrightarrow$ `tripAdapter.syncToQuoteRequest()`
  - `tripAdapter.fromQuotationFacts()` $\longleftrightarrow$ `tripAdapter.syncToQuotationFacts()`
- **Tầng 3 (Facade Updaters / Hooks - `lib/prefillEngine.ts` / `useTemporalTrip.ts`)**: Single-pass state transformations cho React State (`setFacts`, `setFormState`).
- **Tầng 4 (React UI Components - `BasicItineraryDayGrid`, Drawers, Forms)**:
  - **NGHIÊM CẤM** viết code tính toán ngày, co giãn danh sách ngày, tính giá trong các event handler (`handleAddDay`, `handleRemoveDay`, `handleDateChange`).
  - **BẮT BUỘC** chỉ gọi 1 dòng Facade Updater hoặc Adapter Reconciler.

```tsx
// ✅ ĐÚNG: Gọi Adapter + Reconciler hoặc Facade Updater 1 dòng
const handleAddDay = () => {
  const canonical = tripAdapter.fromQuoteRequest(formState, itineraryDays);
  const updated = tripReconciler.addDay(canonical);
  const synced = tripAdapter.syncToQuoteRequest(updated, formState);
  setFormState(synced.formState);
  setItineraryDays(synced.itineraryDays);
};

// ❌ SAI CẤM KỴ: Tự ý mutate inline, Date.now() thủ công, hoặc dùng useEffect để sync
const handleAddDay = () => {
  const nextDay = { day_number: days.length + 1, destination: "" };
  setDays([...days, nextDay]); // ❌ LỆCH: departure_date và duration không được cập nhật!
};
```

### 📜 Contract 3: Typography SSOT (Single Source of Truth)
- Toàn bộ font size, font weight, letter spacing, line height trong brochure **BẮT BUỘC** lấy từ `quote-generator/config/typography.ts` thông qua các class ngữ nghĩa `typo-*` (`typo-display-hero`, `typo-body-base`, `typo-card-title`, v.v.).
- **NGHIÊM CẤM** dùng các class tiện ích tùy tiện của Tailwind như `text-sm`, `text-lg`, `font-bold`, `tracking-wider`, `leading-tight` trong các component brochure `display/`. Sẽ bị chốt chặn `npm run lint:typography` bắt lỗi ngay lập tức.

### 📜 Contract 4: Reusable Component Standards (5 Golden Standards)
Khi tạo hoặc refactor các UI Selectors / Pickers (`DestinationSelect`, `AccommodationSelect`, `PartnerSelect`, `TravelDesignerSelect`):
1. **Tách Headless Hook**: Logic tìm kiếm, lọc, debounce nằm riêng trong `use<Name>Search.ts`.
2. **Chuẩn hóa Callback Contract**: `onChange(id: string | null, profile?: ProfileType | null) => void`.
3. **Đa dạng kích thước & biến thể**: Hỗ trợ `size="sm"|"md"|"lg"` và `variant="default"|"compact"|"inline"`.
4. **Tránh Memory Leak**: Chỉ đăng ký global event listener (`mousedown`) khi dropdown đang mở (`isOpen === true`).
5. **Accessible Keyboard Navigation**: Hỗ trợ phím `ArrowDown`, `ArrowUp`, `Enter`, `Escape`.

---

## ⚡ 5. Hiệu Năng & Ranh Giới Server/Client (Next.js 14+ RSC)

- **Server-First**: Mọi Route Pages trong `app/` mặc định là **Async Server Components (RSC)**.
- **Xóa bỏ Waterfalls**: Sử dụng `Promise.all([params, headers()])` khi nạp dữ liệu ở Server.
- **Client Islands & Dynamic Imports**: Các component nặng hoặc dùng browser APIs bắt buộc phải bọc bằng `next/dynamic` với `{ ssr: false }`:
  - Bản đồ hành trình: `RouteMapClientIsland.tsx`
  - Soạn thảo văn bản: `RichTextEditor.tsx` (bọc TipTap)
  - Drawer & Modals: `AccommodationDrawerModal.tsx`, `PartnerManageDrawer.tsx`
- **Regex Performance**: Khởi tạo RegExp một lần duy nhất ở module scope (Hoist RegExp), không khởi tạo lại bên trong hàm render hoặc vòng lặp `map()`.

---

## 🚫 6. Danh Mục Lỗi Cấm Kỵ (AI Anti-Patterns to Avoid)

| ❌ Hành vi SAI CẤM KỴ | ✅ Hành vi ĐÚNG CHUẨN MỰC |
| :--- | :--- |
| Tự viết logic tính ngày, co giãn lịch trình hoặc tính giá inline trong UI event handler | Sử dụng Domain Reconciler (`tripReconciler.ts`, `pricingRules.ts`) & Canonical Adapter |
| Tự bịa đặt font class Tailwind (`text-2xl font-semibold`) vào brochure UI | Dùng class ngữ nghĩa `typo-*` từ `config/typography.ts` |
| Gọi gửi email/push trực tiếp từ domain service | Ghi Domain Event vào Transactional Outbox |
| Đọc trực tiếp bảng database của notification từ Core Backend | Gọi API qua HTTP hoặc giao tiếp qua Outbox Event stream |
| Dùng `useEffect` để tính toán state phái sinh | Tính toán trực tiếp trong render hoặc gọi hàm pure từ `prefillRules.ts` / Reconciler |
| Dùng `key={index}` trong danh sách động có thêm/xóa/sửa | Dùng định danh duy nhất `key={item.id}` hoặc `key={item.code}` |
| Tạo component khổng lồ >500 dòng chứa nhiều mục đích | Phân rã thành Atoms, Molecules và Sections con độc lập |
| Import chéo giữa Display System và Staff Workspace | Giữ display system độc lập hoàn toàn, chỉ nhận `PageViewModel` |
| Bỏ qua `npm run lint` sau khi code | Luôn chạy và pass 100% các chốt kiểm duyệt chất lượng |

---

## 🧭 7. Bảng Kích Hoạt Kỹ Năng Cục Bộ (Local Skills Index)

Khi nhận nhiệm vụ, hãy tự động kích hoạt kỹ năng tương ứng trong `.agents/skills/`:

| Kỹ năng (Skill Name) | Khi nào cần kích hoạt? |
| :--- | :--- |
| `fastapi` | Tạo/sửa API router, Pydantic schemas, streaming SSE, background workers. |
| `notification-core` | Thiết kế kiến trúc sự kiện thông báo, policy, preferences, inbox semantics. |
| `notification-fastapi` | Tạo/sửa API router notification, asyncpg DB models, transaction boundaries. |
| `notification-reliability` | Thiết kế outbox, retry, idempotency key, worker failure isolation, DLQ. |
| `notification-review` | Thực hiện review gate kiểm tra correctness, reliability trước khi merge code notification. |
| `quote-generator-display-governor` | Sửa đổi giao diện brochure, theme, view modes (desktop/mobile/pdf), layout system. |
| `quote-generator-prefill-governor` | Thêm field vào form intake, tính ngày/đêm, gán default values, tính toán chi phí. |
| `quote-generator-typography-ssot` | Sửa đổi cỡ chữ, phông nền, headings, button text, CTA, token typography. |
| `react-component-reuse-governor` | Tạo mới hoặc refactor các UI Selectors, Pickers, Modals, Headless hooks. |
| `quote-generator-section-builder` | Thêm mới hoặc tái cấu trúc các brochure sections (`Hero`, `Itinerary`, `Hotels`, v.v.). |
| `quote-generator-parity-review` | So sánh độ khớp giao diện (parity audit) giữa code Next.js và prototype HTML gốc. |

---

## 🧪 8. Quy Trình Tự Kiểm Thử (Self-Verification Protocol)

Sau khi hoàn thành bất kỳ tác vụ code nào, AI **BẮT BUỘC** chạy kiểm tra theo thứ tự:

1. **Backend Core & Domain Rules**:
   ```bash
   PYTHONPATH=. pytest tests/test_domain_rules.py tests/test_business_gates.py tests/test_quote_request_service.py tests/test_quote_request_revisions.py
   ```
2. **Notification Subsystem**:
   ```bash
   PYTHONPATH=. pytest tests/test_notification_api.py
   curl -f http://localhost:8116/health
   ```
3. **Frontend (`quote-generator`)**:
   ```bash
   cd quote-generator
   npm run lint               # Kiểm tra ESLint & TypeScript
   npm run lint:typography    # Kiểm tra vi phạm Typography SSOT
   npm run lint:display-system# Kiểm tra ranh giới Display
   npm run build              # Kiểm tra Server Component & Production Build
   ```
