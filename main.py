import uuid
import json
import logging
import os
import asyncio
import copy
import re
from functools import partial
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from markupsafe import Markup, escape
from pydantic import BaseModel, ValidationError, Field
from typing import List, Optional
from datetime import date
from github_publish import publish_to_github, publish_file_to_github
from image_selector import select_landing_image
from destination_profiles import get_profile, get_layout_images_for_destination, get_available_images_for_destination, SOFT_TRANSITIONS

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("quotation")

app = FastAPI(title="Quotation Webhook API")

# CORS — required for ChatGPT Custom GPT Actions to reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
# Removed: app.mount("/published", StaticFiles(directory="published"), name="published")
# We now use a dynamic route below to handle /published to allow GitHub API fallback on Vercel

# Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Multi-brand configurations
BRANDS = {
    "vietnam_safar": {
        "id": "vietnam_safar",
        "name": "Vietnam Safar",
        "domain": "journeys.vietnamsafar.vn",
        "logo": "/assets/brands/vietnam_safar.png",
        "color_primary": "#17412e",
        "color_primary_dark": "#0e2f22",
        "color_accent": "#b7894b",
        "color_accent_light": "#d8bd85",
        "font_serif": "Cormorant Garamond",
        "font_sans": "Montserrat",
        "font_accent": "Allura"
    },
    "capella_travel": {
        "id": "capella_travel",
        "name": "Capella Travel",
        "domain": "journeys.capellatravel.com",
        "logo": "/assets/brands/capella_travel.png",
        "color_primary": "#CBA135",
        "color_primary_dark": "#B7894B",
        "color_accent": "#333333",
        "color_accent_light": "#4F4F4F",
        "font_serif": "Cormorant Garamond",
        "font_sans": "Montserrat",
        "font_accent": "Cormorant Garamond"
    },
    "selvara": {
        "id": "selvara",
        "name": "Selvara Journeys",
        "domain": "my.selvarajourneys.com",
        "logo": "/assets/brands/selvara.svg",
        "color_primary": "#A98338",
        "color_primary_dark": "#8C6A29",
        "color_accent": "#4F5D4E",
        "color_accent_light": "#6B7A6A",
        "font_serif": "Cormorant Garamond",
        "font_sans": "Jost",
        "font_accent": "Cormorant Garamond"
    }
}

def resolve_brand(request: Optional[Request], payload_dict: dict = None) -> dict:
    """Resolve brand based on query param, seller name, or content match."""
    brand_id = None
    if request is not None:
        try:
            brand_id = request.query_params.get("brand")
        except AttributeError:
            pass
    if brand_id and brand_id in BRANDS:
        return BRANDS[brand_id]
    
    if payload_dict:
        # Check seller companyName
        seller = payload_dict.get("seller") or {}
        comp_name = seller.get("companyName", "").lower() if isinstance(seller, dict) else ""
        if "capella" in comp_name:
            return BRANDS["capella_travel"]
        elif "selvara" in comp_name:
            return BRANDS["selvara"]
            
        # General string match fallback in payload representation
        try:
            payload_str = json.dumps(payload_dict).lower()
            if "capella" in payload_str:
                return BRANDS["capella_travel"]
            elif "selvara" in payload_str:
                return BRANDS["selvara"]
        except Exception:
            pass
            
    return BRANDS["vietnam_safar"]

# ── Luxury Day Title Templates ────────────────────────────────────────────────
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
        "ar": "روح {city}: بين السكون والجمال"
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

# Coordinates mapping for Vietnam travel destinations (matches Leaflet SLUG_COORDS)
SLUG_COORDS = {
    "ha-noi": [21.0285, 105.8542],
    "quang-ninh": [20.9599, 107.0436],
    "lao-cai": [22.3364, 103.8438],
    "da-nang": [16.0544, 108.2022],
    "quang-nam": [15.8801, 108.3380],
    "lam-dong": [11.9404, 108.4583],
    "ho-chi-minh": [10.8231, 106.6297],
    "khanh-hoa": [12.2388, 109.1967],
    "ninh-binh": [20.2539, 105.9750],
    "thua-thien-hue": [16.4637, 107.5909],
    "kien-giang": [10.2899, 103.9840],
    "binh-thuan": [10.9333, 108.1000],
    "can-tho": [10.0401, 105.7882],
    "mekong": [10.2435, 106.3756],
    "ha-giang": [22.8233, 104.9836],
    "nghe-an": [18.6736, 105.6811],
    "quang-binh": [17.4833, 106.6000],
    "hai-phong": [20.8449, 106.6881],
    "dak-lak": [12.6667, 108.0500],
    "gia-lai": [13.9833, 108.0000],
    "kon-tum": [14.3500, 108.0000],
    "ba-ria-vung-tau": [10.4114, 107.1363],
    "thanh-hoa": [19.8075, 105.7764],
    "phu-yen": [13.0881, 109.3025],
    "binh-dinh": [13.7753, 109.2294],
    "dien-bien": [21.3833, 103.0167],
    "son-la": [21.3333, 103.9167],
    "lai-chau": [22.4000, 103.4500],
    "yen-bai": [21.7000, 104.8667],
    "hoa-binh": [20.8167, 105.3333],
    "lang-son": [21.8500, 106.7500],
    "dong-nai": [10.9574, 106.8427],
    "binh-duong": [11.0000, 106.6667],
    "tien-giang": [10.3592, 106.3653],
    "dong-thap": [10.4500, 105.6333],
    "vinh-long": [10.2500, 105.9667],
    "an-giang": [10.3833, 105.4333],
    "cao-bang": [22.6667, 106.2500]
}

# ── Translation System ────────────────────────────────────────────────────────
STATIC_DICTIONARY = {
    "Timeline": {
        "vi": "Lịch Trình Chi Tiết",
        "ar": "الجدول الزمني"
    },
    "Vietnam Safar": {
        "vi": "Vietnam Safar — Đề Xuất Hành Trình",
        "ar": "Vietnam Safar — مقترح سفر"
    },
    "Journey Specifications": {
        "vi": "Thông Số Hành Trình",
        "ar": "مواصفات الرحلة"
    },
    "Core parameters of this B2B travel proposal.": {
        "vi": "Các thông số cơ bản của đề xuất hành trình này.",
        "ar": "المعايير الأساسية لمقترح السفر."
    },
    "Market & Nationality": {
        "vi": "Thị Trường & Quốc Tịch",
        "ar": "السوق والجنسية"
    },
    "Guest Profile": {
        "vi": "Thông Chi Tiết Thượng Khách",
        "ar": "ملف الضيوف"
    },
    "Hotel Standard": {
        "vi": "Tiêu Chuẩn Khách Sạn",
        "ar": "فئة الفندق"
    },
    "Meal Preference": {
        "vi": "Tùy Chọn Bữa Ăn",
        "ar": "تفضيلات الوجبات"
    },
    "Tour Type": {
        "vi": "Loại Hình Trải Nghiệm",
        "ar": "نوع الجولة"
    },
    "Route Sequence": {
        "vi": "Tuyến Đường Hành Trình",
        "ar": "تسلسل المسار"
    },
    "Section 1 — Journey at a Glance": {
        "vi": "Phần 1 — Khái Quát Hành Trình",
        "ar": "القسم 1 — لمحة سريعة عن الرحلة"
    },
    "Section 2 — Journey Overview": {
        "vi": "Phần 2 — Tổng Quan Kỳ Nghỉ",
        "ar": "القسم 2 — نظرة عامة على الرحلة"
    },
    "Section 3 — Your Journey, Mapped": {
        "vi": "Phần 3 — Hành Trình Trên Bản Đồ",
        "ar": "القسم 3 — مسار رحلتك على الخريطة"
    },
    "Section 6 — Selected Hotel Plan": {
        "vi": "Phần 6 — Kế Hoạch Khách Sạn",
        "ar": "القسم 6 — خطة الفنادق المختارة"
    },
    "Service Program": {
        "vi": "Chương Trình Trải Nghiệm",
        "ar": "برنامج الخدمة"
    },
    "B2B Package Pricing": {
        "vi": "Bảng Giá Chi Tiết",
        "ar": "أسعار الباقة"
    },
    "Package Inclusions & Exclusions": {
        "vi": "Danh Mục Dịch Vụ Bao Gồm & Loại Trừ",
        "ar": "الخدمات المشمولة والمستثناة من الباقة"
    },
    "Destination Gallery": {
        "vi": "Bộ Sưu Tập Hình Ảnh",
        "ar": "معرض الصور"
    },
    "Booking Terms": {
        "vi": "Điều Khoản Đặt Chỗ",
        "ar": "شروط الحجز"
    },
    "Finalization Checklist": {
        "vi": "Thông Tin Xác Nhận",
        "ar": "قائمة التحقق النهائية"
    },
    "Best for": {
        "vi": "Thành Viên",
        "ar": "مناسب لـ"
    },
    "Travel pace": {
        "vi": "Nhịp Độ",
        "ar": "وتيرة السفر"
    },
    "Service": {
        "vi": "Dịch Vụ",
        "ar": "الخدمة"
    },
    "B2B Partners": {
        "vi": "Đối Tác & Khách Hàng",
        "ar": "الشركاء والضيوف"
    },
    "Relaxed": {
        "vi": "Thư Thái",
        "ar": "مريح"
    },
    "Private": {
        "vi": "Riêng Tư",
        "ar": "خاص"
    },
    "Private Services": {
        "vi": "Dịch Vụ Riêng Tư",
        "ar": "خدمات خاصة"
    },
    "What is Included": {
        "vi": "Dịch Vụ Bao Gồm",
        "ar": "ما يشمله البرنامج"
    },
    "Detailed list of inclusions and exclusions for this proposal.": {
        "vi": "Danh sách chi tiết các dịch vụ bao gồm và không bao gồm của đề xuất này.",
        "ar": "قائمة مفصلة بالخدمات المشمولة والمستثناة من هذا المقترح."
    },
    "Halal & Prayer Coordination": {
        "vi": "Điều Phối Halal & Giờ Cầu Nguyện",
        "ar": "تنسيق الحلال والصلاة"
    },
    "This document is a confidential quotation prepared exclusively for": {
        "vi": "Tài liệu này là báo giá bảo mật được chuẩn bị cho",
        "ar": "هذا عرض سعر سري مخصص لـ"
    },
    "Confidential B2B": {
        "vi": "Báo Giá Bảo Mật",
        "ar": "عرض سعر سري"
    },
    "Confidential B2B Proposal": {
        "vi": "Đề Xuất Báo Giá Bảo Mật",
        "ar": "مقترح سفر سري"
    },
    "Vietnam Safar can assist with halal-friendly meal planning where available, no-pork meal notes, seafood or vegetarian alternatives where halal-certified restaurants are limited, and flexible prayer stops during touring days where practical. Halal-certified restaurants are more available in major cities such as Hanoi, Da Nang and Ho Chi Minh City. In mountain, cruise or countryside destinations, suitable seafood, vegetarian or no-pork meals may be recommended.": {
        "vi": "Vietnam Safar có thể hỗ trợ lên kế hoạch cho các bữa ăn thân thiện với người Hồi giáo khi có sẵn, lưu ý không thịt lợn, các giải pháp thay thế bằng hải sản hoặc đồ chay tại những nơi hạn chế nhà hàng chứng nhận Halal, và các điểm dừng cầu nguyện linh hoạt trong những ngày tham quan khi thực tế cho phép. Các nhà hàng được chứng nhận Halal có sẵn nhiều hơn ở các thành phố lớn như Hà Nội, Đà Nẵng và Thành phố Hồ Chí Minh. Tại các điểm đến vùng núi, du thuyền hoặc vùng nông thôn, các bữa ăn hải sản, đồ chay hoặc không thịt lợn phù hợp có thể được khuyên dùng.",
        "ar": "يمكن لـ Vietnam Safar المساعدة في التخطيط لوجبات الطعام الصديقة للمسلمين عند توفرها، مع ملاحظة عدم تقديم لحم الخنزير، والبدائل من المأكولات البحرية أو النباتية عندما تكون المطاعم المعتمدة للحلال محدودة، وتنسيق محطات مرنة لأوقات الصلاة خلال أيام الجولات السياحية عندما يكون ذلك عملياً."
    },
    "Hotel arrangements will be tailored and detailed here for your specific travel dates.": {
        "vi": "Kế hoạch khách sạn sẽ được tùy chỉnh và chi tiết tại đây dựa trên ngày đi cụ thể của bạn.",
        "ar": "سيتم تصميم تفاصيل خطة الفنادق وتخصيصها هنا بناءً على تواريخ سفرك المحددة."
    },
    "Fully private tour with flexible pacing to suit your needs.": {
        "vi": "Hành trình hoàn toàn riêng tư với nhịp độ linh hoạt theo nhu cầu của bạn.",
        "ar": "جولة خاصة بالكامل مع وتيرة مرنة لتناسب احتياجاتك."
    },
    "Premium A/C vehicle transport and handpicked hotels.": {
        "vi": "Vận chuyển bằng xe máy lạnh cao cấp và các khách sạn được tuyển chọn kỹ lưỡng.",
        "ar": "وسائل نقل برية خاصة مكيفة وفنادق مختارة بعناية."
    },
    "Dietary requests, meal planning, and specific preferences are carefully coordinated.": {
        "vi": "Các yêu cầu về chế độ ăn uống, kế hoạch bữa ăn và sở thích đặc biệt đều được điều phối chu đáo.",
        "ar": "تنسيق متطلبات النظام الغذائي والوجبات والتفضيلات الخاصة بعناية."
    },
    "Optimized itinerary balancing iconic sites with leisure time.": {
        "vi": "Lộ trình tối ưu hóa giúp cân bằng giữa các điểm tham quan biểu tượng và thời gian nghỉ ngơi.",
        "ar": "مسار رحلة محسّن يوازن بين المعالم الشهيرة وأوقات الراحة."
    },
    "As per standard booking policy.": {
        "vi": "Theo chính sách đặt chỗ tiêu chuẩn.",
        "ar": "وفقًا لسياسة الحجز القياسية."
    },
    "Payable prior to tour commencement.": {
        "vi": "Thanh toán trước khi hành trình bắt đầu.",
        "ar": "مستحق الدفع trước khi بدء الرحلة."
    },
    "Subject to cancellation charges as per terms.": {
        "vi": "Áp dụng phí hủy theo các điều khoản quy định.",
        "ar": "تخضع لرسوم الإلغاء وفقًا للشروط."
    },
    "Subject to availability upon payment.": {
        "vi": "Tùy thuộc vào tình trạng phòng trống tại thời điểm thanh toán.",
        "ar": "خاضع للتوافر عند الدفع."
    },
    "Passport copies and flight details required for booking.": {
        "vi": "Yêu cầu cung cấp bản sao hộ chiếu và thông tin chuyến bay để đặt dịch vụ.",
        "ar": "مطلوب نسخ من جواز السفر وتفاصيل الرحلة للحجز."
    },
    "Our operations team will coordinate vouchers and guide details.": {
        "vi": "Đội ngũ vận hành của chúng tôi sẽ điều phối voucher và thông tin hướng dẫn viên.",
        "ar": "سيعمل فريق العمليات لدينا على تنسيق القسائم وتفاصيل المرشد."
    },
    "5-star (Luxury)": {
        "vi": "5 sao (Sang trọng)",
        "ar": "5 نجوم (فاخر)"
    },
    "Twin/Double Sharing Basis": {
        "vi": "Cơ sở chia sẻ phòng đôi/hai giường",
        "ar": "على أساس المشاركة المزدوجة/التوأم"
    },
    "Subject to availability and confirmation": {
        "vi": "Tùy thuộc vào tình trạng sẵn có và xác nhận",
        "ar": "خاضع للتوافر والتأكيد"
    },
    "Not Included": {
        "vi": "Không bao gồm",
        "ar": "غير مشمول"
    },
    "Included": {
        "vi": "Được bao gồm",
        "ar": "مشمول"
    },
    "Twin-sharing basis": {
        "vi": "Cơ sở chia sẻ phòng đôi/hai giường",
        "ar": "على أساس المشاركة المزدوجة/التوأم"
    },
    "Balanced Highlights": {
        "vi": "Điểm Nhấn Cân Bằng",
        "ar": "أبرز الفعاليات المتوازنة"
    },
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
    "Your Travel Specialist": {
        "ar": "Anh Son Le",
        "vi": "Le",
        "en": "Anh Son Le"
    },
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

    # Inclusions, Exclusions new structured formats
    "What Your Journey Includes": {
        "vi": "Những Gì Hành Trình Bao Gồm",
        "ar": "ما تشمله برنامج رحلتك"
    },
    "Your journey has been thoughtfully arranged to ensure a seamless and comfortable experience throughout.": {
        "vi": "Hành trình của bạn đã được sắp xếp chu đáo để đảm bảo trải nghiệm suôn sẻ và thoải mái trong suốt chuyến đi.",
        "ar": "لقد تم ترتيب رحلتك بعناية لضمان تجربة سلسة ومريحة طوال الوقت."
    },
    "Handpicked Accommodation": {
        "vi": "Khách Sạn Được Lựa Chọn Cẩn Thận",
        "ar": "إقامة مختارة بعناية"
    },
    "Carefully selected hotels and stays as detailed in your journey proposal.": {
        "vi": "Các khách sạn và nơi lưu trú được lựa chọn kỹ lưỡng như chi tiết trong đề xuất hành trình.",
        "ar": "فنادق وإقامات مختارة بعناية كما هو مفصل في مقترح رحلتك."
    },
    "Private Transportation": {
        "vi": "Phương Tiện Vận Chuyển Riêng Tư",
        "ar": "وسائل نقل خاصة"
    },
    "Private ground transportation and scheduled transfers throughout the journey, as specified in the itinerary.": {
        "vi": "Phương tiện vận chuyển mặt đất riêng tư và đưa đón theo lịch trình suốt hành trình, như quy định trong lịch trình.",
        "ar": "وسائل نقل برية خاصة وتنقلات مجدولة طوال الرحلة، كما هو حدد في مسار الرحلة."
    },
    "Curated Experiences": {
        "vi": "Trải Nghiệm Được Thiết Kế Riêng",
        "ar": "تجارب منسقة"
    },
    "Entrance arrangements and experiences included as outlined in your itinerary.": {
        "vi": "Bố trí lối vào và các trải nghiệm được bao gồm như phác thảo trong lịch trình của bạn.",
        "ar": "رسوم الدخول والأنشطة المشمولة والموضحة في مسار رحلتك."
    },
    "Expert Local Guidance": {
        "vi": "Hướng Dẫn Viên Địa Phương Chuyên Nghiệp",
        "ar": "إرشاد محلي خبير"
    },
    "Services of carefully selected, licensed local guides where specified.": {
        "vi": "Dịch vụ của hướng dẫn viên địa phương có giấy phép được lựa chọn cẩn thận khi được chỉ định.",
        "ar": "خدمات مرشدين محليين مرخصين ومختارين بعناية عند تحديد ذلك."
    },
    "Dining Experiences": {
        "vi": "Trải Nghiệm Ẩm Thực",
        "ar": "تجارب تناول الطعام"
    },
    "Meals and dining arrangements as detailed in the itinerary.": {
        "vi": "Các bữa ăn và bố trí ăn uống như chi tiết trong lịch trình.",
        "ar": "الوجبات وترتيبات تناول الطعام كما هي مفصلة في مسار الرحلة."
    },
    "Journey Connections": {
        "vi": "Kết Nối Hành Trình",
        "ar": "روابط التنقل"
    },
    "Domestic flights, rail journeys, ferries, or other transportation included where specifically stated in the itinerary.": {
        "vi": "Các chuyến bay nội địa, hành trình đường sắt, phà hoặc phương tiện vận chuyển khác được bao gồm khi được ghi rõ trong lịch trình.",
        "ar": "رحلات الطيران الداخلية، أو السكك الحديدية، أو العبّارات، أو غيرها من وسائل النقل المشمولة عند ذكرها بوضوح في مسار الرحلة."
    },
    "What Your Journey Excludes": {
        "vi": "Những Gì Không Bao Gồm",
        "ar": "الخدمات غير المشمولة"
    },
    "To keep your journey transparent and clearly defined, the following are not included unless specifically stated otherwise:": {
        "vi": "Để giữ cho hành trình của bạn minh bạch và rõ ràng, các khoản sau đây không được bao gồm trừ khi có tuyên bố cụ thể khác:",
        "ar": "للحفاظ على شفافية ووضوح رحلتك، لا تشمل الرحلة الخدمات التالية ما لم يُنص على خلاف ذلك:"
    },
    "Visa fees and travel documentation": {
        "vi": "Lệ phí visa và giấy tờ du lịch",
        "ar": "رسوم التأشيرة ووثائق السفر"
    },
    "Personal expenses": {
        "vi": "Chi phí cá nhân",
        "ar": "المصاريف الشخصية"
    },
    "Optional experiences not specified in the itinerary": {
        "vi": "Các trải nghiệm tùy chọn không được chỉ định trong lịch trình",
        "ar": "التجارب الاختيارية غير المحددة في مسار الرحلة"
    },
    "Tips and gratuities": {
        "vi": "Tiền tips và tiền boa",
        "ar": "البقشيش والإكراميات"
    },
    "Any services not expressly listed as included": {
        "vi": "Bất kỳ dịch vụ nào không được liệt kê rõ ràng là bao gồm",
        "ar": "أي خدمات أخرى لم يتم ذكرها صراحة ضمن الخدمات المشمولة"
    },
    "Day-by-Day Journey Program": {
        "vi": "Chương Trình Hành Trình Chi Tiết",
        "ar": "برنامج الرحلة يومًا بيوم"
    },
    "Translating Journey...": {
        "vi": "Đang Dịch Hành Trình...",
        "ar": "جاري ترجمة الرحلة..."
    },
    "CANCEL": {
        "vi": "HỦY BỎ",
        "ar": "إلغاء"
    },
    # Inclusions & Exclusions & Conditions
    "Private air-conditioned transportation throughout": {
        "vi": "Phương tiện vận chuyển riêng tư có điều hòa suốt hành trình",
        "ar": "وسائل نقل خاصة مكيفة طوال الرحلة"
    },
    "Accommodation with daily breakfast": {
        "vi": "Lưu trú kèm bữa ăn sáng hàng ngày",
        "ar": "الإقامة مع وجبة إفطار يومية"
    },
    "Meals as mentioned in the program": {
        "vi": "Các bữa ăn theo chương trình",
        "ar": "الوجبات كما هي مذكورة في البرنامج"
    },
    "All sightseeing entrance fees as mentioned": {
        "vi": "Toàn bộ vé tham quan các điểm theo chương trình",
        "ar": "جميع رسوم دخول المعالم السياحية المذكورة"
    },
    "English-speaking local guide": {
        "vi": "Hướng dẫn viên bản địa nói tiếng Anh",
        "ar": "مرشد محلي يتحدث الإنجليزية"
    },
    "International flights": {
        "vi": "Vé máy bay quốc tế",
        "ar": "رحلات الطيران الدولية"
    },
    "Vietnam visa and visa processing fees": {
        "vi": "Lệ phí cấp và xử lý visa Việt Nam",
        "ar": "تأشيرة فيتنام ورسوم معالجة التأشيرة"
    },
    "Travel insurance": {
        "vi": "Bảo hiểm du lịch",
        "ar": "التأمين على السفر"
    },
    "Personal expenses, laundry, beverages and tips": {
        "vi": "Chi phí cá nhân, giặt ủi, đồ uống và tiền tip",
        "ar": "المصاريف الشخصية والغسيل والمشروبات والإكراميات"
    },
    "Optional activities not mentioned in the program": {
        "vi": "Các hoạt động tùy chọn ngoài chương trình",
        "ar": "الأنشطة الاختيارية غير المذكورة في البرنامج"
    },
    "Rates are B2B net indicative and subject to reconfirmation at the time of booking.": {
        "vi": "Giá đề xuất mang tính chất tham khảo và sẽ được xác nhận lại khi đặt dịch vụ.",
        "ar": "الأسعار التقديرية وتخضع لإعادة التأكيد عند الحجز."
    },
    "Final price may vary depending on hotel availability, resort category, cruise selection, domestic flight fare, rooming arrangement, child policy, and final travel services confirmed.": {
        "vi": "Giá cuối cùng có thể thay đổi tùy thuộc vào tình trạng phòng khách sạn, hạng phòng, lựa chọn du thuyền, giá vé máy bay nội địa, cách sắp xếp phòng, chính sách trẻ em và các dịch vụ du lịch được xác nhận cuối cùng.",
        "ar": "قد يختلف السعر النهائي اعتمادًا على توفر الفنادق، فئة المنتجع، اختيار الكروز، أسعار الطيران الداخلي، ترتيبات الغرف، سياسة الأطفال، والخدمات المؤكدة نهائياً."
    },

    # Template static text & headings
    "Behind the Itinerary Curation": {
        "vi": "Hậu Trường Thiết Kế Hành Trình",
        "ar": "خلف كواليس تصميم المسار"
    },
    "Why This Journey Inspires": {
        "vi": "Tại Sao Hành Trình Này Đầy Cảm Hứng",
        "ar": "لماذا تلهم هذه الرحلة"
    },
    "The Anatomy of the Experience": {
        "vi": "Chi Tiết Trải Nghiệm",
        "ar": "تفاصيل التجربة"
    },
    "A Perfectly Paced Journey": {
        "vi": "Một Hành Trình Có Nhịp Độ Hoàn Hảo",
        "ar": "رحلة ذات وتيرة مثالية"
    },
    "Value Propositions": {
        "vi": "Giá Trị Cốt Lõi",
        "ar": "مزايا الرحلة"
    },
    "Tailored care, balanced pacing, and seamless logistics designed specifically for your group.": {
        "vi": "Dịch vụ được cá nhân hóa, nhịp độ cân bằng và hậu cần liền mạch được thiết kế riêng cho đoàn của bạn.",
        "ar": "رعاية مخصصة، وتيرة متوازنة، ولوجستيات سلسة مصممة خصيصًا لمجموعتكم."
    },
    "Muslim-Friendly Travel Care": {
        "vi": "Dịch Vụ Thân Thiện Với Người Hồi Giáo",
        "ar": "الرعاية الصديقة للمسلمين"
    },
    "Carefully coordinated services ensuring comfort, halal-friendly meals, and prayer mindfulness.": {
        "vi": "Các dịch vụ được điều phối cẩn thận đảm bảo sự thoải mái, bữa ăn thân thiện với người Hồi giáo và thời gian cầu nguyện thích hợp.",
        "ar": "خدمات منسقة بعناية تضمن الراحة، ووجبات صديقة للمسلمين، ومراعاة أوقات الصلاة."
    },
    "Crafting a bespoke luxury narrative in": {
        "vi": "Đang kiến tạo hành trình sang trọng độc bản tại",
        "ar": "جاري صياغة مسار رحلة فاخر مخصص في"
    },

    # PWA Notifications Prompt
    "Stay Updated": {
        "vi": "Cập Nhật Thông Tin",
        "ar": "ابق على اطلاع"
    },
    "Enable notifications to get live updates for your itinerary, guide details, and booking status.": {
        "vi": "Bật thông báo để nhận cập nhật trực tiếp về lịch trình, thông tin hướng dẫn viên và trạng thái đặt chỗ.",
        "ar": "قم بتمكين الإشعارات للحصول على تحديثات مباشرة لمسار رحلتك وتفاصيل المرشد وحالة الحجز."
    },
    "Later": {
        "vi": "Để sau",
        "ar": "لاحقاً"
    },
    "Enable": {
        "vi": "Bật",
        "ar": "تمكين"
    },
    "Notifications Active": {
        "vi": "Đã Bật Thông Báo",
        "ar": "الإشعارات نشطة"
    },
    "You'll receive live itinerary updates here.": {
        "vi": "Bạn sẽ nhận được cập nhật lịch trình trực tiếp tại đây.",
        "ar": "ستتلقى تحديثات مباشرة لمسار الرحلة هنا."
    },
    "Vịnh Hạ Long": {
        "en": "Halong Bay",
        "ar": "Halong Bay",
        "vi": "Vịnh Hạ Long"
    },
    "Hạ Long": {
        "en": "Halong",
        "ar": "Halong",
        "vi": "Hạ Long"
    },
    "Hà Nội": {
        "en": "Hanoi",
        "ar": "Hanoi",
        "vi": "Hà Nội"
    },
    "Đà Nẵng": {
        "en": "Da Nang",
        "ar": "Da Nang",
        "vi": "Đà Nẵng"
    },
    "Hội An": {
        "en": "Hoi An",
        "ar": "Hoi An",
        "vi": "Hội An"
    },
    "Hồ Chí Minh": {
        "en": "Ho Chi Minh City",
        "ar": "Ho Chi Minh City",
        "vi": "Hồ Chí Minh"
    },
    "Thành phố Hồ Chí Minh": {
        "en": "Ho Chi Minh City",
        "ar": "Ho Chi Minh City",
        "vi": "Thành phố Hồ Chí Minh"
    },
    "Sa Pa": {
        "en": "Sapa",
        "ar": "Sapa",
        "vi": "Sa Pa"
    },
    "Ninh Bình": {
        "en": "Ninh Binh",
        "ar": "Ninh Binh",
        "vi": "Ninh Bình"
    },
    "Đồng bằng sông Cửu Long": {
        "en": "Mekong Delta",
        "ar": "Mekong Delta",
        "vi": "Đồng bằng sông Cửu Long"
    },
    # Interactive Map Section
    "Your Journey, Mapped": {
        "ar": "رحلتك على الخريطة",
        "vi": "Hành Trình Của Bạn Trên Bản Đồ"
    },
    "An interactive map showing your curated path through Vietnam's iconic landmarks and luxury stopovers. Click on a destination in the list or the map to explore highlights.": {
        "ar": "خريطة تفاعلية تعرض مسارك المنسق عبر معالم فيتنام الشهيرة ومحطات التوقف الفاخرة. انقر على وجهة في القائمة أو الخريطة لاستكشاف المعالم البارزة.",
        "vi": "Bản đồ tương tác hiển thị lộ trình được thiết kế riêng của bạn qua các địa danh mang tính biểu tượng và điểm dừng chân sang trọng của Việt Nam. Nhấp vào một điểm đến trong danh sách hoặc bản đồ để khám phá các điểm nổi bật."
    },
    "Classic": {
        "ar": "كلاسيكي",
        "vi": "Bản đồ"
    },
    "Image": {
        "ar": "صورة",
        "vi": "Hình ảnh"
    },
    "Loading Interactive Route Map...": {
        "ar": "جاري تحميل الخريطة التفاعلية...",
        "vi": "Đang Tải Bản Đồ Lộ Trình Tương Tác..."
    },
    "Journey Overview": {
        "ar": "نظرة عامة على الرحلة",
        "vi": "Tổng Quan Hành Trình"
    },
    "Route Map": {
        "ar": "خريطة المسار",
        "vi": "Bản đồ lộ trình"
    },
    "Itinerary": {
        "ar": "برنامج الرحلة",
        "vi": "Lịch trình"
    },
    "Quotation": {
        "ar": "عرض السعر",
        "vi": "Báo giá"
    },
    "Terms": {
        "ar": "الشروط",
        "vi": "Điều khoản"
    },
    "PDF Preview": {
        "ar": "معاينة PDF",
        "vi": "Xem trước PDF"
    },
    "View Luxury Rates": {
        "ar": "عرض الأسعار الفاخرة",
        "vi": "Xem giá cao cấp"
    },
    "Explore the Journey": {
        "ar": "استكشف الرحلة",
        "vi": "Khám phá hành trình"
    },
    "Overview": {
        "ar": "نظرة عامة",
        "vi": "Tổng quan"
    },
    "Guests": {
        "ar": "الضيوف",
        "vi": "Khách"
    },
    "Travel dates": {
        "ar": "تواريخ السفر",
        "vi": "Ngày đi"
    },
    "Route": {
        "ar": "المسار",
        "vi": "Tuyến đường"
    },
    "Style": {
        "ar": "النمط",
        "vi": "Phong cách"
    },
    "Ref.": {
        "ar": "الرقم المرجعي",
        "vi": "Mã tham chiếu"
    },
    "Contact": {
        "ar": "التواصل",
        "vi": "Liên hệ"
    },
    "Interactive Route map": {
        "ar": "خريطة المسار التفاعلية",
        "vi": "Bản đồ lộ trình tương tác"
    },
    "Luxury Quotation": {
        "ar": "عرض سعر فاخر",
        "vi": "Báo giá cao cấp"
    },
    "B2B Travel Proposal": {
        "ar": "مقترح سفر",
        "vi": "Đề xuất du lịch"
    },
    "Confidential B2B Proposal": {
        "ar": "مقترح سفر سري",
        "vi": "Đề xuất báo giá bảo mật"
    },
    "Enable Notifications": {
        "ar": "تفعيل الإشعارات",
        "vi": "Bật thông báo"
    },
    "Previous image": {
        "ar": "الصورة السابقة",
        "vi": "Ảnh trước"
    },
    "Next image": {
        "ar": "الصورة التالية",
        "vi": "Ảnh tiếp theo"
    },
    "Go to slide": {
        "ar": "الانتقال إلى الشريحة",
        "vi": "Chuyển đến slide"
    },
    "Editing": {
        "ar": "قيد التحرير",
        "vi": "Đang chỉnh sửa"
    },
    "Publish to Web": {
        "ar": "نشر على الويب",
        "vi": "Xuất bản lên web"
    },
    "Publishing...": {
        "ar": "جارٍ النشر...",
        "vi": "Đang xuất bản..."
    },
    "Committing to GitHub...": {
        "ar": "جارٍ حفظ التغييرات على GitHub...",
        "vi": "Đang lưu lên GitHub..."
    },
    "Translate this block": {
        "ar": "ترجمة هذا المقطع",
        "vi": "Dịch đoạn này"
    },
    "Change": {
        "ar": "تغيير",
        "vi": "Đổi"
    },
    "Remove this block": {
        "ar": "إزالة هذا القسم",
        "vi": "Xóa khối này"
    },
    "Remove this block? This action cannot be undone.": {
        "ar": "هل تريد إزالة هذا القسم؟ لا يمكن التراجع عن هذا الإجراء.",
        "vi": "Xóa khối này? Hành động này không thể hoàn tác."
    },
    "Itinerary Update": {
        "ar": "تحديث برنامج الرحلة",
        "vi": "Cập nhật lịch trình"
    },
    "Your private guide has been assigned: Mr. Minh (Phone: +84 911 538 738).": {
        "ar": "تم تعيين مرشدك الخاص: Mr. Minh (Phone: +84 911 538 738).",
        "vi": "Hướng dẫn viên riêng của bạn đã được chỉ định: Mr. Minh (Phone: +84 911 538 738)."
    },
    "English": {
        "ar": "الإنجليزية",
        "vi": "Tiếng Anh"
    },
    "Arabic": {
        "ar": "العربية",
        "vi": "Tiếng Ả Rập"
    },
    "Vietnamese": {
        "ar": "الفيتنامية",
        "vi": "Tiếng Việt"
    },
    "TEL:": {
        "ar": "هاتف:",
        "vi": "ĐT:"
    },
    "Please enable notifications in your browser settings to receive updates.": {
        "ar": "يرجى تفعيل الإشعارات من إعدادات المتصفح لتلقي التحديثات.",
        "vi": "Vui lòng bật thông báo trong trình duyệt để nhận cập nhật."
    },

    # Value Propositions (Why it works)
    "Private & Flexible": {
        "ar": "خصوصية ومرونة",
        "vi": "Riêng Tư & Linh Hoạt"
    },
    "Comfort & Pacing": {
        "ar": "الراحة والوتيرة",
        "vi": "Thoải Mái & Nhịp Độ"
    },
    "Muslim-Friendly Care": {
        "ar": "الرعاية الصديقة للمسلمين",
        "vi": "Dịch Vụ Thân Thiện Với Người Hồi Giáo"
    },
    "Dietary & Special Care": {
        "ar": "الرعاية الغذائية والخاصة",
        "vi": "Chế Độ Ăn & Chăm Sóc Đặc Biệt"
    },
    "Balanced Highlights": {
        "ar": "أبرز الفعاليات المتوازنة",
        "vi": "Điểm Nhấn Cân Bằng"
    },

    # Destination Gallery Labels
    "The city collection": {
        "ar": "مجموعة المدينة",
        "vi": "Bộ sưu tập đô thị"
    },
    "Cinematic destination panels crafted for a premium travel proposal.": {
        "ar": "لوحات وجهة سينمائية تم إعدادها لمقترح سفر متميز.",
        "vi": "Hình ảnh điểm đến đậm chất điện ảnh được thiết kế cho đề xuất du lịch cao cấp."
    },
    "Destination imagery woven into the quotation.": {
        "ar": "صور الوجهات منسوجة بعناية داخل عرض السعر.",
        "vi": "Hình ảnh điểm đến được đan cài tinh tế trong báo giá."
    },
    "Destination Gallery": {
        "ar": "معرض الصور",
        "vi": "Bộ Sưu Tập Hình Ảnh"
    },
    "Highlight": {
        "ar": "أبرز المعالم",
        "vi": "Điểm Nổi Bật"
    },
    "Experience": {
        "ar": "التجربة",
        "vi": "Trải Nghiệm"
    },
    "Journey": {
        "ar": "الرحلة",
        "vi": "Hành Trình"
    },
    "Destination": {
        "ar": "الوجهة",
        "vi": "Điểm Đến"
    },

    # Day Pacing
    "Sense of Pace: Active": {
        "ar": "وتيرة السفر: نشطة",
        "vi": "Nhịp độ: Năng động"
    },
    "Sense of Pace: Moderate": {
        "ar": "وتيرة السفر: معتدلة",
        "vi": "Nhịp độ: Vừa phải"
    },
    "Minasi Premium Hotel is a boutique luxury hotel nestled in Hanoi's historic quarters, offering elegant design, personalized service, and modern comforts.": {
        "vi": "Minasi Premium Hotel là khách sạn boutique sang trọng tọa lạc tại khu phố cổ lịch sử của Hà Nội, mang đến thiết kế thanh lịch, dịch vụ cá nhân hóa và tiện nghi hiện đại.",
        "ar": "يُعد Minasi Premium Hotel فندقًا فاخرًا يقع في الأحياء التاريخية بمدينة Hanoi، ويتميز بتصميم أنيق وخدمة مخصصة ووسائل راحة حديثة."
    },
    "La Casta Cruise is a luxury 5-star cruise on Halong Bay, offering spacious junior suites with private ocean-view balconies and high-class amenities.": {
        "vi": "Du thuyền La Casta là du thuyền 5 sao sang trọng trên Vịnh Hạ Long, cung cấp các phòng suite rộng rãi với ban công riêng hướng biển và các tiện nghi cao cấp.",
        "ar": "يُعد La Casta Cruise كروزًا فاخرًا من فئة 5 نجوم في Halong Bay، ويوفر أجنحة Junior واسعة مع شرفات خاصة مطلة على البحر ووسائل راحة راقية."
    },
    "Bora Hotel in Sapa offers breathtaking mountain views and stylish, cozy accommodations for travelers exploring the beautiful northern highlands.": {
        "vi": "Bora Hotel tại Sapa mang đến tầm nhìn ra núi non ngoạn mục cùng không gian lưu trú phong cách, ấm cúng cho du khách khám phá vùng cao phía bắc xinh đẹp.",
        "ar": "يوفر Bora Hotel في Sapa إطلالات جبلية خلابة وأماكن إقامة أنيقة ومريحة للمسافرين الذين يستكشفون المرتفعات الشمالية الجميلة."
    },
    "CICILIA Rouge Dalat brings colonial vintage charm and sophisticated boutique luxury to the misty streets of Dalat.": {
        "vi": "CICILIA Rouge Dalat mang nét quyến rũ cổ điển thời thuộc địa và sự sang trọng tinh tế của boutique đến những con phố sương mù của Đà Lạt.",
        "ar": "يضفي CICILIA Rouge Dalat سحرًا عتيقًا من العهد الاستعماري وفخامة راقية على شوارع Dalat الضبابية."
    },
    "Minh Toan SAFI Ocean Hotel overlooks the stunning My Khe Beach in Da Nang, offering spacious ocean-view rooms and premium seaside hospitality.": {
        "vi": "Khách sạn Minh Toàn SAFI Ocean hướng tầm nhìn ra bãi biển Mỹ Khê tuyệt đẹp ở Đà Nẵng, cung cấp các phòng rộng rãi hướng biển và dịch vụ nghỉ dưỡng cao cấp ven biển.",
        "ar": "يطل Minh Toan SAFI Ocean Hotel على شاطئ My Khe المذهل في Da Nang، ويتميز بغرف واسعة مطلة على البحر وضيافة راقية على شاطئ البحر."
    },
    "Cicilia Saigon Center offers elegant and contemporary accommodations in the heart of District 1, Ho Chi Minh City.": {
        "vi": "Cicilia Saigon Center cung cấp chỗ nghỉ thanh lịch và hiện đại ngay tại trung tâm Quận 1, Thành phố Hồ Chí Minh.",
        "ar": "يوفر Cicilia Saigon Center أماكن إقامة أنيقة وعصرية في قلب المنطقة 1 بمدينة Ho Chi Minh City."
    },
    "offers refined luxury accommodations, personalized service, and modern comforts.": {
        "vi": "mang đến chỗ nghỉ sang trọng tinh tế, dịch vụ cá nhân hóa và các tiện nghi hiện đại.",
        "ar": "يقدم أماكن إقامة فاخرة وخدمات مخصصة ووسائل راحة حديثة."
    },
    "The cities in frames": {
        "vi": "Những Thành Phố Trong Khung Cảnh",
        "ar": "المدن في إطارات"
    },
    "Through Local Eyes": {
        "vi": "Qua Góc Nhìn Bản Địa",
        "ar": "من خلال عيون محلية"
    },
    "The city collection": {
        "vi": "Bộ Sưu Tập Thành Phố",
        "ar": "مجموعة المدينة"
    },
    "Sense of Pace: Immersive": {
        "ar": "وتيرة السفر: غامرة",
        "vi": "Nhịp độ: Trải nghiệm sâu"
    },
    "Sense of Pace: Balanced": {
        "ar": "وتيرة السفر: متوازنة",
        "vi": "Nhịp độ: Cân bằng"
    },
    "Sense of Pace: Relaxed": {
        "ar": "وتيرة السفر: مريحة",
        "vi": "Nhịp độ: Thư thái"
    },

    # Pricing Headers
    "Journey Investment": {
        "ar": "الاستثمار في الرحلة",
        "vi": "Hành Trình Đầu Tư"
    },
    "Total": {
        "ar": "الإجمالي",
        "vi": "Tổng"
    },
    "Currency": {
        "ar": "العملة",
        "vi": "Tiền tệ"
    },
    "Final rates subject to reconfirmation.": {
        "ar": "الأسعار النهائية تخضع لإعادة التأكيد.",
        "vi": "Giá cuối cùng có thể thay đổi khi xác nhận."
    },

    # Day Title Prefix
    "Day": {
        "ar": "يوم",
        "vi": "Ngày"
    },
    "DAY": {
        "ar": "يوم",
        "vi": "NGÀY"
    },

    # Vietnamese Destinations translations
    "Hanoi": {
        "vi": "Hà Nội",
        "ar": "Hanoi"
    },
    "Ha Long Bay": {
        "vi": "Vịnh Hạ Long",
        "ar": "Ha Long Bay"
    },
    "Halong Bay": {
        "vi": "Vịnh Hạ Long",
        "ar": "Halong Bay"
    },
    "Halong": {
        "vi": "Hạ Long",
        "ar": "Halong"
    },
    "Sapa": {
        "vi": "Sa Pa",
        "ar": "Sapa"
    },
    "Da Nang": {
        "vi": "Đà Nẵng",
        "ar": "Da Nang"
    },
    "Hoi An": {
        "vi": "Hội An",
        "ar": "Hoi An"
    },
    "Dalat": {
        "vi": "Đà Lạt",
        "ar": "Dalat"
    },
    "Da Lat": {
        "vi": "Đà Lạt",
        "ar": "Da Lat"
    },
    "Ninh Binh": {
        "vi": "Ninh Bình",
        "ar": "Ninh Binh"
    },
    "Ninh Bình": {
        "vi": "Ninh Bình",
        "ar": "Ninh Binh"
    },
    "Mekong Delta": {
        "vi": "Đồng bằng sông Cửu Long",
        "ar": "Mekong Delta"
    },
    "Ho Chi Minh City": {
        "vi": "Hồ Chí Minh",
        "ar": "Ho Chi Minh City"
    },
    "Ho Chi Minh": {
        "vi": "Hồ Chí Minh",
        "ar": "Ho Chi Minh"
    },
    "Saigon": {
        "vi": "Hồ Chí Minh",
        "ar": "Ho Chi Minh City"
    },

    # Specialist Section
    "Custom Itineraries, Luxury Travel, Local Experiences": {
        "vi": "Thiết kế lịch trình riêng, Du lịch sang trọng, Trải nghiệm bản địa",
        "ar": "مسارات مخصصة، سفر فاخر، تجارب محلية"
    },
    "Years designing bespoke journeys": {
        "vi": "Nhiều năm thiết kế các hành trình độc bản",
        "ar": "سنوات من الخبرة في تصميم الرحلات المخصصة"
    },
    "Your Dedicated Specialist": {
        "vi": "Chuyên Viên Riêng Của Bạn",
        "ar": "مستشارك المتخصص"
    },
    "Meet Your Travel Specialist": {
        "vi": "Gặp Gỡ Chuyên Gia Thiết Kế Hành Trình",
        "ar": "تعرّف على مصمم رحلتك"
    },
    "I am your dedicated travel specialist. I handpicked every hotel, private transfer, and local guide on this itinerary to ensure you experience the true depth of Vietnam in comfort, privacy, and at your own pace. I will personally oversee your journey from behind the scenes.": {
        "vi": "Tôi là chuyên gia thiết kế hành trình riêng của bạn. Tôi đã tự tay chọn lọc từng khách sạn, chuyến xe riêng tư và hướng dẫn viên bản địa trong lịch trình này để đảm bảo bạn được trải nghiệm chiều sâu thực sự của Việt Nam một cách thoải mái, riêng tư nhất và theo nhịp độ của riêng bạn. Tôi sẽ đích thân đồng hành và giám sát chuyến đi của bạn.",
        "ar": "أنا مصمم رحلتك المخصص. لقد اخترت بنفسي كل فندق، وسيلة نقل خاصة، ومرشد محلي في هذا المسار لضمان تجربتك للعمق الحقيقي لفيتنام بكل راحة وخصوصية وبوتيرتك الخاصة. سأشرف شخصيًا على رحلتك خلف الكواليس."
    },
    "Private Luxury Quotation": {
        "ar": "عرض سعر خاص فاخر",
        "vi": "Báo giá sang trọng riêng tư"
    },
    "Prepared for": {
        "ar": "مُعدّ لصالح",
        "vi": "Chuẩn bị cho"
    },
    "Luxury quotation prepared for": {
        "ar": "عرض سعر فاخر مُعدّ لصالح",
        "vi": "Báo giá sang trọng được chuẩn bị cho"
    },
    "Refer to Booking & Payment terms below.": {
        "ar": "يرجى الرجوع إلى شروط الحجز والدفع أدناه.",
        "vi": "Vui lòng tham khảo các điều khoản Đặt chỗ & Thanh toán bên dưới."
    },
    "Share travel dates, preferred hotel tier, rooming list and any dietary or mobility requirements. We will reconfirm availability and return a finalized quotation.": {
        "ar": "يرجى مشاركة تواريخ السفر، فئة الفندق المفضلة، قائمة توزيع الغرف، وأي متطلبات غذائية أو حركية. سنقوم بتأكيد الإمكانية وإرسال عرض السعر النهائي.",
        "vi": "Hãy chia sẻ ngày đi, hạng khách sạn mong muốn, danh sách phòng và bất kỳ yêu cầu ăn uống hoặc đi lại nào. Chúng tôi sẽ xác nhận tình trạng dịch vụ và gửi báo giá hoàn chỉnh."
    },

    "Confirmed Booking Itinerary": {
        "ar": "برنامج الرحلة المؤكد",
        "vi": "Hành trình đặt chỗ đã xác nhận"
    },
    "Detailed booking itinerary prepared for": {
        "ar": "برنامج رحلة مفصل مُعدّ لصالح",
        "vi": "Hành trình chi tiết được chuẩn bị cho"
    },
    "PROGRAM OVERVIEW": {
        "ar": "نظرة عامة على البرنامج",
        "vi": "TỔNG QUAN CHƯƠNG TRÌNH"
    }
}

def translate_filter(text: str, lang: str = "en") -> str:
    if not text:
        return ""
    clean_text = text.strip()
    # 1. Tra từ điển tĩnh trước
    if clean_text in STATIC_DICTIONARY:
        val = STATIC_DICTIONARY[clean_text].get(lang or "en")
        if val:
            return val
    # 2. Nếu không phải tiếng Việt ("vi") mà không tìm thấy bản dịch, thực hiện bỏ dấu tiếng Việt để hiển thị không dấu
    if lang != "vi":
        import unicodedata
        s = ''.join(c for c in unicodedata.normalize('NFD', clean_text) if unicodedata.category(c) != 'Mn')
        return s.replace('Đ', 'D').replace('đ', 'd')
    return clean_text

templates.env.filters["translate"] = translate_filter


ARABIC_PLACE_NAME_ALIASES = {
    "مدينة هو تشي منه": "Ho Chi Minh City",
    "هو تشي منه": "Ho Chi Minh City",
    "سايغون": "Ho Chi Minh City",
    "خليج ها لونغ": "Halong Bay",
    "خليج هالونج": "Halong Bay",
    "ها لونغ": "Halong",
    "هالونغ": "Halong",
    "دا نانغ": "Da Nang",
    "دانانغ": "Da Nang",
    "هوي آن": "Hoi An",
    "هوي ان": "Hoi An",
    "دالات": "Dalat",
    "سابا": "Sapa",
    "هانوي": "Hanoi",
    "هانوى": "Hanoi",
    "نينه بينه": "Ninh Binh",
    "دلتا ميكونغ": "Mekong Delta",
    "نها ترانغ": "Nha Trang",
    "نها ترانج": "Nha Trang",
    "سوق دونغ سوان": "Dong Xuan Market",
    "تام كوك": "Tam Coc",
    "هانغ موا": "Hang Mua",
    "قمة فانسيبان": "Fansipan",
    "فانسيبان": "Fansipan",
    "قرية كات كات": "Cat Cat Village",
    "كات كات": "Cat Cat",
    "لاو تشاي": "Lao Chai",
    "تا فان": "Ta Van",
    "با نا هيلز": "Ba Na Hills",
    "غابة جوز الهند باي ماو": "Bay Mau Coconut Forest",
    "هوا فو ثانه": "Hoa Phu Thanh",
    "لانغ بيانغ": "Lang Biang",
    "شلال داتانلا": "Datanla Waterfall",
    "مقهى مي لينه": "Me Linh Coffee",
    "أنفاق كو تشي": "Cu Chi Tunnels",
    "كو تشي": "Cu Chi",
    "سوق بن ثانه": "Ben Thanh Market",
    "مطار تان سون نهات": "Tan Son Nhat Airport",
    "ميناسي بريميوم": "Minasi Premium Hotel",
    "فندق ميناسي بريميوم": "Minasi Premium Hotel",
    "لا كاستا كروز": "La Casta Cruise",
    "فندق بورا": "Bora Hotel",
    "مينه توان صافي أوشن": "Minh Toan SAFI Ocean Hotel",
    "فندق مينه توان صافي أوشن": "Minh Toan SAFI Ocean Hotel",
    "سيسيليا روج دالات": "CICILIA Rouge Dalat",
    "فندق سيسيليا روج دالات": "CICILIA Rouge Dalat",
    "سيسيليا سايغون سنتر": "Cicilia Saigon Center",
    "فندق سيسيليا سايغون سنتر": "Cicilia Saigon Center",
}

ARABIC_CANONICAL_LTR_PHRASES = tuple(sorted({
    *ARABIC_PLACE_NAME_ALIASES.values(),
    "Silver Waterfall",
    "Egg Coffee",
    "Train Street Coffee",
    "Moana Coffee",
    "Han River Cruise",
    "Crazy House",
    "Clay Tunnel",
    "Fresh Garden",
    "Elephant Waterfall",
    "Apartment Coffee",
    "Central Post Office",
    "Hoi An Ancient Town",
    "Vietnam Safar",
    "Discovery Asia Travel Group",
    "B2B",
    "USD",
    "E-visa",
    "SIM",
    "Fast Track",
    "WhatsApp",
}, key=len, reverse=True))

ARABIC_LTR_PATTERNS = (
    re.compile(r"\b(?:QT|VS)-[A-Z0-9-]+\b"),
    re.compile(r"\+?\d[\d\s().-]{6,}\d"),
    re.compile(r"\b(?:https?://|www\.)[^\s<]+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}\s+[A-Za-z]+\s+[–-]\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}\b"),
    re.compile(r"\b\d[\d,]*(?:\.\d+)?\s*(?:USD|دولار أمريكي)\b"),
)


def canonicalize_place_names_in_text(text: str, lang: str = "en") -> str:
    if not text or lang != "ar":
        return text
    normalized = text
    for source, canonical in sorted(ARABIC_PLACE_NAME_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        normalized = normalized.replace(source, canonical)
    return normalized


def _ltr_span(value: str) -> str:
    return f'<span class="ltr-token">{escape(value)}</span>'


def format_arabic_mixed_content(text: str, lang: str = "en"):
    if not text:
        return ""
    if lang != "ar":
        return text

    normalized = canonicalize_place_names_in_text(text, lang)
    placeholders: dict[str, str] = {}
    placeholder_counter = 0

    def add_placeholder(raw_value: str) -> str:
        nonlocal placeholder_counter
        key = f"__LTR_TOKEN_{placeholder_counter}__"
        placeholder_counter += 1
        placeholders[key] = _ltr_span(raw_value)
        return key

    working = normalized
    for phrase in ARABIC_CANONICAL_LTR_PHRASES:
        pattern = re.compile(re.escape(phrase))
        working = pattern.sub(lambda match: add_placeholder(match.group(0)), working)

    for pattern in ARABIC_LTR_PATTERNS:
        working = pattern.sub(lambda match: add_placeholder(match.group(0)), working)

    rendered = str(escape(working))
    for key, html in placeholders.items():
        rendered = rendered.replace(key, html)
    return Markup(rendered)


def rtl_mixed_filter(text: str, lang: str = "en"):
    return format_arabic_mixed_content(text, lang)


templates.env.filters["rtl_mixed"] = rtl_mixed_filter


def format_date_filter(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        from datetime import datetime
        formats = [
            "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
            "%d/%m/%Y", "%m/%d/%Y",
            "%Y/%m/%d", "%b %d, %Y", "%d %b %Y", "%B %d, %Y",
            "%d %b %Y", "%d %B %Y"
        ]
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                break
            except ValueError:
                pass
        if dt:
            return dt.strftime("%d %b %Y")
    except Exception:
        pass
    return str(date_str)

templates.env.filters["format_date"] = format_date_filter


def format_display_date_range(checkin: str, checkout: str) -> str:
    return format_display_date_range_for_lang(checkin, checkout, "en")


def format_display_date_range_for_lang(checkin: str, checkout: str, lang: str = "en") -> str:
    try:
        from datetime import datetime
        ci = datetime.strptime(checkin, "%Y-%m-%d")
        co = datetime.strptime(checkout, "%Y-%m-%d")
        if lang == "ar":
            arabic_months = {
                1: "يناير",
                2: "فبراير",
                3: "مارس",
                4: "أبريل",
                5: "مايو",
                6: "يونيو",
                7: "يوليو",
                8: "أغسطس",
                9: "سبتمبر",
                10: "أكتوبر",
                11: "نوفمبر",
                12: "ديسمبر",
            }
            return f"{ci.day:02d} {arabic_months[ci.month]} – {co.day:02d} {arabic_months[co.month]} {co.year}"
        return f"{ci.strftime('%d %b')} – {co.strftime('%d %b %Y')}"
    except Exception:
        return f"{checkin} – {checkout}"


def format_duration_label(days_count: int, nights_count: int, lang: str = "en") -> str:
    if lang == "ar":
        return f"{days_count} يومًا / {nights_count} ليلة"
    if lang == "vi":
        return f"{days_count} ngày / {nights_count} đêm"
    return f"{days_count}D{nights_count}N"


def format_currency_display(amount: float, currency: str = "USD", lang: str = "en", *, per_person: bool = False) -> str:
    amount_text = f"{amount:,.0f}"
    if lang == "ar":
        base = f"{amount_text} دولار أمريكي" if currency == "USD" else f"{amount_text} {currency}"
        return f"{base} للشخص الواحد" if per_person else base
    base = f"{currency} {amount_text}"
    return f"{base} / person" if per_person else base


def normalize_room_note(text: str, lang: str = "en") -> str:
    if not text:
        return ""
    normalized = text.strip()
    if lang == "ar":
        mapping = {
            "Double/Twin Bed Room for 2 Adults": "غرفة مزدوجة أو بسريرين منفصلين لشخصين بالغين",
            "Twin/Double Sharing": "مشاركة غرفة مزدوجة أو بسريرين منفصلين",
        }
        return mapping.get(normalized, translate_filter(normalized, lang))
    return normalized


def _extract_image_url(image_value, default_img: str = "") -> str:
    if isinstance(image_value, dict):
        return image_value.get("url") or default_img
    if isinstance(image_value, str):
        return image_value or default_img
    return default_img


def canonicalize_place_names_in_data(value, lang: str = "en"):
    if isinstance(value, str):
        return canonicalize_place_names_in_text(value, lang)
    if isinstance(value, list):
        return [canonicalize_place_names_in_data(item, lang) for item in value]
    if isinstance(value, dict):
        return {key: canonicalize_place_names_in_data(item, lang) for key, item in value.items()}
    return value


def localize_place_name(text: str, lang: str = "en") -> str:
    if not text:
        return ""
    slug = _normalize_location_slug(text)
    canonical_by_slug = {
        "ha-noi": "Hanoi",
        "quang-ninh": "Halong Bay",
        "lao-cai": "Sapa",
        "da-nang": "Da Nang",
        "quang-nam": "Hoi An",
        "lam-dong": "Dalat",
        "ninh-binh": "Ninh Binh",
        "ho-chi-minh": "Ho Chi Minh City",
        "mekong": "Mekong Delta",
        "khanh-hoa": "Nha Trang",
    }
    if slug:
        canonical_name = canonical_by_slug.get(slug)
        if canonical_name:
            return translate_filter(canonical_name, lang)

    return translate_filter(text, lang)

async def translate_payload_llm(payload_dict: dict, target_lang: str, payload_type: str = "quotation", baseline_lang: str = "en") -> dict:
    """
    Translates all translatable string values in a payload dictionary to target_lang
    using a single batch LLM request with high-end luxury copywriting tone.
    """
    import copy
    import json
    import re
    from pydantic_ai import Agent
    import llm_client

    def is_translatable(key: str, val: str) -> bool:
        if not isinstance(val, str):
            return False
        val_clean = val.strip()
        if len(val_clean) <= 2:
            return False
        if re.match(r"^\d{4}-\d{2}-\d{2}$", val_clean):
            return False
        if val_clean.startswith("QT-") or val_clean.startswith("VS-"):
            return False
        # Ignore strictly technical or numeric keys or literal status options
        ignored_keys = {
            "currency", "priceType", "status", "startDate", "endDate", 
            "checkInDate", "checkOutDate", "block_id", "service_type",
            "hotel", "activity", "guide", "transfer", "flight"
        }
        if key in ignored_keys:
            return False
        # Also ignore literal values for status fields
        if val_clean in {"pending", "not_required"}:
            return False
        return True

    def _extract(data: any, path: str = "") -> list[tuple[str, str]]:
        extracted = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k in {"retrievalStatus", "candidateBlocks"}:
                    continue
                current_path = f"{path}.{k}" if path else k
                if isinstance(v, str) and is_translatable(k, v):
                    extracted.append((current_path, v))
                elif isinstance(v, (dict, list)):
                    extracted.extend(_extract(v, current_path))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                if isinstance(item, str) and is_translatable("", item):
                    extracted.append((current_path, item))
                elif isinstance(item, (dict, list)):
                    extracted.extend(_extract(item, current_path))
        return extracted

    def _inject(data: any, trans_map: dict[str, str], path: str = ""):
        if isinstance(data, dict):
            for k, v in data.items():
                current_path = f"{path}.{k}" if path else k
                if isinstance(v, str) and current_path in trans_map:
                    data[k] = trans_map[current_path]
                elif isinstance(v, (dict, list)):
                    _inject(v, trans_map, current_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                if isinstance(item, str) and current_path in trans_map:
                    data[i] = trans_map[current_path]
                elif isinstance(item, (dict, list)):
                    _inject(item, trans_map, current_path)

    def _normalize_digits(text: str) -> str:
        table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        return text.translate(table)

    def _extract_numeric_tokens(text: str) -> list[str]:
        return re.findall(r"\d+(?:[.,]\d+)?", _normalize_digits(text or ""))

    # Clone the dictionary to avoid side effects
    working_dict = copy.deepcopy(payload_dict)
    all_pairs = _extract(working_dict)
    if not all_pairs:
        return working_dict

    # Check against STATIC_DICTIONARY first to save LLM tokens
    pairs_to_translate = []
    local_translations = {}
    
    for path, val in all_pairs:
        clean_val = val.strip()
        if clean_val in STATIC_DICTIONARY and target_lang in STATIC_DICTIONARY[clean_val]:
            local_translations[path] = STATIC_DICTIONARY[clean_val][target_lang]
        else:
            pairs_to_translate.append((path, val))

    # If all items are pre-translated, we can skip the LLM call entirely!
    if not pairs_to_translate:
        _inject(working_dict, local_translations)
        return working_dict

    # Prepare batch prompt
    flat_texts = [p[1] for p in pairs_to_translate]
    
    # Extract some context if available
    tour_title = ""
    if "landingpageContent" in payload_dict:
        tour_title = payload_dict["landingpageContent"].get("heroSection", {}).get("subtitle", "")
    elif "title" in payload_dict:
        tour_title = payload_dict.get("title", "")

    guest_profile = payload_dict.get("journeyGlance", {}).get("guestProfile", "") or payload_dict.get("preparedFor", "")

    target_lang_name = {
        "en": "English",
        "vi": "Vietnamese (Tiếng Việt)",
        "ar": "Arabic (العربية)"
    }.get(target_lang, target_lang.upper())

    # Build prompt
    prompt = (
        f"Translate the following list of luxury travel text strings into {target_lang_name}.\n\n"
        f"CONTEXT OF THE TOUR:\n"
        f"- Tour Title: {tour_title}\n"
        f"- Travelers: {guest_profile}\n\n"
        f"INPUT TEXTS TO TRANSLATE:\n"
        + json.dumps(flat_texts, ensure_ascii=False, indent=2)
    )

    system_prompt = (
        "You are an expert multilingual Luxury Travel Copywritter with faithful translator.\n"
        f"Your task is to translate the given list of travel text strings into {target_lang_name}.\n\n"
        "RULES FOR PREMIUM & LUXURY TRANSLATION:\n"
        "1. Tone and vocabulary:\n"
        "   - English ('en'): polished, elegant, but fact-faithful.\n"
        "   - Vietnamese ('vi'): natural, polished, but fact-faithful.\n"
        "   - Arabic ('ar'): polished Modern Standard Arabic, but fact-faithful.\n"
        "2. Fidelity is mandatory:\n"
        "   - Do NOT add meals, activities, shopping, romance, welcome experiences, or travel logic not present in the source string.\n"
        "   - Do NOT change route order, destination sequence, proper nouns, dates, quantities, or prices.\n"
        "   - If the source string is operational or factual, keep it operational and factual.\n"
        "   - You may improve fluency, but not meaning.\n"
        "2. Format requirements:\n"
        "   - You MUST return a valid JSON array of strings containing the translations in the EXACT SAME order and quantity.\n"
        "   - Do NOT omit any strings. Do NOT combine strings.\n"
        "   - Output ONLY the raw JSON list of strings. Do NOT wrap it in markdown block fences like ```json. Do NOT include any chat preamble, comments, or explanations."
    )

    try:
        agent = Agent(
            model=llm_client.get_model(),
            system_prompt=system_prompt
        )
        res = await agent.run(prompt)
        res_text = res.output.strip()
        
        # Strip potential markdown fences if agent returned them despite instructions
        if res_text.startswith("```"):
            lines = res_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            res_text = "\n".join(lines).strip()

        translated_list = json.loads(res_text)
        
        if not isinstance(translated_list, list) or len(translated_list) != len(flat_texts):
            log.warning("[translate_payload_llm] LLM returned invalid array size: expected %d, got %s", len(flat_texts), type(translated_list))
            return payload_dict

        # Build injection map combining local and LLM translations
        trans_map = copy.deepcopy(local_translations)
        for (path, _), trans in zip(pairs_to_translate, translated_list):
            src_numbers = _extract_numeric_tokens(_)
            tgt_numbers = _extract_numeric_tokens(trans)
            if src_numbers and src_numbers != tgt_numbers:
                log.warning("[translate_payload_llm] Numeric drift detected for %s; preserving source text", path)
                trans_map[path] = _
            else:
                trans_map[path] = trans

        _inject(working_dict, trans_map)
        return working_dict

    except Exception as exc:
        log.exception("[translate_payload_llm] Batch translation failed to %s: %s", target_lang, exc)
        return payload_dict


def _load_ctx_data(item_id: str) -> dict | None:
    """Load the single ctx.json file from memory store, disk, or GitHub in production."""
    # First check quotations memory store
    entry = quotations.get(item_id) or itineraries.get(item_id)
    if entry and entry.get("ctx"):
        return entry["ctx"]
        
    # Fetch from GitHub first if production
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        repo = os.getenv("GITHUB_REPO")
        token = os.getenv("GITHUB_TOKEN")
        if repo and token:
            import urllib.request
            try:
                url = f"https://api.github.com/repos/{repo}/contents/published/{item_id}/ctx.json"
                req = urllib.request.Request(url, headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3.raw",
                    "User-Agent": "quotation-landingpage/1.0"
                })
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    # Cache in memory
                    store = itineraries if item_id.startswith("iti_") else quotations
                    if item_id in store:
                        store[item_id]["ctx"] = data
                    else:
                        store[item_id] = {"ctx": data}
                    return data
            except Exception as ex:
                log.warning("Failed to fetch ctx.json from GitHub for %s: %s", item_id, ex)

    path = os.path.join("published", item_id, "ctx.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning("Failed to parse ctx.json for %s: %s", item_id, e)
    return None

def _load_translation_status(item_id: str, default_lang: str = "en") -> dict:
    """Reads translation status from ctx.json."""
    ctx_data = _load_ctx_data(item_id)
    if ctx_data and "translation_status" in ctx_data:
        return ctx_data["translation_status"]
    # Fallback to checking disk structure (in case migrated from older builds)
    path = os.path.join("published", item_id, "translation_status.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    ctx = {
        "baseline_lang": default_lang,
        "available_langs": [default_lang]
    }

async def _save_translation_status(item_id: str, status: dict):
    # This is a legacy helper. In the single-JSON design, we save status directly in ctx.json.
    # We still keep this helper for backward compatibility and saving legacy translation_status.json if needed.
    path = os.path.join("published", item_id, "translation_status.json")
    content = json.dumps(status, ensure_ascii=False, indent=2)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

async def _translate_item_on_demand(item_id: str, target_lang: str, is_itinerary: bool = False) -> bool:
    """
    Translates the baseline payload to target_lang on-demand.
    Updates translations dictionary inside the single ctx.json file.
    No HTML/PDF suffix files are written to disk.
    """
    if target_lang not in ("en", "vi", "ar"):
        return False
        
    ctx_data = _load_ctx_data(item_id)
    if not ctx_data:
        log.warning("[translation] ctx.json not found for %s", item_id)
        return False
        
    available_langs = ctx_data.get("available_langs", [])
    if target_lang in available_langs:
        return True
        
    baseline_payload_dict = ctx_data.get("baseline_payload")
    baseline_lang = ctx_data.get("baseline_lang", "en")
    
    if not baseline_payload_dict:
        log.warning("[translation] baseline_payload not found in ctx.json for %s", item_id)
        return False
        
    try:
        log.info("[translation] Translating %s from %s to %s via LLM...", item_id, baseline_lang, target_lang)
        translated_dict = await translate_payload_llm(baseline_payload_dict, target_lang, baseline_lang=baseline_lang)
        
        # Validate translated dict
        if is_itinerary:
            DetailItineraryPayload.model_validate(translated_dict)
        else:
            TourQuotationPayload.model_validate(translated_dict)
            
        # Update translations in ctx_data
        translations = ctx_data.get("translations", {})
        translations[target_lang] = translated_dict
        ctx_data["translations"] = translations
        
        # Update available_langs
        if target_lang not in available_langs:
            available_langs.append(target_lang)
        ctx_data["available_langs"] = available_langs
        ctx_data["translation_status"] = {
            "baseline_lang": baseline_lang,
            "available_langs": available_langs
        }
        
        # Write updated ctx.json to disk
        quo_dir = os.path.join("published", item_id)
        os.makedirs(quo_dir, exist_ok=True)
        ctx_path = os.path.join(quo_dir, "ctx.json")
        with open(ctx_path, "w", encoding="utf-8") as f:
            json.dump(ctx_data, f, ensure_ascii=False, default=str)
            
        # Update RAM stores if present
        store = itineraries if is_itinerary else quotations
        if item_id in store:
            store[item_id]["ctx"] = ctx_data
            
        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            await publish_file_to_github(
                file_path=f"published/{item_id}/ctx.json",
                html_content=json.dumps(ctx_data, ensure_ascii=False, default=str),
                commit_message=f"Update translations in ctx.json for {item_id}"
            )
            
        log.info("[translation] Successfully translated %s to %s and saved to ctx.json", item_id, target_lang)
        return True
    except Exception as e:
        log.exception("[translation] Failed to translate %s on-demand: %s", item_id, e)
        return False


# ── In-memory quotation store ─────────────────────────────────────────────────
# { quotation_id: { "payload": dict, "html": str, "status": str,
#                   "published_url": str|None, "version": int } }
quotations: dict[str, dict] = {}
itineraries: dict[str, dict] = {}

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8111")


# ── Debug middleware — logs every incoming request and response ──────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start = time.monotonic()

    # Log request headers for ALL methods
    log.debug(
        "→ REQUEST  %s %s  headers=%s",
        request.method,
        request.url,
        dict(request.headers),
    )

    if request.method in ("POST", "PUT", "PATCH"):
        body_bytes = await request.body()

        # Log raw body
        if body_bytes:
            try:
                body_json = json.loads(body_bytes)
                log.debug(
                    "→ BODY [%s %s]:\n%s",
                    request.method,
                    request.url.path,
                    json.dumps(body_json, indent=2, ensure_ascii=False),
                )
            except Exception:
                log.debug("→ BODY (non-JSON, %d bytes): %s", len(body_bytes), body_bytes[:500])
        else:
            log.warning("→ BODY is EMPTY for %s %s — possible middleware body-read issue", request.method, request.url.path)

        # Rebuild receive so FastAPI/Starlette can read the body again.
        # IMPORTANT: must handle both http.request and http.disconnect messages.
        body_consumed = False

        async def receive():
            nonlocal body_consumed
            if not body_consumed:
                body_consumed = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            # Subsequent calls return disconnect so the connection lifecycle ends cleanly
            return {"type": "http.disconnect"}

        request = Request(request.scope, receive)

    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        log.exception("← EXCEPTION after %.0fms for %s %s: %s", elapsed, request.method, request.url.path, exc)
        raise

    elapsed = (time.monotonic() - start) * 1000
    log.info(
        "← RESPONSE %s %s  status=%s  time=%.0fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


# ── Validation error handler — surfaces exact Pydantic field errors ──────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    log.error(
        "VALIDATION ERROR [%s %s] — %d error(s):\n%s",
        request.method,
        request.url.path,
        len(errors),
        json.dumps(errors, indent=2, default=str),
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": errors,
            "hint": "Check the field path in each error's 'loc' to find the missing or invalid field.",
        },
    )


# ── Generic error handler — catches any unhandled exceptions ─────────────────
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    log.exception("UNHANDLED EXCEPTION [%s %s]", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ── Pydantic models — mapped 1:1 from the OpenAPI schema (v2.1.0) ───────────
# Only fields listed under `required:` in the spec are non-Optional here.

class Duration(BaseModel):
    # required: [days, nights]
    days:   int
    nights: int
    label:  Optional[str] = None


class TravelDates(BaseModel):
    # required: [startDate, endDate]
    startDate:   date
    endDate:     date
    displayText: Optional[str] = None


class GuestComposition(BaseModel):
    # required: [totalGuests]
    totalGuests:  int
    adults:       Optional[int]       = None
    children:     Optional[int]       = None
    infants:      Optional[int]       = None
    childrenAges: Optional[List[int]] = None
    displayText:  Optional[str]       = None


class Customer(BaseModel):
    # required: [name]
    name:        str
    contactName: Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    address:     Optional[str] = None
    nationality: Optional[str] = None
    market:      Optional[str] = None


class Seller(BaseModel):
    # required: [companyName]
    companyName: str
    contactName: Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    address:     Optional[str] = None
    taxCode:     Optional[str] = None
    website:     Optional[str] = None


class TextSection(BaseModel):
    # required: [paragraphs]
    paragraphs: List[str]
    heading:    Optional[str] = None


class ItineraryDay(BaseModel):
    # required: [dayNumber, title, description]
    dayNumber:          int
    title:              str
    description:        List[str]
    date:               Optional[str]        = None  # kept as str to avoid Pydantic v2 field-name shadowing
    overnight:          Optional[str]        = None
    meals:              Optional[List[str]]  = None
    destinations:       Optional[List[str]]  = None
    activities:         Optional[List[str]]  = None
    optionalActivities: Optional[List[str]]  = None
    notes:              Optional[List[str]]  = None


class MoneyAmount(BaseModel):
    # required: [amount, currency]
    amount:      float
    currency:    str
    displayText: Optional[str]  = None
    isFromPrice: Optional[bool] = None


class PriceOption(BaseModel):
    # required: [hotelCategory, pricePerPerson, totalPrice]
    hotelCategory:        str
    pricePerPerson:       MoneyAmount
    totalPrice:           MoneyAmount
    optionName:           Optional[str]       = None
    isConfirmedMainOption: Optional[bool]     = None
    isAlternativeOption:  Optional[bool]      = None
    notes:                Optional[List[str]] = None


class TourPricing(BaseModel):
    # required: [currency, priceOptions]
    currency:     str
    priceOptions: List[PriceOption]
    pricingTitle: Optional[str]   = None
    basis:        Optional[str]   = None
    totalGuests:  Optional[int]   = None
    subtotal:     Optional[float] = None
    discountTotal: Optional[float] = None
    taxTotal:     Optional[float] = None
    grandTotal:   Optional[float] = None


from quotation_schemas import TourQuotationPayload


# ── Detailed Itinerary Booking Models ───────────────────────────────────────

class BookedHotel(BaseModel):
    name: str
    star: Optional[int] = None
    addressArea: Optional[str] = None
    roomType: Optional[str] = None
    checkInDate: str
    checkOutDate: str
    nights: int
    destination: str
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    imageUrl: Optional[str] = None
    pricePerNightUsd: Optional[float] = None
    pricePerNightVnd: Optional[float] = None


class BookedActivity(BaseModel):
    activityName: str
    operator: Optional[str] = None
    date: str
    area: str
    durationHours: Optional[float] = None
    privateGroup: Optional[bool] = True
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    imageUrl: Optional[str] = None
    pricePerAdultUsd: Optional[float] = None
    pricePerChildUsd: Optional[float] = None
    totalEstimateUsd: Optional[float] = None


class BookedTransfer(BaseModel):
    transferType: str  # airport_pickup, airport_dropoff, intercity, day_trip_return
    fromLocation: str
    toLocation: str
    date: str
    vehicleRequirement: str  # e.g., 7-seat, 16-seat
    seats: Optional[int] = None
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    priceUsd: Optional[float] = None
    priceVnd: Optional[float] = None


class BookedGuide(BaseModel):
    guideName: Optional[str] = None
    language: str
    destination: str
    dates: List[str]
    days: int
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    pricePerDayUsd: Optional[float] = None
    totalEstimateUsd: Optional[float] = None


class BookedFlight(BaseModel):
    flightNumber: str
    airline: str
    date: str
    fromCity: str
    toCity: str
    departureTime: Optional[str] = None
    arrivalTime: Optional[str] = None
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    priceUsd: Optional[float] = None


class DetailItineraryPayload(BaseModel):
    quotationNumber: str
    quotationTitle: str
    tourTitle: str
    duration: Duration
    preparedFor: str
    nationality: Optional[str] = None
    travelDates: TravelDates
    guests: GuestComposition
    route: List[str]
    travelStyle: Optional[List[str]] = None
    
    # Service and itinerary lists
    notes: Optional[List[str]] = None
    seller: Optional[Seller] = None
    programOverview: Optional[TextSection] = None
    hotels: List[BookedHotel] = Field(default_factory=list)
    activities: List[BookedActivity] = Field(default_factory=list)
    transfers: List[BookedTransfer] = Field(default_factory=list)
    flights: List[BookedFlight] = Field(default_factory=list)
    guides: List[BookedGuide] = Field(default_factory=list)
    itinerary: List[ItineraryDay] = Field(default_factory=list)
    inclusions: Optional[List[str]] = None
    exclusions: Optional[List[str]] = None
    priceConditions: Optional[TextSection] = None
    pricing: Optional[TourPricing] = None
# ── Context builder (pure fn — no I/O) ───────────────────────────────────────


def truncate_text(text: Optional[str], max_chars: int) -> str:
    if not text:
        return ""
    text_str = str(text).strip()
    if len(text_str) <= max_chars:
        return text_str
    # Try to split on last space to avoid cutting words
    truncated = text_str[:max_chars].rsplit(" ", 1)[0]
    if not truncated:
        truncated = text_str[:max_chars - 3]
    return truncated.strip() + "..."


def _load_quotation_manual_override(quotation_id: str) -> dict:
    path = os.path.join("published", quotation_id, "manual_overrides.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log.warning("Failed to load manual override for %s: %s", quotation_id, exc)
        return {}


def _lang_override(override: dict, lang: str) -> dict:
    return ((override or {}).get("langs") or {}).get(lang, {})


def _compress_route_sequence(stops: list[str]) -> list[str]:
    compressed: list[str] = []
    for stop in stops:
        if not stop:
            continue
        if not compressed or compressed[-1] != stop:
            compressed.append(stop)
    return compressed


def _build_factual_day_title(day_number: int, stops: list[str], lang: str) -> str:
    clean_stops = [truncate_text(localize_place_name(stop, lang), 40) for stop in stops if stop]
    if not clean_stops:
        clean_stops = ["Vietnam"]
    day_label = {
        "vi": f"Ngày {day_number}",
        "ar": f"اليوم {day_number}",
    }.get(lang, f"Day {day_number}")
    route = " → ".join(clean_stops)
    return f"{day_label} — {route}"


def _build_route_stop_label(day_number: int, stop: str, lang: str, *, prefix: str | None = None) -> str:
    day_label = {
        "vi": f"Ngày {day_number}",
        "ar": f"اليوم {day_number}",
    }.get(lang, f"Day {day_number}")
    localized_stop = localize_place_name(stop, lang)
    if prefix:
        return f"{day_label} — {prefix} {localized_stop}"
    return f"{day_label} — {localized_stop}"


def _build_route_stops_from_timeline(timeline_days: list[dict]) -> list[dict]:
    route_stops: list[dict] = []
    for day in timeline_days:
        day_stops = [stop for stop in (day.get("destinations") or []) if stop]
        if not day_stops and day.get("overnight"):
            day_stops = [day["overnight"]]
        first_stop = day_stops[0] if day_stops else ""
        for idx, stop in enumerate(day_stops, start=1):
            is_last = idx == len(day_stops)
            returns_to_origin = len(day_stops) > 2 and is_last and stop == first_stop
            kind = "overnight" if is_last and stop == day.get("overnight") else "visit"
            map_title = _build_route_stop_label(day["dayNumber"], stop, day.get("lang", "en"))
            show_marker = True
            if len(day_stops) > 1 and idx < len(day_stops):
                kind = "transfer" if idx == 1 else "visit"
            if idx == 1 and len(day_stops) > 1:
                prefix = {"vi": "Khởi hành từ", "ar": "الانطلاق من", "en": "Depart from"}.get(
                    day.get("lang", "en"),
                    "Depart from",
                )
                map_title = _build_route_stop_label(day["dayNumber"], stop, day.get("lang", "en"), prefix=prefix)
                show_marker = False
            elif returns_to_origin:
                prefix = {"vi": "Trở lại", "ar": "العودة إلى", "en": "Return to"}.get(
                    day.get("lang", "en"),
                    "Return to",
                )
                map_title = _build_route_stop_label(day["dayNumber"], stop, day.get("lang", "en"), prefix=prefix)
                kind = "return"
                show_marker = False
            elif len(day_stops) > 1:
                map_title = _build_route_stop_label(day["dayNumber"], stop, day.get("lang", "en"))
            localized_stop = localize_place_name(stop, day.get("lang", "en"))
            route_stops.append({
                "dayNumber": day["dayNumber"],
                "stopOrder": idx,
                "destination": stop,
                "displayName": localized_stop,
                "mapTitle": map_title,
                "kind": kind,
                "showMarker": show_marker,
            })
    return route_stops


def _format_day_range_label(day_start: int, day_end: int, lang: str) -> str:
    if day_start == day_end:
        return {
            "vi": f"Ngày {day_start}",
            "ar": f"اليوم {day_start}",
        }.get(lang, f"Day {day_start}")
    return {
        "vi": f"Ngày {day_start}-{day_end}",
        "ar": f"الأيام {day_start}-{day_end}",
    }.get(lang, f"Days {day_start}-{day_end}")


def _format_nights_label(nights: int, lang: str) -> str:
    if lang == "vi":
        return f"{nights} đêm"
    if lang == "ar":
        return f"{nights} ليالٍ" if nights != 1 else "ليلة واحدة"
    return f"{nights} night" if nights == 1 else f"{nights} nights"


def _normalize_location_slug(location: str) -> str | None:
    if not location:
        return None
    from image_selector import resolve_slug_locally
    resolved = resolve_slug_locally(location)
    if resolved:
        return resolved

    normalized = location.lower().strip()
    extra_keywords = {
        "هانوي": "ha-noi",
        "هانوى": "ha-noi",
        "مدينة هو تشي منه": "ho-chi-minh",
        "هو تشي منه": "ho-chi-minh",
        "سايغون": "ho-chi-minh",
        "دا نانغ": "da-nang",
        "دانانغ": "da-nang",
        "هوي آن": "quang-nam",
        "هوي ان": "quang-nam",
        "خليج ها لونغ": "quang-ninh",
        "خليج هالونج": "quang-ninh",
        "هالونغ": "quang-ninh",
        "سابا": "lao-cai",
        "نينه بينه": "ninh-binh",
        "نها ترانغ": "khanh-hoa",
        "نها ترانج": "khanh-hoa",
        "دالات": "lam-dong",
        "دلتا ميكونغ": "mekong",
    }
    if normalized in extra_keywords:
        return extra_keywords[normalized]
    for keyword, slug in extra_keywords.items():
        if keyword in normalized:
            return slug
    return None


def _build_stay_segments_from_timeline(
    timeline_days: list[dict],
    hotel_plan_items: list[dict],
    lang: str,
) -> list[dict]:
    stay_segments: list[dict] = []
    if not timeline_days:
        return stay_segments

    grouped_days: list[list[dict]] = []
    current_group: list[dict] = []
    current_overnight_slug = None

    for day in timeline_days:
        overnight = day.get("overnight") or (day.get("destinations") or [None])[-1]
        overnight_slug = _normalize_location_slug(overnight or "")
        if not current_group or overnight_slug == current_overnight_slug:
            current_group.append(day)
            current_overnight_slug = overnight_slug
            continue
        grouped_days.append(current_group)
        current_group = [day]
        current_overnight_slug = overnight_slug
    if current_group:
        grouped_days.append(current_group)

    hotel_cursor = 0
    for order, days in enumerate(grouped_days, start=1):
        first_day = days[0]
        last_day = days[-1]
        city = last_day.get("overnight") or (last_day.get("destinations") or [None])[-1] or "Vietnam"
        city_slug = _normalize_location_slug(city)
        display_name = localize_place_name(city, lang)

        matched_hotel = None
        for idx in range(hotel_cursor, len(hotel_plan_items)):
            hotel = hotel_plan_items[idx]
            hotel_slug = _normalize_location_slug(hotel.get("destination", ""))
            if city_slug and hotel_slug == city_slug:
                matched_hotel = hotel
                hotel_cursor = idx + 1
                break
            if not city_slug and hotel.get("destination") == city:
                matched_hotel = hotel
                hotel_cursor = idx + 1
                break
        if matched_hotel is None and hotel_cursor < len(hotel_plan_items):
            matched_hotel = hotel_plan_items[hotel_cursor]
            hotel_cursor += 1

        excursions: list[str] = []
        activity_previews: list[dict] = []
        for day in days:
            day_destinations = [dest for dest in (day.get("destinations") or []) if dest]
            excursion_candidates = day_destinations[1:-1] if len(day_destinations) > 2 else []
            for dest in excursion_candidates:
                if not dest or _normalize_location_slug(dest) == city_slug:
                    continue
                translated_dest = localize_place_name(dest, lang)
                if translated_dest not in excursions:
                    excursions.append(translated_dest)
            description = ""
            if day.get("description"):
                description = day["description"][0]
            elif day.get("activities"):
                description = day["activities"][0]
            if description:
                activity_previews.append({
                    "dayNumber": day["dayNumber"],
                    "label": {
                        "vi": f"Ngày {day['dayNumber']}",
                        "ar": f"اليوم {day['dayNumber']}",
                    }.get(lang, f"Day {day['dayNumber']}"),
                    "summary": truncate_text(description, 120),
                })

        day_start = first_day["dayNumber"]
        day_end = last_day["dayNumber"]
        nights = max(1, day_end - day_start + 1)
        stay_segments.append({
            "segmentId": f"stay-{order}",
            "order": order,
            "city": city,
            "displayName": display_name,
            "dayStart": day_start,
            "dayEnd": day_end,
            "daysLabel": _format_day_range_label(day_start, day_end, lang),
            "nights": nights,
            "nightsLabel": _format_nights_label(nights, lang),
            "hotelName": matched_hotel.get("name", "") if matched_hotel else "",
            "hotelImage": matched_hotel.get("hotel_img", "") if matched_hotel else "",
            "hotelDateRange": matched_hotel.get("date_range", "") if matched_hotel else "",
            "coords": list(SLUG_COORDS.get(city_slug, ())) if city_slug in SLUG_COORDS else None,
            "excursions": excursions,
            "activityPreviews": activity_previews,
            "transportFromPrevious": "",
        })

    for idx, segment in enumerate(stay_segments):
        if idx == 0:
            continue
        previous = stay_segments[idx - 1]
        segment["transportFromPrevious"] = f"{previous['displayName']} → {segment['displayName']}"

    return stay_segments


def _build_timeline_days(
    quotation_id: str,
    payload: "TourQuotationPayload",
    lang: str,
    manual_override: dict,
    start_date_str: str = ""
) -> list[dict]:
    from datetime import datetime, timedelta
    lang_override = _lang_override(manual_override, lang)
    day_overrides = lang_override.get("day_overrides", {})
    timeline_days: list[dict] = []

    base_date = None
    if start_date_str:
        try:
            base_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            pass

    for itinerary_day in payload.itinerary:
        override_day = day_overrides.get(str(itinerary_day.dayNumber), {})
        raw_destinations = override_day.get("destinations") or [itinerary_day.destination]
        destinations = [truncate_text(localize_place_name(dest, lang), 40) for dest in raw_destinations if dest]
        overnight = truncate_text(
            localize_place_name(override_day.get("overnight", itinerary_day.destination), lang),
            40,
        )
        title = truncate_text(
            override_day.get("title") or _build_factual_day_title(itinerary_day.dayNumber, destinations, lang),
            120,
        )
        summary = canonicalize_place_names_in_text(
            truncate_text(override_day.get("summary", itinerary_day.summary), 350),
            lang,
        )
        dining = truncate_text(override_day.get("dining", itinerary_day.dining), 80)
        main_inclusions = canonicalize_place_names_in_text(
            truncate_text(
                override_day.get("mainInclusions", itinerary_day.mainInclusions),
                140,
            ),
            lang,
        )
        day_date_str = getattr(itinerary_day, "date", "") or ""
        if base_date:
            try:
                curr_date = base_date + timedelta(days=itinerary_day.dayNumber - 1)
                day_date_str = curr_date.strftime("%Y-%m-%d")
            except Exception:
                pass

        timeline_days.append({
            "dayNumber": itinerary_day.dayNumber,
            "date": day_date_str,
            "lang": lang,
            "title": title,
            "description": [summary] if summary else [],
            "overnight": overnight,
            "meals": [dining] if dining else [],
            "activities": [main_inclusions] if main_inclusions else [],
            "notes": [translate_filter(truncate_text(f"Sense of Pace: {itinerary_day.senseOfPace}", 80), lang)] if itinerary_day.senseOfPace else [],
            "destinations": destinations,
        })

    return timeline_days

def _build_itinerary_days_flat(timeline_days: list[dict], stay_segments: list[dict], lang: str, manual_override: dict = None) -> list[dict]:
    day_slugs = {}
    day_cities = {}
    for seg in stay_segments:
        city = seg.get("city", "Vietnam")
        slug = _normalize_location_slug(city) or "default"
        for day_num in range(seg["dayStart"], seg["dayEnd"] + 1):
            day_slugs[day_num] = slug
            day_cities[day_num] = seg.get("displayName") or city
            
    edited = (manual_override or {}).get("edited_fields", {})
    
    # Pre-calculate random image pools partitioned across days for each destination
    import hashlib
    import random
    
    dest_day_counts = {}
    for d in timeline_days:
        d_num = d["dayNumber"]
        d_slug = day_slugs.get(d_num, "default")
        dest_day_counts[d_slug] = dest_day_counts.get(d_slug, 0) + 1
        
    dest_image_pools = {}
    for d_slug in dest_day_counts:
        imgs = get_available_images_for_destination(d_slug)
        if imgs:
            seed_val = int(hashlib.md5(d_slug.encode()).hexdigest(), 16)
            rng = random.Random(seed_val)
            rng.shuffle(imgs)
        dest_image_pools[d_slug] = imgs
        
    dest_day_indices = {}
    flat_days = []
    
    for i, day_data in enumerate(timeline_days):
        day_num = day_data["dayNumber"]
        slug = day_slugs.get(day_num, "default")
        city = day_cities.get(day_num, "Vietnam")
        
        imgs = dest_image_pools.get(slug, [])
        day_idx = dest_day_indices.get(slug, 0)
        
        if len(imgs) > 0:
            num_days = dest_day_counts.get(slug, 1)
            num_imgs = len(imgs)
            
            # Partition imgs across days without overlap
            if num_imgs >= num_days:
                base_count = num_imgs // num_days
                extra = num_imgs % num_days
                chunk_size = base_count + (1 if day_idx < extra else 0)
                start_idx = day_idx * base_count + min(day_idx, extra)
                end_idx = start_idx + chunk_size
                day_imgs = imgs[start_idx:end_idx]
            else:
                # If there are fewer images than days, we must repeat to avoid empty images
                # but we try to give 1 image per day by repeating the pool
                day_imgs = [imgs[day_idx % num_imgs]]

            hero_img = day_imgs[0]
            carousel_imgs = day_imgs if len(day_imgs) > 1 else []
            s1_img = day_imgs[1] if len(day_imgs) > 1 else ""
            s2_img = day_imgs[2] if len(day_imgs) > 2 else ""
        else:
            hero_img = ""
            carousel_imgs = []
            s1_img = ""
            s2_img = ""
            
        dest_day_indices[slug] = day_idx + 1
        
        # Always use single layout for itinerary as requested
        layout_type = "single"


        layout_images = {
            "hero": hero_img,
            "small-1": s1_img,
            "small-2": s2_img,
            "carousel": carousel_imgs
        }
        
        # Apply user image overrides if present
        if f"day_img_hero_{day_num}" in edited:
            layout_images["hero"] = edited[f"day_img_hero_{day_num}"]
        if f"day_img_small1_{day_num}" in edited:
            layout_images["small-1"] = edited[f"day_img_small1_{day_num}"]
        if f"day_img_small2_{day_num}" in edited:
            layout_images["small-2"] = edited[f"day_img_small2_{day_num}"]
            
        is_alternate = (i % 2 != 0)
        
        day_with_layout = {
            **day_data, 
            "layout_type": layout_type, 
            "layout_images": layout_images,
            "is_alternate": is_alternate,
            "segment_city": city
        }
        flat_days.append(day_with_layout)
        
    return flat_days

# ── Context builder (pure fn — no I/O) ───────────────────────────────────────

def _build_ctx(quotation_id, payload: "TourQuotationPayload", hero_image_url, destinations: list[dict], lang: str = "en", template_name: str = "vietnam_luxury_brosure.html", brand: dict = None):
    """Build template context. Shared by /quotations (landingpage) and /quotations/{id}/pdf."""
    default_img = "/assets/vietnam-safar-logo.png"
    manual_override = _load_quotation_manual_override(quotation_id)
    lang_override = _lang_override(manual_override, lang)
    
    # Defaults for seller/contact
    seller_name  = "Vietnam Safar – Discovery Asia Travel Group"
    seller_email = "sales@vietnamsafar.vn"
    seller_phone = "+84 911 538 738"
    if brand:
        if brand.get("id") == "capella_travel":
            seller_name = "Capella Travel"
            seller_email = "sales@capellatravel.com"
        elif brand.get("id") == "selvara":
            seller_name = "Selvara Journeys"
            seller_email = "sales@selvarajourneys.com"

    # Resolve key display strings from new Spec 36 schema
    tour_title    = truncate_text(payload.landingpageContent.heroSection.subtitle, 70)
    prepared_for  = truncate_text(payload.journeyGlance.guestProfile, 60)
    
    # Calculate duration
    days_count = len(payload.itinerary)
    nights_count = max(0, days_count - 1)
    duration_lbl  = format_duration_label(days_count, nights_count, lang)
    
    # Travel dates - fallback to hotel plan if checkInDate is available, otherwise placeholder
    travel_dates = "Flexible Dates"
    quotation_start_date = ""
    if payload.hotelPlan.hotels:
        start_date = payload.hotelPlan.hotels[0].checkInDate
        end_date = payload.hotelPlan.hotels[-1].checkOutDate
        if start_date and end_date:
            travel_dates = format_display_date_range_for_lang(start_date, end_date, lang)
            quotation_start_date = start_date
            
    guests_txt    = truncate_text(payload.journeyGlance.guestProfile, 100)
    
    timeline_days = _build_timeline_days(quotation_id, payload, lang, manual_override, start_date_str=quotation_start_date)
    route_stops = _build_route_stops_from_timeline(timeline_days)
    route_list = _compress_route_sequence([stop["displayName"] for stop in route_stops])
    route_txt = canonicalize_place_names_in_text(
        lang_override.get("route_txt") or " \u2013 ".join(route_list),
        lang,
    )
    
    nationality   = truncate_text(payload.journeyGlance.market, 60)
    travel_style  = truncate_text(payload.journeyGlance.partnerNote, 100)

    # Estimate guest count
    guests_count = 1
    import re
    m = re.search(r'(\d+)\s+adult', guests_txt, re.IGNORECASE)
    if m:
        guests_count = int(m.group(1))

    # Construct pricing context from agent custom pricing dict or default
    price_options = []
    total_price = ""
    price_per_pax = ""
    grand_total_num = 0.0
    currency = "USD"

    # Check if pricing is custom pricing context dict (from pricing engine)
    if isinstance(payload.pricing, dict) or hasattr(payload.pricing, "totalPriceUsd"):
        p_dict = payload.pricing if isinstance(payload.pricing, dict) else payload.pricing.model_dump()
        currency = p_dict.get("currency", "USD")
        grand_total_num = p_dict.get("totalPriceUsd", 0.0)
        
        price_per_person = grand_total_num / max(1, guests_count)
        
        price_per_pax = format_currency_display(price_per_person, currency, lang, per_person=True)
        total_price = format_currency_display(grand_total_num, currency, lang)
        
        price_options = [{
            "hotelCategory": truncate_text(payload.journeyGlance.hotelStandard, 80),
            "optionName": "Main confirmed option",
            "pricePerPerson": {
                "amount": price_per_person,
                "currency": currency,
                "displayText": price_per_pax,
                "isFromPrice": False
            },
            "totalPrice": {
                "amount": grand_total_num,
                "currency": currency,
                "displayText": total_price,
                "isFromPrice": False
            },
            "isConfirmedMainOption": True,
            "isAlternativeOption": False,
            "notes": ["Calculated based on actual supplier costs"]
        }]
    else:
        # Standard Pricing model
        currency = payload.pricing.currency
        for opt in payload.pricing.priceOptions:
            price_per_person_amt = opt.amount or 0.0
            total_price_amt = price_per_person_amt * guests_count
            
            p_pax_txt = format_currency_display(price_per_person_amt, currency, lang, per_person=True)
            tot_txt = format_currency_display(total_price_amt, currency, lang)
            
            cleaned_opt_notes = opt.notes
            if cleaned_opt_notes:
                import re
                pattern = r'^\s*(?:USD|EUR|INR|GBP|VND|[$€₹đ])?\s*[\d,.]+\s*(?:USD|EUR|INR|GBP|VND|[$€₹đ])?\s*(?:per person|per pax|/person|/pax)?\s+on\s+'
                cleaned_opt_notes = re.sub(pattern, '', cleaned_opt_notes, flags=re.IGNORECASE).strip()
            
            price_options.append({
                "hotelCategory": truncate_text(opt.label, 80),
                "optionName": truncate_text(cleaned_opt_notes, 150) if cleaned_opt_notes else "",
                "pricePerPerson": {
                    "amount": price_per_person_amt,
                    "currency": currency,
                    "displayText": p_pax_txt,
                    "isFromPrice": False
                },
                "totalPrice": {
                    "amount": total_price_amt,
                    "currency": currency,
                    "displayText": tot_txt,
                    "isFromPrice": False
                },
                "isConfirmedMainOption": True,
                "isAlternativeOption": False,
                "notes": [truncate_text(opt.notes, 150)] if opt.notes else []
            })
        grand_total_num = payload.pricing.grandTotal or 0.0
        total_price = format_currency_display(grand_total_num, currency, lang)

    default_inclusions = [
        {"title": "Handpicked Accommodation", "desc": "Carefully selected hotels and stays as detailed in your journey proposal."},
        {"title": "Private Transportation", "desc": "Private ground transportation and scheduled transfers throughout the journey, as specified in the itinerary."},
        {"title": "Curated Experiences", "desc": "Entrance arrangements and experiences included as outlined in your itinerary."},
        {"title": "Expert Local Guidance", "desc": "Services of carefully selected, licensed local guides where specified."},
        {"title": "Dining Experiences", "desc": "Meals and dining arrangements as detailed in the itinerary."},
        {"title": "Journey Connections", "desc": "Domestic flights, rail journeys, ferries, or other transportation included where specifically stated in the itinerary."}
    ]
    default_exclusions = [
        "International flights",
        "Visa fees and travel documentation",
        "Travel insurance",
        "Personal expenses",
        "Optional experiences not specified in the itinerary",
        "Tips and gratuities",
        "Any services not expressly listed as included"
    ]

    # Extract inclusions from itinerary day mainInclusions dynamically, unless quote override exists
    if lang_override.get("inclusions"):
        inc_lines = [canonicalize_place_names_in_text(truncate_text(x, 160), lang) for x in lang_override["inclusions"]]
    else:
        inc_lines = []
        for d in payload.itinerary:
            if d.mainInclusions and d.mainInclusions not in inc_lines:
                inc_lines.append(d.mainInclusions)
        if not inc_lines:
            inc_lines = [
                {
                    "title": translate_filter(item["title"], lang),
                    "desc": translate_filter(item["desc"], lang)
                } for item in default_inclusions
            ]
        else:
            inc_lines = [canonicalize_place_names_in_text(translate_filter(truncate_text(x, 120), lang), lang) for x in inc_lines]

    if lang_override.get("exclusions"):
        exc_lines = [canonicalize_place_names_in_text(truncate_text(x, 160), lang) for x in lang_override["exclusions"]]
    else:
        exc_lines = [canonicalize_place_names_in_text(translate_filter(truncate_text(x, 120), lang), lang) for x in default_exclusions]

    inclusions_title = translate_filter("What Your Journey Includes", lang)
    inclusions_lede = translate_filter("Your journey has been thoughtfully arranged to ensure a seamless and comfortable experience throughout.", lang)
    exclusions_title = translate_filter("Exclusions", lang)
    exclusions_lede = translate_filter("To keep your journey transparent and clearly defined, the following are not included unless specifically stated otherwise:", lang)

    # Overview paragraphs
    overview_paras = []
    if getattr(payload, "programOverview", None) and payload.programOverview.paragraphs:
        overview_paras = [canonicalize_place_names_in_text(truncate_text(p, 500), lang) for p in payload.programOverview.paragraphs]
        overview_heading = truncate_text(payload.programOverview.heading or "PROGRAM OVERVIEW", 60)
    elif payload.quotationNarrative:
        paras = [p.strip() for p in payload.quotationNarrative.split('\n') if p.strip()]
        overview_paras = [canonicalize_place_names_in_text(truncate_text(p, 500), lang) for p in paras]
        overview_heading = "PROGRAM OVERVIEW"
    
    if not overview_paras:
        overview_paras = ["A refined travel experience designed for your journey."]
        overview_heading = "PROGRAM OVERVIEW"
        
    lede = canonicalize_place_names_in_text(truncate_text(overview_paras[0], 500), lang)

    # Fallback to local parsing if destinations list is empty (e.g. offline/sandbox test)
    if not destinations and payload.itinerary:
        from image_selector import resolve_slug_locally, get_random_image_for_province, get_all_images_for_province
        seen_names = set()
        for day in payload.itinerary:
            if day.destination and day.destination not in seen_names:
                seen_names.add(day.destination)
                slug = resolve_slug_locally(day.destination)
                if slug:
                    dest_dict = {
                        "name": day.destination,
                        "slug": slug,
                        "image_url": get_random_image_for_province(slug),
                        "images": get_all_images_for_province(slug)
                    }
                    destinations.append(dest_dict)

    import os
    import random

    def _local_slug_lookup(text: str) -> str | None:
        if not text:
            return None
        normalized = str(text).strip().lower()
        slug_map = {
            "hanoi": "ha-noi", "hà nội": "ha-noi", "ha noi": "ha-noi", "hanoï": "ha-noi",
            "ninh binh": "ninh-binh", "ninh bình": "ninh-binh", "ninhbinh": "ninh-binh",
            "halong bay": "quang-ninh", "halong": "quang-ninh", "ha long": "quang-ninh", "quảng ninh": "quang-ninh", "vịnh hạ long": "quang-ninh", "vinh ha long": "quang-ninh",
            "sapa": "lao-cai", "sa pa": "lao-cai", "lào cai": "lao-cai", "lao cai": "lao-cai", "laocai": "lao-cai"
        }
        for k, v in slug_map.items():
            if k in normalized:
                return v
        return None

    def _find_real_image_for_province(slug: str, fallback_img: str = "/assets/vietnam-safar-logo.png") -> str:
        if not slug or slug == "unknown":
            return fallback_img
        folder_path = os.path.join("assets", slug)
        if os.path.isdir(folder_path):
            valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
            files = [
                f for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f)) and os.path.splitext(f)[1].lower() in valid_exts
            ]
            if files:
                return f"/assets/{slug}/{random.choice(files)}"
        return fallback_img

    def _find_all_real_images_for_province(slug: str, fallback_img: str = "/assets/vietnam-safar-logo.png") -> list[str]:
        if not slug or slug == "unknown":
            return [fallback_img]
        folder_path = os.path.join("assets", slug)
        if os.path.isdir(folder_path):
            valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
            files = sorted([
                f for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f)) and os.path.splitext(f)[1].lower() in valid_exts
            ])
            if files:
                return [f"/assets/{slug}/{f}" for f in files]
        return [fallback_img]

    translated_destinations = []
    for d in destinations:
        d_copy = d.copy()
        raw_name = d_copy.get("name", "")
        d_copy["name"] = localize_place_name(raw_name, lang)
        
        # Resolve slug for the destination
        slug = d_copy.get("slug")
        if not slug or slug == "unknown":
            slug = _local_slug_lookup(raw_name) or _local_slug_lookup(d_copy.get("name"))

        image_url = _extract_image_url(d_copy.get("image_url"), default_img)
        raw_images = d_copy.get("images") or []
        images = [
            _extract_image_url(img, default_img)
            for img in raw_images
            if _extract_image_url(img, default_img)
        ]

        # If mock path or file doesn't exist, replace with real image
        if slug and slug != "unknown":
            is_mock_url = "mock-" in image_url
            file_exists = True
            if image_url.startswith("/assets/"):
                file_path = image_url.lstrip("/")
                if not os.path.exists(file_path):
                    file_exists = False
            
            if is_mock_url or not file_exists or image_url == default_img:
                real_img = _find_real_image_for_province(slug, default_img)
                if real_img != default_img:
                    image_url = real_img

            real_images = []
            for img in images:
                is_mock = "mock-" in img
                f_exists = True
                if img.startswith("/assets/"):
                    f_path = img.lstrip("/")
                    if not os.path.exists(f_path):
                        f_exists = False
                if not is_mock and f_exists and img != default_img:
                    real_images.append(img)
            
            if not real_images:
                real_prov_imgs = _find_all_real_images_for_province(slug, default_img)
                if real_prov_imgs and real_prov_imgs[0] != default_img:
                    real_images = real_prov_imgs
            
            if not real_images:
                real_images = [image_url]
                
            images = real_images

        d_copy["image_url"] = image_url
        d_copy["images"] = images
        d_copy["slug"] = slug or "unknown"
        translated_destinations.append(d_copy)
    destinations = translated_destinations

    # Gallery helpers
    def _d_img(i): return destinations[i].get("image_url", default_img) if i < len(destinations) else default_img
    def _d_name(i): return truncate_text(destinations[i].get("name", ""), 40) if i < len(destinations) else ""

    img_0 = _extract_image_url(hero_image_url, default_img)
    if "mock-" in img_0 or (img_0.startswith("/assets/") and not os.path.exists(img_0.lstrip("/"))):
        import re
        hero_slug = None
        m = re.search(r'mock-([^./\s]+)', img_0)
        if m:
            hero_slug = _local_slug_lookup(m.group(1))
        if not hero_slug and destinations:
            hero_slug = destinations[0].get("slug")
        if hero_slug and hero_slug != "unknown":
            real_hero = _find_real_image_for_province(hero_slug, default_img)
            if real_hero != default_img:
                img_0 = real_hero

    img_1 = _d_img(0)
    img_2 = _d_img(1)
    img_3 = _d_img(2)
    img_4 = _d_img(3)

    # ── Deduplicated Chapter Divider Images ─────────────────────────────────
    used_divider_imgs = {img_0, img_1}

    # Collect all available real destination images
    all_dest_images = []
    for d in destinations:
        for im in d.get("images", []):
            if im and im != default_img and im not in all_dest_images:
                all_dest_images.append(im)
    for d in destinations:
        s = d.get("slug")
        if s:
            p_imgs = _find_all_real_images_for_province(s, default_img)
            for im in p_imgs:
                if im and im != default_img and im not in all_dest_images:
                    all_dest_images.append(im)

    # 1. Pick img_itinerary_divider (landscape hero image, prefer 2nd destination or unused image)
    img_itinerary_divider = ""
    if len(destinations) > 1 and destinations[1].get("images"):
        cand = [im for im in destinations[1]["images"] if im not in used_divider_imgs]
        if cand:
            img_itinerary_divider = cand[0]
    if not img_itinerary_divider:
        cand = [im for im in all_dest_images if im not in used_divider_imgs]
        if cand:
            img_itinerary_divider = cand[0]
        else:
            img_itinerary_divider = img_1 or img_0
    used_divider_imgs.add(img_itinerary_divider)

    # 2. Pick img_hotel_divider (sanctuary/nature hero image, prefer 3rd destination or unused image)
    img_hotel_divider = ""
    if len(destinations) > 2 and destinations[2].get("images"):
        cand = [im for im in destinations[2]["images"] if im not in used_divider_imgs]
        if cand:
            img_hotel_divider = cand[0]
    if not img_hotel_divider:
        cand = [im for im in all_dest_images if im not in used_divider_imgs]
        if cand:
            img_hotel_divider = cand[0]
        else:
            img_hotel_divider = img_2 or img_0
    used_divider_imgs.add(img_hotel_divider)

    # User edit overrides
    edited_fields = manual_override.get("edited_fields", {}) if manual_override else {}
    if edited_fields.get("img_itinerary_divider"):
        img_itinerary_divider = edited_fields["img_itinerary_divider"]
    if edited_fields.get("img_hotel_divider"):
        img_hotel_divider = edited_fields["img_hotel_divider"]

    # Highlight experiences — first 3 itinerary days
    experiences = [
        {"num": f"{i+1:02d}", "title": truncate_text(f"{translate_filter('Day', lang)} {day.dayNumber}: {localize_place_name(day.destination, lang)}", 80),
         "desc": canonicalize_place_names_in_text(truncate_text(day.summary, 160), lang)}
        for i, day in enumerate(payload.itinerary[:3])
    ]
    while len(experiences) < 3:
        experiences.append({"num": f"{len(experiences)+1:02d}", "title": "Premium Experience",
                            "desc": "A carefully curated moment in this journey."})

    # Price conditions note
    price_cond_paras = [
        "Rates are indicative and subject to reconfirmation at the time of booking.",
        "Final price may vary depending on hotel availability, resort category, cruise selection, domestic flight fare, rooming arrangement, child policy, and final travel services confirmed."
    ]
    price_cond_paras = [translate_filter(truncate_text(x, 250), lang) for x in price_cond_paras]

    # --- GAP ALIGNMENT LOGIC ---
    show_muslim_care = False
    
    # Check meal preference in journeyGlance
    if payload.journeyGlance and payload.journeyGlance.mealPreference:
        if "halal" in payload.journeyGlance.mealPreference.lower() or "no pork" in payload.journeyGlance.mealPreference.lower():
            show_muslim_care = True
            
    # Check nationality / market (case-insensitive substring checks)
    muslim_keywords = ["saudi", "arabia", "uae", "emirates", "qatar", "kuwait", "oman", "bahrain", "gcc", "middle east", "malaysia", "indonesia", "egypt", "jordan", "turkey", "halal", "muslim"]
    
    nat_str = (nationality or "").lower()
    if any(k in nat_str for k in muslim_keywords):
        show_muslim_care = True

    # Journey at a Glance defaults/fallbacks
    glance = payload.journeyGlance
    glance_market = truncate_text(glance.market, 60)
    glance_profile = truncate_text(glance.guestProfile, 100)
    glance_standard = truncate_text(glance.hotelStandard, 80)
    glance_meals = truncate_text(glance.mealPreference, 100)
    glance_price_type = truncate_text(glance.priceType, 60)
    glance_tour_code = truncate_text(glance.tourCode, 40)
    glance_flights = truncate_text(glance.domesticFlights, 100)
    glance_basis = truncate_text(glance.priceBasis, 80)
    glance_partner_note = truncate_text(glance.partnerNote, 100)
    glance_validity = truncate_text(glance.validity, 60)

    # Why works defaults/fallbacks
    why = payload.whyWorks
    why_private = truncate_text(why.privateFlexible, 250)
    why_comfort = truncate_text(why.comfort, 250)
    why_muslim = truncate_text(why.muslimFriendly, 250)
    why_balanced = truncate_text(why.balancedHighlights, 250)

    # Selected Hotel Plan defaults/fallbacks
    hotel_plan_items = []
    hotel_room_notes = ""
    if payload.hotelPlan:
        for idx, item in enumerate(payload.hotelPlan.hotels):
            details = get_luxury_hotel_details(
                item.hotelArrangement, 
                item.destination, 
                item.checkInDate, 
                item.checkOutDate,
                index=idx,
                lang=lang
            )
            hotel_plan_items.append(canonicalize_place_names_in_data(details, lang))
        hotel_room_notes = truncate_text(normalize_room_note(payload.hotelPlan.roomNotes or "", lang), 200)

    stay_segments = _build_stay_segments_from_timeline(timeline_days, hotel_plan_items, lang)

    # Optional Enhancements defaults/fallbacks
    opt_enhancements = []
    if payload.optionalEnhancements:
        for item in payload.optionalEnhancements:
            opt_dict = item.model_dump(mode="json")
            opt_dict["name"] = truncate_text(opt_dict.get("name"), 80)
            opt_dict["description"] = truncate_text(opt_dict.get("description"), 200)
            opt_enhancements.append(opt_dict)

    # Booking Terms defaults/fallbacks
    b_terms = payload.bookingTerms
    term_deposit = truncate_text(b_terms.deposit, 300)
    term_balance = truncate_text(b_terms.balance, 300)
    term_cancellation = truncate_text(b_terms.cancellation, 300)
    term_confirmation = truncate_text(b_terms.confirmation, 300)

    # Finalization defaults/fallbacks
    final = payload.finalization
    final_req = [truncate_text(final.finalDetailsRequired, 300)]
    final_after = [truncate_text(final.afterConfirmation, 300)]

    mapped_itinerary = timeline_days

    # Multi-language support for dynamic itinerary subtitle
    days_cnt = len(payload.itinerary)
    if lang == "vi":
        itinerary_p_val = f"Hành trình riêng tư {duration_lbl} của bạn — {days_cnt} ngày, được thiết kế tỉ mỉ."
    elif lang == "ar":
        itinerary_p_val = f"رحلتك الخاصة {duration_lbl} — {days_cnt} يوماً، تم تصميمها بعناية."
    else:
        itinerary_p_val = f"Your private {duration_lbl} journey — {days_cnt} days, carefully crafted."

    # Journey investment header translation
    pricing_h2_title = translate_filter("Journey Investment", lang)
    pricing_h2_val = f"{pricing_h2_title}: {total_price}" if total_price else ""

    # Generate static map URL based on route stops or fall back to destinations
    coords_list = []
    for stop in route_stops:
        normalized = stop["destination"].lower().strip()
        matched = None
        for name, coords in SLUG_COORDS.items():
            if normalized == name:
                matched = coords
                break
        if matched is None:
            for slug, coords in SLUG_COORDS.items():
                if normalized in (slug, slug.replace("-", " ")):
                    matched = coords
                    break
        if matched and (not coords_list or coords_list[-1] != tuple(matched)):
            coords_list.append(tuple(matched))
    if not coords_list:
        for d in destinations:
            slug = d.get("slug")
            if slug and slug in SLUG_COORDS:
                lat, lng = SLUG_COORDS[slug]
                if not coords_list or coords_list[-1] != (lat, lng):
                    coords_list.append((lat, lng))

    static_map_url = ""
    if coords_list:
        markers = []
        for idx, (lat, lng) in enumerate(coords_list):
            markers.append(f"{lng},{lat},pm2gnm{idx+1}")
        pt_param = "~".join(markers)
        
        pl_coords = []
        for lat, lng in coords_list:
            pl_coords.append(f"{lng},{lat}")
        pl_param = f"c:17412eff,w:4,{','.join(pl_coords)}"
        
        static_map_url = f"https://static-maps.yandex.ru/1.x/?l=map&size=650,350&lang=en_US&pt={pt_param}"
        if len(coords_list) > 1:
            static_map_url += f"&pl={pl_param}"

    client_i18n = {
        "notification_title": translate_filter("Enable Notifications", lang),
        "previous_image": translate_filter("Previous image", lang),
        "next_image": translate_filter("Next image", lang),
        "go_to_slide": translate_filter("Go to slide", lang),
        "editing": translate_filter("Editing", lang),
        "publish_to_web": translate_filter("Publish to Web", lang),
        "publishing": translate_filter("Publishing...", lang),
        "committing_to_github": translate_filter("Committing to GitHub...", lang),
        "translate_block": translate_filter("Translate this block", lang),
        "change": translate_filter("Change", lang),
        "remove_block": translate_filter("Remove this block", lang),
        "remove_block_confirm": translate_filter("Remove this block? This action cannot be undone.", lang),
        "language_names": {
            "en": translate_filter("English", lang),
            "ar": translate_filter("Arabic", lang),
            "vi": translate_filter("Vietnamese", lang),
        },
        "test_notification_title": translate_filter("Itinerary Update", lang),
        "test_notification_body": translate_filter(
            "Your private guide has been assigned: Mr. Minh (Phone: +84 911 538 738).",
            lang,
        ),
        "enable_notifications_browser": translate_filter(
            "Please enable notifications in your browser settings to receive updates.",
            lang,
        ),
    }

    hero_meta_1 = lang_override.get("hero_meta_1") or f"{days_count} DAYS • {nights_count} NIGHTS • {guests_txt.upper() if guests_txt else 'FAMILY VACATION'}"
    letter_greeting = lang_override.get("letter_greeting") or f"Dear {prepared_for},"
    letter_intro = lang_override.get("letter_intro") or (
        f"I am delighted to present this privately arranged journey: {overview_heading}, created for "
        f"{guests_txt or 'two guests'} travelling from {travel_dates}. The route unfolds from {route_txt}."
    )
    letter_body_p2 = lang_override.get("letter_body_p2") or (
        "The programme has been considered around a gentler family rhythm: early check-in in Hanoi, "
        "private guiding and transfers, a premium overnight train cabin, and enough space between active days "
        "to pause. Dining, room arrangements and transitions have been planned with care, without adding "
        "unnecessary movement."
    )
    letter_outro = lang_override.get("letter_outro") or (
        "Please review the journey as a starting point for a personal conversation. Every final detail can be "
        "refined around your preferred pace, room choices and family priorities."
    )
    letter_sign_off = lang_override.get("letter_sign_off") or "Anh Son Le"
    letter_sender = lang_override.get("letter_sender") or "Your Journey Designer"

    return {
        # IDs & images
        "quotation_id":   quotation_id,
        "static_map_url": static_map_url,
        "img_0": img_0, "img_1": img_1, "img_2": img_2, "img_3": img_3, "img_4": img_4,
        "img_itinerary_divider": img_itinerary_divider,
        "img_hotel_divider":     img_hotel_divider,
        "destinations":   destinations,
        # Hero / header
        "quotation_title": truncate_text(payload.landingpageContent.heroSection.headline, 100),
        "tour_title":      tour_title,
        "kicker":          f"{translate_filter('Private Luxury Quotation', lang)} \u2012 {duration_lbl} \u2012 {travel_dates}",
        "lede":            lede,
        # Guest & trip meta
        "customer_name":   prepared_for,
        "nationality":     nationality,
        "travel_style":    travel_style,
        "guests_txt":      guests_txt,
        "route_txt":       route_txt,
        "duration_label":  duration_lbl,
        "travel_dates":    travel_dates,
        "hotel_options":   [],
        "confirmed_option": "",
        # Seller / contact
        "seller_name":    seller_name,
        "seller_email":   seller_email,
        "contact":        seller_phone,
        "contact_web":    brand.get("domain") if brand else "www.vietnamsafar.vn",
        "contact_phone":  seller_phone,
        "hero_meta_1":    hero_meta_1,
        # Quotation ref
        "quotation_number": payload.quotationNumber or quotation_id,
        "quotation_date":   quotation_start_date or travel_dates,
        "travel_dates_raw": quotation_start_date,
        "valid_until":      glance_validity,
        # Strip badges
        "strip_duration":  duration_lbl,
        "strip_best_for":  nationality or "B2B Partners",
        "strip_pace":      "Relaxed",
        "strip_service":   "Private",
        # Overview section
        "overview_heading": translate_filter(overview_heading, lang),
        "overview_h2":      f"{translate_filter('Prepared for', lang)}: {prepared_for} \u2014 {tour_title}",
        "overview_p":       canonicalize_place_names_in_text(payload.quotationNarrative, lang),
        "overview_paras":   overview_paras,
        # Experiences (first 3 days)
        "experiences":      experiences,
        # Gallery section
        "route_map_h2": translate_filter(lang_override.get("route_map_h2") or "Your Journey, Mapped", lang),
        "route_map_p":  translate_filter(lang_override.get("route_map_p") or "An interactive map showing your curated path through Vietnam's iconic landmarks and luxury stopovers. Click on a destination in the list or the map to explore highlights.", lang),
        "journey_h2":   translate_filter(lang_override.get("journey_h2") or "Destination imagery woven into the quotation.", lang),
        "journey_p":    translate_filter(lang_override.get("journey_p") or "Cinematic destination panels crafted for a premium travel proposal.", lang),
        "gal1_label":   translate_filter("Highlight", lang) if len(destinations) > 0 else translate_filter("Destination", lang),
        "gal1_title":   _d_name(0), "gal2_label": translate_filter("Destination", lang), "gal2_title": _d_name(1),
        "gal3_label":   translate_filter("Experience", lang), "gal3_title": _d_name(2), "gal4_label": translate_filter("Journey", lang), "gal4_title": _d_name(3),
        # Itinerary section
        "itinerary_h2": translate_filter("Day-by-Day Journey Program", lang),
        "itinerary_p":  itinerary_p_val,
        "itinerary":    mapped_itinerary,
        "timeline_days": mapped_itinerary,
        "route_stops": route_stops,
        "stay_segments": stay_segments,
        "itinerary_days": _build_itinerary_days_flat(mapped_itinerary, stay_segments, lang, manual_override),
        # Pricing section
        "currency":       currency,
        "pricing_title":  translate_filter("Journey Investment", lang),
        "pricing_basis":  glance_basis,
        "price_options":  price_options,
        "price_per_pax":  price_per_pax,
        "total_price":    total_price,
        "grand_total":    grand_total_num,
        "subtotal":       grand_total_num,
        "tax_total":      0.0,
        "pricing_h2":     pricing_h2_val,
        "pricing_p":      f"{translate_filter('Total', lang)}: {guests_txt}. {translate_filter('Currency', lang)}: {currency}. {translate_filter('Final rates subject to reconfirmation.', lang)}",
        # Inclusions / exclusions
        "inclusions":     inc_lines,
        "exclusions":     exc_lines,
        "inclusions_title": inclusions_title,
        "inclusions_lede": inclusions_lede,
        "exclusions_title": exclusions_title,
        "exclusions_lede": exclusions_lede,
        # Price conditions
        "price_cond_paras": [] if lang_override.get("hide_price_conditions") else price_cond_paras,
        "payment_terms":    translate_filter("Refer to Booking & Payment terms below.", lang),
        "terms_p":          price_cond_paras[0] if price_cond_paras else "",
        "letter_greeting":  letter_greeting,
        "letter_intro":     letter_intro,
        "letter_body_p2":   letter_body_p2,
        "letter_outro":     letter_outro,
        "letter_sign_off":  letter_sign_off,
        "letter_sender":    letter_sender,
        # CTA
        "cta_h2": lang_override.get("cta_h2", translate_filter("Confirm dates, then refine the luxury layer.", lang)),
        "cta_p":  translate_filter("Share travel dates, preferred hotel tier, rooming list and any dietary or mobility requirements. We will reconfirm availability and return a finalized quotation.", lang),
        # Footer
        "footer_text": f"{tour_title} — {translate_filter('Luxury quotation prepared for', lang)} {prepared_for}.",
        # Raw quotation (for reference / debugging)
        "raw_quotation":  "",
        # GAP ALIGNMENT context
        "show_muslim_care": show_muslim_care,
        "glance_market": glance_market,
        "glance_profile": glance_profile,
        "glance_standard": glance_standard,
        "glance_meals": glance_meals,
        "glance_price_type": glance_price_type,
        "glance_tour_code": glance_tour_code,
        "glance_flights": glance_flights,
        "glance_basis": glance_basis,
        "glance_partner_note": glance_partner_note,
        "glance_validity": glance_validity,
        "why_private": why_private,
        "why_comfort": why_comfort,
        "why_muslim": why_muslim,
        "why_balanced": why_balanced,
        "hotels": hotel_plan_items,
        "room_notes": hotel_room_notes,
        "optional_enhancements": opt_enhancements,
        "term_deposit": term_deposit,
        "term_balance": term_balance,
        "term_cancellation": term_cancellation,
        "term_confirmation": term_confirmation,
        "final_req": final_req,
        "final_after": final_after,
        "show_hotel_intro": not lang_override.get("hide_hotel_intro", False),
        "show_designer_section": not lang_override.get("hide_designer_section", False),
        "lang": lang,
        "template_name": template_name,
        "brand": brand or BRANDS["vietnam_safar"],
        "translation_status": _load_translation_status(quotation_id, default_lang=lang),
        "client_i18n": client_i18n,
    }
    ctx = canonicalize_place_names_in_data(ctx, lang)
    return ctx


def _load_ctx(quotation_id: str) -> dict | None:
    """Load ctx from memory store or persisted ctx.json (cross-instance resilience)."""
    entry = quotations.get(quotation_id)
    if entry and entry.get("ctx"):
        return entry["ctx"]
    ctx_path = os.path.join("published", quotation_id, "ctx.json")
    if os.path.isfile(ctx_path):
        with open(ctx_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _load_itinerary_ctx(itinerary_id: str) -> dict | None:
    """Load itinerary ctx from memory store or persisted ctx.json (cross-instance resilience)."""
    entry = itineraries.get(itinerary_id)
    if entry and entry.get("ctx"):
        return entry["ctx"]
    ctx_path = os.path.join("published", itinerary_id, "ctx.json")
    if os.path.isfile(ctx_path):
        with open(ctx_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _build_itinerary_ctx(itinerary_id: str, payload: DetailItineraryPayload, hero_image_url: str, destinations: list[dict], lang: str = "en", template_name: str = "detail_itinerary_landingpage_template.html"):
    """Build rendering context for the detailed itinerary landing page."""
    default_img = "/assets/vietnam-safar-logo.png"
    seller = payload.seller
    seller_name  = (seller.companyName if seller else None) or "Vietnam Safar – Discovery Asia Travel Group"
    seller_email = (seller.email if seller else None) or "sales@vietnamsafar.vn"
    seller_phone = (seller.phone if seller else None) or "+84 911 538 738"

    tour_title    = truncate_text(payload.tourTitle, 70)
    prepared_for  = truncate_text(payload.preparedFor, 60)
    duration_lbl  = payload.duration.label or f"{payload.duration.days}D{payload.duration.nights}"
    travel_dates  = payload.travelDates.displayText or f"{payload.travelDates.startDate} – {payload.travelDates.endDate}"
    guests_txt    = truncate_text(payload.guests.displayText or f"{payload.guests.totalGuests} guests", 100)
    route_txt     = " – ".join(payload.route)
    nationality   = truncate_text(payload.nationality or "", 60)
    travel_style  = truncate_text(" | ".join(payload.travelStyle) if payload.travelStyle else "Private", 100)

    # Narrative overview
    overview_paras = [truncate_text(p, 500) for p in payload.programOverview.paragraphs] if payload.programOverview and payload.programOverview.paragraphs else []
    overview_heading = truncate_text(payload.programOverview.heading or "PROGRAM OVERVIEW", 60) if payload.programOverview else "PROGRAM OVERVIEW"
    lede = truncate_text(overview_paras[0] if overview_paras else "A detailed booking itinerary crafted for your journey.", 500)

    # Translate destinations name for multi-language
    translated_destinations = []
    for d in destinations:
        d_copy = d.copy()
        raw_name = d_copy.get("name", "")
        d_copy["name"] = translate_filter(raw_name, lang)
        translated_destinations.append(d_copy)
    destinations = translated_destinations

    # Translate destinations name for multi-language
    translated_destinations = []
    for d in destinations:
        d_copy = d.copy()
        raw_name = d_copy.get("name", "")
        d_copy["name"] = translate_filter(raw_name, lang)
        translated_destinations.append(d_copy)
    destinations = translated_destinations

    # Gallery helpers
    def _d_img(i): return destinations[i].get("image_url", default_img) if i < len(destinations) else default_img
    def _d_name(i): return truncate_text(destinations[i].get("name", ""), 40) if i < len(destinations) else ""

    img_0 = hero_image_url
    img_1 = _d_img(0)
    img_2 = _d_img(1)
    img_3 = _d_img(2)
    img_4 = _d_img(3)

    # Highlight experiences — first 3 itinerary days
    experiences = []
    for i, day in enumerate(payload.itinerary[:3]):
        title = day.title
        if not title or title.lower().startswith("explore "):
            city = day.destinations[0] if (day.destinations and day.destinations[0]) else (day.overnight or "Vietnam")
            title = get_luxury_day_title(city, day.dayNumber, lang)
        else:
            title = truncate_text(title, 80)
        desc = truncate_text(day.description[0] if day.description else f"{translate_filter('Day', lang)} {day.dayNumber} of the journey.", 160)
        experiences.append({"num": f"{i+1:02d}", "title": title, "desc": desc})
    while len(experiences) < 3:
        experiences.append({"num": f"{len(experiences)+1:02d}", "title": "Premium Experience",
                            "desc": "A carefully curated moment in this journey."})

    default_inclusions = [
        {"title": "Handpicked Accommodation", "desc": "Carefully selected hotels and stays as detailed in your journey proposal."},
        {"title": "Private Transportation", "desc": "Private ground transportation and scheduled transfers throughout the journey, as specified in the itinerary."},
        {"title": "Curated Experiences", "desc": "Entrance arrangements and experiences included as outlined in your itinerary."},
        {"title": "Expert Local Guidance", "desc": "Services of carefully selected, licensed local guides where specified."},
        {"title": "Dining Experiences", "desc": "Meals and dining arrangements as detailed in the itinerary."},
        {"title": "Journey Connections", "desc": "Domestic flights, rail journeys, ferries, or other transportation included where specifically stated in the itinerary."}
    ]
    default_exclusions = [
        "International flights",
        "Visa fees and travel documentation",
        "Travel insurance",
        "Personal expenses",
        "Optional experiences not specified in the itinerary",
        "Tips and gratuities",
        "Any services not expressly listed as included"
    ]

    if getattr(payload, "inclusions", None):
        inc_lines = [translate_filter(truncate_text(x, 120), lang) for x in payload.inclusions]
    else:
        inc_lines = [
            {
                "title": translate_filter(item["title"], lang),
                "desc": translate_filter(item["desc"], lang)
            } for item in default_inclusions
        ]
        
    if getattr(payload, "exclusions", None):
        exc_lines = [translate_filter(truncate_text(x, 120), lang) for x in payload.exclusions]
    else:
        exc_lines = [translate_filter(truncate_text(x, 120), lang) for x in default_exclusions]

    inclusions_title = translate_filter("What Your Journey Includes", lang)
    inclusions_lede = translate_filter("Your journey has been thoughtfully arranged to ensure a seamless and comfortable experience throughout.", lang)
    exclusions_title = translate_filter("Exclusions", lang)
    exclusions_lede = translate_filter("To keep your journey transparent and clearly defined, the following are not included unless specifically stated otherwise:", lang)

    # Pricing fields from payload
    main_option   = next((o for o in payload.pricing.priceOptions if o.isConfirmedMainOption), None) if payload.pricing else None
    currency      = payload.pricing.currency if payload.pricing else "USD"
    if main_option:
        price_per_pax = main_option.pricePerPerson.displayText or f"{currency} {main_option.pricePerPerson.amount:,.0f} / person"
        total_price   = main_option.totalPrice.displayText or f"{currency} {main_option.totalPrice.amount:,.0f}"
        grand_total_num = main_option.totalPrice.amount
    else:
        price_per_pax = ""
        total_price   = ""
        grand_total_num = 0.0

    # Map daily services
    days_list = []
    for day in payload.itinerary:
        day_date = day.date
        
        # Match hotels: check-in date <= day_date < check-out date
        day_hotels = []
        for idx, h in enumerate(payload.hotels):
            if h.checkInDate and h.checkOutDate and h.checkInDate <= day_date < h.checkOutDate:  # type: ignore
                h_dict = h.model_dump(mode="json")
                h_dict["_index"] = idx
                h_dict["name"] = truncate_text(h_dict.get("name"), 80)
                h_dict["roomType"] = truncate_text(h_dict.get("roomType"), 80)
                h_dict["destination"] = truncate_text(h_dict.get("destination"), 60)
                h_dict["notes"] = truncate_text(h_dict.get("notes"), 150)
                day_hotels.append(h_dict)
        
        # Match activities
        day_activities = []
        for idx, act in enumerate(payload.activities):
            if act.date == day_date:
                act_dict = act.model_dump(mode="json")
                act_dict["_index"] = idx
                act_dict["activityName"] = truncate_text(act_dict.get("activityName"), 80)
                act_dict["operator"] = truncate_text(act_dict.get("operator"), 80)
                act_dict["notes"] = truncate_text(act_dict.get("notes"), 150)
                day_activities.append(act_dict)

        # Match transfers
        day_transfers = []
        for idx, tx in enumerate(payload.transfers):
            if tx.date == day_date:
                tx_dict = tx.model_dump(mode="json")
                tx_dict["_index"] = idx
                tx_dict["vehicleRequirement"] = truncate_text(tx_dict.get("vehicleRequirement"), 80)
                tx_dict["fromLocation"] = truncate_text(tx_dict.get("fromLocation"), 60)
                tx_dict["toLocation"] = truncate_text(tx_dict.get("toLocation"), 60)
                tx_dict["notes"] = truncate_text(tx_dict.get("notes"), 150)
                day_transfers.append(tx_dict)

        # Match flights
        day_flights = []
        for idx, fl in enumerate(payload.flights):
            if fl.date == day_date:
                fl_dict = fl.model_dump(mode="json")
                fl_dict["_index"] = idx
                fl_dict["flightNumber"] = truncate_text(fl_dict.get("flightNumber"), 30)
                fl_dict["airline"] = truncate_text(fl_dict.get("airline"), 50)
                fl_dict["fromCity"] = truncate_text(fl_dict.get("fromCity"), 40)
                fl_dict["toCity"] = truncate_text(fl_dict.get("toCity"), 40)
                fl_dict["notes"] = truncate_text(fl_dict.get("notes"), 150)
                day_flights.append(fl_dict)

        # Match guides
        day_guides = []
        for idx, gd in enumerate(payload.guides):
            if gd.dates and day_date in gd.dates:
                gd_dict = gd.model_dump(mode="json")
                gd_dict["_index"] = idx
                gd_dict["guideName"] = truncate_text(gd_dict.get("guideName"), 60)
                gd_dict["destination"] = truncate_text(gd_dict.get("destination"), 60)
                gd_dict["notes"] = truncate_text(gd_dict.get("notes"), 150)
                day_guides.append(gd_dict)

        title = day.title
        if not title or title.lower().startswith("explore "):
            city = day.destinations[0] if (day.destinations and day.destinations[0]) else (day.overnight or "Vietnam")
            title = get_luxury_day_title(city, day.dayNumber, lang)
        else:
            title = truncate_text(title, 80)

        days_list.append({
            "dayNumber": day.dayNumber,
            "date": day_date,
            "title": title,
            "description": [truncate_text(d, 350) for d in day.description],
            "overnight": translate_filter(truncate_text(day.overnight, 40), lang),
            "meals": [truncate_text(m, 80) for m in (day.meals or [])],
            "destinations": [translate_filter(truncate_text(dest, 40), lang) for dest in (day.destinations or [])],
            "activities": [truncate_text(act, 120) for act in (day.activities or [])],
            "optionalActivities": [truncate_text(opt, 120) for opt in (day.optionalActivities or [])],
            "notes": [translate_filter(truncate_text(nt, 150), lang) for nt in (day.notes or [])],
            "booked_hotels": day_hotels,
            "booked_activities": day_activities,
            "booked_transfers": day_transfers,
            "booked_flights": day_flights,
            "booked_guides": day_guides,
        })

    # Multi-language support for dynamic itinerary subtitle
    days_cnt = len(payload.itinerary)
    if lang == "vi":
        itinerary_p_val = f"Hành trình riêng tư {duration_lbl} của bạn — {days_cnt} ngày, được thiết kế tỉ mỉ."
    elif lang == "ar":
        itinerary_p_val = f"رحلتك الخاصة {duration_lbl} — {days_cnt} يوماً، تم تصميمها بعناية."
    else:
        itinerary_p_val = f"Your private {duration_lbl} journey — {days_cnt} days, carefully crafted."

    # Journey investment header translation
    pricing_h2_title = translate_filter("Journey Investment", lang)
    pricing_h2_val = f"{pricing_h2_title}: {total_price}" if total_price else ""

    return {
        "itinerary_id":     itinerary_id,
        "img_0": img_0, "img_1": img_1, "img_2": img_2, "img_3": img_3, "img_4": img_4,
        "destinations":     destinations,
        # Hero / header
        "quotation_title":  truncate_text(payload.quotationTitle, 100),
        "tour_title":       tour_title,
        "kicker":           f"{translate_filter('Confirmed Booking Itinerary', lang)} • {duration_lbl} • {travel_dates}",
        "lede":             lede,
        # Guest & trip meta
        "customer_name":    prepared_for,
        "nationality":      nationality,
        "travel_style":     travel_style,
        "guests_txt":       guests_txt,
        "guests_adults":    payload.guests.adults,
        "guests_children":   payload.guests.children,
        "route_txt":        route_txt,
        "duration_label":   duration_lbl,
        "travel_dates":     travel_dates,
        # Seller / contact
        "seller_name":      seller_name,
        "seller_email":     seller_email,
        "contact":          seller_phone,
        "contact_web":      "www.vietnamsafar.vn",
        "contact_phone":    seller_phone,
        "quotation_number": payload.quotationNumber or itinerary_id,
        "valid_until":      "N/A",
        # Overview
        "overview_heading": translate_filter(overview_heading, lang),
        "overview_h2":      f"{prepared_for} — {tour_title}",
        "overview_p":       " ".join(overview_paras),
        "overview_paras":   overview_paras,
        # Experiences
        "experiences":      experiences,
        # Daily Itinerary with matched services
        "itinerary":        days_list,
        # Consolidated list of booked services (useful for summary tabs/cards!)
        "hotels":           [
            {
                **h.model_dump(mode="json"),
                "name": truncate_text(h.name, 80),
                "roomType": truncate_text(h.roomType, 80),
                "destination": truncate_text(h.destination, 60),
                "notes": truncate_text(h.notes, 150)
            } for h in payload.hotels
        ],
        "activities":       [
            {
                **act.model_dump(mode="json"),
                "activityName": truncate_text(act.activityName, 80),
                "operator": truncate_text(act.operator, 80),
                "notes": truncate_text(act.notes, 150)
            } for act in payload.activities
        ],
        "transfers":        [
            {
                **tx.model_dump(mode="json"),
                "vehicleRequirement": truncate_text(tx.vehicleRequirement, 80),
                "fromLocation": truncate_text(tx.fromLocation, 60),
                "toLocation": truncate_text(tx.toLocation, 60),
                "notes": truncate_text(tx.notes, 150)
            } for tx in payload.transfers
        ],
        "flights":          [
            {
                **fl.model_dump(mode="json"),
                "flightNumber": truncate_text(fl.flightNumber, 30),
                "airline": truncate_text(fl.airline, 50),
                "fromCity": truncate_text(fl.fromCity, 40),
                "toCity": truncate_text(fl.toCity, 40),
                "notes": truncate_text(fl.notes, 150)
            } for fl in payload.flights
        ],
        "guides":           [
            {
                **gd.model_dump(mode="json"),
                "guideName": truncate_text(gd.guideName, 60),
                "destination": truncate_text(gd.destination, 60),
                "notes": truncate_text(gd.notes, 150)
            } for gd in payload.guides
        ],
        # Inclusions / exclusions
        "inclusions":       inc_lines,
        "exclusions":       exc_lines,
        "inclusions_title": inclusions_title,
        "inclusions_lede": inclusions_lede,
        "exclusions_title": exclusions_title,
        "exclusions_lede": exclusions_lede,
        "notes":            [truncate_text(x, 200) for x in (payload.notes or [])],
        # Pricing section
        "currency":       currency,
        "pricing_title":  translate_filter(truncate_text(payload.pricing.pricingTitle or "Journey Investment" if payload.pricing else "", 100), lang),
        "pricing_basis":  translate_filter(truncate_text(payload.pricing.basis or "Indicative basis" if payload.pricing else "", 80), lang),
        "price_options":  [
            {
                **o.model_dump(mode="json"),
                "hotelCategory": truncate_text(o.hotelCategory, 80),
                "optionName": truncate_text(o.optionName, 80),
                "notes": [truncate_text(n, 150) for n in o.notes] if o.notes else []
            } for o in payload.pricing.priceOptions
        ] if payload.pricing else [],
        "price_per_pax":  price_per_pax,
        "total_price":    total_price,
        "grand_total":    grand_total_num,
        "subtotal":       payload.pricing.subtotal if payload.pricing else 0.0,
        "tax_total":      payload.pricing.taxTotal if payload.pricing else 0.0,
        "pricing_h2":     pricing_h2_val,
        "pricing_p":      f"{translate_filter('Total', lang)}: {guests_txt}. {translate_filter('Currency', lang)}: {currency}." if total_price else "",
        # Footer
        "footer_text":      f"{tour_title} — {translate_filter('Detailed booking itinerary prepared for', lang)} {prepared_for}.",
        "lang":             lang,
        "template_name":    template_name,
        "translation_status": _load_translation_status(itinerary_id, default_lang=lang),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.post("/quotations/b2c")
async def create_quotation_b2c(request: Request):
    """
    Receives structured B2C quotation data,
    renders a B2C Jinja2 landing page template, stores it, and returns the preview URL.
    """
    body = await request.json()
    log.debug("[/quotations/b2c] Incoming keys: %s", list(body.keys()))

    # Unwrap ChatGPT Action wrapper if present
    data = body.get("params", body)
    log.debug("[/quotations/b2c] Data keys after unwrap: %s", list(data.keys()))
    lang = data.get("language") or data.get("lang") or request.query_params.get("lang") or request.query_params.get("language") or "en"
    if lang not in ("en", "vi", "ar"):
        lang = "en"

    try:
        payload = TourQuotationPayload.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        log.error("[/quotations/b2c] Pydantic validation failed — %d error(s):\n%s",
                  len(errors), json.dumps(errors, indent=2, default=str))
        return JSONResponse(status_code=422, content={"detail": errors,
            "hint": "Field path is in 'loc'. Check which required field is missing."})

    quotation_id = f"quo_{uuid.uuid4().hex[:12]}"

    # ── Extract destinations from route + itinerary for the gallery ──────────
    route_list = []
    for d in payload.itinerary:
        if d.destination and d.destination not in route_list:
            route_list.append(d.destination)
    route_text = " ".join(route_list)
    itinerary_text = " ".join(
        (day.destination or "") + " " + (day.summary or "")
        for day in payload.itinerary
    )
    text_context = route_text + " " + itinerary_text

    from image_selector import extract_and_map_destinations, get_random_image_for_province, get_all_images_for_province
    destinations = await extract_and_map_destinations(text_context, max_items=None)
    
    # Resolve image urls for each destination
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))
        d["images"] = get_all_images_for_province(d.get("slug"))

    log.debug("[/quotations/b2c] Extracted destinations: %s", destinations)

    default_img = "/assets/vietnam-safar-logo.png"
    
    # Hero image: Pick a random image from the resolved destinations, or default
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/quotations/b2c] Hero image resolved: %s", hero_image_url)

    brand_config = resolve_brand(request, payload.model_dump(mode="json"))
    ctx = _build_ctx(quotation_id, payload, hero_image_url, destinations, lang=lang, template_name="vietnam_heritage_luxury_b2c.html", brand=brand_config)
    ctx["baseline_payload"] = payload.model_dump(mode="json")
    ctx["baseline_lang"] = lang
    ctx["brand"] = brand_config
    ctx["translations"] = {}
    ctx["available_langs"] = [lang]
    ctx["translation_status"] = {"baseline_lang": lang, "available_langs": [lang]}

    if "designer_img" in data:
        ctx["designer_img"] = data["designer_img"]

    # ── Render landing page HTML ───────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    tmpl_lp  = templates.get_template("vietnam_heritage_luxury_b2c.html")
    tmpl_pdf = templates.get_template("vietnam_heritage_luxury_b2c_pdf.html")

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render,  **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )
    initial_html_sync = _capture_html_sync_state(rendered_html)
    initial_html_sync["captured_from_version"] = 1
    ctx.setdefault("html_sync", {})[lang] = initial_html_sync

    # ── Update in-memory store ────────────────────────────────────────────
    quotations[quotation_id] = {
        "payload":       payload.model_dump(mode="json"),
        "ctx":           ctx,
        "html":          rendered_html,
        "pdf_html":      rendered_pdf,
        "status":        "pending",
        "published_url": None,
        "pdf_url":       None,
        "version":       0,
    }

    # ── Publish to GitHub or save locally with language suffix ──────────────
    sfx = f"_{lang}" if lang != "en" else ""
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

    if ENVIRONMENT == "production":
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            log.error("[/quotations/b2c] GITHUB_TOKEN or GITHUB_REPO not set — cannot persist on Vercel.")
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: GITHUB_TOKEN / GITHUB_REPO env vars are missing.",
            )
        try:
            # Publish landing page, PDF, ctx, and payload in parallel
            # Publish files sequentially to avoid 409 conflict
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/v1{sfx}.html",
                html_content=rendered_html,
                commit_message=f"Publish B2C quotation {quotation_id} v1{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/pdf{sfx}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish B2C PDF view for quotation {quotation_id} pdf{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/pdf_{lang}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish B2C PDF view for quotation {quotation_id} pdf_{lang}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/ctx.json",
                html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                commit_message=f"Publish B2C Context for {quotation_id}",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/payload.json",
                html_content=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
                commit_message=f"Publish B2C Payload for {quotation_id}",
            )
            # Initialize and save translation status
            await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
            
            quotations[quotation_id]["status"]        = "published"
            quotations[quotation_id]["published_url"] = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
            quotations[quotation_id]["pdf_url"]       = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf"
            quotations[quotation_id]["version"]       = 1
            log.info("[/quotations/b2c] ✓ v1{sfx} + pdf{sfx} committed to GitHub.")
        except Exception as exc:
            log.exception("[/quotations/b2c] GitHub publish FAILED for %s: %s", quotation_id, exc)
            raise HTTPException(
                status_code=502,
                detail=f"GitHub publish failed: {exc}. Check GITHUB_TOKEN permissions.",
            )

    else:
        # ── Localhost only: persist to disk ────────────────────────────────────
        quo_dir = os.path.join("published", quotation_id)
        os.makedirs(quo_dir, exist_ok=True)
        with open(os.path.join(quo_dir, f"v1{sfx}.html"),  "w", encoding="utf-8") as _f:
            _f.write(rendered_html)
        with open(os.path.join(quo_dir, f"pdf{sfx}.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(quo_dir, f"pdf_{lang}.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as _f:
            json.dump(ctx, _f, ensure_ascii=False, default=str)
        with open(os.path.join(quo_dir, "payload.json"), "w", encoding="utf-8") as _f:
            json.dump(payload.model_dump(mode="json"), _f, ensure_ascii=False)
        await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
        
        quotations[quotation_id]["status"]  = "published"
        quotations[quotation_id]["version"] = 1
        log.info("[/quotations/b2c] Localhost: v1{sfx}.html + pdf{sfx}.html + ctx.json written to disk.")

    log.info("[/quotations/b2c] ✓ id=%s  preparedFor=%s  days=%d",
             quotation_id, payload.journeyGlance.guestProfile, len(payload.itinerary))

    quotation_url = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
    return {
        "quotationId":  quotation_id,
        "status":       "published",
        "version":      1,
        "message":      "B2C Landing page published. Open quotationUrl to preview and edit inline.",
        "quotationUrl": quotation_url,
        "pdfUrl":       f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf",
    }


@app.post("/quotations")
async def create_quotation(request: Request):
    """
    Receives structured quotation data from a ChatGPT Custom GPT Action,
    renders a Jinja2 landing page template, stores it, and returns the preview URL.
    """
    body = await request.json()
    log.debug("[/quotations] Incoming keys: %s", list(body.keys()))

    # Unwrap ChatGPT Action wrapper if present
    data = body.get("params", body)
    log.debug("[/quotations] Data keys after unwrap: %s", list(data.keys()))
    lang = data.get("language") or data.get("lang") or request.query_params.get("lang") or request.query_params.get("language") or "en"
    if lang not in ("en", "vi", "ar"):
        lang = "en"

    try:
        payload = TourQuotationPayload.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        log.error("[/quotations] Pydantic validation failed — %d error(s):\n%s",
                  len(errors), json.dumps(errors, indent=2, default=str))
        return JSONResponse(status_code=422, content={"detail": errors,
            "hint": "Field path is in 'loc'. Check which required field is missing."})

    quotation_id = f"quo_{uuid.uuid4().hex[:12]}"

    # ── Extract destinations from route + itinerary for the gallery ──────────
    route_list = []
    for d in payload.itinerary:
        if d.destination and d.destination not in route_list:
            route_list.append(d.destination)
    route_text = " ".join(route_list)
    itinerary_text = " ".join(
        (day.destination or "") + " " + (day.summary or "")
        for day in payload.itinerary
    )
    text_context = route_text + " " + itinerary_text

    from image_selector import extract_and_map_destinations, get_random_image_for_province, get_all_images_for_province
    destinations = await extract_and_map_destinations(text_context, max_items=None)
    
    # Resolve image urls for each destination
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))
        d["images"] = get_all_images_for_province(d.get("slug"))

    log.debug("[/quotations] Extracted destinations: %s", destinations)

    default_img = "/assets/vietnam-safar-logo.png"
    
    # Hero image: Pick a random image from the resolved destinations, or default
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/quotations] Hero image resolved: %s", hero_image_url)

    brand_config = resolve_brand(request, payload.model_dump(mode="json"))
    ctx = _build_ctx(quotation_id, payload, hero_image_url, destinations, lang=lang, template_name="vietnam_luxury_brosure.html", brand=brand_config)
    ctx["baseline_payload"] = payload.model_dump(mode="json")
    ctx["baseline_lang"] = lang
    ctx["translations"] = {}
    ctx["available_langs"] = [lang]
    ctx["translation_status"] = {"baseline_lang": lang, "available_langs": [lang]}
    ctx["brand"] = brand_config

    if "designer_img" in data:
        ctx["designer_img"] = data["designer_img"]

    # ── Render landing page HTML ───────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    base_tmpl = ctx.get("template_name", "vietnam_luxury_brosure.html")
    tmpl_lp  = templates.get_template(base_tmpl)
    tmpl_pdf = templates.get_template(base_tmpl.replace(".html", "_pdf.html"))

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render,  **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )
    initial_html_sync = _capture_html_sync_state(rendered_html)
    initial_html_sync["captured_from_version"] = 1
    ctx.setdefault("html_sync", {})[lang] = initial_html_sync

    # ── Update in-memory store ────────────────────────────────────────────
    quotations[quotation_id] = {
        "payload":       payload.model_dump(mode="json"),
        "ctx":           ctx,
        "html":          rendered_html,
        "pdf_html":      rendered_pdf,
        "status":        "pending",
        "published_url": None,
        "pdf_url":       None,
        "version":       0,
    }

    # ── Publish to GitHub or save locally with language suffix ──────────────
    sfx = f"_{lang}" if lang != "en" else ""
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

    if ENVIRONMENT == "production":
        # Hard requirement: GITHUB_TOKEN and GITHUB_REPO must be configured.
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            log.error("[/quotations] GITHUB_TOKEN or GITHUB_REPO not set — cannot persist on Vercel.")
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: GITHUB_TOKEN / GITHUB_REPO env vars are missing.",
            )
        try:
            # Publish landing page, PDF, ctx, and payload in parallel
            # Publish files sequentially to avoid 409 conflict
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/v1{sfx}.html",
                html_content=rendered_html,
                commit_message=f"Publish quotation {quotation_id} v1{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/pdf{sfx}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish B2B PDF view for quotation {quotation_id} pdf{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/pdf_{lang}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish B2B PDF view for quotation {quotation_id} pdf_{lang}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/ctx.json",
                html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                commit_message=f"Publish B2B Context for {quotation_id}",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/payload.json",
                html_content=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
                commit_message=f"Publish B2B Payload for {quotation_id}",
            )
            # Initialize and save translation status
            await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
            
            quotations[quotation_id]["status"]        = "published"
            quotations[quotation_id]["published_url"] = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
            quotations[quotation_id]["pdf_url"]       = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf"
            quotations[quotation_id]["version"]       = 1
            log.info("[/quotations] ✓ v1{sfx} + pdf{sfx} committed to GitHub.")
        except Exception as exc:
            log.exception("[/quotations] GitHub publish FAILED for %s: %s", quotation_id, exc)
            raise HTTPException(
                status_code=502,
                detail=f"GitHub publish failed: {exc}. Check GITHUB_TOKEN permissions.",
            )

    else:
        # ── Localhost only: persist to disk ────────────────────────────────────
        quo_dir = os.path.join("published", quotation_id)
        os.makedirs(quo_dir, exist_ok=True)
        with open(os.path.join(quo_dir, f"v1{sfx}.html"),  "w", encoding="utf-8") as _f:
            _f.write(rendered_html)
        with open(os.path.join(quo_dir, f"pdf{sfx}.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(quo_dir, f"pdf_{lang}.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as _f:
            json.dump(ctx, _f, ensure_ascii=False, default=str)
        with open(os.path.join(quo_dir, "payload.json"), "w", encoding="utf-8") as _f:
            json.dump(payload.model_dump(mode="json"), _f, ensure_ascii=False)
        await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
        
        quotations[quotation_id]["status"]  = "published"
        quotations[quotation_id]["version"] = 1
        log.info("[/quotations] Localhost: v1{sfx}.html + pdf{sfx}.html + ctx.json written to disk.")

    log.info("[/quotations] ✓ id=%s  preparedFor=%s  days=%d  route=%s",
             quotation_id, payload.journeyGlance.guestProfile,
             len(payload.itinerary), " > ".join(route_list))

    # quotationUrl should be the stable permalink API endpoint
    quotation_url = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
    return {
        "quotationId":  quotation_id,
        "status":       "published",
        "version":      1,
        "message":      "Landing page published. Open quotationUrl to preview and edit inline.",
        "quotationUrl": quotation_url,
        "pdfUrl":       f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf",
    }


# ── GET /published/{file_path:path} — Dynamic static files ────────────────────

@app.get("/published/{file_path:path}")
async def get_published_file(file_path: str):
    """
    Serve files from the local 'published' directory if they exist.
    On Vercel (where no rebuild happens and local file might be missing),
    fetch the file directly from GitHub API and serve it.
    """
    import mimetypes
    from fastapi.responses import Response, FileResponse

    local_path = os.path.join("published", file_path)
    if os.path.isfile(local_path):
        return FileResponse(local_path)
        
    # File not found locally - if we are on Vercel, try fetching from GitHub
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        import httpx
        repo = os.getenv("GITHUB_REPO")
        token = os.getenv("GITHUB_TOKEN")
        if repo and token:
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {
                    "Authorization": f"token {token}", 
                    "Accept": "application/vnd.github.v3.raw"
                }
                gh_url = f"https://api.github.com/repos/{repo}/contents/published/{file_path}"
                resp = await client.get(gh_url, headers=headers)
                if resp.status_code == 401:
                    log.warning("[/published] GITHUB_TOKEN unauthorized (401), trying without token")
                    resp = await client.get(gh_url)
                if resp.status_code == 200:
                    log.info("[/published] Fetched %s from GitHub API", file_path)
                    mt, _ = mimetypes.guess_type(file_path)
                    if not mt:
                        mt = "application/octet-stream"
                    return Response(content=resp.content, media_type=mt)
                    
    raise HTTPException(status_code=404, detail=f"File {file_path} not found.")


# ── GET /quotations/{id}/pdf — A4-optimised PDF view ─────────────────────
# IMPORTANT: must be registered BEFORE the {quotation_id} catch-all route.

from html.parser import HTMLParser

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

class EditableFieldsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.edited_fields = {}
        self.stack = []

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        attrs_dict = dict(attrs)
        is_void = tag_lower in VOID_TAGS

        attr_str = "".join([f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs])
        for item in self.stack:
            if is_void:
                item['acc'].append(f"<{tag}{attr_str} />")
            else:
                item['acc'].append(f"<{tag}{attr_str}>")
                item['depth'] += 1

        if "data-editable" in attrs_dict and not is_void:
            field_name = attrs_dict["data-editable"]
            img_url = ""
            if "style" in attrs_dict:
                match = re.search(r'url\((["\']?)(.*?)\1\)', attrs_dict["style"])
                if match:
                    img_url = match.group(2)
            elif "src" in attrs_dict:
                img_url = attrs_dict["src"]

            self.stack.append({
                'field': field_name,
                'tag': tag_lower,
                'depth': 1,
                'acc': [],
                'img_url': img_url
            })

    def handle_startendtag(self, tag, attrs):
        tag_lower = tag.lower()
        attr_str = "".join([f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs])
        for item in self.stack:
            item['acc'].append(f"<{tag}{attr_str} />")

    def handle_data(self, data):
        for item in self.stack:
            item['acc'].append(data)

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in VOID_TAGS:
            return

        new_stack = []
        for item in self.stack:
            item['depth'] -= 1
            if item['depth'] == 0 and item['tag'] == tag_lower:
                val = "".join(item['acc']).strip()
                if not val and item.get('img_url'):
                    val = item['img_url']
                elif not item['field'].startswith("day_img_") and not item['field'].startswith("img_"):
                    val = re.sub(r'<[^>]*>', '', str(val)).strip()
                self.edited_fields[item['field']] = val
            else:
                item['acc'].append(f"</{tag}>")
                new_stack.append(item)
        self.stack = new_stack

def parse_edited_fields(html_content: str) -> dict:
    parser = EditableFieldsParser()
    parser.feed(html_content)
    return parser.edited_fields

def _normalize_visible_text(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r'<\s*br\s*/?>', '\n', value, flags=re.IGNORECASE)
    value = re.sub(r'</\s*(div|p|li|h[1-6])\s*>', '\n', value, flags=re.IGNORECASE)
    value = re.sub(r'<[^>]*>', '', value)
    value = value.replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in value.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()

def _extract_editable_inner_html(html_content: str, field_name: str) -> str:
    pattern = rf'<(?P<tag>[a-zA-Z0-9]+)(?P<attrs>[^>]*?)data-editable=["\']{re.escape(field_name)}["\'](?P<attrs2>[^>]*)>(?P<body>.*?)</(?P=tag)>'
    match = re.search(pattern, html_content, flags=re.DOTALL)
    if match:
        return match.group("body").strip()
    return ""

def _extract_letter_intro_parts(letter_intro_text: str) -> dict:
    parts = {}
    if not letter_intro_text:
        return parts

    guest_match = re.search(r'created for\s+(.*?)\s+travelling from', letter_intro_text, flags=re.IGNORECASE | re.DOTALL)
    if guest_match:
        parts["guests_txt"] = " ".join(guest_match.group(1).split())

    route_match = re.search(r'The route unfolds from\s+(.*?)(?:\.|$)', letter_intro_text, flags=re.IGNORECASE | re.DOTALL)
    if route_match:
        parts["route_txt"] = " ".join(route_match.group(1).split())

    title_match = re.search(r'journey:\s+(.*?),\s+created for', letter_intro_text, flags=re.IGNORECASE | re.DOTALL)
    if title_match:
        parts["overview_heading"] = " ".join(title_match.group(1).split())

    return parts

def _capture_composite_sync_state(html_content: str) -> dict:
    edited_fields = parse_edited_fields(html_content)
    composite = {
        "top_level": {},
        "hotels": {},
    }

    top_fields = [
        "hero_meta_1",
        "letter_greeting",
        "letter_intro",
        "letter_body_p2",
        "letter_outro",
        "letter_sign_off",
        "letter_sender",
        "contact",
        "seller_email",
        "contact_phone",
        "footer_text",
    ]
    for field_name in top_fields:
        value = edited_fields.get(field_name)
        if value:
            composite["top_level"][field_name] = value

    letter_greeting = composite["top_level"].get("letter_greeting", "")
    greeting_match = re.match(r'^Dear\s+(.*?)(?:,)?$', letter_greeting, flags=re.IGNORECASE | re.DOTALL)
    if greeting_match:
        composite["top_level"]["customer_name"] = " ".join(greeting_match.group(1).split())

    composite["top_level"].update(_extract_letter_intro_parts(composite["top_level"].get("letter_intro", "")))

    hotel_indexes = sorted({int(idx) for idx in re.findall(r'data-editable=["\']hotel_intro_(\d+)["\']', html_content)})
    room_type_label = re.compile(r'Room\s*type\s*:?\s*', flags=re.IGNORECASE)
    for idx in hotel_indexes:
        hotel_intro_html = _extract_editable_inner_html(html_content, f"hotel_intro_{idx}")
        hotel_intro_text = _normalize_visible_text(hotel_intro_html)
        room_type = ""

        room_match = room_type_label.search(hotel_intro_text)
        if room_match:
            intro_text = hotel_intro_text[:room_match.start()].strip()
            room_type_text = hotel_intro_text[room_match.end():].strip()
            if "\n" in room_type_text:
                room_type_text = room_type_text.split("\n", 1)[0].strip()
            hotel_intro_text = intro_text
            room_type = room_type_text

        explicit_room_type = edited_fields.get(f"hotel_room_type_{idx}")
        if explicit_room_type:
            room_type = explicit_room_type.strip()

        hotel_entry = {}
        if hotel_intro_text:
            hotel_entry["hotel_intro"] = hotel_intro_text
        if room_type:
            hotel_entry["room_type"] = room_type
        if hotel_entry:
            composite["hotels"][str(idx)] = hotel_entry

    if not composite["top_level"]:
        composite.pop("top_level")
    if not composite["hotels"]:
        composite.pop("hotels")
    return composite

def get_existing_editable_keys(html_content: str) -> set[str]:
    import re
    return set(re.findall(r'data-editable=["\']([^"\']+)["\']', html_content))

def extract_editor_components(rendered_html: str) -> str:
    """
    Extracts the publish-bar, loading overlay, translation-status,
    and editor-scripts from the rendered Jinja2 template.
    """
    idx_bar = rendered_html.find('id="publish-bar"')
    if idx_bar == -1:
        idx_bar = rendered_html.find("id='publish-bar'")
    if idx_bar == -1:
        return ""
        
    idx_start = rendered_html.rfind('<div', 0, idx_bar)
    if idx_start == -1:
        idx_start = idx_bar
        
    idx_scripts = rendered_html.find('id="editor-scripts"')
    if idx_scripts == -1:
        idx_scripts = rendered_html.find("id='editor-scripts'")
    if idx_scripts == -1:
        return ""
        
    idx_end_script = rendered_html.find('</script>', idx_scripts)
    if idx_end_script == -1:
        return ""
    idx_end = idx_end_script + len('</script>')
    
    return rendered_html[idx_start:idx_end]

def make_itinerary_editor_visible(html_content: str) -> str:
    import re
    # Strip style="display: none;" from #publish-bar
    pattern = r'(<div[^>]*id=["\']publish-bar["\'][^>]*style=["\']display:\s*none;?["\'][^>]*>)'
    def repl(match):
        tag = match.group(1)
        tag = re.sub(r'style=["\']display:\s*none;?["\']', '', tag)
        return tag
    return re.sub(pattern, repl, html_content)

def sync_itinerary_deletions_to_payloads(ctx: dict, active_days: set[int], active_cards: dict):
    if "itinerary" in ctx:
        ctx["itinerary"] = [day for day in ctx["itinerary"] if day.get("dayNumber") in active_days]
    if "hotels" in ctx:
        ctx["hotels"] = [h for i, h in enumerate(ctx["hotels"]) if i in active_cards["hotel"]]
    if "activities" in ctx:
        ctx["activities"] = [act for i, act in enumerate(ctx["activities"]) if i in active_cards["activity"]]
    if "transfers" in ctx:
        ctx["transfers"] = [tx for i, tx in enumerate(ctx["transfers"]) if i in active_cards["transfer"]]
    if "flights" in ctx:
        ctx["flights"] = [fl for i, fl in enumerate(ctx["flights"]) if i in active_cards["flight"]]
    if "guides" in ctx:
        ctx["guides"] = [gd for i, gd in enumerate(ctx["guides"]) if i in active_cards["guide"]]

    def filter_payload(p_dict):
        if not p_dict:
            return
        if "itinerary" in p_dict:
            p_dict["itinerary"] = [day for day in p_dict["itinerary"] if day.get("dayNumber") in active_days]
        if "hotels" in p_dict:
            p_dict["hotels"] = [h for i, h in enumerate(p_dict["hotels"]) if i in active_cards["hotel"]]
        if "activities" in p_dict:
            p_dict["activities"] = [act for i, act in enumerate(p_dict["activities"]) if i in active_cards["activity"]]
        if "transfers" in p_dict:
            p_dict["transfers"] = [tx for i, tx in enumerate(p_dict["transfers"]) if i in active_cards["transfer"]]
        if "flights" in p_dict:
            p_dict["flights"] = [fl for i, fl in enumerate(p_dict["flights"]) if i in active_cards["flight"]]
        if "guides" in p_dict:
            p_dict["guides"] = [gd for i, gd in enumerate(p_dict["guides"]) if i in active_cards["guide"]]

    if "baseline_payload" in ctx:
        filter_payload(ctx["baseline_payload"])

    if "translations" in ctx:
        for lang_key in ctx["translations"]:
            filter_payload(ctx["translations"][lang_key])

def filter_and_override_ctx(lang_ctx: dict, existing_keys: set[str], edited_fields: dict, override_text: bool = True):
    """
    Filters out deleted blocks and optionally overrides text content of remaining blocks
    based on the saved editable state.
    """
    # Simple variables
    if override_text:
        for key in [
            'tour_title', 'kicker', 'lede', 'customer_name', 'overview_heading', 
            'guests_txt', 'travel_dates', 'route_txt', 'travel_style', 
            'quotation_number', 'contact', 'why_private', 'why_comfort', 
            'why_muslim', 'why_balanced', 'journey_h2', 'journey_p', 
            'route_map_h2', 'route_map_p',
            'itinerary_h2', 'itinerary_p', 'room_notes', 'pricing_h2', 
            'pricing_p', 'pricing_kicker', 'muslim_care_text', 'term_deposit', 'term_balance', 
            'term_cancellation', 'term_confirmation', 'cta_h2', 'designer_kicker', 
            'designer_title', 'designer_quote', 'designer_expertise', 
            'designer_experience', 'designer_signature',
            'journey_overview_title', 'label_prepared_for', 'label_overview',
            'label_guests', 'label_travel_dates', 'label_route', 'label_style',
            'label_ref', 'label_contact', 'label_nationality', 'label_duration',
            'hero_meta_1', 'hero_meta_2', 'footer_text', 'seller_email',
            'contact_phone', 'letter_greeting', 'letter_intro', 'letter_body_p2',
            'letter_outro', 'letter_sign_off', 'letter_sender', 'letter_highlight'
        ]:
            if key in edited_fields:
                lang_ctx[key] = edited_fields[key]
            
    # 1. Filter and update itinerary days
    new_itinerary = []
    for idx, day in enumerate(lang_ctx.get('itinerary', []), 1):
        t_key = f"day_title_{idx}"
        if t_key in existing_keys:
            if override_text:
                if t_key in edited_fields:
                    day['title'] = edited_fields[t_key]
                
                badge_key = f"day_badge_{idx}"
                if badge_key in edited_fields:
                    day['day_badge_text'] = edited_fields[badge_key]

                num_key = f"day_num_{idx}"
                if num_key in edited_fields:
                    day['day_num_text'] = edited_fields[num_key]

                lh_key = f"day_label_highlights_{idx}"
                if lh_key in edited_fields:
                    day['label_highlights'] = edited_fields[lh_key]

                ln_key = f"day_label_notes_{idx}"
                if ln_key in edited_fields:
                    day['label_notes'] = edited_fields[ln_key]

                lo_key = f"day_label_overnight_{idx}"
                if lo_key in edited_fields:
                    day['label_overnight'] = edited_fields[lo_key]

                lm_key = f"day_label_meals_{idx}"
                if lm_key in edited_fields:
                    day['label_meals'] = edited_fields[lm_key]
                    
                # Rebuild day description paragraphs
                any_desc_edited = any(f"day_desc_{idx}_{p}" in edited_fields for p in range(20))
                if any_desc_edited:
                    desc_paras = []
                    p = 0
                    while True:
                        p_key = f"day_desc_{idx}_{p}"
                        if p_key in edited_fields:
                            desc_paras.append(edited_fields[p_key])
                            p += 1
                        elif p_key in existing_keys:
                            orig_desc = day.get('description', [])
                            if p < len(orig_desc):
                                desc_paras.append(orig_desc[p])
                            else:
                                desc_paras.append("")
                            p += 1
                        else:
                            break
                    day['description'] = desc_paras

                # Update Overnight & Meals even if description itself was unchanged.
                o_key = f"day_overnight_{idx}"
                if o_key in edited_fields:
                    day['overnight'] = edited_fields[o_key]
                m_key = f"day_meals_{idx}"
                if m_key in edited_fields:
                    day['meals'] = [m.strip() for m in re.split(r'[·•\-,/]', edited_fields[m_key]) if m.strip()]

                # Update Highlights (activities)
                h_key = f"day_highlights_{idx}"
                if h_key in edited_fields:
                    day['activities'] = [h.strip() for h in re.split(r'[·•\-,/]', edited_fields[h_key]) if h.strip()]

                # Update Notes list
                any_notes_edited = any(f"day_note_{idx}_{p}" in edited_fields for p in range(20))
                if any_notes_edited:
                    notes_list = []
                    p = 0
                    while True:
                        n_key = f"day_note_{idx}_{p}"
                        if n_key in edited_fields:
                            notes_list.append(edited_fields[n_key])
                            p += 1
                        elif n_key in existing_keys:
                            orig_notes = day.get('notes', [])
                            if p < len(orig_notes):
                                notes_list.append(orig_notes[p])
                            else:
                                notes_list.append("")
                            p += 1
                        else:
                            break
                    day['notes'] = notes_list
            new_itinerary.append(day)
    lang_ctx['itinerary'] = new_itinerary
    
    # 1b. Update chapter layout images if edited_fields contains day_img_*
    for chapter in lang_ctx.get('chapters', []):
        for day in chapter.get('days', []):
            d_num = day.get('dayNumber')
            if d_num:
                layout_imgs = day.setdefault('layout_images', {})
                if edited_fields.get(f"day_img_hero_{d_num}"):
                    layout_imgs['hero'] = edited_fields[f"day_img_hero_{d_num}"]
                if edited_fields.get(f"day_img_small1_{d_num}"):
                    layout_imgs['small-1'] = edited_fields[f"day_img_small1_{d_num}"]
                if edited_fields.get(f"day_img_small2_{d_num}"):
                    layout_imgs['small-2'] = edited_fields[f"day_img_small2_{d_num}"]
    
    # 2. Filter and update hotels
    new_hotels = []
    for h_idx, hotel in enumerate(lang_ctx.get('hotels', []), 1):
        name_key = f"hotel_name_{h_idx}"
        if name_key in existing_keys:
            if override_text:
                city_key = f"hotel_city_{h_idx}"
                date_key = f"hotel_date_{h_idx}"
                tel_key = f"hotel_tel_{h_idx}"
                intro_key = f"hotel_intro_{h_idx}"
                info_key = f"hotel_info_name_{h_idx}"
                
                if name_key in edited_fields:
                    hotel['hotel_name'] = edited_fields[name_key]
                if city_key in edited_fields:
                    hotel['city_country'] = edited_fields[city_key]
                if date_key in edited_fields:
                    hotel['check_in_out'] = edited_fields[date_key]
                if tel_key in edited_fields:
                    hotel['telephone'] = edited_fields[tel_key]
                if intro_key in edited_fields:
                    hotel['hotel_intro'] = edited_fields[intro_key]
                if info_key in edited_fields:
                    hotel['room_name'] = edited_fields[info_key]
                    hotel['room_type'] = edited_fields[info_key]
            new_hotels.append(hotel)
    lang_ctx['hotels'] = new_hotels
    
    # 3. Filter and update inclusions
    new_inclusions = []
    for inc_idx, item in enumerate(lang_ctx.get('inclusions', []), 1):
        key = f"inc_{inc_idx}"
        if key in existing_keys:
            if override_text and key in edited_fields:
                new_inclusions.append(edited_fields[key])
            else:
                new_inclusions.append(item)
    lang_ctx['inclusions'] = new_inclusions
    
    # 4. Filter and update exclusions
    new_exclusions = []
    for exc_idx, item in enumerate(lang_ctx.get('exclusions', []), 1):
        key = f"exc_{exc_idx}"
        if key in existing_keys:
            if override_text and key in edited_fields:
                new_exclusions.append(edited_fields[key])
            else:
                new_exclusions.append(item)
    lang_ctx['exclusions'] = new_exclusions
    
    # 5. Filter and update pricing per pax
    new_price_options = []
    for p_idx, opt in enumerate(lang_ctx.get('price_options', []), 1):
        key = f"price_pax_{p_idx}"
        key_total = f"price_total_{p_idx}"
        key_cat = f"price_opt_cat_{p_idx}"
        key_name = f"price_opt_name_{p_idx}"
        if key in existing_keys or key_total in existing_keys or key_cat in existing_keys or key_name in existing_keys:
            if override_text:
                if key in edited_fields:
                    clean_val = re.sub(r'<[^>]*>', '', str(edited_fields[key])).strip()
                    if 'pricePerPerson' in opt and isinstance(opt['pricePerPerson'], dict):
                        opt['pricePerPerson']['displayText'] = clean_val
                if key_total in edited_fields:
                    clean_val = re.sub(r'<[^>]*>', '', str(edited_fields[key_total])).strip()
                    if 'totalPrice' in opt and isinstance(opt['totalPrice'], dict):
                        opt['totalPrice']['displayText'] = clean_val
                if key_cat in edited_fields:
                    clean_val = re.sub(r'<[^>]*>', '', str(edited_fields[key_cat])).strip()
                    opt['hotelCategory'] = clean_val
                if key_name in edited_fields:
                    clean_val = re.sub(r'<[^>]*>', '', str(edited_fields[key_name])).strip()
                    opt['optionName'] = clean_val

            # Guarantee sanitization of existing displayText values
            if 'pricePerPerson' in opt and isinstance(opt['pricePerPerson'], dict) and opt['pricePerPerson'].get('displayText'):
                opt['pricePerPerson']['displayText'] = re.sub(r'<[^>]*>', '', str(opt['pricePerPerson']['displayText'])).strip()
            if 'totalPrice' in opt and isinstance(opt['totalPrice'], dict) and opt['totalPrice'].get('displayText'):
                opt['totalPrice']['displayText'] = re.sub(r'<[^>]*>', '', str(opt['totalPrice']['displayText'])).strip()
            if opt.get('hotelCategory'):
                opt['hotelCategory'] = re.sub(r'<[^>]*>', '', str(opt['hotelCategory'])).strip()
            if opt.get('optionName'):
                opt['optionName'] = re.sub(r'<[^>]*>', '', str(opt['optionName'])).strip()

            new_price_options.append(opt)
    lang_ctx['price_options'] = new_price_options
    
    # 6. Filter and update map segment descriptions and sidebar fields
    if "stay_segments" in lang_ctx:
        new_stay_segments = []
        for s_idx, segment in enumerate(lang_ctx["stay_segments"]):
            desc_key = f"map_segment_desc_{s_idx}"
            duration_key = f"map_segment_duration_{s_idx}"
            title_key = f"map_segment_title_{s_idx}"
            hotel_key = f"map_segment_hotel_{s_idx}"
            
            if desc_key in edited_fields and override_text:
                segment["mapSegmentDesc"] = edited_fields[desc_key]
            
            # The JS uses dest.daysLabel, dest.nightsLabel for durationHtml. We can override daysLabel for now.
            if duration_key in edited_fields and override_text:
                # We save it into mapSegmentDuration so JS can use it instead of computing durationHtml
                segment["mapSegmentDuration"] = edited_fields[duration_key]
                
            if title_key in edited_fields and override_text:
                segment["displayName"] = edited_fields[title_key]
                
            if hotel_key in edited_fields and override_text:
                segment["hotelName"] = edited_fields[hotel_key]
                
            new_stay_segments.append(segment)
        lang_ctx["stay_segments"] = new_stay_segments

    if "itinerary_days" in lang_ctx and "itinerary" in lang_ctx:
        existing_flat_days = {
            day.get("dayNumber"): day
            for day in lang_ctx.get("itinerary_days", [])
            if day.get("dayNumber")
        }
        rebuilt_flat_days = []
        for flat_idx, timeline_day in enumerate(lang_ctx.get("itinerary", [])):
            day_number = timeline_day.get("dayNumber")
            flat_day = copy.deepcopy(existing_flat_days.get(day_number, {}))
            if not flat_day:
                flat_day = {
                    "dayNumber": day_number,
                    "layout_type": "single",
                    "layout_images": {},
                    "is_alternate": bool(flat_idx % 2),
                }
            flat_day.update({
                "dayNumber": day_number,
                "date": timeline_day.get("date"),
                "lang": timeline_day.get("lang", lang_ctx.get("lang", "en")),
                "title": timeline_day.get("title", ""),
                "description": copy.deepcopy(timeline_day.get("description", [])),
                "overnight": timeline_day.get("overnight", ""),
                "meals": copy.deepcopy(timeline_day.get("meals", [])),
                "activities": copy.deepcopy(timeline_day.get("activities", [])),
                "notes": copy.deepcopy(timeline_day.get("notes", [])),
                "destinations": copy.deepcopy(timeline_day.get("destinations", [])),
                "label_highlights": timeline_day.get("label_highlights"),
                "label_notes": timeline_day.get("label_notes"),
                "label_overnight": timeline_day.get("label_overnight"),
                "label_meals": timeline_day.get("label_meals"),
            })
            if not flat_day.get("segment_city"):
                destinations = timeline_day.get("destinations") or []
                flat_day["segment_city"] = destinations[0] if destinations else timeline_day.get("overnight", "Vietnam")
            rebuilt_flat_days.append(flat_day)
        lang_ctx["itinerary_days"] = rebuilt_flat_days

def filter_and_override_ctx_by_html(lang_ctx: dict, html_content: str, override_text: bool = True):
    """
    Backward-compatible wrapper that derives editable state from HTML.
    """
    filter_and_override_ctx(
        lang_ctx,
        get_existing_editable_keys(html_content),
        parse_edited_fields(html_content),
        override_text=override_text,
    )
    lang = lang_ctx.get("lang", "en")
    if lang == "ar":
        lang_ctx.update(canonicalize_place_names_in_data(lang_ctx, lang))

def _get_lang_sync_key(target_lang: str | None, baseline_lang: str) -> str:
    if target_lang in ("en", "vi", "ar"):
        return target_lang
    return baseline_lang

def _extract_custom_images_from_html(html_content: str) -> dict:
    extracted = {}
    
    # Extract --designer-img
    designer_match = re.search(r'--designer-img:\s*url\((["\']?)(.*?)\1\)', html_content)
    if designer_match:
        extracted["designer_img"] = designer_match.group(2)
        
    # Extract --hero-img
    hero_match = re.search(r'--hero-img:\s*url\((["\']?)(.*?)\1\)', html_content)
    if hero_match:
        extracted["hero_img"] = hero_match.group(2)

    # Extract img_hotel_divider
    hotel_div_match = re.search(r'data-editable=["\']img_hotel_divider["\'][^>]*src=["\']([^"\']+)["\']', html_content)
    if not hotel_div_match:
        hotel_div_match = re.search(r'src=["\']([^"\']+)["\'][^>]*data-editable=["\']img_hotel_divider["\']', html_content)
    if hotel_div_match:
        extracted["img_hotel_divider"] = hotel_div_match.group(1)

    # Extract img_itinerary_divider
    iti_div_match = re.search(r'data-editable=["\']img_itinerary_divider["\'][^>]*url\((["\']?)(.*?)\1\)', html_content)
    if not iti_div_match:
        iti_div_match = re.search(r'data-editable=["\']img_itinerary_divider["\'][^>]*src=["\']([^"\']+)["\']', html_content)
    if iti_div_match:
        extracted["img_itinerary_divider"] = iti_div_match.group(2 if len(iti_div_match.groups()) > 1 else 1)
        
    return extracted

def _capture_html_sync_state(html_content: str) -> dict:
    return {
        "existing_keys": sorted(get_existing_editable_keys(html_content)),
        "edited_fields": parse_edited_fields(html_content),
        "composite_fields": _capture_composite_sync_state(html_content),
    }

def _save_ctx_html_sync_state(ctx_data: dict, target_lang: str | None, html_content: str, captured_from_version: int | None = None) -> str:
    baseline_lang = ctx_data.get("baseline_lang", "en")
    lang_key = _get_lang_sync_key(target_lang, baseline_lang)
    html_sync = ctx_data.setdefault("html_sync", {})
    html_sync_state = _capture_html_sync_state(html_content)
    if captured_from_version is not None:
        html_sync_state["captured_from_version"] = captured_from_version
    html_sync[lang_key] = html_sync_state
    return lang_key

def _apply_composite_html_sync(lang_ctx: dict, composite_fields: dict):
    if not composite_fields:
        return

    top_level = composite_fields.get("top_level", {})
    for key, value in top_level.items():
        if value:
            lang_ctx[key] = value

    hotels = composite_fields.get("hotels", {})
    if hotels:
        for idx, hotel in enumerate(lang_ctx.get("hotels", []), 1):
            hotel_sync = hotels.get(str(idx))
            if not hotel_sync:
                continue
            if hotel_sync.get("hotel_intro"):
                hotel["introduction"] = hotel_sync["hotel_intro"]
                hotel["hotel_intro"] = hotel_sync["hotel_intro"]
            if hotel_sync.get("room_type"):
                hotel["room_type"] = hotel_sync["room_type"]
                hotel["room_name"] = hotel_sync["room_type"]

def _apply_ctx_html_sync(
    lang_ctx: dict,
    ctx_data: dict,
    target_lang: str,
    baseline_lang: str,
) -> bool:
    html_sync = ctx_data.get("html_sync", {})
    applied = False

    lang_sync = html_sync.get(target_lang)
    if lang_sync:
        filter_and_override_ctx(
            lang_ctx,
            set(lang_sync.get("existing_keys", [])),
            lang_sync.get("edited_fields", {}),
            override_text=True,
        )
        _apply_composite_html_sync(lang_ctx, lang_sync.get("composite_fields", {}))
        if target_lang == "ar":
            lang_ctx.update(canonicalize_place_names_in_data(lang_ctx, target_lang))
        return True

    if target_lang != baseline_lang:
        baseline_sync = html_sync.get(baseline_lang)
        if baseline_sync:
            filter_and_override_ctx(
                lang_ctx,
                set(baseline_sync.get("existing_keys", [])),
                {},
                override_text=False,
            )
            _apply_composite_html_sync(lang_ctx, baseline_sync.get("composite_fields", {}))
            if target_lang == "ar":
                lang_ctx.update(canonicalize_place_names_in_data(lang_ctx, target_lang))
            applied = True

    return applied

async def _render_quotation_doc_from_ctx(
    ctx_data: dict,
    quotation_id: str,
    target_lang: str,
    request: Request = None,
    is_pdf: bool = True,
    ignore_published_html: bool = False,
) -> tuple[str, str]:
    baseline_lang = ctx_data.get("baseline_lang", "en")
    effective_lang = target_lang if target_lang in ("en", "vi", "ar") else baseline_lang
    payload_dict = (
        ctx_data.get("baseline_payload")
        if effective_lang == baseline_lang
        else ctx_data.get("translations", {}).get(effective_lang)
    )
    if not payload_dict:
        payload_dict = ctx_data.get("baseline_payload")
        effective_lang = baseline_lang

    payload_obj = TourQuotationPayload.model_validate(payload_dict)
    base_tmpl = ctx_data.get("template_name", "vietnam_luxury_brosure.html")
    tmpl_name = base_tmpl.replace(".html", "_pdf.html") if is_pdf else base_tmpl
    tmpl = templates.get_template(tmpl_name)

    brand_config = resolve_brand(request, payload_dict)
    hero_image_url = ctx_data.get("img_0", "/assets/vietnam-safar-logo.png")
    if hero_image_url == "/assets/vietnam-safar-logo.png":
        for day in ctx_data.get("itinerary_days", []) or ctx_data.get("itinerary", []):
            day_hero = day.get("layout_images", {}).get("hero")
            if day_hero:
                hero_image_url = day_hero
                break

    lang_ctx = _build_ctx(
        quotation_id=quotation_id,
        payload=payload_obj,
        hero_image_url=hero_image_url,
        destinations=ctx_data.get("destinations", []),
        lang=effective_lang,
        template_name=base_tmpl,
        brand=brand_config,
    )
    lang_ctx["brand"] = brand_config
    if ctx_data.get("designer_img"):
        lang_ctx["designer_img"] = ctx_data.get("designer_img")
    
    if ctx_data.get("hero_img"):
        lang_ctx["hero_img_custom"] = ctx_data.get("hero_img")
    elif hero_image_url != "/assets/vietnam-safar-logo.png":
        lang_ctx["hero_img_custom"] = hero_image_url

    lang_ctx["translations"] = ctx_data.get("translations", {})
    lang_ctx["baseline_lang"] = baseline_lang
    lang_ctx["translation_status"] = ctx_data.get(
        "translation_status",
        {"baseline_lang": baseline_lang, "available_langs": [baseline_lang]},
    )

    if not ignore_published_html:
        if not _apply_ctx_html_sync(lang_ctx, ctx_data, effective_lang, baseline_lang):
            latest_lang = None if effective_lang == baseline_lang else effective_lang
            html_content = await _get_latest_published_html(quotation_id, lang=latest_lang, fallback=False)
            if html_content:
                filter_and_override_ctx_by_html(lang_ctx, html_content, override_text=True)
            elif effective_lang != baseline_lang:
                baseline_html = await _get_latest_published_html(quotation_id, lang=None, fallback=False)
                if baseline_html:
                    filter_and_override_ctx_by_html(lang_ctx, baseline_html, override_text=False)

    rendered_html = tmpl.render(**lang_ctx)
    return rendered_html, effective_lang

async def _get_latest_published_html(quotation_id: str, lang: str = None, fallback: bool = True) -> str | None:
    """Gets the latest published HTML content from memory, disk, or GitHub."""
    if not lang:
        entry = quotations.get(quotation_id)
        if entry and entry.get("html"):
            return entry["html"]

    from github_publish import get_next_version
    next_version = await get_next_version(quotation_id)
    if next_version <= 1:
        return None
    current_version = next_version - 1
    
    # Try language specific published file first (e.g. v1_ar.html)
    lang_suffix = f"_{lang}" if lang else ""
    file_options = [
        f"{quotation_id}/v{current_version}{lang_suffix}.html"
    ]
    if fallback and lang:
        file_options.append(f"{quotation_id}/v{current_version}.html")
    
    for file_path in file_options:
        local_path = os.path.join("published", file_path)
        if os.path.isfile(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass

        # Fetch from GitHub if production
        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            repo = os.getenv("GITHUB_REPO")
            token = os.getenv("GITHUB_TOKEN")
            if repo and token:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    headers = {
                        "Authorization": f"token {token}", 
                        "Accept": "application/vnd.github.v3.raw"
                    }
                    gh_url = f"https://api.github.com/repos/{repo}/contents/published/{file_path}"
                    resp = await client.get(gh_url, headers=headers)
                    if resp.status_code == 200:
                        return resp.text
    return None

@app.get("/quotations/{quotation_id}/pdf", response_class=HTMLResponse)
async def get_quotation_pdf(quotation_id: str, request: Request):
    """
    Dynamically renders PDF HTML for a quotation in target language.
    Auto-triggers the browser print dialog.
    """
    lang = request.query_params.get("lang") or request.query_params.get("language")
    if lang not in ("en", "vi", "ar"):
        lang = None
        
    ctx_data = _load_ctx_data(quotation_id)
    if not ctx_data:
        raise HTTPException(status_code=404, detail=f"PDF for quotation '{quotation_id}' not found.")
        
    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = lang or baseline_lang
    
    # Trigger lazy translation if not available
    if target_lang != baseline_lang:
        available_langs = ctx_data.get("available_langs", [])
        if target_lang not in available_langs:
            success = await _translate_item_on_demand(quotation_id, target_lang, is_itinerary=False)
            if success:
                ctx_data = _load_ctx_data(quotation_id) or ctx_data
                
    # Extract appropriate payload dict
    if target_lang == baseline_lang:
        payload_dict = ctx_data.get("baseline_payload")
    else:
        payload_dict = ctx_data.get("translations", {}).get(target_lang)
        
    if not payload_dict:
        payload_dict = ctx_data.get("baseline_payload")
        target_lang = baseline_lang
        
    try:
        rendered_html, _ = await _render_quotation_doc_from_ctx(ctx_data, quotation_id, target_lang, request, is_pdf=True)
        return HTMLResponse(content=rendered_html)
    except Exception as err:
        log.exception("[/quotations] Dynamic PDF render failed for %s: %s", quotation_id, err)
        raise HTTPException(status_code=500, detail=f"PDF render error: {err}")


@app.post("/api/v1/quotations/{quotation_id}/translate")
async def translate_quotation_endpoint(quotation_id: str, lang: str):
    """Triggers on-demand translation for a quotation."""
    if lang not in ("en", "vi", "ar"):
        raise HTTPException(status_code=400, detail="Unsupported language")
    success = await _translate_item_on_demand(quotation_id, lang, is_itinerary=False)
    if not success:
        raise HTTPException(status_code=500, detail="Translation failed")
    status = _load_translation_status(quotation_id)
    return status

@app.post("/api/v1/itineraries/{itinerary_id}/translate")
async def translate_itinerary_endpoint(itinerary_id: str, lang: str):
    """Triggers on-demand translation for an itinerary."""
    if lang not in ("en", "vi", "ar"):
        raise HTTPException(status_code=400, detail="Unsupported language")
    success = await _translate_item_on_demand(itinerary_id, lang, is_itinerary=True)
    if not success:
        raise HTTPException(status_code=500, detail="Translation failed")
    status = _load_translation_status(itinerary_id)
    return status

@app.get("/api/v1/quotations/{quotation_id}/translation-status")
async def get_quotation_translation_status(quotation_id: str):
    """Returns the translation status of a quotation."""
    status = _load_translation_status(quotation_id)
    try:
        from github_publish import get_next_version
        next_ver = await get_next_version(quotation_id)
        status["latest_version"] = max(1, next_ver - 1)
    except Exception:
        status["latest_version"] = 1
    return status

@app.get("/api/v1/itineraries/{itinerary_id}/translation-status")
async def get_itinerary_translation_status(itinerary_id: str):
    """Returns the translation status of an itinerary."""
    status = _load_translation_status(itinerary_id)
    try:
        from github_publish import get_next_version
        next_ver = await get_next_version(itinerary_id)
        status["latest_version"] = max(1, next_ver - 1)
    except Exception:
        status["latest_version"] = 1
    return status


class TranslateBlockRequest(BaseModel):
    text: str
    target_lang: str


@app.post("/api/v1/translate-block")
async def translate_block_endpoint(payload: TranslateBlockRequest):
    """Translates a single block of text into target language."""
    if payload.target_lang not in ("en", "vi", "ar"):
        raise HTTPException(status_code=400, detail="Unsupported language")
    
    if not payload.text.strip():
        return {"translated_text": ""}

    from pydantic_ai import Agent
    import llm_client
    
    target_lang_name = {
        "en": "English",
        "vi": "Vietnamese (Tiếng Việt)",
        "ar": "Arabic (العربية)"
    }.get(payload.target_lang, payload.target_lang.upper())
    
    system_prompt = (
        "You are an expert multilingual Luxury Travel Copywriter.\n"
        f"Your task is to translate the given travel text string into {target_lang_name}.\n\n"
        "RULES FOR PREMIUM & LUXURY TRANSLATION:\n"
        "1. Tone and vocabulary:\n"
        "   - English ('en'): Evoke bespoke elegance, exclusive privileges, and poetic serenity (e.g., 'Serene sanctuary', 'Heritage journey', 'Curated experiences').\n"
        "   - Vietnamese ('vi'): Use elegant, respectful, and sophisticated Sino-Vietnamese phrasing (e.g., 'Thượng khách', 'Kiệt tác trú ẩn', 'Hành trình di sản', 'Điểm hẹn yên bình').\n"
        "   - Arabic ('ar'): Use Royal Modern Standard Arabic (Fusha) with respectful honorifics (e.g., 'الضيوف الكرام', 'رحلة منسقة خصيصاً', 'ملاذات هادئة'). Ensure proper Right-to-Left layout flow.\n"
        "2. Output format:\n"
        "   - Return ONLY the translation of the input text. Keep HTML tags intact if any exist in the source.\n"
        "   - Do NOT wrap the translation in quotes or code fences. Do NOT include any chat preamble, comments, or explanations."
    )
    
    try:
        agent = Agent(
            model=llm_client.get_model(),
            system_prompt=system_prompt
        )
        res = await agent.run(payload.text)
        translated_text = res.output.strip()
        
        # Clean up any potential markdown code blocks returned by the model
        if translated_text.startswith("```"):
            lines = translated_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            translated_text = "\n".join(lines).strip()
            
        return {"translated_text": translated_text}
    except Exception as e:
        log.exception("[translate-block] Block translation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/quotations/{quotation_id}", response_class=HTMLResponse)
async def get_quotation(quotation_id: str, request: Request):
    """
    Stable permalink for a quotation.
    Loads Single JSON context (ctx.json), extracts language-specific payload,
    builds the localized context, and renders dynamically.
    """
    lang = request.query_params.get("lang") or request.query_params.get("language")
    if lang not in ("en", "vi", "ar"):
        lang = None # fallback to baseline
        
    ctx_data = _load_ctx_data(quotation_id)
    if not ctx_data:
        raise HTTPException(
            status_code=404,
            detail=f"Quotation '{quotation_id}' not found. It may still be deploying, please refresh in 30 seconds."
        )
        
    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = lang or baseline_lang
    
    # Trigger lazy translation if not available
    if target_lang != baseline_lang:
        available_langs = ctx_data.get("available_langs", [])
        if target_lang not in available_langs:
            success = await _translate_item_on_demand(quotation_id, target_lang, is_itinerary=False)
            if success:
                ctx_data = _load_ctx_data(quotation_id) or ctx_data
                
    # Extract appropriate payload dict
    if target_lang == baseline_lang:
        payload_dict = ctx_data.get("baseline_payload")
    else:
        payload_dict = ctx_data.get("translations", {}).get(target_lang)
        
    # Fallback to general context if payload extraction failed
    if not payload_dict:
        log.warning("[get_quotation] Localized payload for %s not found, using baseline", target_lang)
        payload_dict = ctx_data.get("baseline_payload")
        target_lang = baseline_lang
        
    try:
        payload_obj = TourQuotationPayload.model_validate(payload_dict)
        tmpl_name = ctx_data.get("template_name", "vietnam_luxury_brosure.html")
        tmpl = templates.get_template(tmpl_name)
        
        # Build clean context for target lang
        hero_image_url = ctx_data.get("img_0", "/assets/vietnam-safar-logo.png")
        destinations = ctx_data.get("destinations", [])
        translations = ctx_data.get("translations", {})
        
        # Resolve brand from request and payload
        brand_config = resolve_brand(request, payload_dict)

        lang_ctx = _build_ctx(
            quotation_id=quotation_id,
            payload=payload_obj,
            hero_image_url=hero_image_url,
            destinations=destinations,
            lang=target_lang,
            template_name=tmpl_name,
            brand=brand_config,
        )
        lang_ctx["brand"] = brand_config
        lang_ctx["translations"] = translations
        lang_ctx["baseline_lang"] = baseline_lang
        lang_ctx["translation_status"] = ctx_data.get("translation_status", {"baseline_lang": baseline_lang, "available_langs": [baseline_lang]})
        try:
            from github_publish import get_next_version
            next_ver = await get_next_version(quotation_id)
            lang_ctx["latest_version"] = max(1, next_ver - 1)
        except Exception:
            lang_ctx["latest_version"] = 1
        
        # Try to load language-specific published HTML (no fallback)
        latest_lang = None if target_lang == baseline_lang else target_lang
        html_content = await _get_latest_published_html(quotation_id, lang=latest_lang, fallback=False)
        if html_content:
            # Strip the old editor block entirely if it exists in the static HTML to avoid duplicate DOM elements and duplicate IDs (e.g. duplicate domain-modal)
            idx_bar = html_content.find('id="publish-bar"')
            if idx_bar == -1:
                idx_bar = html_content.find("id='publish-bar'")
            if idx_bar != -1:
                idx_start = html_content.rfind('<div', 0, idx_bar)
                if idx_start != -1:
                    idx_scripts = html_content.find('id="editor-scripts"')
                    if idx_scripts == -1:
                        idx_scripts = html_content.find("id='editor-scripts'")
                    if idx_scripts != -1:
                        idx_end_script = html_content.find('</script>', idx_scripts)
                        if idx_end_script != -1:
                            idx_end = idx_end_script + len('</script>')
                            html_content = html_content[:idx_start] + html_content[idx_end:]

            # Re-inject brand data dynamically into the static HTML to support brand switching
            import json
            brand_json = json.dumps(brand_config, ensure_ascii=False)
            import re
            html_content = re.sub(
                r'<script[^>]*id=["\']brand-data["\'][^>]*>.*?</script>',
                f'<script id="brand-data" type="application/json">{brand_json}</script>',
                html_content,
                flags=re.DOTALL
            )
            # Re-inject editor components
            editor_block = extract_editor_components(tmpl.render(**lang_ctx))
            if editor_block:
                # Strip old script blocks containing translateBlock to avoid variable redeclaration SyntaxErrors (let/const)
                import re
                html_content = re.sub(
                    r'<script[^>]*>(?:(?!<\/script>).)*translateBlock(?:(?!<\/script>).)*<\/script>',
                    '',
                    html_content,
                    flags=re.DOTALL
                )
                idx_body = html_content.rfind('</body>')
                if idx_body != -1:
                    html_content = html_content[:idx_body] + editor_block + html_content[idx_body:]
                else:
                    html_content += editor_block
            return HTMLResponse(content=html_content)
            
        # If language-specific published HTML is missing, check if baseline published HTML exists
        # so we can filter out deleted blocks and override baseline edits when rendering fallback JINJA2
        if target_lang != baseline_lang:
            baseline_html = await _get_latest_published_html(quotation_id, lang=None, fallback=False)
            if baseline_html:
                filter_and_override_ctx_by_html(lang_ctx, baseline_html, override_text=False)
                
        rendered_html = tmpl.render(**lang_ctx)
        return HTMLResponse(content=rendered_html)
    except Exception as err:
        log.exception("[/quotations] Dynamic HTML render failed for %s: %s", quotation_id, err)
        raise HTTPException(status_code=500, detail=f"Render error: {err}")



# ── POST /quotations/{id}/publish — commit to GitHub → Vercel ─────────────────

class PublishRequest(BaseModel):
    html: str
    template_name: Optional[str] = None

class ApproveRequest(BaseModel):
    html: str
    token: str

@app.post("/quotations/{quotation_id}/publish")
async def publish_quotation(quotation_id: str, body: PublishRequest, request: Request, lang: str = None, language: str = None):
    """
    Commit the edited HTML (sent from browser) to GitHub published/ folder.
    Does NOT require the in-memory store — quotation_id + html come from the request.
    This makes the endpoint resilient across Vercel serverless instances.
    """
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    log.info("[publish] Received publish for quotation_id=%s, template_name=%s, target_lang=%s", quotation_id, body.template_name, target_lang)

    # Fetch the next version from GitHub directly to ensure it works across serverless instances
    from github_publish import get_next_version, publish_to_github
    version = await get_next_version(quotation_id)

    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    
    ctx_data = _load_ctx_data(quotation_id)
    baseline_lang = "en"
    rendered_pdf = None
    effective_lang = target_lang
    if ctx_data:
        baseline_lang = ctx_data.get("baseline_lang", "en")
        
        # Extract custom images and store in ctx_data
        custom_images = _extract_custom_images_from_html(body.html)
        ctx_data.update(custom_images)
        
        if body.template_name and ctx_data.get("template_name") != body.template_name:
            ctx_data["template_name"] = body.template_name
            ctx_data["html_sync"] = {}
            new_html, _ = await _render_quotation_doc_from_ctx(
                ctx_data,
                quotation_id,
                target_lang or baseline_lang,
                request=request,
                is_pdf=False,
                ignore_published_html=True,
            )
            _save_ctx_html_sync_state(ctx_data, target_lang, new_html, captured_from_version=version)
            # Strip editor scripts before publishing
            idx_bar = new_html.find('id="publish-bar"')
            if idx_bar == -1:
                idx_bar = new_html.find("id='publish-bar'")
            if idx_bar != -1:
                idx_start = new_html.rfind('<div', 0, idx_bar)
                if idx_start != -1:
                    idx_scripts = new_html.find('id="editor-scripts"')
                    if idx_scripts == -1:
                        idx_scripts = new_html.find("id='editor-scripts'")
                    if idx_scripts != -1:
                        idx_end_script = new_html.find('</script>', idx_scripts)
                        if idx_end_script != -1:
                            idx_end = idx_end_script + len('</script>')
                            new_html = new_html[:idx_start] + new_html[idx_end:]
            body.html = new_html
        else:
            _save_ctx_html_sync_state(ctx_data, target_lang, body.html, captured_from_version=version)

        rendered_pdf, effective_lang = await _render_quotation_doc_from_ctx(
            ctx_data,
            quotation_id,
            target_lang or baseline_lang,
            request=request,
            is_pdf=True,
            ignore_published_html=bool(body.template_name),
        )

        if quotation_id in quotations:
            quotations[quotation_id]["ctx"] = ctx_data

    lang_suffix = f"_{target_lang}" if target_lang and target_lang != baseline_lang else ""
    filename = f"v{version}{lang_suffix}.html"

    if ENVIRONMENT == "production":
        try:
            # Publish files sequentially to avoid 409 conflict
            published_url = await publish_to_github(
                quotation_id=quotation_id,
                html_content=body.html,
                version=version,
                lang=target_lang,
                baseline_lang=baseline_lang
            )
            if ctx_data and rendered_pdf is not None:
                pdf_suffix = "" if effective_lang == baseline_lang else f"_{effective_lang}"
                pdf_files = {f"published/{quotation_id}/pdf{pdf_suffix}.html"}
                if effective_lang == baseline_lang:
                    pdf_files.add(f"published/{quotation_id}/pdf_{effective_lang}.html")
                for pdf_path in sorted(pdf_files):
                    await publish_file_to_github(
                        file_path=pdf_path,
                        html_content=rendered_pdf,
                        commit_message=f"Update PDF view for quotation {quotation_id} {os.path.basename(pdf_path)} (version {version})",
                    )
                await publish_file_to_github(
                    file_path=f"published/{quotation_id}/ctx.json",
                    html_content=json.dumps(ctx_data, ensure_ascii=False, default=str),
                    commit_message=f"Update context for quotation {quotation_id} (version {version})",
                )
        except Exception as exc:
            log.exception("[publish] Failed for %s", quotation_id)
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        # Localhost: write to disk
        quo_dir = os.path.join("published", quotation_id)
        os.makedirs(quo_dir, exist_ok=True)
        file_path = os.path.join(quo_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body.html)
        if ctx_data and rendered_pdf is not None:
            with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as f:
                json.dump(ctx_data, f, ensure_ascii=False, default=str)
            pdf_suffix = "" if effective_lang == baseline_lang else f"_{effective_lang}"
            pdf_paths = {os.path.join(quo_dir, f"pdf{pdf_suffix}.html")}
            if effective_lang == baseline_lang:
                pdf_paths.add(os.path.join(quo_dir, f"pdf_{effective_lang}.html"))
            for pdf_path in pdf_paths:
                with open(pdf_path, "w", encoding="utf-8") as f:
                    f.write(rendered_pdf)
        published_url = f"{PUBLIC_BASE_URL}/published/{quotation_id}/{filename}"
        log.info("[publish] Localhost: wrote to disk %s", file_path)

    # Update in-memory store if entry exists (same instance flow)
    entry = quotations.get(quotation_id)
    if entry:
        entry["status"]        = "published"
        entry["published_url"] = published_url
        entry["html"]          = body.html
        if ctx_data:
            entry["ctx"] = ctx_data
        if rendered_pdf is not None:
            entry["pdf_html"] = rendered_pdf
        entry["version"]       = version

    log.info("[publish] ✓ %s v%d (lang=%s) → %s", quotation_id, version, target_lang, published_url)
    return {"published_url": published_url, "version": version, "status": "published"}



# ── Detailed Itinerary Endpoints ─────────────────────────────────────────────

@app.post("/itineraries")
async def create_itinerary(request: Request):
    """
    Receives structured itinerary data, renders a Jinja2 template with booked services,
    stores it locally or on GitHub, and returns the preview/PDF URLs.
    """
    body = await request.json()
    log.debug("[/itineraries] Incoming keys: %s", list(body.keys()))

    # Unwrap ChatGPT Action wrapper if present
    data = body.get("params", body)
    log.debug("[/itineraries] Data keys after unwrap: %s", list(data.keys()))
    lang = data.get("language") or data.get("lang") or request.query_params.get("lang") or request.query_params.get("language") or "en"
    if lang not in ("en", "vi", "ar"):
        lang = "en"

    try:
        payload = DetailItineraryPayload.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        log.error("[/itineraries] Pydantic validation failed — %d error(s):\n%s",
                  len(errors), json.dumps(errors, indent=2, default=str))
        return JSONResponse(status_code=422, content={"detail": errors,
            "hint": "Field path is in 'loc'. Check which required field is missing."})

    itinerary_id = f"iti_{uuid.uuid4().hex[:12]}"

    # Extract destinations from route + itinerary for the gallery
    route_text = " ".join(payload.route)
    itinerary_text = " ".join(
        " ".join(day.destinations or []) + " " + day.title
        for day in payload.itinerary
    )
    text_context = route_text + " " + itinerary_text
    if payload.notes:
        text_context += " " + " ".join(payload.notes)

    from image_selector import (
        extract_and_map_destinations,
        get_random_image_for_province,
        get_province_slug_for_location,
        resolve_slug_locally,
        resolve_slug_from_known,
        get_all_images_for_province,
    )
    destinations = await extract_and_map_destinations(text_context, max_items=None)

    # Resolve image urls for each destination
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))
        d["images"] = get_all_images_for_province(d.get("slug"))

    log.debug("[/itineraries] Extracted destinations: %s", destinations)

    default_img = "/assets/vietnam-safar-logo.png"

    # Hero image: Pick a random image from the resolved destinations, or default
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/itineraries] Hero image resolved: %s", hero_image_url)

    # ── Smart slug resolver for hotels & activities ───────────────────────────
    # Tái sử dụng kết quả đã extract — KHÔNG gọi OpenAI thêm nếu không cần thiết.
    #
    # Thứ tự ưu tiên:
    #   1. resolve_slug_locally()     → tra KEYWORD_MAP tĩnh (không cần mạng)
    #   2. resolve_slug_from_known()  → tra bảng destinations đã extract (không cần mạng)
    #   3. random.choice(extracted_slugs) → fallback ngẫu nhiên từ tour này (không cần mạng)
    #   4. get_province_slug_for_location() → last resort: gọi OpenAI (hiếm khi cần)
    #
    extracted_slugs = [d["slug"] for d in destinations if d.get("slug")]
    known_slugs = {d["name"].lower(): d["slug"] for d in destinations if d.get("name") and d.get("slug")}

    async def _resolve_slug_smart(location: str | None) -> str | None:
        """3-tier resolver: local map → known slugs → random fallback → OpenAI last resort."""
        if not location:
            return random.choice(extracted_slugs) if extracted_slugs else None
        # Tầng 1: local keyword map (pure Python)
        slug = resolve_slug_locally(location)
        if slug:
            log.debug("[slug] '%s' → '%s' (local map)", location, slug)
            return slug
        # Tầng 2: từ bảng destinations đã extract (pure Python)
        slug = resolve_slug_from_known(location, known_slugs)
        if slug:
            log.debug("[slug] '%s' → '%s' (known slugs)", location, slug)
            return slug
        # Tầng 3: chọn ngẫu nhiên từ slugs đã biết trong tour (pure Python)
        if extracted_slugs:
            slug = random.choice(extracted_slugs)
            log.debug("[slug] '%s' → '%s' (random fallback)", location, slug)
            return slug
        # Tầng 4: last resort — gọi OpenAI (chỉ khi không có bất kỳ thông tin nào)
        log.warning("[slug] '%s' → calling OpenAI (last resort)", location)
        return await get_province_slug_for_location(location)

    # Hotels — resolve tất cả song song (asyncio.gather)
    hotels_without_img = [h for h in payload.hotels if not h.imageUrl]
    if hotels_without_img:
        hotel_slugs = await asyncio.gather(
            *[_resolve_slug_smart(h.destination or h.addressArea) for h in hotels_without_img]  # type: ignore
        )
        for h, slug in zip(hotels_without_img, hotel_slugs):
            h.imageUrl = get_random_image_for_province(slug)

    # Activities — resolve tất cả song song (asyncio.gather)
    activities_without_img = [act for act in payload.activities if not act.imageUrl]
    if activities_without_img:
        activity_slugs = await asyncio.gather(
            *[_resolve_slug_smart(act.area or act.activityName) for act in activities_without_img]
        )
        for act, slug in zip(activities_without_img, activity_slugs):
            act.imageUrl = get_random_image_for_province(slug)

    ctx = _build_itinerary_ctx(itinerary_id, payload, hero_image_url, destinations, lang=lang, template_name="detail_itinerary_landingpage_template.html")
    ctx["baseline_payload"] = payload.model_dump(mode="json")
    ctx["baseline_lang"] = lang
    ctx["translations"] = {}
    ctx["available_langs"] = [lang]
    ctx["translation_status"] = {"baseline_lang": lang, "available_langs": [lang]}
    ctx["brand"] = resolve_brand(request, payload.model_dump(mode="json"))

    # Render landing page HTML and PDF
    loop = asyncio.get_event_loop()
    tmpl_lp  = templates.get_template("detail_itinerary_landingpage_template.html")
    tmpl_pdf = templates.get_template("detail_itinerary_landingpage_template_pdf.html")

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render,  **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )

    # Update in-memory store
    itineraries[itinerary_id] = {
        "payload":       payload.model_dump(mode="json"),
        "ctx":           ctx,
        "html":          rendered_html,
        "pdf_html":      rendered_pdf,
        "status":        "pending",
        "published_url": None,
        "pdf_url":       None,
        "version":       0,
    }

    sfx = f"_{lang}" if lang != "en" else ""
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

    if ENVIRONMENT == "production":
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            log.error("[/itineraries] GITHUB_TOKEN or GITHUB_REPO not set — cannot persist on Vercel.")
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: GITHUB_TOKEN / GITHUB_REPO env vars are missing.",
            )
        try:
            # Commit to GitHub
            # Publish files sequentially to avoid 409 conflict
            await publish_file_to_github(
                file_path=f"published/{itinerary_id}/v1{sfx}.html",
                html_content=rendered_html,
                commit_message=f"Publish itinerary {itinerary_id} v1{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{itinerary_id}/pdf{sfx}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish PDF view for itinerary {itinerary_id} pdf{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{itinerary_id}/ctx.json",
                html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                commit_message=f"Publish itinerary context for {itinerary_id}",
            )
            await publish_file_to_github(
                file_path=f"published/{itinerary_id}/payload.json",
                html_content=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
                commit_message=f"Publish itinerary payload for {itinerary_id}",
            )
            # Initialize and save translation status
            await _save_translation_status(itinerary_id, {"baseline_lang": lang, "available_langs": [lang]})
            
            itineraries[itinerary_id]["status"]        = "published"
            itineraries[itinerary_id]["published_url"] = f"{PUBLIC_BASE_URL}/itineraries/{itinerary_id}"
            itineraries[itinerary_id]["pdf_url"]       = f"{PUBLIC_BASE_URL}/itineraries/{itinerary_id}/pdf"
            itineraries[itinerary_id]["version"]       = 1
            log.info("[/itineraries] ✓ v1{sfx} + pdf{sfx} committed to GitHub.")
        except Exception as exc:
            log.exception("[/itineraries] GitHub publish FAILED for %s: %s", itinerary_id, exc)
            raise HTTPException(
                status_code=502,
                detail=f"GitHub publish failed: {exc}.",
            )
    else:
        # Localhost: write to disk
        iti_dir = os.path.join("published", itinerary_id)
        os.makedirs(iti_dir, exist_ok=True)
        with open(os.path.join(iti_dir, f"v1{sfx}.html"),  "w", encoding="utf-8") as _f:
            _f.write(rendered_html)
        with open(os.path.join(iti_dir, f"pdf{sfx}.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(iti_dir, "ctx.json"), "w", encoding="utf-8") as _f:
            json.dump(ctx, _f, ensure_ascii=False, default=str)
        with open(os.path.join(iti_dir, "payload.json"), "w", encoding="utf-8") as _f:
            json.dump(payload.model_dump(mode="json"), _f, ensure_ascii=False)
        await _save_translation_status(itinerary_id, {"baseline_lang": lang, "available_langs": [lang]})
        
        itineraries[itinerary_id]["status"]  = "published"
        itineraries[itinerary_id]["version"] = 1
        log.info("[/itineraries] Localhost: v1{sfx}.html + pdf{sfx}.html + ctx.json written to disk.")

    log.info("[/itineraries] ✓ id=%s  preparedFor=%s  days=%d",
             itinerary_id, payload.preparedFor, payload.duration.days)

    itinerary_url = f"{PUBLIC_BASE_URL}/itineraries/{itinerary_id}"
    return {
        "itineraryId":  itinerary_id,
        "status":       "published",
        "version":      1,
        "message":      "Itinerary page published. Open itineraryUrl to preview and edit inline.",
        "itineraryUrl": itinerary_url,
        "pdfUrl":       f"{PUBLIC_BASE_URL}/itineraries/{itinerary_id}/pdf",
    }


@app.get("/itineraries/{itinerary_id}", response_class=HTMLResponse)
async def get_itinerary(itinerary_id: str, request: Request):
    """
    Stable permalink for an itinerary.
    Loads Single JSON context (ctx.json), extracts language-specific payload,
    builds the localized context, and renders dynamically.
    """
    lang = request.query_params.get("lang") or request.query_params.get("language")
    if lang not in ("en", "vi", "ar"):
        lang = None # fallback to baseline
        
    ctx_data = _load_ctx_data(itinerary_id)
    if not ctx_data:
        raise HTTPException(
            status_code=404,
            detail=f"Itinerary '{itinerary_id}' not found. It may still be deploying, please refresh in 30 seconds."
        )
        
    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = lang or baseline_lang
    
    # Trigger lazy translation if not available
    if target_lang != baseline_lang:
        available_langs = ctx_data.get("available_langs", [])
        if target_lang not in available_langs:
            success = await _translate_item_on_demand(itinerary_id, target_lang, is_itinerary=True)
            if success:
                ctx_data = _load_ctx_data(itinerary_id) or ctx_data
                
    # Extract appropriate payload dict
    if target_lang == baseline_lang:
        payload_dict = ctx_data.get("baseline_payload")
    else:
        payload_dict = ctx_data.get("translations", {}).get(target_lang)
        
    # Fallback to general context if payload extraction failed
    if not payload_dict:
        log.warning("[get_itinerary] Localized payload for %s not found, using baseline", target_lang)
        payload_dict = ctx_data.get("baseline_payload")
        target_lang = baseline_lang
        
    try:
        payload_obj = DetailItineraryPayload.model_validate(payload_dict)
        tmpl_name = ctx_data.get("template_name", "detail_itinerary_landingpage_template.html")
        tmpl = templates.get_template(tmpl_name)
        
        # Build clean context for target lang
        hero_image_url = ctx_data.get("img_0", "/assets/vietnam-safar-logo.png")
        destinations = ctx_data.get("destinations", [])
        translations = ctx_data.get("translations", {})
        
        # Resolve brand from request and payload
        brand_config = resolve_brand(request, payload_dict)

        lang_ctx = _build_itinerary_ctx(
            itinerary_id=itinerary_id,
            payload=payload_obj,
            hero_image_url=hero_image_url,
            destinations=destinations,
            lang=target_lang,
            template_name=tmpl_name
        )
        lang_ctx["brand"] = brand_config
        lang_ctx["translations"] = translations
        lang_ctx["baseline_lang"] = baseline_lang
        lang_ctx["translation_status"] = ctx_data.get("translation_status", {"baseline_lang": baseline_lang, "available_langs": [baseline_lang]})
        try:
            from github_publish import get_next_version
            next_ver = await get_next_version(itinerary_id)
            lang_ctx["latest_version"] = max(1, next_ver - 1)
        except Exception:
            lang_ctx["latest_version"] = 1
        
        # Try to load language-specific published HTML (no fallback)
        latest_lang = None if target_lang == baseline_lang else target_lang
        html_content = await _get_latest_published_html(itinerary_id, lang=latest_lang, fallback=False)
        if html_content:
            # Re-inject brand data dynamically into the static HTML to support brand switching
            import json
            brand_json = json.dumps(brand_config, ensure_ascii=False)
            import re
            html_content = re.sub(
                r'<script[^>]*id=["\']brand-data["\'][^>]*>.*?</script>',
                f'<script id="brand-data" type="application/json">{brand_json}</script>',
                html_content,
                flags=re.DOTALL
            )
            # Re-enable editor publish bar by making it visible
            html_content = make_itinerary_editor_visible(html_content)
            return HTMLResponse(content=html_content)
            
        # If language-specific published HTML is missing, check if baseline published HTML exists
        # so we can filter out deleted blocks when rendering fallback JINJA2
        if target_lang != baseline_lang:
            baseline_html = await _get_latest_published_html(itinerary_id, lang=None, fallback=False)
            if baseline_html:
                from html.parser import HTMLParser
                class ActiveParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.active_days = set()
                        self.active_cards = {"hotel": set(), "activity": set(), "transfer": set(), "flight": set(), "guide": set()}
                    def handle_starttag(self, tag, attrs):
                        attrs_dict = dict(attrs)
                        if tag == 'div' and 'data-day-number' in attrs_dict:
                            try: self.active_days.add(int(attrs_dict['data-day-number']))
                            except ValueError: pass
                        if 'class' in attrs_dict and 'service-card' in attrs_dict['class']:
                            c_type = attrs_dict.get("data-type")
                            idx_str = attrs_dict.get("data-index")
                            if c_type in self.active_cards and idx_str is not None:
                                try: self.active_cards[c_type].add(int(idx_str))
                                except ValueError: pass
                p = ActiveParser()
                p.feed(baseline_html)
                sync_itinerary_deletions_to_payloads(lang_ctx, p.active_days, p.active_cards)
                
        rendered_html = tmpl.render(**lang_ctx)
        return HTMLResponse(content=rendered_html)
    except Exception as err:
        log.exception("[/itineraries] Dynamic HTML render failed for %s: %s", itinerary_id, err)
        raise HTTPException(status_code=500, detail=f"Render error: {err}")


@app.get("/itineraries/{itinerary_id}/pdf", response_class=HTMLResponse)
async def get_itinerary_pdf(itinerary_id: str, request: Request):
    """
    Dynamically renders PDF HTML for an itinerary in target language.
    Auto-triggers the browser print dialog.
    """
    lang = request.query_params.get("lang") or request.query_params.get("language")
    if lang not in ("en", "vi", "ar"):
        lang = None
        
    ctx_data = _load_ctx_data(itinerary_id)
    if not ctx_data:
        raise HTTPException(status_code=404, detail=f"PDF for itinerary '{itinerary_id}' not found.")
        
    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = lang or baseline_lang
    
    # Trigger lazy translation if not available
    if target_lang != baseline_lang:
        available_langs = ctx_data.get("available_langs", [])
        if target_lang not in available_langs:
            success = await _translate_item_on_demand(itinerary_id, target_lang, is_itinerary=True)
            if success:
                ctx_data = _load_ctx_data(itinerary_id) or ctx_data
                
    # Extract appropriate payload dict
    if target_lang == baseline_lang:
        payload_dict = ctx_data.get("baseline_payload")
    else:
        payload_dict = ctx_data.get("translations", {}).get(target_lang)
        
    if not payload_dict:
        payload_dict = ctx_data.get("baseline_payload")
        target_lang = baseline_lang
        
    try:
        payload_obj = DetailItineraryPayload.model_validate(payload_dict)
        base_tmpl = ctx_data.get("template_name", "detail_itinerary_landingpage_template.html")
        tmpl_name = base_tmpl.replace(".html", "_pdf.html")
        tmpl = templates.get_template(tmpl_name)
        
        hero_image_url = ctx_data.get("img_0", "/assets/vietnam-safar-logo.png")
        destinations = ctx_data.get("destinations", [])
        translations = ctx_data.get("translations", {})
        
        # Resolve brand from request and payload
        brand_config = resolve_brand(request, payload_dict)

        lang_ctx = _build_itinerary_ctx(
            itinerary_id=itinerary_id,
            payload=payload_obj,
            hero_image_url=hero_image_url,
            destinations=destinations,
            lang=target_lang,
            template_name=base_tmpl
        )
        lang_ctx["brand"] = brand_config
        lang_ctx["translations"] = translations
        lang_ctx["baseline_lang"] = baseline_lang
        lang_ctx["translation_status"] = ctx_data.get("translation_status", {"baseline_lang": baseline_lang, "available_langs": [baseline_lang]})
        try:
            from github_publish import get_next_version
            next_ver = await get_next_version(itinerary_id)
            lang_ctx["latest_version"] = max(1, next_ver - 1)
        except Exception:
            lang_ctx["latest_version"] = 1
        
        rendered_html = tmpl.render(**lang_ctx)
        return HTMLResponse(content=rendered_html)
    except Exception as err:
        log.exception("[/itineraries] Dynamic PDF render failed for %s: %s", itinerary_id, err)
        raise HTTPException(status_code=500, detail=f"PDF render error: {err}")


@app.post("/itineraries/{itinerary_id}/publish")
async def publish_itinerary(itinerary_id: str, body: PublishRequest, lang: str = None, language: str = None):
    """ Saves inline edits back to the system. """
    from github_publish import get_next_version, publish_to_github
    version = await get_next_version(itinerary_id)

    # Update ctx.json and pdf.html using values from the edited HTML
    from html.parser import HTMLParser
    
    class ServiceCardParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cards = []
            self.active_days = set()
            self.active_cards = {"hotel": set(), "activity": set(), "transfer": set(), "flight": set(), "guide": set()}
            
        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if tag == 'div' and 'data-day-number' in attrs_dict:
                try:
                    self.active_days.add(int(attrs_dict['data-day-number']))
                except ValueError:
                    pass
            if 'class' in attrs_dict and 'service-card' in attrs_dict['class']:  # type: ignore
                self.cards.append(attrs_dict)
                c_type = attrs_dict.get("data-type")
                idx_str = attrs_dict.get("data-index")
                if c_type in self.active_cards and idx_str is not None:
                    try:
                        self.active_cards[c_type].add(int(idx_str))
                    except ValueError:
                        pass

    parser = ServiceCardParser()
    parser.feed(body.html)
    
    ctx = _load_itinerary_ctx(itinerary_id)
    if ctx:
        sync_itinerary_deletions_to_payloads(ctx, parser.active_days, parser.active_cards)
    rendered_pdf = None
    if ctx:
        for card in parser.cards:
            card_type = card.get("data-type")
            idx_str = card.get("data-index")
            if idx_str is None:
                continue
            idx = int(idx_str)
            
            if card_type == "hotel":
                if idx < len(ctx.get("hotels", [])):
                    h = ctx["hotels"][idx]
                    h["pricePerNightUsd"] = float(card.get("data-price-per-night", 0))
                    h["nights"] = int(card.get("data-nights", 0))
                    h["rooms"] = int(card.get("data-rooms", 1))
            elif card_type == "activity":
                if idx < len(ctx.get("activities", [])):
                    act = ctx["activities"][idx]
                    act["pricePerAdultUsd"] = float(card.get("data-price-adult", 0))
                    act["pricePerChildUsd"] = float(card.get("data-price-child", 0))
                    adults = int(card.get("data-adults", ctx.get("guests_adults") or 0))
                    children = int(card.get("data-children", ctx.get("guests_children") or 0))
                    act["totalEstimateUsd"] = (act["pricePerAdultUsd"] * adults) + (act["pricePerChildUsd"] * children)
            elif card_type == "transfer":
                if idx < len(ctx.get("transfers", [])):
                    tx = ctx["transfers"][idx]
                    base = float(card.get("data-base-cost", 0))
                    tolls = float(card.get("data-tolls", 0))
                    overnight = float(card.get("data-overnight", 0))
                    surcharges = float(card.get("data-surcharges", 0))
                    vat = float(card.get("data-vat", 0))
                    tx["priceUsd"] = base + tolls + overnight + surcharges + vat
            elif card_type == "flight":
                if idx < len(ctx.get("flights", [])):
                    fl = ctx["flights"][idx]
                    fl["priceUsd"] = float(card.get("data-price-ticket", 0))
            elif card_type == "guide":
                if idx < len(ctx.get("guides", [])):
                    gd = ctx["guides"][idx]
                    gd["pricePerDayUsd"] = float(card.get("data-price-day", 0))
                    gd["days"] = int(card.get("data-days", 0))
                    gd["totalEstimateUsd"] = gd["pricePerDayUsd"] * gd["days"]

        # Recalculate Grand Total in ctx
        grand_total = 0.0
        for h in ctx.get("hotels", []):
            grand_total += (h.get("pricePerNightUsd") or 0.0) * (h.get("nights") or 0) * (h.get("rooms") or 1)
        for act in ctx.get("activities", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (act.get("pricePerAdultUsd") or 0.0) * adults + (act.get("pricePerChildUsd") or 0.0) * children
        for tx in ctx.get("transfers", []):
            grand_total += tx.get("priceUsd") or 0.0
        for fl in ctx.get("flights", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (fl.get("priceUsd") or 0.0) * (adults + children)
        for gd in ctx.get("guides", []):
            grand_total += (gd.get("pricePerDayUsd") or 0.0) * (gd.get("days") or 0)

        ctx["grand_total"] = grand_total
        
        if ctx.get("price_options"):
            for opt in ctx["price_options"]:
                if opt.get("isConfirmedMainOption"):
                    opt["totalPrice"]["amount"] = grand_total
                    opt["totalPrice"]["displayText"] = f"${grand_total:,.0f} total"
                    guests_adults = ctx.get("guests_adults") or 1
                    per_person = grand_total / guests_adults
                    opt["pricePerPerson"]["amount"] = per_person
                    opt["pricePerPerson"]["displayText"] = f"${per_person:,.0f} per adult"
            
            main_option = next((o for o in ctx["price_options"] if o.get("isConfirmedMainOption")), None)
            if main_option:
                ctx["total_price"] = main_option["totalPrice"]["displayText"]
                ctx["price_per_pax"] = main_option["pricePerPerson"]["displayText"]
                ctx["pricing_h2"] = f"Indicative Price: {ctx['total_price']}"
                ctx["pricing_p"] = f"Grand total for {ctx['guests_txt']}. Currency: {ctx['currency']}."

        loop = asyncio.get_event_loop()
        tmpl_pdf = templates.get_template("detail_itinerary_landingpage_template_pdf.html")
        rendered_pdf = await loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx))
        
        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            from github_publish import publish_file_to_github
            try:
                # Publish files sequentially to avoid 409 conflict
                await publish_file_to_github(
                    file_path=f"published/{itinerary_id}/pdf.html",
                    html_content=rendered_pdf,
                    commit_message=f"Update PDF view for itinerary {itinerary_id} (version {version})",
                )
                await publish_file_to_github(
                    file_path=f"published/{itinerary_id}/ctx.json",
                    html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                    commit_message=f"Update context for itinerary {itinerary_id} (version {version})",
                )
            except Exception as e:
                log.warning("Failed to publish updated PDF/ctx to GitHub: %s", e)
        else:
            iti_dir = os.path.join("published", itinerary_id)
            os.makedirs(iti_dir, exist_ok=True)
            with open(os.path.join(iti_dir, "ctx.json"), "w", encoding="utf-8") as _f:
                json.dump(ctx, _f, ensure_ascii=False, default=str)
            with open(os.path.join(iti_dir, "pdf.html"), "w", encoding="utf-8") as _f:
                _f.write(rendered_pdf)

    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    baseline_lang = "en"
    if ctx:
        baseline_lang = ctx.get("baseline_lang", "en")

    lang_suffix = f"_{target_lang}" if target_lang and target_lang != baseline_lang else ""
    filename = f"v{version}{lang_suffix}.html"

    if ENVIRONMENT == "production":
        try:
            published_url = await publish_to_github(
                quotation_id=itinerary_id,
                html_content=body.html,
                version=version,
                lang=target_lang,
                baseline_lang=baseline_lang
            )
        except Exception as exc:
            log.exception("[publish_itinerary] Failed for %s", itinerary_id)
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        # Localhost: write to disk
        iti_dir = os.path.join("published", itinerary_id)
        os.makedirs(iti_dir, exist_ok=True)
        file_path = os.path.join(iti_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body.html)
        published_url = f"{PUBLIC_BASE_URL}/published/{itinerary_id}/{filename}"
        log.info("[publish_itinerary] Localhost: wrote to disk %s", file_path)

    entry = itineraries.get(itinerary_id)
    if entry:
        entry["status"]        = "published"
        entry["published_url"] = published_url
        entry["html"]          = body.html
        if ctx:
            entry["ctx"]       = ctx
            entry["pdf_html"]  = rendered_pdf
        entry["version"]       = version

    log.info("[publish_itinerary] ✓ %s v%d → %s", itinerary_id, version, published_url)
    return {"published_url": published_url, "version": version, "status": "published"}


@app.post("/itineraries/{itinerary_id}/approve")
async def approve_itinerary(itinerary_id: str, body: ApproveRequest):
    """
    Saves inline edits back to the system, recalculates ctx/PDF,
    and calls the DMC Core webhook with the JWT token.
    """
    from github_publish import get_next_version, publish_to_github
    version = await get_next_version(itinerary_id)

    # 1. Update ctx.json and pdf.html using values from the edited HTML
    from html.parser import HTMLParser
    
    class ServiceCardParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cards = []
            self.active_days = set()
            self.active_cards = {"hotel": set(), "activity": set(), "transfer": set(), "flight": set(), "guide": set()}
            
        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if tag == 'div' and 'data-day-number' in attrs_dict:
                try:
                    self.active_days.add(int(attrs_dict['data-day-number']))
                except ValueError:
                    pass
            if 'class' in attrs_dict and 'service-card' in attrs_dict['class']:  # type: ignore
                self.cards.append(attrs_dict)
                c_type = attrs_dict.get("data-type")
                idx_str = attrs_dict.get("data-index")
                if c_type in self.active_cards and idx_str is not None:
                    try:
                        self.active_cards[c_type].add(int(idx_str))
                    except ValueError:
                        pass

    parser = ServiceCardParser()
    parser.feed(body.html)
    
    ctx = _load_itinerary_ctx(itinerary_id)
    if ctx:
        sync_itinerary_deletions_to_payloads(ctx, parser.active_days, parser.active_cards)
    rendered_pdf = None
    if ctx:
        for card in parser.cards:
            card_type = card.get("data-type")
            idx_str = card.get("data-index")
            if idx_str is None:
                continue
            idx = int(idx_str)
            
            if card_type == "hotel":
                if idx < len(ctx.get("hotels", [])):
                    h = ctx["hotels"][idx]
                    h["pricePerNightUsd"] = float(card.get("data-price-per-night", 0))
                    h["nights"] = int(card.get("data-nights", 0))
                    h["rooms"] = int(card.get("data-rooms", 1))
            elif card_type == "activity":
                if idx < len(ctx.get("activities", [])):
                    act = ctx["activities"][idx]
                    act["pricePerAdultUsd"] = float(card.get("data-price-adult", 0))
                    act["pricePerChildUsd"] = float(card.get("data-price-child", 0))
                    adults = int(card.get("data-adults", ctx.get("guests_adults") or 0))
                    children = int(card.get("data-children", ctx.get("guests_children") or 0))
                    act["totalEstimateUsd"] = (act["pricePerAdultUsd"] * adults) + (act["pricePerChildUsd"] * children)
            elif card_type == "transfer":
                if idx < len(ctx.get("transfers", [])):
                    tx = ctx["transfers"][idx]
                    base = float(card.get("data-base-cost", 0))
                    tolls = float(card.get("data-tolls", 0))
                    overnight = float(card.get("data-overnight", 0))
                    surcharges = float(card.get("data-surcharges", 0))
                    vat = float(card.get("data-vat", 0))
                    tx["priceUsd"] = base + tolls + overnight + surcharges + vat
            elif card_type == "flight":
                if idx < len(ctx.get("flights", [])):
                    fl = ctx["flights"][idx]
                    fl["priceUsd"] = float(card.get("data-price-ticket", 0))
            elif card_type == "guide":
                if idx < len(ctx.get("guides", [])):
                    gd = ctx["guides"][idx]
                    gd["pricePerDayUsd"] = float(card.get("data-price-day", 0))
                    gd["days"] = int(card.get("data-days", 0))
                    gd["totalEstimateUsd"] = gd["pricePerDayUsd"] * gd["days"]

        # Recalculate Grand Total in ctx
        grand_total = 0.0
        for h in ctx.get("hotels", []):
            grand_total += (h.get("pricePerNightUsd") or 0.0) * (h.get("nights") or 0) * (h.get("rooms") or 1)
        for act in ctx.get("activities", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (act.get("pricePerAdultUsd") or 0.0) * adults + (act.get("pricePerChildUsd") or 0.0) * children
        for tx in ctx.get("transfers", []):
            grand_total += tx.get("priceUsd") or 0.0
        for fl in ctx.get("flights", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (fl.get("priceUsd") or 0.0) * (adults + children)
        for gd in ctx.get("guides", []):
            grand_total += (gd.get("pricePerDayUsd") or 0.0) * (gd.get("days") or 0)

        ctx["grand_total"] = grand_total
        
        if ctx.get("price_options"):
            for opt in ctx["price_options"]:
                if opt.get("isConfirmedMainOption"):
                    opt["totalPrice"]["amount"] = grand_total
                    opt["totalPrice"]["displayText"] = f"${grand_total:,.0f} total"
                    guests_adults = ctx.get("guests_adults") or 1
                    per_person = grand_total / guests_adults
                    opt["pricePerPerson"]["amount"] = per_person
                    opt["pricePerPerson"]["displayText"] = f"${per_person:,.0f} per adult"
            
            main_option = next((o for o in ctx["price_options"] if o.get("isConfirmedMainOption")), None)
            if main_option:
                ctx["total_price"] = main_option["totalPrice"]["displayText"]
                ctx["price_per_pax"] = main_option["pricePerPerson"]["displayText"]
                ctx["pricing_h2"] = f"Indicative Price: {ctx['total_price']}"
                ctx["pricing_p"] = f"Grand total for {ctx['guests_txt']}. Currency: {ctx['currency']}."

        loop = asyncio.get_event_loop()
        tmpl_pdf = templates.get_template("detail_itinerary_landingpage_template_pdf.html")
        rendered_pdf = await loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx))
        
        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            from github_publish import publish_file_to_github
            try:
                # Publish files sequentially to avoid 409 conflict
                await publish_file_to_github(
                    file_path=f"published/{itinerary_id}/pdf.html",
                    html_content=rendered_pdf,
                    commit_message=f"Update PDF view for approved itinerary {itinerary_id} (version {version})",
                )
                await publish_file_to_github(
                    file_path=f"published/{itinerary_id}/ctx.json",
                    html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                    commit_message=f"Update context for approved itinerary {itinerary_id} (version {version})",
                )
            except Exception as e:
                log.warning("Failed to publish approved PDF/ctx to GitHub: %s", e)
        else:
            iti_dir = os.path.join("published", itinerary_id)
            os.makedirs(iti_dir, exist_ok=True)
            with open(os.path.join(iti_dir, "ctx.json"), "w", encoding="utf-8") as _f:
                json.dump(ctx, _f, ensure_ascii=False, default=str)
            with open(os.path.join(iti_dir, "pdf.html"), "w", encoding="utf-8") as _f:
                _f.write(rendered_pdf)

    # 2. Save the edited HTML
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        try:
            published_url = await publish_to_github(
                quotation_id=itinerary_id,
                html_content=body.html,
                version=version,
            )
        except Exception as exc:
            log.exception("[approve_itinerary] Failed to publish HTML for %s", itinerary_id)
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        # Localhost: write to disk
        iti_dir = os.path.join("published", itinerary_id)
        os.makedirs(iti_dir, exist_ok=True)
        filename = f"v{version}.html"
        file_path = os.path.join(iti_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body.html)
        published_url = f"{PUBLIC_BASE_URL}/published/{itinerary_id}/{filename}"
        log.info("[approve_itinerary] Localhost: wrote to disk %s", file_path)

    # Update in-memory
    entry = itineraries.get(itinerary_id)
    if entry:
        entry["status"]        = "approved"
        entry["published_url"] = published_url
        entry["html"]          = body.html
        if ctx:
            entry["ctx"]       = ctx
            entry["pdf_html"]  = rendered_pdf
        entry["version"]       = version

    # 3. Webhook callback to DMC Core
    dmc_core_url = (os.environ.get("DMC_CORE_URL") or "http://localhost:8000").rstrip("/")
    webhook_url = f"{dmc_core_url}/webhooks/landing-page/approve"
    log.info("[approve_itinerary] Triggering callback to DMC Core: %s", webhook_url)
    
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {body.token}"}
            payload = {
                "itinerary_id": itinerary_id,
                "status": "approved",
                "grand_total": grand_total if ctx else 0.0
            }
            resp = await client.post(webhook_url, json=payload, headers=headers)
            log.info("[approve_itinerary] DMC Core response status: %d, body: %s", resp.status_code, resp.text)
            if resp.status_code not in (200, 201):
                log.error("[approve_itinerary] DMC Core webhook returned error status %d", resp.status_code)
                raise HTTPException(status_code=502, detail=f"DMC Core webhook callback failed: status {resp.status_code}")
    except Exception as exc:
        log.exception("[approve_itinerary] DMC Core callback failed: %s", exc)
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=502, detail=f"DMC Core callback failed: {exc}")

    log.info("[approve_itinerary] ✓ %s approved v%d → %s", itinerary_id, version, published_url)
    return {"published_url": published_url, "version": version, "status": "approved"}


# ── Landing page (static demo) ───────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_landing_page():
    # Serve the original static demo file directly
    with open("vietnam-heritage-luxury-landingpage.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("assets/vietnam-safar-logo.png", media_type="image/png")


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    from fastapi.responses import Response
    content = """// Service Worker for Vietnam Safar PWA
const CACHE_NAME = 'vietnam-safar-v2';
const ASSETS = [
  '/',
  '/favicon.ico',
  '/assets/vietnam-safar-logo.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if (!event.request.url.startsWith('http')) return;

  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(event.request) || caches.match('/');
      })
    );
    return;
  }
  
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).then(networkResponse => {
        if (networkResponse && networkResponse.status === 200 && (event.request.url.includes('/assets/') || event.request.url.includes('unpkg.com') || event.request.url.includes('basemaps.cartocdn.com'))) {
          const cacheCopy = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, cacheCopy);
          });
        }
        return networkResponse;
      }).catch(() => {});
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const urlToOpen = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
      for (let i = 0; i < windowClients.length; i++) {
        const client = windowClients[i];
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});
"""
    return Response(content=content, media_type="application/javascript")


@app.get("/manifest.json", include_in_schema=False)
async def web_manifest(id: str = None, type: str = None):
    name = "Vietnam Safar - Luxury Travel"
    start_url = "/"
    if id and type:
        start_url = f"/{type}/{id}"
        if type == "quotations":
            entry = quotations.get(id)
            if entry and entry.get("ctx"):
                q_title = entry["ctx"].get("quotation_title") or entry["ctx"].get("tour_title")
                if q_title:
                    name = f"Itinerary: {q_title}"
        elif type == "itineraries":
            entry = itineraries.get(id)
            if entry and entry.get("ctx"):
                i_title = entry["ctx"].get("tour_title") or entry["ctx"].get("quotation_title")
                if i_title:
                    name = f"Itinerary: {i_title}"
                    
    manifest_data = {
        "name": name,
        "short_name": "Vietnam Safar",
        "description": "Your luxury travel itinerary and quotation custom-tailored by Vietnam Safar.",
        "start_url": start_url,
        "display": "standalone",
        "background_color": "#f8f3e9",
        "theme_color": "#17412e",
        "orientation": "any",
        "icons": [
            {
                "src": "/assets/vietnam-safar-logo.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/assets/vietnam-safar-logo.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return manifest_data


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Privacy Policy – Vietnam Safar Quotation API</title>
  <style>
    :root {
      --ivory: #f8f3e9;
      --emerald: #17412e;
      --gold: #b8860b;
      --gold-2: #daa520;
      --ink: #11130f;
      --muted: #706a5d;
      --line: rgba(183,137,75,.22);
      --card: #fffaf1;
      --serif: Georgia, 'Times New Roman', serif;
      --sans: system-ui, Arial, Helvetica, sans-serif;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      background: var(--ivory);
      color: var(--ink);
      font-family: var(--sans);
      line-height: 1.75;
    }
    header {
      background: var(--emerald);
      color: #fff;
      padding: 48px 0 40px;
      text-align: center;
    }
    header .kicker {
      color: var(--gold-2);
      font-size: 11px;
      letter-spacing: .22em;
      text-transform: uppercase;
      font-weight: 700;
      margin-bottom: 14px;
    }
    header h1 {
      font-family: var(--serif);
      font-size: clamp(28px, 5vw, 52px);
      font-weight: 500;
      letter-spacing: -.04em;
    }
    header p {
      margin-top: 12px;
      color: rgba(255,255,255,.7);
      font-size: 14px;
    }
    .container { width: min(820px, 92%); margin: 0 auto; }
    main { padding: 56px 0 80px; }
    section {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 32px 36px;
      margin-bottom: 20px;
    }
    h2 {
      font-family: var(--serif);
      font-size: 22px;
      font-weight: 500;
      color: var(--emerald);
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--line);
    }
    p { color: var(--muted); font-size: 15px; margin-bottom: 12px; }
    p:last-child { margin-bottom: 0; }
    ul { color: var(--muted); font-size: 15px; padding-left: 22px; margin-bottom: 12px; }
    ul li { margin-bottom: 6px; }
    a { color: var(--gold); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .badge {
      display: inline-block;
      background: rgba(183,137,75,.12);
      border: 1px solid var(--line);
      color: var(--gold);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .14em;
      text-transform: uppercase;
      border-radius: 999px;
      padding: 4px 14px;
      margin-bottom: 20px;
    }
    footer {
      text-align: center;
      font-size: 13px;
      color: var(--muted);
      padding: 24px 0 40px;
    }
  </style>
</head>
<body>
  <header>
    <div class="container">
      <div class="kicker">Legal</div>
      <h1>Privacy Policy</h1>
      <p>Vietnam Safar – Discovery Asia Travel Group &nbsp;|&nbsp; Quotation API</p>
    </div>
  </header>

  <main>
    <div class="container">
      <div class="badge">Effective date: May 13, 2026</div>

      <section>
        <h2>1. Overview</h2>
        <p>
          This Privacy Policy describes how <strong>Vietnam Safar – Discovery Asia Travel Group</strong>
          ("we", "our", or "us") handles information submitted through the Vietnam Safar Quotation API,
          which powers the Custom GPT integration for generating travel quotation documents.
        </p>
        <p>
          By using this API or the associated Custom GPT, you agree to the practices described in this policy.
        </p>
      </section>

      <section>
        <h2>2. Information We Collect</h2>
        <p>Through the Quotation API, we may receive the following data submitted by the GPT or user:</p>
        <ul>
          <li>Quotation metadata (quotation number, date, validity period, currency)</li>
          <li>Customer information (company name, contact name, email, phone, address)</li>
          <li>Seller / issuer information (company name, contact details)</li>
          <li>Line items (product or service names, quantities, pricing)</li>
          <li>Payment terms, delivery terms, and notes</li>
          <li>Source identifier (e.g. "custom-gpt", "ChatGPT upload")</li>
        </ul>
      </section>

      <section>
        <h2>3. How We Use This Information</h2>
        <p>Submitted quotation data is used solely for the following purposes:</p>
        <ul>
          <li>Generating and storing travel quotation records for B2B partners</li>
          <li>Enabling the Custom GPT to produce accurate quotation landing pages and documents</li>
          <li>Internal logging and debugging to ensure system reliability</li>
        </ul>
        <p>
          We do <strong>not</strong> use this data for advertising, profiling, or any purpose
          unrelated to the quotation workflow.
        </p>
      </section>

      <section>
        <h2>4. Data Sharing</h2>
        <p>
          We do not sell, rent, or share submitted data with third parties, except as required
          to operate the service (e.g. hosting infrastructure) or comply with applicable law.
        </p>
        <p>
          Data transmitted through the Custom GPT integration is subject to
          <a href="https://openai.com/policies/privacy-policy" target="_blank" rel="noopener">
            OpenAI's Privacy Policy
          </a> for the processing performed on OpenAI's platform.
        </p>
      </section>

      <section>
        <h2>5. Data Retention</h2>
        <p>
          Quotation records are retained for as long as necessary to fulfil the business purpose
          for which they were created, or as required by applicable regulations.
          Internal debug logs are purged on a rolling basis.
        </p>
      </section>

      <section>
        <h2>6. Security</h2>
        <p>
          All data is transmitted over HTTPS. We implement reasonable technical and organisational
          measures to protect submitted information against unauthorised access, loss, or disclosure.
        </p>
      </section>

      <section>
        <h2>7. Your Rights</h2>
        <p>
          You may request access to, correction of, or deletion of any personal data submitted
          through this API by contacting us at the address below.
        </p>
      </section>

      <section>
        <h2>8. Contact</h2>
        <p>
          <strong>Vietnam Safar – Discovery Asia Travel Group</strong><br />
          Email: <a href="mailto:safa@vietnamsafar.vn">safa@vietnamsafar.vn</a><br />
          Phone: <a href="tel:+84911538738">+84 911 538 738</a><br />
          Website: <a href="https://vietnamsafar.vn" target="_blank" rel="noopener">vietnamsafar.vn</a>
        </p>
      </section>
    </div>
  </main>

  <footer>
    <div class="container">
      &copy; 2026 Vietnam Safar – Discovery Asia Travel Group. All rights reserved.
    </div>
  </footer>
</body>
</html>"""
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8111, reload=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Agent-Facing Endpoints — Simplified for Hermes Pool multi-agent pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def _build_agent_ctx(
    session_id: str,
    tour_brief: dict,
    pricing: dict,
    services: dict,
    customer_name: str,
    destinations: list[dict],
    hero_image_url: str,
) -> dict:
    """Build Jinja2 template context from simplified agent workspace data.

    Maps sparse agent output (services, pricing, tour_brief) into the full
    template context dict expected by vietnam_heritage_luxury_b2c.html.
    Missing fields get empty defaults — no UndefinedError at render time.
    """
    # ── Seller info ─────────────────────────────────────────────────
    seller_name = os.getenv("SELLER_NAME", "Vietnam Safar \u2013 Discovery Asia Travel Group")
    seller_email = os.getenv("SELLER_EMAIL", "sales@vietnamsafar.vn")
    seller_phone = os.getenv("SELLER_PHONE", "+84 911 538 738")

    # ── Tour brief fields ────────────────────────────────────────────
    title = tour_brief.get("title", "") or tour_brief.get("tour_name", "")
    subtitle = tour_brief.get("subtitle", "") or tour_brief.get("description", "")
    dests_list = tour_brief.get("destinations", [])
    pax_adults = tour_brief.get("adults", 2)
    pax_children = tour_brief.get("children", 0)
    pax_total = pax_adults + pax_children
    days = tour_brief.get("days", 0) or tour_brief.get("duration_days", 0)
    nights = max(0, days - 1) if days else 0
    duration_lbl = f"{days}D{nights}N" if days else ""
    route_txt = " \u2013 ".join(dests_list)
    guests_txt = f"{pax_adults} Adults" + (f" + {pax_children} Children" if pax_children else "")
    nationality = tour_brief.get("nationality", "") or tour_brief.get("market", "")
    travel_dates = tour_brief.get("travel_dates", "") or tour_brief.get("dates", "")
    travel_style = tour_brief.get("travel_style", "") or tour_brief.get("style", "")
    hotel_standard = tour_brief.get("hotel_standard", "") or tour_brief.get("hotelStandard", "")
    meal_pref = tour_brief.get("meal_preference", "") or tour_brief.get("mealPreference", "")
    tour_code = tour_brief.get("tour_code", "") or tour_brief.get("tourCode", "")

    # ── Pricing ──────────────────────────────────────────────────────
    currency = pricing.get("currency", "USD")
    hotel_price = float(pricing.get("hotel", 0) or 0)
    guide_price = float(pricing.get("guide", 0) or 0)
    transport_price = float(pricing.get("transport", 0) or 0)
    activity_price = float(pricing.get("activity", 0) or 0)
    total = hotel_price + guide_price + transport_price + activity_price
    price_per_person = total / max(1, pax_adults)

    p_pax_txt = f"{currency} {price_per_person:,.0f} / person" if total > 0 else ""
    total_txt = f"{currency} {total:,.0f}" if total > 0 else ""

    price_options = [{
        "hotelCategory": hotel_standard or "Standard",
        "optionName": "Main option",
        "pricePerPerson": {
            "amount": price_per_person,
            "currency": currency,
            "displayText": p_pax_txt,
            "isFromPrice": False,
        },
        "totalPrice": {
            "amount": total,
            "currency": currency,
            "displayText": total_txt,
            "isFromPrice": False,
        },
        "isConfirmedMainOption": True,
        "isAlternativeOption": False,
        "notes": ["Calculated from agent workspace data"],
    }] if total > 0 else []

    # ── Hotels (from services) ───────────────────────────────────────
    hotel_data = services.get("hotel", {}) or {}
    hotel_plan_items = [{
        "destination": hotel_data.get("destination", ""),
        "checkInDate": hotel_data.get("check_in", ""),
        "checkOutDate": hotel_data.get("check_out", ""),
        "hotelArrangement": hotel_data.get("name", ""),
        "status": "confirmed",
    }] if hotel_data else []
    hotel_room_notes = hotel_data.get("notes", "")

    # ── Services ─────────────────────────────────────────────────────
    guide_data = services.get("guide", {}) or {}
    transport_data = services.get("transport", {}) or {}
    activities_data = services.get("activities", []) or []

    # ── Itinerary ────────────────────────────────────────────────────
    days_list = tour_brief.get("itinerary", [])
    if not days_list and days:
        # Build a simple day-by-day from destinations
        for i, dest in enumerate(dests_list or ["Destination"]):
            days_list.append({
                "dayNumber": i + 1,
                "title": f"Explore {dest}",
                "date": "",
                "overnight": dest,
                "meals": [],
                "activities": ["Sightseeing and exploration"],
                "notes": [],
                "description": f"Discover the beauty of {dest}.",
                "destinations": [dest],
            })

    mapped_itinerary = []
    for d in days_list:
        title = d.get("title", "")
        if not title or title.lower().startswith("explore "):
            dest = d.get("overnight") or (d.get("destinations")[0] if d.get("destinations") else "Vietnam")
            title = get_luxury_day_title(dest, d.get("dayNumber", 1), "en")
        mapped_itinerary.append({
            "dayNumber": d.get("dayNumber", 0),
            "title": title,
            "date": d.get("date", ""),
            "overnight": d.get("overnight", ""),
            "meals": d.get("meals", []) or [],
            "activities": d.get("activities", []) or [],
            "notes": d.get("notes", []) or [],
            "description": d.get("description", ""),
            "destinations": [d.get("destination", "")] if d.get("destination") else [],
        })

    # ── Destinations for gallery ─────────────────────────────────────
    gallery_destinations = []
    for i, dest in enumerate(destinations or []):
        img_url = dest.get("image_url", "") or hero_image_url
        gallery_destinations.append({
            "name": dest.get("name", ""),
            "image_url": img_url,
        })

    # ── Why works section ────────────────────────────────────────────
    why_private = (
        "Your personal sanctuary on the move \u2014 private guides, dedicated transport, "
        "and experiences curated exclusively for you."
    )
    why_comfort = (
        "Handpicked accommodations, seamless logistics, and a pace that lets you "
        "truly absorb each destination."
    )
    why_muslim = (
        "Dietary requests, meal planning, and specific preferences are carefully "
        "coordinated to suit all travelers."
    )
    why_balanced = (
        "A carefully balanced rhythm of discovery, relaxation, and cultural ",
        "immersion \u2014 crafted for meaningful travel.",
    )

    # Set image CSS variables
    img_vars = {}
    for i, dest in enumerate(gallery_destinations[:5]):
        img_vars[f"img_{i}"] = dest["image_url"]

    return {
        "quotation_id": session_id,
        "destinations": gallery_destinations,
        "tour_title": title,
        "quotation_title": title,
        "kicker": f"Private Luxury Quotation \u2012 {duration_lbl} \u2012 {travel_dates}" if duration_lbl else "Private Luxury Quotation",
        "lede": subtitle,
        "customer_name": customer_name,
        "nationality": nationality,
        "travel_style": travel_style,
        "guests_txt": guests_txt,
        "route_txt": route_txt,
        "travel_dates": travel_dates,
        "duration_label": duration_lbl,
        # Pricing
        "currency": currency,
        "total_price": total_txt,
        "price_per_pax": p_pax_txt,
        "grand_total": total,
        "subtotal": total,
        "tax_total": 0.0,
        "pricing_title": "PRICE QUOTATION \u2013 INDICATIVE",
        "pricing_basis": "Indicative pricing, subject to reconfirmation",
        "price_options": price_options,
        "pricing_h2": f"Total: {total_txt}" if total_txt else "",
        "pricing_p": f"Grand total for {guests_txt}. Currency: {currency}. Final rates subject to reconfirmation.",
        # Itinerary
        "itinerary_h2": "Day-by-Day Journey",
        "itinerary_p": f"Your private journey \u2014 {len(mapped_itinerary)} days of exploration." if mapped_itinerary else "",
        "itinerary": mapped_itinerary,
        # Overview
        "overview_heading": "Journey Overview",
        "overview_h2": f"{customer_name} \u2014 {title}",
        "overview_p": subtitle,
        "overview_paras": [subtitle] if subtitle else [],
        # Why works
        "why_private": why_private,
        "why_comfort": why_comfort,
        "why_muslim": why_muslim,
        "why_balanced": why_balanced,
        # Hotels
        "hotels": hotel_plan_items,
        "room_notes": hotel_room_notes,
        "optional_enhancements": [],
        # Contact
        "contact": seller_name,
        "contact_phone": seller_phone,
        "contact_web": "www.vietnamsafar.vn",
        "seller_email": seller_email,
        "seller_name": seller_name,
        # Inclusions / exclusions
        "inclusions": [],
        "exclusions": [],
        # Payment terms
        "payment_terms": "Refer to Booking & Payment terms.",
        "term_deposit": "",
        "term_balance": "",
        "term_cancellation": "",
        "term_confirmation": "",
        "final_req": "",
        "final_after": "",
        "cta_h2": "Confirm your travel dates to finalize.",
        "cta_p": "Share any additional requirements \u2014 we will reconfirm availability and return a finalized quotation.",
        # Price conditions
        "price_cond_paras": [""],
        "terms_p": "",
        # Footer
        "footer_text": f"{title} \u2014 Luxury quotation prepared for {customer_name}." if title else "Luxury quotation.",
        # Journey glance
        "show_muslim_care": True,
        "glance_market": nationality,
        "glance_profile": guests_txt,
        "glance_standard": hotel_standard,
        "glance_meals": meal_pref,
        "glance_price_type": "Indicative",
        "glance_tour_code": tour_code,
        "glance_flights": "",
        "glance_basis": "Indicative pricing, subject to reconfirmation",
        "glance_partner_note": "",
        "glance_validity": "Subject to confirmation at time of booking",
        # Raw
        "raw_quotation": "",
        # Images
        **img_vars,
    }


@app.post("/api/v1/landing-page")
async def create_landing_page_agent(request: Request):
    """Simplified landing page endpoint for Hermes Pool multi-agent pipeline.

    Accepts workspace data from session.md instead of full TourQuotationPayload.
    Uses existing template rendering + file persistence infrastructure.

    Request body:
    {
        "session_id": "session-xxx",
        "tour_brief": { "title", "destinations", "adults", "children", "days", ... },
        "pricing": { "hotel", "guide", "transport", "activity", "currency" },
        "services": { "hotel": {...}, "guide": {...}, "transport": {...}, "activities": [...] },
        "customer_name": "...",
        "agent_notes": "..."
    }

    Returns:
    {
        "quotationId": "...",
        "quotationUrl": "...",
        "pdfUrl": "...",
        "localPath": "...",
        "status": "published"
    }
    """
    body = await request.json()

    session_id = body.get("session_id", f"quo_{uuid.uuid4().hex[:12]}")
    tour_brief = body.get("tour_brief", {})
    pricing = body.get("pricing", {})
    services = body.get("services", {})
    customer_name = body.get("customer_name", "Valued Customer")
    agent_notes = body.get("agent_notes", "")

    log.info("[/api/v1/landing-page] session=%s customer=%s", session_id, customer_name)

    # ── 1. Image selection ──────────────────────────────────────────────
    route_list = tour_brief.get("destinations", [])
    route_text = " ".join(route_list)
    itinerary_text = " ".join(
        d.get("title", "") or d.get("destination", "")
        for d in (tour_brief.get("itinerary", []) or [])
    )
    text_context = route_text + " " + itinerary_text

    from image_selector import extract_and_map_destinations, get_random_image_for_province, get_all_images_for_province

    destinations = await extract_and_map_destinations(text_context, max_items=None) if text_context.strip() else []
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))
        d["images"] = get_all_images_for_province(d.get("slug"))
    default_img = "/assets/vietnam-safar-logo.png"
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/api/v1/landing-page] destinations=%d hero=%s", len(destinations), hero_image_url)

    # ── 2. Build template context ───────────────────────────────────────
    ctx = _build_agent_ctx(session_id, tour_brief, pricing, services, customer_name, destinations, hero_image_url)

    # ── 3. Render templates ─────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    tmpl_lp = templates.get_template("vietnam_heritage_luxury_b2c.html")
    tmpl_pdf = templates.get_template("vietnam_heritage_luxury_b2c_pdf.html")

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render, **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )

    # ── 4. Write to disk (always — both local and production) ───────────
    quo_dir = os.path.join("published", session_id)
    os.makedirs(quo_dir, exist_ok=True)

    v1_path = os.path.join(quo_dir, "v1.html")
    pdf_path = os.path.join(quo_dir, "pdf.html")
    ctx_path = os.path.join(quo_dir, "ctx.json")

    with open(v1_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    with open(pdf_path, "w", encoding="utf-8") as f:
        f.write(rendered_pdf)
    with open(ctx_path, "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, default=str)

    log.info("[/api/v1/landing-page] Written: %s, %s, %s", v1_path, pdf_path, ctx_path)

    # ── 5. Optional GitHub publish (production only) ────────────────────
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    published_url: str | None = None
    pdf_static_url: str | None = None

    if ENVIRONMENT == "production" and os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_REPO"):
        try:
            from github_publish import publish_file_to_github, publish_to_github

            # Publish files sequentially to avoid 409 conflict
            published_url = await publish_to_github(session_id, rendered_html, version=1)
            pdf_static_url = await publish_file_to_github(
                file_path=f"published/{session_id}/pdf.html",
                html_content=rendered_pdf,
                commit_message=f"Publish PDF for quotation {session_id}",
            )
            log.info("[/api/v1/landing-page] GitHub published: %s", published_url)
        except Exception as exc:
            log.warning("[/api/v1/landing-page] GitHub publish skipped: %s", exc)

    # ── 6. Build response URL ───────────────────────────────────────────
    base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8111")
    quotation_url = published_url or f"{base_url}/published/{session_id}/v1.html"
    pdf_url = pdf_static_url or f"{base_url}/published/{session_id}/pdf.html"
    local_path = str(v1_path)

    return {
        "quotationId": session_id,
        "quotationUrl": quotation_url,
        "pdfUrl": pdf_url,
        "localPath": local_path,
        "status": "published",
        "version": 1,
    }


def format_hotel_dates(checkin: str, checkout: str, lang: str = "en") -> str:
    return format_display_date_range_for_lang(checkin, checkout, lang)


# ── Dynamic hotel details fuzzy resolver (Fusion Search + info.json) ──────────
def strip_accents(text: str) -> str:
    import unicodedata
    if not text:
        return ""
    normalized = unicodedata.normalize('NFD', text)
    stripped = "".join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return stripped.replace('Đ', 'D').replace('đ', 'd')

HOTEL_STOP_WORDS = {
    'hotel', 'resort', 'cruise', 'spa', 'villas', 'luxury', 'premium', 
    'boutique', 'stay', 'suites', 'center', 'ocean', 'safi', 'premium',
    'classic', 'legend', 'metropole', 'retreat', 'lodge', 'palace',
    'khach', 'san', 'khachsan', 'nha', 'du', 'thuyen', 'duthuyen'
}

def tokenize_hotel_name(text: str) -> set:
    import re
    if not text:
        return set()
    clean = re.sub(r'[^a-zA-Z0-9\s-]', '', strip_accents(text)).lower()
    tokens = set(re.split(r'[\s-]', clean))
    return {t for t in tokens if t and t not in HOTEL_STOP_WORDS}

def char_similarity(str1: str, str2: str) -> float:
    import difflib
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def calculate_match_score(hotel_name: str, city_name: str, city_dir: str, hotel_dir: str) -> float:
    score = 0.0
    norm_city_input = strip_accents(city_name).lower().replace(" ", "").replace("-", "")
    norm_city_dir = strip_accents(city_dir).lower().replace(" ", "").replace("-", "")
    
    city_aliases = {
        "saigon": {"saigon", "hochiminh", "hochiminhcity", "hcmc"},
        "hanoi": {"hanoi"},
        "halong": {"halong", "halongbay", "quangninh"},
        "dalat": {"dalat", "lamdong"},
        "danang": {"danang"},
        "sapa": {"sapa", "laocai"}
    }
    
    city_matched = False
    if norm_city_input == norm_city_dir:
        city_matched = True
    else:
        for key, aliases in city_aliases.items():
            if norm_city_input in aliases and norm_city_dir in aliases:
                city_matched = True
                break
                
    if city_matched:
        score += 2.0
        
    input_tokens = tokenize_hotel_name(hotel_name)
    dir_tokens = tokenize_hotel_name(hotel_dir)
    
    matched_tokens = set()
    for it in input_tokens:
        for dt in dir_tokens:
            if it == dt or char_similarity(it, dt) >= 0.8:
                matched_tokens.add(it)
                break
                
    if input_tokens and dir_tokens:
        jaccard = len(matched_tokens) / len(input_tokens.union(dir_tokens))
        score += jaccard * 3.0
        
        for dt in dir_tokens:
            for it in input_tokens:
                if dt in it or it in dt:
                    score += 0.5
                    break
    else:
        sim = char_similarity(hotel_name, hotel_dir)
        score += sim * 2.0
            
    return score

def resolve_hotel_details(hotel_name: str, city_name: str, base_dir: str = "assets/hotels", index: int = 0, lang: str = "en") -> dict | None:
    if not os.path.exists(base_dir):
        return None
        
    best_score = -1.0
    best_match = None
    
    for city_dir in os.listdir(base_dir):
        city_path = os.path.join(base_dir, city_dir)
        if not os.path.isdir(city_path):
            continue
            
        for hotel_dir in os.listdir(city_path):
            hotel_path = os.path.join(city_path, hotel_dir)
            if not os.path.isdir(hotel_path):
                continue
                
            score = calculate_match_score(hotel_name, city_name, city_dir, hotel_dir)
            if score > best_score:
                best_score = score
                best_match = (city_dir, hotel_dir, hotel_path)
                
    city_matched_bool = False
    if best_match:
        norm_input = city_name.lower().replace(" ", "").replace("-", "")
        norm_dir = best_match[0].lower().replace(" ", "").replace("-", "")
        city_matched_bool = (norm_input == norm_dir)
        
    threshold = 2.2 if city_matched_bool else 1.5
    
    # Token matching check (protection against same-city false matches)
    input_tokens = tokenize_hotel_name(hotel_name)
    dir_tokens = tokenize_hotel_name(best_match[1]) if best_match else set()
    matched_tokens = set()
    for it in input_tokens:
        for dt in dir_tokens:
            if it == dt or char_similarity(it, dt) >= 0.8:
                matched_tokens.add(it)
                break
    has_token_match = len(matched_tokens) > 0
    
    if best_match and best_score >= threshold and has_token_match:
        city_dir, hotel_dir, matched_path = best_match
        
        name = hotel_name.split("(")[0].strip() if hotel_name else "Luxury Hotel"
        tel = "+84 28 3933 3226"
        suffix = translate_filter("offers refined luxury accommodations, personalized service, and modern comforts.", lang)
        intro = f"{name} {suffix}"
        
        info_path = os.path.join(matched_path, "info.json")
        if os.path.exists(info_path):
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                    name = info.get("name", name)
                    tel = info.get("tel", tel)
                    intro = info.get("introduction", intro)
            except Exception:
                pass
                
        ext_dir = os.path.join(matched_path, "exterior")
        ext_imgs = []
        if os.path.exists(ext_dir) and os.path.isdir(ext_dir):
            ext_imgs = sorted([f for f in os.listdir(ext_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
            
        int_dir = os.path.join(matched_path, "interior")
        int_imgs = []
        if os.path.exists(int_dir) and os.path.isdir(int_dir):
            int_imgs = sorted([f for f in os.listdir(int_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
            
        root_imgs = sorted([f for f in os.listdir(matched_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
        
        # Translate introduction
        if "offers refined luxury accommodations" in intro:
            suffix = translate_filter("offers refined luxury accommodations, personalized service, and modern comforts.", lang)
            intro = f"{name} {suffix}"
        else:
            intro = translate_filter(intro, lang)

        # Resolve exterior image using modulo on index to rotate/shuffle images
        if ext_imgs:
            ext_idx = index % len(ext_imgs)
            ext_img = f"/assets/hotels/{city_dir}/{hotel_dir}/exterior/{ext_imgs[ext_idx]}"
        elif int_imgs:
            ext_idx = index % len(int_imgs)
            ext_img = f"/assets/hotels/{city_dir}/{hotel_dir}/interior/{int_imgs[ext_idx]}"
        elif root_imgs:
            ext_idx = index % len(root_imgs)
            ext_img = f"/assets/hotels/{city_dir}/{hotel_dir}/{root_imgs[ext_idx]}"
        else:
            ext_img = ""

        # Resolve interior image (offsetting index by 1 to get a different picture)
        if int_imgs:
            int_idx = (index + 1) % len(int_imgs)
            int_img = f"/assets/hotels/{city_dir}/{hotel_dir}/interior/{int_imgs[int_idx]}"
        elif ext_imgs:
            int_idx = (index + 1) % len(ext_imgs)
            int_img = f"/assets/hotels/{city_dir}/{hotel_dir}/exterior/{ext_imgs[int_idx]}"
        elif root_imgs:
            int_idx = (index + 1) % len(root_imgs)
            int_img = f"/assets/hotels/{city_dir}/{hotel_dir}/{root_imgs[int_idx]}"
        else:
            int_img = ""
            
        return {
            "name": name,
            "tel": tel,
            "introduction": intro,
            "hotel_img": ext_img,
            "room_img": int_img
        }
        
    return None


def get_luxury_hotel_details(hotel_name_or_arr: str, destination: str, checkin: str, checkout: str, index: int = 0, lang: str = "en") -> dict:
    name_lower = hotel_name_or_arr.lower() if hotel_name_or_arr else ""
    date_range = format_hotel_dates(checkin, checkout, lang)
    city_country = f"{destination.upper()}, VIETNAM" if destination else "VIETNAM"
    
    # Parse name, room type, and notes from hotelArrangement
    raw_name = hotel_name_or_arr
    room_type = ""
    notes = ""
    
    if hotel_name_or_arr:
        parts = [p.strip() for p in hotel_name_or_arr.split(" - ") if p.strip()]
        if len(parts) > 0:
            raw_name = parts[0]
        if len(parts) > 1:
            room_type = parts[1]
        if len(parts) > 2:
            notes = " - ".join(parts[2:])
        if not room_type:
            paren_match = re.search(r'\(([^()]+)\)\s*$', hotel_name_or_arr)
            if paren_match:
                room_type = paren_match.group(1).strip()
            
    name = raw_name.split("(")[0].strip() if raw_name else "Luxury Hotel"
    tel = "+84 28 3933 3226"
    suffix = translate_filter("offers refined luxury accommodations, personalized service, and modern comforts.", lang)
    intro = f"{name} {suffix}"
    hotel_img = ""
    room_img = ""
    
    # 1. Try resolving dynamically from the local database (Fusion Search + info.json)
    resolved = resolve_hotel_details(name, destination, index=index, lang=lang)
    if resolved:
        name = resolved["name"]
        tel = resolved["tel"]
        intro = resolved["introduction"]
        hotel_img = resolved["hotel_img"]
        room_img = resolved["room_img"]
    else:
        # 2. Legacy static overrides (No destination fallback here, only name-based override)
        if "metropole" in name_lower:
            name = "Sofitel Legend Metropole Hanoi"
            tel = "+84 24 3826 6919"
            intro = "A historic landmark since 1901, the Sofitel Legend Metropole Hanoi features French colonial grandeur blended with contemporary luxury. Located in the heart of Hanoi, it has welcomed playwrights, ambassadors, and heads of state. The hotel offers guestrooms adorned with rich wood, classic elegance, and refined Vietnamese touches. Indulge in culinary excellence at Le Beaulieu or relax at the heritage-rich Bamboo Bar by the garden pool, experiencing timeless colonial prestige."
            hotel_img = "/assets/hotels/metropole_facade.jpg"
            room_img = "/assets/hotels/metropole_room.jpg"
        elif "orchid" in name_lower:
            name = "Orchid Classic Cruise"
            tel = "+84 96 123 4567"
            intro = "Cruising the pristine waters of Lan Ha Bay and Halong Bay, Orchid Classic Cruise offers an intimate boutique experience with charter-level luxury. Featuring elegant Indochine architecture combined with modern wooden furnishings, the cruise hosts spacious suites, each featuring a private ocean-view balcony and a walk-in shower. Guests can relax in the outdoor jacuzzi, enjoy sunset cocktails on the sundeck, and savor fine dining showcasing local seafood delicacies."
            hotel_img = "/assets/hotels/orchid_cruise.jpg"
            room_img = "/assets/hotels/orchid_room.jpg"
        elif "four seasons" in name_lower or "nam hai" in name_lower:
            name = "Four Seasons Resort The Nam Hai"
            tel = "+84 235 394 0000"
            intro = "An oasis of luxury along a pristine portal of Hoi An's coastline, Four Seasons Resort The Nam Hai offers a sleek, design-led sanctuary. Inspired by traditional wind-and-water principles, the villas are designed with high ceilings, central platforms, and private terrace views. Guests can lounge by three infinity pools, experience holistic therapies at the floating spa pavilions, and relish exceptional Vietnamese culinary artistry under the shade of mature coconut palms."
            hotel_img = "/assets/hotels/nam_hai_facade.jpg"
            room_img = "/assets/hotels/nam_hai_room.jpg"
        elif "ylang" in name_lower:
            name = "Heritage Line Ylang"
            tel = "+84 28 3933 3226"
            intro = "Cruising Lan Ha Bay, part of Vietnam's famous Halong Bay, Ylang has a length of 57 meters, a draft of 1.9 meters and a cruise speed of around 10 nautical knots. Launched in 2019, the vessel is a mix of Indochinese-Vietnamese design, comprised of 10 suites divided into two room categories, both of which feature private balconies, separate lounge areas, walk-in showers and separate bathtubs, large sliding doors, air conditioning and beautiful wood panels. Facilities include the reception-lobby area, a boutique, spa and sauna areas, a wellness studio, a library lounge, a restaurant and bar, as well as a terrace deck with a pool."
            hotel_img = "/assets/hotels/orchid_cruise.jpg"
            room_img = "/assets/hotels/orchid_room.jpg"

    return {
        "city_country": city_country,
        "name": name,
        "introduction": intro,
        "hotel_img": hotel_img,
        "room_img": room_img,
        "room_type": room_type,
        "room_name": room_type,
        "notes": notes,
        "date_range": date_range,
        "tel": tel,
        "destination": destination,
        "checkInDate": checkin,
        "checkOutDate": checkout
    }

# Reload trigger comment to refresh cached templates and routing logic v2
