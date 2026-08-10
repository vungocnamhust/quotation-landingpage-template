import asyncio
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import patch
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
import main
import image_selector
from quote_generation import NarrativeGenerator, _fallback_narrative_result

# Generate a unique new Quotation ID
NEW_QUO_ID = f"quo_{uuid.uuid4().hex[:12]}"
print(f"Creating new Quotation V2 with ID: {NEW_QUO_ID}")

@asynccontextmanager
async def mock_db_session():
    class DummySession:
        bind = None
        def add(self, instance):
            pass
        async def execute(self, statement, *args, **kwargs):
            class DummyResult:
                def scalar_one_or_none(self):
                    return None
                def scalars(self):
                    return self
                def first(self):
                    return None
                def all(self):
                    return []
            return DummyResult()
        async def get(self, entity_cls, ident):
            instance = entity_cls()
            if hasattr(instance, "id"):
                instance.id = ident
            if hasattr(instance, "quotation_id"):
                instance.quotation_id = ident
            if hasattr(instance, "template_name"):
                instance.template_name = "vietnam_luxury_brosure.html"
            if hasattr(instance, "baseline_lang"):
                instance.baseline_lang = "en"
            if hasattr(instance, "revision"):
                instance.revision = 1
            if hasattr(instance, "document_json"):
                try:
                    with open(f"published/{ident}/document.json", "r", encoding="utf-8") as f:
                        instance.document_json = json.load(f)
                except Exception:
                    instance.document_json = {"meta": {"version": 1, "revision": 1}}
            return instance
        async def flush(self):
            pass
        async def commit(self):
            pass
    yield DummySession()

def create_sample_quote_request() -> dict:
    return {
        "opportunity_id": f"OPP-{NEW_QUO_ID.upper()}",
        "brand_id": "capella_travel",
        "lang": "en",
        "trip_facts": {
            "destinations": ["Hanoi", "Hue", "Hoi An", "Phu Quoc"],
            "start_date": "2026-11-01",
            "end_date": "2026-11-10",
            "duration_days": 10,
            "duration_nights": 9,
            "display_route_text": "Hanoi – Hue – Hoi An – Phu Quoc",
            "display_travel_dates": "01 Nov – 10 Nov 2026",
            "itinerary": [
                {
                    "day_number": 1,
                    "destination": "Hanoi",
                    "summary": "Arrival in Hanoi. Private VIP welcome at airport and transfer to Capella Hanoi.",
                    "overnight": "Hanoi",
                    "meals": ["Welcome Dinner"],
                    "highlights": ["VIP Airport Fast-track", "Capella Opera Suite Check-in", "Welcome Dinner"],
                    "notes": ["Sense of Pace: Relaxed"],
                    "display_date": "01 Nov 2026"
                },
                {
                    "day_number": 2,
                    "destination": "Hanoi",
                    "summary": "Private French Quarter & Old Quarter culinary exploration.",
                    "overnight": "Hanoi",
                    "meals": ["Breakfast", "Lunch"],
                    "highlights": ["Private Cyclo Discovery", "Gourmet Street Food", "Water Puppet VIP Seating"],
                    "notes": ["Sense of Pace: Immersive"],
                    "display_date": "02 Nov 2026"
                },
                {
                    "day_number": 3,
                    "destination": "Hue",
                    "summary": "Flight to Imperial City of Hue. Private dragon boat ride on Perfume River.",
                    "overnight": "Hue",
                    "meals": ["Breakfast", "Dinner"],
                    "highlights": ["Imperial Citadel Tour", "Private Royal Banquet"],
                    "notes": ["Sense of Pace: Cultural"],
                    "display_date": "03 Nov 2026"
                },
                {
                    "day_number": 4,
                    "destination": "Hoi An",
                    "summary": "Scenic drive via Hai Van Pass to Four Seasons Nam Hai Hoi An.",
                    "overnight": "Hoi An",
                    "meals": ["Breakfast", "Lunch"],
                    "highlights": ["Hai Van Pass Drive", "Ancient Town Lantern Walking Tour"],
                    "notes": ["Sense of Pace: Relaxed"],
                    "display_date": "04 Nov 2026"
                },
                {
                    "day_number": 5,
                    "destination": "Hoi An",
                    "summary": "Private cooking masterclass at Tra Que Organic Village & Beach Relaxation.",
                    "overnight": "Hoi An",
                    "meals": ["Breakfast", "Lunch"],
                    "highlights": ["Tra Que Farming & Cooking", "Private Beach Sunset"],
                    "notes": ["Sense of Pace: Leisure"],
                    "display_date": "05 Nov 2026"
                },
                {
                    "day_number": 6,
                    "destination": "Phu Quoc",
                    "summary": "Flight to Phu Quoc Island. Check-in to Regent Phu Quoc Ocean Pool Villa.",
                    "overnight": "Phu Quoc",
                    "meals": ["Breakfast", "Sunset Cocktail"],
                    "highlights": ["Private Ocean Villa", "Rooftop Sunset Sundown"],
                    "notes": ["Sense of Pace: Ultra Relaxed"],
                    "display_date": "06 Nov 2026"
                },
                {
                    "day_number": 7,
                    "destination": "Phu Quoc",
                    "summary": "Private luxury yacht cruise through An Thoi archipelago.",
                    "overnight": "Phu Quoc",
                    "meals": ["Breakfast", "Seafood BBQ Lunch"],
                    "highlights": ["Snorkeling at Coral Reefs", "Gourmet Seafood BBQ"],
                    "notes": ["Sense of Pace: Exclusive"],
                    "display_date": "07 Nov 2026"
                },
                {
                    "day_number": 8,
                    "destination": "Phu Quoc",
                    "summary": "Spa sanctuary day & private beach dinner under the stars.",
                    "overnight": "Phu Quoc",
                    "meals": ["Breakfast", "Private Beach Dinner"],
                    "highlights": ["Signature Couple Spa Treatment", "Candlelit Beach Dining"],
                    "notes": ["Sense of Pace: Wellness"],
                    "display_date": "08 Nov 2026"
                },
                {
                    "day_number": 9,
                    "destination": "Hanoi",
                    "summary": "Flight back to Hanoi for final evening shopping & farewell dinner.",
                    "overnight": "Hanoi",
                    "meals": ["Breakfast", "Farewell Dinner"],
                    "highlights": ["Art Gallery Tour", "Michelin-starred Farewell Dinner"],
                    "notes": ["Sense of Pace: Celebration"],
                    "display_date": "09 Nov 2026"
                },
                {
                    "day_number": 10,
                    "destination": "Hanoi",
                    "summary": "Leisure morning, private luxury transfer to airport for international flight.",
                    "overnight": "Hanoi",
                    "meals": ["Breakfast"],
                    "highlights": ["Private Airport Transfer"],
                    "notes": ["Sense of Pace: Departure"],
                    "display_date": "10 Nov 2026"
                }
            ]
        },
        "pricing_facts": {
            "conditions": ["Rates are indicative subject to seasonal hotel availability."],
            "options": [
                {
                    "id": "ultra-luxury-tier",
                    "label": "Capella, Nam Hai & Regent Villas",
                    "currency": "USD",
                    "per_traveler_amount_minor": 520_000,
                    "group_total_amount_minor": 1_040_000,
                }
            ]
        },
        "customer_facts": {
            "customer_name": "Lord & Lady Harrington",
            "adults": 2,
            "children": 0,
            "nationality": "United Kingdom",
            "guest_profile": "VIP Honeymoon Couple",
            "market": "UK / Europe",
            "party_label": "Lord & Lady Harrington",
            "greeting_name": "Lord & Lady Harrington"
        },
        "service_facts": {
            "hotels": [
                {
                    "destination": "Hanoi",
                    "name": "Capella Hanoi",
                    "room_type": "Capella Suite",
                    "check_in": "2026-11-01",
                    "check_out": "2026-11-03",
                    "intro": "Opera-inspired ultra luxury in Hanoi Old Quarter.",
                    "phone": "+84 24 3987 8888",
                    "display_city": "HANOI, VIETNAM",
                    "display_date": "01 Nov – 03 Nov 2026"
                },
                {
                    "destination": "Hue",
                    "name": "Azerai La Residence Hue",
                    "room_type": "Superior River View Suite",
                    "check_in": "2026-11-03",
                    "check_out": "2026-11-04",
                    "intro": "Art Deco mansion on the banks of the Perfume River.",
                    "phone": "+84 234 3837 475",
                    "display_city": "HUE, VIETNAM",
                    "display_date": "03 Nov – 04 Nov 2026"
                },
                {
                    "destination": "Hoi An",
                    "name": "Four Seasons Resort The Nam Hai",
                    "room_type": "Oceanfront Villa",
                    "check_in": "2026-11-04",
                    "check_out": "2026-11-06",
                    "intro": "All-villa luxury resort along Ha My Beach.",
                    "phone": "+84 235 3940 000",
                    "display_city": "HOI AN, VIETNAM",
                    "display_date": "04 Nov – 06 Nov 2026"
                },
                {
                    "destination": "Phu Quoc",
                    "name": "Regent Phu Quoc",
                    "room_type": "Sky Pool Villa",
                    "check_in": "2026-11-06",
                    "check_out": "2026-11-09",
                    "intro": "Haute luxury island sanctuary overlooking the Gulf of Siam.",
                    "phone": "+84 297 388 0000",
                    "display_city": "PHU QUOC, VIETNAM",
                    "display_date": "06 Nov – 09 Nov 2026"
                }
            ],
            "inclusions": [
                "Private VIP Airport Fast-track & Transfers in Luxury Vehicles",
                "5-Star Ultra Luxury Suites & Ocean Villas with Daily Breakfast",
                "Dedicated English-speaking Private Tour Guide & Private Driver",
                "Private Yacht Charter in Phu Quoc Archipelago",
                "24/7 Personal Travel Concierge Service"
            ],
            "exclusions": [
                "International Airfare",
                "Personal Expenses & Gratuities",
                "Travel Insurance"
            ]
        },
        "booking_facts": {
            "title": "Booking & Payment Terms",
            "description": "Capella Travel luxury booking policy.",
            "items": [
                {"key": "deposit", "label": "Deposit", "body": "30% deposit required upon confirmation."},
                {"key": "balance", "label": "Balance", "body": "70% balance due 60 days before arrival."},
                {"key": "cancellation", "label": "Cancellation", "body": "Written notice required. See full terms."}
            ]
        },
        "seller_facts": {
            "seller_name": "Capella Travel",
            "seller_email": "concierge@capellatravel.com",
            "seller_phone": "+84 911 538 738",
            "designer_name": "Julian Vance",
            "designer_title": "Principal Luxury Travel Architect",
            "designer_quote": "Crafting unforgettable moments of coastal elegance and heritage in Indochina."
        }
    }

async def mock_generate(self, request, brand_profile):
    return _fallback_narrative_result(request, brand_profile), 'fallback', []

async def mock_extract_destinations(text, max_items=None):
    return [
        {'name': 'Hanoi', 'slug': 'ha-noi'},
        {'name': 'Hue', 'slug': 'thua-thien-hue'},
        {'name': 'Hoi An', 'slug': 'quang-nam'},
        {'name': 'Phu Quoc', 'slug': 'kien-giang'}
    ]

def main_run():
    payload = create_sample_quote_request()
    print(f"Creating Quotation {NEW_QUO_ID} via API /api/v2/quotations...")

    with patch.object(NarrativeGenerator, 'generate', mock_generate), \
         patch.object(image_selector, 'extract_and_map_destinations', mock_extract_destinations), \
         patch.object(main, '_get_db_session_factory', lambda: mock_db_session):
        client = TestClient(main.app)
        response = client.post('/api/v2/quotations', json=payload)
        
        print("HTTP Status Code:", response.status_code)
        if response.status_code == 200:
            res = response.json()
            quo_id = res.get('quotationId')
            print("\n=======================================================")
            print(" 🎉 NEW QUOTATION V2 CREATED SUCCESSFULLY!")
            print("=======================================================")
            print(f"New Quotation ID: {quo_id}")
            print(f"Status:           {res.get('status')}")
            print(f"Baseline Lang:    {res.get('baselineLang')}")
            print(f"Quotation URL:    http://localhost:8111/quotations/{quo_id}?brand=capella_travel")
            print(f"PDF URL:          http://localhost:8111/quotations/{quo_id}/pdf?brand=capella_travel")
            return quo_id
        else:
            print("Error details:", response.text)
            return None

if __name__ == "__main__":
    main_run()
