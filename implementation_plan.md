# Implementation Plan: Full Multi-Language Support

## Phân Tích Nhanh Kiến Trúc Hiện Tại

> [!NOTE]
> `switchLanguage()` trong template **đang full-page reload** (redirect `?lang=ar`).
> Đây là kiến trúc đúng — không cần thêm client-side JS switcher.
> **Toàn bộ fix tập trung vào server-side render.** Khi user click chuyển ngôn ngữ, server render lại toàn trang với `lang=ar` → mọi text phải đúng tại thời điểm render.

---

## Phạm Vi Thay Đổi

| File | Loại thay đổi |
|------|--------------|
| `main.py` | MODIFY — Mở rộng `STATIC_DICTIONARY`, refactor `get_luxury_day_title()`, `get_luxury_hotel_details()`, `_build_ctx()` |
| `templates/vietnam_heritage_luxury.html` | MODIFY — Wrap hardcoded strings bằng `| translate(lang)` |
| `quotation_schemas.py` | MODIFY — Thêm optional fields vào `HotelItem`, `BookingTerms` |
| `generate_21d20n_arabic_quotation.py` | MODIFY — Bổ sung `exclusions` và `hotelIntroduction` tiếng Ả Rập |

---

## Task 1 — Mở rộng `STATIC_DICTIONARY` trong `main.py`

**File:** [`main.py`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/main.py) ~ line 60

**Hiện trạng:** Dictionary chỉ có ~15 keys cho template cũ.
**Mục tiêu:** Thêm ~40 keys mới cho tất cả label tĩnh trong `vietnam_heritage_luxury.html`.

**Keys cần thêm:**

```python
# ── Hero Section ───────────────────────────────────────────
"View Luxury Rates":        {"ar": "عرض الأسعار الفاخرة",       "vi": "Xem Bảng Giá Sang Trọng"},
"Explore the Journey":      {"ar": "استكشف الرحلة",              "vi": "Khám Phá Hành Trình"},
"Journey Overview":         {"ar": "نظرة عامة على الرحلة",       "vi": "Tổng Quan Hành Trình"},
"Prepared for":             {"ar": "مُعَدٌّ لـ",                  "vi": "Chuẩn Bị Cho"},
"Overview":                 {"ar": "نظرة عامة",                   "vi": "Tổng Quan"},
"Guests":                   {"ar": "الضيوف",                      "vi": "Khách"},
"Travel dates":             {"ar": "تواريخ السفر",                "vi": "Ngày Đi"},
"Route":                    {"ar": "المسار",                      "vi": "Tuyến Đường"},
"Style":                    {"ar": "النمط",                       "vi": "Phong Cách"},
"Ref.":                     {"ar": "رقم المرجع",                  "vi": "Mã Tham Chiếu"},
"Contact":                  {"ar": "التواصل",                     "vi": "Liên Hệ"},

# ── Route Map Section ──────────────────────────────────────
"Your Journey, Mapped":     {"ar": "مسار رحلتك على الخريطة",     "vi": "Hành Trình Trên Bản Đồ"},
"An interactive map...":    {"ar": "خريطة تفاعلية تُظهر مسارك المنسق...", "vi": "Bản đồ tương tác..."},
"Loading Interactive Route Map...": {"ar": "جارٍ تحميل خريطة المسار...", "vi": "Đang tải bản đồ..."},

# ── Why Works Section ──────────────────────────────────────
"Private & Flexible":       {"ar": "خاص ومرن",                   "vi": "Riêng Tư & Linh Hoạt"},
"Comfort & Pacing":         {"ar": "الراحة والوتيرة",             "vi": "Tiện Nghi & Nhịp Độ"},
"Muslim-Friendly Care":     {"ar": "الرعاية الصديقة للمسلمين",    "vi": "Thân Thiện Hồi Giáo"},
"Balanced Design":          {"ar": "التصميم المتوازن",             "vi": "Thiết Kế Cân Bằng"},

# ── Itinerary Section ──────────────────────────────────────
"DAY":                      {"ar": "اليوم",                       "vi": "NGÀY"},
"Highlights:":              {"ar": "أبرز الفعاليات:",              "vi": "Điểm Nổi Bật:"},
"Notes:":                   {"ar": "ملاحظات:",                    "vi": "Ghi Chú:"},
"Overnight":                {"ar": "المبيت",                      "vi": "Qua Đêm"},
"Meals":                    {"ar": "الوجبات",                     "vi": "Bữa Ăn"},

# ── Hotel Plan Section ─────────────────────────────────────
"Selected Hotel Plan":      {"ar": "خطة الفنادق المختارة",        "vi": "Kế Hoạch Khách Sạn"},
"Proposed hotels and luxury cruises selected for your journey. Subject to availability at confirmation.":
    {"ar": "الفنادق والرحلات البحرية الفاخرة المختارة لرحلتك. تخضع للتوافر عند التأكيد.",
     "vi": "Các khách sạn và du thuyền sang trọng được tuyển chọn cho hành trình của bạn."},
"Room\n            Notes & Special Requests":
    {"ar": "ملاحظات الغرفة والطلبات الخاصة",    "vi": "Ghi Chú Phòng & Yêu Cầu Đặc Biệt"},
"TEL:":                     {"ar": "هاتف:",                       "vi": "ĐT:"},

# ── Pricing Section ────────────────────────────────────────
"per person":               {"ar": "للشخص الواحد",               "vi": "mỗi người"},
"total package":            {"ar": "إجمالي الباقة",               "vi": "tổng gói"},
"Per person:":              {"ar": "للشخص الواحد:",               "vi": "Mỗi người:"},
"Total:":                   {"ar": "الإجمالي:",                   "vi": "Tổng:"},
"Important Note":           {"ar": "ملاحظة مهمة",                 "vi": "Lưu Ý Quan Trọng"},
"✓ CONFIRMED\n                MAIN OPTION":
    {"ar": "✓ الخيار الرئيسي المؤكد",           "vi": "✓ LỰA CHỌN ĐÃ XÁC NHẬN"},
"ALTERNATIVE OPTION":       {"ar": "خيار بديل",                   "vi": "LỰA CHỌN THAY THẾ"},

# ── Inclusions/Exclusions Section ─────────────────────────
"What Your Journey Includes": {"ar": "ما يشمله برنامج رحلتك",    "vi": "Những Gì Hành Trình Bao Gồm"},
"Inclusions":               {"ar": "ما يشمله البرنامج",           "vi": "Dịch Vụ Bao Gồm"},
"Exclusions":               {"ar": "ما لا يشمله البرنامج",        "vi": "Dịch Vụ Không Bao Gồm"},

# ── Muslim-Friendly Section ────────────────────────────────
"Muslim-Friendly Travel Care": {"ar": "الرعاية الصديقة للمسلمين", "vi": "Dịch Vụ Thân Thiện Với Người Hồi Giáo"},
"Carefully coordinated services ensuring comfort, halal-friendly\n            meals, and prayer mindfulness.":
    {"ar": "خدمات منسقة بعناية لضمان الراحة ووجبات حلال ومراعاة أوقات الصلاة.",
     "vi": "Dịch vụ phối hợp cẩn thận để đảm bảo tiện nghi, bữa ăn Halal và giờ cầu nguyện."},

# ── Payment Terms Section ──────────────────────────────────
"Booking & Payment Terms":  {"ar": "شروط الحجز والدفع",           "vi": "Điều Khoản Đặt Chỗ & Thanh Toán"},
"Commercial conditions, deposits, and cancellation policy for this\n            booking.":
    {"ar": "الشروط التجارية والودائع وسياسة الإلغاء لهذا الحجز.",
     "vi": "Điều kiện thương mại, đặt cọc và chính sách hủy cho đặt chỗ này."},
"Term":                     {"ar": "البند",                       "vi": "Điều Khoản"},
"Condition":                {"ar": "الشرط",                       "vi": "Điều Kiện"},
"Deposit":                  {"ar": "الدفعة المقدمة",               "vi": "Đặt Cọc"},
"Balance":                  {"ar": "المبلغ المتبقي",               "vi": "Số Dư"},
"Cancellation":             {"ar": "الإلغاء",                     "vi": "Hủy Bỏ"},
"Confirmation":             {"ar": "التأكيد",                     "vi": "Xác Nhận"},

# ── Meet Specialist Section ────────────────────────────────
"Your Dedicated Specialist": {"ar": "مستشارك المتخصص",           "vi": "Chuyên Viên Riêng Của Bạn"},
"Meet Your Travel Specialist": {"ar": "تعرّف على مصمم رحلتك",     "vi": "Gặp Gỡ Chuyên Gia Hành Trình"},
"Expertise:":               {"ar": "التخصص:",                     "vi": "Chuyên Môn:"},
"Experience:":              {"ar": "الخبرة:",                     "vi": "Kinh Nghiệm:"},
"Your Travel Specialist":   {"ar": "مصمم رحلتك",                  "vi": "Chuyên Gia Hành Trình"},

# ── Contact / CTA Section ──────────────────────────────────
"Next step":                {"ar": "الخطوة التالية",              "vi": "Bước Tiếp Theo"},
"Final\n                   Details Required":
    {"ar": "التفاصيل النهائية المطلوبة",          "vi": "Thông Tin Cần Thiết"},
"After\n                   Confirmation":
    {"ar": "بعد التأكيد",                          "vi": "Sau Khi Xác Nhận"},
"Website":                  {"ar": "الموقع الإلكتروني",           "vi": "Website"},
"WhatsApp":                 {"ar": "واتساب",                      "vi": "WhatsApp"},
"Prepared by":              {"ar": "أُعدَّ بواسطة",               "vi": "Được Chuẩn Bị Bởi"},
"Request final confirmation": {"ar": "طلب التأكيد النهائي",       "vi": "Yêu Cầu Xác Nhận Cuối"},
```

---

## Task 2 — Wrap Hardcoded Strings trong Template

**File:** [`templates/vietnam_heritage_luxury.html`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/templates/vietnam_heritage_luxury.html)

Danh sách các vị trí cần thay đổi (theo thứ tự xuất hiện trong file):

| Line | Before | After |
|------|--------|-------|
| 1702 | `View Luxury Rates` | `{{ "View Luxury Rates" \| translate(lang) }}` |
| 1703 | `Explore the Journey` | `{{ "Explore the Journey" \| translate(lang) }}` |
| 1707 | `Journey Overview` | `{{ "Journey Overview" \| translate(lang) }}` |
| 1709 | `Prepared for` | `{{ "Prepared for" \| translate(lang) }}` |
| 1711 | `Overview` | `{{ "Overview" \| translate(lang) }}` |
| 1713 | `Guests` | `{{ "Guests" \| translate(lang) }}` |
| 1716 | `Travel dates` | `{{ "Travel dates" \| translate(lang) }}` |
| 1719 | `Route` | `{{ "Route" \| translate(lang) }}` |
| 1722 | `Style` | `{{ "Style" \| translate(lang) }}` |
| 1724 | `Ref.` | `{{ "Ref." \| translate(lang) }}` |
| 1726 | `Contact` | `{{ "Contact" \| translate(lang) }}` |
| 1748 | `Your Journey, Mapped` | `{{ "Your Journey, Mapped" \| translate(lang) }}` |
| 1757 | `Loading Interactive Route Map...` | `{{ "Loading Interactive Route Map..." \| translate(lang) }}` |
| 1782 | `Private &amp; Flexible` | `{{ "Private & Flexible" \| translate(lang) }}` |
| 1789 | `Comfort &amp; Pacing` | `{{ "Comfort & Pacing" \| translate(lang) }}` |
| 1796 | `Muslim-Friendly Care` | `{{ "Muslim-Friendly Care" \| translate(lang) }}` |
| 2028 | `Room Notes & Special Requests` | `{{ "Room Notes & Special Requests" \| translate(lang) }}` |
| 2056 | `total package` | `{{ "total package" \| translate(lang) }}` |
| 2063 | `per person` | `{{ "per person" \| translate(lang) }}` |
| 2068 | `✓ CONFIRMED MAIN OPTION` | `{{ "✓ CONFIRMED\n                MAIN OPTION" \| translate(lang) }}` |
| 2073 | `ALTERNATIVE OPTION` | `{{ "ALTERNATIVE OPTION" \| translate(lang) }}` |
| 2080 | `Important Note` | `{{ "Important Note" \| translate(lang) }}` |
| 2091 | `What Your Journey Includes` | `{{ "What Your Journey Includes" \| translate(lang) }}` |
| 2095 | `Inclusions` | `{{ "Inclusions" \| translate(lang) }}` |
| 2103 | `Exclusions` | `{{ "Exclusions" \| translate(lang) }}` |
| 2121 | `Muslim-Friendly Travel Care` | `{{ "Muslim-Friendly Travel Care" \| translate(lang) }}` |
| 2122-2123 | `Carefully coordinated services...` | `{{ "Carefully coordinated services ensuring..." \| translate(lang) }}` |
| 2148 | `Booking &amp; Payment Terms` | `{{ "Booking & Payment Terms" \| translate(lang) }}` |
| 2149-2150 | `Commercial conditions...` | `{{ "Commercial conditions..." \| translate(lang) }}` |
| 2156 | `Term` | `{{ "Term" \| translate(lang) }}` |
| 2157 | `Condition` | `{{ "Condition" \| translate(lang) }}` |
| 2162 | `Deposit` | `{{ "Deposit" \| translate(lang) }}` |
| 2166 | `Balance` | `{{ "Balance" \| translate(lang) }}` |
| 2170 | `Cancellation` | `{{ "Cancellation" \| translate(lang) }}` |
| 2174 | `Confirmation` | `{{ "Confirmation" \| translate(lang) }}` |
| 2193 | `Your Dedicated Specialist` | `{{ "Your Dedicated Specialist" \| translate(lang) }}` |
| 2194 | `Meet Your Travel Specialist` | `{{ "Meet Your Travel Specialist" \| translate(lang) }}` |
| 2197 | `Expertise:` | `{{ "Expertise:" \| translate(lang) }}` |
| 2198 | `Experience:` | `{{ "Experience:" \| translate(lang) }}` |
| 2200 | `Your Travel Specialist` | `{{ "Your Travel Specialist" \| translate(lang) }}` |
| 2210 | `Next step` | `{{ "Next step" \| translate(lang) }}` |
| 2215 | `Final Details Required` | `{{ "Final\n                   Details Required" \| translate(lang) }}` |
| 2225 | `After Confirmation` | `{{ "After\n                   Confirmation" \| translate(lang) }}` |
| 2236 | `Website` | `{{ "Website" \| translate(lang) }}` |
| 2238 | `WhatsApp` | `{{ "WhatsApp" \| translate(lang) }}` |
| 2240 | `Prepared by` | `{{ "Prepared by" \| translate(lang) }}` |
| 2244 | `Request final confirmation` | `{{ "Request final confirmation" \| translate(lang) }}` |

> [!IMPORTANT]
> Các text có xuống dòng (`\n`) hoặc khoảng trắng nhiều trong HTML sẽ không khớp với key trong dictionary. **Giải pháp:** Chuẩn hóa lại tất cả key trong STATIC_DICTIONARY thành chuỗi không có newline, và sử dụng helper `text.strip()` đã có sẵn trong `translate_filter()`.

---

## Task 3 — Refactor `get_luxury_day_title()` thành locale-aware

**File:** [`main.py`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/main.py) ~ line 637

**Chiến lược:** Tạo `_DAY_TITLE_TEMPLATES` dict với 3 ngôn ngữ. Hàm nhận thêm `lang: str = "en"`.

```python
_DAY_TITLE_TEMPLATES: dict[str, list[str]] = {
    "en": [
        "Behind Closed Doors: The {city} Chapter",
        "{city} Unveiled: A Private Insider Expedition",
        "The Living Heritage of {city}",
        "Exclusive Perspectives: Inside {city}",
        "The Masterclasses of {city}",
        "The {city} Collection: A Curated Sojourn",
        "An Elegant Portrait of {city}",
        "The Anatomy of {city}: Culture & Contrast",
        "Vignettes of {city}",
        "Echoes of {city}",
        "The Soul and Substance of {city}",
        "Impressions of {city}: A Paced Exploration",
        "{city} Redefined: {element_a} & {element_b}",
        "From {landscape_a} to {landscape_b}: The {city} Landscape",
        "The Spirit of {city}: Between {concept_a} and {concept_b}",
    ],
    "ar": [
        "خلف الأبواب المغلقة: فصل {city}",
        "{city} المكشوفة: رحلة داخلية خاصة",
        "الإرث الحي في {city}",
        "منظور حصري: داخل {city}",
        "فنون {city} الراقية",
        "مجموعة {city}: إقامة منتقاة",
        "لوحة أنيقة من {city}",
        "تشريح {city}: الثقافة والتناقض",
        "لقطات من {city}",
        "أصداء {city}",
        "روح {city} وجوهرها",
        "انطباعات {city}: استكشاف مدروس",
        "{city} المُعاد تعريفها: {element_a} و{element_b}",
        "من {landscape_a} إلى {landscape_b}: مشهد {city}",
        "روح {city}: بين {concept_a} و{concept_b}",
    ],
    "vi": [
        "Bí Ẩn Bên Trong: Chương {city}",
        "Khám Phá {city}: Hành Trình Nội Bộ",
        "Di Sản Sống Động Của {city}",
        "Góc Nhìn Độc Quyền: Bên Trong {city}",
        "Tinh Hoa {city}",
        "Bộ Sưu Tập {city}: Kỳ Nghỉ Được Tuyển Chọn",
        "Chân Dung Thanh Lịch Về {city}",
        "Giải Phẫu {city}: Văn Hóa & Tương Phản",
        "Phác Họa {city}",
        "Tiếng Vọng Của {city}",
        "Linh Hồn Và Thực Chất Của {city}",
        "Ấn Tượng Về {city}: Khám Phá Ung Dung",
    ],
}

# Thêm _CITY_VARS_AR cho tiếng Ả Rập (tương tự _CITY_VARS đang có)
_CITY_VARS_AR: dict[str, dict] = {
    "hanoi": {
        "element_a": "الأناقة الفرنسية", "element_b": "أصداء الحي القديم",
        "landscape_a": "الشوارع المظللة", "landscape_b": "البحيرات الخلابة",
        "concept_a": "الإرث العريق", "concept_b": "الحداثة الراقية",
    },
    "sapa": {
        "element_a": "التراث القبلي", "element_b": "الضباب الجبلي",
        "landscape_a": "قمم المرتفعات", "landscape_b": "وديان المدرجات",
        "concept_a": "العزلة الجبلية", "concept_b": "التناقض الثقافي",
    },
    "da nang": {
        "element_a": "سحر الساحل", "element_b": "جبال الرخام",
        "landscape_a": "الشواطئ الرملية", "landscape_b": "الجسور الحديثة",
        "concept_a": "النبض الحضري", "concept_b": "العزلة البحرية",
    },
    "ho chi minh": {
        "element_a": "الموروث الاستعماري الفرنسي", "element_b": "خطوط ناطحات السحاب",
        "landscape_a": "الازدحام الحضري", "landscape_b": "مناظر الواجهة النهرية",
        "concept_a": "الروح التاريخية", "concept_b": "طاقة المستقبل",
    },
}

def get_luxury_day_title(city: str, lang: str = "en") -> str:
    """Generate a locale-aware premium day title for a given destination city."""
    if not city:
        _fallbacks = {"ar": "يوم من الاكتشافات المختارة", "vi": "Ngày Khám Phá Được Tuyển Chọn"}
        return _fallbacks.get(lang, "A Day of Curated Discoveries")
    
    city_clean = city.strip().replace("Explore ", "").replace("explore ", "")
    city_lower = city_clean.lower()
    city_title = city_clean.title()
    
    # Build city-specific vars
    vars = {...}  # giữ nguyên logic hiện tại cho 'en'
    
    templates = _DAY_TITLE_TEMPLATES.get(lang, _DAY_TITLE_TEMPLATES["en"])
    
    if lang == "ar":
        ar_vars = _CITY_VARS_AR.get(city_lower, {
            "element_a": "الفن", "element_b": "الثقافة",
            "landscape_a": "المناطق الطبيعية", "landscape_b": "المناطق الحضرية",
            "concept_a": "التراث", "concept_b": "التجديد",
        })
        return random.choice(templates).format(city=city_title, **ar_vars)
    
    return random.choice(templates).format(city=city_title, **vars)
```

**Cập nhật call site** tại line 1039 trong `main.py`:
```python
# Before
"title": truncate_text(get_luxury_day_title(d.destination), 80),
# After
"title": truncate_text(get_luxury_day_title(d.destination, lang=lang), 80),
```

---

## Task 4 — Locale-aware Exclusions trong `_build_ctx()`

**File:** [`main.py`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/main.py) ~ line 888

```python
# Thêm constant ở đầu file (trước _build_ctx)
DEFAULT_EXCLUSIONS: dict[str, list[str]] = {
    "en": [
        "International flights",
        "Vietnam visa and visa processing fees",
        "Travel insurance",
        "Personal expenses, laundry, beverages and tips",
        "Optional activities not mentioned in the program",
    ],
    "ar": [
        "تذاكر الطيران الدولية",
        "رسوم تأشيرة فيتنام ومعالجة الطلبات",
        "التأمين على السفر",
        "النفقات الشخصية والغسيل والمشروبات والإكراميات",
        "الأنشطة الاختيارية غير المذكورة في البرنامج",
    ],
    "vi": [
        "Vé máy bay quốc tế",
        "Phí visa Việt Nam và phí xử lý",
        "Bảo hiểm du lịch",
        "Chi phí cá nhân, giặt ủi, đồ uống và tiền boa",
        "Các hoạt động tùy chọn không đề cập trong chương trình",
    ],
}

# Trong _build_ctx(), thay thế exc_lines cứng:
# Before (line 888-894):
exc_lines = [
    "International flights",
    ...
]
# After:
exc_lines = (
    getattr(payload.bookingTerms, "exclusions", None)
    or DEFAULT_EXCLUSIONS.get(lang, DEFAULT_EXCLUSIONS["en"])
)
```

---

## Task 5 — Locale-aware Hotel Introductions trong `get_luxury_hotel_details()`

**File:** [`main.py`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/main.py) ~ line 528

**Chiến lược:** Thêm `lang` parameter và từ điển mô tả đa ngôn ngữ cho từng khách sạn được biết.

```python
_HOTEL_INTROS: dict[str, dict[str, str]] = {
    "Minasi Premium Hotel": {
        "en": "Minasi Premium Hotel is a boutique luxury hotel nestled in Hanoi's historic quarters, offering elegant design, personalized service, and modern comforts.",
        "ar": "فندق ميناسي بريميوم هو فندق بوتيك فاخر يقع في الأحياء التاريخية لهانوي، يقدم تصميماً أنيقاً وخدمة شخصية ووسائل راحة عصرية.",
        "vi": "Minasi Premium Hotel là khách sạn boutique sang trọng nằm trong khu phố cổ Hà Nội, cung cấp thiết kế thanh lịch, dịch vụ cá nhân và tiện nghi hiện đại.",
    },
    "La Casta Cruise": {
        "en": "La Casta Cruise is a luxury 5-star cruise on Halong Bay, offering spacious junior suites with private ocean-view balconies and high-class amenities.",
        "ar": "لا كاستا كروز هي رحلة بحرية فاخرة من فئة 5 نجوم على خليج هالونج، تقدم أجنحة جونيور واسعة مع شرفات خاصة مطلة على البحر وخدمات راقية.",
        "vi": "La Casta Cruise là du thuyền 5 sao sang trọng trên Vịnh Hạ Long, cung cấp các phòng junior suite rộng rãi với ban công hướng biển riêng tư và tiện nghi cao cấp.",
    },
    "Bora Hotel": {
        "en": "Bora Hotel in Sapa offers breathtaking mountain views and stylish, cozy accommodations for travelers exploring the beautiful northern highlands.",
        "ar": "يوفر فندق بورا في سابا إطلالات جبلية خلابة وإقامة أنيقة ودافئة للمسافرين الراغبين في استكشاف المرتفعات الشمالية الجميلة.",
        "vi": "Bora Hotel tại Sapa cung cấp tầm nhìn núi non tuyệt vời và chỗ ở phong cách ấm cúng cho du khách khám phá vùng cao nguyên phía Bắc tươi đẹp.",
    },
    "Minh Toan SAFI Ocean Hotel": {
        "en": "Minh Toan SAFI Ocean Hotel overlooks the stunning My Khe Beach in Da Nang, offering spacious ocean-view rooms and premium seaside hospitality.",
        "ar": "يطل فندق مين توان سافي أوشن على شاطئ ماي خي الرائع في دا نانغ، ويقدم غرفاً فسيحة مطلة على المحيط وضيافة ساحلية فاخرة.",
        "vi": "Minh Toan SAFI Ocean Hotel nhìn ra bãi biển Mỹ Khê tuyệt đẹp tại Đà Nẵng, cung cấp các phòng rộng rãi hướng biển và dịch vụ bên bờ biển cao cấp.",
    },
    "CICILIA Rouge Dalat": {
        "en": "CICILIA Rouge Dalat brings colonial vintage charm and sophisticated boutique luxury to the misty streets of Dalat.",
        "ar": "يجمع فندق سيسيليا روج دالات بين السحر الاستعماري الكلاسيكي والفخامة البوتيك الراقية في شوارع دالات الضبابية.",
        "vi": "CICILIA Rouge Dalat mang vẻ quyến rũ vintage thuộc địa và xa hoa boutique tinh tế đến những con phố sương mù của Đà Lạt.",
    },
    "Cicilia Saigon Center": {
        "en": "Cicilia Saigon Center offers elegant and contemporary accommodations in the heart of District 1, Ho Chi Minh City.",
        "ar": "يقدم فندق سيسيليا سايغون سنتر إقامة أنيقة ومعاصرة في قلب الحي الأول في مدينة هو تشي منه.",
        "vi": "Cicilia Saigon Center cung cấp chỗ ở thanh lịch và hiện đại tại trung tâm Quận 1, Thành phố Hồ Chí Minh.",
    },
}

def get_luxury_hotel_details(hotel_name: str, destination: str, lang: str = "en") -> dict:
    # ...existing logic...
    # Cuối hàm, khi trả về introduction, ưu tiên bản dịch:
    intro = (
        _HOTEL_INTROS.get(hotel_name, {}).get(lang)
        or _HOTEL_INTROS.get(hotel_name, {}).get("en")
        or existing_intro_logic  # giữ nguyên fallback hiện tại
    )
    result["introduction"] = intro
    return result
```

---

## Task 6 — Mở rộng Schema `quotation_schemas.py`

**File:** [`quotation_schemas.py`](file:///Users/nam/Workspace/projects/running/travel.ai/quotation-landingpage-template/quotation_schemas.py)

```python
class HotelItem(BaseModel):
    # ...existing fields...
    hotelIntroduction: Optional[str] = None  # ← THÊM MỚI: mô tả hotel theo lang
    cityCountry: Optional[str] = None        # ← THÊM MỚI: "هانوي، فيتنام"

class BookingTerms(BaseModel):
    # ...existing fields...
    exclusions: Optional[list[str]] = None   # ← THÊM MỚI: override danh sách loại trừ
```

**Áp dụng trong `_build_ctx()`:**
```python
# Hotel intro: Client override > locale dict > English fallback
for hotel in payload.hotelPlan.hotels:
    intro = hotel.hotelIntroduction or get_luxury_hotel_details(name, dest, lang)["introduction"]
    city_country = hotel.cityCountry or _build_city_country_label(dest, lang)
```

---

## Task 7 — Cập nhật `generate_21d20n_arabic_quotation.py`

Sau khi Schema mở rộng, bổ sung các trường mới vào payload tiếng Ả Rập:

```python
# Trong hotelPlan.hotels, mỗi entry thêm:
{
    "destination": "Hanoi",
    "hotelArrangement": "Minasi Premium Hotel - 3 Nights",
    "checkInDate": "2026-08-10",
    "checkOutDate": "2026-08-13",
    "hotelIntroduction": "فندق ميناسي بريميوم هو فندق بوتيك فاخر...",
    "cityCountry": "هانوي، فيتنام",
}

# bookingTerms thêm:
"exclusions": [
    "تذاكر الطيران الدولية",
    "رسوم تأشيرة فيتنام ومعالجة الطلبات",
    "التأمين على السفر",
    "النفقات الشخصية والغسيل والمشروبات والإكراميات",
    "الأنشطة الاختيارية غير المذكورة في البرنامج",
]
```

---

## Thứ Tự Thực Hiện & Task Checklist

```
[ ] Task 1 — Mở rộng STATIC_DICTIONARY trong main.py (~40 keys mới)
[ ] Task 2 — Wrap hardcoded strings trong template bằng | translate(lang) (~45 vị trí)
[ ] Task 3 — Refactor get_luxury_day_title() thêm lang param + AR/VI templates
[ ] Task 4 — Thêm DEFAULT_EXCLUSIONS dict + cập nhật _build_ctx() dùng nó
[ ] Task 5 — Thêm _HOTEL_INTROS dict + cập nhật get_luxury_hotel_details() thêm lang
[ ] Task 6 — Mở rộng Schema HotelItem và BookingTerms thêm optional fields
[ ] Task 7 — Cập nhật generate_21d20n_arabic_quotation.py với data mới
[ ] Task 8 — Chạy lại script, verify 100% text tiếng Ả Rập trên landing page
```

---

## Verification Plan

Sau khi implement xong, chạy lại `find_non_arabic.py` và kỳ vọng kết quả:

**Chấp nhận còn tiếng Anh** (tên riêng không dịch):
- Tên khách sạn: `Minasi Premium Hotel`, `La Casta Cruise`...
- Số điện thoại: `TEL: +84...`
- URL: `www.vietnamsafar.vn`
- Tên công ty: `Vietnam Safar`
- Số báo giá: `QT-2026-ARAB-21D20N`
- `DAY 1`, `DAY 2`... (số thứ tự)

**Phải là tiếng Ả Rập hoàn toàn:**
- Tất cả tiêu đề section
- Tiêu đề mỗi ngày lịch trình
- Mô tả khách sạn
- Inclusions & Exclusions
- Bảng điều khoản thanh toán
- Khu vực Contact/CTA
- Muslim-Friendly section
```
