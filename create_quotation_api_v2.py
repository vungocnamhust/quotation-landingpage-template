import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
SOURCE_QUOTE_ID = os.getenv("SOURCE_QUOTE_ID", "quo_ca0ee9497372")
SOURCE_CTX_PATH = BASE_DIR / "published" / SOURCE_QUOTE_ID / "ctx.json"
SOURCE_LIVE_URL = os.getenv("SOURCE_QUOTE_URL", f"http://localhost:8111/quotations/{SOURCE_QUOTE_ID}")

URL = os.getenv("QUOTATION_API_V2_URL", "http://localhost:8111/api/v2/quotations")
TARGET_BRAND = os.getenv("QUOTATION_BRAND_ID", "capella_travel")
TARGET_LANG = os.getenv("QUOTATION_LANG", "en")
TIMEOUT_SECONDS = float(os.getenv("QUOTATION_API_TIMEOUT", "60"))

ROUTE_SPLIT_RE = re.compile(r"\s+[–-]\s+")
CURRENCY_RE = re.compile(r"([A-Z]{3})")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_text(value: str) -> str:
    text = " ".join((value or "").split())
    return "" if text.lower() in {"none", "null"} else text


def _load_source_html() -> str:
    try:
        response = requests.get(SOURCE_LIVE_URL, timeout=min(TIMEOUT_SECONDS, 10))
        response.raise_for_status()
        if response.text.strip():
            return response.text
    except Exception:
        pass

    for candidate_name in ("v2.html", "v1.html"):
        candidate = BASE_DIR / "published" / SOURCE_QUOTE_ID / candidate_name
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    return ""


def _extract_editable_texts(source_html: str) -> dict[str, str]:
    if not source_html.strip():
        return {}
    soup = BeautifulSoup(source_html, "html.parser")
    editable_texts: dict[str, str] = {}
    for element in soup.select("[data-editable]"):
        key = (element.get("data-editable") or "").strip()
        if not key:
            continue
        editable_texts[key] = _clean_text(element.get_text(" ", strip=True))
    return editable_texts


def _extract_indexed_editable_items(editables: dict[str, str], prefix: str) -> list[str]:
    indexed: list[tuple[int, str]] = []
    for key, value in editables.items():
        if not key.startswith(prefix):
            continue
        try:
            indexed.append((int(key[len(prefix):]), value))
        except ValueError:
            continue
    return [value for _, value in sorted(indexed)]


def _first_non_empty(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return ""


def _extract_destinations(ctx: dict) -> list[str]:
    route_text = ctx.get("route_txt") or ""
    route_destinations = [part.strip() for part in ROUTE_SPLIT_RE.split(route_text) if part.strip()]
    if route_destinations:
        return route_destinations

    destinations = []
    for day in ctx.get("itinerary_days") or []:
        city = _first_non_empty(day.get("segment_city"), (day.get("destinations") or [None])[0], day.get("overnight"))
        if city and city not in destinations:
            destinations.append(city)
    return destinations


def _extract_total_budget(ctx: dict) -> float | None:
    options = ctx.get("price_options") or []
    for option in options:
        total_price = option.get("totalPrice") or {}
        amount = total_price.get("amount")
        if amount not in (None, ""):
            try:
                return float(amount)
            except (TypeError, ValueError):
                pass
    for option in options:
        per_person = option.get("pricePerPerson") or {}
        amount = per_person.get("amount")
        if amount not in (None, ""):
            try:
                return float(amount)
            except (TypeError, ValueError):
                pass
    return None


def _extract_currency(ctx: dict) -> str:
    options = ctx.get("price_options") or []
    for option in options:
        for key in ("totalPrice", "pricePerPerson"):
            currency = ((option.get(key) or {}).get("currency")) or ""
            if currency:
                return currency
            display_text = ((option.get(key) or {}).get("displayText")) or ""
            match = CURRENCY_RE.search(display_text)
            if match:
                return match.group(1)
    return "USD"


def _build_trip_facts(ctx: dict, editables: dict[str, str]) -> dict:
    itinerary = []
    for index, day in enumerate(ctx.get("itinerary_days") or [], 1):
        description = day.get("description") or []
        summary = description[0] if description else day.get("title") or ""
        itinerary.append(
            {
                "day_number": day.get("dayNumber") or index,
                "destination": _first_non_empty(day.get("segment_city"), (day.get("destinations") or [None])[0], day.get("overnight")),
                "summary": summary,
                "overnight": day.get("overnight") or "",
                "meals": day.get("meals") or [],
                "display_title": day.get("title") or "",
                "highlights": day.get("activities") or [],
                "notes": day.get("notes") or [],
                "sense_of_pace": "",
                "display_date": day.get("date") or "",
                "label_highlights": day.get("label_highlights") or "Highlights:",
                "label_notes": day.get("label_notes") or "Notes:",
            }
        )
        for note in day.get("notes") or []:
            if isinstance(note, str) and note.startswith("Sense of Pace:"):
                itinerary[-1]["sense_of_pace"] = note.split(":", 1)[1].strip()

    return {
        "title": editables.get("tour_title") or ctx.get("tour_title") or "Vietnam Private Journey",
        "subtitle": ctx.get("lede") or "",
        "destinations": _extract_destinations(ctx),
        "start_date": ((ctx.get("itinerary_days") or [{}])[0]).get("date") or "",
        "end_date": ((ctx.get("itinerary_days") or [{}])[-1]).get("date") if ctx.get("itinerary_days") else "",
        "duration_days": len(itinerary),
        "duration_nights": max(len(itinerary) - 1, 0),
        "itinerary": itinerary,
        "special_requirements": [],
        "display_route_text": ctx.get("route_txt") or "",
        "display_travel_dates": editables.get("hero_meta_2") or ctx.get("travel_dates") or "",
        "hero_meta_1": editables.get("hero_meta_1") or ctx.get("hero_meta_1") or "",
        "hero_meta_2": editables.get("hero_meta_2") or ctx.get("hero_meta_2") or "",
        "footer_text": editables.get("footer_text") or ctx.get("footer_text") or "",
        "overview_title": editables.get("journey_overview_title") or ctx.get("quotation_title") or "",
        "journey_overview_title": editables.get("journey_overview_title") or "",
        "letter_highlight": editables.get("letter_highlight") or "",
        "letter_greeting": editables.get("letter_greeting") or "",
        "letter_intro": editables.get("letter_intro") or "",
        "letter_body": editables.get("letter_body_p2") or "",
        "letter_outro": editables.get("letter_outro") or "",
        "letter_sign_off": editables.get("letter_sign_off") or "",
        "letter_sender": editables.get("letter_sender") or "",
        "route_title": editables.get("route_map_h2") or ctx.get("route_map_h2") or "",
        "route_description": editables.get("route_map_p") or ctx.get("route_map_p") or "",
        "itinerary_title": editables.get("itinerary_h2") or ctx.get("itinerary_h2") or "",
        "itinerary_description": editables.get("itinerary_p") or ctx.get("itinerary_p") or "",
        "cover_kicker": editables.get("cover_kicker") or ctx.get("cover_kicker") or "",
    }


def _build_pricing_facts(ctx: dict, editables: dict[str, str]) -> dict:
    options = ctx.get("price_options") or []
    first_option = options[0] if options else {}
    return {
        "currency": _extract_currency(ctx),
        "total_budget": _extract_total_budget(ctx),
        "price_basis": ctx.get("glance_basis") or "Indicative pricing, subject to reconfirmation",
        "option_label": first_option.get("optionName") or first_option.get("hotelCategory") or "Main option",
        "kicker": ctx.get("pricing_kicker") or "Package Pricing",
        "display_title": editables.get("pricing_h2") or ctx.get("pricing_h2") or "",
        "display_subtitle": editables.get("pricing_p") or ctx.get("pricing_p") or "",
        "cta_label": editables.get("payment_cta") or ctx.get("payment_cta") or "",
        "conditions": ctx.get("price_cond_paras") or [],
        "options": [
            {
                "category": option.get("hotelCategory") or "",
                "name": option.get("optionName") or "",
                "per_person_text": ((option.get("pricePerPerson") or {}).get("displayText")) or "",
                "total_text": ((option.get("totalPrice") or {}).get("displayText")) or "",
                "is_total": bool(option.get("is_total")),
                "is_confirmed_main_option": bool(option.get("isConfirmedMainOption")),
                "is_alternative_option": bool(option.get("isAlternativeOption")),
            }
            for option in options
        ],
    }


def _build_customer_facts(ctx: dict) -> dict:
    return {
        "customer_name": ctx.get("customer_name") or "Guest",
        "adults": 2,
        "children": 0,
        "nationality": ctx.get("nationality") or "",
        "guest_profile": ctx.get("guests_txt") or ctx.get("customer_name") or "Private guests",
        "market": ctx.get("glance_market") or "",
        "party_label": ctx.get("guests_txt") or ctx.get("customer_name") or "",
        "greeting_name": ctx.get("customer_name") or "",
    }


def _build_service_facts(ctx: dict) -> dict:
    hotels = []
    for hotel in ctx.get("hotels") or []:
        hotels.append(
            {
                "destination": hotel.get("destination") or hotel.get("city_country") or "",
                "name": hotel.get("name") or "",
                "room_type": hotel.get("room_type") or hotel.get("room_name") or "",
                "check_in": hotel.get("checkInDate") or "",
                "check_out": hotel.get("checkOutDate") or "",
                "intro": hotel.get("introduction") or hotel.get("hotel_intro") or "",
                "phone": hotel.get("tel") or hotel.get("telephone") or "",
                "display_city": hotel.get("city_country") or "",
                "display_date": hotel.get("date_range") or hotel.get("check_in_out") or "",
                "hotel_asset": hotel.get("hotel_img") or "",
                "room_asset": hotel.get("room_img") or "",
            }
        )
    return {
        "hotels": hotels,
        "inclusions": ctx.get("inclusions") or [],
        "exclusions": ctx.get("exclusions") or [],
        "room_notes": ctx.get("room_notes") or "",
    }


def _build_booking_facts(ctx: dict, editables: dict[str, str]) -> dict:
    indexed_labels = _extract_indexed_editable_items(editables, "booking_term_label_")
    indexed_bodies = _extract_indexed_editable_items(editables, "booking_term_body_")
    items = []
    booking_keys = ("deposit", "balance", "cancellation", "confirmation")
    for index, (key, default_label) in enumerate(
        zip(booking_keys, ("Deposit", "Balance", "Cancellation", "Confirmation")),
        0,
    ):
        body = (
            indexed_bodies[index]
            if index < len(indexed_bodies)
            else ctx.get(f"term_{key}") or ""
        )
        label = (
            indexed_labels[index]
            if index < len(indexed_labels)
            else ctx.get(f"payment_label_{key}") or default_label
        )
        if body or label:
            items.append({"key": key, "label": label, "body": body})
    return {
        "title": editables.get("payment_title") or ctx.get("payment_title") or "Booking & Payment Terms",
        "description": editables.get("payment_desc") or ctx.get("payment_desc") or "",
        "items": items,
    }


def _build_finalization_facts(ctx: dict, editables: dict[str, str]) -> dict:
    return {
        "required_title": editables.get("final_req_title") or ctx.get("final_req_title") or "",
        "after_confirmation_title": editables.get("final_after_title") or ctx.get("final_after_title") or "",
        "required_items": _extract_indexed_editable_items(editables, "final_req_") or ctx.get("final_req") or [],
        "after_confirmation_items": _extract_indexed_editable_items(editables, "final_after_") or ctx.get("final_after") or [],
    }


def _build_seller_facts(ctx: dict, editables: dict[str, str]) -> dict:
    return {
        "seller_name": editables.get("seller_name") or ctx.get("seller_name") or "",
        "seller_subtitle": editables.get("seller_subtitle") or ctx.get("seller_subtitle") or "",
        "seller_email": ctx.get("seller_email") or "",
        "seller_phone": ctx.get("contact_phone") or ctx.get("contact") or "",
        "contact_web": ctx.get("contact_web") or "",
        "designer_name": editables.get("seller_name") or ctx.get("seller_name") or "",
        "designer_signature": editables.get("letter_sender") or ctx.get("designer_signature") or "",
        "designer_kicker": editables.get("designer_kicker") or ctx.get("designer_kicker") or "",
        "designer_quote": editables.get("designer_quote") or ctx.get("designer_quote") or "",
        "designer_experience": editables.get("designer_experience") or ctx.get("designer_experience") or "",
        "designer_title": editables.get("designer_title") or ctx.get("designer_title") or "",
        "cta_body": editables.get("cta_h2") or ctx.get("cta_h2") or "",
        "designer_email": ctx.get("seller_email") or "",
        "designer_phone": ctx.get("contact_phone") or ctx.get("contact") or "",
    }


def build_payload() -> dict:
    ctx = _load_json(SOURCE_CTX_PATH)
    editables = _extract_editable_texts(_load_source_html())
    return {
        "opportunity_id": ctx.get("quotation_number") or SOURCE_QUOTE_ID,
        "brand_id": TARGET_BRAND,
        "lang": TARGET_LANG,
        "trip_facts": _build_trip_facts(ctx, editables),
        "pricing_facts": _build_pricing_facts(ctx, editables),
        "customer_facts": _build_customer_facts(ctx),
        "service_facts": _build_service_facts(ctx),
        "booking_facts": _build_booking_facts(ctx, editables),
        "finalization_facts": _build_finalization_facts(ctx, editables),
        "seller_facts": _build_seller_facts(ctx, editables),
        "retrieval_refs": [],
    }


def main() -> None:
    payload = build_payload()

    print("POST", URL)
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    response = requests.post(URL, json=payload, timeout=TIMEOUT_SECONDS)
    print("status_code:", response.status_code)

    try:
        response_data = response.json()
    except ValueError:
        print(response.text)
        response.raise_for_status()
        return

    print(json.dumps(response_data, ensure_ascii=False, indent=2))
    response.raise_for_status()

    quotation_url = response_data.get("quotationUrl") or ""
    pdf_url = response_data.get("pdfUrl") or ""
    quotation_id = response_data.get("quotationId") or ""

    print("\nquotation_id:", quotation_id)
    print("quotation_url:", quotation_url)
    print("pdf_url:", pdf_url)


if __name__ == "__main__":
    main()
