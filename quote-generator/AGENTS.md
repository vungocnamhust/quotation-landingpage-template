<!-- BEGIN:quote-generator-agent-rules -->
# Frontend Next.js 14+ Agent Rules (`quote-generator`)

> **Chú ý cho AI Coding Assistants**: Mọi thay đổi trong thư mục `quote-generator/` đều phải tuân thủ nghiêm ngặt các quy chuẩn sau đây. Tham khảo toàn bộ Master Rules tại [../AGENTS.md](../AGENTS.md).

---

## ⚡ 1. Server-First & Ranh Giới RSC
- Tất cả các trang trong `app/` đều là **Async React Server Components (RSC)**.
- Chỉ gắn directive `"use client"` khi component thực sự cần tương tác DOM, state cục bộ, hoặc browser events.
- Các component nặng (Bản đồ Leaflet/Mapbox, TipTap Rich Text Editor, Drawer Modals) **BẮT BUỘC** bọc qua `dynamic(..., { ssr: false })`.
- Xóa bỏ waterfalls ở Server bằng cách nạp dữ liệu song song qua `Promise.all([params, headers()])`.

---

## 🎨 2. Typography SSOT & Semantic Tokens
- **BẮT BUỘC** dùng class ngữ nghĩa `typo-*` từ `config/typography.ts`.
- **NGHIÊM CẤM** dùng các class tiện ích Tailwind tùy tiện như `text-sm`, `text-lg`, `font-bold`, `tracking-wider` trong các brochure components (`components/display/`).
- Mọi thay đổi về chữ phải chạy kiểm tra bằng lệnh: `npm run lint:typography`.

---

## 🔄 3. Quản Lý Trạng Thái & 3-Layer Prefill Engine
- Toàn bộ logic phái sinh dữ liệu (tính số đêm, suy luận điểm đến qua đêm, gán bữa ăn mặc định đa ngữ EN/VI/AR) **PHẢI** nằm trong `lib/prefillRules.ts`.
- Trong React component, cập nhật state thông qua các atomic facade updaters trong `lib/prefillEngine.ts`:
  ```tsx
  // ✅ Chuẩn mực:
  setFacts(current => updateCustomerName(current, value));
  setFacts(current => updateItineraryDates(current, startDate, endDate));
  ```
- **NGHIÊM CẤM** tạo chuỗi `useEffect` để đồng bộ state phái sinh hoặc tự ý mutate state inline.

---

## 🧩 4. Chuẩn Hóa Reusable UI Selectors (5 Golden Standards)
Khi làm việc với các Selector (`DestinationSelect`, `AccommodationSelect`, `PartnerSelect`, `TravelDesignerSelect`):
1. Tách Headless Search Hook (`use<Name>Search.ts`).
2. Chuẩn hóa callback: `onChange(id: string | null, profile?: T | null) => void`.
3. Chỉ đăng ký global event listener (`mousedown`) khi `isOpen === true`.
4. Hỗ trợ đầy đủ `size` (`sm`|`md`|`lg`), `variant` (`default`|`compact`|`inline`), và phím điều hướng A11y (`ArrowDown`, `ArrowUp`, `Enter`, `Escape`).

---

## 🧪 5. Quality Gates Bắt Buộc Trước Khi Hoàn Thành
```bash
npm run lint
npm run lint:typography
npm run lint:display-system
npm run build
```
<!-- END:quote-generator-agent-rules -->
