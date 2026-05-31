#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Test: POST /itineraries — Vietnam Luxury Family Booked Itinerary
# Usage: bash test_create_itinerary.sh
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL="${1:-http://localhost:9013}"

curl -X POST "$BASE_URL/itineraries" \
  -H "Content-Type: application/json" \
  -s \
  -w "\n\n--- HTTP STATUS: %{http_code} ---\n" \
  -d '{
  "quotationNumber": "ITI-2026-0099",
  "quotationTitle": "CONFIRMED BOOKING ITINERARY",
  "tourTitle": "VIETNAM SLOW NATURE, MOUNTAIN & BEACH FAMILY JOURNEY",
  "duration": {
    "days": 12,
    "nights": 11,
    "label": "12D11N"
  },
  "preparedFor": "Mr. Nam & Family",
  "nationality": "Vietnam",
  "travelDates": {
    "startDate": "2026-09-26",
    "endDate": "2026-10-07",
    "displayText": "26 September 2026 – 07 October 2026"
  },
  "guests": {
    "adults": 4,
    "children": 4,
    "totalGuests": 8,
    "childrenAges": [4, 8, 10, 11],
    "displayText": "4 Adults + 4 Children"
  },
  "route": ["Hanoi", "Ninh Binh", "Sapa", "Ha Long Bay", "Da Nang", "Hoi An"],
  "travelStyle": ["Private", "Luxury Resort Stay", "Slow Travel paced"],
  "programOverview": {
    "heading": "TRIP CONFIRMATION",
    "paragraphs": [
      "Your private luxury family journey in Vietnam has been fully booked and secured. This document lists your confirmed accommodations, daily guides, private transfers, domestic flights, and planned tours.",
      "The program features exceptional handpicked hotels such as the Sofitel Legend Metropole in Hanoi, MGallery in Sapa, and the InterContinental in Da Nang, combined with a luxury overnight cruise in Ha Long Bay and relaxed private sightseeing."
    ]
  },
  "hotels": [
    {
      "name": "Sofitel Legend Metropole Hanoi",
      "star": 5,
      "addressArea": "French Quarter, Hanoi",
      "roomType": "Premium Room (Connecting Rooms)",
      "checkInDate": "2026-09-26",
      "checkOutDate": "2026-09-29",
      "nights": 3,
      "destination": "Hanoi",
      "status": "Confirmed",
      "notes": "Premium breakfast included. Requesting extra baby cot.",
      "pricePerNightUsd": 350
    },
    {
      "name": "Hotel de la Coupole - MGallery Sapa",
      "star": 5,
      "addressArea": "Sapa Center, Lao Cai",
      "roomType": "Deluxe Family Suite",
      "checkInDate": "2026-09-29",
      "checkOutDate": "2026-10-02",
      "nights": 3,
      "destination": "Sapa",
      "status": "Confirmed",
      "notes": "Heated pool access. High floors preferred.",
      "pricePerNightUsd": 210
    },
    {
      "name": "InterContinental Danang Sun Peninsula Resort",
      "star": 5,
      "addressArea": "Son Tra Peninsula, Da Nang",
      "roomType": "Classic Oceanview Suite",
      "checkInDate": "2026-10-03",
      "checkOutDate": "2026-10-07",
      "nights": 4,
      "destination": "Da Nang",
      "status": "Confirmed",
      "notes": "Includes Club Lounge benefits.",
      "pricePerNightUsd": 550
    }
  ],
  "activities": [
    {
      "activityName": "Trang An Scenic Water Rowing boat ride",
      "operator": "Trang An Ecotourism Center",
      "date": "2026-09-28",
      "area": "Ninh Binh",
      "durationHours": 3.5,
      "privateGroup": true,
      "status": "Confirmed",
      "notes": "Private boat for the family. Inclusions: Life vests, entry tickets.",
      "pricePerAdultUsd": 25,
      "pricePerChildUsd": 18.75,
      "totalEstimateUsd": 87.5
    },
    {
      "activityName": "Fansipan Cable Car & Peak Visit",
      "operator": "Sun World Fansipan Legend",
      "date": "2026-09-30",
      "area": "Sapa",
      "durationHours": 4,
      "privateGroup": true,
      "status": "Confirmed",
      "notes": "Includes VIP cable car cabin & Funicular train tickets.",
      "pricePerAdultUsd": 50,
      "pricePerChildUsd": 35,
      "totalEstimateUsd": 170.0
    }
  ],
  "transfers": [
    {
      "transferType": "airport_pickup",
      "fromLocation": "Noi Bai Int Airport (HAN)",
      "toLocation": "Sofitel Legend Metropole Hanoi",
      "date": "2026-09-26",
      "vehicleRequirement": "16-Seat Ford Transit VIP D-Car",
      "seats": 12,
      "status": "Confirmed",
      "notes": "Driver holding board under \"Mr. Nam Family\"",
      "priceUsd": 45
    },
    {
      "transferType": "intercity",
      "fromLocation": "Sofitel Metropole Hanoi",
      "toLocation": "Hotel de la Coupole Sapa",
      "date": "2026-09-29",
      "vehicleRequirement": "16-Seat Ford Transit VIP D-Car",
      "seats": 12,
      "status": "Confirmed",
      "notes": "Scenic highway drive with comfortable restroom stops.",
      "priceUsd": 140
    }
  ],
  "flights": [
    {
      "flightNumber": "VN-171",
      "airline": "Vietnam Airlines",
      "date": "2026-10-03",
      "fromCity": "Hanoi (HAN)",
      "toCity": "Da Nang (DAD)",
      "departureTime": "10:30",
      "arrivalTime": "11:55",
      "status": "Confirmed",
      "notes": "Domestic economy flight tickets sent in PDF format.",
      "priceUsd": 95
    }
  ],
  "guides": [
    {
      "guideName": "Anh Tuan",
      "language": "English",
      "destination": "Hanoi & Ninh Binh",
      "dates": ["2026-09-26", "2026-09-27", "2026-09-28"],
      "days": 3,
      "status": "Confirmed",
      "notes": "Specialist in Northern Vietnam history.",
      "pricePerDayUsd": 65,
      "totalEstimateUsd": 195
    }
  ],
  "itinerary": [
    {
      "dayNumber": 1,
      "date": "2026-09-26",
      "title": "Arrival in Hanoi | Private Welcome & Check-In",
      "description": [
        "Welcome to Hanoi! Upon arrival at Noi Bai Airport, our private driver and English-speaking guide will meet you outside the arrivals hall.",
        "Transfer in comfort to your luxurious French colonial hotel in the heart of Hanoi. Enjoy the remainder of the day relaxing at the hotel."
      ],
      "overnight": "Hanoi",
      "meals": ["No meals"],
      "destinations": ["Hanoi"],
      "activities": ["Private airport pickup"]
    },
    {
      "dayNumber": 2,
      "date": "2026-09-27",
      "title": "Hanoi Private Cultural Discovery | French & Old Quarters",
      "description": [
        "Spend the morning exploring Hanoi’s rich history. Wander through the atmospheric Old Quarter streets, visit the Temple of Literature, and enjoy egg coffee overlooking Hoan Kiem Lake.",
        "Your private guide is flexible and will pace the day to suit your family’s energy levels."
      ],
      "overnight": "Hanoi",
      "meals": ["Breakfast", "Lunch"],
      "destinations": ["Hanoi"],
      "activities": ["Old Quarter walking tour"]
    },
    {
      "dayNumber": 3,
      "date": "2026-09-28",
      "title": "Ninh Binh Day Tour | Trang An Waterway Boat Ride",
      "description": [
        "Depart for Ninh Binh province by private vehicle. Arrive at Trang An Ecotourism complex and board your private rowboat.",
        "Glide along calm waters winding between vertical limestone cliffs and through majestic caves. Return to Hanoi in the late afternoon."
      ],
      "overnight": "Hanoi",
      "meals": ["Breakfast", "Lunch"],
      "destinations": ["Ninh Binh", "Trang An"],
      "activities": ["Trang An Boat Excursion"]
    },
    {
      "dayNumber": 4,
      "date": "2026-09-29",
      "title": "Hanoi to Sapa Highlands | Scenic Mountain Drive",
      "description": [
        "Check out of Sofitel Metropole and begin your private highway transfer to the Sapa mountain range.",
        "Watch the cityscape dissolve into terraced valleys and misty peak ranges. Arrive in Sapa in the afternoon, check in to your MGallery resort, and enjoy the cool mountain air."
      ],
      "overnight": "Sapa",
      "meals": ["Breakfast"],
      "destinations": ["Sapa"],
      "activities": ["Private highway transfer"]
    },
    {
      "dayNumber": 5,
      "date": "2026-09-30",
      "title": "Fansipan Mountain | VIP Cable Car Peak Excursion",
      "description": [
        "Ascend Fansipan Peak—the roof of Indochina. Take the scenic VIP cable car cabin soaring above clouds and lush terraced fields.",
        "At the summit, admire breathtaking panoramic views of the Hoang Lien Son range. Spend the afternoon at leisure in Sapa town."
      ],
      "overnight": "Sapa",
      "meals": ["Breakfast", "Lunch"],
      "destinations": ["Sapa", "Fansipan"],
      "activities": ["Fansipan Peak visit"]
    }
  ],
  "inclusions": [
    "Confirmed accommodations at 5-star Sofitel, MGallery, and InterContinental",
    "Private air-conditioned 16-seat Ford Transit VIP transport throughout",
    "Private English-speaking local guide on sightseeing days",
    "Daily breakfast and lunches mentioned in the daily schedule",
    "All entrance fees, cable car tickets, and boat ride fees",
    "Vietnam Airlines domestic flight Hanoi to Da Nang",
    "Local 24/7 hotline support"
  ],
  "exclusions": [
    "International flights to/from Vietnam",
    "Visa and visa processing fees",
    "Travel insurance",
    "Personal expenses, laundry, and drinks",
    "Tips for local guide and driver"
  ],
  "notes": [
    "Special request: Connecting rooms at Sofitel Legend Metropole Hanoi and club privileges at InterContinental Danang are guaranteed.",
    "Baby cot is confirmed for Hanoi hotel."
  ],
  "pricing": {
    "currency": "USD",
    "pricingTitle": "CONFIRMED ITINERARY COST & PRICING",
    "basis": "Twin/Double Sharing basis",
    "priceOptions": [
      {
        "hotelCategory": "5★ Luxury Resort Stay",
        "pricePerPerson": {
          "amount": 2850.0,
          "currency": "USD",
          "displayText": "$2,850 per adult"
        },
        "totalPrice": {
          "amount": 11400.0,
          "currency": "USD",
          "displayText": "$11,400 total"
        },
        "optionName": "Main confirmed option",
        "isConfirmedMainOption": true
      }
    ]
  }
}'

