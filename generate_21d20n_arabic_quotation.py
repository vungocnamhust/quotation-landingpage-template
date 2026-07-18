import json
import os
import sys
import types
from fastapi.testclient import TestClient

# Add current directory to path so main can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Stub the image selector module before importing main so this script
# can run without the full AI/image-selection dependency stack.
image_selector = types.ModuleType("image_selector")
async def mock_extract_and_map_destinations(text, max_items=None):
    print("[Mock] Extracting and mapping destinations for: Hanoi, Halong Bay, Sapa, Da Nang, Hoi An, Dalat, Ho Chi Minh")
    return [
        {"name": "Hanoi", "slug": "ha-noi"},
        {"name": "Halong Bay", "slug": "quang-ninh"},
        {"name": "Sapa", "slug": "lao-cai"},
        {"name": "Da Nang", "slug": "da-nang"},
        {"name": "Hoi An", "slug": "quang-nam"},
        {"name": "Dalat", "slug": "lam-dong"},
        {"name": "Ho Chi Minh City", "slug": "ho-chi-minh"}
    ]

async def mock_select_landing_image(payload, model_name=None):
    print("[Mock] Selecting landing image")
    return "/assets/halong-bay.jpg"

def mock_get_random_image_for_province(slug):
    return {
        "url": f"/assets/mock-{slug}.jpg",
        "province": slug,
        "source": "mock",
    }

def mock_get_all_images_for_province(slug):
    return [mock_get_random_image_for_province(slug)]

def mock_resolve_slug_locally(location):
    if not location:
        return None
    normalized = str(location).strip().lower()
    slug_map = {
        "hanoi": "ha-noi",
        "halong bay": "quang-ninh",
        "halong": "quang-ninh",
        "sapa": "lao-cai",
        "da nang": "da-nang",
        "hoi an": "quang-nam",
        "dalat": "lam-dong",
        "da lat": "lam-dong",
        "ho chi minh city": "ho-chi-minh",
        "ninh binh": "ninh-binh",
        "mekong delta": "mekong",
        "tan son nhat airport": "ho-chi-minh",
    }
    return slug_map.get(normalized)

image_selector.extract_and_map_destinations = mock_extract_and_map_destinations
image_selector.select_landing_image = mock_select_landing_image
image_selector.get_random_image_for_province = mock_get_random_image_for_province
image_selector.get_all_images_for_province = mock_get_all_images_for_province
image_selector.resolve_slug_locally = mock_resolve_slug_locally
sys.modules["image_selector"] = image_selector

from main import app

client = TestClient(app)

# Structure the full 21-day Arabic itinerary payload
payload = {
    "quotationNumber": "QT-2026-ARAB-21D20N",
    "lang": "ar",  # Triggers RTL and Arabic formatting in templates
    "quotationNarrative": (
        "رحلة فاخرة مصممة بعناية لمدة 21 يومًا تربط أبرز محطات فيتنام بين Hanoi وHalong Bay وSapa "
        "ثم Da Nang وDalat وHo Chi Minh City. يركز البرنامج على خط سير واضح، وتنقلات منظمة، وإقامة مختارة بعناية "
        "مع الحفاظ على دقة التفاصيل كما وردت في البرنامج الأساسي دون إضافة أنشطة أو مزايا غير مؤكدة."
    ),
    "landingpageContent": {
        "heroSection": {
            "headline": "رحلة الأحلام الفاخرة في فيتنام",
            "subtitle": "اكتشف روعة الطبيعة وسحر الثقافة عبر 21 يومًا من الاسترخاء والمغامرة الراقية"
        },
        "visualDescription": "A luxury travel landing page featuring scenery of Halong Bay and Sapa mountains."
    },
    "journeyGlance": {
        "market": "GCC / Arab Market",
        "guestProfile": "شخصان بالغان",
        "hotelStandard": "فنادق 4 نجوم فاخرة وكروز 5 نجوم",
        "mealPreference": "إفطار يومي + 4 وجبات مشمولة على متن كروز Halong Bay",
        "priceType": "Indicative",
        "tourCode": "VS-2026-21D20N-ARAB",
        "domesticFlights": "مشمولة (Hanoi - Da Nang، Da Nang - Dalat، Dalat - Ho Chi Minh City)",
        "priceBasis": "أساس الغرفة المزدوجة المشتركة (Twin/Double Sharing)",
        "partnerNote": "رحلة خاصة مع تنقلات منظمة وخدمات مختارة وفق البرنامج",
        "validity": "صالحة للسفر في أغسطس 2026"
    },
    "whyWorks": {
        "privateFlexible": "تتيح لك السيارة الخاصة والمرشد الشخصي مرونة تامة لتعديل وتيرة الرحلة وجداول اليوم بما يناسب تفضيلاتك الخاصة وعائلتك.",
        "comfort": "تم اختيار فنادق 4 نجوم عالية الجودة وكروز 5 نجوم بعناية فائقة لتوفير أقصى درجات الراحة والاسترخاء بعد الجولات اليومية.",
        "muslimFriendly": "تم تنظيم عناصر الرحلة والخدمات الأساسية بشكل واضح ومباشر بما يسهّل مراجعة كل يوم وكل انتقال بدقة.",
        "balancedHighlights": "يجمع البرنامج بين المدن التاريخية، الرحلات الطبيعية، المرتفعات الجبلية، الساحل، والجنوب الحضري ضمن تسلسل تنقل متدرج وواضح."
    },
    "itinerary": [
        {
            "dayNumber": 1,
            "destination": "Hanoi",
            "summary": "الوصول إلى Hanoi والاستقبال في المطار ثم الانتقال إلى Minasi Premium Hotel للمبيت.",
            "mainInclusions": "الاستقبال في المطار والانتقال بسيارة خاصة إلى الفندق.",
            "senseOfPace": "Relaxed",
            "dining": ""
        },
        {
            "dayNumber": 2,
            "destination": "Hanoi",
            "summary": "استكشاف Hanoi مع زيارة Dong Xuan Market، وركوب السيكلو، وتجربة Egg Coffee أو Train Street Coffee.",
            "mainInclusions": "جولة سيكلو وتنقلات البرنامج داخل Hanoi.",
            "senseOfPace": "Immersive",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 3,
            "destination": "Hanoi",
            "summary": "رحلة يومية من Hanoi إلى Ninh Binh لزيارة Tam Coc وHang Mua ثم العودة إلى Hanoi.",
            "mainInclusions": "تنقل خاص لرحلة Ninh Binh وفق البرنامج.",
            "senseOfPace": "Active",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 4,
            "destination": "Halong Bay",
            "summary": "الانتقال من Hanoi إلى Halong Bay بسيارة خاصة ثم الصعود على متن La Casta Cruise للمبيت.",
            "mainInclusions": "سيارة خاصة من Hanoi إلى Halong Bay وإقامة على متن La Casta Cruise.",
            "senseOfPace": "Relaxed",
            "dining": "الوجبات المشمولة وفق برنامج الكروز"
        },
        {
            "dayNumber": 5,
            "destination": "Hanoi",
            "summary": "مغادرة الكروز والعودة من Halong Bay إلى Hanoi بسيارة خاصة للمبيت في Minasi Premium Hotel.",
            "mainInclusions": "العودة بسيارة خاصة من Halong Bay إلى Hanoi.",
            "senseOfPace": "Relaxed",
            "dining": ""
        },
        {
            "dayNumber": 6,
            "destination": "Sapa",
            "summary": "الانتقال من Hanoi إلى Sapa بواسطة حافلة نوم ثم المبيت في Bora Hotel.",
            "mainInclusions": "تذكرة حافلة النوم والتنقلات الأساسية عند الوصول إلى Sapa.",
            "senseOfPace": "Moderate",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 7,
            "destination": "Sapa",
            "summary": "زيارة Fansipan ثم Cat Cat Village ضمن برنامج الاستكشاف في Sapa.",
            "mainInclusions": "رسوم برنامج Fansipan وCat Cat Village.",
            "senseOfPace": "Active",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 8,
            "destination": "Sapa",
            "summary": "زيارة Lao Chai وTa Van ثم Silver Waterfall ضمن برنامج اليوم في Sapa.",
            "mainInclusions": "تنقلات ورسوم البرنامج في Sapa.",
            "senseOfPace": "Moderate",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 9,
            "destination": "Sapa",
            "summary": "زيارة الجسر الزجاجي ثم Moana Coffee في Sapa.",
            "mainInclusions": "تنقلات ورسوم البرنامج لليوم في Sapa.",
            "senseOfPace": "Immersive",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 10,
            "destination": "Hanoi",
            "summary": "العودة من Sapa إلى Hanoi بواسطة حافلة نوم ثم المبيت في Minasi Premium Hotel.",
            "mainInclusions": "تذكرة حافلة النوم من Sapa إلى Hanoi.",
            "senseOfPace": "Relaxed",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 11,
            "destination": "Da Nang",
            "summary": "رحلة طيران داخلية من Hanoi إلى Da Nang ثم تجربة Han River Cruise.",
            "mainInclusions": "تذكرة طيران داخلية Hanoi - Da Nang وHan River Cruise.",
            "senseOfPace": "Moderate",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 12,
            "destination": "Da Nang",
            "summary": "زيارة Ba Na Hills ضمن برنامج اليوم الكامل من Da Nang.",
            "mainInclusions": "رسوم برنامج Ba Na Hills.",
            "senseOfPace": "Active",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 13,
            "destination": "Da Nang",
            "summary": "زيارة Bay Mau Coconut Forest ثم Hoi An Ancient Town قبل العودة إلى Da Nang.",
            "mainInclusions": "تنقلات ورسوم البرنامج لزيارة Bay Mau Coconut Forest وHoi An.",
            "senseOfPace": "Immersive",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 14,
            "destination": "Da Nang",
            "summary": "تجربة Hoa Phu Thanh rafting ضمن برنامج اليوم في Da Nang.",
            "mainInclusions": "رسوم برنامج Hoa Phu Thanh.",
            "senseOfPace": "Active",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 15,
            "destination": "Dalat",
            "summary": "رحلة طيران داخلية مباشرة من Da Nang إلى Dalat ثم الانتقال إلى CICILIA Rouge Dalat.",
            "mainInclusions": "تذكرة طيران داخلية Da Nang - Dalat والانتقال من المطار.",
            "senseOfPace": "Moderate",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 16,
            "destination": "Dalat",
            "summary": "زيارة Lang Biang والتلفريك وCrazy House وClay Tunnel ضمن برنامج Dalat.",
            "mainInclusions": "رسوم برنامج Dalat وفق المسار المحدد.",
            "senseOfPace": "Active",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 17,
            "destination": "Dalat",
            "summary": "زيارة Fresh Garden وDatanla Waterfall وElephant Waterfall وMe Linh Coffee.",
            "mainInclusions": "تنقلات ورسوم البرنامج لزيارة Fresh Garden وDatanla Waterfall وElephant Waterfall وMe Linh Coffee.",
            "senseOfPace": "Immersive",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 18,
            "destination": "Ho Chi Minh City",
            "summary": "رحلة طيران داخلية مباشرة من Dalat إلى Ho Chi Minh City ثم الانتقال إلى Cicilia Saigon Center.",
            "mainInclusions": "تذكرة طيران داخلية Dalat - Ho Chi Minh City والانتقال من المطار.",
            "senseOfPace": "Active",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 19,
            "destination": "Ho Chi Minh City",
            "summary": "زيارة Cu Chi Tunnels ثم Apartment Coffee وBen Thanh Market وCentral Post Office في Ho Chi Minh City.",
            "mainInclusions": "تنقلات ورسوم البرنامج في Ho Chi Minh City.",
            "senseOfPace": "Immersive",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 20,
            "destination": "Ho Chi Minh City",
            "summary": "رحلة يومية إلى Mekong Delta ثم العودة إلى Ho Chi Minh City.",
            "mainInclusions": "تنقلات وجولة Mekong Delta وفق البرنامج.",
            "senseOfPace": "Moderate",
            "dining": "إفطار في الفندق"
        },
        {
            "dayNumber": 21,
            "destination": "Ho Chi Minh City",
            "summary": "مغادرة Ho Chi Minh City والانتقال إلى Tan Son Nhat Airport للرحلة الدولية.",
            "mainInclusions": "الانتقال بسيارة خاصة إلى Tan Son Nhat Airport.",
            "senseOfPace": "Relaxed",
            "dining": "إفطار في الفندق"
        }
    ],
    "hotelPlan": {
        "hotels": [
            {
                "destination": "Hanoi",
                "checkInDate": "2026-08-10",
                "checkOutDate": "2026-08-13",
                "hotelArrangement": "Minasi Premium Hotel - Deluxe Room (City View, 25 sqm) - 3 Nights"
            },
            {
                "destination": "Halong Bay",
                "checkInDate": "2026-08-13",
                "checkOutDate": "2026-08-14",
                "hotelArrangement": "La Casta Cruise - Junior Suite Cabin (Ocean View & Private Balcony, 30 sqm) - 1 Night"
            },
            {
                "destination": "Hanoi",
                "checkInDate": "2026-08-14",
                "checkOutDate": "2026-08-15",
                "hotelArrangement": "Minasi Premium Hotel - Deluxe Room (City View, 25 sqm) - 1 Night"
            },
            {
                "destination": "Sapa",
                "checkInDate": "2026-08-15",
                "checkOutDate": "2026-08-19",
                "hotelArrangement": "Bora Hotel - Deluxe Room (Mountain View & Private Balcony, 25 sqm) - 4 Nights"
            },
            {
                "destination": "Hanoi",
                "checkInDate": "2026-08-19",
                "checkOutDate": "2026-08-20",
                "hotelArrangement": "Minasi Premium Hotel - Deluxe Room (City View, 25 sqm) - 1 Night"
            },
            {
                "destination": "Da Nang",
                "checkInDate": "2026-08-20",
                "checkOutDate": "2026-08-24",
                "hotelArrangement": "Minh Toan SAFI Ocean Hotel - Delight Ocean Room (Sea View, 32 sqm) - 4 Nights"
            },
            {
                "destination": "Dalat",
                "checkInDate": "2026-08-24",
                "checkOutDate": "2026-08-27",
                "hotelArrangement": "CICILIA Rouge Dalat - Vintage Balcony Room (Balcony & Outside View, 30 sqm) - 3 Nights"
            },
            {
                "destination": "Ho Chi Minh City",
                "checkInDate": "2026-08-27",
                "checkOutDate": "2026-08-30",
                "hotelArrangement": "Cicilia Saigon Center - Premium Deluxe Room (City View, 22 sqm) - 3 Nights"
            }
        ],
        "roomNotes": "غرفة مزدوجة أو بسريرين منفصلين لشخصين بالغين"
    },
    "optionalEnhancements": [
        {
            "title": "مرشد سياحي يتحدث اللغة العربية طوال الجولة",
            "status": "On request"
        },
        {
            "title": "ترقية الغرف في الفنادق إلى أجنحة فاخرة (Suite)",
            "status": "On request"
        }
    ],
    "bookingTerms": {
        "deposit": "شروط الدفع تخضع لسياسة الحجز الفعلية عند التأكيد.",
        "balance": "يتم استكمال الرصيد وفق جدول الدفع المعتمد عند تثبيت الحجز.",
        "cancellation": "تطبق سياسة الإلغاء النهائية بحسب شروط الحجز المؤكدة.",
        "confirmation": "جميع الخدمات والأسعار تخضع للتوافر عند التأكيد النهائي."
    },
    "finalization": {
        "finalDetailsRequired": "المستندات المطلوبة تشمل نسخة من جواز السفر الصالح وتفاصيل الرحلات الدولية لاستكمال الترتيبات.",
        "afterConfirmation": "بعد التأكيد سيتم تزويدك بقسائم الخدمات النهائية وتفاصيل التشغيل ذات الصلة."
    },
    "pricing": {
        "currency": "USD",
        "pricingTitle": "تفاصيل عرض السعر الفاخر",
        "basis": "بناءً على شخصين بالغين يتشاركان غرفة مزدوجة (Twin/Double Sharing)",
        "priceOptions": [
            {
                "label": "الإقامة في فنادق 4 نجوم وكروز 5 نجوم (شخصين)",
                "notes": "1995 دولار للشخص الواحد في الغرفة المزدوجة",
                "amount": 1995.0
            }
        ],
        "subtotal": 3990.0,
        "discountTotal": 0.0,
        "taxTotal": 0.0,
        "grandTotal": 3990.0
    },
    "retrievalStatus": {
        "hotel": "pending",
        "activity": "pending",
        "guide": "pending",
        "transfer": "pending",
        "flight": "pending"
    },
    "candidateBlocks": [
        {
            "block_id": "H_HANOI_1",
            "service_type": "hotel",
            "destination": "Hanoi",
            "source_day_numbers": [1, 2, 3]
        },
        {
            "block_id": "H_HALONG",
            "service_type": "hotel",
            "destination": "Halong Bay",
            "source_day_numbers": [4]
        },
        {
            "block_id": "H_HANOI_2",
            "service_type": "hotel",
            "destination": "Hanoi",
            "source_day_numbers": [5]
        },
        {
            "block_id": "H_SAPA",
            "service_type": "hotel",
            "destination": "Sapa",
            "source_day_numbers": [6, 7, 8, 9]
        },
        {
            "block_id": "H_HANOI_3",
            "service_type": "hotel",
            "destination": "Hanoi",
            "source_day_numbers": [10]
        },
        {
            "block_id": "H_DANANG",
            "service_type": "hotel",
            "destination": "Da Nang",
            "source_day_numbers": [11, 12, 13, 14]
        },
        {
            "block_id": "H_DALAT",
            "service_type": "hotel",
            "destination": "Dalat",
            "source_day_numbers": [15, 16, 17]
        },
        {
            "block_id": "H_HCMC",
            "service_type": "hotel",
            "destination": "Ho Chi Minh City",
            "source_day_numbers": [18, 19, 20, 21]
        }
    ],
    "inclusions": [
        "الإقامة في فنادق 4 نجوم مع وجبة الإفطار اليومية.",
        "الإقامة على متن كروز 5 نجوم في Halong Bay مع 4 وجبات مشمولة وفق برنامج الكروز.",
        "سيارة خاصة للتنقلات السياحية واستقبالات المطارات وفق البرنامج، باستثناء رحلة حافلة النوم ذهابًا وإيابًا بين Hanoi وSapa.",
        "رسوم دخول المواقع المذكورة في البرنامج.",
        "تذاكر الطيران الداخلية للقطاعات Hanoi - Da Nang وDa Nang - Dalat وDalat - Ho Chi Minh City.",
        "Vietnam E-visa.",
        "خدمة Fast Track عند الوصول.",
        "مرشد خاص للاستقبال في اليوم الأول ولجولات المشاهدة، باستثناء فترة الكروز في Halong Bay.",
        "SIM 4G / Internet."
    ],
    "exclusions": [
        "المصاريف الشخصية.",
        "تذاكر الطيران الدولية ذهابًا وإيابًا."
    ]
}

print("POST /quotations (B2B Arab)...")
response = client.post("/quotations?lang=ar", json=payload)
print("Response status code:", response.status_code)
try:
    res_json = response.json()
    print("Response JSON:", json.dumps(res_json, indent=2))
    quotation_id = res_json.get("quotationId")
    if quotation_id:
        print(f"Quotation {quotation_id} generated successfully!")
        
        # Verify get endpoint
        get_res = client.get(f"/quotations/{quotation_id}?lang=ar")
        print(f"GET /quotations/{quotation_id} status:", get_res.status_code)
        
        get_pdf_res = client.get(f"/quotations/{quotation_id}/pdf?lang=ar")
        print(f"GET /quotations/{quotation_id}/pdf status:", get_pdf_res.status_code)
        
except Exception as e:
    print("Failed to parse response:", e)
    print("Response text:", response.text)
