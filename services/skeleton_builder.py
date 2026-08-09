"""Build a valid canonical document using facts and deterministic values only."""
from __future__ import annotations

from typing import Any

from quote_document import CreateQuoteRequestV1, QuoteDocumentV1, build_rich_content_from_fact_sources


class SkeletonBuilder:
    @staticmethod
    def _hotel_date_range(check_in: str | None, check_out: str | None) -> str:
        return " – ".join(value for value in (check_in, check_out) if value)

    @staticmethod
    def _build_stay_segments(days: list[dict[str, Any]], hotels: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Derive the route map from immutable Facts, never from generated copy."""
        grouped: list[list[dict[str, Any]]] = []
        for day in days:
            city = day.get("overnight") or day.get("segmentCity") or ""
            if grouped and (grouped[-1][-1].get("overnight") or grouped[-1][-1].get("segmentCity") or "") == city:
                grouped[-1].append(day)
            else:
                grouped.append([day])

        segments: list[dict[str, Any]] = []
        hotel_cursor = 0
        for index, group in enumerate(grouped, 1):
            first, last = group[0], group[-1]
            city = last.get("overnight") or last.get("segmentCity") or ""
            hotel = next((item for item in hotels[hotel_cursor:] if item.get("city") == city), None)
            if hotel is not None:
                hotel_cursor = hotels.index(hotel) + 1
            start, end = first["dayNumber"], last["dayNumber"]
            day_label = f"Day {start}" if start == end else f"Days {start}–{end}"
            nights = max(1, end - start + 1)
            segments.append({
                "id": f"stay-{index}",
                "displayName": city,
                "daysLabel": day_label,
                "nightsLabel": f"{nights} Night" if nights == 1 else f"{nights} Nights",
                "hotelName": (hotel or {}).get("name") or "",
                "hotelDateRange": (hotel or {}).get("hotelDate") or "",
                "hotelImage": (hotel or {}).get("hotelImage") or {},
                "mapSegmentDesc": "",
                "mapSegmentDuration": "",
                "coords": [],
            })
        return segments

    def build(self, *, quotation_id: str, payload: CreateQuoteRequestV1, resolved_facts: dict[str, Any], template: str) -> dict[str, Any]:
        trip, customer, pricing, services, designer = payload.trip_facts, payload.customer_facts, payload.pricing_facts, payload.service_facts, payload.designer_facts
        days = []
        for index, day in enumerate(trip.itinerary, 1):
            number = day.day_number or index
            days.append({"id": f"day-{number}", "dayNumber": number, "dayDate": day.display_date or "", "segmentCity": day.destination or "", "title": "", "description": [], "overnight": day.overnight or "", "meals": day.meals, "activities": [], "notes": day.notes, "labelHighlights": "", "labelNotes": ""})
        hotels = []
        for index, hotel in enumerate(services.hotels, 1):
            hotels.append({"id": f"hotel-{index}", "city": hotel.display_city or hotel.destination or "", "name": hotel.name or "", "introduction": hotel.intro or "", "hotelDate": hotel.display_date or self._hotel_date_range(hotel.check_in, hotel.check_out), "tel": hotel.phone or "", "roomType": hotel.room_type or "", "hotelImage": {"r2Key": hotel.hotel_asset or ""}, "roomImage": {"r2Key": hotel.room_asset or ""}})
        stay_segments = self._build_stay_segments(days, hotels)
        document = {
            "meta": {"quotationId": quotation_id, "opportunityId": payload.opportunity_id or "", "lang": payload.lang or "en", "brandId": payload.brand_id or "", "template": "quote-generator", "revision": 1, "status": "draft", "contentSchemaVersion": 1},
            "presentation": {"renderer": "quote-generator", "themeId": payload.presentation_options.theme_id, "layoutVersion": payload.presentation_options.layout_version},
            "traveler": {"customerName": customer.customer_name or "", "guestProfile": customer.guest_profile or "", "nationality": customer.nationality or "", "adults": customer.adults or 0, "children": customer.children or 0},
            "trip": {"title": "", "lede": "", "durationText": resolved_facts["duration"]["label"], "routeText": resolved_facts["routeLabel"], "travelDates": resolved_facts["travelDateLabel"], "quotationNumber": quotation_id, "priceBasis": ""},
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
                        "groupTotalAmountMinor": item.group_total_amount_minor,
                    }
                    for i, item in enumerate(pricing.options, 1)
                ],
            },
            "designer": {"subtitle": designer.seller_subtitle or "", "signature": designer.designer_signature or "", "kicker": designer.designer_kicker or "", "quote": designer.designer_quote or "", "experience": designer.designer_experience or "", "title": designer.designer_title or "", "ctaBody": designer.cta_body or ""},
        }
        document["content"] = build_rich_content_from_fact_sources({
            "inclusions": list(services.inclusions),
            "exclusions": list(services.exclusions),
            "bookingTerms": {
                "description": payload.booking_facts.description or "",
                "items": [{"key": item.key or "", "label": item.label or "", "body": item.body or ""} for item in payload.booking_facts.items],
            },
            "finalization": {
                "requiredTitle": payload.finalization_facts.required_title or "Final Details Required",
                "afterConfirmationTitle": payload.finalization_facts.after_confirmation_title or "After Confirmation",
                "requiredItems": list(payload.finalization_facts.required_items),
                "afterConfirmation": list(payload.finalization_facts.after_confirmation_items),
            },
        })
        # Fact media is materialized by the API's contract-aware media-slot
        # boundary. Keeping this builder media-free prevents a second partial
        # mapper from silently dropping logo, divider, ornament, or designer
        # slots during quotation creation.
        return QuoteDocumentV1.model_validate(document).model_dump(mode="json")
