import json
import re
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient


class _FakeAgent:
    def __init__(self, *args, **kwargs):
        pass


fake_pydantic_ai = types.ModuleType("pydantic_ai")
fake_pydantic_ai.Agent = _FakeAgent
sys.modules.setdefault("pydantic_ai", fake_pydantic_ai)

fake_llm_client = types.ModuleType("llm_client")
fake_llm_client.get_model = lambda: None
sys.modules.setdefault("llm_client", fake_llm_client)

from main import app


client = TestClient(app)

base_payload = {
    "quotationNumber": "QT-2026-SYNC-0001",
    "quotationNarrative": "A synchronized quotation regression scenario for testing publish and PDF consistency.",
    "programOverview": {
        "heading": "PROGRAM OVERVIEW",
        "paragraphs": [
            "A carefully curated Vietnam journey designed for regression testing.",
            "The sequence moves gently through Hanoi and nearby highlights with a premium tone.",
        ],
    },
    "landingpageContent": {
        "heroSection": {
            "headline": "LUXURY QUOTATION",
            "subtitle": "SYNC CONSISTENCY JOURNEY - 2D1N",
        },
        "visualDescription": "A refined luxury landing page for consistency testing.",
    },
    "journeyGlance": {
        "market": "Qatar / GCC",
        "guestProfile": "2 Adults",
        "hotelStandard": "5★ Luxury",
        "mealPreference": "Halal-friendly meals",
        "priceType": "Indicative",
        "tourCode": "VS-SYNC-2026",
        "domesticFlights": "Excluded",
        "priceBasis": "Twin/double sharing basis",
        "partnerNote": "Regression test only",
        "validity": "On request",
    },
    "whyWorks": {
        "privateFlexible": "Private pacing for a controlled sync regression.",
        "comfort": "Comfort-led operations with predictable structure.",
        "muslimFriendly": "Halal-friendly planning is clearly stated.",
        "balancedHighlights": "Balanced text blocks help verify publish drift.",
    },
    "itinerary": [
        {
            "dayNumber": 1,
            "destination": "Hanoi",
            "summary": "Arrival in Hanoi with private welcome.",
            "mainInclusions": "Private airport transfer.",
            "senseOfPace": "Relaxed",
            "dining": "No meals",
        },
        {
            "dayNumber": 2,
            "destination": "Hanoi",
            "summary": "A gentle cultural day in Hanoi.",
            "mainInclusions": "Guide and sightseeing entries.",
            "senseOfPace": "Immersive",
            "dining": "Breakfast",
        },
    ],
    "hotelPlan": {
        "hotels": [
            {
                "destination": "Hanoi",
                "checkInDate": "2026-09-26",
                "checkOutDate": "2026-09-27",
                "hotelArrangement": "Sofitel Legend Metropole Hanoi (Suite)",
            }
        ],
        "roomNotes": "Premium high floor suite preferred.",
    },
    "optionalEnhancements": [
        {
            "title": "Vintage Vespa evening ride",
            "status": "Recommended",
        }
    ],
    "bookingTerms": {
        "deposit": "30% deposit upon confirmation.",
        "balance": "Balance due 45 days prior to arrival.",
        "cancellation": "Free cancellation up to 60 days before.",
        "confirmation": "Instant confirmation on deposit receipt.",
    },
    "finalization": {
        "finalDetailsRequired": "Passport copy required.",
        "afterConfirmation": "24/7 concierge support.",
    },
    "pricing": {
        "totalPriceUsd": 5200.0,
        "currency": "USD",
        "markupApplied": 0.15,
        "breakdown": {
            "hotels": 2500.0,
            "activities": 500.0,
            "guides": 300.0,
            "transfers": 400.0,
            "flights": 0.0,
        },
    },
    "retrievalStatus": {
        "hotel": "pending",
        "activity": "pending",
        "guide": "pending",
        "transfer": "pending",
        "flight": "pending",
    },
    "candidateBlocks": [
        {
            "block_id": "H1",
            "service_type": "hotel",
            "destination": "Hanoi",
            "source_day_numbers": [1, 2],
        }
    ],
}


def replace_editable_value(html: str, field: str, new_value: str) -> str:
    pattern = rf'(<[^>]+data-editable="{re.escape(field)}"[^>]*>)(.*?)(</[^>]+>)'
    updated_html, count = re.subn(pattern, rf"\1{new_value}\3", html, count=1, flags=re.DOTALL)
    if count != 1:
        raise AssertionError(f"Editable field '{field}' not found")
    return updated_html


print("Creating quotation for sync regression...")
create_res = client.post("/quotations", json=base_payload)
assert create_res.status_code == 200, create_res.text
quotation_id = create_res.json()["quotationId"]

html_res = client.get(f"/quotations/{quotation_id}")
assert html_res.status_code == 200, html_res.text
original_html = html_res.text

updated_title = "Synced Master Title After Publish"
edited_html = replace_editable_value(original_html, "tour_title", updated_title)

print("Publishing edited quotation...")
publish_res = client.post(f"/quotations/{quotation_id}/publish", json={"html": edited_html})
assert publish_res.status_code == 200, publish_res.text
publish_data = publish_res.json()
assert publish_data["version"] == 2, publish_data

quo_dir = Path("published") / quotation_id
ctx_data = json.loads((quo_dir / "ctx.json").read_text(encoding="utf-8"))
assert ctx_data["html_sync"]["en"]["edited_fields"]["tour_title"] == updated_title

pdf_html = (quo_dir / "pdf.html").read_text(encoding="utf-8")
pdf_en_html = (quo_dir / "pdf_en.html").read_text(encoding="utf-8")
assert updated_title in pdf_html
assert updated_title in pdf_en_html

pdf_res = client.get(f"/quotations/{quotation_id}/pdf")
assert pdf_res.status_code == 200, pdf_res.text
assert updated_title in pdf_res.text

print("Corrupting latest published HTML to verify ctx.json remains the source of truth...")
(quo_dir / "v2.html").write_text(original_html, encoding="utf-8")

pdf_res_after_corruption = client.get(f"/quotations/{quotation_id}/pdf")
assert pdf_res_after_corruption.status_code == 200, pdf_res_after_corruption.text
assert updated_title in pdf_res_after_corruption.text

print("Quotation sync regression passed for", quotation_id)
