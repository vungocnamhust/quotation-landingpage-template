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
  "quotationType": "tour",
  "status": "confirmed",
  "publishStatus": "published",
  "source": "custom-gpt",
  "language": "en",
  "quotationTitle": "LUXURY QUOTATION",
  "tourTitle": "VIETNAM SLOW NATURE, MOUNTAIN & BEACH FAMILY JOURNEY \u2013 12D11N",
  "duration": {
    "days": 12,
    "nights": 11,
    "label": "12D11N"
  },
  "preparedFor": "Qatar Family Guests",
  "nationality": "Qatar",
  "travelDates": {
    "startDate": "2026-09-26",
    "endDate": "2026-10-07",
    "displayText": "26 September 2026 \u2013 07 October 2026"
  },
  "guests": {
    "adults": 4,
    "children": 4,
    "infants": 0,
    "totalGuests": 8,
    "childrenAges": [4, 8, 10, 11],
    "displayText": "4 Adults + 4 Children"
  },
  "travelStyle": [
    "Private",
    "Halal-Friendly",
    "Luxury Family Journey",
    "Slow Nature, Mountain & Beach Escape"
  ],
  "route": ["Hanoi", "Ninh Binh", "Sapa", "Ha Long Bay", "Da Nang", "Hoi An"],
  "hotelOptions": ["4\u2605 Premium", "5\u2605 Luxury"],
  "confirmedMainOption": "5\u2605 Luxury",
  "alternativeOptionRetained": "4\u2605 Premium",
  "programOverview": {
    "heading": "PROGRAM OVERVIEW",
    "paragraphs": [
      "A refined Vietnam family journey created for Qatari travelers seeking a slower, more elegant way to experience the country'\''s natural beauty. This program avoids rushed sightseeing and focuses instead on comfort, scenery, fresh mountain air, gentle cultural encounters, peaceful cruising, and beachside relaxation.",
      "The journey begins in Hanoi, where the family eases into Vietnam with soft cultural discovery and private arrangements. It then continues to Ninh Binh, a cinematic landscape of limestone mountains, rivers, rice fields, and quiet countryside. From there, the program moves into the northern highlands of Sapa, where cool air, terraced valleys, and mountain viewpoints create a peaceful nature retreat.",
      "The experience continues with an overnight cruise in Ha Long Bay, one of Vietnam'\''s most iconic natural wonders, before the family flies south to Da Nang for coastal comfort, resort relaxation, Ba Na Hills, the Golden Bridge, and the lantern-lit charm of Hoi An.",
      "This itinerary is especially suitable for a family with children, with private transfers, flexible timing, easy sightseeing days, and enough leisure time to enjoy the hotels, beach, and scenery."
    ]
  },
  "itinerary": [
    {
      "dayNumber": 1,
      "date": "2026-09-26",
      "title": "Arrival in Hanoi | Private Welcome & Gentle First Evening",
      "description": [
        "Upon arrival at Noi Bai International Airport, the family will be warmly welcomed by the local Vietnam Safar team and escorted by private vehicle to the hotel in Hanoi.",
        "Depending on arrival time, the family may enjoy a gentle walk near the hotel, a quiet cafe moment, or simply relax and recover. No sightseeing is scheduled on this day."
      ],
      "overnight": "Hanoi",
      "meals": ["No meals"],
      "destinations": ["Hanoi"],
      "activities": ["Private airport welcome", "Private hotel transfer", "Leisure time"]
    },
    {
      "dayNumber": 2,
      "date": "2026-09-27",
      "title": "Hanoi Elegant Cultural Discovery | Old Quarter, Lake Views & Train Street Experience",
      "description": [
        "After breakfast, begin a relaxed introduction to Hanoi, Vietnam'\''s graceful capital. Visit the peaceful area around Hoan Kiem Lake, pass through French colonial streets, and explore the Old Quarter.",
        "A highlight of the day is the Train Street coffee experience, subject to local regulations.",
        "The afternoon remains flexible, with time for rest, shopping, or returning early to the hotel."
      ],
      "overnight": "Hanoi",
      "meals": ["Breakfast", "Lunch"],
      "destinations": ["Hanoi"],
      "activities": ["Hoan Kiem Lake", "French colonial streets", "Old Quarter", "Train Street coffee experience"]
    },
    {
      "dayNumber": 3,
      "date": "2026-09-28",
      "title": "Ninh Binh Luxury Nature Escape | Limestone Valleys & Trang An Scenic Boat Ride",
      "description": [
        "Today is dedicated to one of Northern Vietnam'\''s most beautiful natural regions: Ninh Binh. After breakfast, travel by private vehicle through the countryside.",
        "Visit Hoa Lu Ancient Capital, then enjoy the highlight of the day: a peaceful Trang An boat journey through calm waterways surrounded by towering limestone cliffs.",
        "Return to Hanoi in the late afternoon."
      ],
      "overnight": "Hanoi",
      "meals": ["Breakfast", "Lunch"],
      "destinations": ["Ninh Binh", "Hoa Lu", "Trang An"],
      "activities": ["Private countryside transfer", "Hoa Lu Ancient Capital", "Trang An scenic boat ride", "Nature and photo stops"]
    },
    {
      "dayNumber": 4,
      "date": "2026-09-29",
      "title": "Hanoi to Sapa Highlands | Scenic Private Mountain Journey",
      "description": [
        "After breakfast, depart Hanoi for Sapa by private vehicle through the northern mountain landscapes.",
        "Upon arrival, check in and enjoy the day at leisure with mountain views and cool air."
      ],
      "overnight": "Sapa",
      "meals": ["Breakfast"],
      "destinations": ["Sapa"],
      "activities": ["Private transfer from Hanoi to Sapa", "Mountain scenery", "Hotel leisure time"]
    },
    {
      "dayNumber": 5,
      "date": "2026-09-30",
      "title": "Sapa Valley Serenity | Terraced Rice Fields, Village Views & Gentle Nature Walk",
      "description": [
        "A signature nature day in Sapa. Travel into the Muong Hoa Valley area and enjoy a light walking route around Lao Chai and Ta Van village areas.",
        "The afternoon can be kept easy, allowing the family to return to the hotel for rest and mountain views."
      ],
      "overnight": "Sapa",
      "meals": ["Breakfast", "Lunch"],
      "destinations": ["Sapa", "Muong Hoa Valley", "Lao Chai", "Ta Van"],
      "activities": ["Muong Hoa Valley visit", "Terraced rice field views", "Gentle village walk", "Photo stops"]
    },
    {
      "dayNumber": 6,
      "date": "2026-10-01",
      "title": "Fansipan Cable Car Experience | Mountain Panorama & Return to Hanoi",
      "description": [
        "After breakfast, enjoy the famous Fansipan cable car experience, weather permitting, offering sweeping views over the Sapa highlands.",
        "After the visit, return to Sapa town and begin the private transfer back to Hanoi."
      ],
      "overnight": "Hanoi",
      "meals": ["Breakfast"],
      "destinations": ["Fansipan", "Sapa", "Hanoi"],
      "activities": ["Fansipan cable car experience", "Mountain panorama", "Private transfer back to Hanoi"],
      "notes": ["Fansipan cable car experience is subject to weather conditions."]
    },
    {
      "dayNumber": 7,
      "date": "2026-10-02",
      "title": "Ha Long Bay Luxury Overnight Cruise | Limestone Islands, Calm Waters & Sunset Moments",
      "description": [
        "Depart Hanoi for Ha Long Bay by private transfer. Board the overnight cruise and sail through emerald waters surrounded by dramatic limestone islands.",
        "As the sun begins to set, the bay becomes especially peaceful, creating a memorable family moment. Dinner is served onboard."
      ],
      "overnight": "Ha Long Bay Cruise",
      "meals": ["Breakfast", "Lunch", "Dinner"],
      "destinations": ["Ha Long Bay"],
      "activities": ["Private transfer to Ha Long Bay", "Overnight cruise", "Limestone island scenery", "Sunset onboard"],
      "optionalActivities": ["Cave visit", "Kayaking", "Bamboo boat experience"]
    },
    {
      "dayNumber": 8,
      "date": "2026-10-03",
      "title": "Peaceful Morning on Ha Long Bay | Fly to Da Nang for Coastal Relaxation",
      "description": [
        "Wake up to a calm morning on Ha Long Bay. Enjoy brunch onboard while the cruise slowly returns to the pier.",
        "After disembarkation, transfer to Hanoi for the domestic flight to Da Nang. The evening is free for rest."
      ],
      "overnight": "Da Nang",
      "meals": ["Brunch"],
      "destinations": ["Ha Long Bay", "Hanoi", "Da Nang"],
      "activities": ["Morning cruise", "Brunch onboard", "Transfer for domestic flight", "Private transfer to Da Nang hotel"]
    },
    {
      "dayNumber": 9,
      "date": "2026-10-04",
      "title": "Da Nang Beach Leisure | Family Relaxation Day",
      "description": [
        "This day is reserved fully for relaxation. The family can enjoy a slower beach resort rhythm.",
        "Guests may enjoy the pool, beach, spa, or simply spend quality family time at the resort."
      ],
      "overnight": "Da Nang",
      "meals": ["Breakfast"],
      "destinations": ["Da Nang"],
      "activities": ["Beach leisure", "Resort relaxation", "Free family time"],
      "optionalActivities": ["Private activities on request"]
    },
    {
      "dayNumber": 10,
      "date": "2026-10-05",
      "title": "Ba Na Hills & Golden Bridge | Mountain Air, Cable Car Views & Iconic Scenery",
      "description": [
        "After breakfast, travel privately to Ba Na Hills. The experience begins with a scenic cable car ride above forests and hills.",
        "Visit the Golden Bridge, one of Vietnam'\''s most recognized landmarks, and enjoy time for family photos."
      ],
      "overnight": "Da Nang",
      "meals": ["Breakfast", "Lunch"],
      "destinations": ["Da Nang", "Ba Na Hills", "Golden Bridge"],
      "activities": ["Private transfer to Ba Na Hills", "Cable car ride", "Golden Bridge visit", "Family photo time"]
    },
    {
      "dayNumber": 11,
      "date": "2026-10-06",
      "title": "Coconut Forest & Hoi An Ancient Town | Lanterns, River Charm & Soft Evening Atmosphere",
      "description": [
        "Begin the day with a visit to Cam Thanh Coconut Forest. The family will enjoy a traditional basket boat experience through water coconut palms.",
        "Later, continue to Hoi An Ancient Town. Walk through lantern-lit streets and enjoy a gentle river boat experience."
      ],
      "overnight": "Da Nang",
      "meals": ["Breakfast", "Dinner"],
      "destinations": ["Cam Thanh Coconut Forest", "Hoi An", "Da Nang"],
      "activities": ["Basket boat experience", "Hoi An Ancient Town walk", "Lantern-lit streets", "River boat experience"]
    },
    {
      "dayNumber": 12,
      "date": "2026-10-07",
      "title": "Departure from Da Nang | Private Airport Transfer",
      "description": [
        "Enjoy breakfast and free time until the scheduled private transfer to Da Nang International Airport.",
        "The journey ends with a smooth departure, leaving the family with a balanced experience of Vietnam'\''s culture, mountains, nature, cruising, and beach."
      ],
      "overnight": null,
      "meals": ["Breakfast"],
      "destinations": ["Da Nang"],
      "activities": ["Free time before departure", "Private airport transfer"]
    }
  ],
  "pricing": {
    "currency": "SAR",
    "pricingTitle": "PRICE QUOTATION \u2013 B2B NET INDICATIVE",
    "basis": "B2B net indicative",
    "totalGuests": 8,
    "priceOptions": [
      {
        "hotelCategory": "4\u2605 Premium",
        "optionName": "4-star premium option",
        "pricePerPerson": {
          "amount": 4850,
          "currency": "SAR",
          "displayText": "SAR 4,850 / person",
          "isFromPrice": true
        },
        "totalPrice": {
          "amount": 38800,
          "currency": "SAR",
          "displayText": "SAR 38,800",
          "isFromPrice": true
        },
        "isConfirmedMainOption": false,
        "isAlternativeOption": true
      },
      {
        "hotelCategory": "5\u2605 Luxury",
        "optionName": "Main luxury option",
        "pricePerPerson": {
          "amount": 5650,
          "currency": "SAR",
          "displayText": "SAR 5,650 / person",
          "isFromPrice": true
        },
        "totalPrice": {
          "amount": 45200,
          "currency": "SAR",
          "displayText": "SAR 45,200",
          "isFromPrice": true
        },
        "isConfirmedMainOption": true,
        "isAlternativeOption": false
      }
    ],
    "grandTotal": 45200
  },
  "inclusions": [
    "Private airport pick-up and drop-off",
    "Private A/C transportation throughout the itinerary",
    "Accommodation with daily breakfast",
    "Meals as mentioned in the program",
    "English-speaking local guide on sightseeing days",
    "Entrance fees for mentioned sightseeing",
    "Hanoi cultural discovery and Train Street experience",
    "Ninh Binh full-day nature excursion with Trang An boat ride",
    "Sapa mountain experience with light village walk",
    "Fansipan cable car experience, weather permitting",
    "1-night Ha Long Bay overnight cruise",
    "Da Nang beach leisure stay",
    "Ba Na Hills and Golden Bridge excursion",
    "Coconut Forest basket boat experience",
    "Hoi An Ancient Town and lantern river experience",
    "Halal-friendly meal arrangements, seafood / vegetarian options where suitable"
  ],
  "exclusions": [
    "International flights",
    "Vietnam visa and visa processing fees",
    "Travel insurance",
    "Personal expenses",
    "Tips for guide and driver",
    "Optional activities not mentioned",
    "Early check-in / late check-out",
    "Domestic flight Hanoi to Da Nang, subject to final routing",
    "Peak season, gala dinner, or compulsory hotel surcharges if applied"
  ],
  "priceConditions": {
    "heading": "PRICE CONDITIONS",
    "paragraphs": [
      "Rates are B2B net indicative and subject to reconfirmation at the time of booking.",
      "Final price may vary depending on hotel availability, resort category, cruise selection, domestic flight fare, rooming arrangement, child policy, and final travel services confirmed.",
      "Child rates may be adjusted after confirming the room setup, bed sharing, extra bed requirements, and hotel/cruise child policies."
    ]
  },
  "notes": [
    "Luxury private halal-friendly Vietnam family journey for 8 guests from Qatar, 12D11N.",
    "Confirmed main option: 5-star Luxury. Alternative option retained: 4-star Premium."
  ],
  "internalNotes": [
    "Full raw quotation is stored in rawQuotation field."
  ],
  "rawQuotation": "LUXURY QUOTATION\n\nVIETNAM SLOW NATURE, MOUNTAIN & BEACH FAMILY JOURNEY - 12D11N\n\nPrepared for: Qatar Family Guests\nNationality: Qatar\nTravel Dates: 26 September 2026 - 07 October 2026\nGuests: 4 Adults + 4 Children (ages 4, 8, 10, 11)\nTravel Style: Private | Halal-Friendly | Luxury Family Journey\nRoute: Hanoi - Ninh Binh - Sapa - Ha Long Bay - Da Nang - Hoi An\nHotel Options: 4-star Premium & 5-star Luxury\nDuration: 12 Days / 11 Nights\n\nPRICE QUOTATION - B2B NET INDICATIVE\n4-star Premium: SAR 4,850/person | Total: SAR 38,800\n5-star Luxury (CONFIRMED): SAR 5,650/person | Total: SAR 45,200\n\nRates are B2B net indicative and subject to reconfirmation at time of booking."
}'
