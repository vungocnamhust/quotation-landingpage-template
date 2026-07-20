from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()  # Load environment variables from .env file

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    prompt={
        "id": "{replace here}",
        "version": "5",
    },
    input=[
        {
            "role": "developer",
            "content": [
                {
                    "type": "input_text",
                    "text": 'You are the Tour Quote JSON Builder for Vietnam Safar / Discovery Asia Travel Group, assisting B2B partners in creating and revising luxury and halal-friendly tour quotations or converting approved quotes into landing page packages using supplied templates and details.\n\nWhen a user asks to create a quotation, you must:\n- Strictly follow any provided tour template, uploaded PDF, brief, or direct tour details.\n- Write in a premium, professional, warmly persuasive B2B style, suitable for travel agents, DMCs, and tour operators.\n- NEVER invent or assume critical data like exact prices, flight or supplier details, legal terms, hotel names, etc., unless specifically provided or you are expressly instructed to estimate; clearly list and label all such assumptions under “Assumptions Used”.\n- For non-critical or omitted fields, sensibly assign empty or clearly derived values rather than requesting the missing data; do not delay outputs unnecessarily.\n- Ensure that all essential details (customer identity, tour title, route, duration, travel dates, guest count, currency, price options, inclusions/exclusions, itinerary, and grand total) are preserved exactly from the latest approved version when revising.\n- For revision tasks, never overwrite an approved quotation with a generic, uploaded, older, or reconstructed format—update only what is necessary.\n\nQuotation Structure: Output a JSON object with the following fields as relevant (omit if not applicable):\n\n- QuotationTitle (“Tên” field): Compose as a short, sales-ready, luxury-phrased, destination-focused commercial title containing: [Luxury/Premium/Serene/Grand/Exclusive travel phrase], [Country], [Duration, e.g. “8D7N”], and [Target customer segment]. Example: “Luxury Northern Vietnam Escape – 8D7N for Saudi Families & Couples”.\n- ClientPartnerInfo\n- TourOverview\n- DayByDayItinerary (structured by day)\n- ServiceDetails\n- HotelsAccommodation\n- PriceTable\n- Inclusions\n- Exclusions\n- TermsConditions\n- NotesRecommendations\n- CallToAction\n- AssumptionsUsed (if any)\n- MetaFields: { destination, travelDates, duration, guests, marketType, groupType, hotelCategory, roomType, mealPlan, transportation, guideService, entranceFees, activities, currency, pricePerPerson, totalPrice, paymentTerms, cancellationPolicy, importantNotes }\n\nReasoning Order:\n- Always perform reasoning FIRST (analyzing supplied user data, templates, purpose, critical vs non-critical information, and identifying when assumptions are required, followed by deriving placeholder/non-critical fields as needed and strictly matching/retaining any provided or approved data).\n- Output the full JSON with conclusions/quotations LAST.\n- All assumptions or missing data must be clearly documented under “AssumptionsUsed”.\n\nOutput Format:\n- Output a complete, self-contained JSON object matching the above specification, with empty or null values for omitted fields if the user data is incomplete.\n- Do not wrap output in code blocks.\n- For input templates (PDF, text, or JSON), extract and retain all user-provided structure, using it as the primary guide for formatting and included fields.\n\nExample:\n\nInput: \nTour brief: VIP Halal Journey, 7 days in Hanoi–Halong–Ninh Binh, private tour, 4-star, Saudi FIT, with guide, single bus, includes entrance fees, daily breakfast/lunch, no flights. No prices, hotels, or dates provided.\n\nOutput:\n{\n  "QuotationTitle": "Grand Halal Vietnam Adventure – 7D6N for Saudi FITs",\n  "ClientPartnerInfo": null,\n  "TourOverview": "A luxurious, fully halal-compliant journey covering Hanoi, Halong Bay, and Ninh Binh, tailored for discerning Saudi guests, with private services, premium meals, and exclusive sightseeing.",\n  "DayByDayItinerary": [\n    {"Day": 1, "Title": "Arrive Hanoi", "Description": "Meet and greet, transfer to hotel, orientation tour, welcome dinner."},\n    {"Day": 2, "Title": "Hanoi Exploration", "Description": "Full-day city tour including Islamic sites, museums, Old Quarter, and local halal lunch."},\n    "... (Repeat for all days, tailored to brief / template.)"\n  ],\n  "ServiceDetails": {"PrivateBus": true, "TourGuide": "English/Arabic speaking", "EntranceFees": true},\n  "HotelsAccommodation": {"Category": "4-star", "Names": null},\n  "PriceTable": null,\n  "Inclusions": ["Daily breakfast and lunch (halal)", "Entrance fees", "Guide service", "Airport transfers", "Sightseeing as per itinerary"],\n  "Exclusions": ["International flights", "Dinner unless specified", "Personal expenses", "Tips"],\n  "TermsConditions": null,\n  "NotesRecommendations": ["Final hotel names, dates, and prices pending confirmation."],\n  "CallToAction": "Contact us to secure your client’s VIP halal adventure today!",\n  "AssumptionsUsed": ["Itinerary order inferred from brief. Hotel names and prices pending."],\n  "MetaFields": {\n    "destination": "Vietnam (Hanoi, Halong, Ninh Binh)",\n    "travelDates": null,\n    "duration": "7D6N",\n    "guests": null,\n    "marketType": "Saudi",\n    "groupType": "FIT",\n    "hotelCategory": "4-star",\n    "roomType": null,\n    "mealPlan": "Breakfast and lunch (halal)",\n    "transportation": "Private bus",\n    "guideService": "English/Arabic",\n    "entranceFees": true,\n    "activities": ["City tours", "Halong Bay cruise", "Cultural visits"],\n    "currency": null,\n    "pricePerPerson": null,\n    "totalPrice": null,\n    "paymentTerms": null,\n    "cancellationPolicy": null,\n    "importantNotes": ["Final quote subject to hotel and supplier confirmation."]\n  }\n}\n\n(For real quotations, JSON will be much longer/more detailed, especially for day-by-day itineraries, inclusions, and price table.)\n\nImportant: Always reason through user inputs and templates before producing or revising quotation JSON outputs. Never generate conclusions or output before internal reasoning is complete. All JSON fields should result from evidence-based reasoning or clearly articulated assumptions.\n\n—\nReminder: \n- Strictly follow the provided template, structure, and data for quotation and landing page outputs. \n- Never output generic/assumed details for critical info unless labeled as “Assumptions Used.”\n- Output MUST be a complete well-structured JSON as described, with reasoning preceding the quotation content.',
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "New quotation:\nadult: 4\nchildren: 4\nexplore viet nam\ninterests: slow, nature exploration\ndurations: 10D9N",
                }
            ],
        },
    ],
    text={
        "format": {
            "type": "json_schema",
            "name": "tour_quotation_payload",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "quotationNumber": {
                        "type": "string",
                        "description": "Unique identifier generated as a string based on this formula: 'QT-{YYYYMMDD}-{DESTINATION_CODE}-{DURATION}-{MARKET}'. Example: 'QT-20260920-VNSEEK-10D9N-QTR'. Ensure it is short, unique, and strictly follows this pattern.",
                    },
                    "quotationType": {
                        "type": "string",
                        "enum": ["tour", "other"],
                        "description": "Category of service.",
                    },
                    "source": {"type": "string", "description": "Originating source."},
                    "language": {
                        "type": "string",
                        "description": "Content language code.",
                    },
                    "quotationTitle": {
                        "type": "string",
                        "description": "Sales-ready, luxury-phrased title. Must include: [Luxury/Premium/Serene/Grand/Exclusive], [Country], [Duration e.g. 8D7N], and [Customer Segment].",
                    },
                    "tourTitle": {
                        "type": "string",
                        "description": "Sales-ready, luxury-phrased title. Must include: [Luxury/Premium/Serene/Grand/Exclusive], [Country], [Duration e.g. 8D7N], and [Customer Segment].",
                    },
                    "duration": {"$ref": "#/$defs/Duration"},
                    "preparedFor": {"type": "string", "description": "Client name."},
                    "nationality": {
                        "type": "string",
                        "description": "Client nationality.",
                    },
                    "travelDates": {"$ref": "#/$defs/TravelDates"},
                    "guests": {"$ref": "#/$defs/GuestComposition"},
                    "travelStyle": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["FIT", "GIT", "Other"]},
                        "description": "Travel style tags.",
                    },
                    "route": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Route sequence.",
                    },
                    "hotelOptions": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["3", "4", "5"]},
                        "description": "Hotel star categories.",
                    },
                    "confirmedMainOption": {
                        "type": "string",
                        "description": "Selected hotel option.",
                    },
                    "alternativeOptionRetained": {
                        "type": "string",
                        "description": "Alternative hotel option.",
                    },
                    "programOverview": {"$ref": "#/$defs/TextSection"},
                    "itinerary": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/ItineraryDay"},
                        "description": "Detailed day-by-day plan. Descriptions must be written in an engaging, professional, and evocative travel-writing style.",
                    },
                    "inclusions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Included items.",
                    },
                    "exclusions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Excluded items.",
                    },
                    "notes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "General notes.",
                    },
                },
                "required": [
                    "quotationNumber",
                    "quotationType",
                    "source",
                    "language",
                    "quotationTitle",
                    "tourTitle",
                    "duration",
                    "preparedFor",
                    "nationality",
                    "travelDates",
                    "guests",
                    "travelStyle",
                    "route",
                    "hotelOptions",
                    "confirmedMainOption",
                    "alternativeOptionRetained",
                    "programOverview",
                    "itinerary",
                    "inclusions",
                    "exclusions",
                    "notes",
                ],
                "additionalProperties": False,
                "$defs": {
                    "Duration": {
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer"},
                            "nights": {"type": "integer"},
                            "label": {"type": "string"},
                        },
                        "required": ["days", "nights", "label"],
                        "additionalProperties": False,
                    },
                    "TravelDates": {
                        "type": "object",
                        "properties": {
                            "startDate": {"type": "string", "format": "date"},
                            "endDate": {"type": "string", "format": "date"},
                            "displayText": {"type": "string"},
                        },
                        "required": ["startDate", "endDate", "displayText"],
                        "additionalProperties": False,
                    },
                    "GuestComposition": {
                        "type": "object",
                        "properties": {
                            "adults": {"type": "integer"},
                            "children": {"type": "integer"},
                            "totalGuests": {"type": "integer"},
                            "childrenAges": {
                                "type": "array",
                                "items": {"type": "integer"},
                            },
                            "displayText": {"type": "string"},
                        },
                        "required": [
                            "adults",
                            "children",
                            "totalGuests",
                            "childrenAges",
                            "displayText",
                        ],
                        "additionalProperties": False,
                    },
                    "TextSection": {
                        "type": "object",
                        "properties": {
                            "heading": {"type": "string"},
                            "paragraphs": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["heading", "paragraphs"],
                        "additionalProperties": False,
                    },
                    "ItineraryDay": {
                        "type": "object",
                        "properties": {
                            "dayNumber": {"type": "integer"},
                            "date": {"type": "string", "format": "date"},
                            "title": {"type": "string"},
                            "description": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "overnight": {"type": "string"},
                            "meals": {"type": "array", "items": {"type": "string"}},
                            "destinations": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "activities": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "dayNumber",
                            "date",
                            "title",
                            "description",
                            "overnight",
                            "meals",
                            "destinations",
                            "activities",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
        },
        "verbosity": "medium",
    },
    reasoning={"summary": "auto"},
    tools=[
        {
            "type": "file_search",
            "vector_store_ids": ["vs_6a0fb96192e48191bfb38f95d684138f"],
        },
        {
            "type": "web_search",
            "user_location": {"type": "approximate", "country": "VN"},
            "search_context_size": "medium",
        },
    ],
    store=True,
    include=["reasoning.encrypted_content", "web_search_call.action.sources"],
)
