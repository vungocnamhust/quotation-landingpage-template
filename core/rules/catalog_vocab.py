"""SSOT vocab for product catalog (15.2). Pure data, no I/O.

Mirrored manually in ``quote-generator/components/product/types.ts`` — keep
both files' comments pointing at each other when either changes.
"""
from __future__ import annotations

CATEGORY: frozenset[str] = frozenset(
    {
        "accommodation",
        "transportation",
        "ticket",
        "flights",
        "guide",
        "guide_expense",
        "experience",
        "meal",
        "visa",
        "others",
    }
)

UNIT: frozenset[str] = frozenset(
    {"room", "person", "vehicle", "group", "ticket", "flight_seat", "visa_case", "set"}
)

TIME_BASIS: frozenset[str] = frozenset({"night", "day", "trip"})

DEFAULT_CHARGE_UNIT_BY_CATEGORY: dict[str, tuple[str, str]] = {
    "accommodation": ("room", "night"),
    "transportation": ("vehicle", "day"),
    "ticket": ("person", "trip"),
    "flights": ("person", "trip"),
    "guide": ("group", "day"),
    "guide_expense": ("group", "day"),
    "experience": ("person", "trip"),
    "meal": ("person", "trip"),
    "visa": ("person", "trip"),
    "others": ("set", "trip"),
}

SUBCATEGORY_BY_CATEGORY: dict[str, frozenset[str]] = {
    "accommodation": frozenset(
        {
            "hotel",
            "resort",
            "boutique_hotel",
            "villa",
            "overnight_cruise",
            "overnight_train",
            "lodge",
            "homestay",
            "other_overnight_accommodation",
        }
    ),
    "transportation": frozenset(
        {
            "car_4_seat",
            "car_7_seat",
            "limousine_van_9_seat",
            "van_16_seat",
            "bus_29_seat",
            "bus_35_seat",
            "bus_45_seat",
            "train",
            "ferry_boat",
            "speedboat",
            "other_transportation",
        }
    ),
    "ticket": frozenset(
        {
            "park",
            "national_park",
            "attraction",
            "museum",
            "heritage_site",
            "cable_car",
            "boat_ticket",
            "entrance_ticket",
            "show",
            "performance",
            "other_admission",
        }
    ),
    "flights": frozenset(
        {
            "domestic_flight",
            "regional_flight",
            "international_flight",
            "charter_flight",
            "seaplane",
            "helicopter",
            "other_flights",
        }
    ),
    "guide": frozenset(
        {
            "local_guide",
            "full_trip_guide",
            "tour_escort",
            "specialist_guide",
            "language_specific_guide",
            "other_guide",
        }
    ),
    "guide_expense": frozenset(
        {
            "guide_accommodation",
            "guide_meals",
            "guide_transportation",
            "guide_flight",
            "guide_train",
            "guide_entrance_fee",
            "guide_allowance",
            "other_guide_expense",
        }
    ),
    "experience": frozenset(
        {
            "workshop",
            "jeep_tour",
            "vespa_tour",
            "cycling",
            "cooking_class",
            "food_tour",
            "art_craft_experience",
            "wellness",
            "cultural_experience",
            "private_access",
            "expert_meeting",
            "photography",
            "boat_experience",
            "adventure_activity",
            "other_experience",
        }
    ),
    "meal": frozenset(
        {
            "breakfast",
            "lunch",
            "dinner",
            "set_menu",
            "fine_dining",
            "street_food",
            "halal_meal",
            "vegetarian_meal",
            "special_event_dinner",
            "drinks_package",
            "other_fnb",
        }
    ),
    "visa": frozenset(
        {
            "standard_visa",
            "e_visa",
            "urgent_visa",
            "visa_on_arrival_support",
            "visa_processing_service",
            "special_nationality_visa",
            "other_visa",
        }
    ),
    "others": frozenset(
        {
            "airport_fast_track",
            "meet_and_assist",
            "vip_airport_service",
            "sim",
            "esim",
            "souvenir",
            "welcome_gift",
            "porterage",
            "lounge",
            "photographer",
            "security",
            "concierge",
            "other_ancillary_service",
        }
    ),
}
