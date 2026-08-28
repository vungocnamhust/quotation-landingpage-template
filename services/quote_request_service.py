from __future__ import annotations

import copy
import re
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.quote_request import QuoteRequest, QuoteRequestRevision
from repositories.quote_request_repository import QuoteRequestRepository
from repositories.quotation_repository import ContentActionPlanRepository, QuotationDocumentRepository, QuotationRepository
from schemas.v2.quote_request import (
    QuotationMinimalOverridesSchema,
    QuoteRequestCreateSchema,
    QuoteRequestEditPayloadSchema,
)
from services.outbox_service import OutboxService


REQUEST_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "new": frozenset({"under_review", "archived"}),
    "under_review": frozenset({"quotation_created", "archived"}),
    "quotation_created": frozenset({"archived"}),
    "archived": frozenset({"under_review"}),
}


class RequestRevisionConflictError(Exception):
    def __init__(self, current_revision: int) -> None:
        self.current_revision = current_revision
        super().__init__("Request changed in another session.")


MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9, "sept": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def parse_advisor_dates_to_iso(raw_text: str | None) -> tuple[str | None, str | None]:
    if not raw_text or not raw_text.strip():
        return None, None

    text = raw_text.strip().lower()

    # Match ISO range: "2026-11-09 to 2026-11-20" or "2026-11-09 - 2026-11-20"
    iso_range_match = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:to|-|–)\s*(\d{4}-\d{2}-\d{2})", text)
    if iso_range_match:
        return iso_range_match.group(1), iso_range_match.group(2)

    # Match format like "09–20 nov 2026" or "09 - 20 november 2026"
    day_range_match = re.search(r"(\d{1,2})\s*(?:to|-|–)\s*(\d{1,2})\s+([a-z]+)\s+(\d{4})", text)
    if day_range_match:
        start_day = int(day_range_match.group(1))
        end_day = int(day_range_match.group(2))
        month_str = day_range_match.group(3)
        year = int(day_range_match.group(4))
        month = MONTH_MAP.get(month_str)
        if month:
            try:
                start_dt = datetime(year, month, start_day)
                end_dt = datetime(year, month, end_day)
                return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return None, None


from core.rules import (
    calculate_duration,
    calculate_tri_pricing,
    consolidate_stays_from_day_accommodations,
    date_for_itinerary_day,
    generate_party_label,
    parse_iso_date,
    resolve_client_display_name,
)


def derive_children_details(children: int, kid_ages: list[int]) -> str:
    if children <= 0:
        return ""
    if not kid_ages:
        return f"{children} child" if children == 1 else f"{children} children"
    ages_str = ", ".join(str(age) for age in kid_ages)
    if children == 1:
        return f"1 child (age {ages_str})"
    return f"{children} children (ages {ages_str})"


def convert_request_to_quotation_facts(
    req: QuoteRequest,
    overrides: QuotationMinimalOverridesSchema | None = None,
) -> dict[str, Any]:
    payload = req.payload_json or {}

    # Extract base parameters with override fallbacks
    adults = overrides.adults if (overrides and overrides.adults is not None) else (req.adults or 2)
    children = overrides.children if (overrides and overrides.children is not None) else (req.children or 0)
    kid_ages = overrides.kid_ages if (overrides and overrides.kid_ages) else (req.kid_ages or [])
    start_date = (overrides.start_date if overrides and overrides.start_date else req.start_date)
    end_date = (overrides.end_date if overrides and overrides.end_date else req.end_date)
    brand_id = (overrides.brand_id if overrides and overrides.brand_id else payload.get("brand_id")) or "selvara"
    lang = (overrides.lang if overrides and overrides.lang else payload.get("lang") or "en")
    template_id = (overrides.template_id if overrides and overrides.template_id else "itinerary-imagery-v1")
    designer_profile_id = (overrides.travel_designer_id if overrides and overrides.travel_designer_id else (req.created_by_profile_id or payload.get("travel_designer_id")))

    default_meals = ["Bữa sáng"] if lang == "vi" else ["الإفطار"] if lang == "ar" else ["Breakfast"]
    children_details = req.children_details or derive_children_details(children, kid_ages)
    party_label = generate_party_label(adults, children, customer_name=None, lang=lang, kid_ages=kid_ages)

    # Itinerary and Stays derivation
    itinerary_facts: list[dict[str, Any]] = []
    hotels_facts: list[dict[str, Any]] = []
    destinations = req.destinations or []

    if overrides and overrides.itinerary_with_stays:
        extracted_dests = []
        for day in overrides.itinerary_with_stays:
            dest = day.destination
            overnight_loc = day.overnight or dest
            if dest and dest not in extracted_dests:
                extracted_dests.append(dest)
            if overnight_loc and overnight_loc not in extracted_dests:
                extracted_dests.append(overnight_loc)
            itinerary_facts.append({
                "day_number": day.day_number,
                "title": day.title or None,
                "destination": dest,
                "destination_ref": day.destination_ref if isinstance(day.destination_ref, dict) else None,
                "summary": day.summary or f"Day {day.day_number} exploration",
                "overnight": overnight_loc,
                "meals": day.meals if day.meals and len(day.meals) > 0 else default_meals,
                "highlights": day.highlights if day.highlights else [],
                "notes": day.notes if day.notes else [],
                "sense_of_pace": day.sense_of_pace or "balanced",
                "display_date": day.display_date or date_for_itinerary_day(start_date, day.day_number),
                "accommodation_id": day.accommodation_id,
                "accommodation_name": day.accommodation_name,
                "room_type": day.room_type,
            })
        if extracted_dests:
            destinations = extracted_dests
        hotels_facts = consolidate_stays_from_day_accommodations(overrides.itinerary_with_stays, start_date)
    else:
        itinerary_days_raw = payload.get("itinerary_days", [])
        for idx, day in enumerate(itinerary_days_raw, start=1):
            itinerary_facts.append({
                "day_number": day.get("day_number", idx),
                "destination": day.get("destination"),
                "destination_ref": None,
                "summary": day.get("summary") or f"Day {idx} exploration",
                "overnight": day.get("overnight"),
                "meals": day.get("meals") or default_meals,
                "highlights": day.get("highlights") or [],
                "notes": day.get("notes") or [],
                "sense_of_pace": "balanced",
                "display_date": day.get("display_date"),
            })

    # Consolidate special requirements & notes
    special_reqs: list[str] = []
    if req.special_requirements and req.special_requirements.strip():
        special_reqs.append(req.special_requirements.strip())
    if payload.get("dietary") and payload["dietary"].strip():
        special_reqs.append(f"Dietary: {payload['dietary'].strip()}")
    if payload.get("halal") and payload["halal"].strip():
        special_reqs.append(f"Halal/Prayer: {payload['halal'].strip()}")
    if payload.get("mobility") and payload["mobility"].strip():
        special_reqs.append(f"Mobility: {payload['mobility'].strip()}")
    if payload.get("health_considerations") and payload["health_considerations"].strip():
        special_reqs.append(f"Health: {payload['health_considerations'].strip()}")

    # Derive dynamic Inclusions & Exclusions from scope if provided
    inclusions: list[str] = []
    if payload.get("visa_fasttrack") == "Yes":
        inclusions.append("Airport transfer and international arrival fast-track assistance")
    else:
        inclusions.append("Airport transfer and arrival greeting")

    if payload.get("private_vehicle") == "Yes":
        veh_pref = payload.get("vehicle_preference")
        inclusions.append(f"Private vehicle transfers ({veh_pref})" if veh_pref else "All private transfers in air-conditioned vehicles")
    else:
        inclusions.append("All private transfers mentioned in the itinerary")

    guide_scope = payload.get("guide_scope")
    guide_lang = payload.get("guide_language") or "English"
    if guide_scope == "Full-trip guide":
        inclusions.append(f"Full-trip private {guide_lang}-speaking tour director/guide")
    elif guide_scope == "Local guides by destination":
        inclusions.append(f"Expert local {guide_lang}-speaking guides by destination")
    else:
        inclusions.append(f"Professional {guide_lang}-speaking guides mentioned in itinerary")

    if payload.get("domestic_flights") == "Yes":
        inclusions.append("Domestic flights as specified in the confirmed route")

    if payload.get("rail_cruise") and payload["rail_cruise"].strip():
        inclusions.append(f"Boat / Cruise / Rail: {payload['rail_cruise'].strip()}")

    meal_plan = payload.get("meal_plan")
    if meal_plan:
        inclusions.append(f"Meals included according to plan: {meal_plan}")
    else:
        inclusions.append("All meals mentioned in the itinerary (Daily breakfast included)")

    inclusions.append("Accommodations, experiences, admission fees, and exclusive arrangements")

    # Exclusions
    exclusions: list[str] = []
    if payload.get("intl_flights") != "Yes":
        exclusions.append("International flights to and from destinations")
    if payload.get("insurance") != "Yes":
        exclusions.append("Comprehensive travel insurance")
    exclusions.extend([
        "Personal expenses (beverages, laundry, telephone)",
        "Optional experiences not specified in the confirmed itinerary",
        "Tips and gratuities for guides and drivers",
        "Any services not expressly listed as included",
    ])

    # Commercial & Pricing Option Setup
    currency = (
        (overrides.pricing_options[0].currency if overrides and overrides.pricing_options and overrides.pricing_options[0].currency else None)
        or (overrides.pricing.currency if overrides and overrides.pricing and overrides.pricing.currency else None)
        or (payload.get("currency") or "USD")
    )
    per_traveler_minor = 350000
    group_total_minor = 700000
    per_adult_minor = None
    per_child_minor = None

    pricing_options: list[dict[str, Any]] = []

    if overrides and overrides.pricing_options:
        for idx, opt_ov in enumerate(overrides.pricing_options, start=1):
            opt_curr = opt_ov.currency or currency
            opt_adult = opt_ov.per_adult_amount_minor
            opt_child = opt_ov.per_child_amount_minor
            opt_total = opt_ov.group_total_amount_minor
            opt_per_traveler = opt_adult

            if opt_total is not None and opt_adult is None and adults > 0:
                opt_per_traveler = int(opt_total / adults)
                opt_adult = opt_per_traveler
            elif opt_adult is not None and opt_total is None:
                calculated_total = opt_adult * adults
                if opt_child is not None and children > 0:
                    calculated_total += opt_child * children
                opt_total = calculated_total

            pricing_options.append({
                "id": f"opt-{idx}",
                "label": opt_ov.label or f"Option {idx}",
                "currency": opt_curr,
                "per_traveler_amount_minor": opt_per_traveler or 350000,
                "group_total_amount_minor": opt_total or 700000,
                "per_adult_amount_minor": opt_adult,
                "per_child_amount_minor": opt_child,
            })
    elif overrides and overrides.pricing:
        pricing_ov = overrides.pricing
        if pricing_ov.group_total_amount_minor is not None:
            group_total_minor = pricing_ov.group_total_amount_minor
        if pricing_ov.per_adult_amount_minor is not None:
            per_adult_minor = pricing_ov.per_adult_amount_minor
            per_traveler_minor = per_adult_minor
        elif pricing_ov.group_total_amount_minor is not None and adults > 0:
            per_traveler_minor = int(pricing_ov.group_total_amount_minor / adults)
            per_adult_minor = per_traveler_minor
        if pricing_ov.per_child_amount_minor is not None:
            per_child_minor = pricing_ov.per_child_amount_minor
        pricing_options = [
            {
                "id": "opt-standard",
                "label": pricing_ov.label or "Standard Luxury Option",
                "currency": currency,
                "per_traveler_amount_minor": per_traveler_minor,
                "group_total_amount_minor": group_total_minor,
                "per_adult_amount_minor": per_adult_minor,
                "per_child_amount_minor": per_child_minor,
            }
        ]
    else:
        budget_raw = payload.get("budget")
        budget_basis = payload.get("budget_basis") or "Total trip"
        if budget_raw is not None and float(budget_raw) > 0:
            budget_val = float(budget_raw)
            if budget_basis in ["Per person", "Per person / day"]:
                per_traveler_minor = int(budget_val * 100)
                group_total_minor = int(budget_val * adults * 100)
            else:
                group_total_minor = int(budget_val * 100)
                per_traveler_minor = int((budget_val / adults) * 100) if adults > 0 else group_total_minor
        per_adult_minor = per_traveler_minor
        pricing_options = [
            {
                "id": "opt-standard",
                "label": "Standard Luxury Option",
                "currency": currency,
                "per_traveler_amount_minor": per_traveler_minor,
                "group_total_amount_minor": group_total_minor,
                "per_adult_amount_minor": per_adult_minor,
                "per_child_amount_minor": per_child_minor,
            }
        ]

    partner_id = req.partner_id or payload.get("partner_id")
    room_notes = payload.get("room_configuration") or payload.get("hotel_style") or None

    # Handle B2B client name vs advisor name separation
    client_name_val = payload.get("client_name")
    if overrides and overrides.customer_name:
        display_customer_name = overrides.customer_name.strip()
    else:
        display_customer_name = resolve_client_display_name(req.role, req.customer_name, client_name=client_name_val)

    booking_title = f"Journey for {display_customer_name}"
    booking_description = (
        f"Bespoke luxury journey for {display_customer_name}, "
        f"prepared for {req.customer_name} ({req.company_name or 'Travel Advisor'})."
        if req.role == "advisor" else
        "Custom luxury journey proposal prepared from enquiry details."
    )

    calc_days, calc_nights = calculate_duration(start_date, end_date)
    final_days = calc_days if calc_days is not None else (len(itinerary_facts) if itinerary_facts else None)
    final_nights = calc_nights if calc_nights is not None else ((len(itinerary_facts) - 1) if len(itinerary_facts) > 1 else None)

    facts: dict[str, Any] = {
        "source": {
            "kind": "manual",
            "opportunityId": req.id,
        },
        "opportunity_id": req.id,
        "brand_id": brand_id,
        "lang": lang,
        "presentation_options": {
            "template_id": template_id,
            "travel_designer_id": designer_profile_id,
            "partner_id": partner_id,
        },
        "trip_facts": {
            "destinations": destinations,
            "destination_refs": [],
            "start_date": start_date,
            "end_date": end_date,
            "duration_days": final_days,
            "duration_nights": final_nights,
            "itinerary": itinerary_facts,
            "special_requirements": special_reqs,
            "display_route_text": " & ".join(destinations) if destinations else None,
            "display_travel_dates": req.raw_dates_text if req.raw_dates_text else None,
            "routing_constraints": payload.get("routing_constraints"),
            "priorities": [
                p for p in [payload.get("priority_1"), payload.get("priority_2"), payload.get("priority_3")] if p
            ],
            "must_have": payload.get("must_have"),
            "avoid": payload.get("avoid"),
        },
        "customer_facts": {
            "customer_name": display_customer_name,
            "adults": adults,
            "children": children,
            "kid_ages": kid_ages,
            "nationality": req.market or "International",
            "guest_profile": children_details if children > 0 else "Luxury Couple / Individual",
            "travel_style": req.travel_style or "Living Heritage",
            "market": req.market,
            "party_label": party_label,
            "greeting_name": display_customer_name,
            "advisor_name": req.customer_name if req.role == "advisor" else None,
            "advisor_agency": req.company_name if req.role == "advisor" else None,
        },
        "service_facts": {
            "hotels": hotels_facts,
            "inclusions": inclusions,
            "exclusions": exclusions,
            "room_notes": room_notes,
        },
        "pricing_facts": {
            "conditions": [f"Prices based on {adults} guests sharing" if adults > 1 else "Prices based on single occupancy"],
            "options": pricing_options,
        },
        "booking_facts": {
            "title": booking_title,
            "description": booking_description,
            "items": [],
        },
        "designer_facts": {
            "seller_subtitle": "Luxury Journey Designer",
            "designer_signature": None,
            "designer_kicker": "Personalized Proposal",
            "designer_quote": "Crafting unforgettable bespoke travel experiences across Indochina.",
            "designer_experience": "Over 10 years of luxury travel design excellence.",
            "designer_title": "Senior Travel Designer",
            "cta_body": "Contact your travel designer to personalize this itinerary.",
        },
    }
    return facts


class QuoteRequestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = QuoteRequestRepository(session)

    async def create_quote_request(
        self,
        payload: QuoteRequestCreateSchema,
        *,
        created_by_profile_id: str | None = None,
    ) -> QuoteRequest:
        # Anti-bot honeypot check
        if payload.website and payload.website.strip():
            raise ValueError("Bot submission rejected.")

        # Determine start/end dates
        start_date = payload.start_date
        end_date = payload.end_date
        if payload.raw_dates_text and (not start_date or not end_date):
            parsed_start, parsed_end = parse_advisor_dates_to_iso(payload.raw_dates_text)
            if parsed_start and not start_date:
                start_date = parsed_start
            if parsed_end and not end_date:
                end_date = parsed_end

        children_details = payload.children_details or derive_children_details(payload.children, payload.kid_ages)

        payload_dict = payload.model_dump()

        designer_id = created_by_profile_id or payload.travel_designer_id or payload.created_by_profile_id

        req = await self.repo.create_request(
            role=payload.role,
            customer_name=payload.customer_name,
            email=payload.email,
            phone=payload.phone,
            company_name=payload.company_name,
            market=payload.market,
            preferred_contact=payload.preferred_contact,
            destinations=payload.destinations,
            start_date=start_date,
            end_date=end_date,
            raw_dates_text=payload.raw_dates_text,
            adults=payload.adults,
            children=payload.children,
            kid_ages=payload.kid_ages,
            children_details=children_details,
            travel_style=payload.travel_style,
            special_requirements=payload.special_requirements,
            payload_json=payload_dict,
            created_by_profile_id=designer_id,
            partner_id=payload.partner_id,
        )

        outbox = OutboxService(self.session)
        await outbox.emit_event(
            event_type="quote_request.created",
            aggregate_type="quote_request",
            aggregate_id=req.id,
            brand_id=(payload_dict.get("brand_id") or "selvara"),
            actor_email=payload.email,
            payload={
                "customer_name": payload.customer_name,
                "email": payload.email,
                "destination": ", ".join(payload.destinations) if payload.destinations else "Vietnam",
                "designer_id": designer_id,
                "title": f"Inquiry from {payload.customer_name}",
            },
        )

        return req

    async def edit_quote_request(
        self,
        request_id: str,
        payload: QuoteRequestEditPayloadSchema,
        *,
        updated_by_profile_id: str | None = None,
        change_source: str = "manual_edit",
    ) -> tuple[QuoteRequest, QuoteRequestRevision]:
        # Anti-bot honeypot check
        if payload.website and payload.website.strip():
            raise ValueError("Bot submission rejected.")

        req = await self.repo.get_by_id(request_id)
        if not req:
            raise KeyError(f"QuoteRequest {request_id} not found.")

        # Determine start/end dates
        start_date = payload.start_date
        end_date = payload.end_date
        if payload.raw_dates_text and (not start_date or not end_date):
            parsed_start, parsed_end = parse_advisor_dates_to_iso(payload.raw_dates_text)
            if parsed_start and not start_date:
                start_date = parsed_start
            if parsed_end and not end_date:
                end_date = parsed_end

        children_details = payload.children_details or derive_children_details(payload.children, payload.kid_ages)
        payload_dict = payload.model_dump()

        designer_id = updated_by_profile_id or payload.travel_designer_id or payload.created_by_profile_id

        req, rev = await self.repo.save_edited_request(
            req,
            role=payload.role,
            customer_name=payload.customer_name,
            email=payload.email,
            phone=payload.phone,
            company_name=payload.company_name,
            market=payload.market,
            preferred_contact=payload.preferred_contact,
            destinations=payload.destinations,
            start_date=start_date,
            end_date=end_date,
            raw_dates_text=payload.raw_dates_text,
            adults=payload.adults,
            children=payload.children,
            kid_ages=payload.kid_ages,
            children_details=children_details,
            travel_style=payload.travel_style,
            special_requirements=payload.special_requirements,
            payload_json=payload_dict,
            partner_id=payload.partner_id,
            updated_by_profile_id=designer_id,
            change_summary=payload.change_summary or "Edited via workspace",
            change_source=change_source,
        )

        outbox = OutboxService(self.session)
        await outbox.emit_event(
            event_type="quote_request.edited",
            aggregate_type="quote_request",
            aggregate_id=req.id,
            brand_id=(payload_dict.get("brand_id") or "selvara"),
            actor_email=payload.email,
            payload={
                "customer_name": payload.customer_name,
                "request_title": f"Inquiry for {payload.customer_name}",
                "designer_id": designer_id,
                "change_summary": payload.change_summary or "Edited via workspace",
            },
        )

        return req, rev

    async def transition_request_status(
        self,
        request_id: str,
        *,
        target_status: str,
        base_revision: int,
        actor_email: str | None,
        updated_by_profile_id: str | None = None,
        linked_quotation_id: str | None = None,
        allow_system_conversion: bool = False,
    ) -> QuoteRequest:
        req = await self.repo.get_by_id_for_update(request_id)
        if req is None:
            raise KeyError(f"QuoteRequest {request_id} not found.")
        if req.current_revision != base_revision:
            raise RequestRevisionConflictError(req.current_revision)
        allowed = target_status in REQUEST_STATUS_TRANSITIONS.get(req.status, frozenset())
        if allow_system_conversion and req.status == "new" and target_status == "quotation_created":
            allowed = True
        if not allowed:
            raise ValueError(f"Cannot move request from '{req.status}' to '{target_status}'.")

        previous_status = req.status
        req.status = target_status
        req.current_revision += 1
        req.updated_by_profile_id = updated_by_profile_id
        if linked_quotation_id is not None:
            req.linked_quotation_id = linked_quotation_id
        await self.repo.create_revision(
            request_id=req.id, revision=req.current_revision, role=req.role, status=req.status,
            customer_name=req.customer_name, email=req.email, phone=req.phone,
            company_name=req.company_name, market=req.market, preferred_contact=req.preferred_contact,
            destinations=req.destinations, start_date=req.start_date, end_date=req.end_date,
            raw_dates_text=req.raw_dates_text, adults=req.adults, children=req.children,
            kid_ages=req.kid_ages, children_details=req.children_details,
            travel_style=req.travel_style, special_requirements=req.special_requirements,
            payload_json=req.payload_json,
            change_summary=f"Workflow status changed from {previous_status} to {target_status}",
            change_source="workflow_status_change", created_by_profile_id=updated_by_profile_id,
        )
        await self.session.flush()
        await OutboxService(self.session).emit_event(
            event_type="quote_request.status_changed", aggregate_type="quote_request", aggregate_id=req.id,
            brand_id=str(req.payload_json.get("brand_id") or "selvara"), actor_email=actor_email,
            payload={"previous_status": previous_status, "status": target_status,
                     "revision": req.current_revision, "linked_quotation_id": req.linked_quotation_id},
        )
        return req

    async def get_request_revisions(self, request_id: str) -> list[QuoteRequestRevision]:
        req = await self.repo.get_by_id(request_id)
        if not req:
            raise KeyError(f"QuoteRequest {request_id} not found.")
        return await self.repo.get_revisions_by_request_id(request_id)

    async def get_request_revision(self, request_id: str, revision: int) -> QuoteRequestRevision:
        rev = await self.repo.get_revision_by_number(request_id, revision)
        if not rev:
            raise KeyError(f"Revision {revision} for QuoteRequest {request_id} not found.")
        return rev

    async def generate_quotation_from_request(
        self,
        request_id: str,
        *,
        created_by_profile_id: str | None = None,
        brand_id: str = "selvara",
        template_name: str = "itinerary-imagery-v1",
        overrides: QuotationMinimalOverridesSchema | None = None,
    ) -> dict[str, Any]:
        req = await self.repo.get_by_id(request_id)
        if not req:
            raise KeyError(f"QuoteRequest {request_id} not found.")

        source_revision = overrides.request_revision if overrides and overrides.request_revision else req.current_revision
        source_req = req
        if source_revision != req.current_revision:
            revision_snapshot = await self.repo.get_revision_by_number(request_id, source_revision)
            if revision_snapshot is None:
                raise KeyError(f"Revision {source_revision} for QuoteRequest {request_id} not found.")
            source_req = copy.copy(req)
            for field in (
                "role", "customer_name", "email", "phone", "company_name", "market", "preferred_contact",
                "destinations", "start_date", "end_date", "raw_dates_text", "adults", "children", "kid_ages",
                "children_details", "travel_style", "special_requirements", "payload_json",
            ):
                setattr(source_req, field, copy.deepcopy(getattr(revision_snapshot, field)))

        facts = convert_request_to_quotation_facts(source_req, overrides)

        effective_brand = facts.get("brand_id") or (req.payload_json or {}).get("brand_id") or brand_id
        effective_designer = (
            (facts.get("presentation_options") or {}).get("travel_designer_id")
            or req.created_by_profile_id
            or created_by_profile_id
            or (req.payload_json or {}).get("travel_designer_id")
        )
        effective_lang = facts.get("lang") or "en"
        effective_template = (facts.get("presentation_options") or {}).get("template_id") or template_name
        customer_display_name = (facts.get("customer_facts") or {}).get("customer_name") or req.customer_name or "Valued Guest"
        title = f"Journey for {customer_display_name}"

        # Create new quotation ID
        quotation_id = f"quo_{uuid.uuid4().hex[:12]}"
        quo_repo = QuotationRepository(self.session)
        doc_repo = QuotationDocumentRepository(self.session)

        from api.dependencies import V2_RENDERER_NAME
        from core.rules.semantic_identity import assign_missing_source_fact_ids
        from quote_document import CreateQuoteRequestV1
        from repositories.destination_repository import DestinationRepository, seed_destination_catalog
        from repositories.travel_designer_repository import (
            TravelDesignerRepository,
            apply_travel_designer_snapshot,
            serialize_travel_designer,
        )
        from services.facts_contract import normalize_legacy_facts_snapshot
        from services.facts_resolver import FactsResolver
        from services.media_default_service import MediaDefaultService
        from services.skeleton_builder import SkeletonBuilder

        normalized_facts = normalize_legacy_facts_snapshot(facts)
        payload = CreateQuoteRequestV1.model_validate(normalized_facts)
        await seed_destination_catalog(self.session)
        dest_repo = DestinationRepository(self.session)
        facts_resolver = FactsResolver()
        canonical, resolved = await facts_resolver.resolve(payload, dest_repo.resolve)
        # Match direct V2 intake: every first-version Fact gets a durable
        # identity before the skeleton and initial bypass plan are derived.
        # Otherwise an id-less day could be addressed as both ``1`` and
        # ``day-1``, making an atomic itinerary candidate impossible to apply.
        canonical_payload = canonical.model_dump(mode="json")
        canonical_payload["trip_facts"]["itinerary"] = assign_missing_source_fact_ids(
            list(canonical_payload["trip_facts"].get("itinerary") or []),
            creation_namespace=quotation_id,
            kind="itinerary_day",
        )
        canonical_payload["service_facts"]["hotels"] = assign_missing_source_fact_ids(
            list(canonical_payload["service_facts"].get("hotels") or []),
            creation_namespace=quotation_id,
            kind="hotel",
        )
        canonical, resolved = await facts_resolver.resolve(
            CreateQuoteRequestV1.model_validate(canonical_payload),
            dest_repo.resolve,
        )

        # Resolve Travel Designer
        designers = TravelDesignerRepository(self.session)
        designer_id = (
            (facts.get("presentation_options") or {}).get("travel_designer_id")
            or req.created_by_profile_id
            or created_by_profile_id
            or (req.payload_json or {}).get("travel_designer_id")
            or effective_designer
        )
        designer_profile = None
        if designer_id:
            designer_profile = await designers.get_profile(designer_id)
        if designer_profile is None:
            designer_profile = await designers.get_brand_default(effective_brand)
        if designer_profile is None:
            active_profiles = await designers.list_profiles(active_only=True, limit=1)
            if active_profiles:
                designer_profile = active_profiles[0]

        resolved_designer_id = designer_profile.id if designer_profile else None

        document = SkeletonBuilder().build(
            quotation_id=quotation_id,
            payload=canonical,
            resolved_facts=resolved,
            template=V2_RENDERER_NAME,
        )
        if designer_profile:
            apply_travel_designer_snapshot(document, serialize_travel_designer(designer_profile))
            canonical.presentation_options.travel_designer_id = designer_profile.id

        document["meta"]["resolvedDestinationRefs"] = {
            key: resolved.get(key) for key in ("routeDestinationRefs", "itinerary", "hotels")
        }

        # Create quotation record with V2_RENDERER_NAME
        quotation = await quo_repo.create_quotation(
            quotation_id=quotation_id,
            brand_id=effective_brand,
            template_name=V2_RENDERER_NAME,
            baseline_lang=effective_lang,
            opportunity_id=req.id,
            customer_name=customer_display_name,
            title=title,
            status="draft",
            source_kind="manual",
            source_snapshot_at=datetime.now().astimezone(),
            designer_profile_id=resolved_designer_id,
            created_by_profile_id=created_by_profile_id or resolved_designer_id,
            quotation_family_id=quotation_id,
            business_version=1,
            source_request_id=req.id,
            source_request_revision=source_revision,
        )

        # Create quotation request snapshot
        await quo_repo.create_quotation_request(
            quotation_id=quotation_id,
            request_json=canonical.model_dump(mode="json"),
        )
        await quo_repo.create_version_facts(
            quotation_id=quotation.id,
            canonical_facts_json=canonical.model_dump(mode="json"),
            resolved_facts_json=resolved,
            facts_hash=resolved.get("factsHash", ""),
            source_request_id=req.id,
            source_request_revision=source_revision,
        )

        # Media enrichment is best effort. Missing catalogue photos remain
        # explicit Design/publication blockers instead of aborting creation.
        await MediaDefaultService(self.session).apply_missing(
            document=document,
            quotation_id=quotation_id,
            lang=effective_lang,
        )


        # Save initial document revision
        saved = await doc_repo.save_current_document(
            quotation_id=quotation.id,
            lang=effective_lang,
            document_json=document,
            expected_revision=0,
        )
        document.setdefault("meta", {})["revision"] = saved.revision
        await doc_repo.append_document_revision(
            quotation_id=quotation.id,
            lang=effective_lang,
            revision=saved.revision,
            document_json=document,
            change_source="create_from_request",
        )
        from services.quotation_change_plan_service import QuotationChangePlanService
        await QuotationChangePlanService.persist(
            repository=ContentActionPlanRepository(self.session),
            quotation_id=quotation.id,
            predecessor_quotation_id=None,
            facts_hash=resolved.get("factsHash", ""),
            correlation_id=f"create-{quotation.id}",
            actions=QuotationChangePlanService.build_initial(canonical.model_dump(mode="json")),
        )

        # Conversion is a workflow transition too; it must be revisioned and
        # emitted through the same transactional outbox path as Kanban moves.
        await self.transition_request_status(
            req.id,
            target_status="quotation_created",
            base_revision=req.current_revision,
            actor_email=req.email,
            updated_by_profile_id=effective_designer,
            linked_quotation_id=quotation.id,
            allow_system_conversion=True,
        )

        outbox = OutboxService(self.session)
        await outbox.emit_event(
            event_type="quote_request.converted",
            aggregate_type="quote_request",
            aggregate_id=req.id,
            brand_id=effective_brand,
            actor_email=req.email,
            payload={
                "request_title": f"Inquiry for {customer_display_name}",
                "quotation_id": quotation.id,
                "designer_profile_id": effective_designer,
            },
        )
        await outbox.emit_event(
            event_type="quotation.created",
            aggregate_type="quotation",
            aggregate_id=quotation.id,
            brand_id=effective_brand,
            actor_email=req.email,
            payload={
                "title": title,
                "customer_name": customer_display_name,
                "designer_profile_id": effective_designer,
            },
        )

        return {
            "quotation_id": quotation.id,
            "request_id": req.id,
            "redirect_url": f"/workspace/quotations/{quotation.id}/edit?stage=facts&lang={effective_lang}",
            "status": "draft",
            "current_revision": saved.revision,
            "facts_snapshot": canonical.model_dump(mode="json"),
        }
