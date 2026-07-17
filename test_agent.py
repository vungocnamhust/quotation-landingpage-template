import json
import os
import sys
from fastapi.testclient import TestClient

# Add current directory to path so main can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main import app

client = TestClient(app)

# A sample structured payload matching TourQuotationPayload
STRUCTURED_PAYLOAD = {
    "quotationNarrative": "A premium slow-paced heritage journey designed for family travelers.",
    "landingpageContent": {
        "heroSection": {
            "headline": "HERITAGE & NATURAL WONDERS",
            "subtitle": "VIETNAM LUXURY IMPERIAL & COASTAL JOURNEY"
        },
        "visualDescription": "A luxury travel landing page featuring beautiful scenery of Vietnam."
    },
    "journeyGlance": {
        "market": "Global Luxury Travelers",
        "guestProfile": "2 Adults (Couple)",
        "hotelStandard": "5★ Ultra-Luxury",
        "mealPreference": "All-inclusive Breakfasts + Curated Gourmet Dinning",
        "priceType": "Indicative",
        "tourCode": "VS-8D7N-HERITAGE",
        "domesticFlights": "Included",
        "priceBasis": "Twin-sharing basis",
        "partnerNote": "Private VIP transfers.",
        "validity": "Valid for travel from September to December 2026"
    },
    "whyWorks": {
        "privateFlexible": "Your personal chauffeur is at your exclusive disposal.",
        "comfort": "Rest easy with pre-selected five-star boutique hotels.",
        "muslimFriendly": "Dietary requests are fully respected.",
        "balancedHighlights": "Perfectly balanced highlights."
    },
    "itinerary": [
        {
            "dayNumber": 1,
            "destination": "Hanoi",
            "summary": "Welcome to Hanoi. Private VIP immigration handling at airport.",
            "mainInclusions": "VIP Airport Fast-track, luxury transfer.",
            "senseOfPace": "Relaxed",
            "dining": "Dinner"
        },
        {
            "dayNumber": 2,
            "destination": "Halong Bay",
            "summary": "Board your ultra-luxury cruise ship.",
            "mainInclusions": "Luxury transfer, cruise cabin.",
            "senseOfPace": "Relaxed",
            "dining": "Breakfast, Lunch, Dinner"
        }
    ],
    "hotelPlan": {
        "hotels": [
            {
                "destination": "Hanoi",
                "checkInDate": "2026-09-20",
                "checkOutDate": "2026-09-21",
                "hotelArrangement": "Sofitel Legend Metropole Hanoi"
            }
        ],
        "roomNotes": "King size bed requested."
    },
    "optionalEnhancements": [],
    "bookingTerms": {
        "deposit": "30% deposit upon confirmation.",
        "balance": "Balance due 45 days prior.",
        "cancellation": "Free cancellation up to 60 days.",
        "confirmation": "Instant confirmation."
    },
    "finalization": {
        "finalDetailsRequired": "Passport copy.",
        "afterConfirmation": "24/7 dedicated support."
    },
    "pricing": {
        "totalPriceUsd": 5000.0,
        "currency": "USD",
        "markupApplied": 0.1,
        "breakdown": {
            "hotels": 3000.0,
            "activities": 1000.0,
            "guides": 500.0,
            "transfers": 500.0,
            "flights": 0.0
        }
    },
    "retrievalStatus": {
        "hotel": "pending",
        "activity": "pending",
        "guide": "pending",
        "transfer": "pending",
        "flight": "pending"
    },
    "candidateBlocks": []
}

def test_structured_payload_optimization():
    print("--- Test Case 1: Structured Payload Token Optimization ---")
    print("Sending structured payload directly to /api/v1/quotations/agent...")

    response = client.post(
        "/api/v1/quotations/agent",
        json={"payload": STRUCTURED_PAYLOAD, "session_id": "quo_agent_structured_opt"}
    )

    print(f"Response status code: {response.status_code}")
    assert response.status_code == 200
    res_data = response.json()
    print("Success! LLM run was bypassed successfully!")
    print(f"Quotation URL: {res_data.get('quotationUrl')}")
    print(f"PDF URL: {res_data.get('pdfUrl')}\n")

def test_agent_generation():
    print("--- Test Case 2: Natural Language Prompt (requires LLM) ---")
    prompt = (
        "Create a 5-day heritage trip to Hanoi and Halong Bay for a Singaporean couple. "
        "They want luxury 5-star hotels, halal-friendly dining options, a slow and relaxed pace, "
        "and private transfers. Target dates are October 15-20, 2026."
    )

    print(f"Sending prompt to /api/v1/quotations/agent:\n'{prompt}'\n")

    response = client.post(
        "/api/v1/quotations/agent",
        json={"prompt": prompt, "session_id": "quo_agent_test"}
    )

    print(f"Response status code: {response.status_code}")
    if response.status_code == 200:
        res_data = response.json()
        print("\nSuccess! Generated Quotation Details:")
        print(f"Quotation ID: {res_data.get('quotationId')}")
        print(f"Quotation URL: {res_data.get('quotationUrl')}")
    else:
        print("\nFailed (As expected if API keys are placeholders/quota-exceeded):")
        print(response.text[:200] + "...")

if __name__ == "__main__":
    test_structured_payload_optimization()
    test_agent_generation()
