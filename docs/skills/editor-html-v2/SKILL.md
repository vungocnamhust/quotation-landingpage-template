---
name: editor-html-v2
description: Quy trình định nghĩa và bổ sung dữ liệu mới (data field) vào Editor V2 Sidebar & Landingpage Template (Quotation V2). Sử dụng khi cần thêm field mới vào Sidebar Editor, cập nhật JSON schema QuoteDocument, hoặc đồng bộ hiển thị 2 chiều với template HTML.
---

# Editor HTML V2 Skill

Tài liệu hướng dẫn quy trình từng bước để định nghĩa, bổ sung và đồng bộ một trường dữ liệu văn bản (**Text Field**) hoặc thuộc tính mới vào **Sidebar Editor V2** và **Jinja HTML Landing Page Template**.

---

## 1. Tổng quan Kiến trúc Editor V2

Editor V2 hoạt động dựa trên cơ chế **Form-based Reactive Control Panel** nằm ở cột bên phải (Sidebar Editor Panel) kết hợp với **Inline Editing** trên giao diện Landing Page bên trái.

* **Frontend State**: `state.document` trong `assets/brochure_shared_draft.js`
* **Schema Reference**: `QuoteDocument` trong `quote_document.py`
* **Jinja HTML Template**: `templates/vietnam_luxury_brosure.html`
* **Persistence API**: `PUT /api/v2/quotations/{quotation_id}/document` (Autosave kèm `baseRevision`)

---

## 2. Quy trình 3 bước thêm Data Field vào Editor V2

### Bước 1: Khai báo trường mới trong `getSidebarSections()`
Mở file [assets/brochure_shared_draft.js](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/assets/brochure_shared_draft.js) và tìm đến hàm `getSidebarSections()`.

Sử dụng hàm helper `field(path, label, type)` để khai báo:
```javascript
field("đường_dẫn_json", "Nhãn hiển thị", "kiểu_input")
```

#### Các loại Input hỗ trợ (`type`):
* `"text"` *(mặc định)*: Ô nhập 1 dòng `<input type="text">`
* `"textarea"`: Ô nhập văn bản nhiều dòng `<textarea>`
* `"color"`: Bộ chọn màu sắc `<input type="color">`
* `"asset"`: Bộ chọn/tải ảnh `<input type="file">` & Media Gallery

#### Ví dụ khai báo:
```javascript
// Thêm ô "Ghi chú đặc biệt" vào nhóm Trip
const trip = [
  field("trip.title", "Trip title"),
  field("trip.lede", "Trip lede", "textarea"),
  field("trip.specialNote", "Ghi chú đặc biệt", "textarea"), // 👈 Trường mới
];

// Thêm ô "Hotline 24/7" vào nhóm Designer
const designer = [
  field("designer.name", "Designer name"),
  field("designer.hotline247", "Hotline 24/7", "text"), // 👈 Trường mới
  field("designer.email", "Email"),
];
```

---

### Bước 2: Cơ chế Tự động Ràng buộc Dữ liệu (`data-path`)
Hệ thống sử dụng hàm `renderField()` để tự động render HTML cho Sidebar:

```html
<label class="draft-field">
  <span>Ghi chú đặc biệt</span>
  <input type="text" data-path="trip.specialNote" value="..." />
</label>
```

* **Tự động lắng nghe (`input` Event)**: Khi người dùng nhập liệu, sự kiện `input` tự động lấy `data-path="trip.specialNote"`, cập nhật giá trị vào `state.document` và gọi `scheduleSave()` để **Autosave ngầm (debounce 2s)** qua API `PUT /api/v2/quotations/{id}/document`.
* Không cần viết thêm bất kỳ đoạn code bắt sự kiện thủ công nào!

---

### Bước 3: Đồng bộ hiển thị lên Landing Page Template
Để nội dung từ Sidebar hiển thị và cho phép chỉnh sửa trực tiếp trên trang Landing Page bên trái:

Mở file Jinja template [templates/vietnam_luxury_brosure.html](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/templates/vietnam_luxury_brosure.html) và gắn thuộc tính `data-editable`:

```html
<p data-editable="trip.specialNote">
  {{ (document.trip if document else {}).specialNote or "Ghi chú mặc định..." }}
</p>
```

---

## 3. Tóm tắt nhanh Check-list Thực thi

1. Mở `assets/brochure_shared_draft.js` ➔ Thêm dòng `field("path.field", "Label", "text/textarea")` vào `getSidebarSections()`.
2. Mở `templates/vietnam_luxury_brosure.html` ➔ Thêm thẻ HTML có `data-editable="path.field"`.
3. Tải lại trang (`F5`) ➔ Ô nhập mới xuất hiện trên Sidebar, cho phép sửa trực tiếp và tự động Autosave lên Postgres DB!
