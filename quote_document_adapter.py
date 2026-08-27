from __future__ import annotations

import copy
from typing import Any

from quote_document import (
    QuoteAssetRef,
    QuoteDocumentV1,
    QuoteListItem,
    QuoteSection,
    QuoteTermItem,
    SECTION_TYPES,
    build_default_sections,
    build_rich_content_from_legacy,
    rich_content_values,
    strip_legacy_rich_document_fields,
)


def _asset_ref(value: Any) -> QuoteAssetRef:
    if isinstance(value, dict):
        return QuoteAssetRef(
            assetId=value.get("assetId") or "",
            r2Key=value.get("r2Key") or "",
            url=value.get("url") or "",
            status=value.get("status") or "ready",
        )
    if isinstance(value, str):
        return QuoteAssetRef(url=value, status="ready")
    return QuoteAssetRef()


def _list_items(values: list[Any] | None, prefix: str) -> list[QuoteListItem]:
    items: list[QuoteListItem] = []
    for index, item in enumerate(values or [], 1):
        text = item.get("text") if isinstance(item, dict) else str(item or "")
        if text:
            items.append(QuoteListItem(id=f"{prefix}-{index}", text=text))
    return items


def _term_items(lang_ctx: dict) -> list[QuoteTermItem]:
    items = [
        QuoteTermItem(
            id="deposit",
            key="deposit",
            label=lang_ctx.get("payment_label_deposit") or "Deposit",
            body=lang_ctx.get("term_deposit") or "",
        ),
        QuoteTermItem(
            id="balance",
            key="balance",
            label=lang_ctx.get("payment_label_balance") or "Balance",
            body=lang_ctx.get("term_balance") or "",
        ),
        QuoteTermItem(
            id="cancellation",
            key="cancellation",
            label=lang_ctx.get("payment_label_cancellation") or "Cancellation",
            body=lang_ctx.get("term_cancellation") or "",
        ),
        QuoteTermItem(
            id="confirmation",
            key="confirmation",
            label=lang_ctx.get("payment_label_confirmation") or "Confirmation",
            body=lang_ctx.get("term_confirmation") or "",
        ),
    ]
    return [item for item in items if item.label or item.body]


def _normalize_layout(layout: dict | None) -> list[QuoteSection]:
    raw_sections = (layout or {}).get("sections") or []
    if not raw_sections:
        return build_default_sections()
    normalized: list[QuoteSection] = []
    for index, section in enumerate(raw_sections, 1):
        if isinstance(section, QuoteSection):
            normalized.append(section)
            continue
        if not isinstance(section, dict):
            continue
        section_type = section.get("type") or "hero"
        if section_type not in SECTION_TYPES:
            continue
        normalized.append(
            QuoteSection(
                id=section.get("id") or section_type or f"section-{index}",
                type=section_type,
                enabled=bool(section.get("enabled", True)),
                order=int(section.get("order") or index),
                props=copy.deepcopy(section.get("props") or {}),
            )
        )
    return normalized or build_default_sections()


def build_quote_document_from_lang_ctx(lang_ctx: dict, quotation_id: str, lang: str) -> dict:
    brand = copy.deepcopy(lang_ctx.get("brand") or {})
    itinerary_days = copy.deepcopy(lang_ctx.get("itinerary_days") or [])
    stay_segments = copy.deepcopy(lang_ctx.get("stay_segments") or [])
    hotels = copy.deepcopy(lang_ctx.get("hotels") or [])
    price_options = copy.deepcopy(lang_ctx.get("price_options") or [])
    stored_document = lang_ctx.get("quote_document") or lang_ctx.get("brochure_draft") or {}
    stored_layout = stored_document.get("layout") if isinstance(stored_document, dict) else {}

    # This function is retained exclusively by legacy-artifact migration and
    # repair commands.  It materializes the strict rich-content contract here,
    # before handing the result to the V2 validator; runtime never performs
    # this conversion on a loaded V2 document.
    payload = {
            "meta": {
                "quotationId": quotation_id,
                "opportunityId": lang_ctx.get("opportunity_id") or lang_ctx.get("quotation_number") or quotation_id,
                "lang": lang,
                "brandId": brand.get("id") or "vietnam_safar",
                "version": int(lang_ctx.get("latest_version") or 1),
                "template": lang_ctx.get("template_name") or "vietnam_luxury_brosure.html",
                "revision": int((((stored_document.get("meta") or {}).get("revision")) if isinstance(stored_document, dict) else 1) or 1),
                "status": "draft",
            },
            "brand": {
                "name": brand.get("name") or "",
                "domain": brand.get("domain") or "",
                "logo": _asset_ref(brand.get("logo")),
                "colors": {
                    "primary": brand.get("color_primary") or "#17412e",
                    "primaryDark": brand.get("color_primary_dark") or "#0e2f22",
                    "accent": brand.get("color_accent") or "#b7894b",
                    "accentLight": brand.get("color_accent_light") or "#d8bd85",
                    "bgMain": brand.get("color_bg_main") or "#f9f6f0",
                    "bgAlt": brand.get("color_bg_alt") or "#fffaf1",
                    "textMain": brand.get("color_text_main") or "#11130f",
                    "textMuted": brand.get("color_text_muted") or "#706a5d",
                    "textLight": brand.get("color_text_light") or "#ffffff",
                },
                "fonts": {
                    "serif": brand.get("font_serif") or "Cormorant Garamond",
                    "sans": brand.get("font_sans") or "Montserrat",
                    "accent": brand.get("font_accent") or "Allura",
                },
            },
            "assets": {
                "hero": _asset_ref(lang_ctx.get("hero_img_custom") or lang_ctx.get("img_0")),
                "itineraryDivider": _asset_ref(lang_ctx.get("img_itinerary_divider")),
                "staysDivider": _asset_ref(lang_ctx.get("img_stays_divider")),
                "hotelDivider": _asset_ref(lang_ctx.get("img_hotel_divider")),
            },
            "traveler": {
                "customerName": lang_ctx.get("customer_name") or "",
                "guestProfile": lang_ctx.get("guests_txt") or "",
                "nationality": lang_ctx.get("nationality") or "",
            },
            "trip": {
                "title": lang_ctx.get("tour_title") or "",
                "lede": lang_ctx.get("lede") or "",
                "durationText": lang_ctx.get("duration_label") or "",
                "routeText": lang_ctx.get("route_txt") or "",
                "travelDates": lang_ctx.get("travel_dates") or "",
                "quotationNumber": lang_ctx.get("quotation_number") or quotation_id,
            },
            "narrative": {
                "coverKicker": lang_ctx.get("cover_kicker") or "A Privately Arranged Journey",
                "heroMeta1": lang_ctx.get("hero_meta_1") or "",
                "heroMeta2": lang_ctx.get("hero_meta_2") or "",
                "journeyOverviewTitle": lang_ctx.get("journey_overview_title") or "A Journey Shaped Around Your Family",
                "letterHighlight": lang_ctx.get("letter_highlight") or "This journey was designed to leave room for both discovery and rest.",
                "letterGreeting": lang_ctx.get("letter_greeting") or f"Dear {lang_ctx.get('greeting_name') or lang_ctx.get('customer_name') or 'Valued Guest'},",
                "letterIntro": lang_ctx.get("letter_intro") or "",
                "letterBody2": lang_ctx.get("letter_body_p2") or "",
                "letterOutro": lang_ctx.get("letter_outro") or "",
                "letterSignOff": lang_ctx.get("letter_sign_off") or lang_ctx.get("seller_name") or "Eddie - Trung Hieu Pham",
                "letterSender": lang_ctx.get("letter_sender") or "Your Journey Designer",
                "footerText": lang_ctx.get("footer_text") or "",
            },
            "route": {
                "title": lang_ctx.get("route_map_h2") or "",
                "description": lang_ctx.get("route_map_p") or "",
                "staySegments": [
                    {
                        "id": segment.get("segmentId") or f"stay-{idx}",
                        "displayName": segment.get("displayName") or "",
                        "daysLabel": segment.get("daysLabel") or "",
                        "nightsLabel": segment.get("nightsLabel") or "",
                        "hotelName": segment.get("hotelName") or "",
                        "hotelDateRange": segment.get("hotelDateRange") or "",
                        "hotelImage": _asset_ref(segment.get("hotelImage")),
                        "mapSegmentDesc": segment.get("mapSegmentDesc") or "",
                        "coords": copy.deepcopy(segment.get("coords") or []),
                    }
                    for idx, segment in enumerate(stay_segments, 1)
                ],
            },
            "itinerary": {
                "title": lang_ctx.get("itinerary_h2") or "",
                "description": lang_ctx.get("itinerary_p") or "",
                "days": [
                    {
                        "id": day.get("id") or f"day-{day.get('dayNumber') or idx}",
                        "dayNumber": day.get("dayNumber") or idx,
                        "segmentCity": day.get("segment_city") or "",
                        "title": day.get("title") or "",
                        "description": copy.deepcopy(day.get("description") or []),
                        "overnight": day.get("overnight") or "",
                        "meals": copy.deepcopy(day.get("meals") or []),
                        "activities": copy.deepcopy(day.get("activities") or []),
                        "notes": copy.deepcopy(day.get("notes") or []),
                        "labelHighlights": day.get("label_highlights") or "Highlights:",
                        "labelNotes": day.get("label_notes") or "Notes:",
                        "layoutType": day.get("layout_type") or "single",
                        "images": {
                            "hero": _asset_ref((day.get("layout_images") or {}).get("hero")),
                            "small1": _asset_ref((day.get("layout_images") or {}).get("small-1")),
                            "small2": _asset_ref((day.get("layout_images") or {}).get("small-2")),
                            "carousel": [_asset_ref(img) for img in ((day.get("layout_images") or {}).get("carousel") or [])],
                        },
                    }
                    for idx, day in enumerate(itinerary_days, 1)
                ],
            },
            "stays": {
                "hotels": [
                    {
                        "id": hotel.get("id") or f"hotel-{idx}",
                        "city": hotel.get("city_country") or "",
                        "name": hotel.get("name") or "",
                        "introduction": hotel.get("introduction") or hotel.get("hotel_intro") or "",
                        "hotelDate": hotel.get("date_range") or hotel.get("check_in_out") or "",
                        "tel": hotel.get("tel") or hotel.get("telephone") or "",
                        "roomType": hotel.get("room_type") or hotel.get("room_name") or "",
                        "hotelImage": _asset_ref(hotel.get("hotel_img")),
                        "roomImage": _asset_ref(hotel.get("room_img")),
                    }
                    for idx, hotel in enumerate(hotels, 1)
                ],
                "roomNotes": lang_ctx.get("room_notes") or "",
            },
            "pricing": {
                "kicker": lang_ctx.get("pricing_kicker") or "Package Pricing",
                "title": lang_ctx.get("pricing_h2") or "",
                "description": lang_ctx.get("pricing_p") or "",
                "ctaLabel": lang_ctx.get("payment_cta") or "",
                "conditions": _list_items(lang_ctx.get("price_cond_paras") or [], "price-cond"),
                "options": [
                    {
                        "id": option.get("id") or f"price-{idx}",
                        "category": option.get("hotelCategory") or "",
                        "name": option.get("optionName") or "",
                        "perPersonText": ((option.get("pricePerPerson") or {}).get("displayText") if isinstance(option.get("pricePerPerson"), dict) else "") or "",
                        "totalText": ((option.get("totalPrice") or {}).get("displayText") if isinstance(option.get("totalPrice"), dict) else "") or "",
                        "isTotal": bool(option.get("is_total")),
                        "isConfirmedMainOption": bool(option.get("isConfirmedMainOption")),
                        "isAlternativeOption": bool(option.get("isAlternativeOption")),
                    }
                    for idx, option in enumerate(price_options, 1)
                ],
            },
            "inclusions": _list_items(lang_ctx.get("inclusions") or [], "inc"),
            "exclusions": _list_items(lang_ctx.get("exclusions") or [], "exc"),
            "bookingTerms": {
                "kicker": lang_ctx.get("payment_kicker") or "Important Notes",
                "title": lang_ctx.get("payment_title") or "Booking & Payment Terms",
                "description": lang_ctx.get("payment_desc") or "",
                "items": [item.model_dump() for item in _term_items(lang_ctx)],
            },
            "designer": {
                "name": lang_ctx.get("seller_name") or "Eddie",
                "subtitle": lang_ctx.get("seller_subtitle") or "Trung Hieu Pham",
                "kicker": lang_ctx.get("designer_kicker") or "YOUR JOURNEY DESIGNER",
                "signature": lang_ctx.get("designer_signature") or "TRAVEL DESIGNER",
                "experience": lang_ctx.get("designer_experience") or "Present throughout the planning, quietly working behind the journey.",
                "quote": lang_ctx.get("designer_quote") or "",
                "title": lang_ctx.get("designer_title") or "",
                "ctaBody": lang_ctx.get("cta_h2") or "",
                "phone": lang_ctx.get("contact_phone") or lang_ctx.get("contact") or "+84 911 538 738",
                "email": lang_ctx.get("seller_email") or "",
                "image": _asset_ref(lang_ctx.get("designer_img") or "/assets/dias_team/hieu.jpg"),
            },
            "layout": {
                "sections": [
                    section.model_dump()
                    for section in _normalize_layout(stored_layout)
                ]
            },
            "generationStatus": copy.deepcopy((stored_document.get("generationStatus") if isinstance(stored_document, dict) else None) or {
                "narrative": "manual",
                "assets": "manual",
                "warnings": [],
            }),
            "viewOverrides": copy.deepcopy((stored_document.get("viewOverrides") if isinstance(stored_document, dict) else None) or {"web": {}, "pdf": {}}),
        }
    payload["content"] = build_rich_content_from_legacy(payload)
    payload["meta"]["contentSchemaVersion"] = 1
    payload = strip_legacy_rich_document_fields(payload)
    quote_document = QuoteDocumentV1.model_validate(payload)
    return quote_document.model_dump(mode="json")


def normalize_quote_document(document: dict | None, quotation_id: str, lang: str, *, template_name: str = "vietnam_luxury_brosure.html", brand_id: str = "vietnam_safar") -> dict:
    payload = copy.deepcopy(document or {})
    payload.setdefault("meta", {})
    payload["meta"]["quotationId"] = payload["meta"].get("quotationId") or quotation_id
    payload["meta"]["lang"] = payload["meta"].get("lang") or lang
    payload["meta"]["brandId"] = payload["meta"].get("brandId") or brand_id
    payload["meta"]["template"] = payload["meta"].get("template") or template_name
    # Atomic V2 cutover: legacy HTML is migrated by the explicit preflight
    # command, never by a runtime adapter or public renderer.
    if not isinstance(payload.get("content"), dict) or not isinstance(payload.get("content", {}).get("sections"), dict):
        raise ValueError("content.sections is required; run scripts/migrate_v2_rich_content.py before loading this document.")
    if payload["meta"].get("contentSchemaVersion") != 1:
        raise ValueError("meta.contentSchemaVersion=1 is required before loading this document.")
    payload["layout"] = payload.get("layout") or {"sections": build_default_sections()}
    return QuoteDocumentV1.model_validate(payload).model_dump(mode="json")


def apply_quote_document_to_lang_ctx(lang_ctx: dict, document: dict) -> None:
    quote_document = QuoteDocumentV1.model_validate(document)
    rich_content = rich_content_values(quote_document)
    brand = quote_document.brand
    lang_ctx["brand"] = {
        **copy.deepcopy(lang_ctx.get("brand") or {}),
        "name": brand.name,
        "domain": brand.domain,
        "logo": brand.logo.url,
        "color_primary": brand.colors.get("primary") or "#17412e",
        "color_primary_dark": brand.colors.get("primaryDark") or "#0e2f22",
        "color_accent": brand.colors.get("accent") or "#b7894b",
        "color_accent_light": brand.colors.get("accentLight") or "#d8bd85",
        "color_bg_main": brand.colors.get("bgMain") or "#f9f6f0",
        "color_bg_alt": brand.colors.get("bgAlt") or "#fffaf1",
        "color_text_main": brand.colors.get("textMain") or "#11130f",
        "color_text_muted": brand.colors.get("textMuted") or "#706a5d",
        "color_text_light": brand.colors.get("textLight") or "#ffffff",
        "font_serif": brand.fonts.get("serif") or "Cormorant Garamond",
        "font_sans": brand.fonts.get("sans") or "Montserrat",
        "font_accent": brand.fonts.get("accent") or "Allura",
    }

    lang_ctx["hero_img_custom"] = quote_document.assets.hero.url or lang_ctx.get("hero_img_custom")
    lang_ctx["img_0"] = quote_document.assets.hero.url or lang_ctx.get("img_0")
    lang_ctx["img_itinerary_divider"] = quote_document.assets.itineraryDivider.url or lang_ctx.get("img_itinerary_divider")
    lang_ctx["img_stays_divider"] = quote_document.assets.staysDivider.url or lang_ctx.get("img_stays_divider")
    lang_ctx["img_hotel_divider"] = quote_document.assets.hotelDivider.url or lang_ctx.get("img_hotel_divider")
    lang_ctx["designer_img"] = quote_document.designer.image.url or lang_ctx.get("designer_img")
    lang_ctx["customer_name"] = quote_document.traveler.customerName or lang_ctx.get("customer_name")
    lang_ctx["guests_txt"] = quote_document.traveler.guestProfile or lang_ctx.get("guests_txt")
    lang_ctx["nationality"] = quote_document.traveler.nationality or lang_ctx.get("nationality")
    lang_ctx["tour_title"] = quote_document.trip.title or lang_ctx.get("tour_title")
    lang_ctx["lede"] = quote_document.trip.lede or lang_ctx.get("lede")
    lang_ctx["duration_label"] = quote_document.trip.durationText or lang_ctx.get("duration_label")
    lang_ctx["route_txt"] = quote_document.trip.routeText or lang_ctx.get("route_txt")
    lang_ctx["travel_dates"] = quote_document.trip.travelDates or lang_ctx.get("travel_dates")
    lang_ctx["quotation_number"] = quote_document.trip.quotationNumber or lang_ctx.get("quotation_number")

    lang_ctx["cover_kicker"] = quote_document.narrative.coverKicker or lang_ctx.get("cover_kicker")
    lang_ctx["hero_meta_1"] = quote_document.narrative.heroMeta1 or lang_ctx.get("hero_meta_1")
    lang_ctx["hero_meta_2"] = quote_document.narrative.heroMeta2 or lang_ctx.get("hero_meta_2")
    lang_ctx["journey_overview_title"] = quote_document.narrative.journeyOverviewTitle or lang_ctx.get("journey_overview_title")
    lang_ctx["letter_highlight"] = quote_document.narrative.letterHighlight or lang_ctx.get("letter_highlight")
    lang_ctx["letter_greeting"] = quote_document.narrative.letterGreeting or lang_ctx.get("letter_greeting")
    lang_ctx["letter_intro"] = quote_document.narrative.letterIntro or lang_ctx.get("letter_intro")
    lang_ctx["letter_body_p2"] = quote_document.narrative.letterBody2 or lang_ctx.get("letter_body_p2")
    lang_ctx["letter_outro"] = quote_document.narrative.letterOutro or lang_ctx.get("letter_outro")
    lang_ctx["letter_sign_off"] = quote_document.narrative.letterSignOff or lang_ctx.get("letter_sign_off")
    lang_ctx["letter_sender"] = quote_document.narrative.letterSender or lang_ctx.get("letter_sender")
    lang_ctx["footer_text"] = quote_document.narrative.footerText or lang_ctx.get("footer_text")

    lang_ctx["route_map_h2"] = quote_document.route.title or lang_ctx.get("route_map_h2")
    lang_ctx["route_map_p"] = quote_document.route.description or lang_ctx.get("route_map_p")
    lang_ctx["stay_segments"] = [
        {
            "segmentId": segment.id,
            "displayName": segment.displayName,
            "daysLabel": segment.daysLabel,
            "nightsLabel": segment.nightsLabel,
            "hotelName": segment.hotelName,
            "hotelDateRange": segment.hotelDateRange,
            "hotelImage": segment.hotelImage.url,
            "mapSegmentDesc": segment.mapSegmentDesc,
            "coords": copy.deepcopy(segment.coords),
        }
        for segment in quote_document.route.staySegments
    ]

    lang_ctx["itinerary_h2"] = quote_document.itinerary.title or lang_ctx.get("itinerary_h2")
    lang_ctx["itinerary_p"] = quote_document.itinerary.description or lang_ctx.get("itinerary_p")
    lang_ctx["itinerary_days"] = [
        {
            "id": day.id,
            "dayNumber": day.dayNumber,
            "segment_city": day.segmentCity,
            "title": day.title,
            "description": copy.deepcopy(day.description),
            "overnight": day.overnight,
            "meals": copy.deepcopy(day.meals),
            "activities": copy.deepcopy(day.activities),
            "notes": copy.deepcopy(day.notes),
            "label_highlights": day.labelHighlights,
            "label_notes": day.labelNotes,
            "layout_type": day.layoutType,
            "layout_images": {
                "hero": day.images.hero.url,
                "small-1": day.images.small1.url,
                "small-2": day.images.small2.url,
                "carousel": [item.url for item in day.images.carousel if item.url],
            },
        }
        for day in quote_document.itinerary.days
    ]
    lang_ctx["itinerary"] = [
        {
            "dayNumber": day.dayNumber,
            "title": day.title,
            "description": copy.deepcopy(day.description),
            "overnight": day.overnight,
            "meals": copy.deepcopy(day.meals),
            "activities": copy.deepcopy(day.activities),
            "notes": copy.deepcopy(day.notes),
            "destinations": [day.segmentCity] if day.segmentCity else [],
            "label_highlights": day.labelHighlights,
            "label_notes": day.labelNotes,
        }
        for day in quote_document.itinerary.days
    ]
    lang_ctx["timeline_days"] = copy.deepcopy(lang_ctx["itinerary"])

    lang_ctx["hotels"] = [
        {
            "id": hotel.id,
            "city_country": hotel.city,
            "name": hotel.name,
            "introduction": hotel.introduction,
            "hotel_intro": hotel.introduction,
            "date_range": hotel.hotelDate,
            "tel": hotel.tel,
            "telephone": hotel.tel,
            "room_type": hotel.roomType,
            "room_name": hotel.roomType,
            "hotel_img": hotel.hotelImage.url,
            "room_img": hotel.roomImage.url,
        }
        for hotel in quote_document.stays.hotels
    ]
    lang_ctx["room_notes"] = quote_document.stays.roomNotes or lang_ctx.get("room_notes")

    lang_ctx["pricing_kicker"] = quote_document.pricing.kicker or lang_ctx.get("pricing_kicker")
    lang_ctx["pricing_h2"] = quote_document.pricing.title or lang_ctx.get("pricing_h2")
    lang_ctx["pricing_p"] = quote_document.pricing.description or lang_ctx.get("pricing_p")
    lang_ctx["payment_cta"] = quote_document.pricing.ctaLabel or lang_ctx.get("payment_cta")
    lang_ctx["price_cond_paras"] = [item.text for item in quote_document.pricing.conditions]
    def legacy_price_text(amount_minor: int | None, currency: str, suffix: str, fallback: str) -> str:
        if amount_minor is None or not currency:
            return fallback
        divisor = 1 if currency == "VND" else 100
        return f"{currency} {amount_minor / divisor:,.0f} {suffix}".strip()

    lang_ctx["price_options"] = [
        {
            "id": option.id,
            "hotelCategory": option.label,
            "optionName": option.label,
            "pricePerPerson": {"displayText": legacy_price_text(option.perTravelerAmountMinor, option.currency, "/ person", option.legacyPerPersonText)},
            "totalPrice": {"displayText": legacy_price_text(option.groupTotalAmountMinor, option.currency, "total", option.legacyTotalText)},
            # This bridge is for legacy Jinja snapshots only. Public V2 React
            # rendering consumes the typed values directly and has no status.
            "is_total": False,
            "isConfirmedMainOption": index == 0,
            "isAlternativeOption": False,
        }
        for index, option in enumerate(quote_document.pricing.options)
    ]

    lang_ctx["inclusions"] = rich_content["inclusions"]
    lang_ctx["exclusions"] = rich_content["exclusions"]

    lang_ctx["payment_desc"] = rich_content["bookingDescription"] or lang_ctx.get("payment_desc")
    lang_ctx["booking_terms_items"] = rich_content["bookingItems"]
    item_map = {
        str(item["label"]).strip().lower(): QuoteTermItem(id=str(index), label=str(item["label"]), body=str(item["body"]))
        for index, item in enumerate(rich_content["bookingItems"], 1)
    }
    lang_ctx["payment_label_deposit"] = item_map.get("deposit", QuoteTermItem(id="deposit")).label or lang_ctx.get("payment_label_deposit")
    lang_ctx["payment_label_balance"] = item_map.get("balance", QuoteTermItem(id="balance")).label or lang_ctx.get("payment_label_balance")
    lang_ctx["payment_label_cancellation"] = item_map.get("cancellation", QuoteTermItem(id="cancellation")).label or lang_ctx.get("payment_label_cancellation")
    lang_ctx["payment_label_confirmation"] = item_map.get("confirmation", QuoteTermItem(id="confirmation")).label or lang_ctx.get("payment_label_confirmation")
    lang_ctx["term_deposit"] = item_map.get("deposit", QuoteTermItem(id="deposit")).body or lang_ctx.get("term_deposit")
    lang_ctx["term_balance"] = item_map.get("balance", QuoteTermItem(id="balance")).body or lang_ctx.get("term_balance")
    lang_ctx["term_cancellation"] = item_map.get("cancellation", QuoteTermItem(id="cancellation")).body or lang_ctx.get("term_cancellation")
    lang_ctx["term_confirmation"] = item_map.get("confirmation", QuoteTermItem(id="confirmation")).body or lang_ctx.get("term_confirmation")

    lang_ctx["seller_name"] = quote_document.designer.name or lang_ctx.get("seller_name")
    lang_ctx["seller_subtitle"] = quote_document.designer.subtitle or lang_ctx.get("seller_subtitle")
    lang_ctx["designer_kicker"] = quote_document.designer.kicker or lang_ctx.get("designer_kicker")
    lang_ctx["designer_signature"] = quote_document.designer.signature or lang_ctx.get("designer_signature")
    lang_ctx["designer_experience"] = quote_document.designer.experience or lang_ctx.get("designer_experience")
    lang_ctx["designer_quote"] = quote_document.designer.quote or lang_ctx.get("designer_quote")
    lang_ctx["designer_title"] = quote_document.designer.title or lang_ctx.get("designer_title")
    lang_ctx["cta_h2"] = quote_document.designer.ctaBody or lang_ctx.get("cta_h2")
    lang_ctx["contact_phone"] = quote_document.designer.phone or lang_ctx.get("contact_phone")
    lang_ctx["contact"] = quote_document.designer.phone or lang_ctx.get("contact")
    lang_ctx["seller_email"] = quote_document.designer.email or lang_ctx.get("seller_email")

    section_enabled = {}
    section_order = {}
    for section in quote_document.layout.sections:
        section_enabled[section.type] = section.enabled
        section_order[section.type] = section.order
    lang_ctx["section_enabled"] = section_enabled
    lang_ctx["section_order"] = section_order
    lang_ctx["show_designer_section"] = section_enabled.get("designer", True)
    lang_ctx["quote_document"] = quote_document.model_dump(mode="json")
    lang_ctx["brochure_draft"] = quote_document.model_dump(mode="json")


def _build_compatibility_payload_from_quote_request(request_payload: Any, document: dict) -> dict[str, Any]:
    from quote_generation import BRAND_PROFILES
    quote_document = QuoteDocumentV1.model_validate(document)
    rich_content = rich_content_values(quote_document)
    itinerary = []
    for day in quote_document.itinerary.days:
        itinerary.append({
            "dayNumber": day.dayNumber,
            "destination": day.segmentCity or day.title or "Vietnam",
            "summary": day.title or (day.description[0] if day.description else ""),
            "mainInclusions": " • ".join(day.activities or day.meals) or (day.description[0] if day.description else "Private arrangements as outlined."),
            "senseOfPace": "Private paced journey",
            "dining": ", ".join(day.meals) if day.meals else "As arranged",
        })

    hotels = []
    for hotel in request_payload.service_facts.hotels:
        hotels.append({
            "destination": hotel.destination,
            "checkInDate": hotel.check_in or "",
            "checkOutDate": hotel.check_out or "",
            "hotelArrangement": hotel.intro or hotel.name or f"Selected stay in {hotel.destination or 'Vietnam'}",
        })
    if not hotels:
        for hotel in quote_document.stays.hotels:
            hotels.append({
                "destination": hotel.city,
                "checkInDate": hotel.hotelDate.split(" - ")[0] if " - " in hotel.hotelDate else "",
                "checkOutDate": hotel.hotelDate.split(" - ")[1] if " - " in hotel.hotelDate else "",
                "hotelArrangement": hotel.introduction or hotel.name,
            })

    booking_item_map = {str(item["label"]).strip().lower(): str(item["body"]) for item in rich_content["bookingItems"]}
    pricing_options = request_payload.pricing_facts.options
    first_pricing_option = pricing_options[0] if pricing_options else None
    currency = first_pricing_option.currency if first_pricing_option else "USD"
    currency_divisor = 1 if currency == "VND" else 100
    total_budget = (first_pricing_option.group_total_amount_minor / currency_divisor) if first_pricing_option else 0.0
    return {
        "quotationNarrative": "\n".join(filter(None, [
            quote_document.trip.lede,
            quote_document.narrative.letterIntro,
            quote_document.narrative.letterBody2,
            quote_document.narrative.letterOutro,
        ])),
        "programOverview": {
            "heading": "PROGRAM OVERVIEW",
            "paragraphs": [item for item in [
                quote_document.trip.lede,
                quote_document.narrative.letterIntro,
                quote_document.narrative.letterBody2,
            ] if item],
        },
        "landingpageContent": {
            "heroSection": {
                "headline": quote_document.trip.title or "Vietnam Private Journey",
                "subtitle": quote_document.trip.title or "Vietnam Private Journey",
            },
            "visualDescription": quote_document.brand.name or "Luxury travel brochure",
        },
        "journeyGlance": {
            "market": request_payload.customer_facts.market or quote_document.traveler.nationality or "International",
            "guestProfile": quote_document.traveler.guestProfile or "Private guests",
            "hotelStandard": "Luxury",
            "mealPreference": "As arranged",
            "priceType": "Indicative",
            "tourCode": request_payload.opportunity_id or quote_document.trip.quotationNumber or quote_document.meta.quotationId,
            "domesticFlights": "On request",
            "partnerNote": BRAND_PROFILES.get(quote_document.meta.brandId, BRAND_PROFILES["vietnam_safar"]).content_policy.tone,
            "validity": "Subject to final confirmation and availability.",
        },
        "whyWorks": {
            "privateFlexible": "Private pacing and curated service remain central throughout the journey.",
            "comfort": "Selected stays, private transfers, and considered transitions are built into the experience.",
            "muslimFriendly": "Guest preferences and service details can be tailored during final confirmation.",
            "balancedHighlights": "The route balances signature moments with quieter pauses and comfortable movement.",
        },
        "itinerary": itinerary,
        "hotelPlan": {
            "hotels": hotels,
            "roomNotes": quote_document.stays.roomNotes or "",
        },
        "optionalEnhancements": [],
        "bookingTerms": {
            "deposit": booking_item_map.get("deposit") or "As per standard booking policy.",
            "balance": booking_item_map.get("balance") or "Payable prior to tour commencement.",
            "cancellation": booking_item_map.get("cancellation") or "Subject to cancellation charges as per terms.",
            "confirmation": booking_item_map.get("confirmation") or "Subject to availability upon payment.",
        },
        "pricing": {
            "currency": currency,
            "pricingTitle": "PRICE QUOTATION – INDICATIVE",
            "priceOptions": [
                {
                    "label": option.label or f"Option {index:02d}",
                    "notes": "",
                    "amount": (option.groupTotalAmountMinor / (1 if option.currency == "VND" else 100)) if option.groupTotalAmountMinor else None,
                }
                for index, option in enumerate(quote_document.pricing.options, 1)
            ] or [{
                "label": "Option 01",
                "notes": "",
                "amount": None,
            }],
            "subtotal": total_budget or None,
            "discountTotal": None,
            "taxTotal": None,
            "grandTotal": total_budget or None,
        },
        "retrievalStatus": {
            "hotel": "pending",
            "activity": "pending",
            "guide": "pending",
            "transfer": "pending",
            "flight": "pending",
        },
        "candidateBlocks": [],
        "inclusions": rich_content["inclusions"],
        "exclusions": rich_content["exclusions"],
        "quotationNumber": request_payload.opportunity_id or quote_document.trip.quotationNumber or quote_document.meta.quotationId,
    }
