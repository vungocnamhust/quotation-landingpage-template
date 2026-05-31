from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()  # Load environment variables from .env file

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    prompt={
        "id": "{replace here}",
        "version": "1",
    },
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": '{\n  "quotationNumber": "TBD-20260920-10DQN",\n  "quotationType": "tour",\n  "source": "Vietnam Safar / Discovery Asia Travel Group (B2B quotation draft)",\n  "language": "en",\n  "quotationTitle": "Exclusive Vietnam Explorer – 10D9N for Qatar Families",\n  "tourTitle": "Exclusive Vietnam Explorer – 10D9N for Qatar Families",\n  "duration": {\n    "days": 10,\n    "nights": 9,\n    "label": "10D9N"\n  },\n  "preparedFor": "TBD – Qatar Family (2 Adults, 2 Children)",\n  "nationality": "Qatar",\n  "travelDates": {\n    "startDate": "2026-09-20",\n    "endDate": "2026-09-29",\n    "displayText": "20 Sep 2026 – 29 Sep 2026"\n  },\n  "guests": {\n    "adults": 2,\n    "children": 2,\n    "totalGuests": 4,\n    "childrenAges": [],\n    "displayText": "2 Adults + 2 Children"\n  },\n  "travelStyle": [\n    "Other"\n  ],\n  "route": [\n    "Hanoi",\n    "Ninh Binh",\n    "Ha Long Bay",\n    "Da Nang",\n    "Hoi An",\n    "Ho Chi Minh City",\n    "Mekong Delta"\n  ],\n  "hotelOptions": [\n    "3",\n    "4",\n    "5"\n  ],\n  "confirmedMainOption": "",\n  "alternativeOptionRetained": "",\n  "programOverview": {\n    "heading": "A serene, halal-conscious Vietnam journey for Qatar families",\n    "paragraphs": [\n      "This 10-day Vietnam itinerary is crafted for comfort and effortless discovery—from Hanoi’s timeless charm, to the limestone landscapes of Ninh Binh, and an overnight experience on Ha Long Bay. Then you’ll move into Central Vietnam’s coastal highlights with iconic viewpoints and lantern-lit Hoi An, before finishing in the dynamic South with Mekong Delta serenity and classic Ho Chi Minh City moments.",\n      "Your program uses private transfers and A/C comfort, includes sightseeing entrance fees as per plan, and offers halal-friendly meal arrangements (seafood/vegetarian options) throughout the journey. "\n    ]\n  },\n  "itinerary": [\n    {\n      "dayNumber": 1,\n      "date": "2026-09-20",\n      "title": "Arrival in Hanoi – welcome & gentle first moments",\n      "description": [\n        "Arrive at Noi Bai International Airport and enjoy a warm meet-and-greet before a private transfer to your hotel in Hanoi.",\n        "The rest of the day is kept unhurried—perfect for family settling in, a light stroll around the Old Quarter area, and an easy transition to Vietnam’s rhythm."\n      ],\n      "overnight": "Hanoi",\n      "meals": [],\n      "destinations": [\n        "Hanoi"\n      ],\n      "activities": [\n        "Private airport pickup & transfer",\n        "Leisure time / Old Quarter orientation"\n      ]\n    },\n    {\n      "dayNumber": 2,\n      "date": "2026-09-21",\n      "title": "Hanoi cultural discovery – classic landmarks & local atmosphere",\n      "description": [\n        "Enjoy a guided cultural walk through Hanoi’s highlights around Hoan Kiem Lake and the French colonial boulevards, with time for relaxed photo stops.",\n        "Experience a memorable Train Street-style coffee stop (subject to local regulations and operational conditions), then return to your hotel for family downtime."\n      ],\n      "overnight": "Hanoi",\n      "meals": [\n        "Breakfast",\n        "Lunch (halal-friendly)"\n      ],\n      "destinations": [\n        "Hanoi"\n      ],\n      "activities": [\n        "Hanoi cultural discovery",\n        "Train Street coffee experience (subject to local regulations)"\n      ]\n    },\n    {\n      "dayNumber": 3,\n      "date": "2026-09-22",\n      "title": "Ninh Binh – ‘Ha Long Bay on Land’ limestone scenery",\n      "description": [\n        "Travel to Ninh Binh for a full-day landscape escape.",\n        "Explore Hoa Lu’s heritage sites, climb viewpoints at Mua Cave for panoramic views, and unwind on a scenic Trang An boat ride through limestone valleys and calm waterways."\n      ],\n      "overnight": "Hanoi",\n      "meals": [\n        "Breakfast",\n        "Lunch (halal-friendly)"\n      ],\n      "destinations": [\n        "Ninh Binh",\n        "Hanoi"\n      ],\n      "activities": [\n        "Hoa Lu visit",\n        "Mua Cave viewpoint experience",\n        "Trang An boat ride"\n      ]\n    },\n    {\n      "dayNumber": 4,\n      "date": "2026-09-23",\n      "title": "Ha Long Bay – overnight cruise among emerald karsts",\n      "description": [\n        "Head toward Ha Long Bay for an unforgettable UNESCO-style overnight experience.",\n        "After embarking, enjoy time aboard as the bay’s limestone scenery opens up around you—then settle in for the evening with a family-friendly pace."\n      ],\n      "overnight": "Ha Long Bay (Cruise)",\n      "meals": [\n        "Breakfast",\n        "Lunch (on cruise)",\n        "Dinner (halal-friendly as arranged)"\n      ],\n      "destinations": [\n        "Ha Long Bay"\n      ],\n      "activities": [\n        "Ha Long Bay transfer",\n        "Cruise embarkation",\n        "Relaxed evening onboard"\n      ]\n    },\n    {\n      "dayNumber": 5,\n      "date": "2026-09-24",\n      "title": "Ha Long Bay morning – then fly to Da Nang",\n      "description": [\n        "Wake to the bay’s morning stillness and enjoy a relaxed cruise experience with fresh air and scenic views.",\n        "After brunch onboard, disembark and transfer to the airport for your journey onward to Central Vietnam—Da Nang."\n      ],\n      "overnight": "Da Nang",\n      "meals": [\n        "Breakfast",\n        "Brunch (on cruise)"\n      ],\n      "destinations": [\n        "Ha Long Bay",\n        "Da Nang"\n      ],\n      "activities": [\n        "Morning on Ha Long Bay",\n        "Transfer to Da Nang"\n      ]\n    },\n    {\n      "dayNumber": 6,\n      "date": "2026-09-25",\n      "title": "Ba Na Hills & Golden Bridge – panoramic wonder",\n      "description": [\n        "Travel to Ba Na Hills and ascend by cable car for cool mountain air and sweeping views.",\n        "Visit the iconic Golden Bridge, then enjoy a comfortable, family-friendly exploration of the hilltop complex at a relaxed pace."\n      ],\n      "overnight": "Da Nang",\n      "meals": [\n        "Breakfast",\n        "Lunch (halal-friendly)"\n      ],\n      "destinations": [\n        "Da Nang",\n        "Ba Na Hills"\n      ],\n      "activities": [\n        "Golden Bridge excursion",\n        "Ba Na Hills cable car experience"\n      ]\n    },\n    {\n      "dayNumber": 7,\n      "date": "2026-09-26",\n      "title": "Marble Mountains & Coconut Forest – lantern-lit Hoi An evening",\n      "description": [\n        "Start with Marble Mountains, known for limestone caves, viewpoints, and serene spiritual spaces.",\n        "Continue to Cam Thanh Coconut Forest for a basket-boat experience through shaded coconut waterways.",\n        "In the late afternoon, arrive in Hoi An for a gentle walking tour through lantern-lit lanes—followed by a calm river lantern moment before returning for rest."\n      ],\n      "overnight": "Da Nang",\n      "meals": [\n        "Breakfast",\n        "Dinner (halal-friendly as arranged)"\n      ],\n      "destinations": [\n        "Marble Mountains",\n        "Cam Thanh Coconut Forest",\n        "Hoi An",\n        "Da Nang"\n      ],\n      "activities": [\n        "Marble Mountains visit",\n        "Coconut Forest basket boat ride",\n        "Hoi An Ancient Town lantern experience"\n      ]\n    },\n    {\n      "dayNumber": 8,\n      "date": "2026-09-27",\n      "title": "Hoi An at ease – culture, craft & coastal calm",\n      "description": [\n        "A slower day designed for families—choose a paced cultural route through Hoi An at your preferred comfort level.",\n        "Enjoy additional time for photos, local craft browsing, and relaxing breaks before your smooth transition toward the South."\n      ],\n      "overnight": "Ho Chi Minh City",\n      "meals": [\n        "Breakfast",\n        "Lunch (halal-friendly)"\n      ],\n      "destinations": [\n        "Hoi An",\n        "Ho Chi Minh City"\n      ],\n      "activities": [\n        "Flexible Hoi An exploration",\n        "Transfer to Ho Chi Minh City"\n      ]\n    },\n    {\n      "dayNumber": 9,\n      "date": "2026-09-28",\n      "title": "Mekong Delta – waterways, gardens & rural serenity",\n      "description": [\n        "Spend a full day in the Mekong Delta, discovering village life and scenic canals.",\n        "Enjoy a boat-focused experience (motorboat cruising and a calm rowing-boat moment where applicable), with a garden-style lunch arranged for halal-friendly dining."\n      ],\n      "overnight": "Ho Chi Minh City",\n      "meals": [\n        "Breakfast",\n        "Lunch (halal-friendly)"\n      ],\n      "destinations": [\n        "Mekong Delta",\n        "Ho Chi Minh City"\n      ],\n      "activities": [\n        "Mekong Delta excursion",\n        "Boat experience (motorboat + rowing, as arranged)"\n      ]\n    },\n    {\n      "dayNumber": 10,\n      "date": "2026-09-29",\n      "title": "Ho Chi Minh City – last impressions & departure",\n      "description": [\n        "Enjoy breakfast and final family moments in Ho Chi Minh City (program time-flexible based on your flight).",\n        "Then transfer to the airport for your onward flight, concluding your Vietnam discovery journey."\n      ],\n      "overnight": "",\n      "meals": [\n        "Breakfast"\n      ],\n      "destinations": [\n        "Ho Chi Minh City"\n      ],\n      "activities": [\n        "Airport transfer & departure"\n      ]\n    }\n  ],\n  "inclusions": [\n    "Private airport pick-up & drop-off (as per itinerary)",\n    "Private A/C transportation throughout the itinerary",\n    "Accommodation with daily breakfast",\n    "Meals as mentioned in the program (halal-friendly options arranged, e.g., seafood/vegetarian)",\n    "All sightseeing entrance fees as specified in the program",\n    "English-speaking local guide",\n    "Ha Long Bay overnight cruise experience (1 night) included in the program style",\n    "Ninh Binh full-day tour (Hoa Lu + Mua Cave viewpoint + Trang An boat ride) in the program style",\n    "Ba Na Hills & Golden Bridge excursion in the program style",\n    "Marble Mountains, Coconut Forest basket-boat experience & Hoi An Ancient Town lantern atmosphere in the program style",\n    "Mekong Delta full-day excursion with boat experiences in the program style"\n  ],\n  "exclusions": [\n    "International flights",\n    "Vietnam visa & visa processing fees",\n    "Travel insurance",\n    "Personal expenses (laundry, beverages, shopping, tips)",\n    "Optional activities not mentioned in the program",\n    "Domestic flights (if required for intercity transfers), quoted separately based on availability"\n  ],\n  "notes": [\n    "Halal-friendly meal arrangements are provided with seafood/vegetarian options; exact menu confirmation is subject to supplier availability at booking time. ",\n    "Entrance fees are included according to the confirmed sightseeing list in the program. ",\n    "Assumptions Used: (1) This 10D/9N route uses Hanoi → Ninh Binh → Ha Long (1-night) → Da Nang/Ho i An → Ho Chi Minh City → Mekong Delta; (2) Intercity transfers that may require domestic flights are excluded unless separately confirmed; (3) Meal plan follows the typical included pattern from our Vietnam halal-friendly program templates—final meal timings will be confirmed after hotel/cruise selection."\n  ]\n}',
                }
            ],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": '{\n  "wave1": {\n    "hotels": [\n      {\n        "block_id": "H1",\n        "task": "hotel_search",\n        "destination": "Hanoi",\n        "checkin": "2026-09-20",\n        "checkout": "2026-09-23",\n        "nights": 3,\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "star_options": [\n          3,\n          4,\n          5\n        ],\n        "halal_required": true,\n        "special_requirements": [\n          "family room"\n        ],\n        "search_query": "Hanoi hotel 3-5 star family September"\n      },\n      {\n        "block_id": "H2",\n        "task": "hotel_search",\n        "destination": "Ha Long Bay",\n        "checkin": "2026-09-23",\n        "checkout": "2026-09-24",\n        "nights": 1,\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "star_options": [\n          3,\n          4,\n          5\n        ],\n        "halal_required": true,\n        "special_requirements": [\n          "overnight cruise"\n        ],\n        "search_query": "Ha Long Bay cruise 3-5 star family September"\n      },\n      {\n        "block_id": "H3",\n        "task": "hotel_search",\n        "destination": "Da Nang",\n        "checkin": "2026-09-24",\n        "checkout": "2026-09-28",\n        "nights": 4,\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "star_options": [\n          3,\n          4,\n          5\n        ],\n        "halal_required": true,\n        "special_requirements": [\n          "family room"\n        ],\n        "search_query": "Da Nang hotel 3-5 star family September"\n      },\n      {\n        "block_id": "H4",\n        "task": "hotel_search",\n        "destination": "Ho Chi Minh City",\n        "checkin": "2026-09-28",\n        "checkout": "2026-09-29",\n        "nights": 1,\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "star_options": [\n          3,\n          4,\n          5\n        ],\n        "halal_required": true,\n        "special_requirements": [\n          "family room"\n        ],\n        "search_query": "Ho Chi Minh City hotel 3-5 star family September"\n      }\n    ],\n    "activities": [\n      {\n        "block_id": "A1",\n        "task": "activity_search",\n        "area": "Hanoi",\n        "date": "2026-09-21",\n        "activities": [\n          "Hanoi cultural discovery",\n          "Train Street coffee experience"\n        ],\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "halal_required": true,\n        "special_requirements": [\n          "private group"\n        ],\n        "search_query": "Hanoi cultural tour family halal price"\n      },\n      {\n        "block_id": "A2",\n        "task": "activity_search",\n        "area": "Ninh Binh",\n        "date": "2026-09-22",\n        "activities": [\n          "Hoa Lu visit",\n          "Mua Cave viewpoint experience",\n          "Trang An boat ride"\n        ],\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "halal_required": true,\n        "special_requirements": [\n          "family-friendly"\n        ],\n        "search_query": "Ninh Binh scenic tour family halal price"\n      },\n      {\n        "block_id": "A3",\n        "task": "activity_search",\n        "area": "Ha Long Bay",\n        "date": "2026-09-23",\n        "activities": [\n          "Cruise embarkation",\n          "Relaxed evening onboard"\n        ],\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "halal_required": true,\n        "special_requirements": [\n          "family pace"\n        ],\n        "search_query": "Ha Long Bay cruise family halal price"\n      },\n      {\n        "block_id": "A4",\n        "task": "activity_search",\n        "area": "Ha Long Bay",\n        "date": "2026-09-24",\n        "activities": [\n          "Morning on Ha Long Bay",\n          "Transfer to Da Nang"\n        ],\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "halal_required": true,\n        "special_requirements": [\n          "cruise disembark"\n        ],\n        "search_query": "Ha Long Bay morning cruise family halal"\n      },\n      {\n        "block_id": "A5",\n        "task": "activity_search",\n        "area": "Ba Na Hills",\n        "date": "2026-09-25",\n        "activities": [\n          "Golden Bridge excursion",\n          "Ba Na Hills cable car experience"\n        ],\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "halal_required": true,\n        "special_requirements": [\n          "family-friendly"\n        ],\n        "search_query": "Ba Na Hills tour family halal September"\n      },\n      {\n        "block_id": "A6",\n        "task": "activity_search",\n        "area": "Hoi An",\n        "date": "2026-09-26",\n        "activities": [\n          "Marble Mountains visit",\n          "Coconut Forest basket boat ride",\n          "Hoi An lantern experience"\n        ],\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "halal_required": true,\n        "special_requirements": [\n          "family-friendly",\n          "evening activity"\n        ],\n        "search_query": "Hoi An lantern tour family halal price"\n      },\n      {\n        "block_id": "A7",\n        "task": "activity_search",\n        "area": "Hoi An",\n        "date": "2026-09-27",\n        "activities": [\n          "Flexible Hoi An exploration",\n          "Transfer to Ho Chi Minh City"\n        ],\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "halal_required": true,\n        "special_requirements": [\n          "family-friendly"\n        ],\n        "search_query": "Hoi An family tour transfer halal September"\n      },\n      {\n        "block_id": "A8",\n        "task": "activity_search",\n        "area": "Mekong Delta",\n        "date": "2026-09-28",\n        "activities": [\n          "Mekong Delta excursion",\n          "Boat experience motor and rowing"\n        ],\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "halal_required": true,\n        "special_requirements": [\n          "family boat tour"\n        ],\n        "search_query": "Mekong Delta boat tour family halal price"\n      }\n    ],\n    "guides": [\n      {\n        "block_id": "G1",\n        "task": "guide_search",\n        "destination": "Vietnam",\n        "dates": [\n          "2026-09-20",\n          "2026-09-21",\n          "2026-09-22",\n          "2026-09-23",\n          "2026-09-24",\n          "2026-09-25",\n          "2026-09-26",\n          "2026-09-27",\n          "2026-09-28"\n        ],\n        "days": 9,\n        "language": "English",\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "search_query": "Vietnam family friendly guide English 9 days price"\n      }\n    ],\n    "flights": [\n      {\n        "block_id": "F1",\n        "task": "flight_search",\n        "from_city": "Ha Long Bay",\n        "from_iata": "",\n        "to_city": "Da Nang",\n        "to_iata": "DAD",\n        "date": "2026-09-24",\n        "pax": {\n          "adults": 2,\n          "children": 2\n        },\n        "search_query": "Ha Long Bay to Da Nang flight 2026-09-24 ticket price"\n      }\n    ]\n  },\n  "wave2_transfers": [\n    {\n      "block_id": "T1",\n      "task": "transfer_search",\n      "transfer_type": "airport_pickup",\n      "from": "Noi Bai Airport",\n      "to": "Hanoi",\n      "date": "2026-09-20",\n      "pax": {\n        "adults": 2,\n        "children": 2\n      },\n      "vehicle_requirement": "7-seat",\n      "search_query": "private transfer Noi Bai Airport to Hanoi 7-seat price"\n    },\n    {\n      "block_id": "T2",\n      "task": "transfer_search",\n      "transfer_type": "intercity",\n      "from": "Hanoi",\n      "to": "Ninh Binh",\n      "date": "2026-09-22",\n      "pax": {\n        "adults": 2,\n        "children": 2\n      },\n      "vehicle_requirement": "7-seat",\n      "search_query": "private transfer Hanoi to Ninh Binh 7-seat price"\n    },\n    {\n      "block_id": "T3",\n      "task": "transfer_search",\n      "transfer_type": "intercity",\n      "from": "Ninh Binh",\n      "to": "Ha Long Bay",\n      "date": "2026-09-23",\n      "pax": {\n        "adults": 2,\n        "children": 2\n      },\n      "vehicle_requirement": "7-seat",\n      "search_query": "private transfer Ninh Binh to Ha Long Bay 7-seat price"\n    },\n    {\n      "block_id": "T4",\n      "task": "transfer_search",\n      "transfer_type": "airport_pickup",\n      "from": "Ha Long Bay",\n      "to": "Cat Bi Airport",\n      "date": "2026-09-24",\n      "pax": {\n        "adults": 2,\n        "children": 2\n      },\n      "vehicle_requirement": "7-seat",\n      "search_query": "private transfer Ha Long Bay to Cat Bi Airport 7-seat price"\n    },\n    {\n      "block_id": "T5",\n      "task": "transfer_search",\n      "transfer_type": "airport_pickup",\n      "from": "Da Nang Airport",\n      "to": "Da Nang",\n      "date": "2026-09-24",\n      "pax": {\n        "adults": 2,\n        "children": 2\n      },\n      "vehicle_requirement": "7-seat",\n      "search_query": "private transfer Da Nang Airport to Da Nang 7-seat price"\n    },\n    {\n      "block_id": "T6",\n      "task": "transfer_search",\n      "transfer_type": "intercity",\n      "from": "Da Nang",\n      "to": "Hoi An",\n      "date": "2026-09-26",\n      "pax": {\n        "adults": 2,\n        "children": 2\n      },\n      "vehicle_requirement": "7-seat",\n      "search_query": "private transfer Da Nang to Hoi An 7-seat price"\n    },\n    {\n      "block_id": "T7",\n      "task": "transfer_search",\n      "transfer_type": "intercity",\n      "from": "Hoi An",\n      "to": "Da Nang Airport",\n      "date": "2026-09-27",\n      "pax": {\n        "adults": 2,\n        "children": 2\n      },\n      "vehicle_requirement": "7-seat",\n      "search_query": "private transfer Hoi An to Da Nang Airport 7-seat price"\n    },\n    {\n      "block_id": "T8",\n      "task": "transfer_search",\n      "transfer_type": "airport_pickup",\n      "from": "Tan Son Nhat Airport",\n      "to": "Ho Chi Minh City",\n      "date": "2026-09-27",\n      "pax": {\n        "adults": 2,\n        "children": 2\n      },\n      "vehicle_requirement": "7-seat",\n      "search_query": "private transfer Tan Son Nhat Airport to Ho Chi Minh City 7-seat price"\n    },\n    {\n      "block_id": "T9",\n      "task": "transfer_search",\n      "transfer_type": "intercity",\n      "from": "Ho Chi Minh City",\n      "to": "Mekong Delta",\n      "date": "2026-09-28",\n      "pax": {\n        "adults": 2,\n        "children": 2\n      },\n      "vehicle_requirement": "7-seat",\n      "search_query": "private transfer Ho Chi Minh City to Mekong Delta 7-seat price"\n    },\n    {\n      "block_id": "T10",\n      "task": "transfer_search",\n      "transfer_type": "airport_dropoff",\n      "from": "Ho Chi Minh City",\n      "to": "Tan Son Nhat Airport",\n      "date": "2026-09-29",\n      "pax": {\n        "adults": 2,\n        "children": 2\n      },\n      "vehicle_requirement": "7-seat",\n      "search_query": "private transfer Ho Chi Minh City to Tan Son Nhat 7-seat price"\n    }\n  ]\n}',
                }
            ],
        },  # type: ignore
    ],
    text={
        "format": {
            "type": "json_schema",
            "name": "quotation_payload",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "wave1": {
                        "type": "object",
                        "properties": {
                            "hotels": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "block_id": {"type": "string"},
                                        "task": {
                                            "type": "string",
                                            "enum": ["hotel_search", "cruise_search"],
                                        },
                                        "destination": {"type": "string"},
                                        "checkin": {"type": "string"},
                                        "checkout": {"type": "string"},
                                        "nights": {"type": "integer"},
                                        "pax": {
                                            "type": "object",
                                            "properties": {
                                                "adults": {"type": "integer"},
                                                "children": {"type": "integer"},
                                            },
                                            "required": ["adults", "children"],
                                            "additionalProperties": False,
                                        },
                                        "star_options": {
                                            "type": "array",
                                            "items": {"type": "integer"},
                                        },
                                        "halal_required": {"type": "boolean"},
                                        "special_requirements": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "search_query": {"type": "string"},
                                    },
                                    "required": [
                                        "block_id",
                                        "task",
                                        "destination",
                                        "checkin",
                                        "checkout",
                                        "nights",
                                        "pax",
                                        "star_options",
                                        "halal_required",
                                        "special_requirements",
                                        "search_query",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "activities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "block_id": {"type": "string"},
                                        "task": {
                                            "type": "string",
                                            "enum": ["activity_search"],
                                        },
                                        "area": {"type": "string"},
                                        "date": {"type": "string"},
                                        "activities": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "pax": {
                                            "type": "object",
                                            "properties": {
                                                "adults": {"type": "integer"},
                                                "children": {"type": "integer"},
                                            },
                                            "required": ["adults", "children"],
                                            "additionalProperties": False,
                                        },
                                        "halal_required": {"type": "boolean"},
                                        "special_requirements": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "search_query": {"type": "string"},
                                    },
                                    "required": [
                                        "block_id",
                                        "task",
                                        "area",
                                        "date",
                                        "activities",
                                        "pax",
                                        "halal_required",
                                        "special_requirements",
                                        "search_query",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "guides": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "block_id": {"type": "string"},
                                        "task": {
                                            "type": "string",
                                            "enum": ["guide_search"],
                                        },
                                        "destination": {"type": "string"},
                                        "dates": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "days": {"type": "integer"},
                                        "language": {"type": "string"},
                                        "pax": {
                                            "type": "object",
                                            "properties": {
                                                "adults": {"type": "integer"},
                                                "children": {"type": "integer"},
                                            },
                                            "required": ["adults", "children"],
                                            "additionalProperties": False,
                                        },
                                        "search_query": {"type": "string"},
                                    },
                                    "required": [
                                        "block_id",
                                        "task",
                                        "destination",
                                        "dates",
                                        "days",
                                        "language",
                                        "pax",
                                        "search_query",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                            "flights": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "block_id": {"type": "string"},
                                        "task": {
                                            "type": "string",
                                            "enum": ["flight_search"],
                                        },
                                        "from_city": {"type": "string"},
                                        "from_iata": {"type": "string"},
                                        "to_city": {"type": "string"},
                                        "to_iata": {"type": "string"},
                                        "date": {"type": "string"},
                                        "pax": {
                                            "type": "object",
                                            "properties": {
                                                "adults": {"type": "integer"},
                                                "children": {"type": "integer"},
                                            },
                                            "required": ["adults", "children"],
                                            "additionalProperties": False,
                                        },
                                        "search_query": {"type": "string"},
                                    },
                                    "required": [
                                        "block_id",
                                        "task",
                                        "from_city",
                                        "from_iata",
                                        "to_city",
                                        "to_iata",
                                        "date",
                                        "pax",
                                        "search_query",
                                    ],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["hotels", "activities", "guides", "flights"],
                        "additionalProperties": False,
                    },
                    "wave2_transfers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "block_id": {"type": "string"},
                                "task": {"type": "string", "enum": ["transfer_search"]},
                                "transfer_type": {
                                    "type": "string",
                                    "enum": [
                                        "airport_pickup",
                                        "airport_dropoff",
                                        "intercity",
                                        "day_trip_return",
                                    ],
                                },
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                                "date": {"type": "string"},
                                "pax": {
                                    "type": "object",
                                    "properties": {
                                        "adults": {"type": "integer"},
                                        "children": {"type": "integer"},
                                    },
                                    "required": ["adults", "children"],
                                    "additionalProperties": False,
                                },
                                "vehicle_requirement": {
                                    "type": "string",
                                    "enum": [
                                        "4-seat",
                                        "7-seat",
                                        "16-seat",
                                        "29-seat",
                                        "45-seat",
                                    ],
                                },
                                "search_query": {"type": "string"},
                            },
                            "required": [
                                "block_id",
                                "task",
                                "transfer_type",
                                "from",
                                "to",
                                "date",
                                "pax",
                                "vehicle_requirement",
                                "search_query",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["wave1", "wave2_transfers"],
                "additionalProperties": False,
            },
        }
    },
    reasoning={},
    max_output_tokens=18064,
    store=True,
    include=["web_search_call.action.sources"],
)
