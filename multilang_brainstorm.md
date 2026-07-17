# Brainstorm: Giải Quyết Triệt Để 4 RCA Multi-Language

## Tổng Quan Kiến Trúc Đề Xuất

Giải pháp tổng thể là **Hybrid Locale Architecture**:
- **Tầng 1 (Template):** Jinja2 filter `| translate(lang)` bao quanh mọi chuỗi tĩnh → giải quyết RCA 1
- **Tầng 2 (Dictionary):** `STATIC_DICTIONARY` mở rộng đầy đủ cho template Luxury → giải quyết RCA 2
- **Tầng 3 (Backend):** Mọi hàm sinh nội dung động nhận tham số `lang` và tra cứu từ điển cục bộ → giải quyết RCA 3
- **Tầng 4 (Schema):** Mở rộng `TourQuotationPayload` cho phép Client override bất kỳ trường nào → giải quyết RCA 4

---

## RCA 1 — Template Hardcoded Strings

### Phương Án 1A: Wrap toàn bộ bằng `| translate(lang)` *(Khuyến nghị)*

**Cơ chế:** Tìm & thay thế mọi text tĩnh tiếng Anh trong `vietnam_heritage_luxury.html` bằng filter Jinja2.

```html
<!-- BEFORE -->
<h2>Muslim-Friendly Travel Care</h2>
<h3>Inclusions</h3>
<h3>Exclusions</h3>
<th>Term</th>
<th>Condition</th>
<td>Deposit</td>
<h2>Meet Your Travel Specialist</h2>
<h2>Booking & Payment Terms</h2>
<h2>Selected Hotel Plan</h2>

<!-- AFTER -->
<h2>{{ "Muslim-Friendly Travel Care" | translate(lang) }}</h2>
<h3>{{ "Inclusions" | translate(lang) }}</h3>
<h3>{{ "Exclusions" | translate(lang) }}</h3>
<th>{{ "Term" | translate(lang) }}</th>
<th>{{ "Condition" | translate(lang) }}</th>
<td>{{ "Deposit" | translate(lang) }}</td>
<h2>{{ "Meet Your Travel Specialist" | translate(lang) }}</h2>
<h2>{{ "Booking & Payment Terms" | translate(lang) }}</h2>
<h2>{{ "Selected Hotel Plan" | translate(lang) }}</h2>
```

**Ưu điểm:**
- Thay đổi tối thiểu, không phá vỡ cấu trúc hiện tại
- Ngay lập tức có hiệu lực khi render lại
- Fallback tự động về tiếng Anh nếu thiếu từ điển

**Nhược điểm:**
- Phải quét thủ công ~30-50 vị trí trong file template dài 2900+ dòng

**Số lượng cần wrap ước tính:** ~45 chuỗi tĩnh trong `vietnam_heritage_luxury.html`

---

### Phương Án 1B: Data-attribute `data-i18n` + Client-side JS switcher *(Cho button chuyển ngôn ngữ động)*

**Cơ chế:** Thêm `data-i18n="key"` vào từng phần tử HTML. Khi user bấm nút đổi ngôn ngữ, JS đọc file JSON i18n và thay nội dung DOM mà không reload trang.

```html
<!-- Template -->
<h2 data-i18n="muslim_care_heading">Muslim-Friendly Travel Care</h2>
<h3 data-i18n="inclusions">Inclusions</h3>
<td data-i18n="deposit">Deposit</td>
```

```javascript
// i18n switcher JS (thêm vào cuối template)
const I18N_CACHE = {};
async function switchLang(lang) {
  if (!I18N_CACHE[lang]) {
    const res = await fetch(`/assets/i18n/${lang}.json`);
    I18N_CACHE[lang] = await res.json();
  }
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (I18N_CACHE[lang][key]) el.textContent = I18N_CACHE[lang][key];
  });
  document.documentElement.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
  document.documentElement.setAttribute('lang', lang);
}
```

```json
// /assets/i18n/ar.json
{
  "muslim_care_heading": "الرعاية الصديقة للمسلمين",
  "inclusions": "ما يشمله البرنامج",
  "exclusions": "ما لا يشمله البرنامج",
  "deposit": "الدفعة المقدمة",
  "selected_hotel_plan": "خطة الفنادق المختارة",
  ...
}
```

**Ưu điểm:**
- ✅ **Đây là giải pháp DUY NHẤT cho nút "chuyển ngôn ngữ" không reload trang**
- Tách biệt hoàn toàn nội dung dịch ra file JSON riêng, dễ quản lý
- Designer/translator không cần chạm vào Python code
- Có thể mở rộng vô hạn ngôn ngữ chỉ bằng cách thêm file JSON
- Có thể lazy-load để không làm chậm trang

**Nhược điểm:**
- Cần thêm khoảng ~150ms để fetch JSON khi lần đầu chuyển ngôn ngữ (có thể cache)
- Phải duy trì đồng bộ giữa `data-i18n` keys trong template và các file JSON

> [!IMPORTANT]
> **Phương án 1A + 1B phải kết hợp:** 1A để server render đúng ngay từ đầu (SSR), 1B để cho phép switch ngôn ngữ động phía client không reload.

---

## RCA 2 — Mở Rộng `STATIC_DICTIONARY`

### Phương Án 2A: Bổ sung toàn bộ keys của template Luxury vào `STATIC_DICTIONARY`

**Thực thi:** Thêm ~50 keys mới vào dictionary trong `main.py` bao gồm tất cả labels tĩnh của template Luxury.

```python
# main.py — mở rộng STATIC_DICTIONARY
STATIC_DICTIONARY = {
  # ... existing keys ...

  # === RCA 2: LUXURY TEMPLATE KEYS ===
  "Selected Hotel Plan": {
    "ar": "خطة الفنادق المختارة",
    "vi": "Kế Hoạch Khách Sạn"
  },
  "Proposed hotels and luxury cruises selected for your journey. Subject to availability at confirmation.": {
    "ar": "الفنادق والرحلات البحرية الفاخرة المختارة لرحلتك. تخضع للتوافر عند التأكيد.",
    "vi": "Các khách sạn và du thuyền sang trọng được tuyển chọn cho hành trình của bạn."
  },
  "Room Notes & Special Requests": {
    "ar": "ملاحظات الغرفة والطلبات الخاصة",
    "vi": "Ghi Chú Phòng & Yêu Cầu Đặc Biệt"
  },
  "What Your Journey Includes": {
    "ar": "ما يشمله برنامج رحلتك",
    "vi": "Những Gì Hành Trình Bao Gồm"
  },
  "Inclusions": {
    "ar": "ما يشمله البرنامج",
    "vi": "Dịch Vụ Bao Gồm"
  },
  "Exclusions": {
    "ar": "ما لا يشمله البرنامج",
    "vi": "Dịch Vụ Không Bao Gồm"
  },
  "Muslim-Friendly Travel Care": {
    "ar": "الرعاية الصديقة للمسلمين",
    "vi": "Dịch Vụ Thân Thiện Với Người Hồi Giáo"
  },
  # Muslim-Friendly description (long paragraph)
  "Vietnam Safar can assist with halal-friendly meal planning...": {
    "ar": "يمكن لفيتنام سفر المساعدة في التخطيط لوجبات حلال...",
    "vi": "Vietnam Safar có thể hỗ trợ lập kế hoạch bữa ăn Halal..."
  },
  "Booking & Payment Terms": {
    "ar": "شروط الحجز والدفع",
    "vi": "Điều Khoản Đặt Chỗ & Thanh Toán"
  },
  "Commercial conditions, deposits, and cancellation policy for this booking.": {
    "ar": "الشروط التجارية والودائع وسياسة الإلغاء لهذا الحجز.",
    "vi": "Điều kiện thương mại, đặt cọc và chính sách hủy cho đặt chỗ này."
  },
  "Term": { "ar": "البند", "vi": "Điều Khoản" },
  "Condition": { "ar": "الشرط", "vi": "Điều Kiện" },
  "Deposit": { "ar": "الدفعة المقدمة", "vi": "Đặt Cọc" },
  "Balance": { "ar": "المبلغ المتبقي", "vi": "Số Dư" },
  "Cancellation": { "ar": "الإلغاء", "vi": "Hủy Bỏ" },
  "Confirmation": { "ar": "التأكيد", "vi": "Xác Nhận" },
  "Meet Your Travel Specialist": {
    "ar": "تعرّف على مصمم رحلتك",
    "vi": "Gặp Gỡ Chuyên Gia Thiết Kế Hành Trình"
  },
  "Your Dedicated Specialist": {
    "ar": "مستشارك المتخصص",
    "vi": "Chuyên Viên Riêng Của Bạn"
  },
  "Expertise:": { "ar": "التخصص:", "vi": "Chuyên Môn:" },
  "Experience:": { "ar": "الخبرة:", "vi": "Kinh Nghiệm:" },
  "Your Travel Specialist": { "ar": "مصمم رحلتك", "vi": "Chuyên Gia Hành Trình" },
  "Next step": { "ar": "الخطوة التالية", "vi": "Bước Tiếp Theo" },
  "Confirm dates, then refine the luxury layer.": {
    "ar": "أكّد التواريخ ثم اضبط مستوى الفخامة.",
    "vi": "Xác nhận ngày, sau đó tinh chỉnh lớp dịch vụ sang trọng."
  },
  "Final Details Required": { "ar": "التفاصيل النهائية المطلوبة", "vi": "Thông Tin Cần Thiết" },
  "After Confirmation": { "ar": "بعد التأكيد", "vi": "Sau Khi Xác Nhận" },
  "Website": { "ar": "الموقع الإلكتروني", "vi": "Website" },
  "WhatsApp": { "ar": "واتساب", "vi": "WhatsApp" },
  "Prepared by": { "ar": "أُعدّ بواسطة", "vi": "Được Chuẩn Bị Bởi" },
  "Request final confirmation": { "ar": "طلب التأكيد النهائي", "vi": "Yêu Cầu Xác Nhận Cuối" },
  "per person": { "ar": "للشخص الواحد", "vi": "mỗi người" },
  "Total:": { "ar": "الإجمالي:", "vi": "Tổng:" },
  "Important Note": { "ar": "ملاحظة مهمة", "vi": "Lưu Ý Quan Trọng" },
  "✓ CONFIRMED MAIN OPTION": { "ar": "✓ الخيار المؤكد الرئيسي", "vi": "✓ LỰA CHỌN ĐÃ XÁC NHẬN" },
  "Highlights:": { "ar": "أبرز الفعاليات:", "vi": "Điểm Nổi Bật:" },
  "Notes:": { "ar": "ملاحظات:", "vi": "Ghi Chú:" },
  "Overnight": { "ar": "المبيت", "vi": "Qua Đêm" },
  "Meals": { "ar": "الوجبات", "vi": "Bữa Ăn" },
}
```

### Phương Án 2B: Chuyển Dictionary sang file JSON riêng *(Khuyến nghị dài hạn)*

**Cơ chế:** Tách `STATIC_DICTIONARY` ra file `locales/ar.json`, `locales/vi.json`. Backend load khi khởi động.

```python
# main.py
import json, pathlib
_locale_cache = {}
def load_locale(lang: str) -> dict:
    if lang not in _locale_cache:
        path = pathlib.Path(f"locales/{lang}.json")
        _locale_cache[lang] = json.loads(path.read_text()) if path.exists() else {}
    return _locale_cache[lang]

def translate_filter(text: str, lang: str = "en") -> str:
    if not lang or lang == "en":
        return text
    return load_locale(lang).get(text.strip(), text)
```

**Ưu điểm:** Translator/business có thể sửa file JSON mà không cần deploy code.

---

## RCA 3 — Backend Server-Side Generation

### Phương Án 3A: Thêm `lang` parameter vào mọi hàm sinh nội dung *(Khuyến nghị)*

**Day Titles — `get_luxury_day_title(city, lang)`:**

```python
# Thêm từ điển nội địa hóa tiêu đề ngày
_DAY_TITLE_TEMPLATES: dict[str, list[str]] = {
    "en": [
        "Behind Closed Doors: The {city} Chapter",
        "{city} Unveiled: A Private Insider Expedition",
        "The Living Heritage of {city}",
        # ...
    ],
    "ar": [
        "خلف الأبواب المغلقة: فصل {city}",
        "{city} المكشوفة: رحلة داخلية خاصة",
        "الإرث الحي لـ{city}",
        "منظور حصري: داخل {city}",
        "دروس {city} الراقية",
        # ...
    ],
    "vi": [
        "Bí Mật Bên Trong: Chương {city}",
        "Khám Phá {city}: Hành Trình Nội Bộ",
        # ...
    ]
}

def get_luxury_day_title(city: str, lang: str = "en") -> str:
    city_clean = city.strip().title()
    templates = _DAY_TITLE_TEMPLATES.get(lang, _DAY_TITLE_TEMPLATES["en"])
    return random.choice(templates).format(city=city_clean)
```

**Exclusions — `DEFAULT_EXCLUSIONS[lang]`:**

```python
DEFAULT_EXCLUSIONS: dict[str, list[str]] = {
    "en": [
        "International flights",
        "Vietnam visa and visa processing fees",
        "Travel insurance",
        "Personal expenses, laundry, beverages and tips",
        "Optional activities not mentioned in the program",
    ],
    "ar": [
        "رسوم التأشيرة الدولية ومعالجة طلبات الفيزا",
        "تذاكر الطيران الدولية",
        "التأمين على السفر",
        "النفقات الشخصية والغسيل والمشروبات والإكراميات",
        "الأنشطة الاختيارية غير المذكورة في البرنامج",
    ],
    "vi": [
        "Vé máy bay quốc tế",
        "Phí visa Việt Nam và phí xử lý visa",
        "Bảo hiểm du lịch",
        "Chi phí cá nhân, giặt ủi, đồ uống và tiền boa",
        "Các hoạt động tùy chọn không đề cập trong chương trình",
    ]
}

# Trong _build_ctx():
exc_lines = payload.bookingTerms.exclusions or DEFAULT_EXCLUSIONS.get(lang, DEFAULT_EXCLUSIONS["en"])
```

**Hotel Introductions — `_HOTEL_INTROS[hotel_name][lang]`:**

```python
_HOTEL_INTROS: dict[str, dict[str, str]] = {
    "Minasi Premium Hotel": {
        "en": "Minasi Premium Hotel is a boutique luxury hotel nestled in Hanoi's historic quarters...",
        "ar": "فندق ميناسي بريميوم هو فندق بوتيك فاخر يقع في الأحياء التاريخية لهانوي...",
        "vi": "Minasi Premium Hotel là khách sạn boutique sang trọng nằm trong khu phố cổ Hà Nội..."
    },
    "La Casta Cruise": {
        "en": "La Casta Cruise is a luxury 5-star cruise on Halong Bay...",
        "ar": "لا كاستا كروز هي رحلة بحرية فاخرة من فئة 5 نجوم على خليج هالونج...",
    },
    # ... các khách sạn khác
}
```

### Phương Án 3B: Dùng LLM để tự động dịch nội dung động lần đầu & cache

**Cơ chế:** Khi sinh nội dung lần đầu bằng tiếng Anh (day title, hotel intro), gọi LLM để dịch sang `lang` và lưu cache. Các lần sau chỉ cần đọc cache.

```python
async def get_day_title_localized(city: str, lang: str) -> str:
    cache_key = f"day_title:{city}:{lang}"
    if cached := redis_cache.get(cache_key):
        return cached
    en_title = get_luxury_day_title(city, "en")
    if lang == "en":
        return en_title
    # Gọi LLM để dịch sang lang
    translated = await translate_via_llm(en_title, target_lang=lang)
    redis_cache.set(cache_key, translated, ttl=86400)
    return translated
```

**Ưu điểm:** Không cần duy trì từ điển thủ công, chất lượng cao.
**Nhược điểm:** Phụ thuộc vào API LLM, tốn chi phí, cần Redis.

> [!TIP]
> **Phương án 3A là đủ cho thời điểm hiện tại.** Phương án 3B phù hợp khi scale ra 10+ ngôn ngữ.

---

## RCA 4 — Mở Rộng API Payload Schema

### Phương Án 4A: Thêm trường override vào `TourQuotationPayload` *(Khuyến nghị)*

**Cơ chế:** Cho phép Client truyền lên bản dịch sẵn, backend ưu tiên dùng dữ liệu Client truyền lên thay vì tự sinh.

```python
# quotation_schemas.py
class HotelItem(BaseModel):
    destination: str
    checkInDate: str
    checkOutDate: str
    hotelArrangement: str
    # ✅ THÊM MỚI
    hotelName: Optional[str] = None          # Tên khách sạn (nếu muốn override)
    hotelIntroduction: Optional[str] = None   # Mô tả khách sạn theo ngôn ngữ
    cityCountry: Optional[str] = None         # Ví dụ: "دبي، الإمارات"

class BookingTerms(BaseModel):
    deposit: str
    balance: str
    cancellation: str
    confirmation: str
    # ✅ THÊM MỚI
    exclusions: Optional[list[str]] = None    # Client override danh sách loại trừ

class LandingpageContent(BaseModel):
    # ... existing fields ...
    # ✅ THÊM MỚI
    muslimCareText: Optional[str] = None      # Mô tả Muslim Care theo ngôn ngữ
    specialistQuote: Optional[str] = None     # Lời chào của Travel Specialist
    roomNotes: Optional[str] = None           # Ghi chú phòng theo ngôn ngữ
```

**Áp dụng trong `_build_ctx()`:**

```python
# Ưu tiên dữ liệu từ Client, fallback về default
exc_lines = (
    payload.bookingTerms.exclusions
    or DEFAULT_EXCLUSIONS.get(lang, DEFAULT_EXCLUSIONS["en"])
)

# Hotel introduction
for hotel in payload.hotelPlan.hotels:
    intro = (
        hotel.hotelIntroduction
        or _HOTEL_INTROS.get(hotel.hotelName or "", {}).get(lang)
        or _HOTEL_INTROS.get(hotel.hotelName or "", {}).get("en", "")
    )
```

**Áp dụng trong trigger script `generate_21d20n_arabic_quotation.py`:**

```python
"bookingTerms": {
    "deposit": "شروط الدفع: دفع 30% ...",
    "balance": "يتم سداد المبلغ المتبقي...",
    "cancellation": "سياسة الإلغاء...",
    "confirmation": "تخضع جميع الخدمات...",
    # ✅ Override exclusions bằng tiếng Ả Rập
    "exclusions": [
        "تذاكر الطيران الدولية",
        "رسوم التأشيرة الدولية ومعالجة طلبات الفيزا",
        "التأمين على السفر",
        "النفقات الشخصية والغسيل والمشروبات والإكراميات",
        "الأنشطة الاختيارية غير المذكورة في البرنامج",
    ]
},
"hotelPlan": {
    "hotels": [
        {
            "destination": "Hanoi",
            "hotelArrangement": "Minasi Premium Hotel - 3 Nights",
            # ✅ Override mô tả bằng tiếng Ả Rập
            "hotelIntroduction": "فندق ميناسي بريميوم هو فندق بوتيك فاخر يقع في الأحياء التاريخية لهانوي...",
            "cityCountry": "هانوي، فيتنام",
            "checkInDate": "2026-08-10",
            "checkOutDate": "2026-08-13"
        },
        # ...
    ]
}
```

---

## Lộ Trình Thực Hiện Đề Xuất

| Pha | Việc Cần Làm | RCA Giải Quyết | Thời Gian Ước Tính |
|-----|-------------|----------------|---------------------|
| **P1 - Nhanh nhất** | Mở rộng `STATIC_DICTIONARY` + Wrap `\| translate(lang)` trong template | RCA 1, RCA 2 | 2-3 giờ |
| **P2 - Core** | Thêm `exclusions` & `hotelIntroduction` override vào Schema + `_build_ctx()` | RCA 4 + RCA 3 (một phần) | 2-3 giờ |
| **P3 - Hoàn thiện** | Đa ngôn ngữ hóa Day Titles + Hotel Intros theo từ điển nội địa | RCA 3 (hoàn toàn) | 3-4 giờ |
| **P4 - Nút chuyển ngôn ngữ** | `data-i18n` + `/assets/i18n/ar.json` + JS switcher không reload | RCA 1 (dynamic) | 2-3 giờ |

> [!WARNING]
> **P4 là điều kiện bắt buộc để nút chuyển ngôn ngữ hoạt động không reload trang.** P1-P3 chỉ giải quyết phía server render khi render lần đầu theo lang param, KHÔNG cho phép switch ngôn ngữ client-side.

---

## Kiến Trúc Hệ Thống Tổng Hợp Đề Xuất

```
Client clicks "Switch to Arabic"
         │
         ▼
[JS i18n Switcher]
  ├── fetch /assets/i18n/ar.json    (RCA 1 + 2 — static labels)
  ├── swap data-i18n DOM nodes      (RCA 1 — template strings)
  ├── set dir="rtl" lang="ar"       (RTL layout)
  └── [if dynamic content needed]
       └── fetch /quotations/{id}?lang=ar  → server re-renders full page

[Server render with lang=ar]
  ├── Template: {{ "..." | translate(lang) }}  (RCA 1 + 2)
  ├── _build_ctx(lang="ar")
  │     ├── exc_lines = payload.exclusions OR DEFAULT_EXCLUSIONS["ar"]  (RCA 4 + 3)
  │     ├── hotel.intro = payload.hotelIntro OR _HOTEL_INTROS[name]["ar"]  (RCA 4 + 3)
  │     └── day.title = get_luxury_day_title(city, lang="ar")  (RCA 3)
  └── render → return HTML with dir="rtl"
```
