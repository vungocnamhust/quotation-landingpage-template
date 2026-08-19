# Quote Generator Frontend (`quote-generator`)

Hệ thống hiển thị Brochure Báo giá Du lịch Trực tuyến (Display System) và Không gian Làm việc Biên soạn Báo giá (Staff Workspace) được xây dựng trên nền tảng **Next.js 14+ (App Router)** và **Tailwind CSS**.

---

## 🏗️ 1. Cấu Trúc Thư Mục Chi Tiết

```text
quote-generator/
├── app/                         # Next.js App Router (Async Server Components & Layouts)
│   ├── [locale]/q/[slug]/       # Trang xem brochure công khai (RSC, TTFB thấp)
│   ├── workspace/               # Workspace dành cho Sales & Travel Designer
│   │   └── quotations/[id]/edit # Form nhập liệu báo giá & phân phối
│   ├── content-studio/          # Studio tinh chỉnh nội dung & typography
│   ├── layout.tsx               # Root Layout & Font Definitions
│   └── globals.css              # Theme CSS Variables (Chrome, Spacing, Color)
│
├── components/                  # React Component System
│   ├── display/                 # Hệ thống hiển thị brochure công khai
│   │   ├── atoms.tsx            # Badge, PriceTag, Markdown Text, Pill
│   │   ├── molecules.tsx        # HotelCard, DayTimelineCard, CostSummary
│   │   ├── sections.tsx         # Hero, Itinerary, Hotels, Pricing, Designer
│   │   ├── RouteMapClientIsland # Bản đồ tương tác Client Island (Mapbox/Leaflet)
│   │   ├── ItineraryCarousel    # Slider xem ngày hành trình (Client Island)
│   │   └── PdfBrochureDocument  # Template brochure chuyên dụng cho in ấn PDF
│   ├── quotation-workspace/     # Form nhập liệu Facts, Intake, Commercial
│   ├── staff-workspace/         # Quản lý Tour Components, Catalogs, Request Details
│   ├── destination/             # DestinationSelect + useDestinationSearch
│   ├── accommodation/           # AccommodationSelect + useAccommodationSearch
│   ├── partner/                 # PartnerSelect + usePartnerSearch
│   ├── travel-designer/         # TravelDesignerSelect + useTravelDesignerSearch
│   └── ui/                      # Reusable UI Controls (CustomSelect, RichTextEditor)
│
├── config/                      # Design Tokens & Single Source of Truth (SSOT)
│   ├── typography.ts            # 🌟 SSOT Typography: định nghĩa toàn bộ typo-* classes
│   ├── themeTokens.ts           # Token màu sắc và giao diện (Palette, Theme)
│   └── runtimeThemeTokens.ts    # Biến đổi token giao diện tại runtime
│
├── display/                     # Hạt nhân 5-Layer Display System
│   ├── runtimePageBuilder.ts    # Chuyển đổi dữ liệu raw sang PageViewModel
│   ├── layoutRegistry.ts        # Đăng ký các layout và bố cục section
│   ├── themeRegistry.ts         # Đăng ký các theme brochure
│   ├── typographySlots.ts       # Định nghĩa slot typography cho từng section
│   └── types.ts                 # Type definitions cho PageViewModel & Sections
│
├── data/                        # Schema dữ liệu & Dữ liệu tĩnh
│   └── factsTypes.ts            # Schema dữ liệu Quotation Facts
│
├── lib/                         # Core Logic, Prefill Engine & APIs
│   ├── prefillRules.ts          # 🌟 Pure Business Rules (tính ngày, số đêm, meals)
│   ├── prefillEngine.ts         # 🌟 Atomic Facade Updaters cho React State
│   ├── quotationApi.ts          # API Client giao tiếp với FastAPI Backend
│   └── publicQuotationApi.ts    # API Client nạp dữ liệu brochure công khai
│
├── public/                      # Static assets & localized web fonts
└── docs/                        # Tài liệu hợp đồng hệ thống (Display, Prefill, Typo)
```

---

## 💎 2. Hai Trụ Cột Kiến Trúc Cốt Lõi

### A. 5-Layer Display System (Hiển thị Brochure)
Brochure hiển thị không render JSX tùy tiện mà đi qua chu trình 5 tầng:
1. **Theme Tokens**: Cấu hình bảng màu, phông chữ tại `config/themeTokens.ts` và `config/typography.ts`.
2. **View Mode Contract**: Hỗ trợ 3 chế độ xem mượt mà qua URL query:
   - `/?view=desktop`: Giao diện Web Desktop cao cấp.
   - `/?view=mobile`: Giao diện di động dọc, tối ưu chạm vuốt.
   - `/?view=pdf` hoặc `/pdf`: Định dạng dàn trang chuẩn khổ A4 in ấn.
3. **Layout System & Builder**: `display/runtimePageBuilder.ts` map dữ liệu thô sang `PageViewModel`.
4. **Component System**: Phân cấp theo **Atomic Design**:
   - `atoms.tsx` $\to$ `molecules.tsx` $\to$ `sections.tsx`.
5. **Client Islands**: Tách biệt tương tác nặng bằng `dynamic(..., { ssr: false })` (`RouteMapClientIsland`, `ItineraryCarousel`).

---

### B. 3-Layer Prefill & Derivation Engine (Xử lý Dữ liệu)
Quản lý trạng thái nhập liệu báo giá theo 3 lớp chuẩn:
- **Layer 1 - Schema (`data/factsTypes.ts`)**: Định nghĩa type nghiêm ngặt cho `QuotationFacts`.
- **Layer 2 - Pure Business Rules (`lib/prefillRules.ts`)**: Hàm thuần túy (pure functions) không side-effect:
  - `calculateNights(startDate, endDate)`
  - `inferOvernightDestinations(itinerary)`
  - `getDefaultMealsForLang(lang)` (Hỗ trợ đa ngữ EN, VI, AR).
- **Layer 3 - Atomic Facade Updaters (`lib/prefillEngine.ts`)**: Các hàm updater cập nhật đơn lượt:
  ```tsx
  // Sử dụng trong Component:
  setFacts(current => updateCustomerName(current, "John Doe"));
  setFacts(current => updateItineraryDayDestination(current, dayIndex, "Hanoi"));
  ```
  *(Tuyệt đối không dùng chuỗi `useEffect` để đồng bộ state qua lại).*

---

## 🎨 3. Quy Chuẩn Typography SSOT (Bắt Buộc)

- Mọi định dạng chữ trong brochure **PHẢI** dùng class `typo-*` được export từ [`config/typography.ts`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/quote-generator/config/typography.ts).
- **Không sử dụng**: `text-xl`, `font-bold`, `tracking-wide`, v.v. trực tiếp trong các component thuộc `components/display/`.

---

## 🚀 4. Lệnh Khởi Chạy & Kiểm Tra Chất Lượng (Quality Gates)

```bash
# Khởi chạy môi trường dev (port 8115)
npm run dev

# Kiểm tra cú pháp & type
npm run lint

# Kiểm tra tuân thủ Typography SSOT
npm run lint:typography

# Kiểm tra ranh giới hiển thị Display System
npm run lint:display-system

# Kiểm tra Build Production (Server Component & Webpack)
npm run build
```
