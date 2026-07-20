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
    print("[Mock] Extracting and mapping destinations for: Hanoi, Ninh Binh, Halong Bay, Sapa")
    return [
        {"name": "Hanoi", "slug": "ha-noi"},
        {"name": "Ninh Binh", "slug": "ninh-binh"},
        {"name": "Halong Bay", "slug": "quang-ninh"},
        {"name": "Sapa", "slug": "lao-cai"}
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
        "ninh binh": "ninh-binh",
        "ninhbinh": "ninh-binh",
        "halong bay": "quang-ninh",
        "halong": "quang-ninh",
        "ha long": "quang-ninh",
        "sapa": "lao-cai",
        "lao cai": "lao-cai",
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

# Structure the full 7-day Indian traveler English itinerary payload
payload = {
    "quotationNumber": "QT-2026-CAPELLA-7D6N-IND",
    "lang": "en",
    "quotationNarrative": (
        "A premium, personalized 7-day private journey crafted by Capella Travel for our Indian guests. "
        "The itinerary showcases the historic soul of Hanoi, the mystical rivers of Ninh Binh, "
        "an overnight cruise through the magical waters of Ha Long Bay, and the breathtaking terraced mountains of Sapa. "
        "Every detail, from the double and triple room configurations to the carefully curated vegetarian culinary experiences, "
        "has been designed for your group of 5 adults to travel in ultimate comfort."
    ),
    "landingpageContent": {
        "heroSection": {
            "headline": "Bespoke Northern Vietnam Exploration",
            "subtitle": "A Luxury Private Journey Specially Crafted for 5 Indian Guests"
        },
        "visualDescription": "A luxury travel landing page featuring scenery of Hanoi, Ninh Binh, Halong Bay, and Sapa mountains."
    },
    "journeyGlance": {
        "market": "Indian Market",
        "guestProfile": "5 Adults (Double + Triple Room Configuration)",
        "hotelStandard": "Premium 4★ Hotels & 5★ Luxury Cruise",
        "mealPreference": "Indian Vegetarian (Lacto-Ovo: Eggs allowed, strictly no meat, fish, or seafood)",
        "priceType": "Indicative",
        "tourCode": "CT-2026-7D6N-IND",
        "domesticFlights": "Not Required (Private ground transfers & premium overnight train)",
        "priceBasis": "Twin/Double/Triple sharing basis (1 Double Room + 1 Triple Room)",
        "partnerNote": "Fully private tour with dedicated English-speaking guides, private transfers, and curated vegetarian meals.",
        "validity": "Valid for travel from September to October 2026"
    },
    "whyWorks": {
        "privateFlexible": (
            "Travel in complete exclusivity with your private air-conditioned vehicle and dedicated English-speaking guide. "
            "The daily pacing is highly flexible, ensuring your group can explore Hanoi, Ninh Binh, Sapa, and Halong Bay "
            "comfortably at your own speed."
        ),
        "comfort": (
            "Enjoy premium accommodations including Hanoi Le Jardin Hotel & Spa, Ambassador Signature Cruise in Halong, "
            "and Aliana Boutique Sapa. For the overnight train journey to Sapa, we have pre-arranged 2 private 4-berth cabins "
            "on the Chapa Express Train to guarantee absolute privacy and space for your group of 5."
        ),
        "muslimFriendly": (
            "Your dietary requirements are fully respected. All included meals feature carefully curated Indian vegetarian selections, "
            "with eggs permitted and strictly no meat, fish, or seafood. Restaurants and cruise chefs are briefed to prevent cross-contamination."
        ),
        "balancedHighlights": (
            "A perfect harmony of historic culture in Hanoi, scenic rivers in Ninh Binh, a luxury overnight cruise in Halong Bay, "
            "and highland exploration in Sapa, offering a complete northern Vietnam experience in 7 days."
        )
    },
    "itinerary": [
        {
            "dayNumber": 1,
            "destination": "Hanoi",
            "summary": (
                "Welcome to Hanoi! Upon arriving at Noi Bai International Airport on your early morning flight (arrivals at 5:00 AM and 7:30 AM), "
                "our private host will greet you at the boarding gate with VIP Airport Fast-track service to expedite immigration. "
                "Transfer by private air-conditioned vehicle to Hanoi Le Jardin Hotel & Spa, where early check-in has been pre-arranged "
                "so you can rest immediately. In the evening, gather for a welcome Indian vegetarian dinner."
            ),
            "mainInclusions": "VIP Airport Fast-track, private airport transfer, pre-arranged hotel early check-in, gourmet Indian vegetarian welcome dinner.",
            "senseOfPace": "Relaxed",
            "dining": "Indian Vegetarian Welcome Dinner"
        },
        {
            "dayNumber": 2,
            "destination": "Ninh Binh",
            "summary": (
                "Embark on a full-day private excursion to Ninh Binh. Experience the serene beauty of Trang An landscape complex, "
                "a UNESCO World Heritage site, during a traditional rowboat tour through limestone caves. Visit the ancient capital of Hoa Lu "
                "and climb to the peak of Mua Cave for panoramic views over the rice fields. Savor a local vegetarian lunch (eggs allowed, no fish/meat). "
                "Return to Hanoi for your overnight stay."
            ),
            "mainInclusions": "Private roundtrip vehicle to Ninh Binh, English guide, Trang An boat tour, Mua Cave entry, vegetarian lunch.",
            "senseOfPace": "Active",
            "dining": "Breakfast & Indian Vegetarian Lunch"
        },
        {
            "dayNumber": 3,
            "destination": "Halong Bay",
            "summary": (
                "Depart Hanoi by private vehicle to Halong Bay. Board the premium Ambassador Signature Cruise, where your Double and Triple "
                "cabins await. Glide past iconic karst formations and enjoy a delicious vegetarian buffet lunch on board. "
                "Participate in cruise activities including a bamboo boat ride, kayaking, or climbing for scenic viewpoints. "
                "Savor a premium vegetarian set-dinner on board under the stars."
            ),
            "mainInclusions": "Private transfer Hanoi - Halong, double & triple cabins on Ambassador Signature Cruise, cruise excursions, onboard vegetarian lunch and dinner.",
            "senseOfPace": "Relaxed",
            "dining": "Breakfast, Onboard Vegetarian Lunch & Dinner"
        },
        {
            "dayNumber": 4,
            "destination": "Hanoi / Sapa",
            "summary": (
                "Greet the sunrise with Tai Chi on the sundeck. After a vegetarian brunch, check out and transfer back to Hanoi. "
                "Enjoy a private half-day city tour of Hanoi, visiting the historic Temple of Literature and Hoan Kiem Lake. "
                "Enjoy some free time for shopping. In the evening, savor a vegetarian dinner in Hanoi before boarding the Chapa Express Train "
                "to Sapa, where you will stay in 2 private 4-berth cabins for complete comfort."
            ),
            "mainInclusions": "Onboard vegetarian brunch, private transfer Halong - Hanoi, Hanoi half-day tour with guide and entry tickets, private vegetarian dinner, Chapa Express Train tickets.",
            "senseOfPace": "Active",
            "dining": "Onboard Vegetarian Brunch & Private Dinner"
        },
        {
            "dayNumber": 5,
            "destination": "Sapa",
            "summary": (
                "Arrive at Lao Cai station early in the morning and transfer to Sapa town. Check in to Aliana Boutique Sapa Hotel And Spa "
                "and enjoy a hot breakfast. Embark on a guided trekking tour to Cat Cat village, learning about the Black Hmong culture "
                "and viewing the scenic waterfall. Savor a local vegetarian lunch. Spend a relaxed afternoon exploring Sapa town at leisure."
            ),
            "mainInclusions": "Station transfer, Sapa tour with guide and entry tickets, vegetarian lunch.",
            "senseOfPace": "Immersive",
            "dining": "Breakfast & Vegetarian Lunch"
        },
        {
            "dayNumber": 6,
            "destination": "Sapa",
            "summary": (
                "A highlights day in Sapa! Take the Fansipan cable car, the longest three-rope cable car system in the world, to ascend "
                "the 'Roof of Indochina' at 3,143 meters. Explore the spiritual pagoda complex at the summit. Enjoy a scenic vegetarian lunch. "
                "In the afternoon, visit Ta Van village or shop for souvenirs in Sapa town. Overnight at Aliana Boutique Sapa."
            ),
            "mainInclusions": "Fansipan cable car roundtrip tickets, guide, Sapa transfers, vegetarian lunch.",
            "senseOfPace": "Active",
            "dining": "Breakfast & Vegetarian Lunch"
        },
        {
            "dayNumber": 7,
            "destination": "Hanoi",
            "summary": (
                "Enjoy a leisurely morning in Sapa for final sightseeing or shopping. In the afternoon, board your private luxury vehicle "
                "for the scenic drive back to Hanoi (approx. 5 hours). Arrive directly at Noi Bai International Airport "
                "for your late-evening international departure flight."
            ),
            "mainInclusions": "Private luxury transfer Sapa - Hanoi Airport.",
            "senseOfPace": "Relaxed",
            "dining": "Breakfast"
        }
    ],
    "hotelPlan": {
        "hotels": [
            {
                "destination": "Hanoi",
                "checkInDate": "2026-09-30",
                "checkOutDate": "2026-10-02",
                "hotelArrangement": "Hanoi Le Jardin Hotel & Spa - 1 Deluxe Double Room + 1 Deluxe Triple Room - 2 Nights"
            },
            {
                "destination": "Halong Bay",
                "checkInDate": "2026-10-02",
                "checkOutDate": "2026-10-03",
                "hotelArrangement": "Ambassador Signature Cruise - 1 Premium Double Cabin + 1 Premium Triple Cabin - 1 Night"
            },
            {
                "destination": "Sapa",
                "checkInDate": "2026-10-03",
                "checkOutDate": "2026-10-04",
                "hotelArrangement": "Chapa Express Train (Overnight sleeper train) - 2 Private 4-Berth Cabins - 1 Night"
            },
            {
                "destination": "Sapa",
                "checkInDate": "2026-10-04",
                "checkOutDate": "2026-10-06",
                "hotelArrangement": "Aliana Boutique Sapa Hotel And Spa - 1 Deluxe Double Room + 1 Deluxe Triple Room - 2 Nights"
            }
        ],
        "roomNotes": (
            "Double + Triple room configurations pre-arranged across all properties. "
            "For the overnight train, 2 private 4-berth cabins have been fully booked for 5 guests to ensure complete comfort."
        )
    },
    "optionalEnhancements": [
        {
            "title": "Private Vegetarian Cooking Class in Hanoi (adapted for Indian recipes)",
            "status": "Recommended"
        },
        {
            "title": "Room Upgrade to Executive Suite at Aliana Boutique Sapa Hotel & Spa",
            "status": "On request"
        }
    ],
    "bookingTerms": {
        "deposit": "A 30% deposit is required at the time of booking to secure hotels, cruise, and train cabins.",
        "balance": "The remaining 70% balance is due 30 days prior to arrival.",
        "cancellation": "Free cancellation up to 45 days prior to departure. 50% cancellation fee between 44 and 15 days.",
        "confirmation": "Subject to availability. Final confirmations will be sent within 24 hours of deposit receipt."
    },
    "finalization": {
        "finalDetailsRequired": "Passport copies valid for at least 6 months and international flight details are required to complete arrangements.",
        "afterConfirmation": "Your dedicated 24/7 travel host details and final service vouchers will be shared 7 days prior to departure."
    },
    "pricing": {
        "currency": "USD",
        "pricingTitle": "Premium Journey Investment",
        "basis": "Based on 5 Adults sharing 1 Double Room + 1 Triple Room",
        "priceOptions": [
            {
                "label": "Premium Accommodations & Cruise (5 Adults)",
                "notes": "1,091.25 USD per person on Double + Triple sharing basis",
                "amount": 1091.25
            }
        ],
        "subtotal": 5456.25,
        "discountTotal": 0.0,
        "taxTotal": 0.0,
        "grandTotal": 5456.25
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
            "source_day_numbers": [1, 2]
        },
        {
            "block_id": "H_HALONG",
            "service_type": "hotel",
            "destination": "Halong Bay",
            "source_day_numbers": [3]
        },
        {
            "block_id": "T_TRAIN",
            "service_type": "transfer",
            "destination": "Sapa",
            "source_day_numbers": [4]
        },
        {
            "block_id": "H_SAPA",
            "service_type": "hotel",
            "destination": "Sapa",
            "source_day_numbers": [5, 6]
        }
    ],
    "inclusions": [
        "Premium accommodation in Hanoi (Hanoi Le Jardin Hotel & Spa) and Sapa (Aliana Boutique Sapa) with early check-in pre-arranged on Day 1.",
        "Overnight luxury cruise on Ambassador Signature Cruise in Halong Bay with all onboard meals included.",
        "Overnight sleeper train tickets on Chapa Express Train in 2 private 4-berth cabins for comfort and privacy.",
        "Private VIP fast-track immigration handling and airport transfers upon arrival in Hanoi.",
        "All ground transfers in private air-conditioned vehicles as detailed in the itinerary.",
        "Private English-speaking guides for all sightseeing tours and excursions.",
        "All entrance fees, boat tickets, and activity charges (including Fansipan cable car tickets).",
        "Vietnam E-visas processing and fees included for all 5 guests.",
        "Dedicated Indian vegetarian meals (Lacto-Ovo: eggs allowed, strictly no meat, fish, or seafood) pre-arranged at all stops."
    ],
    "exclusions": [
        "International flights to and from Vietnam.",
        "Personal expenses (laundry, beverages, telephone calls, etc.).",
        "Travel insurance (highly recommended).",
        "Tips and gratuities for guides and drivers."
    ]
}

print("POST /quotations (B2B English)...")
response = client.post("/quotations?lang=en", json=payload)
print("Response status code:", response.status_code)
try:
    res_json = response.json()
    print("Response JSON:", json.dumps(res_json, indent=2))
    quotation_id = res_json.get("quotationId")
    if quotation_id:
        print(f"Quotation {quotation_id} generated successfully!")
        
        # Verify get endpoint and save HTML
        get_res = client.get(f"/quotations/{quotation_id}?lang=en")
        print(f"GET /quotations/{quotation_id} status:", get_res.status_code)
        if get_res.status_code == 200:
            output_file = "vietnam-heritage-luxury-indian-7d6n-quotation.html"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(get_res.text)
            print(f"HTML saved to: {output_file}")
        
        get_pdf_res = client.get(f"/quotations/{quotation_id}/pdf?lang=en")
        print(f"GET /quotations/{quotation_id}/pdf status:", get_pdf_res.status_code)
        
except Exception as e:
    print("Failed to parse response:", e)
    print("Response text:", response.text)
