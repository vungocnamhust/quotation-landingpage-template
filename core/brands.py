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
