#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Test: POST /quotations — Vietnam Luxury Family Journey 12D11N
# Usage: bash test_create_quotation.sh
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL="${1:-http://localhost:8001}"

curl -X POST "$BASE_URL/quotations" \
  -H "Content-Type: application/json" \
  -s \
  -w "\n\n--- HTTP STATUS: %{http_code} ---\n" \
  -d '{
  "quotationNumber": "QT-2026-0001",
  "quotationNarrative": "A refined Vietnam family journey created for Qatari travelers seeking a slower, more elegant way to experience the country’s natural beauty.",
  "landingpageContent": {
    "heroSection": {
      "headline": "LUXURY QUOTATION",
      "subtitle": "VIETNAM SLOW NATURE, MOUNTAIN & BEACH FAMILY JOURNEY – 12D11N"
    },
    "visualDescription": "A luxury travel landing page with mountain and beach imagery."
  },
  "journeyGlance": {
    "market": "Qatar / GCC",
    "guestProfile": "4 Adults + 4 Children",
    "hotelStandard": "5★ Luxury",
    "mealPreference": "Halal-friendly meals",
    "priceType": "Indicative",
    "tourCode": "VS-2026-TBD",
    "domesticFlights": "Excluded (Quoted separately)",
    "priceBasis": "Twin/double sharing basis",
    "partnerNote": "Indicative rates only",
    "validity": "On request"
  },
  "whyWorks": {
    "privateFlexible": "Private vehicle and guide allow the guests to travel at a comfortable pace.",
    "comfort": "Family-friendly spacing and premium vehicles.",
    "muslimFriendly": "Halal-friendly meals and no-pork notes.",
    "balancedHighlights": "A balanced mix of mountains, cruise, and beaches."
  },
  "itinerary": [
    {
      "dayNumber": 1,
      "destination": "Hanoi",
      "summary": "Arrival in Hanoi. Private welcome and transfer to hotel.",
      "mainInclusions": "Private airport pickup and luxury transfer.",
      "senseOfPace": "Relaxed",
      "dining": "No meals"
    },
    {
      "dayNumber": 2,
      "destination": "Hanoi",
      "summary": "Hanoi cultural discovery. Hoan Kiem Lake, Old Quarter, Train street experience.",
      "mainInclusions": "English speaking guide, sightseeing entries.",
      "senseOfPace": "Immersive",
      "dining": "Breakfast, Lunch (Halal-friendly)"
    }
  ],
  "hotelPlan": {
    "hotels": [
      {
        "destination": "Hanoi",
        "checkInDate": "2026-09-26",
        "checkOutDate": "2026-09-29",
        "hotelArrangement": "Sofitel Legend Metropole Hanoi (Suite)"
      }
    ],
    "roomNotes": "Premium high floor suite preferred."
  },
  "optionalEnhancements": [
    {
      "title": "Private street food tour by vintage Vespa",
      "status": "Recommended"
    }
  ],
  "bookingTerms": {
    "deposit": "30% deposit upon confirmation.",
    "balance": "Balance due 45 days prior to arrival.",
    "cancellation": "Free cancellation up to 60 days before.",
    "confirmation": "Instant confirmation on deposit receipt."
  },
  "finalization": {
    "finalDetailsRequired": "Copy of passport valid for 6 months.",
    "afterConfirmation": "24/7 dedicated local concierge support."
  },
  "pricing": {
    "totalPriceUsd": 45200.0,
    "currency": "SAR",
    "markupApplied": 0.15,
    "breakdown": {
      "hotels": 20000.0,
      "activities": 5000.0,
      "guides": 3000.0,
      "transfers": 4000.0,
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
  "candidateBlocks": [
    {
      "block_id": "H1",
      "service_type": "hotel",
      "destination": "Hanoi",
      "source_day_numbers": [1]
    }
  ]
}'
