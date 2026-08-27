"""Multi-brand configurations, constants, and helper utilities."""

import copy
import json
from typing import Any, Optional
from fastapi import Request
from quote_document import QuoteDocumentV1

BRAND_OWNED_CTX_FIELDS = frozenset({
    "seller_name",
    "seller_email",
    "contact",
    "contact_phone",
    "contact_web",
})

BRAND_OWNED_EDITABLE_FIELDS = frozenset({
    "seller_name",
    "seller_name2",
    "seller_email",
    "contact",
    "contact_phone",
    "contact_web",
})

BRANDS: dict[str, dict[str, Any]] = {
    "vietnam_safar": {
        "id": "vietnam_safar",
        "name": "Vietnam Safar",
        "domain": "journeys.vietnamsafar.vn",
        "logo": "/assets/brands/vietnam_safar.png",
        "color_primary": "#17412e",
        "color_primary_dark": "#0e2f22",
        "color_accent": "#b7894b",
        "color_accent_light": "#d8bd85",
        "font_serif": "Cormorant Garamond",
        "font_sans": "Montserrat",
        "font_accent": "Allura",
        "boilerplate": {
            "inclusions": [
                "Private airport transfers and arrival assistance",
                "Private transportation in air-conditioned vehicles",
                "English-speaking guides for the experiences described in the itinerary",
                "Accommodation and meal arrangements listed in the confirmed program",
                "Entrance fees and curated experiences specified in the quotation",
            ],
            "exclusions": [
                "International and domestic flights unless expressly listed",
                "Travel insurance, visas, and personal documentation costs",
                "Personal expenses, minibar, laundry, and incidental charges",
                "Optional activities and meals not specified in the quotation",
                "Tips and gratuities for guides, drivers, and hotel staff",
            ],
            "booking_terms": {
                "description": "Commercial terms are prepared for a private journey proposal and remain subject to supplier confirmation and availability.",
                "items": [
                    {"key": "deposit", "label": "Deposit", "body": "A deposit is required to secure the proposed arrangements and supplier reservations."},
                    {"key": "balance", "label": "Balance Settlement", "body": "The remaining balance is payable before arrival according to the confirmed payment schedule."},
                    {"key": "cancellation", "label": "Cancellation Policy", "body": "Cancellation charges follow the terms of the confirmed hotels, cruises, transport providers, and experience partners."},
                ],
            },
        },
    },
    "capella_travel": {
        "id": "capella_travel",
        "name": "Capella Travel",
        "domain": "journeys.capellatravel.com",
        "logo": "/assets/brands/capella_travel.png",
        "color_primary": "#CBA135",
        "color_primary_dark": "#B7894B",
        "color_accent": "#333333",
        "color_accent_light": "#4F4F4F",
        "font_serif": "Cormorant Garamond",
        "font_sans": "Montserrat",
        "font_accent": "Cormorant Garamond",
        "boilerplate": {
            "inclusions": [
                "Private arrival assistance and premium airport transfers",
                "Private chauffeured transportation throughout confirmed touring days",
                "Specialist English-speaking guides for curated experiences",
                "Selected accommodation and daily breakfast as specified in the program",
                "Entrance fees, reservations, and hosted experiences listed in the quotation",
            ],
            "exclusions": [
                "International airfare and domestic flights unless specifically included",
                "Travel insurance, visa fees, and personal documentation expenses",
                "Personal spending, minibar, spa, laundry, and hotel incidentals",
                "Meals, drinks, and experiences not expressly listed as included",
                "Gratuities and discretionary tips for guides, drivers, and hotel teams",
            ],
            "booking_terms": {
                "description": "Indicative pricing is presented for private review and remains subject to final supplier confirmation at the time of booking.",
                "items": [
                    {"key": "deposit", "label": "Deposit", "body": "A deposit is required to confirm supplier space and begin final booking arrangements."},
                    {"key": "balance", "label": "Balance Settlement", "body": "The balance is due before travel, with the exact settlement date confirmed in the final invoice."},
                    {"key": "cancellation", "label": "Cancellation Policy", "body": "Cancellation terms vary by confirmed supplier and will be governed by the final booking conditions."},
                ],
            },
        },
    },
    "selvara": {
        "id": "selvara",
        "name": "Selvara Journeys",
        "domain": "my.selvarajourneys.com",
        "logo": "/assets/brands/selvara.svg",
        "color_primary": "#A98338",
        "color_primary_dark": "#8C6A29",
        "color_accent": "#4F5D4E",
        "color_accent_light": "#6B7A6A",
        "font_serif": "Cormorant Garamond",
        "font_sans": "Jost",
        "font_accent": "Cormorant Garamond",
        "boilerplate": {
            "inclusions": [
                "Private transfers and hosted arrival coordination",
                "Private transport for confirmed journey segments",
                "Local expert guiding for the experiences included in the program",
                "Accommodation and breakfast arrangements listed in the itinerary",
                "Curated activities, entrance fees, and supplier reservations specified in the quotation",
            ],
            "exclusions": [
                "International flights and domestic air sectors unless expressly included",
                "Travel insurance, visa services, and personal documents",
                "Personal expenses, laundry, minibar, and incidental hotel charges",
                "Optional wellness, dining, or experience upgrades not listed in the program",
                "Tips and discretionary gratuities",
            ],
            "booking_terms": {
                "description": "This private journey proposal is indicative and subject to final booking confirmation, supplier space, and seasonal availability.",
                "items": [
                    {"key": "deposit", "label": "Deposit", "body": "A deposit secures the journey proposal and allows confirmed supplier arrangements to proceed."},
                    {"key": "balance", "label": "Balance Settlement", "body": "Final balance is payable before the journey begins according to the confirmed invoice timeline."},
                    {"key": "cancellation", "label": "Cancellation Policy", "body": "Cancellation fees are based on the final confirmed supplier terms and the timing of cancellation."},
                ],
            },
        },
    },
}

BRAND_LOGO_ASSETS = {
    brand_cfg.get("logo")
    for brand_cfg in BRANDS.values()
    if brand_cfg.get("logo")
}

LEGACY_BRAND_PLACEHOLDER_ASSETS = frozenset({
    "/assets/vietnam-safar-logo.png",
})


def _is_brand_placeholder_image(image_url: str | None) -> bool:
    return bool(image_url) and (
        image_url in BRAND_LOGO_ASSETS
        or image_url in LEGACY_BRAND_PLACEHOLDER_ASSETS
    )


def resolve_brand(request: Optional[Request], payload_dict: dict = None) -> dict:
    """Resolve brand based on query param, seller name, or content match."""
    brand_id = None
    if request is not None:
        try:
            brand_id = request.query_params.get("brand")
        except AttributeError:
            pass
    if brand_id and brand_id in BRANDS:
        return BRANDS[brand_id]

    if payload_dict:
        seller = payload_dict.get("seller") or {}
        comp_name = seller.get("companyName", "").lower() if isinstance(seller, dict) else ""
        if "capella" in comp_name:
            return BRANDS["capella_travel"]
        elif "selvara" in comp_name:
            return BRANDS["selvara"]

        try:
            payload_str = json.dumps(payload_dict).lower()
            if "capella" in payload_str:
                return BRANDS["capella_travel"]
            elif "selvara" in payload_str:
                return BRANDS["selvara"]
        except Exception:
            pass

    return BRANDS["vietnam_safar"]


def get_brand_boilerplate(brand_id: str | None) -> dict[str, Any]:
    """Return brand-owned brochure boilerplate without exposing shared config state."""
    brand = BRANDS.get(brand_id or "") or BRANDS["vietnam_safar"]
    fallback = BRANDS["vietnam_safar"].get("boilerplate") or {}
    boilerplate = brand.get("boilerplate") or fallback
    return copy.deepcopy(boilerplate)


def _capture_brand_owned_fields(lang_ctx: dict) -> dict:
    return {
        key: lang_ctx.get(key)
        for key in BRAND_OWNED_CTX_FIELDS
    }


def _restore_brand_owned_fields(lang_ctx: dict, brand_owned_fields: dict):
    for key, value in (brand_owned_fields or {}).items():
        if value:
            lang_ctx[key] = value


def _is_brand_switched(ctx_data: dict, brand_config: dict) -> bool:
    stored_brand = ctx_data.get("brand") if isinstance(ctx_data, dict) else {}
    stored_brand_id = stored_brand.get("id") if isinstance(stored_brand, dict) else None
    requested_brand_id = (brand_config or {}).get("id")
    return bool(stored_brand_id and requested_brand_id and stored_brand_id != requested_brand_id)


def _default_brand_logo(brand_config: dict | None) -> str:
    return (brand_config or {}).get("logo") or "/assets/vietnam-safar-logo.png"


def _brand_config_from_quote_document(document: dict) -> dict:
    quote_document = QuoteDocumentV1.model_validate(document)
    brand_id = quote_document.meta.brandId or "vietnam_safar"
    base_brand = copy.deepcopy(BRANDS.get(brand_id) or BRANDS["vietnam_safar"])
    base_brand.update({
        "id": brand_id,
        "name": quote_document.brand.name or base_brand.get("name"),
        "domain": quote_document.brand.domain or base_brand.get("domain"),
        "logo": quote_document.brand.logo.url or base_brand.get("logo"),
        "color_primary": quote_document.brand.colors.get("primary") or base_brand.get("color_primary"),
        "color_primary_dark": quote_document.brand.colors.get("primaryDark") or base_brand.get("color_primary_dark"),
        "color_accent": quote_document.brand.colors.get("accent") or base_brand.get("color_accent"),
        "color_accent_light": quote_document.brand.colors.get("accentLight") or base_brand.get("color_accent_light"),
        "color_bg_main": quote_document.brand.colors.get("bgMain") or base_brand.get("color_bg_main"),
        "color_bg_alt": quote_document.brand.colors.get("bgAlt") or base_brand.get("color_bg_alt"),
        "color_text_main": quote_document.brand.colors.get("textMain") or base_brand.get("color_text_main"),
        "color_text_muted": quote_document.brand.colors.get("textMuted") or base_brand.get("color_text_muted"),
        "color_text_light": quote_document.brand.colors.get("textLight") or base_brand.get("color_text_light"),
        "font_serif": quote_document.brand.fonts.get("serif") or base_brand.get("font_serif"),
        "font_sans": quote_document.brand.fonts.get("sans") or base_brand.get("font_sans"),
        "font_accent": quote_document.brand.fonts.get("accent") or base_brand.get("font_accent"),
    })
    return base_brand
