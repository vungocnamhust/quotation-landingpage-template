import json
import os
import sys
from fastapi.testclient import TestClient

# Add current directory to path so main can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Mock the OpenAI-based image selector before importing main
import image_selector
async def mock_extract_and_map_destinations(text, max_items=None):
    print("[Mock] Extracting and mapping destinations for: Hanoi, Halong Bay, Hoi An, Da Nang")
    return [
        {"name": "Hà Nội", "slug": "ha-noi"},
        {"name": "Vịnh Hạ Long", "slug": "quang-ninh"},
        {"name": "Hội An", "slug": "quang-nam"},
        {"name": "Đà Nẵng", "slug": "da-nang"}
    ]
image_selector.extract_and_map_destinations = mock_extract_and_map_destinations

from main import app

client = TestClient(app)

payload = {
    "quotationNumber": "QT-2026-8D7N",
    "quotationNarrative": "A premium 8-day private heritage journey weaving through Vietnam's iconic wonders, from the historic charm of Hanoi and mystical waters of Halong Bay to the lantern-lit streets of Hoi An.",
    "landingpageContent": {
        "heroSection": {
            "headline": "HERITAGE & NATURAL WONDERS",
            "subtitle": "VIETNAM LUXURY IMPERIAL & COASTAL JOURNEY — 8D7N"
        },
        "visualDescription": "A luxury travel landing page featuring beautiful scenery of Vietnam."
    },
    "journeyGlance": {
        "market": "Global Luxury Travelers",
        "guestProfile": "2 Adults (Couple / Honeymooners)",
        "hotelStandard": "5★ Ultra-Luxury & Boutique Resorts",
        "mealPreference": "All-inclusive Breakfasts + Curated Gourmet Dinning",
        "priceType": "Indicative",
        "tourCode": "VS-8D7N-HERITAGE",
        "domesticFlights": "Included (Hanoi to Da Nang - Business Class)",
        "priceBasis": "Twin-sharing basis",
        "partnerNote": "Private VIP transfers, english speaking guides, all entry tickets included.",
        "validity": "Valid for travel from September to December 2026"
    },
    "whyWorks": {
        "privateFlexible": "Your personal chauffeur and dedicated English-speaking historian guide are at your exclusive disposal, ensuring the pace is entirely yours to set.",
        "comfort": "Rest easy with pre-selected five-star boutique hotels, private business-class internal flights, and spacious Mercedes-Benz V-Class transfers throughout the trip.",
        "muslimFriendly": "Dietary requests are fully respected; we have pre-arranged halal-certified dining options and pork-free gourmet menus at every destination.",
        "balancedHighlights": "Perfectly balanced between the high-energy culture of Hanoi, the serene cruising of Halong Bay, and the atmospheric slow-living coastal beauty of Hoi An."
    },
    "itinerary": [
        {
            "dayNumber": 1,
            "destination": "Hanoi",
            "summary": "Welcome to Hanoi. Private VIP immigration handling at Noi Bai Airport, followed by a luxury transfer to your hotel. Unwind and enjoy a welcome Vietnamese fusion dinner.",
            "mainInclusions": "VIP Airport Fast-track, luxury airport transfer, welcome dinner.",
            "senseOfPace": "Relaxed",
            "dining": "Dinner"
        },
        {
            "dayNumber": 2,
            "destination": "Hanoi",
            "summary": "Explore Hanoi's rich cultural landmarks: Ho Chi Minh Mausoleum, the historic Temple of Literature, and a cyclo ride through the 36 streets of the Old Quarter. End with a unique Train Street coffee experience.",
            "mainInclusions": "English guide, private transport, entrance tickets, Old Quarter cyclo tour.",
            "senseOfPace": "Immersive",
            "dining": "Breakfast & Lunch"
        },
        {
            "dayNumber": 3,
            "destination": "Halong Bay",
            "summary": "Scenic drive to Halong Bay. Board your ultra-luxury cruise ship. Sail past spectacular limestone karsts, visit hidden caves, and enjoy sunset cocktails on the sundeck.",
            "mainInclusions": "Luxury transfer to Halong Bay, luxury cruise cabin, onboard activities, all meals.",
            "senseOfPace": "Relaxed",
            "dining": "Breakfast, Lunch, Dinner"
        },
        {
            "dayNumber": 4,
            "destination": "Da Nang",
            "summary": "Morning tai-chi on the sundeck and light breakfast. Cruise back to port, then transfer directly to Noi Bai Airport for a quick flight to Da Nang. Private transfer to Hoi An Ancient Town.",
            "mainInclusions": "Flight Hanoi - Da Nang, cruise activities, airport transfers, hotel check-in.",
            "senseOfPace": "Active",
            "dining": "Breakfast & Brunch"
        },
        {
            "dayNumber": 5,
            "destination": "Hoi An",
            "summary": "Walking tour of Hoi An Ancient Town. Discover Chinese assembly halls, the Japanese Covered Bridge, and participate in a private, hands-on traditional lantern-making workshop.",
            "mainInclusions": "Hoi An walking tour tickets, lantern workshop session, private guide.",
            "senseOfPace": "Immersive",
            "dining": "Breakfast & Lunch"
        },
        {
            "dayNumber": 6,
            "destination": "Hoi An",
            "summary": "Discover the ancient Cham ruins at My Son Sanctuary, followed by a scenic cruise on the Thu Bon River. Spend a relaxing afternoon exploring Hoi An's boutique shops or beach clubs.",
            "mainInclusions": "My Son Sanctuary entrance, river boat cruise, private guide, transport.",
            "senseOfPace": "Moderate",
            "dining": "Breakfast"
        },
        {
            "dayNumber": 7,
            "destination": "Da Nang",
            "summary": "Take a day trip to the Sun World Ba Na Hills. Ride the world's longest cable car system and walk along the iconic Golden Bridge held by giant stone hands.",
            "mainInclusions": "Cable car tickets, Ba Na Hills entry, private transfers, local guide.",
            "senseOfPace": "Active",
            "dining": "Breakfast & Lunch"
        },
        {
            "dayNumber": 8,
            "destination": "Da Nang",
            "summary": "Morning at leisure. Final private transfer to Da Nang International Airport for your departure flight, carrying beautiful memories of Vietnam.",
            "mainInclusions": "Private airport departure transfer.",
            "senseOfPace": "Relaxed",
            "dining": "Breakfast"
        }
    ],
    "hotelPlan": {
        "hotels": [
            {
                "destination": "Hanoi",
                "checkInDate": "2026-09-20",
                "checkOutDate": "2026-09-22",
                "hotelArrangement": "Sofitel Legend Metropole Hanoi (Grand Luxury Room)"
            },
            {
                "destination": "Halong Bay",
                "checkInDate": "2026-09-22",
                "checkOutDate": "2026-09-23",
                "hotelArrangement": "Orchid Classic Cruise (Suite with Private Balcony)"
            },
            {
                "destination": "Hoi An",
                "checkInDate": "2026-09-23",
                "checkOutDate": "2026-09-27",
                "hotelArrangement": "Four Seasons Resort The Nam Hai (One-Bedroom Villa)"
            }
        ],
        "roomNotes": "King size bed requested. Quiet room on high floor or private corner location."
    },
    "optionalEnhancements": [
        {
            "title": "Private Evening Street Food Tour by Vintage Vespa in Hanoi",
            "status": "Recommended"
        },
        {
            "title": "Private Sunrise Yacht and Champagne Cruise in Da Nang Bay",
            "status": "Recommended"
        }
    ],
    "bookingTerms": {
        "deposit": "30% deposit upon booking confirmation to secure luxury accommodations.",
        "balance": "70% balance due 30 days prior to departure.",
        "cancellation": "Free cancellation up to 45 days prior to arrival. 50% between 44 to 15 days.",
        "confirmation": "Subject to availability. Confirmations sent within 24 hours of deposit."
    },
    "finalization": {
        "finalDetailsRequired": "Colored passport scan valid for at least 6 months and visa details if required.",
        "afterConfirmation": "24/7 VIP Concierge contact details will be shared 7 days prior to departure."
    },
    "pricing": {
        "totalPriceUsd": 14950.0,
        "currency": "USD",
        "markupApplied": 0.15,
        "breakdown": {
            "hotels": 8500.0,
            "activities": 2500.0,
            "guides": 1200.0,
            "transfers": 1500.0,
            "flights": 1250.0
        }
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
            "block_id": "H1",
            "service_type": "hotel",
            "destination": "Hanoi",
            "source_day_numbers": [1, 2]
        },
        {
            "block_id": "H2",
            "service_type": "hotel",
            "destination": "Halong Bay",
            "source_day_numbers": [3]
        },
        {
            "block_id": "H3",
            "service_type": "hotel",
            "destination": "Hoi An",
            "source_day_numbers": [4, 5, 6, 7]
        }
    ]
}

print("Generating quotation...")
response = client.post("/quotations/b2c", json=payload)
if response.status_code == 200:
    res_data = response.json()
    quotation_id = res_data.get("quotationId")
    print(f"Quotation created successfully with ID: {quotation_id}")
    
    # Retrieve the rendered HTML via test client GET request
    get_response = client.get(f"/quotations/{quotation_id}")
    if get_response.status_code == 200:
        output_file = "vietnam-heritage-luxury-8d7n-quotation.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(get_response.text)
        print(f"HTML saved to: {output_file}")
    else:
        print(f"Failed to retrieve HTML content (Status {get_response.status_code}):", get_response.text)
else:
    print("Failed to create quotation:", response.status_code)
    print(response.text)
