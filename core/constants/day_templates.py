"""Luxury day title templates and title generation helpers."""

LUXURY_DAY_TEMPLATES = [
    {
        "en": "Behind Closed Doors: The {city} Chapter",
        "vi": "Đằng sau những cánh cửa: Chương {city}",
        "ar": "خلف الأبواب المغلقة: فصل {city}"
    },
    {
        "en": "{city} Unveiled: A Private Insider Expedition",
        "vi": "Hé lộ {city}: Hành trình khám phá riêng tư",
        "ar": "كشف أسرار {city}: رحلة استكشافية خاصة"
    },
    {
        "en": "The Living Heritage of {city}",
        "vi": "Di sản sống của {city}",
        "ar": "التراث الحي لـ {city}"
    },
    {
        "en": "Exclusive Perspectives: Inside {city}",
        "vi": "Góc nhìn độc bản: Bên trong {city}",
        "ar": "آفاق حصرية: داخل {city}"
    },
    {
        "en": "The Masterclasses of {city}",
        "vi": "Những lớp học bậc thầy tại {city}",
        "ar": "دروس احترافية في {city}"
    },
    {
        "en": "The {city} Collection: A Curated Sojourn",
        "vi": "Bộ sưu tập {city}: Kỳ nghỉ được chọn lọc",
        "ar": "مجموعة {city}: إقامة منسقة"
    },
    {
        "en": "An Elegant Portrait of {city}",
        "vi": "Chân dung thanh lịch của {city}",
        "ar": "صورة أنيقة لـ {city}"
    },
    {
        "en": "The Anatomy of {city}: Culture & Contrast",
        "vi": "Giải phẫu {city}: Văn hóa và Sự tương phản",
        "ar": "تفاصيل {city}: الثقافة والتناقض"
    },
    {
        "en": "A Design-Led Journey Through {city}",
        "vi": "Hành trình nghệ thuật qua {city}",
        "ar": "رحلة مستوحاة من التصميم عبر {city}"
    },
    {
        "en": "The {city} Dossier: A Tailored Agenda",
        "vi": "Hồ sơ {city}: Lịch trình thiết kế riêng",
        "ar": "ملف {city}: جدول أعمال مخصص"
    },
    {
        "en": "Vignettes of {city}",
        "vi": "Những mảnh ghép ký ức {city}",
        "ar": "لوحات قصيرة من {city}"
    },
    {
        "en": "{city} in Frames: A Visual Narrative",
        "vi": "Khung cảnh {city}: Tường thuật thị giác",
        "ar": "{city} في إطارات: سرد مرئي"
    },
    {
        "en": "Echoes of {city}",
        "vi": "Âm vang {city}",
        "ar": "أصداء {city}"
    },
    {
        "en": "The Soul and Substance of {city}",
        "vi": "Hồn cốt và Bản sắc của {city}",
        "ar": "روح وجوهر {city}"
    },
    {
        "en": "Impressions of {city}: A Paced Exploration",
        "vi": "Ấn tượng {city}: Khám phá thư thái",
        "ar": "انطباعات عن {city}: استكشاف متأنٍ"
    },
    {
        "en": "{city} Redefined: Tradition & Innovation",
        "vi": "Định nghĩa lại {city}: Truyền thống và Đổi mới",
        "ar": "إعادة تعريف {city}: بين الأصالة والتجديد"
    },
    {
        "en": "From Ancient Streets to Modern Beats: The {city} Landscape",
        "vi": "Từ phố cổ đến nhịp điệu hiện đại: Cảnh sắc {city}",
        "ar": "من الشوارع القديمة إلى الإيقاعات الحديثة: مشهد {city}"
    },
    {
        "en": "The Spirit of {city}: Between Silence and Splendor",
        "vi": "Tâm hồn {city}: Giữa tĩnh lặng và Huy hoàng",
        "ar": "روح {city}: بين السكون وال Huy hoàng"
    }
]


def get_luxury_day_title(city: str, day_number: int, lang: str) -> str:
    if not city:
        city = "Vietnam"
    tpl_idx = (day_number - 1) % len(LUXURY_DAY_TEMPLATES)
    tpl = LUXURY_DAY_TEMPLATES[tpl_idx]
    lang_key = lang if lang in ("en", "vi", "ar") else "en"
    raw_tpl = tpl.get(lang_key, tpl["en"])
    return raw_tpl.format(city=city)
