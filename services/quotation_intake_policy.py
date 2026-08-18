from __future__ import annotations

from core.rules import parse_iso_date
from quote_document import CreateQuoteRequestV1


def quotation_intake_missing_inputs(payload: CreateQuoteRequestV1) -> list[str]:
    """Return canonical fact paths required before a manual V2 quote is created."""
    missing: list[str] = []
    trip = payload.trip_facts
    customer = payload.customer_facts

    if not payload.brand_id:
        missing.append("brand_id")
    if not payload.presentation_options.template_id:
        missing.append("presentation_options.template_id")
    if not payload.lang:
        missing.append("lang")
    if not payload.presentation_options.travel_designer_id:
        missing.append("presentation_options.travel_designer_id")
    start_date, end_date = parse_iso_date(trip.start_date), parse_iso_date(trip.end_date)
    if start_date is None:
        missing.append("trip_facts.start_date")
    if end_date is None:
        missing.append("trip_facts.end_date")
    if start_date is not None and end_date is not None and end_date < start_date:
        missing.append("trip_facts.end_date")

    if start_date is not None and end_date is not None and end_date >= start_date:
        expected_day_count = (end_date - start_date).days + 1
        if len(trip.itinerary) != expected_day_count:
            missing.append("trip_facts.itinerary")
    elif not trip.itinerary:
        missing.append("trip_facts.itinerary")

    for index, day in enumerate(trip.itinerary):
        if day.day_number != index + 1:
            missing.append(f"trip_facts.itinerary[{index}].day_number")
        if not (day.destination or "").strip():
            missing.append(f"trip_facts.itinerary[{index}].destination")
        if not (day.summary or "").strip():
            missing.append(f"trip_facts.itinerary[{index}].summary")
        if not (day.overnight or "").strip():
            missing.append(f"trip_facts.itinerary[{index}].overnight")

    if not payload.service_facts.hotels:
        missing.append("service_facts.hotels")
    for index, hotel in enumerate(payload.service_facts.hotels):
        if not (hotel.accommodation_id or "").strip():
            missing.append(f"service_facts.hotels[{index}].accommodation_id")
        if not (hotel.destination or "").strip():
            missing.append(f"service_facts.hotels[{index}].destination")
        if not (hotel.name or "").strip():
            missing.append(f"service_facts.hotels[{index}].name")
        if not (hotel.room_type or "").strip():
            missing.append(f"service_facts.hotels[{index}].room_type")
        check_in, check_out = parse_iso_date(hotel.check_in), parse_iso_date(hotel.check_out)
        if check_in is None:
            missing.append(f"service_facts.hotels[{index}].check_in")
        if check_out is None or (check_in is not None and check_out < check_in):
            missing.append(f"service_facts.hotels[{index}].check_out")

    if not (customer.customer_name or "").strip():
        missing.append("customer_facts.customer_name")
    if not (customer.nationality or "").strip():
        missing.append("customer_facts.nationality")
    if customer.adults is None or customer.adults < 1:
        missing.append("customer_facts.adults")
    if customer.children is not None and customer.children < 0:
        missing.append("customer_facts.children")
    return missing
