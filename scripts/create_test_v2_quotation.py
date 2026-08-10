import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

import main
import image_selector
from contextlib import asynccontextmanager

from quote_document import CreateQuoteRequestV1
from quote_document_adapter import normalize_quote_document
from quote_generation import NarrativeGenerator, _fallback_narrative_result

@asynccontextmanager
async def mock_db_session():
    class DummySession:
        def add(self, instance):
            pass
        async def execute(self, statement, *args, **kwargs):
            class DummyResult:
                def scalar_one_or_none(self):
                    doc_path = Path(f"published/quo_60c3acf8f3ff/document.json")
                    if doc_path.exists():
                        doc_json = json.loads(doc_path.read_text(encoding="utf-8"))
                    else:
                        doc_json = {}
                    from db.models.quotation import QuotationDocument
                    qd = QuotationDocument()
                    qd.quotation_id = "quo_60c3acf8f3ff"
                    qd.lang = "en"
                    qd.revision = 1
                    qd.document_json = doc_json
                    return qd
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
        "opportunity_id": "OPP-TEST-V2-001",
        "brand_id": "vietnam_safar",
        "lang": "en",
        "trip_facts": {
            "destinations": ["Hanoi", "Ninh Binh", "Halong Bay", "Sapa"],
            "start_date": "2026-10-01",
            "end_date": "2026-10-08",
            "duration_days": 8,
            "duration_nights": 7,
            "display_route_text": "Hanoi – Ninh Binh – Halong Bay – Sapa – Hanoi",
            "display_travel_dates": "01 Oct – 08 Oct 2026",
            "itinerary": [
                {
                    "day_number": 1,
                    "destination": "Hanoi",
                    "summary": "Arrival in Hanoi. VIP fast-track welcome and private transfer to luxury hotel in Old Quarter.",
                    "overnight": "Hanoi",
                    "meals": ["Welcome Dinner"],
                    "highlights": ["VIP Fast-track", "Private Transfer", "Gourmet Welcome Dinner"],
                    "notes": ["Sense of Pace: Relaxed"],
                    "display_date": "01 Oct 2026"
                },
                {
                    "day_number": 2,
                    "destination": "Hanoi",
                    "summary": "Full day private cultural discovery of Hanoi: Temple of Literature, French Quarter, and street food tour.",
                    "overnight": "Hanoi",
                    "meals": ["Breakfast", "Lunch"],
                    "highlights": ["Temple of Literature", "Cyclo Tour", "Street Food Exploration"],
                    "notes": ["Sense of Pace: Immersive"],
                    "display_date": "02 Oct 2026"
                },
                {
                    "day_number": 3,
                    "destination": "Ninh Binh",
                    "summary": "Private drive to Ninh Binh. Sample sampan ride through Trang An caves and climb Mua Cave peak.",
                    "overnight": "Ninh Binh",
                    "meals": ["Breakfast", "Lunch"],
                    "highlights": ["Trang An Sampan Ride", "Mua Cave Viewpoint"],
                    "notes": ["Sense of Pace: Active"],
                    "display_date": "03 Oct 2026"
                },
                {
                    "day_number": 4,
                    "destination": "Halong Bay",
                    "summary": "Transfer to Halong Bay. Board 5-star luxury cruise through Lan Ha Bay. Sunset tea and gourmet dinner.",
                    "overnight": "Halong Bay",
                    "meals": ["Breakfast", "Lunch", "Dinner"],
                    "highlights": ["5-Star Luxury Cruise", "Kayaking", "Sunset Sundowner"],
                    "notes": ["Sense of Pace: Relaxed"],
                    "display_date": "04 Oct 2026"
                },
                {
                    "day_number": 5,
                    "destination": "Sapa",
                    "summary": "Morning Tai Chi on sundeck, disembark and private transfer to Sapa highlands.",
                    "overnight": "Sapa",
                    "meals": ["Brunch", "Dinner"],
                    "highlights": ["Tai Chi at Sunrise", "Scenic Transfer to Sapa"],
                    "notes": ["Sense of Pace: Scenic"],
                    "display_date": "05 Oct 2026"
                },
                {
                    "day_number": 6,
                    "destination": "Sapa",
                    "summary": "Fansipan Peak cable car experience and trek through Muong Hoa valley ethnic Hmong villages.",
                    "overnight": "Sapa",
                    "meals": ["Breakfast", "Lunch"],
                    "highlights": ["Fansipan Cable Car", "Valley Trekking"],
                    "notes": ["Sense of Pace: Active"],
                    "display_date": "06 Oct 2026"
                },
                {
                    "day_number": 7,
                    "destination": "Hanoi",
                    "summary": "Relaxed morning in Sapa resort, afternoon luxury drive back to Hanoi for farewell dinner.",
                    "overnight": "Hanoi",
                    "meals": ["Breakfast", "Farewell Dinner"],
                    "highlights": ["Resort Spa Morning", "Farewell Dinner"],
                    "notes": ["Sense of Pace: Relaxed"],
                    "display_date": "07 Oct 2026"
                },
                {
                    "day_number": 8,
                    "destination": "Hanoi",
                    "summary": "Leisure morning, private airport transfer for international departure flight.",
                    "overnight": "Hanoi",
                    "meals": ["Breakfast"],
                    "highlights": ["Private Airport Transfer"],
                    "notes": ["Sense of Pace: Departure"],
                    "display_date": "08 Oct 2026"
                }
            ]
        },
        "pricing_facts": {
            "conditions": ["Rates are indicative subject to seasonal hotel availability."],
            "options": [
                {
                    "id": "signature-luxury-tier",
                    "label": "5★ Luxury Hotels & Cruise",
                    "currency": "USD",
                    "per_traveler_amount_minor": 350_000,
                    "group_total_amount_minor": 700_000,
                }
            ]
        },
        "customer_facts": {
            "customer_name": "Alexander & Sarah",
            "adults": 2,
            "children": 0,
            "nationality": "United Kingdom",
            "guest_profile": "Private Couple",
            "market": "UK / Europe",
            "party_label": "Alexander & Sarah",
            "greeting_name": "Alexander & Sarah"
        },
        "service_facts": {
            "hotels": [
                {
                    "destination": "Hanoi",
                    "name": "Capella Hanoi",
                    "room_type": "Capella Suite",
                    "check_in": "2026-10-01",
                    "check_out": "2026-10-03",
                    "intro": "An opera-inspired luxury sanctuary in the heart of Hanoi.",
                    "phone": "+84 24 3987 8888",
                    "display_city": "HANOI, VIETNAM",
                    "display_date": "01 Oct – 03 Oct 2026"
                },
                {
                    "destination": "Halong Bay",
                    "name": "Capella Cruise Halong",
                    "room_type": "Executive Suite",
                    "check_in": "2026-10-04",
                    "check_out": "2026-10-05",
                    "intro": "Ultra-luxury overnight cruise in Lan Ha Bay.",
                    "phone": "+84 90 123 4567",
                    "display_city": "HALONG BAY, VIETNAM",
                    "display_date": "04 Oct – 05 Oct 2026"
                },
                {
                    "destination": "Sapa",
                    "name": "Hotel de la Coupole - MGallery Sapa",
                    "room_type": "Executive Suite",
                    "check_in": "2026-10-05",
                    "check_out": "2026-10-07",
                    "intro": "French haute couture meets Indochina heritage in Sapa.",
                    "phone": "+84 214 362 9999",
                    "display_city": "SAPA, VIETNAM",
                    "display_date": "05 Oct – 07 Oct 2026"
                }
            ],
            "inclusions": [
                "Private VIP Airport Transfers in Mercedes S-Class",
                "5-Star Luxury Accommodations with Breakfast",
                "Dedicated English-speaking Private Tour Guide",
                "All Entrance Fees, Cable Car Tickets & Sampan Excursions",
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
            "description": "Standard Capella Travel luxury booking policy.",
            "items": [
                {"key": "deposit", "label": "Deposit", "body": "30% deposit required upon confirmation."},
                {"key": "balance", "label": "Balance", "body": "70% balance due 30 days before arrival."},
                {"key": "cancellation", "label": "Cancellation", "body": "Full refund up to 45 days prior to arrival."}
            ]
        },
        "finalization_facts": {
            "required_title": "Before we confirm",
            "required_items": ["Passport details for every traveller"],
            "after_confirmation_title": "After confirmation",
            "after_confirmation_items": ["Final travel documents and vouchers"],
        },
        "seller_facts": {
            "seller_name": "Capella Travel",
            "seller_email": "concierge@capellatravel.com",
            "seller_phone": "+84 911 538 738",
            "designer_name": "Elena Vance",
            "designer_title": "Senior Luxury Travel Architect",
            "designer_quote": "Designing timeless memories through authentic, private Indochina travel experiences."
        }
    }

async def mock_generate(self, request, brand_profile):
    return _fallback_narrative_result(request, brand_profile), 'fallback', []

async def mock_extract_destinations(text, max_items=None):
    return [
        {'name': 'Hanoi', 'slug': 'ha-noi'},
        {'name': 'Ninh Binh', 'slug': 'ninh-binh'},
        {'name': 'Ha Long', 'slug': 'quang-ninh'},
        {'name': 'Sapa', 'slug': 'lao-cai'}
    ]

def main_run():
    payload = create_sample_quote_request()
    print("Submitting CreateQuoteRequestV1 to /api/v2/quotations...")

    with patch.object(NarrativeGenerator, 'generate', mock_generate), \
         patch.object(image_selector, 'extract_and_map_destinations', mock_extract_destinations), \
         patch.object(main, '_get_db_session_factory', lambda: mock_db_session):
        client = TestClient(main.app)
        response = client.post('/api/v2/quotations', json=payload)
        
        print("HTTP Status Code:", response.status_code)
        if response.status_code == 200:
            res = response.json()
            print("\n=======================================================")
            print(" 🎉 QUOTATION V2 TEST CREATED SUCCESSFULLY!")
            print("=======================================================")
            print(f"Quotation ID:     {res.get('quotationId')}")
            print(f"Status:           {res.get('status')}")
            print(f"Baseline Lang:    {res.get('baselineLang')}")
            print(f"Current Revision: {res.get('currentRevision')}")
            print(f"Current Version:  {res.get('currentVersion')}")
            print(f"Quotation URL:    {res.get('quotationUrl')}")
            print(f"PDF URL:          {res.get('pdfUrl')}")
            print("\n--- Document Meta ---")
            print(json.dumps(res.get('document', {}).get('meta', {}), indent=2))
            print("\n--- Route Stay Segments ---")
            for seg in res.get('document', {}).get('route', {}).get('staySegments', []):
                print(f"  • {seg.get('displayName')} ({seg.get('daysLabel')}, {seg.get('nightsLabel')}) -> Hotel: {seg.get('hotelName')}")
            print("\n--- Sections Included ---")
            for sec in res.get('document', {}).get('layout', {}).get('sections', []):
                print(f"  • [{sec.get('id')}] {sec.get('type')} (Enabled: {sec.get('enabled')})")
        else:
            print("Error details:", response.text)

if __name__ == "__main__":
    main_run()
