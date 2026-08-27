"""Build a valid canonical document using facts and deterministic values only."""
from __future__ import annotations

from typing import Any

from core.brands import get_brand_boilerplate
from quote_document import CreateQuoteRequestV1, QuoteDocumentV1, build_rich_content_from_fact_sources


DESIGNER_PRESENTATION_DEFAULTS = {
    "kicker": "YOUR JOURNEY DESIGNER",
    "title": "Let Us Shape the Final Details Together",
    "quote": "I believe the desire to travel is contagious—and it is my privilege to turn that inspiration into thoughtfully designed journeys filled with meaningful experiences, authentic connections, and lasting memories",
    "signature": "TRAVEL DESIGNER",
    "experience": "Present throughout the planning, quietly working behind the journey.",
    "ctaBody": "",
}


class SkeletonBuilder:
    @staticmethod
    def _hotel_date_range(check_in: str | None, check_out: str | None) -> str:
        return " – ".join(value for value in (check_in, check_out) if value)

    @staticmethod
    def _route_stop_default(*, group: list[dict[str, Any]], city: str, hotel_name: str, lang: str) -> str:
        start, end = group[0]["dayNumber"], group[-1]["dayNumber"]
        activities = list(dict.fromkeys(
            value.strip()
            for day in group
            for value in [str(day.get("factSummary") or ""), *[str(item) for item in day.get("factHighlights") or []]]
            if value and value.strip()
        ))
        activity_copy = " ".join(activities)
        if lang == "vi":
            day_label = f"Ngày {start}" if start == end else f"Ngày {start}–{end}"
            stay_copy = f"Lưu trú tại {hotel_name}." if hotel_name else ""
        elif lang == "ar":
            day_label = f"اليوم {start}" if start == end else f"الأيام {start}–{end}"
            stay_copy = f"الإقامة في {hotel_name}." if hotel_name else ""
        else:
            day_label = f"Day {start}" if start == end else f"Days {start}–{end}"
            stay_copy = f"Stay at {hotel_name}." if hotel_name else ""
        activity_copy = activity_copy if activity_copy.endswith((".", "!", "?")) else f"{activity_copy}." if activity_copy else ""
        return " ".join(part for part in (f"{day_label} — {city}.", stay_copy, activity_copy) if part)

    @classmethod
    def _build_stay_segments(cls, days: list[dict[str, Any]], hotels: list[dict[str, Any]], *, lang: str = "en") -> list[dict[str, Any]]:
        """Derive the route map from immutable Facts, never from generated copy."""
        grouped: list[list[dict[str, Any]]] = []
        for day in days:
            point = day.get("overnightRef") or day.get("destinationRef") or {}
            destination_id = point.get("id") or day.get("overnight") or day.get("segmentCity") or ""
            previous = grouped[-1][-1] if grouped else None
            previous_point = (previous.get("overnightRef") or previous.get("destinationRef") or {}) if previous else {}
            previous_id = previous_point.get("id") or (previous.get("overnight") if previous else "") or (previous.get("segmentCity") if previous else "") or ""
            if grouped and previous_id == destination_id:
                grouped[-1].append(day)
            else:
                grouped.append([day])

        segments: list[dict[str, Any]] = []
        hotel_cursor = 0
        for index, group in enumerate(grouped, 1):
            first, last = group[0], group[-1]
            point = last.get("overnightRef") or last.get("destinationRef") or {}
            city = point.get("name") or last.get("overnight") or last.get("segmentCity") or ""
            hotel = next((item for item in hotels[hotel_cursor:] if item.get("city") == city), None)
            if hotel is not None:
                hotel_cursor = hotels.index(hotel) + 1
            start, end = first["dayNumber"], last["dayNumber"]
            day_label = f"Day {start}" if start == end else f"Days {start}–{end}"
            nights = max(1, end - start + 1)
            hotel_name = (hotel or {}).get("name") or ""
            segments.append({
                "id": f"stay-{index}",
                "hotelSourceFactId": (hotel or {}).get("sourceFactId") or (hotel or {}).get("id") or "",
                "destinationId": point.get("id") or "",
                "dayStart": start,
                "dayEnd": end,
                "displayName": city,
                "daysLabel": day_label,
                "nightsLabel": f"{nights} Night" if nights == 1 else f"{nights} Nights",
                "hotelName": hotel_name,
                "hotelDateRange": (hotel or {}).get("hotelDate") or "",
                "hotelImage": (hotel or {}).get("hotelImage") or {},
                "mapSegmentDesc": cls._route_stop_default(group=group, city=city, hotel_name=hotel_name, lang=lang),
                "coords": list(point.get("coordinates") or []),
            })
        return segments

    def build(self, *, quotation_id: str, payload: CreateQuoteRequestV1, resolved_facts: dict[str, Any], template: str) -> dict[str, Any]:
        trip, customer, pricing, services, designer = payload.trip_facts, payload.customer_facts, payload.pricing_facts, payload.service_facts, payload.designer_facts
        resolved_itinerary = resolved_facts.get("itinerary") or []
        days = []
        for index, day in enumerate(trip.itinerary, 1):
            number = day.day_number or index
            refs = resolved_itinerary[index - 1] if index - 1 < len(resolved_itinerary) else {}
            fact_id = day.id or f"day-{number}"
            days.append({"id": f"day-{number}", "sourceFactId": fact_id, "dayNumber": number, "dayDate": day.display_date or "", "segmentCity": day.destination or "", "destinationRef": refs.get("destinationRef"), "overnightRef": refs.get("overnightRef"), "factSummary": day.summary or "", "factHighlights": list(day.highlights), "title": "", "description": [], "overnight": day.overnight or "", "meals": day.meals, "activities": [], "notes": day.notes})
        resolved_hotels = resolved_facts.get("hotels") or []
        hotels = []
        for index, hotel in enumerate(services.hotels, 1):
            hotel_ref = resolved_hotels[index - 1] if index - 1 < len(resolved_hotels) else {}
            fact_id = hotel.id or f"hotel-{index}"
            hotels.append({"id": fact_id, "sourceFactId": fact_id, "city": hotel.display_city or hotel.destination or "", "name": hotel.name or "", "introduction": hotel.intro or "", "editorialIntroduction": "", "hotelDate": hotel.display_date or self._hotel_date_range(hotel.check_in, hotel.check_out), "tel": hotel.phone or "", "roomType": hotel.room_type or "", "destinationRef": hotel_ref.get("destinationRef"), "hotelImage": {"r2Key": hotel.hotel_asset or ""}, "roomImage": {"r2Key": hotel.room_asset or ""}})
        stay_segments = self._build_stay_segments(days, hotels, lang=payload.lang or "en")
        for day in days:
            day.pop("factSummary", None)
            day.pop("factHighlights", None)
        document = {
            "meta": {"quotationId": quotation_id, "opportunityId": payload.opportunity_id or "", "lang": payload.lang or "en", "brandId": payload.brand_id or "", "template": "quote-generator", "revision": 1, "status": "draft", "contentSchemaVersion": 1},
            "presentation": {"renderer": "quote-generator", "templateId": payload.presentation_options.template_id or "", "themeId": payload.presentation_options.theme_id, "layoutVersion": payload.presentation_options.layout_version},
            "traveler": {"customerName": customer.customer_name or "", "guestProfile": customer.guest_profile or "", "nationality": customer.nationality or "", "adults": customer.adults or 0, "children": customer.children or 0, "kidAges": list(customer.kid_ages), "advisorName": customer.advisor_name or "", "advisorAgency": customer.advisor_agency or ""},
            "trip": {"title": "", "lede": "", "durationText": resolved_facts["duration"]["label"], "routeText": resolved_facts["routeLabel"], "travelDates": resolved_facts["travelDateLabel"], "quotationNumber": quotation_id},
            "narrative": {"coverKicker": "", "heroMeta1": "", "heroMeta2": "", "journeyOverviewTitle": "", "letterHighlight": "", "letterGreeting": "", "letterIntro": "", "letterBody2": "", "letterOutro": "", "letterSignOff": "", "letterSender": "", "footerText": ""},
            "route": {"title": "", "description": "", "staySegments": stay_segments},
            "itinerary": {"title": "", "description": "", "days": days},
            "stays": {"hotels": hotels, "roomNotes": services.room_notes or ""},
            "pricing": {
                "conditions": [{"id": f"pricing-condition-{i}", "text": item} for i, item in enumerate(pricing.conditions, 1)],
                "options": [
                    {
                        "id": item.id or f"pricing-option-{i}",
                        "label": item.label,
                        "currency": item.currency,
                        "perTravelerAmountMinor": item.per_traveler_amount_minor,
                        "perAdultAmountMinor": item.per_adult_amount_minor,
                        "perChildAmountMinor": item.per_child_amount_minor,
                        "groupTotalAmountMinor": item.group_total_amount_minor,
                    }
                    for i, item in enumerate(pricing.options, 1)
                ],
            },
            "designer": {
                "subtitle": designer.seller_subtitle or "",
                "signature": designer.designer_signature or DESIGNER_PRESENTATION_DEFAULTS["signature"],
                "kicker": designer.designer_kicker or DESIGNER_PRESENTATION_DEFAULTS["kicker"],
                "quote": designer.designer_quote or DESIGNER_PRESENTATION_DEFAULTS["quote"],
                "experience": designer.designer_experience or DESIGNER_PRESENTATION_DEFAULTS["experience"],
                "title": designer.designer_title or DESIGNER_PRESENTATION_DEFAULTS["title"],
                "ctaBody": designer.cta_body or DESIGNER_PRESENTATION_DEFAULTS["ctaBody"],
            },
        }
        document["content"] = build_rich_content_from_fact_sources({
            "inclusions": list(services.inclusions),
            "exclusions": list(services.exclusions),
            "bookingTerms": {
                "description": payload.booking_facts.description or "",
                "items": [{"key": item.key or "", "label": item.label or "", "body": item.body or ""} for item in payload.booking_facts.items],
            },
            "boilerplate": get_brand_boilerplate(payload.brand_id),
        })
        # Fact media is materialized by the API's contract-aware media-slot
        # boundary. Keeping this builder media-free prevents a second partial
        # mapper from silently dropping logo, divider, ornament, or designer
        # slots during quotation creation.
        return QuoteDocumentV1.model_validate(document).model_dump(mode="json")
