# Master Guidelines & Vibe Coding Rules for AI Agents

> **Dành cho AI Assistants (Cursor, Windsurf, Claude Code, Antigravity, Codex)**: Đây là tài liệu quy chuẩn tối thượng (Single Source of Truth) định hình toàn bộ kiến trúc, hợp đồng dữ liệu và phong cách lập trình cho repository này. Mọi thay đổi code đều **BẮT BUỘC** tuân thủ tuyệt đối các quy tắc dưới đây.

---

## 🏛️ 1. Bản Đồ Tư Duy Kiến Trúc (Architecture Mental Model)

Repository là một hệ thống **Monorepo** gồm 2 phần chính:
1. **Core Backend (Python / FastAPI)**:
   - Điểm khởi chạy `main.py` và các API routers trong `routers/`.
   - Nghiệp vụ phân tách theo mô hình: **Router** $\to$ **Service** $\to$ **Repository** $\to$ **Database** (`db/`, `alembic/`).
   - Động cơ sinh tài liệu & xuất bản: `quote_document.py`, `quote_generation.py`, `templates/`, `published/`.
2. **Frontend App (`quote-generator` / Next.js 14+ App Router)**:
   - Tầng xem brochure công khai: Server Component (RSC), render siêu tốc, hỗ trợ 3 chế độ `desktop`, `mobile`, `pdf`.
   - Tầng nghiệp vụ nhân viên: `workspace/` (Quotation Intake, Facts Form, Commercial Panels) và `content-studio/`.

---

## 🐍 2. Chuẩn Mực Backend (FastAPI & Python Guidelines)

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

## ⚛️ 3. 4 Hợp Đồng Bất Biến Frontend (`quote-generator`)

Khi làm việc trong thư mục `quote-generator/`, AI **TUYỆT ĐỐI KHÔNG ĐƯỢC VI PHẠM** 4 hợp đồng cốt lõi sau:

### 📜 Contract 1: 5-Layer Display System SSOT
Hệ thống brochure hiển thị công khai tuân theo 5 tầng nghiêm ngặt:
$$\text{Theme Tokens} \longrightarrow \text{View Modes} \longrightarrow \text{Layout System} \longrightarrow \text{Component System} \longrightarrow \text{Section ViewModel}$$
- **Atoms** (`components/display/atoms.tsx`): Badge, PriceTag, Markdown Text, Pill.
- **Molecules** (`components/display/molecules.tsx`): HotelCard, DayTimelineCard, CostSummary.
- **Sections** (`components/display/sections.tsx`): HeroSection, ItinerarySection, PricingSection, v.v.
- **Ranh giới cô lập**: Tuyệt đối **KHÔNG** import các component chỉnh sửa (`workspace/`, `content-studio/`, editor tools) vào tầng `display/` hoặc ngược lại.

### 📜 Contract 2: 3-Layer Prefill & Data Derivation Engine
$$\text{Layer 1: Schema (factsTypes.ts)} \longrightarrow \text{Layer 2: Pure Rules (prefillRules.ts)} \longrightarrow \text{Layer 3: Facade Updaters (prefillEngine.ts)}$$
- **Quy tắc**: Mọi logic tính toán (tính số đêm, suy luận điểm đến qua đêm, tính chi phí, gán bữa ăn mặc định đa ngữ EN/VI/AR qua `getDefaultMealsForLang(lang)`) **PHẢI** nằm trong `prefillRules.ts`.
- **Thực thi trong React**: Gọi trực tiếp các atomic facade updater trong `prefillEngine.ts`:
  ```tsx
  // ✅ ĐÚNG: Gọi Atomic Facade Updater
  setFacts(current => updateCustomerName(current, value));
  setFacts(current => updateItineraryDates(current, startDate, endDate));

  // ❌ SAI: Tự ý mutate inline hoặc tạo chuỗi useEffect để sync state
  useEffect(() => {
    setFacts({ ...facts, nights: calculateNights(facts.startDate, facts.endDate) });
  }, [facts.startDate, facts.endDate]);
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

## ⚡ 4. Hiệu Năng & Ranh Giới Server/Client (Next.js 14+ RSC)

- **Server-First**: Mọi Route Pages trong `app/` mặc định là **Async Server Components (RSC)**.
- **Xóa bỏ Waterfalls**: Sử dụng `Promise.all([params, headers()])` khi nạp dữ liệu ở Server.
- **Client Islands & Dynamic Imports**: Các component nặng hoặc dùng browser APIs bắt buộc phải bọc bằng `next/dynamic` với `{ ssr: false }`:
  - Bản đồ hành trình: `RouteMapClientIsland.tsx`
  - Soạn thảo văn bản: `RichTextEditor.tsx` (bọc TipTap)
  - Drawer & Modals: `AccommodationDrawerModal.tsx`, `PartnerManageDrawer.tsx`
- **Regex Performance**: Khởi tạo RegExp một lần duy nhất ở module scope (Hoist RegExp), không khởi tạo lại bên trong hàm render hoặc vòng lặp `map()`.

---

## 🚫 5. Danh Mục Lỗi Cấm Kỵ (AI Anti-Patterns to Avoid)

| ❌ Hành vi SAI CẤM KỴ | ✅ Hành vi ĐÚNG CHUẨN MỰC |
| :--- | :--- |
| Tự bịa đặt font class Tailwind (`text-2xl font-semibold`) vào brochure UI | Dùng class ngữ nghĩa `typo-*` từ `config/typography.ts` |
| Dùng `useEffect` để tính toán state phái sinh | Tính toán trực tiếp trong render hoặc gọi hàm pure từ `prefillRules.ts` |
| Dùng `key={index}` trong danh sách động có thêm/xóa/sửa | Dùng định danh duy nhất `key={item.id}` hoặc `key={item.code}` |
| Tạo component khổng lồ >500 dòng chứa nhiều mục đích | Phân rã thành Atoms, Molecules và Sections con độc lập |
| Import chéo giữa Display System và Staff Workspace | Giữ display system độc lập hoàn toàn, chỉ nhận `PageViewModel` |
| Bỏ qua `npm run lint` sau khi code | Luôn chạy và pass 100% 4 chốt kiểm duyệt chất lượng |

---

## 🧭 6. Bảng Kích Hoạt Kỹ Năng Cục Bộ (Local Skills Index)

Khi nhận nhiệm vụ, hãy tự động kích hoạt kỹ năng tương ứng trong `.agents/skills/`:

| Kỹ năng (Skill Name) | Khi nào cần kích hoạt? |
| :--- | :--- |
| `fastapi` | Tạo/sửa API router, Pydantic schemas, streaming SSE, background workers. |
| `quote-generator-display-governor` | Sửa đổi giao diện brochure, theme, view modes (desktop/mobile/pdf), layout system. |
| `quote-generator-prefill-governor` | Thêm field vào form intake, tính ngày/đêm, gán default values, tính toán chi phí. |
| `quote-generator-typography-ssot` | Sửa đổi cỡ chữ, phông nền, headings, button text, CTA, token typography. |
| `react-component-reuse-governor` | Tạo mới hoặc refactor các UI Selectors, Pickers, Modals, Headless hooks. |
| `quote-generator-section-builder` | Thêm mới hoặc tái cấu trúc các brochure sections (`Hero`, `Itinerary`, `Hotels`, v.v.). |
| `quote-generator-parity-review` | So sánh độ khớp giao diện (parity audit) giữa code Next.js và prototype HTML gốc. |

---

## 🧪 7. Quy Trình Tự Kiểm Thử (Self-Verification Protocol)

Sau khi hoàn thành bất kỳ tác vụ code nào, AI **BẮT BUỘC** chạy kiểm tra theo thứ tự:

1. **Backend**:
   ```bash
   python -m pytest tests
   ```
2. **Frontend**:
   ```bash
   cd quote-generator
   npm run lint               # Kiểm tra ESLint & TypeScript
   npm run lint:typography    # Kiểm tra vi phạm Typography SSOT
   npm run lint:display-system# Kiểm tra ranh giới Display
   npm run build              # Kiểm tra Server Component & Production Build
   ```
