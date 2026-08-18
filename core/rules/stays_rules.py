"""Pure domain rules for accommodation stays consolidation and boundary validation."""

from __future__ import annotations

from typing import Any
from core.rules.dates_rules import date_for_itinerary_day, parse_iso_date


def consolidate_stays_from_day_accommodations(
    itinerary_with_stays: list[dict[str, Any]],
    start_date: str | None,
) -> list[dict[str, Any]]:
    """Cluster contiguous itinerary days that share the same accommodation into discrete HotelFact objects.

    Business Rules:
    1. Only days with a valid accommodation_id (or accommodation_name) produce stays.
    2. Contiguous days sharing the same accommodation_id and room_type are merged into a single Stay.
    3. check_in is set to the start date of the first day in the stay cluster.
    4. check_out is set to the date of the day immediately following the last day in the stay cluster.
    5. Consecutive stays with different hotels are preserved as separate sequential HotelFact objects.
    """
    if not itinerary_with_stays:
        return []

    hotels: list[dict[str, Any]] = []
    current_stay: dict[str, Any] | None = None
    stay_start_day: int = 1
    stay_end_day: int = 1

    for idx, day_item in enumerate(itinerary_with_stays):
        if hasattr(day_item, "model_dump"):
            day = day_item.model_dump()
        elif isinstance(day_item, dict):
            day = day_item
        else:
            day = {}

        day_num = int(day.get("day_number") or idx + 1)
        acc_id = day.get("accommodation_id")
        acc_name = day.get("accommodation_name")
        room_type = day.get("room_type") or "Standard Room"
        destination = day.get("destination")

        if not acc_id and not acc_name:
            # Day with no hotel assigned (e.g. overnight transit, night train, or final departure day)
            if current_stay:
                current_stay["check_in"] = date_for_itinerary_day(start_date, stay_start_day)
                current_stay["check_out"] = date_for_itinerary_day(start_date, stay_end_day + 1)
                hotels.append(current_stay)
                current_stay = None
            continue

        # If matching current stay, extend stay_end_day
        if (
            current_stay is not None
            and current_stay.get("accommodation_id") == acc_id
            and current_stay.get("room_type") == room_type
        ):
            stay_end_day = day_num
            continue

        # If switching to a new hotel, close previous stay
        if current_stay:
            current_stay["check_in"] = date_for_itinerary_day(start_date, stay_start_day)
            current_stay["check_out"] = date_for_itinerary_day(start_date, stay_end_day + 1)
            hotels.append(current_stay)

        # Start new stay
        stay_start_day = day_num
        stay_end_day = day_num
        current_stay = {
            "accommodation_id": acc_id,
            "destination": destination,
            "name": acc_name or "Hotel",
            "room_type": room_type,
            "check_in": None,
            "check_out": None,
            "intro": "Breakfast included.",
            "phone": None,
            "display_city": destination,
            "display_date": None,
            "hotel_asset": None,
            "room_asset": None,
        }

    # Flush final stay if still open
    if current_stay:
        current_stay["check_in"] = date_for_itinerary_day(start_date, stay_start_day)
        current_stay["check_out"] = date_for_itinerary_day(start_date, stay_end_day + 1)
        hotels.append(current_stay)

    return hotels


def validate_hotel_boundaries(
    check_in: str | None,
    check_out: str | None,
    tour_start_date: str | None,
    tour_end_date: str | None,
) -> tuple[bool, str | None]:
    """Validate check_in and check_out against tour boundary dates.

    Returns (is_valid, error_code_or_message).
    """
    cin = parse_iso_date(check_in)
    cout = parse_iso_date(check_out)
    tstart = parse_iso_date(tour_start_date)
    tend = parse_iso_date(tour_end_date)

    if cin and tstart and cin < tstart:
        return False, f"Check-in date ({check_in}) cannot be before tour start date ({tour_start_date})."
    if cout and tend and cout > tend:
        return False, f"Check-out date ({check_out}) cannot be after tour end date ({tour_end_date})."
    if cin and cout and cout < cin:
        return False, f"Check-out date ({check_out}) must be on or after check-in date ({check_in})."

    return True, None
