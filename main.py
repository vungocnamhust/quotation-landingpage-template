import uuid
import json
import logging
import os
import asyncio
import copy
import re
import html
import socket
import secrets
from functools import partial
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Request, HTTPException, UploadFile, File, Form, Path
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from markupsafe import Markup, escape
from pydantic import BaseModel, ConfigDict, ValidationError, Field, field_validator, model_validator
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from typing import Annotated, Any, List, Optional, Literal
from datetime import date, datetime, timezone
from github_publish import publish_to_github, publish_file_to_github
from image_selector import select_landing_image
from destination_profiles import DESTINATION_PROFILES, get_profile, get_layout_images_for_destination, get_available_images_for_destination, SOFT_TRANSITIONS
from destination_catalog_seed import BASELINE_DESTINATION_COORDINATES
from quote_document import (
    BrandContentPolicy,
    BrandProfile,
    CreateQuoteRequestV1,
    QuoteDocumentV1,
    SECTION_REGISTRY,
    rich_content_values,
    validate_quote_document_sections,
)
from quote_document_adapter import (
    apply_quote_document_to_lang_ctx,
    build_quote_document_from_lang_ctx,
    normalize_quote_document,
)
from editable_brochure_contract import (
    editable_contract_payload,
    design_identity_field, is_design_copy_field,
    is_fact_media_field, media_slot_descriptor, expand_media_slot_field_ids,
    is_gallery_field,
)
from quote_generation import (
    BRAND_PROFILES,
    QuoteGenerationService,
)
from db.session import get_session_factory
from repositories import (
    BrandRepository,
    ContentDraftRepository,
    DocumentRevisionConflictError,
    PublicationRepository,
    PublicationTargetRepository,
    QuotationDocumentRepository,
    QuotationRepository,
    QuotationVersionImpactRepository,
)
from services.facts_resolver import FactsResolutionError, FactsResolver
from services.facts_contract import normalize_legacy_facts_snapshot
from services.quotation_intake_policy import quotation_intake_missing_inputs
from services.skeleton_builder import SkeletonBuilder
from services.content_draft_service import ContentDraftService
from services.content_registry import content_owned_targets, content_registry_payload, content_editor_state_payload, content_registry_for_document_payload
from services.section_content_generator import ContentGenerationError
from services.content_readiness_service import resolve_content_readiness
from services.media_service import MediaService
from services.storage.local_media_storage import LocalMediaStorage
from services.storage.r2_storage import R2Storage, R2StorageConfigurationError
from services.media_library_service import MediaLibraryService, is_allowed_prefix, normalize_library_prefix
from services.media_default_service import MediaDefaultService
from services.media_locations import accommodation_asset_location, accommodation_location, destination_default_media_prefix, destination_location, storage_slug, team_location
from repositories.destination_repository import DestinationRepository
from repositories.media_library_repository import MediaLibraryRepository
from repositories.travel_designer_repository import TravelDesignerRepository
from repositories.accommodation_repository import AccommodationRepository
from core.auth import Principal, require_editor, require_editor_or_service, require_quote_admin
from api.dependencies import (
    DbSessionDep,
    EditorOrServicePrincipalDep,
    EditorPrincipalDep,
    OwnedV2QuotationDep,
    QuoteAdminPrincipalDep,
    configure_session_factory_provider,
    get_active_travel_designer,
    require_owned_v2_quotation,
)
from api.runtime import configure_v2_runtime
from schemas.v2.media import MediaSelectionRequest, MediaSyncRequest
from services.publication_runtime import (
    purge_public_urls as _purge_public_url,
    release_transition_cache_urls as _publication_release_transition_cache_urls,
    render_react_pdf_bytes as _render_react_pdf_bytes,
)
from routers.health import router as health_router
from routers.travel_styles import router as travel_styles_router
from routers.v2.quotation_options import router as quotation_options_router
from routers.v2.media import router as legacy_media_router
from routers.v2.workspace import router as workspace_router
from routers.v2.quotation_facts import router as quotation_facts_router
from routers.v2.quotation_document import router as quotation_document_router
from routers.v2.quotation_versions import router as quotation_versions_router
from routers.v2.content_actions import router as content_actions_router
from routers.v2.fast_track import router as fast_track_router
from routers.v2.destinations import router as destinations_router
from routers.v2.accommodations import router as accommodations_router
from routers.v2.travel_designers import router as travel_designers_router
from routers.v2.partners import router as partners_router
from routers.v2.suppliers import router as suppliers_router
from routers.v2.products import router as products_router
from routers.v2.quote_requests import router as quote_requests_router
from routers.v2.rooming_heuristics import router as rooming_heuristics_router
from routers.v1.translations import router as translations_router
from routers.public_brochure import router as public_brochure_router
from notification.api.v2.notifications import router as notifications_v2_router
from notification.api.v2.events import router as events_v2_router
from notification.api.v2.stream import router as stream_v2_router


from core.config import settings

if os.getenv("ENVIRONMENT", "local").strip().lower() in {"local", "development", "dev"} and os.path.exists(".env.local"):
    load_dotenv(".env.local", override=True)
load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("quotation")

V2_RENDERER_NAME = "quote-generator"


class FactsMediaRequest(BaseModel):
    baseRevision: int
    slots: list[dict[str, Any]] = Field(default_factory=list)


class FactsDesignerRequest(BaseModel):
    baseRevision: int
    designerProfileId: str

from core.brands import (
    BRAND_LOGO_ASSETS,
    BRAND_OWNED_CTX_FIELDS,
    BRAND_OWNED_EDITABLE_FIELDS,
    BRANDS,
    LEGACY_BRAND_PLACEHOLDER_ASSETS,
    _brand_config_from_quote_document,
    _capture_brand_owned_fields,
    _default_brand_logo,
    _is_brand_placeholder_image,
    _is_brand_switched,
    _restore_brand_owned_fields,
    resolve_brand,
)
from core.constants.coordinates import SLUG_COORDS
from core.constants.day_templates import LUXURY_DAY_TEMPLATES, get_luxury_day_title
from core.i18n import STATIC_DICTIONARY
from schemas.brand_contract import (
    BrandRenderProfileContract,
    _brand_generation_profile,
    _contrast_ratio,
    _relative_luminance,
    _require_active_v2_brand,
    _serialize_brand_render_profile,
)
from services.media_factory import (
    get_media_library_service as _get_media_library_service,
    get_media_service as _get_media_service,
    _media_service,
    _media_library_service,
)
from services.quotation_validation import (
    _sanitize_html_sync_payload,
    _validate_v2_copy_overrides,
    _validate_v2_identity_overrides,
    _validate_v2_media_overrides,
)
from quote_document_adapter import _build_compatibility_payload_from_quote_request


def _media_classification(item) -> str:
    value = f"{item.parent_prefix}/{item.file_name}".lower()
    return next((tag for tag in ("exterior", "interior", "room", "hero", "ornament") if tag in value), "generic")


# Compatibility exports for existing scripts/tests. New V2 handlers import
# aliases from api.dependencies rather than defining policy in this module.
_resolve_active_travel_designer = get_active_travel_designer
require_owned_quotation = require_owned_v2_quotation


def _get_db_session_factory():
    return get_session_factory()


configure_session_factory_provider(lambda: _get_db_session_factory())

app = FastAPI(title="Quotation Webhook API")
app.include_router(health_router)
app.include_router(travel_styles_router)
app.include_router(quotation_options_router)
app.include_router(legacy_media_router)
app.include_router(workspace_router)
app.include_router(quotation_facts_router)
app.include_router(quotation_document_router)
app.include_router(quotation_versions_router)
app.include_router(content_actions_router)
app.include_router(fast_track_router)
app.include_router(destinations_router)
app.include_router(accommodations_router)
app.include_router(travel_designers_router)
app.include_router(partners_router)
app.include_router(suppliers_router)
app.include_router(products_router)
app.include_router(quote_requests_router)
app.include_router(rooming_heuristics_router)
app.include_router(translations_router)

app.include_router(public_brochure_router)
app.include_router(notifications_v2_router)
app.include_router(events_v2_router)
app.include_router(stream_v2_router)


# CORS — required for ChatGPT Custom GPT Actions to reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Jinja2 templates
templates = Jinja2Templates(directory="templates")

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0",
    "Pragma": "no-cache",
    "Expires": "0"
}
no_cache_headers = NO_CACHE_HEADERS

ASSETS_ROOT = os.path.abspath("assets")

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

HTML_DIRECT_SYNC_FIELDS = (
    "tour_title",
    "kicker",
    "lede",
    "cover_kicker",
    "customer_name",
    "overview_heading",
    "guests_txt",
    "travel_dates",
    "route_txt",
    "travel_style",
    "quotation_number",
    "contact",
    "why_private",
    "why_comfort",
    "why_muslim",
    "why_balanced",
    "journey_h2",
    "journey_p",
    "journey_overview_title",
    "chapter_kicker",
    "route_map_h2",
    "route_map_p",
    "hero_footer",
    "divider_itinerary_kicker",
    "divider_itinerary_title",
    "divider_itinerary_tagline",
    "itinerary_kicker",
    "itinerary_h2",
    "itinerary_p",
    "room_notes",
    "pricing_h2",
    "pricing_p",
    "pricing_kicker",
    "price_cond_first",
    "inc_exc_h2",
    "muslim_care_text",
    "payment_kicker",
    "payment_title",
    "payment_desc",
    "payment_cta",
    "payment_label_deposit",
    "payment_label_balance",
    "payment_label_cancellation",
    "payment_label_confirmation",
    "term_deposit",
    "term_balance",
    "term_cancellation",
    "term_confirmation",
    "cta_h2",
    "designer_kicker",
    "designer_title",
    "designer_quote",
    "designer_expertise",
    "designer_experience",
    "designer_signature",
    "seller_subtitle",
    "contact_phone_btn",
    "contact_email_btn",
    "final_req_title",
    "label_prepared_for",
    "label_overview",
    "label_guests",
    "label_travel_dates",
    "label_route",
    "label_style",
    "label_ref",
    "label_contact",
    "label_nationality",
    "label_duration",
    "hero_meta_1",
    "hero_meta_2",
    "footer_text",
    "letter_greeting",
    "letter_intro",
    "letter_body_p2",
    "letter_outro",
    "letter_sign_off",
    "letter_sender",
    "letter_highlight",
    "divider_hotel_kicker",
    "divider_hotel_title",
    "divider_hotel_tagline",
    "divider_hotel_closing",
)

HTML_RICH_TEXT_FIELDS = frozenset({
    "term_deposit",
    "term_balance",
    "term_cancellation",
    "term_confirmation",
})

HTML_RICH_TEXT_PREFIXES = (
    "day_title_",
    "day_desc_",
    "day_highlights_",
    "day_note_",
    "booking_term_body_",
)

WORD_PASTE_RECOVERABLE_PREFIXES = (
    "day_desc_",
)

WORD_PASTE_TYPOGRAPHY_PREFIXES = (
    "day_desc_",
    "day_highlights_",
    "day_note_",
)


def _field_supports_rich_text(field_name: str) -> bool:
    if not field_name:
        return False
    if field_name in HTML_RICH_TEXT_FIELDS:
        return True
    return any(field_name.startswith(prefix) for prefix in HTML_RICH_TEXT_PREFIXES)


def _field_supports_word_paste_recovery(field_name: str) -> bool:
    if not field_name:
        return False
    return any(field_name.startswith(prefix) for prefix in WORD_PASTE_RECOVERABLE_PREFIXES)


def _field_supports_word_paste_typography_cleanup(field_name: str) -> bool:
    if not field_name:
        return False
    return any(field_name.startswith(prefix) for prefix in WORD_PASTE_TYPOGRAPHY_PREFIXES)



def translate_filter(text: str, lang: str = "en") -> str:
    if not text:
        return ""
    clean_text = text.strip()
    # 1. Tra từ điển tĩnh trước
    if clean_text in STATIC_DICTIONARY:
        val = STATIC_DICTIONARY[clean_text].get(lang or "en")
        if val:
            return val
    # 2. Nếu không phải tiếng Việt ("vi") mà không tìm thấy bản dịch, thực hiện bỏ dấu tiếng Việt để hiển thị không dấu
    if lang != "vi":
        import unicodedata
        s = ''.join(c for c in unicodedata.normalize('NFD', clean_text) if unicodedata.category(c) != 'Mn')
        return s.replace('Đ', 'D').replace('đ', 'd')
    return clean_text

templates.env.filters["translate"] = translate_filter


ARABIC_PLACE_NAME_ALIASES = {
    "مدينة هو تشي منه": "Ho Chi Minh City",
    "هو تشي منه": "Ho Chi Minh City",
    "سايغون": "Ho Chi Minh City",
    "خليج ها لونغ": "Halong Bay",
    "خليج هالونج": "Halong Bay",
    "ها لونغ": "Halong",
    "هالونغ": "Halong",
    "دا نانغ": "Da Nang",
    "دانانغ": "Da Nang",
    "هوي آن": "Hoi An",
    "هوي ان": "Hoi An",
    "دالات": "Dalat",
    "سابا": "Sapa",
    "هانوي": "Hanoi",
    "هانوى": "Hanoi",
    "نينه بينه": "Ninh Binh",
    "دلتا ميكونغ": "Mekong Delta",
    "نها ترانغ": "Nha Trang",
    "نها ترانج": "Nha Trang",
    "سوق دونغ سوان": "Dong Xuan Market",
    "تام كوك": "Tam Coc",
    "هانغ موا": "Hang Mua",
    "قمة فانسيبان": "Fansipan",
    "فانسيبان": "Fansipan",
    "قرية كات كات": "Cat Cat Village",
    "كات كات": "Cat Cat",
    "لاو تشاي": "Lao Chai",
    "تا فان": "Ta Van",
    "با نا هيلز": "Ba Na Hills",
    "غابة جوز الهند باي ماو": "Bay Mau Coconut Forest",
    "هوا فو ثانه": "Hoa Phu Thanh",
    "لانغ بيانغ": "Lang Biang",
    "شلال داتانلا": "Datanla Waterfall",
    "مقهى مي لينه": "Me Linh Coffee",
    "أنفاق كو تشي": "Cu Chi Tunnels",
    "كو تشي": "Cu Chi",
    "سوق بن ثانه": "Ben Thanh Market",
    "مطار تان سون نهات": "Tan Son Nhat Airport",
    "ميناسي بريميوم": "Minasi Premium Hotel",
    "فندق ميناسي بريميوم": "Minasi Premium Hotel",
    "لا كاستا كروز": "La Casta Cruise",
    "فندق بورا": "Bora Hotel",
    "مينه توان صافي أوشن": "Minh Toan SAFI Ocean Hotel",
    "فندق مينه توان صافي أوشن": "Minh Toan SAFI Ocean Hotel",
    "سيسيليا روج دالات": "CICILIA Rouge Dalat",
    "فندق سيسيليا روج دالات": "CICILIA Rouge Dalat",
    "سيسيليا سايغون سنتر": "Cicilia Saigon Center",
    "فندق سيسيليا سايغون سنتر": "Cicilia Saigon Center",
}

ARABIC_CANONICAL_LTR_PHRASES = tuple(sorted({
    *ARABIC_PLACE_NAME_ALIASES.values(),
    "Silver Waterfall",
    "Egg Coffee",
    "Train Street Coffee",
    "Moana Coffee",
    "Han River Cruise",
    "Crazy House",
    "Clay Tunnel",
    "Fresh Garden",
    "Elephant Waterfall",
    "Apartment Coffee",
    "Central Post Office",
    "Hoi An Ancient Town",
    "Vietnam Safar",
    "Discovery Asia Travel Group",
    "B2B",
    "USD",
    "E-visa",
    "SIM",
    "Fast Track",
    "WhatsApp",
}, key=len, reverse=True))

ARABIC_LTR_PATTERNS = (
    re.compile(r"\b(?:QT|VS)-[A-Z0-9-]+\b"),
    re.compile(r"\+?\d[\d\s().-]{6,}\d"),
    re.compile(r"\b(?:https?://|www\.)[^\s<]+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}\s+[A-Za-z]+\s+[–-]\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}\b"),
    re.compile(r"\b\d[\d,]*(?:\.\d+)?\s*(?:USD|دولار أمريكي)\b"),
)


def canonicalize_place_names_in_text(text: str, lang: str = "en") -> str:
    if not text or lang != "ar":
        return text
    normalized = text
    for source, canonical in sorted(ARABIC_PLACE_NAME_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        normalized = normalized.replace(source, canonical)
    return normalized


def _ltr_span(value: str) -> str:
    return f'<span class="ltr-token">{escape(value)}</span>'


def format_arabic_mixed_content(text: str, lang: str = "en"):
    if not text:
        return ""
    if lang != "ar":
        return text

    normalized = canonicalize_place_names_in_text(text, lang)
    placeholders: dict[str, str] = {}
    placeholder_counter = 0

    def add_placeholder(raw_value: str) -> str:
        nonlocal placeholder_counter
        key = f"__LTR_TOKEN_{placeholder_counter}__"
        placeholder_counter += 1
        placeholders[key] = _ltr_span(raw_value)
        return key

    working = normalized
    for phrase in ARABIC_CANONICAL_LTR_PHRASES:
        pattern = re.compile(re.escape(phrase))
        working = pattern.sub(lambda match: add_placeholder(match.group(0)), working)

    for pattern in ARABIC_LTR_PATTERNS:
        working = pattern.sub(lambda match: add_placeholder(match.group(0)), working)

    rendered = str(escape(working))
    for key, html in placeholders.items():
        rendered = rendered.replace(key, html)
    return Markup(rendered)


def rtl_mixed_filter(text: str, lang: str = "en"):
    return format_arabic_mixed_content(text, lang)


templates.env.filters["rtl_mixed"] = rtl_mixed_filter


def render_rich_text_filter(text: str, lang: str = "en"):
    if text is None:
        return ""
    value = _normalize_word_pasted_markup(str(text))
    if "<" not in value and ">" not in value:
        return rtl_mixed_filter(value, lang)
    return Markup(value)


templates.env.filters["render_rich_text"] = render_rich_text_filter


def format_date_filter(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        from datetime import datetime
        formats = [
            "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
            "%d/%m/%Y", "%m/%d/%Y",
            "%Y/%m/%d", "%b %d, %Y", "%d %b %Y", "%B %d, %Y",
            "%d %b %Y", "%d %B %Y"
        ]
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                break
            except ValueError:
                pass
        if dt:
            return dt.strftime("%d %b %Y")
    except Exception:
        pass
    return str(date_str)

templates.env.filters["format_date"] = format_date_filter


def format_display_date_range(checkin: str, checkout: str) -> str:
    return format_display_date_range_for_lang(checkin, checkout, "en")


def format_display_date_range_for_lang(checkin: str, checkout: str, lang: str = "en") -> str:
    try:
        from datetime import datetime
        ci = datetime.strptime(checkin, "%Y-%m-%d")
        co = datetime.strptime(checkout, "%Y-%m-%d")
        if lang == "ar":
            arabic_months = {
                1: "يناير",
                2: "فبراير",
                3: "مارس",
                4: "أبريل",
                5: "مايو",
                6: "يونيو",
                7: "يوليو",
                8: "أغسطس",
                9: "سبتمبر",
                10: "أكتوبر",
                11: "نوفمبر",
                12: "ديسمبر",
            }
            return f"{ci.day:02d} {arabic_months[ci.month]} – {co.day:02d} {arabic_months[co.month]} {co.year}"
        return f"{ci.strftime('%d %b')} – {co.strftime('%d %b %Y')}"
    except Exception:
        return f"{checkin} – {checkout}"


def format_duration_label(days_count: int, nights_count: int, lang: str = "en") -> str:
    if lang == "ar":
        return f"{days_count} يومًا / {nights_count} ليلة"
    if lang == "vi":
        return f"{days_count} ngày / {nights_count} đêm"
    return f"{days_count}D{nights_count}N"


def format_currency_display(amount: float, currency: str = "USD", lang: str = "en", *, per_person: bool = False) -> str:
    amount_text = f"{amount:,.0f}"
    if lang == "ar":
        base = f"{amount_text} دولار أمريكي" if currency == "USD" else f"{amount_text} {currency}"
        return f"{base} للشخص الواحد" if per_person else base
    base = f"{currency} {amount_text}"
    return f"{base} / person" if per_person else base


def normalize_room_note(text: str, lang: str = "en") -> str:
    if not text:
        return ""
    normalized = text.strip()
    if lang == "ar":
        mapping = {
            "Double/Twin Bed Room for 2 Adults": "غرفة مزدوجة أو بسريرين منفصلين لشخصين بالغين",
            "Twin/Double Sharing": "مشاركة غرفة مزدوجة أو بسريرين منفصلين",
        }
        return mapping.get(normalized, translate_filter(normalized, lang))
    return normalized


def _extract_image_url(image_value, default_img: str = "") -> str:
    if isinstance(image_value, dict):
        return image_value.get("url") or default_img
    if isinstance(image_value, str):
        return image_value or default_img
    return default_img


def canonicalize_place_names_in_data(value, lang: str = "en"):
    if isinstance(value, str):
        return canonicalize_place_names_in_text(value, lang)
    if isinstance(value, list):
        return [canonicalize_place_names_in_data(item, lang) for item in value]
    if isinstance(value, dict):
        return {key: canonicalize_place_names_in_data(item, lang) for key, item in value.items()}
    return value


def localize_place_name(text: str, lang: str = "en") -> str:
    if not text:
        return ""
    slug = _normalize_location_slug(text)
    canonical_by_slug = {
        "ha-noi": "Hanoi",
        "quang-ninh": "Halong Bay",
        "lao-cai": "Sapa",
        "da-nang": "Da Nang",
        "quang-nam": "Hoi An",
        "lam-dong": "Dalat",
        "ninh-binh": "Ninh Binh",
        "ho-chi-minh": "Ho Chi Minh City",
        "mekong": "Mekong Delta",
        "khanh-hoa": "Nha Trang",
    }
    if slug:
        canonical_name = canonical_by_slug.get(slug)
        if canonical_name:
            return translate_filter(canonical_name, lang)

    return translate_filter(text, lang)

async def translate_payload_llm(payload_dict: dict, target_lang: str, payload_type: str = "quotation", baseline_lang: str = "en") -> dict:
    """
    Translates all translatable string values in a payload dictionary to target_lang
    using a single batch LLM request with high-end luxury copywriting tone.
    """
    import copy
    import json
    import re
    from pydantic_ai import Agent
    import llm_client

    def is_translatable(key: str, val: str) -> bool:
        if not isinstance(val, str):
            return False
        val_clean = val.strip()
        if len(val_clean) <= 2:
            return False
        if re.match(r"^\d{4}-\d{2}-\d{2}$", val_clean):
            return False
        if val_clean.startswith("QT-") or val_clean.startswith("VS-"):
            return False
        # Ignore strictly technical or numeric keys or literal status options
        ignored_keys = {
            "currency", "priceType", "status", "startDate", "endDate", 
            "checkInDate", "checkOutDate", "block_id", "service_type",
            "hotel", "activity", "guide", "transfer", "flight"
        }
        if key in ignored_keys:
            return False
        # Also ignore literal values for status fields
        if val_clean in {"pending", "not_required"}:
            return False
        return True

    def _extract(data: any, path: str = "") -> list[tuple[str, str]]:
        extracted = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k in {"retrievalStatus", "candidateBlocks"}:
                    continue
                current_path = f"{path}.{k}" if path else k
                if isinstance(v, str) and is_translatable(k, v):
                    extracted.append((current_path, v))
                elif isinstance(v, (dict, list)):
                    extracted.extend(_extract(v, current_path))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                if isinstance(item, str) and is_translatable("", item):
                    extracted.append((current_path, item))
                elif isinstance(item, (dict, list)):
                    extracted.extend(_extract(item, current_path))
        return extracted

    def _inject(data: any, trans_map: dict[str, str], path: str = ""):
        if isinstance(data, dict):
            for k, v in data.items():
                current_path = f"{path}.{k}" if path else k
                if isinstance(v, str) and current_path in trans_map:
                    data[k] = trans_map[current_path]
                elif isinstance(v, (dict, list)):
                    _inject(v, trans_map, current_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                if isinstance(item, str) and current_path in trans_map:
                    data[i] = trans_map[current_path]
                elif isinstance(item, (dict, list)):
                    _inject(item, trans_map, current_path)

    def _normalize_digits(text: str) -> str:
        table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        return text.translate(table)

    def _extract_numeric_tokens(text: str) -> list[str]:
        return re.findall(r"\d+(?:[.,]\d+)?", _normalize_digits(text or ""))

    # Clone the dictionary to avoid side effects
    working_dict = copy.deepcopy(payload_dict)
    all_pairs = _extract(working_dict)
    if not all_pairs:
        return working_dict

    # Check against STATIC_DICTIONARY first to save LLM tokens
    pairs_to_translate = []
    local_translations = {}
    
    for path, val in all_pairs:
        clean_val = val.strip()
        if clean_val in STATIC_DICTIONARY and target_lang in STATIC_DICTIONARY[clean_val]:
            local_translations[path] = STATIC_DICTIONARY[clean_val][target_lang]
        else:
            pairs_to_translate.append((path, val))

    # If all items are pre-translated, we can skip the LLM call entirely!
    if not pairs_to_translate:
        _inject(working_dict, local_translations)
        return working_dict

    # Prepare batch prompt
    flat_texts = [p[1] for p in pairs_to_translate]
    
    # Extract some context if available
    tour_title = ""
    if "landingpageContent" in payload_dict:
        tour_title = payload_dict["landingpageContent"].get("heroSection", {}).get("subtitle", "")
    elif "title" in payload_dict:
        tour_title = payload_dict.get("title", "")

    guest_profile = payload_dict.get("journeyGlance", {}).get("guestProfile", "") or payload_dict.get("preparedFor", "")

    target_lang_name = {
        "en": "English",
        "vi": "Vietnamese (Tiếng Việt)",
        "ar": "Arabic (العربية)"
    }.get(target_lang, target_lang.upper())

    # Build prompt
    prompt = (
        f"Translate the following list of luxury travel text strings into {target_lang_name}.\n\n"
        f"CONTEXT OF THE TOUR:\n"
        f"- Tour Title: {tour_title}\n"
        f"- Travelers: {guest_profile}\n\n"
        f"INPUT TEXTS TO TRANSLATE:\n"
        + json.dumps(flat_texts, ensure_ascii=False, indent=2)
    )

    system_prompt = (
        "You are an expert multilingual Luxury Travel Copywritter with faithful translator.\n"
        f"Your task is to translate the given list of travel text strings into {target_lang_name}.\n\n"
        "RULES FOR PREMIUM & LUXURY TRANSLATION:\n"
        "1. Tone and vocabulary:\n"
        "   - English ('en'): polished, elegant, but fact-faithful.\n"
        "   - Vietnamese ('vi'): natural, polished, but fact-faithful.\n"
        "   - Arabic ('ar'): polished Modern Standard Arabic, but fact-faithful.\n"
        "2. Fidelity is mandatory:\n"
        "   - Do NOT add meals, activities, shopping, romance, welcome experiences, or travel logic not present in the source string.\n"
        "   - Do NOT change route order, destination sequence, proper nouns, dates, quantities, or prices.\n"
        "   - If the source string is operational or factual, keep it operational and factual.\n"
        "   - You may improve fluency, but not meaning.\n"
        "2. Format requirements:\n"
        "   - You MUST return a valid JSON array of strings containing the translations in the EXACT SAME order and quantity.\n"
        "   - Do NOT omit any strings. Do NOT combine strings.\n"
        "   - Output ONLY the raw JSON list of strings. Do NOT wrap it in markdown block fences like ```json. Do NOT include any chat preamble, comments, or explanations."
    )

    try:
        agent = Agent(
            model=llm_client.get_model(),
            system_prompt=system_prompt
        )
        res = await agent.run(prompt)
        res_text = res.output.strip()
        
        # Strip potential markdown fences if agent returned them despite instructions
        if res_text.startswith("```"):
            lines = res_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            res_text = "\n".join(lines).strip()

        translated_list = json.loads(res_text)
        
        if not isinstance(translated_list, list) or len(translated_list) != len(flat_texts):
            log.warning("[translate_payload_llm] LLM returned invalid array size: expected %d, got %s", len(flat_texts), type(translated_list))
            return payload_dict

        # Build injection map combining local and LLM translations
        trans_map = copy.deepcopy(local_translations)
        for (path, _), trans in zip(pairs_to_translate, translated_list):
            src_numbers = _extract_numeric_tokens(_)
            tgt_numbers = _extract_numeric_tokens(trans)
            if src_numbers and src_numbers != tgt_numbers:
                log.warning("[translate_payload_llm] Numeric drift detected for %s; preserving source text", path)
                trans_map[path] = _
            else:
                trans_map[path] = trans

        _inject(working_dict, trans_map)
        return working_dict

    except Exception as exc:
        log.exception("[translate_payload_llm] Batch translation failed to %s: %s", target_lang, exc)
        return payload_dict


def _load_ctx_data(item_id: str) -> dict | None:
    """Load the single ctx.json file from memory store, disk, or GitHub in production."""
    # First check quotations memory store
    entry = quotations.get(item_id) or itineraries.get(item_id)
    if entry and entry.get("ctx"):
        return entry["ctx"]
        
    # Fetch from GitHub first if production
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        repo = os.getenv("GITHUB_REPO")
        token = os.getenv("GITHUB_TOKEN")
        if repo and token:
            import urllib.request
            try:
                url = f"https://api.github.com/repos/{repo}/contents/published/{item_id}/ctx.json"
                req = urllib.request.Request(url, headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3.raw",
                    "User-Agent": "quotation-landingpage/1.0"
                })
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    # Cache in memory
                    store = itineraries if item_id.startswith("iti_") else quotations
                    if item_id in store:
                        store[item_id]["ctx"] = data
                    else:
                        store[item_id] = {"ctx": data}
                    return data
            except Exception as ex:
                log.warning("Failed to fetch ctx.json from GitHub for %s: %s", item_id, ex)

    path = os.path.join("published", item_id, "ctx.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning("Failed to parse ctx.json for %s: %s", item_id, e)
    return None

def _load_translation_status(item_id: str, default_lang: str = "en") -> dict:
    """Reads translation status from ctx.json."""
    ctx_data = _load_ctx_data(item_id)
    if ctx_data and "translation_status" in ctx_data:
        return ctx_data["translation_status"]
    # Fallback to checking disk structure (in case migrated from older builds)
    path = os.path.join("published", item_id, "translation_status.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    ctx = {
        "baseline_lang": default_lang,
        "available_langs": [default_lang]
    }

async def _save_translation_status(item_id: str, status: dict):
    # This is a legacy helper. In the single-JSON design, we save status directly in ctx.json.
    # We still keep this helper for backward compatibility and saving legacy translation_status.json if needed.
    path = os.path.join("published", item_id, "translation_status.json")
    content = json.dumps(status, ensure_ascii=False, indent=2)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

async def _translate_item_on_demand(item_id: str, target_lang: str, is_itinerary: bool = False) -> bool:
    """
    Translates the baseline payload to target_lang on-demand.
    Updates translations dictionary inside the single ctx.json file.
    No HTML/PDF suffix files are written to disk.
    """
    if target_lang not in ("en", "vi", "ar"):
        return False
        
    ctx_data = _load_ctx_data(item_id)
    if not ctx_data:
        log.warning("[translation] ctx.json not found for %s", item_id)
        return False
        
    available_langs = ctx_data.get("available_langs", [])
    if target_lang in available_langs:
        return True
        
    baseline_payload_dict = ctx_data.get("baseline_payload")
    baseline_lang = ctx_data.get("baseline_lang", "en")
    
    if not baseline_payload_dict:
        log.warning("[translation] baseline_payload not found in ctx.json for %s", item_id)
        return False
        
    try:
        log.info("[translation] Translating %s from %s to %s via LLM...", item_id, baseline_lang, target_lang)
        translated_dict = await translate_payload_llm(baseline_payload_dict, target_lang, baseline_lang=baseline_lang)
        
        # Validate translated dict
        if is_itinerary:
            DetailItineraryPayload.model_validate(translated_dict)
        else:
            TourQuotationPayload.model_validate(translated_dict)
            
        # Update translations in ctx_data
        translations = ctx_data.get("translations", {})
        translations[target_lang] = translated_dict
        ctx_data["translations"] = translations
        
        # Update available_langs
        if target_lang not in available_langs:
            available_langs.append(target_lang)
        ctx_data["available_langs"] = available_langs
        ctx_data["translation_status"] = {
            "baseline_lang": baseline_lang,
            "available_langs": available_langs
        }
        
        # Write updated ctx.json to disk
        quo_dir = os.path.join("published", item_id)
        os.makedirs(quo_dir, exist_ok=True)
        ctx_path = os.path.join(quo_dir, "ctx.json")
        with open(ctx_path, "w", encoding="utf-8") as f:
            json.dump(ctx_data, f, ensure_ascii=False, default=str)
            
        # Update RAM stores if present
        store = itineraries if is_itinerary else quotations
        if item_id in store:
            store[item_id]["ctx"] = ctx_data
            
        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            await publish_file_to_github(
                file_path=f"published/{item_id}/ctx.json",
                html_content=json.dumps(ctx_data, ensure_ascii=False, default=str),
                commit_message=f"Update translations in ctx.json for {item_id}"
            )
            
        log.info("[translation] Successfully translated %s to %s and saved to ctx.json", item_id, target_lang)
        return True
    except Exception as e:
        log.exception("[translation] Failed to translate %s on-demand: %s", item_id, e)
        return False


# ── In-memory quotation store ─────────────────────────────────────────────────
# { quotation_id: { "payload": dict, "html": str, "status": str,
#                   "published_url": str|None, "version": int } }
quotations: dict[str, dict] = {}
itineraries: dict[str, dict] = {}

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8111")


# ── Debug middleware — logs every incoming request and response ──────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start = time.monotonic()

    # Log request headers for ALL methods
    log.debug(
        "→ REQUEST  %s %s  headers=%s",
        request.method,
        request.url,
        dict(request.headers),
    )

    if request.method in ("POST", "PUT", "PATCH"):
        body_bytes = await request.body()

        # Log raw body
        if body_bytes:
            try:
                body_json = json.loads(body_bytes)
                log.debug(
                    "→ BODY [%s %s]:\n%s",
                    request.method,
                    request.url.path,
                    json.dumps(body_json, indent=2, ensure_ascii=False),
                )
            except Exception:
                log.debug("→ BODY (non-JSON, %d bytes): %s", len(body_bytes), body_bytes[:500])
        else:
            log.warning("→ BODY is EMPTY for %s %s — possible middleware body-read issue", request.method, request.url.path)

        # Rebuild receive so FastAPI/Starlette can read the body again.
        # IMPORTANT: must handle both http.request and http.disconnect messages.
        body_consumed = False

        async def receive():
            nonlocal body_consumed
            if not body_consumed:
                body_consumed = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            # Subsequent calls return disconnect so the connection lifecycle ends cleanly
            return {"type": "http.disconnect"}

        request = Request(request.scope, receive)

    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        log.exception("← EXCEPTION after %.0fms for %s %s: %s", elapsed, request.method, request.url.path, exc)
        raise

    elapsed = (time.monotonic() - start) * 1000
    log.info(
        "← RESPONSE %s %s  status=%s  time=%.0fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


# ── V2 error envelope — preserves legacy detail while enabling actionable UI ─
def _v2_error_message(detail: Any, fallback: str) -> str:
    if isinstance(detail, str) and detail.strip():
        return detail
    if isinstance(detail, dict) and isinstance(detail.get("message"), str) and detail["message"].strip():
        return detail["message"]
    return fallback


def _v2_error_fields(detail: Any) -> list[dict[str, str]]:
    issues = detail if isinstance(detail, list) else detail.get("errors", []) if isinstance(detail, dict) else []
    result: list[dict[str, str]] = []
    for issue in issues:
        if not isinstance(issue, dict) or not isinstance(issue.get("msg"), str):
            continue
        loc = issue.get("loc")
        path = ".".join(str(part) for part in loc if part != "body") if isinstance(loc, (list, tuple)) else ""
        result.append({"path": path, "message": issue["msg"]})
    return result


def _v2_error_payload(status_code: int, detail: Any, *, request_id: str) -> dict[str, Any]:
    record = detail if isinstance(detail, dict) else {}
    if status_code == 401:
        code, category, recovery, retryable = "AUTHENTICATION_REQUIRED", "authentication", "sign-in", False
    elif status_code == 403:
        code, category, recovery, retryable = "QUOTATION_FORBIDDEN", "authorization", "sign-in", False
    elif status_code == 404:
        code, category, recovery, retryable = "RESOURCE_NOT_FOUND", "not_found", None, False
    elif status_code == 409:
        code, category, recovery, retryable = "REVISION_CONFLICT", "conflict", "reload", True
    elif status_code == 503:
        code, category, recovery, retryable = "DEPENDENCY_UNAVAILABLE", "dependency", "retry", True
    elif status_code == 422 and "review" in record:
        code, category, recovery, retryable = "REVIEW_BLOCKED", "review", "open-blockers", False
    elif status_code == 422 and "missingInputs" in record:
        code, category, recovery, retryable = "INTAKE_INCOMPLETE", "validation", "open-blockers", False
    elif status_code == 422:
        code, category, recovery, retryable = "VALIDATION_FAILED", "validation", None, False
    else:
        code, category, recovery, retryable = "REQUEST_FAILED", "server", "retry", status_code >= 500
    error: dict[str, Any] = {
        "code": code,
        "message": _v2_error_message(detail, "The quotation request could not be completed."),
        "category": category,
        "fieldErrors": _v2_error_fields(detail),
        "retryable": retryable,
        "recovery": recovery,
        "requestId": request_id,
    }
    for key in ("missingInputs", "currentRevision", "review"):
        if key in record:
            error[key] = record[key]
    return {"detail": detail, "error": error}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if not request.url.path.startswith("/api/v2/"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)
    request_id = uuid.uuid4().hex
    return JSONResponse(
        status_code=exc.status_code,
        content=_v2_error_payload(exc.status_code, exc.detail, request_id=request_id),
        headers={**(exc.headers or {}), "X-Request-ID": request_id},
    )


# ── Validation error handler — surfaces exact Pydantic field errors ──────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    log.error(
        "VALIDATION ERROR [%s %s] — %d error(s):\n%s",
        request.method,
        request.url.path,
        len(errors),
        json.dumps(errors, indent=2, default=str),
    )
    detail = json.loads(json.dumps(errors, default=str))
    if request.url.path.startswith("/api/v2/"):
        request_id = uuid.uuid4().hex
        return JSONResponse(status_code=422, content=_v2_error_payload(422, detail, request_id=request_id), headers={"X-Request-ID": request_id})
    return JSONResponse(status_code=422, content={"detail": detail, "hint": "Check the field path in each error's 'loc' to find the missing or invalid field."})


# ── Generic error handler — catches any unhandled exceptions ─────────────────
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    log.exception("UNHANDLED EXCEPTION [%s %s]", request.method, request.url.path)
    if request.url.path.startswith("/api/v2/"):
        request_id = uuid.uuid4().hex
        return JSONResponse(
            status_code=500,
            content={"detail": "The quotation service encountered an unexpected error.", "error": {"code": "INTERNAL_ERROR", "message": "The quotation service encountered an unexpected error. Retry the action or contact support with the request ID.", "category": "server", "fieldErrors": [], "retryable": True, "recovery": "retry", "requestId": request_id}},
            headers={"X-Request-ID": request_id},
        )
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ── Pydantic models — mapped 1:1 from the OpenAPI schema (v2.1.0) ───────────
# Only fields listed under `required:` in the spec are non-Optional here.

class Duration(BaseModel):
    # required: [days, nights]
    days:   int
    nights: int
    label:  Optional[str] = None


class TravelDates(BaseModel):
    # required: [startDate, endDate]
    startDate:   date
    endDate:     date
    displayText: Optional[str] = None


class GuestComposition(BaseModel):
    # required: [totalGuests]
    totalGuests:  int
    adults:       Optional[int]       = None
    children:     Optional[int]       = None
    infants:      Optional[int]       = None
    childrenAges: Optional[List[int]] = None
    displayText:  Optional[str]       = None


class Customer(BaseModel):
    # required: [name]
    name:        str
    contactName: Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    address:     Optional[str] = None
    nationality: Optional[str] = None
    market:      Optional[str] = None


class Seller(BaseModel):
    # required: [companyName]
    companyName: str
    contactName: Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    address:     Optional[str] = None
    taxCode:     Optional[str] = None
    website:     Optional[str] = None


class TextSection(BaseModel):
    # required: [paragraphs]
    paragraphs: List[str]
    heading:    Optional[str] = None


class ItineraryDay(BaseModel):
    # required: [dayNumber, title, description]
    dayNumber:          int
    title:              str
    description:        List[str]
    date:               Optional[str]        = None  # kept as str to avoid Pydantic v2 field-name shadowing
    overnight:          Optional[str]        = None
    meals:              Optional[List[str]]  = None
    destinations:       Optional[List[str]]  = None
    activities:         Optional[List[str]]  = None
    optionalActivities: Optional[List[str]]  = None
    notes:              Optional[List[str]]  = None


class MoneyAmount(BaseModel):
    # required: [amount, currency]
    amount:      float
    currency:    str
    displayText: Optional[str]  = None
    isFromPrice: Optional[bool] = None


class PriceOption(BaseModel):
    # required: [hotelCategory, pricePerPerson, totalPrice]
    hotelCategory:        str
    pricePerPerson:       MoneyAmount
    totalPrice:           MoneyAmount
    optionName:           Optional[str]       = None
    isConfirmedMainOption: Optional[bool]     = None
    isAlternativeOption:  Optional[bool]      = None
    notes:                Optional[List[str]] = None


class TourPricing(BaseModel):
    # required: [currency, priceOptions]
    currency:     str
    priceOptions: List[PriceOption]
    pricingTitle: Optional[str]   = None
    basis:        Optional[str]   = None
    totalGuests:  Optional[int]   = None
    subtotal:     Optional[float] = None
    discountTotal: Optional[float] = None
    taxTotal:     Optional[float] = None
    grandTotal:   Optional[float] = None


from quotation_schemas import TourQuotationPayload


# ── Detailed Itinerary Booking Models ───────────────────────────────────────

class BookedHotel(BaseModel):
    name: str
    star: Optional[int] = None
    addressArea: Optional[str] = None
    roomType: Optional[str] = None
    checkInDate: str
    checkOutDate: str
    nights: int
    destination: str
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    imageUrl: Optional[str] = None
    pricePerNightUsd: Optional[float] = None
    pricePerNightVnd: Optional[float] = None


class BookedActivity(BaseModel):
    activityName: str
    operator: Optional[str] = None
    date: str
    area: str
    durationHours: Optional[float] = None
    privateGroup: Optional[bool] = True
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    imageUrl: Optional[str] = None
    pricePerAdultUsd: Optional[float] = None
    pricePerChildUsd: Optional[float] = None
    totalEstimateUsd: Optional[float] = None


class BookedTransfer(BaseModel):
    transferType: str  # airport_pickup, airport_dropoff, intercity, day_trip_return
    fromLocation: str
    toLocation: str
    date: str
    vehicleRequirement: str  # e.g., 7-seat, 16-seat
    seats: Optional[int] = None
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    priceUsd: Optional[float] = None
    priceVnd: Optional[float] = None


class BookedGuide(BaseModel):
    guideName: Optional[str] = None
    language: str
    destination: str
    dates: List[str]
    days: int
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    pricePerDayUsd: Optional[float] = None
    totalEstimateUsd: Optional[float] = None


class BookedFlight(BaseModel):
    flightNumber: str
    airline: str
    date: str
    fromCity: str
    toCity: str
    departureTime: Optional[str] = None
    arrivalTime: Optional[str] = None
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    priceUsd: Optional[float] = None


class DetailItineraryPayload(BaseModel):
    quotationNumber: str
    quotationTitle: str
    tourTitle: str
    duration: Duration
    preparedFor: str
    nationality: Optional[str] = None
    travelDates: TravelDates
    guests: GuestComposition
    route: List[str]
    travelStyle: Optional[List[str]] = None
    
    # Service and itinerary lists
    notes: Optional[List[str]] = None
    seller: Optional[Seller] = None
    programOverview: Optional[TextSection] = None
    hotels: List[BookedHotel] = Field(default_factory=list)
    activities: List[BookedActivity] = Field(default_factory=list)
    transfers: List[BookedTransfer] = Field(default_factory=list)
    flights: List[BookedFlight] = Field(default_factory=list)
    guides: List[BookedGuide] = Field(default_factory=list)
    itinerary: List[ItineraryDay] = Field(default_factory=list)
    inclusions: Optional[List[str]] = None
    exclusions: Optional[List[str]] = None
    priceConditions: Optional[TextSection] = None
    pricing: Optional[TourPricing] = None
# ── Context builder (pure fn — no I/O) ───────────────────────────────────────


def truncate_text(text: Optional[str], max_chars: int) -> str:
    if not text:
        return ""
    text_str = str(text).strip()
    if len(text_str) <= max_chars:
        return text_str
    # Try to split on last space to avoid cutting words
    truncated = text_str[:max_chars].rsplit(" ", 1)[0]
    if not truncated:
        truncated = text_str[:max_chars - 3]
    return truncated.strip() + "..."


def _load_quotation_manual_override(quotation_id: str) -> dict:
    path = os.path.join("published", quotation_id, "manual_overrides.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        log.warning("Failed to load manual override for %s: %s", quotation_id, exc)
        return {}


def _lang_override(override: dict, lang: str) -> dict:
    return ((override or {}).get("langs") or {}).get(lang, {})


def _compress_route_sequence(stops: list[str]) -> list[str]:
    compressed: list[str] = []
    for stop in stops:
        if not stop:
            continue
        if not compressed or compressed[-1] != stop:
            compressed.append(stop)
    return compressed


def _build_factual_day_title(day_number: int, stops: list[str], lang: str) -> str:
    clean_stops = [truncate_text(localize_place_name(stop, lang), 40) for stop in stops if stop]
    if not clean_stops:
        clean_stops = ["Vietnam"]
    day_label = {
        "vi": f"Ngày {day_number}",
        "ar": f"اليوم {day_number}",
    }.get(lang, f"Day {day_number}")
    route = " → ".join(clean_stops)
    return f"{day_label} — {route}"


def _build_route_stop_label(day_number: int, stop: str, lang: str, *, prefix: str | None = None) -> str:
    day_label = {
        "vi": f"Ngày {day_number}",
        "ar": f"اليوم {day_number}",
    }.get(lang, f"Day {day_number}")
    localized_stop = localize_place_name(stop, lang)
    if prefix:
        return f"{day_label} — {prefix} {localized_stop}"
    return f"{day_label} — {localized_stop}"


def _build_route_stops_from_timeline(timeline_days: list[dict]) -> list[dict]:
    route_stops: list[dict] = []
    for day in timeline_days:
        day_stops = [stop for stop in (day.get("destinations") or []) if stop]
        if not day_stops and day.get("overnight"):
            day_stops = [day["overnight"]]
        first_stop = day_stops[0] if day_stops else ""
        for idx, stop in enumerate(day_stops, start=1):
            is_last = idx == len(day_stops)
            returns_to_origin = len(day_stops) > 2 and is_last and stop == first_stop
            kind = "overnight" if is_last and stop == day.get("overnight") else "visit"
            map_title = _build_route_stop_label(day["dayNumber"], stop, day.get("lang", "en"))
            show_marker = True
            if len(day_stops) > 1 and idx < len(day_stops):
                kind = "transfer" if idx == 1 else "visit"
            if idx == 1 and len(day_stops) > 1:
                prefix = {"vi": "Khởi hành từ", "ar": "الانطلاق من", "en": "Depart from"}.get(
                    day.get("lang", "en"),
                    "Depart from",
                )
                map_title = _build_route_stop_label(day["dayNumber"], stop, day.get("lang", "en"), prefix=prefix)
                show_marker = False
            elif returns_to_origin:
                prefix = {"vi": "Trở lại", "ar": "العودة إلى", "en": "Return to"}.get(
                    day.get("lang", "en"),
                    "Return to",
                )
                map_title = _build_route_stop_label(day["dayNumber"], stop, day.get("lang", "en"), prefix=prefix)
                kind = "return"
                show_marker = False
            elif len(day_stops) > 1:
                map_title = _build_route_stop_label(day["dayNumber"], stop, day.get("lang", "en"))
            localized_stop = localize_place_name(stop, day.get("lang", "en"))
            route_stops.append({
                "dayNumber": day["dayNumber"],
                "stopOrder": idx,
                "destination": stop,
                "displayName": localized_stop,
                "mapTitle": map_title,
                "kind": kind,
                "showMarker": show_marker,
            })
    return route_stops


def _format_day_range_label(day_start: int, day_end: int, lang: str) -> str:
    if day_start == day_end:
        return {
            "vi": f"Ngày {day_start}",
            "ar": f"اليوم {day_start}",
        }.get(lang, f"Day {day_start}")
    return {
        "vi": f"Ngày {day_start}-{day_end}",
        "ar": f"الأيام {day_start}-{day_end}",
    }.get(lang, f"Days {day_start}-{day_end}")


def _format_nights_label(nights: int, lang: str) -> str:
    if lang == "vi":
        return f"{nights} đêm"
    if lang == "ar":
        return f"{nights} ليالٍ" if nights != 1 else "ليلة واحدة"
    return f"{nights} night" if nights == 1 else f"{nights} nights"


def _normalize_location_slug(location: str) -> str | None:
    if not location:
        return None
    from image_selector import resolve_slug_locally
    resolved = resolve_slug_locally(location)
    if resolved:
        return resolved

    normalized = location.lower().strip()
    extra_keywords = {
        "هانوي": "ha-noi",
        "هانوى": "ha-noi",
        "مدينة هو تشي منه": "ho-chi-minh",
        "هو تشي منه": "ho-chi-minh",
        "سايغون": "ho-chi-minh",
        "دا نانغ": "da-nang",
        "دانانغ": "da-nang",
        "هوي آن": "quang-nam",
        "هوي ان": "quang-nam",
        "خليج ها لونغ": "quang-ninh",
        "خليج هالونج": "quang-ninh",
        "هالونغ": "quang-ninh",
        "سابا": "lao-cai",
        "نينه بينه": "ninh-binh",
        "نها ترانغ": "khanh-hoa",
        "نها ترانج": "khanh-hoa",
        "دالات": "lam-dong",
        "دلتا ميكونغ": "mekong",
    }
    if normalized in extra_keywords:
        return extra_keywords[normalized]
    for keyword, slug in extra_keywords.items():
        if keyword in normalized:
            return slug
    return None


def _build_stay_segments_from_timeline(
    timeline_days: list[dict],
    hotel_plan_items: list[dict],
    lang: str,
) -> list[dict]:
    stay_segments: list[dict] = []
    if not timeline_days:
        return stay_segments

    grouped_days: list[list[dict]] = []
    current_group: list[dict] = []
    current_overnight_slug = None

    for day in timeline_days:
        overnight = day.get("overnight") or (day.get("destinations") or [None])[-1]
        overnight_slug = _normalize_location_slug(overnight or "")
        if not current_group or overnight_slug == current_overnight_slug:
            current_group.append(day)
            current_overnight_slug = overnight_slug
            continue
        grouped_days.append(current_group)
        current_group = [day]
        current_overnight_slug = overnight_slug
    if current_group:
        grouped_days.append(current_group)

    hotel_cursor = 0
    for order, days in enumerate(grouped_days, start=1):
        first_day = days[0]
        last_day = days[-1]
        city = last_day.get("overnight") or (last_day.get("destinations") or [None])[-1] or "Vietnam"
        city_slug = _normalize_location_slug(city)
        display_name = localize_place_name(city, lang)

        matched_hotel = None
        for idx in range(hotel_cursor, len(hotel_plan_items)):
            hotel = hotel_plan_items[idx]
            hotel_slug = _normalize_location_slug(hotel.get("destination", ""))
            if city_slug and hotel_slug == city_slug:
                matched_hotel = hotel
                hotel_cursor = idx + 1
                break
            if not city_slug and hotel.get("destination") == city:
                matched_hotel = hotel
                hotel_cursor = idx + 1
                break
        if matched_hotel is None and hotel_cursor < len(hotel_plan_items):
            matched_hotel = hotel_plan_items[hotel_cursor]
            hotel_cursor += 1

        excursions: list[str] = []
        activity_previews: list[dict] = []
        for day in days:
            day_destinations = [dest for dest in (day.get("destinations") or []) if dest]
            excursion_candidates = day_destinations[1:-1] if len(day_destinations) > 2 else []
            for dest in excursion_candidates:
                if not dest or _normalize_location_slug(dest) == city_slug:
                    continue
                translated_dest = localize_place_name(dest, lang)
                if translated_dest not in excursions:
                    excursions.append(translated_dest)
            description = ""
            if day.get("description"):
                description = day["description"][0]
            elif day.get("activities"):
                description = day["activities"][0]
            if description:
                activity_previews.append({
                    "dayNumber": day["dayNumber"],
                    "label": {
                        "vi": f"Ngày {day['dayNumber']}",
                        "ar": f"اليوم {day['dayNumber']}",
                    }.get(lang, f"Day {day['dayNumber']}"),
                    "summary": truncate_text(description, 120),
                })

        day_start = first_day["dayNumber"]
        day_end = last_day["dayNumber"]
        nights = max(1, day_end - day_start + 1)
        stay_segments.append({
            "segmentId": f"stay-{order}",
            "order": order,
            "city": city,
            "displayName": display_name,
            "dayStart": day_start,
            "dayEnd": day_end,
            "daysLabel": _format_day_range_label(day_start, day_end, lang),
            "nights": nights,
            "nightsLabel": _format_nights_label(nights, lang),
            "hotelName": matched_hotel.get("name", "") if matched_hotel else "",
            "hotelImage": matched_hotel.get("hotel_img", "") if matched_hotel else "",
            "hotelDateRange": matched_hotel.get("date_range", "") if matched_hotel else "",
            "coords": list(SLUG_COORDS.get(city_slug, ())) if city_slug in SLUG_COORDS else None,
            "excursions": excursions,
            "activityPreviews": activity_previews,
            "transportFromPrevious": "",
        })

    for idx, segment in enumerate(stay_segments):
        if idx == 0:
            continue
        previous = stay_segments[idx - 1]
        segment["transportFromPrevious"] = f"{previous['displayName']} → {segment['displayName']}"

    return stay_segments


def _build_timeline_days(
    quotation_id: str,
    payload: "TourQuotationPayload",
    lang: str,
    manual_override: dict,
    start_date_str: str = ""
) -> list[dict]:
    from datetime import datetime, timedelta
    lang_override = _lang_override(manual_override, lang)
    day_overrides = lang_override.get("day_overrides", {})
    timeline_days: list[dict] = []

    base_date = None
    if start_date_str:
        try:
            base_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            pass

    for itinerary_day in payload.itinerary:
        override_day = day_overrides.get(str(itinerary_day.dayNumber), {})
        raw_destinations = override_day.get("destinations") or [itinerary_day.destination]
        destinations = [truncate_text(localize_place_name(dest, lang), 40) for dest in raw_destinations if dest]
        raw_overnight = override_day.get("overnight") or getattr(itinerary_day, "overnight", None) or itinerary_day.destination
        overnight = truncate_text(
            localize_place_name(raw_overnight, lang),
            40,
        )
        title = truncate_text(
            override_day.get("title") or _build_factual_day_title(itinerary_day.dayNumber, destinations, lang),
            120,
        )
        summary = canonicalize_place_names_in_text(
            truncate_text(override_day.get("summary", itinerary_day.summary), 350),
            lang,
        )
        dining = truncate_text(override_day.get("dining", itinerary_day.dining), 80)
        main_inclusions = canonicalize_place_names_in_text(
            truncate_text(
                override_day.get("mainInclusions", itinerary_day.mainInclusions),
                140,
            ),
            lang,
        )
        day_date_str = getattr(itinerary_day, "date", "") or ""
        if base_date:
            try:
                curr_date = base_date + timedelta(days=itinerary_day.dayNumber - 1)
                day_date_str = curr_date.strftime("%Y-%m-%d")
            except Exception:
                pass

        timeline_days.append({
            "dayNumber": itinerary_day.dayNumber,
            "date": day_date_str,
            "lang": lang,
            "title": title,
            "description": [summary] if summary else [],
            "overnight": overnight,
            "meals": [dining] if dining else [],
            "activities": [main_inclusions] if main_inclusions else [],
            "notes": [translate_filter(truncate_text(f"Sense of Pace: {itinerary_day.senseOfPace}", 80), lang)] if itinerary_day.senseOfPace else [],
            "destinations": destinations,
        })

    return timeline_days

def _build_itinerary_days_flat(timeline_days: list[dict], stay_segments: list[dict], lang: str, manual_override: dict = None) -> list[dict]:
    day_slugs = {}
    day_cities = {}
    for seg in stay_segments:
        city = seg.get("city", "Vietnam")
        slug = _normalize_location_slug(city) or "default"
        for day_num in range(seg["dayStart"], seg["dayEnd"] + 1):
            day_slugs[day_num] = slug
            day_cities[day_num] = seg.get("displayName") or city
            
    edited = (manual_override or {}).get("edited_fields", {})
    
    effective_day_slugs = {}
    effective_day_cities = {}
    for d in timeline_days:
        d_num = d["dayNumber"]
        d_dests = d.get("destinations") or []
        first_dest = d_dests[0] if (d_dests and d_dests[0]) else None
        if first_dest:
            d_slug = _normalize_location_slug(first_dest) or day_slugs.get(d_num, "default")
            d_city = first_dest
        else:
            d_slug = day_slugs.get(d_num, "default")
            d_city = day_cities.get(d_num, "Vietnam")
        effective_day_slugs[d_num] = d_slug
        effective_day_cities[d_num] = d_city

    # Pre-calculate random image pools partitioned across days for each destination
    import hashlib
    import random
    
    dest_day_counts = {}
    for d in timeline_days:
        d_num = d["dayNumber"]
        d_slug = effective_day_slugs.get(d_num, "default")
        dest_day_counts[d_slug] = dest_day_counts.get(d_slug, 0) + 1
        
    dest_image_pools = {}
    for d_slug in dest_day_counts:
        imgs = get_available_images_for_destination(d_slug)
        if imgs:
            seed_val = int(hashlib.md5(d_slug.encode()).hexdigest(), 16)
            rng = random.Random(seed_val)
            rng.shuffle(imgs)
        dest_image_pools[d_slug] = imgs
        
    dest_day_indices = {}
    flat_days = []
    
    for i, day_data in enumerate(timeline_days):
        day_num = day_data["dayNumber"]
        slug = effective_day_slugs.get(day_num, "default")
        city = effective_day_cities.get(day_num, "Vietnam")
        
        imgs = dest_image_pools.get(slug, [])
        day_idx = dest_day_indices.get(slug, 0)
        
        if len(imgs) > 0:
            num_days = dest_day_counts.get(slug, 1)
            num_imgs = len(imgs)
            
            # Partition imgs across days without overlap
            if num_imgs >= num_days:
                base_count = num_imgs // num_days
                extra = num_imgs % num_days
                chunk_size = base_count + (1 if day_idx < extra else 0)
                start_idx = day_idx * base_count + min(day_idx, extra)
                end_idx = start_idx + chunk_size
                day_imgs = imgs[start_idx:end_idx]
            else:
                # If there are fewer images than days, we must repeat to avoid empty images
                # but we try to give 1 image per day by repeating the pool
                day_imgs = [imgs[day_idx % num_imgs]]

            hero_img = day_imgs[0]
            carousel_imgs = day_imgs if len(day_imgs) > 1 else []
            s1_img = day_imgs[1] if len(day_imgs) > 1 else ""
            s2_img = day_imgs[2] if len(day_imgs) > 2 else ""
        else:
            hero_img = ""
            carousel_imgs = []
            s1_img = ""
            s2_img = ""
            
        dest_day_indices[slug] = day_idx + 1
        
        # Always use single layout for itinerary as requested
        layout_type = "single"


        # Train image enhancement for train journey days
        summary_text = (day_data.get("summary") or "") + " " + (day_data.get("title") or "") + " " + (day_data.get("mainInclusions") or "")
        if "train" in summary_text.lower() or "chapa" in summary_text.lower():
            train_img = "/assets/lao-cai/tau-tren-cao.webp"
            if train_img not in carousel_imgs:
                carousel_imgs.insert(0, train_img)
            if not s1_img:
                s1_img = train_img
            elif not s2_img:
                s2_img = train_img

        layout_images = {
            "hero": hero_img,
            "small-1": s1_img,
            "small-2": s2_img,
            "carousel": carousel_imgs
        }
        
        # Apply user image overrides if present
        if f"day_img_hero_{day_num}" in edited:
            layout_images["hero"] = edited[f"day_img_hero_{day_num}"]
        if f"day_img_small1_{day_num}" in edited:
            layout_images["small-1"] = edited[f"day_img_small1_{day_num}"]
        if f"day_img_small2_{day_num}" in edited:
            layout_images["small-2"] = edited[f"day_img_small2_{day_num}"]
            
        is_alternate = (i % 2 != 0)
        
        day_with_layout = {
            **day_data, 
            "layout_type": layout_type, 
            "layout_images": layout_images,
            "is_alternate": is_alternate,
            "segment_city": city
        }
        flat_days.append(day_with_layout)
        
    return flat_days

# ── Context builder (pure fn — no I/O) ───────────────────────────────────────

def _build_ctx(quotation_id, payload: "TourQuotationPayload", hero_image_url, destinations: list[dict], lang: str = "en", template_name: str = "vietnam_luxury_brosure.html", brand: dict = None):
    """Build template context. Shared by /quotations (landingpage) and /quotations/{id}/pdf."""
    default_img = _default_brand_logo(brand)
    manual_override = _load_quotation_manual_override(quotation_id)
    lang_override = _lang_override(manual_override, lang)
    
    # Defaults for seller/contact
    seller_name  = "Eddie"
    seller_subtitle = "(Trung Hieu Pham)"
    seller_email = "sales@capellatravel.com"
    seller_phone = "+84 913 393 119"
    if brand:
        if brand.get("id") == "capella_travel":
            seller_name = "Eddie"
            seller_subtitle = "(Trung Hieu Pham)"
            seller_email = "sales@capellatravel.com"
            seller_phone = "+84 913 393 119"
        elif brand.get("id") == "selvara":
            seller_name = "Selvara Journeys"
            seller_email = "sales@selvarajourneys.com"
            seller_phone = "+84 913 393 119"

    # Resolve key display strings from new Spec 36 schema
    tour_title    = truncate_text(payload.landingpageContent.heroSection.subtitle, 70)
    prepared_for  = truncate_text(payload.journeyGlance.guestProfile, 60)
    
    # Calculate duration
    days_count = len(payload.itinerary)
    nights_count = max(0, days_count - 1)
    duration_lbl  = format_duration_label(days_count, nights_count, lang)
    
    # Travel dates - fallback to hotel plan if checkInDate is available, otherwise placeholder
    travel_dates = "Flexible Dates"
    quotation_start_date = ""
    if payload.hotelPlan.hotels:
        start_date = payload.hotelPlan.hotels[0].checkInDate
        end_date = payload.hotelPlan.hotels[-1].checkOutDate
        if start_date and end_date:
            travel_dates = format_display_date_range_for_lang(start_date, end_date, lang)
            quotation_start_date = start_date
            
    guests_txt    = truncate_text(payload.journeyGlance.guestProfile, 100)
    
    timeline_days = _build_timeline_days(quotation_id, payload, lang, manual_override, start_date_str=quotation_start_date)
    route_stops = _build_route_stops_from_timeline(timeline_days)
    route_list = _compress_route_sequence([stop["displayName"] for stop in route_stops])
    route_txt = canonicalize_place_names_in_text(
        lang_override.get("route_txt") or " \u2013 ".join(route_list),
        lang,
    )
    
    nationality   = truncate_text(payload.journeyGlance.market, 60)
    travel_style  = truncate_text(payload.journeyGlance.partnerNote, 100)

    # Estimate guest count
    guests_count = 1
    import re
    m = re.search(r'(\d+)\s+adult', guests_txt, re.IGNORECASE)
    if m:
        guests_count = int(m.group(1))

    # Construct pricing context from agent custom pricing dict or default
    price_options = []
    total_price = ""
    price_per_pax = ""
    grand_total_num = 0.0
    currency = "USD"

    # Check if pricing is custom pricing context dict (from pricing engine)
    if isinstance(payload.pricing, dict) or hasattr(payload.pricing, "totalPriceUsd"):
        p_dict = payload.pricing if isinstance(payload.pricing, dict) else payload.pricing.model_dump()
        currency = p_dict.get("currency", "USD")
        grand_total_num = p_dict.get("totalPriceUsd", 0.0)
        
        price_per_person = grand_total_num / max(1, guests_count)
        
        price_per_pax = format_currency_display(price_per_person, currency, lang, per_person=True)
        total_price = format_currency_display(grand_total_num, currency, lang)
        
        price_options = [{
            "hotelCategory": truncate_text(payload.journeyGlance.hotelStandard, 80),
            "optionName": "Main confirmed option",
            "pricePerPerson": {
                "amount": price_per_person,
                "currency": currency,
                "displayText": price_per_pax,
                "isFromPrice": False
            },
            "totalPrice": {
                "amount": grand_total_num,
                "currency": currency,
                "displayText": total_price,
                "isFromPrice": False
            },
            "isConfirmedMainOption": True,
            "isAlternativeOption": False,
            "notes": ["Calculated based on actual supplier costs"]
        }]
    else:
        # Standard Pricing model
        currency = payload.pricing.currency
        for opt in payload.pricing.priceOptions:
            price_per_person_amt = opt.amount or 0.0
            total_price_amt = price_per_person_amt * guests_count
            
            p_pax_txt = format_currency_display(price_per_person_amt, currency, lang, per_person=True)
            tot_txt = format_currency_display(total_price_amt, currency, lang)
            
            cleaned_opt_notes = opt.notes
            if cleaned_opt_notes:
                import re
                pattern = r'^\s*(?:USD|EUR|INR|GBP|VND|[$€₹đ])?\s*[\d,.]+\s*(?:USD|EUR|INR|GBP|VND|[$€₹đ])?\s*(?:per person|per pax|/person|/pax)?\s+on\s+'
                cleaned_opt_notes = re.sub(pattern, '', cleaned_opt_notes, flags=re.IGNORECASE).strip()
            
            price_options.append({
                "hotelCategory": truncate_text(opt.label, 80),
                "optionName": truncate_text(cleaned_opt_notes, 150) if cleaned_opt_notes else "",
                "pricePerPerson": {
                    "amount": price_per_person_amt,
                    "currency": currency,
                    "displayText": p_pax_txt,
                    "isFromPrice": False
                },
                "totalPrice": {
                    "amount": total_price_amt,
                    "currency": currency,
                    "displayText": tot_txt,
                    "isFromPrice": False
                },
                "isConfirmedMainOption": True,
                "isAlternativeOption": False,
                "notes": [truncate_text(opt.notes, 150)] if opt.notes else []
            })
        grand_total_num = payload.pricing.grandTotal or 0.0
        total_price = format_currency_display(grand_total_num, currency, lang)

    default_inclusions = [
        {"title": "Handpicked Accommodation", "desc": "Carefully selected hotels and stays as detailed in your journey proposal."},
        {"title": "Private Transportation", "desc": "Private ground transportation and scheduled transfers throughout the journey, as specified in the itinerary."},
        {"title": "Curated Experiences", "desc": "Entrance arrangements and experiences included as outlined in your itinerary."},
        {"title": "Expert Local Guidance", "desc": "Services of carefully selected, licensed local guides where specified."},
        {"title": "Dining Experiences", "desc": "Meals and dining arrangements as detailed in the itinerary."},
        {"title": "Journey Connections", "desc": "Domestic flights, rail journeys, ferries, or other transportation included where specifically stated in the itinerary."}
    ]
    default_exclusions = [
        "International flights",
        "Visa fees and travel documentation",
        "Travel insurance",
        "Personal expenses",
        "Optional experiences not specified in the itinerary",
        "Tips and gratuities",
        "Any services not expressly listed as included"
    ]

    # Extract inclusions from itinerary day mainInclusions dynamically, unless quote override exists
    if lang_override.get("inclusions"):
        inc_lines = [canonicalize_place_names_in_text(truncate_text(x, 160), lang) for x in lang_override["inclusions"]]
    elif getattr(payload, "inclusions", None):
        inc_lines = [canonicalize_place_names_in_text(translate_filter(truncate_text(x, 160), lang), lang) for x in payload.inclusions]
    else:
        inc_lines = []
        for d in payload.itinerary:
            if d.mainInclusions and d.mainInclusions not in inc_lines:
                inc_lines.append(d.mainInclusions)
        if not inc_lines:
            inc_lines = [
                {
                    "title": translate_filter(item["title"], lang),
                    "desc": translate_filter(item["desc"], lang)
                } for item in default_inclusions
            ]
        else:
            inc_lines = [canonicalize_place_names_in_text(translate_filter(truncate_text(x, 120), lang), lang) for x in inc_lines]

    if lang_override.get("exclusions"):
        exc_lines = [canonicalize_place_names_in_text(truncate_text(x, 160), lang) for x in lang_override["exclusions"]]
    elif getattr(payload, "exclusions", None):
        exc_lines = [canonicalize_place_names_in_text(translate_filter(truncate_text(x, 160), lang), lang) for x in payload.exclusions]
    else:
        exc_lines = [canonicalize_place_names_in_text(translate_filter(truncate_text(x, 120), lang), lang) for x in default_exclusions]

    inclusions_title = translate_filter("What Your Journey Includes", lang)
    inclusions_lede = translate_filter("Your journey has been thoughtfully arranged to ensure a seamless and comfortable experience throughout.", lang)
    exclusions_title = translate_filter("Exclusions", lang)
    exclusions_lede = translate_filter("To keep your journey transparent and clearly defined, the following are not included unless specifically stated otherwise:", lang)

    # Overview paragraphs
    overview_paras = []
    if getattr(payload, "programOverview", None) and payload.programOverview.paragraphs:
        overview_paras = [canonicalize_place_names_in_text(truncate_text(p, 500), lang) for p in payload.programOverview.paragraphs]
        overview_heading = truncate_text(payload.programOverview.heading or "PROGRAM OVERVIEW", 60)
    elif payload.quotationNarrative:
        paras = [p.strip() for p in payload.quotationNarrative.split('\n') if p.strip()]
        overview_paras = [canonicalize_place_names_in_text(truncate_text(p, 500), lang) for p in paras]
        overview_heading = "PROGRAM OVERVIEW"
    
    if not overview_paras:
        overview_paras = ["A refined travel experience designed for your journey."]
        overview_heading = "PROGRAM OVERVIEW"
        
    lede = canonicalize_place_names_in_text(truncate_text(overview_paras[0], 500), lang)

    # Fallback to local parsing if destinations list is empty (e.g. offline/sandbox test)
    if not destinations and payload.itinerary:
        from image_selector import resolve_slug_locally, get_random_image_for_province, get_all_images_for_province
        seen_names = set()
        for day in payload.itinerary:
            if day.destination and day.destination not in seen_names:
                seen_names.add(day.destination)
                slug = resolve_slug_locally(day.destination)
                if slug:
                    dest_dict = {
                        "name": day.destination,
                        "slug": slug,
                        "image_url": get_random_image_for_province(slug),
                        "images": get_all_images_for_province(slug)
                    }
                    destinations.append(dest_dict)

    import os
    import random

    def _local_slug_lookup(text: str) -> str | None:
        if not text:
            return None
        normalized = str(text).strip().lower()
        slug_map = {
            "hanoi": "ha-noi", "hà nội": "ha-noi", "ha noi": "ha-noi", "hanoï": "ha-noi",
            "ninh binh": "ninh-binh", "ninh bình": "ninh-binh", "ninhbinh": "ninh-binh",
            "halong bay": "quang-ninh", "halong": "quang-ninh", "ha long": "quang-ninh", "quảng ninh": "quang-ninh", "vịnh hạ long": "quang-ninh", "vinh ha long": "quang-ninh",
            "sapa": "lao-cai", "sa pa": "lao-cai", "lào cai": "lao-cai", "lao cai": "lao-cai", "laocai": "lao-cai"
        }
        for k, v in slug_map.items():
            if k in normalized:
                return v
        return None

    def _find_real_image_for_province(slug: str, fallback_img: str = "/assets/vietnam-safar-logo.png") -> str:
        if not slug or slug == "unknown":
            return fallback_img
        folder_path = os.path.join("assets", slug)
        if os.path.isdir(folder_path):
            valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
            files = [
                f for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f)) and os.path.splitext(f)[1].lower() in valid_exts
            ]
            if files:
                return f"/assets/{slug}/{random.choice(files)}"
        return fallback_img

    def _find_all_real_images_for_province(slug: str, fallback_img: str = "/assets/vietnam-safar-logo.png") -> list[str]:
        if not slug or slug == "unknown":
            return [fallback_img]
        folder_path = os.path.join("assets", slug)
        if os.path.isdir(folder_path):
            valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
            files = sorted([
                f for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f)) and os.path.splitext(f)[1].lower() in valid_exts
            ])
            if files:
                return [f"/assets/{slug}/{f}" for f in files]
        return [fallback_img]

    translated_destinations = []
    for d in destinations:
        d_copy = d.copy()
        raw_name = d_copy.get("name", "")
        d_copy["name"] = localize_place_name(raw_name, lang)
        
        # Resolve slug for the destination
        slug = d_copy.get("slug")
        if not slug or slug == "unknown":
            slug = _local_slug_lookup(raw_name) or _local_slug_lookup(d_copy.get("name"))

        image_url = _extract_image_url(d_copy.get("image_url"), default_img)
        if _is_brand_placeholder_image(image_url):
            image_url = default_img
        raw_images = d_copy.get("images") or []
        images = [
            (
                default_img
                if _is_brand_placeholder_image(_extract_image_url(img, default_img))
                else _extract_image_url(img, default_img)
            )
            for img in raw_images
            if _extract_image_url(img, default_img)
        ]

        # If mock path or file doesn't exist, replace with real image
        if slug and slug != "unknown":
            is_mock_url = "mock-" in image_url
            file_exists = True
            if image_url.startswith("/assets/"):
                file_path = image_url.lstrip("/")
                if not os.path.exists(file_path):
                    file_exists = False
            
            if is_mock_url or not file_exists or image_url == default_img or _is_brand_placeholder_image(image_url):
                real_img = _find_real_image_for_province(slug, default_img)
                if real_img != default_img:
                    image_url = real_img

            real_images = []
            for img in images:
                is_mock = "mock-" in img
                f_exists = True
                if img.startswith("/assets/"):
                    f_path = img.lstrip("/")
                    if not os.path.exists(f_path):
                        f_exists = False
                if not is_mock and f_exists and img != default_img and not _is_brand_placeholder_image(img):
                    real_images.append(img)
            
            if not real_images:
                real_prov_imgs = _find_all_real_images_for_province(slug, default_img)
                if real_prov_imgs and real_prov_imgs[0] != default_img:
                    real_images = real_prov_imgs
            
            if not real_images:
                real_images = [image_url]
                
            images = real_images

        d_copy["image_url"] = image_url
        d_copy["images"] = images
        d_copy["slug"] = slug or "unknown"
        translated_destinations.append(d_copy)
    destinations = translated_destinations

    # Gallery helpers
    def _d_img(i): return destinations[i].get("image_url", default_img) if i < len(destinations) else default_img
    def _d_name(i): return truncate_text(destinations[i].get("name", ""), 40) if i < len(destinations) else ""

    img_0 = _extract_image_url(hero_image_url, default_img)
    if "mock-" in img_0 or (img_0.startswith("/assets/") and not os.path.exists(img_0.lstrip("/"))):
        import re
        hero_slug = None
        m = re.search(r'mock-([^./\s]+)', img_0)
        if m:
            hero_slug = _local_slug_lookup(m.group(1))
        if not hero_slug and destinations:
            hero_slug = destinations[0].get("slug")
        if hero_slug and hero_slug != "unknown":
            real_hero = _find_real_image_for_province(hero_slug, default_img)
            if real_hero != default_img:
                img_0 = real_hero

    img_1 = _d_img(0)
    img_2 = _d_img(1)
    img_3 = _d_img(2)
    img_4 = _d_img(3)

    # ── Deduplicated Chapter Divider Images ─────────────────────────────────
    used_divider_imgs = {img_0, img_1}

    # Collect all available real destination images
    all_dest_images = []
    for d in destinations:
        for im in d.get("images", []):
            if im and im != default_img and im not in all_dest_images:
                all_dest_images.append(im)
    for d in destinations:
        s = d.get("slug")
        if s:
            p_imgs = _find_all_real_images_for_province(s, default_img)
            for im in p_imgs:
                if im and im != default_img and im not in all_dest_images:
                    all_dest_images.append(im)

    # 1. Pick img_itinerary_divider (landscape hero image, prefer 2nd destination or unused image)
    img_itinerary_divider = ""
    if len(destinations) > 1 and destinations[1].get("images"):
        cand = [im for im in destinations[1]["images"] if im not in used_divider_imgs]
        if cand:
            img_itinerary_divider = cand[0]
    if not img_itinerary_divider:
        cand = [im for im in all_dest_images if im not in used_divider_imgs]
        if cand:
            img_itinerary_divider = cand[0]
        else:
            img_itinerary_divider = img_1 or img_0
    used_divider_imgs.add(img_itinerary_divider)

    # 2. Pick img_hotel_divider (sanctuary/nature hero image, prefer 3rd destination or unused image)
    img_hotel_divider = ""
    if len(destinations) > 2 and destinations[2].get("images"):
        cand = [im for im in destinations[2]["images"] if im not in used_divider_imgs]
        if cand:
            img_hotel_divider = cand[0]
    if not img_hotel_divider:
        cand = [im for im in all_dest_images if im not in used_divider_imgs]
        if cand:
            img_hotel_divider = cand[0]
        else:
            img_hotel_divider = img_2 or img_0
    used_divider_imgs.add(img_hotel_divider)

    # User edit overrides
    edited_fields = manual_override.get("edited_fields", {}) if manual_override else {}
    if edited_fields.get("img_itinerary_divider"):
        img_itinerary_divider = edited_fields["img_itinerary_divider"]
    if edited_fields.get("img_hotel_divider"):
        img_hotel_divider = edited_fields["img_hotel_divider"]

    # Highlight experiences — first 3 itinerary days
    experiences = [
        {"num": f"{i+1:02d}", "title": truncate_text(f"{translate_filter('Day', lang)} {day.dayNumber}: {localize_place_name(day.destination, lang)}", 80),
         "desc": canonicalize_place_names_in_text(truncate_text(day.summary, 160), lang)}
        for i, day in enumerate(payload.itinerary[:3])
    ]
    while len(experiences) < 3:
        experiences.append({"num": f"{len(experiences)+1:02d}", "title": "Premium Experience",
                            "desc": "A carefully curated moment in this journey."})

    # Price conditions note
    price_cond_paras = [
        "Rates are indicative and subject to reconfirmation at the time of booking.",
        "Final price may vary depending on hotel availability, resort category, cruise selection, domestic flight fare, rooming arrangement, child policy, and final travel services confirmed."
    ]
    price_cond_paras = [translate_filter(truncate_text(x, 250), lang) for x in price_cond_paras]

    # --- GAP ALIGNMENT LOGIC ---
    show_muslim_care = False
    
    # Check meal preference in journeyGlance
    if payload.journeyGlance and payload.journeyGlance.mealPreference:
        if "halal" in payload.journeyGlance.mealPreference.lower() or "no pork" in payload.journeyGlance.mealPreference.lower():
            show_muslim_care = True
            
    # Check nationality / market (case-insensitive substring checks)
    muslim_keywords = ["saudi", "arabia", "uae", "emirates", "qatar", "kuwait", "oman", "bahrain", "gcc", "middle east", "malaysia", "indonesia", "egypt", "jordan", "turkey", "halal", "muslim"]
    
    nat_str = (nationality or "").lower()
    if any(k in nat_str for k in muslim_keywords):
        show_muslim_care = True

    # Journey at a Glance defaults/fallbacks
    glance = payload.journeyGlance
    glance_market = truncate_text(glance.market, 60)
    glance_profile = truncate_text(glance.guestProfile, 100)
    glance_standard = truncate_text(glance.hotelStandard, 80)
    glance_meals = truncate_text(glance.mealPreference, 100)
    glance_price_type = truncate_text(glance.priceType, 60)
    glance_tour_code = truncate_text(glance.tourCode, 40)
    glance_flights = truncate_text(glance.domesticFlights, 100)
    glance_basis = ""
    glance_partner_note = truncate_text(glance.partnerNote, 100)
    glance_validity = truncate_text(glance.validity, 60)

    # Why works defaults/fallbacks
    why = payload.whyWorks
    why_private = truncate_text(why.privateFlexible, 250)
    why_comfort = truncate_text(why.comfort, 250)
    why_muslim = truncate_text(why.muslimFriendly, 250)
    why_balanced = truncate_text(why.balancedHighlights, 250)

    # Selected Hotel Plan defaults/fallbacks
    hotel_plan_items = []
    hotel_room_notes = ""
    if payload.hotelPlan:
        for idx, item in enumerate(payload.hotelPlan.hotels):
            details = get_luxury_hotel_details(
                item.hotelArrangement, 
                item.destination, 
                item.checkInDate, 
                item.checkOutDate,
                index=idx,
                lang=lang
            )
            hotel_plan_items.append(canonicalize_place_names_in_data(details, lang))
        hotel_room_notes = truncate_text(normalize_room_note(payload.hotelPlan.roomNotes or "", lang), 200)

    stay_segments = _build_stay_segments_from_timeline(timeline_days, hotel_plan_items, lang)

    # Optional Enhancements defaults/fallbacks
    opt_enhancements = []
    if payload.optionalEnhancements:
        for item in payload.optionalEnhancements:
            opt_dict = item.model_dump(mode="json")
            opt_dict["name"] = truncate_text(opt_dict.get("name"), 80)
            opt_dict["description"] = truncate_text(opt_dict.get("description"), 200)
            opt_enhancements.append(opt_dict)

    # Booking Terms defaults/fallbacks
    b_terms = payload.bookingTerms
    term_deposit = b_terms.deposit or ""
    term_balance = b_terms.balance or ""
    term_cancellation = b_terms.cancellation or ""
    term_confirmation = b_terms.confirmation or ""

    mapped_itinerary = timeline_days

    # Multi-language support for dynamic itinerary subtitle
    days_cnt = len(payload.itinerary)
    if lang == "vi":
        itinerary_p_val = f"Hành trình riêng tư {duration_lbl} của bạn — {days_cnt} ngày, được thiết kế tỉ mỉ."
    elif lang == "ar":
        itinerary_p_val = f"رحلتك الخاصة {duration_lbl} — {days_cnt} يوماً، تم تصميمها بعناية."
    else:
        itinerary_p_val = f"Your private {duration_lbl} journey — {days_cnt} days, carefully crafted."

    # Journey investment header translation
    pricing_h2_title = translate_filter("Journey Investment", lang)
    pricing_h2_val = f"{pricing_h2_title}: {total_price}" if total_price else ""

    # Generate static map URL based on route stops or fall back to destinations
    coords_list = []
    for stop in route_stops:
        normalized = stop["destination"].lower().strip()
        matched = None
        for name, coords in SLUG_COORDS.items():
            if normalized == name:
                matched = coords
                break
        if matched is None:
            for slug, coords in SLUG_COORDS.items():
                if normalized in (slug, slug.replace("-", " ")):
                    matched = coords
                    break
        if matched and (not coords_list or coords_list[-1] != tuple(matched)):
            coords_list.append(tuple(matched))
    if not coords_list:
        for d in destinations:
            slug = d.get("slug")
            if slug and slug in SLUG_COORDS:
                lat, lng = SLUG_COORDS[slug]
                if not coords_list or coords_list[-1] != (lat, lng):
                    coords_list.append((lat, lng))

    static_map_url = ""
    if coords_list:
        markers = []
        for idx, (lat, lng) in enumerate(coords_list):
            markers.append(f"{lng},{lat},pm2gnm{idx+1}")
        pt_param = "~".join(markers)
        
        pl_coords = []
        for lat, lng in coords_list:
            pl_coords.append(f"{lng},{lat}")
        pl_param = f"c:17412eff,w:4,{','.join(pl_coords)}"
        
        static_map_url = f"https://static-maps.yandex.ru/1.x/?l=map&size=650,350&lang=en_US&pt={pt_param}"
        if len(coords_list) > 1:
            static_map_url += f"&pl={pl_param}"

    client_i18n = {
        "notification_title": translate_filter("Enable Notifications", lang),
        "previous_image": translate_filter("Previous image", lang),
        "next_image": translate_filter("Next image", lang),
        "go_to_slide": translate_filter("Go to slide", lang),
        "editing": translate_filter("Editing", lang),
        "publish_to_web": translate_filter("Publish to Web", lang),
        "publishing": translate_filter("Publishing...", lang),
        "committing_to_github": translate_filter("Committing to GitHub...", lang),
        "translate_block": translate_filter("Translate this block", lang),
        "change": translate_filter("Change", lang),
        "remove_block": translate_filter("Remove this block", lang),
        "remove_block_confirm": translate_filter("Remove this block? This action cannot be undone.", lang),
        "language_names": {
            "en": translate_filter("English", lang),
            "ar": translate_filter("Arabic", lang),
            "vi": translate_filter("Vietnamese", lang),
        },
        "test_notification_title": translate_filter("Itinerary Update", lang),
        "test_notification_body": translate_filter(
            "Your private guide has been assigned: Mr. Minh (Phone: +84 911 538 738).",
            lang,
        ),
        "enable_notifications_browser": translate_filter(
            "Please enable notifications in your browser settings to receive updates.",
            lang,
        ),
    }

    hero_meta_1 = lang_override.get("hero_meta_1") or f"{days_count} DAYS • {nights_count} NIGHTS • {guests_txt.upper() if guests_txt else 'FAMILY VACATION'}"
    letter_greeting = lang_override.get("letter_greeting") or f"Dear {prepared_for},"
    letter_intro = lang_override.get("letter_intro") or (
        f"I am delighted to present this privately arranged journey: {overview_heading}, created for "
        f"{guests_txt or 'two guests'} travelling from {travel_dates}. The route unfolds from {route_txt}."
    )
    letter_body_p2 = lang_override.get("letter_body_p2") or (
        "The programme has been considered around a gentler family rhythm: early check-in in Hanoi, "
        "private guiding and transfers, a premium overnight train cabin, and enough space between active days "
        "to pause. Dining, room arrangements and transitions have been planned with care, without adding "
        "unnecessary movement."
    )
    letter_outro = lang_override.get("letter_outro") or (
        "Please review the journey as a starting point for a personal conversation. Every final detail can be "
        "refined around your preferred pace, room choices and family priorities."
    )
    letter_sign_off = lang_override.get("letter_sign_off") or "Anh Son Le"
    letter_sender = lang_override.get("letter_sender") or "Your Journey Designer"

    return {
        # IDs & images
        "quotation_id":   quotation_id,
        "static_map_url": static_map_url,
        "img_0": img_0, "img_1": img_1, "img_2": img_2, "img_3": img_3, "img_4": img_4,
        "img_itinerary_divider": img_itinerary_divider,
        "img_hotel_divider":     img_hotel_divider,
        "destinations":   destinations,
        # Hero / header
        "quotation_title": truncate_text(payload.landingpageContent.heroSection.headline, 100),
        "tour_title":      tour_title,
        "kicker":          f"{translate_filter('Private Luxury Quotation', lang)} \u2012 {duration_lbl} \u2012 {travel_dates}",
        "lede":            lede,
        # Guest & trip meta
        "customer_name":   prepared_for,
        "nationality":     nationality,
        "travel_style":    travel_style,
        "guests_txt":      guests_txt,
        "route_txt":       route_txt,
        "duration_label":  duration_lbl,
        "travel_dates":    travel_dates,
        "hotel_options":   [],
        "confirmed_option": "",
        # Seller / contact
        "seller_name":    seller_name,
        "seller_email":   seller_email,
        "contact":        seller_phone,
        "contact_web":    brand.get("domain") if brand else "www.vietnamsafar.vn",
        "contact_phone":  seller_phone,
        "hero_meta_1":    hero_meta_1,
        # Quotation ref
        "quotation_number": payload.quotationNumber or quotation_id,
        "quotation_date":   quotation_start_date or travel_dates,
        "travel_dates_raw": quotation_start_date,
        "valid_until":      glance_validity,
        # Strip badges
        "strip_duration":  duration_lbl,
        "strip_best_for":  nationality or "B2B Partners",
        "strip_pace":      "Relaxed",
        "strip_service":   "Private",
        # Overview section
        "overview_heading": translate_filter(overview_heading, lang),
        "overview_h2":      f"{translate_filter('Prepared for', lang)}: {prepared_for} \u2014 {tour_title}",
        "overview_p":       canonicalize_place_names_in_text(payload.quotationNarrative, lang),
        "overview_paras":   overview_paras,
        # Experiences (first 3 days)
        "experiences":      experiences,
        # Gallery section
        "route_map_h2": translate_filter(lang_override.get("route_map_h2") or "Your Journey, Mapped", lang),
        "route_map_p":  translate_filter(lang_override.get("route_map_p") or "An interactive map showing your curated path through Vietnam's iconic landmarks and luxury stopovers. Click on a destination in the list or the map to explore highlights.", lang),
        "journey_h2":   translate_filter(lang_override.get("journey_h2") or "Destination imagery woven into the quotation.", lang),
        "journey_p":    translate_filter(lang_override.get("journey_p") or "Cinematic destination panels crafted for a premium travel proposal.", lang),
        "gal1_label":   translate_filter("Highlight", lang) if len(destinations) > 0 else translate_filter("Destination", lang),
        "gal1_title":   _d_name(0), "gal2_label": translate_filter("Destination", lang), "gal2_title": _d_name(1),
        "gal3_label":   translate_filter("Experience", lang), "gal3_title": _d_name(2), "gal4_label": translate_filter("Journey", lang), "gal4_title": _d_name(3),
        # Itinerary section
        "itinerary_h2": translate_filter("Day-by-Day Journey Program", lang),
        "itinerary_p":  itinerary_p_val,
        "itinerary":    mapped_itinerary,
        "timeline_days": mapped_itinerary,
        "route_stops": route_stops,
        "stay_segments": stay_segments,
        "itinerary_days": _build_itinerary_days_flat(mapped_itinerary, stay_segments, lang, manual_override),
        # Pricing section
        "currency":       currency,
        "pricing_title":  translate_filter("Journey Investment", lang),
        "pricing_basis":  glance_basis,
        "price_options":  price_options,
        "price_per_pax":  price_per_pax,
        "total_price":    total_price,
        "grand_total":    grand_total_num,
        "subtotal":       grand_total_num,
        "tax_total":      0.0,
        "pricing_h2":     pricing_h2_val,
        "pricing_p":      f"{translate_filter('Total', lang)}: {guests_txt}. {translate_filter('Currency', lang)}: {currency}. {translate_filter('Final rates subject to reconfirmation.', lang)}",
        # Inclusions / exclusions
        "inclusions":     inc_lines,
        "exclusions":     exc_lines,
        "inclusions_title": inclusions_title,
        "inclusions_lede": inclusions_lede,
        "exclusions_title": exclusions_title,
        "exclusions_lede": exclusions_lede,
        # Price conditions
        "price_cond_paras": [] if lang_override.get("hide_price_conditions") else price_cond_paras,
        "payment_terms":    translate_filter("Refer to Booking & Payment terms below.", lang),
        "terms_p":          price_cond_paras[0] if price_cond_paras else "",
        "letter_greeting":  letter_greeting,
        "letter_intro":     letter_intro,
        "letter_body_p2":   letter_body_p2,
        "letter_outro":     letter_outro,
        "letter_sign_off":  letter_sign_off,
        "letter_sender":    letter_sender,
        # CTA
        "cta_h2": lang_override.get("cta_h2", translate_filter("Confirm dates, then refine the luxury layer.", lang)),
        "cta_p":  translate_filter("Share travel dates, preferred hotel tier, rooming list and any dietary or mobility requirements. We will reconfirm availability and return a finalized quotation.", lang),
        # Footer
        "footer_text": f"{tour_title} — {translate_filter('Luxury quotation prepared for', lang)} {prepared_for}.",
        # Raw quotation (for reference / debugging)
        "raw_quotation":  "",
        # GAP ALIGNMENT context
        "show_muslim_care": show_muslim_care,
        "glance_market": glance_market,
        "glance_profile": glance_profile,
        "glance_standard": glance_standard,
        "glance_meals": glance_meals,
        "glance_price_type": glance_price_type,
        "glance_tour_code": glance_tour_code,
        "glance_flights": glance_flights,
        "glance_basis": glance_basis,
        "glance_partner_note": glance_partner_note,
        "glance_validity": glance_validity,
        "why_private": why_private,
        "why_comfort": why_comfort,
        "why_muslim": why_muslim,
        "why_balanced": why_balanced,
        "hotels": hotel_plan_items,
        "room_notes": hotel_room_notes,
        "optional_enhancements": opt_enhancements,
        "term_deposit": term_deposit,
        "term_balance": term_balance,
        "term_cancellation": term_cancellation,
        "term_confirmation": term_confirmation,
        "show_hotel_intro": not lang_override.get("hide_hotel_intro", False),
        "show_designer_section": not lang_override.get("hide_designer_section", False),
        "lang": lang,
        "template_name": template_name,
        "brand": brand or BRANDS["vietnam_safar"],
        "translation_status": _load_translation_status(quotation_id, default_lang=lang),
        "client_i18n": client_i18n,
    }
    ctx = canonicalize_place_names_in_data(ctx, lang)
    return ctx


def _load_ctx(quotation_id: str) -> dict | None:
    """Load ctx from memory store or persisted ctx.json (cross-instance resilience)."""
    entry = quotations.get(quotation_id)
    if entry and entry.get("ctx"):
        return entry["ctx"]
    ctx_path = os.path.join("published", quotation_id, "ctx.json")
    if os.path.isfile(ctx_path):
        with open(ctx_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _load_itinerary_ctx(itinerary_id: str) -> dict | None:
    """Load itinerary ctx from memory store or persisted ctx.json (cross-instance resilience)."""
    entry = itineraries.get(itinerary_id)
    if entry and entry.get("ctx"):
        return entry["ctx"]
    ctx_path = os.path.join("published", itinerary_id, "ctx.json")
    if os.path.isfile(ctx_path):
        with open(ctx_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _is_brochure_template(template_name: str | None) -> bool:
    return (template_name or "").endswith("vietnam_luxury_brosure.html")


LEGACY_QUOTATION_TEMPLATES = {
    "vietnam_heritage_luxury.html",
    "prototype_itinerary_imagery.html",
}

BROCHURE_TEMPLATE_NAME = "vietnam_luxury_brosure.html"


def _build_brochure_client_i18n(lang: str) -> dict[str, Any]:
    return {
        "notification_title": translate_filter("Enable Notifications", lang),
        "previous_image": translate_filter("Previous image", lang),
        "next_image": translate_filter("Next image", lang),
        "go_to_slide": translate_filter("Go to slide", lang),
        "editing": translate_filter("Editing", lang),
        "publish_to_web": translate_filter("Publish to Web", lang),
        "publishing": translate_filter("Publishing...", lang),
        "committing_to_github": translate_filter("Committing to GitHub...", lang),
        "translate_block": translate_filter("Translate this block", lang),
        "change": translate_filter("Change", lang),
        "remove_block": translate_filter("Remove this block", lang),
        "remove_block_confirm": translate_filter("Remove this block? This action cannot be undone.", lang),
        "language_names": {
            "en": translate_filter("English", lang),
            "ar": translate_filter("Arabic", lang),
            "vi": translate_filter("Vietnamese", lang),
        },
        "test_notification_title": translate_filter("Itinerary Update", lang),
        "test_notification_body": translate_filter(
            "Your private guide has been assigned: Mr. Minh (Phone: +84 911 538 738).",
            lang,
        ),
        "enable_notifications_browser": translate_filter(
            "Please enable notifications in your browser settings to receive updates.",
            lang,
        ),
        "show_draft": translate_filter("Show Draft", lang),
        "hide_draft": translate_filter("Hide Draft", lang),
        "brand_presets_label": translate_filter("Brand Presets", lang),
        "brand_preset_applied": translate_filter("Brand preset applied", lang),
    }


def _build_brochure_brand_presets() -> list[dict[str, Any]]:
    presets: list[dict[str, Any]] = []
    for profile in BRAND_PROFILES.values():
        presets.append({
            "brandId": profile.brand_id,
            "label": profile.display_name.replace(" Journeys", ""),
            "name": profile.display_name,
            "domain": profile.domain,
            "logo": profile.logo,
            "colors": copy.deepcopy(profile.colors),
            "fonts": copy.deepcopy(profile.fonts),
        })
    return presets


def _build_brochure_render_context(
    ctx_data: dict,
    document: dict,
    quotation_id: str,
    lang: str,
    *,
    latest_version: int = 1,
    preview_mode: bool = False,
    editor_mode: bool = False,
) -> dict[str, Any]:
    baseline_lang = ctx_data.get("baseline_lang", lang)
    translation_status = ctx_data.get(
        "translation_status",
        {"baseline_lang": baseline_lang, "available_langs": [baseline_lang]},
    )
    brand_config = _brand_config_from_quote_document(document)
    lang_ctx: dict[str, Any] = {
        "quotation_id": quotation_id,
        "lang": lang,
        "template_name": BROCHURE_TEMPLATE_NAME,
        "brand": brand_config,
        "baseline_lang": baseline_lang,
        "translations": ctx_data.get("translations", {}),
        "translation_status": translation_status,
        "available_langs": ctx_data.get("available_langs", [baseline_lang]),
        "latest_version": latest_version,
        "client_i18n": _build_brochure_client_i18n(lang),
        "brandPresets": _build_brochure_brand_presets(),
        "sectionRegistry": {key: value.model_dump(mode="json") for key, value in SECTION_REGISTRY.items()},
        "destinations": copy.deepcopy(ctx_data.get("destinations") or []),
        "route_stops": copy.deepcopy(ctx_data.get("route_stops") or []),
        "static_map_url": ctx_data.get("static_map_url") or "",
        "quotation_title": "",
        "kicker": "",
        "travel_style": ctx_data.get("travel_style") or "Private",
        "contact_web": brand_config.get("domain") or "",
        "show_hotel_intro": True,
        "show_designer_section": True,
        "inclusions_title": translate_filter("What Your Journey Includes", lang),
        "exclusions_title": translate_filter("Exclusions", lang),
        "inclusions_lede": "",
        "exclusions_lede": "",
        "payment_cta": translate_filter("Approve & Book Now", lang),
        "chapter_kicker": "CHAPTER 01 - THE INVITATION",
        "divider_itinerary_kicker": "DAY-BY-DAY ITINERARY",
        "itinerary_kicker": "CHAPTER 02 · DAY-BY-DAY ITINERARY",
        "divider_hotel_kicker": "THE JOURNEY, BROUGHT TOGETHER",
        "designer_kicker": translate_filter("Your Journey Designer", lang),
        "journey_h2": "",
        "journey_p": "",
        "cta_h2": "",
        "terms_p": "",
    }
    apply_quote_document_to_lang_ctx(lang_ctx, document)
    normalized_price_options = []
    for option in lang_ctx.get("price_options", []) or []:
        next_option = copy.deepcopy(option)
        price_per_person = next_option.get("pricePerPerson") or {}
        total_price = next_option.get("totalPrice") or {}
        price_per_person.setdefault("displayText", price_per_person.get("displayText") or "TBC")
        price_per_person.setdefault("amount", 0)
        price_per_person.setdefault("currency", "")
        total_price.setdefault("displayText", total_price.get("displayText") or "TBC")
        total_price.setdefault("amount", 0)
        total_price.setdefault("currency", "")
        next_option["pricePerPerson"] = price_per_person
        next_option["totalPrice"] = total_price
        normalized_price_options.append(next_option)
    lang_ctx["price_options"] = normalized_price_options
    lang_ctx["brand"] = brand_config
    lang_ctx["contact_web"] = brand_config.get("domain") or lang_ctx.get("contact_web") or ""
    lang_ctx["brochure_preview_mode"] = bool(preview_mode)
    lang_ctx["use_shared_draft_editor"] = bool(editor_mode)
    lang_ctx["quote_document"] = copy.deepcopy(document)
    lang_ctx["brochure_draft"] = copy.deepcopy(document)
    return lang_ctx


def _merge_brochure_render_context(
    ctx_data: dict,
    document: dict,
    quotation_id: str,
    lang: str,
    *,
    latest_version: int = 1,
    preview_mode: bool = False,
    editor_mode: bool = False,
) -> dict[str, Any]:
    render_ctx = _build_brochure_render_context(
        ctx_data,
        document,
        quotation_id,
        lang,
        latest_version=latest_version,
        preview_mode=preview_mode,
        editor_mode=editor_mode,
    )
    merged = copy.deepcopy(ctx_data)
    merged.update(render_ctx)
    return merged


def _load_persisted_quote_document(quotation_id: str) -> dict[str, Any] | None:
    environment = os.getenv("ENVIRONMENT", "local")
    if environment == "production":
        repo = os.getenv("GITHUB_REPO")
        token = os.getenv("GITHUB_TOKEN")
        if repo and token:
            import urllib.request

            try:
                url = f"https://api.github.com/repos/{repo}/contents/published/{quotation_id}/document.json"
                req = urllib.request.Request(
                    url,
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3.raw",
                        "User-Agent": "quotation-landingpage/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception as exc:
                log.warning("Failed to fetch document.json from GitHub for %s: %s", quotation_id, exc)

    path = os.path.join("published", quotation_id, "document.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            log.warning("Failed to parse document.json for %s: %s", quotation_id, exc)
    return None


def _validate_quote_document_or_422(document: dict[str, Any]) -> dict[str, Any]:
    section_errors = validate_quote_document_sections(document)
    if section_errors:
        raise HTTPException(
            status_code=422,
            detail={"errors": [item.model_dump(mode="json") for item in section_errors]},
        )
    try:
        normalized = QuoteDocumentV1.model_validate(document).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.errors()}) from exc
    return normalized


def _normalize_quote_document_structure_or_422(document: dict[str, Any]) -> dict[str, Any]:
    """Validate canonical shape without applying the publish-only section gate.

    Facts media, designer assignment, and deterministic defaults are all valid
    before Content has filled the brochure's required narrative/legal sections.
    Review/Publish remains the sole completeness boundary.
    """
    try:
        candidate = copy.deepcopy(document)
        # Facts/media mutations can start before a staff member creates the
        # rich sections. This supplies only the empty V1 container; it never
        # translates legacy content or makes the document publishable.
        candidate.setdefault("content", {"sections": {}})
        candidate.setdefault("meta", {}).setdefault("contentSchemaVersion", 1)
        return QuoteDocumentV1.model_validate(candidate).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.errors()}) from exc


def _create_quote_request_from_document(document: dict[str, Any]) -> CreateQuoteRequestV1:
    quote_document = QuoteDocumentV1.model_validate(document)
    rich_content = rich_content_values(quote_document)
    hotels = []
    for hotel in quote_document.stays.hotels:
        hotels.append(
            {
                "destination": hotel.city,
                "name": hotel.name,
                "room_type": hotel.roomType,
                "check_in": "",
                "check_out": "",
                "intro": hotel.introduction,
                "phone": hotel.tel,
            }
        )
    return CreateQuoteRequestV1.model_validate(
        {
            "opportunity_id": quote_document.meta.opportunityId,
            "brand_id": quote_document.meta.brandId,
            "lang": quote_document.meta.lang,
            "trip_facts": {
                "destinations": [day.segmentCity for day in quote_document.itinerary.days if day.segmentCity],
                "start_date": "",
                "end_date": "",
                "itinerary": [
                    {
                        "day_number": day.dayNumber,
                        "destination": day.segmentCity,
                        "overnight": day.overnight,
                        "meals": day.meals,
                    }
                    for day in quote_document.itinerary.days
                ],
            },
            "pricing_facts": {
                "conditions": [item.text for item in quote_document.pricing.conditions],
                "options": [
                    {
                        "id": option.id,
                        "label": option.label or f"Option {index:02d}",
                        "currency": option.currency,
                        "per_traveler_amount_minor": option.perTravelerAmountMinor,
                        "group_total_amount_minor": option.groupTotalAmountMinor,
                    }
                    for index, option in enumerate(quote_document.pricing.options, 1)
                    if option.currency and option.perTravelerAmountMinor and option.groupTotalAmountMinor
                ],
            },
            "customer_facts": {
                "customer_name": quote_document.traveler.customerName,
                "adults": quote_document.traveler.adults or 2,
                "children": quote_document.traveler.children,
                "nationality": quote_document.traveler.nationality,
                "guest_profile": quote_document.traveler.guestProfile,
                "travel_style": quote_document.traveler.guestProfile,

            },
            "service_facts": {
                "hotels": hotels,
                "inclusions": rich_content["inclusions"],
                "exclusions": rich_content["exclusions"],
            },
        }
    )


def _safe_asset_ref(url: str | None, asset_id: str | None = None, status: str = "ready") -> dict:
    return {
        "assetId": asset_id or "",
        "url": url or "",
        "status": status,
    }


def _asset_url(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("url") or ""
    if isinstance(value, str):
        return value
    return ""


def _simple_list_to_draft(items: list[Any], prefix: str) -> list[dict]:
    draft_items = []
    for idx, item in enumerate(items or [], 1):
        if isinstance(item, dict):
            text = item.get("text") or item.get("title") or item.get("desc") or ""
        else:
            text = str(item or "")
        draft_items.append({
            "id": f"{prefix}-{idx}",
            "text": text,
        })
    return draft_items


def _draft_items_to_simple_list(items: list[Any]) -> list[str]:
    simple_items = []
    for item in items or []:
        if isinstance(item, dict):
            val = item.get("text") or ""
        else:
            val = str(item or "")
        if val:
            simple_items.append(val)
    return simple_items


def _legacy_build_brochure_draft_from_lang_ctx(lang_ctx: dict, quotation_id: str, lang: str) -> dict:
    brand = copy.deepcopy(lang_ctx.get("brand") or BRANDS["vietnam_safar"])
    hero_url = lang_ctx.get("hero_img_custom") or lang_ctx.get("img_0") or _default_brand_logo(brand)
    itinerary_days = copy.deepcopy(lang_ctx.get("itinerary_days") or [])
    stay_segments = copy.deepcopy(lang_ctx.get("stay_segments") or [])
    hotels = copy.deepcopy(lang_ctx.get("hotels") or [])
    price_options = copy.deepcopy(lang_ctx.get("price_options") or [])

    draft_days = []
    for idx, day in enumerate(itinerary_days, 1):
        layout_images = copy.deepcopy(day.get("layout_images") or {})
        carousel = [_safe_asset_ref(img) for img in (layout_images.get("carousel") or []) if img]
        draft_days.append({
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
                "hero": _safe_asset_ref(layout_images.get("hero")),
                "small1": _safe_asset_ref(layout_images.get("small-1")),
                "small2": _safe_asset_ref(layout_images.get("small-2")),
                "carousel": carousel,
            },
        })

    draft_stays = []
    for idx, hotel in enumerate(hotels, 1):
        draft_stays.append({
            "id": hotel.get("id") or f"hotel-{idx}",
            "city": hotel.get("city_country") or "",
            "name": hotel.get("name") or "",
            "introduction": hotel.get("introduction") or hotel.get("hotel_intro") or "",
            "hotelDate": hotel.get("date_range") or hotel.get("check_in_out") or "",
            "tel": hotel.get("tel") or hotel.get("telephone") or "",
            "roomType": hotel.get("room_type") or hotel.get("room_name") or "",
            "hotelImage": _safe_asset_ref(hotel.get("hotel_img")),
            "roomImage": _safe_asset_ref(hotel.get("room_img")),
        })

    draft_price_options = []
    for idx, opt in enumerate(price_options, 1):
        draft_price_options.append({
            "id": opt.get("id") or f"price-{idx}",
            "category": opt.get("hotelCategory") or "",
            "name": opt.get("optionName") or "",
            "perPersonText": ((opt.get("pricePerPerson") or {}).get("displayText") if isinstance(opt.get("pricePerPerson"), dict) else "") or "",
            "totalText": ((opt.get("totalPrice") or {}).get("displayText") if isinstance(opt.get("totalPrice"), dict) else "") or "",
            "isTotal": bool(opt.get("is_total")),
            "isConfirmedMainOption": bool(opt.get("isConfirmedMainOption")),
            "isAlternativeOption": bool(opt.get("isAlternativeOption")),
        })

    draft_segments = []
    for idx, segment in enumerate(stay_segments, 1):
        draft_segments.append({
            "id": segment.get("segmentId") or f"stay-{idx}",
            "displayName": segment.get("displayName") or "",
            "daysLabel": segment.get("daysLabel") or "",
            "nightsLabel": segment.get("nightsLabel") or "",
            "hotelName": segment.get("hotelName") or "",
            "hotelDateRange": segment.get("hotelDateRange") or "",
            "hotelImage": _safe_asset_ref(segment.get("hotelImage")),
            "mapSegmentDesc": segment.get("mapSegmentDesc") or "",
            "activityPreviews": copy.deepcopy(segment.get("activityPreviews") or []),
            "coords": copy.deepcopy(segment.get("coords") or []),
        })

    return {
        "meta": {
            "quotationId": quotation_id,
            "lang": lang,
            "template": lang_ctx.get("template_name") or "vietnam_luxury_brosure.html",
            "revision": int((((lang_ctx.get("brochure_draft") or {}).get("meta") or {}).get("revision")) or 1),
        },
        "brand": {
            "name": brand.get("name") or "",
            "domain": brand.get("domain") or "",
            "logo": _safe_asset_ref(brand.get("logo")),
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
            "hero": _safe_asset_ref(hero_url),
            "itineraryDivider": _safe_asset_ref(lang_ctx.get("img_itinerary_divider")),
            "staysDivider": _safe_asset_ref(lang_ctx.get("img_stays_divider")),
            "hotelDivider": _safe_asset_ref(lang_ctx.get("img_hotel_divider")),
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
            "heroMeta2": lang_ctx.get("hero_meta_2") or lang_ctx.get("travel_dates") or "",
            "letterGreeting": lang_ctx.get("letter_greeting") or "",
            "letterIntro": lang_ctx.get("letter_intro") or "",
            "letterBody2": lang_ctx.get("letter_body_p2") or "",
            "letterOutro": lang_ctx.get("letter_outro") or "",
            "letterSignOff": lang_ctx.get("letter_sign_off") or "",
            "letterSender": lang_ctx.get("letter_sender") or "",
            "footerText": lang_ctx.get("footer_text") or "",
        },
        "route": {
            "title": lang_ctx.get("route_map_h2") or "",
            "description": lang_ctx.get("route_map_p") or "",
            "staySegments": draft_segments,
        },
        "itinerary": {
            "title": lang_ctx.get("itinerary_h2") or "",
            "description": lang_ctx.get("itinerary_p") or "",
            "days": draft_days,
        },
        "stays": {
            "hotels": draft_stays,
            "roomNotes": lang_ctx.get("room_notes") or "",
        },
        "pricing": {
            "kicker": lang_ctx.get("pricing_kicker") or "Package Pricing",
            "title": lang_ctx.get("pricing_h2") or "",
            "description": lang_ctx.get("pricing_p") or "",
            "conditions": _simple_list_to_draft(lang_ctx.get("price_cond_paras") or [], "price-cond"),
            "options": draft_price_options,
        },
        "inclusions": _simple_list_to_draft(lang_ctx.get("inclusions") or [], "inc"),
        "exclusions": _simple_list_to_draft(lang_ctx.get("exclusions") or [], "exc"),
        "bookingTerms": {
            "kicker": lang_ctx.get("payment_kicker") or "Important Notes",
            "title": lang_ctx.get("payment_title") or "Booking & Payment Terms",
            "description": lang_ctx.get("payment_desc") or "",
            "deposit": lang_ctx.get("term_deposit") or "",
            "balance": lang_ctx.get("term_balance") or "",
            "cancellation": lang_ctx.get("term_cancellation") or "",
            "confirmation": lang_ctx.get("term_confirmation") or "",
        },
        "designer": {
            "name": lang_ctx.get("seller_name") or "",
            "signature": lang_ctx.get("designer_signature") or "",
            "experience": lang_ctx.get("designer_experience") or "",
            "quote": lang_ctx.get("designer_quote") or "",
            "title": lang_ctx.get("designer_title") or "",
            "phone": lang_ctx.get("contact_phone") or lang_ctx.get("contact") or "",
            "email": lang_ctx.get("seller_email") or "",
            "image": _safe_asset_ref(lang_ctx.get("designer_img")),
        },
        "viewOverrides": {
            "web": {},
            "pdf": {},
        },
    }


def _legacy_store_brochure_draft(ctx_data: dict, target_lang: str, draft: dict) -> dict:
    brochure_drafts = ctx_data.setdefault("brochureDrafts", {})
    brochure_drafts[target_lang] = copy.deepcopy(draft)
    ctx_data["brochureDraft"] = copy.deepcopy(draft)
    ctx_data["brochureDraftLang"] = target_lang

    brand = draft.get("brand") or {}
    brand_logo = _asset_url(brand.get("logo"))
    brand_colors = brand.get("colors") or {}
    brand_fonts = brand.get("fonts") or {}
    ctx_data["brand"] = {
        "id": ((ctx_data.get("brand") or {}).get("id") if isinstance(ctx_data.get("brand"), dict) else None) or "vietnam_safar",
        "name": brand.get("name") or "",
        "domain": brand.get("domain") or "",
        "logo": brand_logo or _default_brand_logo(ctx_data.get("brand")),
        "color_primary": brand_colors.get("primary") or "#17412e",
        "color_primary_dark": brand_colors.get("primaryDark") or "#0e2f22",
        "color_accent": brand_colors.get("accent") or "#b7894b",
        "color_accent_light": brand_colors.get("accentLight") or "#d8bd85",
        "color_bg_main": brand_colors.get("bgMain") or "#f9f6f0",
        "color_bg_alt": brand_colors.get("bgAlt") or "#fffaf1",
        "color_text_main": brand_colors.get("textMain") or "#11130f",
        "color_text_muted": brand_colors.get("textMuted") or "#706a5d",
        "color_text_light": brand_colors.get("textLight") or "#ffffff",
        "font_serif": brand_fonts.get("serif") or "Cormorant Garamond",
        "font_sans": brand_fonts.get("sans") or "Montserrat",
        "font_accent": brand_fonts.get("accent") or "Allura",
    }
    ctx_data["hero_img"] = _asset_url(((draft.get("assets") or {}).get("hero")))
    ctx_data["img_itinerary_divider"] = _asset_url(((draft.get("assets") or {}).get("itineraryDivider")))
    ctx_data["img_stays_divider"] = _asset_url(((draft.get("assets") or {}).get("staysDivider")))
    ctx_data["img_hotel_divider"] = _asset_url(((draft.get("assets") or {}).get("hotelDivider")))
    ctx_data["designer_img"] = _asset_url(((draft.get("designer") or {}).get("image")))
    return draft


def _legacy_get_stored_brochure_draft(ctx_data: dict, target_lang: str) -> dict | None:
    brochure_drafts = ctx_data.get("brochureDrafts") or {}
    draft = brochure_drafts.get(target_lang)
    if draft:
        return copy.deepcopy(draft)
    stored_single = ctx_data.get("brochureDraft")
    stored_lang = ctx_data.get("brochureDraftLang")
    if stored_single and stored_lang == target_lang:
        return copy.deepcopy(stored_single)
    return None


def _legacy_ensure_brochure_draft(ctx_data: dict, quotation_id: str, target_lang: str, lang_ctx: dict, *, force_brand_from_ctx: bool = False) -> dict:
    draft = _get_stored_brochure_draft(ctx_data, target_lang)
    if not draft:
        draft = _build_brochure_draft_from_lang_ctx(lang_ctx, quotation_id, target_lang)
        _store_brochure_draft(ctx_data, target_lang, draft)
    elif force_brand_from_ctx:
        fresh_brand = _build_brochure_draft_from_lang_ctx(lang_ctx, quotation_id, target_lang).get("brand") or {}
        draft["brand"] = fresh_brand
        _store_brochure_draft(ctx_data, target_lang, draft)
    return copy.deepcopy(draft)


def _legacy_apply_brochure_draft_to_lang_ctx(lang_ctx: dict, draft: dict):
    brand = copy.deepcopy(lang_ctx.get("brand") or BRANDS["vietnam_safar"])
    draft_brand = draft.get("brand") or {}
    draft_colors = draft_brand.get("colors") or {}
    draft_fonts = draft_brand.get("fonts") or {}
    brand.update({
        "name": draft_brand.get("name") or brand.get("name"),
        "domain": draft_brand.get("domain") or brand.get("domain"),
        "logo": _asset_url(draft_brand.get("logo")) or brand.get("logo"),
        "color_primary": draft_colors.get("primary") or brand.get("color_primary"),
        "color_primary_dark": draft_colors.get("primaryDark") or brand.get("color_primary_dark"),
        "color_accent": draft_colors.get("accent") or brand.get("color_accent"),
        "color_accent_light": draft_colors.get("accentLight") or brand.get("color_accent_light"),
        "color_bg_main": draft_colors.get("bgMain") or brand.get("color_bg_main"),
        "color_bg_alt": draft_colors.get("bgAlt") or brand.get("color_bg_alt"),
        "color_text_main": draft_colors.get("textMain") or brand.get("color_text_main"),
        "color_text_muted": draft_colors.get("textMuted") or brand.get("color_text_muted"),
        "color_text_light": draft_colors.get("textLight") or brand.get("color_text_light"),
        "font_serif": draft_fonts.get("serif") or brand.get("font_serif"),
        "font_sans": draft_fonts.get("sans") or brand.get("font_sans"),
        "font_accent": draft_fonts.get("accent") or brand.get("font_accent"),
    })
    lang_ctx["brand"] = brand

    traveler = draft.get("traveler") or {}
    trip = draft.get("trip") or {}
    narrative = draft.get("narrative") or {}
    route = draft.get("route") or {}
    pricing = draft.get("pricing") or {}
    booking_terms = draft.get("bookingTerms") or {}
    designer = draft.get("designer") or {}
    assets = draft.get("assets") or {}

    lang_ctx["customer_name"] = traveler.get("customerName") or lang_ctx.get("customer_name")
    lang_ctx["guests_txt"] = traveler.get("guestProfile") or lang_ctx.get("guests_txt")
    lang_ctx["nationality"] = traveler.get("nationality") or lang_ctx.get("nationality")
    lang_ctx["tour_title"] = trip.get("title") or lang_ctx.get("tour_title")
    lang_ctx["lede"] = trip.get("lede") or lang_ctx.get("lede")
    lang_ctx["duration_label"] = trip.get("durationText") or lang_ctx.get("duration_label")
    lang_ctx["route_txt"] = trip.get("routeText") or lang_ctx.get("route_txt")
    lang_ctx["travel_dates"] = trip.get("travelDates") or lang_ctx.get("travel_dates")
    lang_ctx["quotation_number"] = trip.get("quotationNumber") or lang_ctx.get("quotation_number")

    lang_ctx["cover_kicker"] = narrative.get("coverKicker") or lang_ctx.get("cover_kicker")
    lang_ctx["hero_meta_1"] = narrative.get("heroMeta1") or lang_ctx.get("hero_meta_1")
    lang_ctx["hero_meta_2"] = narrative.get("heroMeta2") or lang_ctx.get("hero_meta_2")
    lang_ctx["letter_greeting"] = narrative.get("letterGreeting") or lang_ctx.get("letter_greeting")
    lang_ctx["letter_intro"] = narrative.get("letterIntro") or lang_ctx.get("letter_intro")
    lang_ctx["letter_body_p2"] = narrative.get("letterBody2") or lang_ctx.get("letter_body_p2")
    lang_ctx["letter_outro"] = narrative.get("letterOutro") or lang_ctx.get("letter_outro")
    lang_ctx["letter_sign_off"] = narrative.get("letterSignOff") or lang_ctx.get("letter_sign_off")
    lang_ctx["letter_sender"] = narrative.get("letterSender") or lang_ctx.get("letter_sender")
    lang_ctx["footer_text"] = narrative.get("footerText") or lang_ctx.get("footer_text")

    lang_ctx["route_map_h2"] = route.get("title") or lang_ctx.get("route_map_h2")
    lang_ctx["route_map_p"] = route.get("description") or lang_ctx.get("route_map_p")
    lang_ctx["itinerary_h2"] = (draft.get("itinerary") or {}).get("title") or lang_ctx.get("itinerary_h2")
    lang_ctx["itinerary_p"] = (draft.get("itinerary") or {}).get("description") or lang_ctx.get("itinerary_p")

    lang_ctx["pricing_kicker"] = pricing.get("kicker") or lang_ctx.get("pricing_kicker")
    lang_ctx["pricing_h2"] = pricing.get("title") or lang_ctx.get("pricing_h2")
    lang_ctx["pricing_p"] = pricing.get("description") or lang_ctx.get("pricing_p")
    lang_ctx["price_cond_paras"] = _draft_items_to_simple_list(pricing.get("conditions") or []) or lang_ctx.get("price_cond_paras")

    lang_ctx["payment_kicker"] = booking_terms.get("kicker") or lang_ctx.get("payment_kicker")
    lang_ctx["payment_title"] = booking_terms.get("title") or lang_ctx.get("payment_title")
    lang_ctx["payment_desc"] = booking_terms.get("description") or lang_ctx.get("payment_desc")
    lang_ctx["term_deposit"] = booking_terms.get("deposit") or lang_ctx.get("term_deposit")
    lang_ctx["term_balance"] = booking_terms.get("balance") or lang_ctx.get("term_balance")
    lang_ctx["term_cancellation"] = booking_terms.get("cancellation") or lang_ctx.get("term_cancellation")
    lang_ctx["term_confirmation"] = booking_terms.get("confirmation") or lang_ctx.get("term_confirmation")

    lang_ctx["seller_name"] = designer.get("name") or lang_ctx.get("seller_name")
    lang_ctx["designer_signature"] = designer.get("signature") or lang_ctx.get("designer_signature")
    lang_ctx["designer_experience"] = designer.get("experience") or lang_ctx.get("designer_experience")
    lang_ctx["designer_quote"] = designer.get("quote") or lang_ctx.get("designer_quote")
    lang_ctx["designer_title"] = designer.get("title") or lang_ctx.get("designer_title")
    lang_ctx["contact_phone"] = designer.get("phone") or lang_ctx.get("contact_phone")
    lang_ctx["contact"] = designer.get("phone") or lang_ctx.get("contact")
    lang_ctx["seller_email"] = designer.get("email") or lang_ctx.get("seller_email")
    lang_ctx["designer_img"] = _asset_url(designer.get("image")) or lang_ctx.get("designer_img")

    hero_url = _asset_url(assets.get("hero"))
    if hero_url:
        lang_ctx["hero_img_custom"] = hero_url
        lang_ctx["img_0"] = hero_url
    itinerary_divider = _asset_url(assets.get("itineraryDivider"))
    if itinerary_divider:
        lang_ctx["img_itinerary_divider"] = itinerary_divider
    stays_divider = _asset_url(assets.get("staysDivider"))
    if stays_divider:
        lang_ctx["img_stays_divider"] = stays_divider
    hotel_divider = _asset_url(assets.get("hotelDivider"))
    if hotel_divider:
        lang_ctx["img_hotel_divider"] = hotel_divider

    draft_days = (draft.get("itinerary") or {}).get("days") or []
    base_flat_days = copy.deepcopy(lang_ctx.get("itinerary_days") or [])
    base_timeline = copy.deepcopy(lang_ctx.get("itinerary") or [])
    new_flat_days = []
    new_timeline = []
    for idx, day_draft in enumerate(draft_days, 1):
        flat_day = copy.deepcopy(base_flat_days[idx - 1]) if idx - 1 < len(base_flat_days) else {}
        timeline_day = copy.deepcopy(base_timeline[idx - 1]) if idx - 1 < len(base_timeline) else {}
        images = day_draft.get("images") or {}
        flat_day.update({
            "id": day_draft.get("id") or flat_day.get("id") or f"day-{day_draft.get('dayNumber') or idx}",
            "dayNumber": day_draft.get("dayNumber") or flat_day.get("dayNumber") or idx,
            "segment_city": day_draft.get("segmentCity") or flat_day.get("segment_city") or "",
            "title": day_draft.get("title") or "",
            "description": copy.deepcopy(day_draft.get("description") or []),
            "overnight": day_draft.get("overnight") or "",
            "meals": copy.deepcopy(day_draft.get("meals") or []),
            "activities": copy.deepcopy(day_draft.get("activities") or []),
            "notes": copy.deepcopy(day_draft.get("notes") or []),
            "label_highlights": day_draft.get("labelHighlights") or flat_day.get("label_highlights"),
            "label_notes": day_draft.get("labelNotes") or flat_day.get("label_notes"),
            "layout_type": day_draft.get("layoutType") or flat_day.get("layout_type") or "single",
        })
        layout_images = copy.deepcopy(flat_day.get("layout_images") or {})
        layout_images["hero"] = _asset_url(images.get("hero")) or layout_images.get("hero") or ""
        layout_images["small-1"] = _asset_url(images.get("small1")) or layout_images.get("small-1") or ""
        layout_images["small-2"] = _asset_url(images.get("small2")) or layout_images.get("small-2") or ""
        carousel_urls = [_asset_url(item) for item in images.get("carousel") or [] if _asset_url(item)]
        if carousel_urls:
            layout_images["carousel"] = carousel_urls
        flat_day["layout_images"] = layout_images
        timeline_day.update({
            "dayNumber": flat_day["dayNumber"],
            "title": flat_day["title"],
            "description": copy.deepcopy(flat_day["description"]),
            "overnight": flat_day["overnight"],
            "meals": copy.deepcopy(flat_day["meals"]),
            "activities": copy.deepcopy(flat_day["activities"]),
            "notes": copy.deepcopy(flat_day["notes"]),
            "destinations": copy.deepcopy(timeline_day.get("destinations") or ([flat_day["segment_city"]] if flat_day["segment_city"] else [])),
            "label_highlights": flat_day.get("label_highlights"),
            "label_notes": flat_day.get("label_notes"),
        })
        new_flat_days.append(flat_day)
        new_timeline.append(timeline_day)
    if new_flat_days:
        lang_ctx["itinerary_days"] = new_flat_days
        lang_ctx["itinerary"] = new_timeline
        lang_ctx["timeline_days"] = copy.deepcopy(new_timeline)

    draft_segments = route.get("staySegments") or []
    base_segments = copy.deepcopy(lang_ctx.get("stay_segments") or [])
    new_segments = []
    for idx, segment_draft in enumerate(draft_segments, 1):
        segment = copy.deepcopy(base_segments[idx - 1]) if idx - 1 < len(base_segments) else {}
        segment_id = segment_draft.get("id") if "id" in segment_draft else segment.get("segmentId")
        display_name = segment_draft.get("displayName") if "displayName" in segment_draft else segment.get("displayName")
        days_label = segment_draft.get("daysLabel") if "daysLabel" in segment_draft else segment.get("daysLabel")
        nights_label = segment_draft.get("nightsLabel") if "nightsLabel" in segment_draft else segment.get("nightsLabel")
        hotel_name = segment_draft.get("hotelName") if "hotelName" in segment_draft else segment.get("hotelName")
        hotel_date_range = segment_draft.get("hotelDateRange") if "hotelDateRange" in segment_draft else segment.get("hotelDateRange")
        hotel_image = _asset_url(segment_draft.get("hotelImage")) if "hotelImage" in segment_draft else segment.get("hotelImage")
        map_segment_desc = segment_draft.get("mapSegmentDesc") if "mapSegmentDesc" in segment_draft else segment.get("mapSegmentDesc")
        coords = copy.deepcopy(segment_draft.get("coords")) if "coords" in segment_draft else copy.deepcopy(segment.get("coords") or [])
        segment.update({
            "segmentId": segment_id or f"stay-{idx}",
            "displayName": display_name or "",
            "daysLabel": days_label or "",
            "nightsLabel": nights_label or "",
            "hotelName": hotel_name or "",
            "hotelDateRange": hotel_date_range or "",
            "hotelImage": hotel_image or "",
            "mapSegmentDesc": map_segment_desc if map_segment_desc is not None else "",
            "coords": coords or [],
        })
        new_segments.append(segment)
    if new_segments:
        lang_ctx["stay_segments"] = new_segments

    draft_hotels = (draft.get("stays") or {}).get("hotels") or []
    base_hotels = copy.deepcopy(lang_ctx.get("hotels") or [])
    new_hotels = []
    for idx, hotel_draft in enumerate(draft_hotels, 1):
        hotel = copy.deepcopy(base_hotels[idx - 1]) if idx - 1 < len(base_hotels) else {}
        hotel.update({
            "id": hotel_draft.get("id") or hotel.get("id") or f"hotel-{idx}",
            "city_country": hotel_draft.get("city") or hotel.get("city_country") or "",
            "name": hotel_draft.get("name") or hotel.get("name") or "",
            "introduction": hotel_draft.get("introduction") or hotel.get("introduction") or "",
            "hotel_intro": hotel_draft.get("introduction") or hotel.get("hotel_intro") or "",
            "date_range": hotel_draft.get("hotelDate") or hotel.get("date_range") or "",
            "tel": hotel_draft.get("tel") or hotel.get("tel") or "",
            "telephone": hotel_draft.get("tel") or hotel.get("telephone") or "",
            "room_type": hotel_draft.get("roomType") or hotel.get("room_type") or "",
            "room_name": hotel_draft.get("roomType") or hotel.get("room_name") or "",
            "hotel_img": _asset_url(hotel_draft.get("hotelImage")) or hotel.get("hotel_img") or "",
            "room_img": _asset_url(hotel_draft.get("roomImage")) or hotel.get("room_img") or "",
        })
        new_hotels.append(hotel)
    if new_hotels:
        lang_ctx["hotels"] = new_hotels
    lang_ctx["room_notes"] = (draft.get("stays") or {}).get("roomNotes") or lang_ctx.get("room_notes")

    draft_options = pricing.get("options") or []
    base_options = copy.deepcopy(lang_ctx.get("price_options") or [])
    new_options = []
    for idx, option_draft in enumerate(draft_options, 1):
        option = copy.deepcopy(base_options[idx - 1]) if idx - 1 < len(base_options) else {}
        price_per_person = copy.deepcopy(option.get("pricePerPerson") or {})
        total_price = copy.deepcopy(option.get("totalPrice") or {})
        price_per_person["displayText"] = option_draft.get("perPersonText") or price_per_person.get("displayText") or ""
        total_price["displayText"] = option_draft.get("totalText") or total_price.get("displayText") or ""
        option.update({
            "id": option_draft.get("id") or option.get("id") or f"price-{idx}",
            "hotelCategory": option_draft.get("category") or option.get("hotelCategory") or "",
            "optionName": option_draft.get("name") or option.get("optionName") or "",
            "pricePerPerson": price_per_person,
            "totalPrice": total_price,
            "is_total": bool(option_draft.get("isTotal")),
            "isConfirmedMainOption": bool(option_draft.get("isConfirmedMainOption")),
            "isAlternativeOption": bool(option_draft.get("isAlternativeOption")),
        })
        new_options.append(option)
    if new_options:
        lang_ctx["price_options"] = new_options

    draft_inclusions = _draft_items_to_simple_list(draft.get("inclusions") or [])
    draft_exclusions = _draft_items_to_simple_list(draft.get("exclusions") or [])
    if draft_inclusions:
        lang_ctx["inclusions"] = draft_inclusions
    if draft_exclusions:
        lang_ctx["exclusions"] = draft_exclusions

    lang_ctx["brochure_draft"] = copy.deepcopy(draft)


# Canonical brochure document wrappers. These override the legacy draft helpers
# so the rest of the brochure flow can keep calling the same functions.
def _build_brochure_draft_from_lang_ctx(lang_ctx: dict, quotation_id: str, lang: str) -> dict:
    return build_quote_document_from_lang_ctx(lang_ctx, quotation_id, lang)


def _store_brochure_draft(ctx_data: dict, target_lang: str, draft: dict) -> dict:
    requested_brand_id = ((draft.get("meta") or {}).get("brandId")) or None
    fallback_brand_id = ((ctx_data.get("brand") or {}).get("id") if isinstance(ctx_data.get("brand"), dict) else None) or "vietnam_safar"
    normalized = normalize_quote_document(
        draft,
        (draft.get("meta") or {}).get("quotationId") or ctx_data.get("quotation_id") or "",
        target_lang,
        template_name=ctx_data.get("template_name") or "vietnam_luxury_brosure.html",
        brand_id=requested_brand_id or fallback_brand_id,
    )
    ctx_data.setdefault("quoteDocuments", {})[target_lang] = copy.deepcopy(normalized)
    ctx_data["quoteDocument"] = copy.deepcopy(normalized)
    ctx_data["quoteDocumentLang"] = target_lang
    ctx_data.setdefault("brochureDrafts", {})[target_lang] = copy.deepcopy(normalized)
    ctx_data["brochureDraft"] = copy.deepcopy(normalized)
    ctx_data["brochureDraftLang"] = target_lang

    brand = normalized.get("brand") or {}
    brand_colors = brand.get("colors") or {}
    brand_fonts = brand.get("fonts") or {}
    ctx_data["brand"] = {
        "id": ((normalized.get("meta") or {}).get("brandId")) or fallback_brand_id,
        "name": brand.get("name") or "",
        "domain": brand.get("domain") or "",
        "logo": _asset_url(brand.get("logo")) or _default_brand_logo(ctx_data.get("brand")),
        "color_primary": brand_colors.get("primary") or "#17412e",
        "color_primary_dark": brand_colors.get("primaryDark") or "#0e2f22",
        "color_accent": brand_colors.get("accent") or "#b7894b",
        "color_accent_light": brand_colors.get("accentLight") or "#d8bd85",
        "color_bg_main": brand_colors.get("bgMain") or "#f9f6f0",
        "color_bg_alt": brand_colors.get("bgAlt") or "#fffaf1",
        "color_text_main": brand_colors.get("textMain") or "#11130f",
        "color_text_muted": brand_colors.get("textMuted") or "#706a5d",
        "color_text_light": brand_colors.get("textLight") or "#ffffff",
        "font_serif": brand_fonts.get("serif") or "Cormorant Garamond",
        "font_sans": brand_fonts.get("sans") or "Montserrat",
        "font_accent": brand_fonts.get("accent") or "Allura",
    }
    ctx_data["hero_img"] = _asset_url(((normalized.get("assets") or {}).get("hero")))
    ctx_data["img_itinerary_divider"] = _asset_url(((normalized.get("assets") or {}).get("itineraryDivider")))
    ctx_data["img_stays_divider"] = _asset_url(((normalized.get("assets") or {}).get("staysDivider")))
    ctx_data["img_hotel_divider"] = _asset_url(((normalized.get("assets") or {}).get("hotelDivider")))
    ctx_data["designer_img"] = _asset_url(((normalized.get("designer") or {}).get("image")))
    return normalized


def _get_stored_brochure_draft(ctx_data: dict, target_lang: str) -> dict | None:
    quote_documents = ctx_data.get("quoteDocuments") or {}
    draft = quote_documents.get(target_lang)
    if draft:
        return copy.deepcopy(draft)
    stored_single = ctx_data.get("quoteDocument")
    stored_lang = ctx_data.get("quoteDocumentLang")
    if stored_single and stored_lang == target_lang:
        return copy.deepcopy(stored_single)

    brochure_drafts = ctx_data.get("brochureDrafts") or {}
    draft = brochure_drafts.get(target_lang)
    if draft:
        return copy.deepcopy(draft)
    stored_single = ctx_data.get("brochureDraft")
    stored_lang = ctx_data.get("brochureDraftLang")
    if stored_single and stored_lang == target_lang:
        return copy.deepcopy(stored_single)
    return None


def _ensure_brochure_draft(ctx_data: dict, quotation_id: str, target_lang: str, lang_ctx: dict, *, force_brand_from_ctx: bool = False) -> dict:
    draft = _get_stored_brochure_draft(ctx_data, target_lang)
    if not draft:
        draft = _build_brochure_draft_from_lang_ctx(lang_ctx, quotation_id, target_lang)
        _store_brochure_draft(ctx_data, target_lang, draft)
    elif force_brand_from_ctx:
        fresh_document = _build_brochure_draft_from_lang_ctx(lang_ctx, quotation_id, target_lang)
        draft["brand"] = copy.deepcopy(fresh_document.get("brand") or {})
        _store_brochure_draft(ctx_data, target_lang, draft)
    return copy.deepcopy(draft)


def _apply_brochure_draft_to_lang_ctx(lang_ctx: dict, draft: dict):
    apply_quote_document_to_lang_ctx(lang_ctx, draft)


async def _persist_ctx_data(quotation_id: str, ctx_data: dict, commit_message: str):
    quo_dir = os.path.join("published", quotation_id)
    os.makedirs(quo_dir, exist_ok=True)
    if os.getenv("ENVIRONMENT", "local") == "production":
        await publish_file_to_github(
            file_path=f"published/{quotation_id}/ctx.json",
            html_content=json.dumps(ctx_data, ensure_ascii=False, default=str),
            commit_message=commit_message,
        )
    else:
        with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as f:
            json.dump(ctx_data, f, ensure_ascii=False, default=str)
    if quotation_id in quotations:
        quotations[quotation_id]["ctx"] = ctx_data


def _build_publication_storage_keys(quotation_id: str, lang: str, version: int) -> tuple[str, str]:
    return (
        f"quotations/{quotation_id}/publish/{lang}/v{version}/index.html",
        f"quotations/{quotation_id}/publish/{lang}/current/index.html",
    )


def _render_canonical_document_html(document: dict[str, Any], quotation: Any, *, lang: str, view: Literal["web", "print"], version: int = 1) -> str:
    hydrated = _hydrate_r2_asset_urls(_hydrate_canonical_quote_document(document, quotation, lang=lang, revision=int((document.get("meta") or {}).get("revision") or 1)))
    ctx = _build_brochure_render_context({}, hydrated, quotation.id, lang, latest_version=version, preview_mode=view == "web", editor_mode=False)
    template_name = quotation.template_name.replace(".html", "_pdf.html") if view == "print" else quotation.template_name
    return templates.get_template(template_name).render(**ctx)


def _render_pdf_bytes(print_html: str) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright/Chromium is not installed.") from exc
    with sync_playwright() as browser_runtime:
        browser = browser_runtime.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(print_html, wait_until="networkidle")
            return page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
        finally:
            browser.close()


def _legacy_render_react_pdf_bytes(*, hostname: str, release_id: str) -> bytes:
    """Print the private React SSR route; V2 never converts through Jinja.

    The private route resolves its immutable release by ID, not by public host.
    Chromium forbids callers from overriding the ``Host`` header, so use the
    Compose-only origin directly and keep the public hostname out of this
    browser request.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright/Chromium is not installed.") from exc
    quote_generator_url = os.getenv("QUOTE_GENERATOR_INTERNAL_URL", "http://quote-generator:8115").rstrip("/")
    url = f"{quote_generator_url}/internal/releases/{release_id}/pdf"
    with sync_playwright() as browser_runtime:
        browser = browser_runtime.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=60_000)
            page.wait_for_selector('[data-render-ready="true"]', state="attached", timeout=15_000)
            return page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
        finally:
            browser.close()


def _hydrate_canonical_quote_document(
    document: dict[str, Any],
    quotation: Any,
    *,
    lang: str,
    revision: int,
) -> dict[str, Any]:
    normalized = copy.deepcopy(document or {})
    meta = normalized.setdefault("meta", {})
    meta["quotationId"] = quotation.id
    meta["lang"] = lang
    meta["template"] = quotation.template_name
    meta["brandId"] = quotation.brand_id
    if quotation.opportunity_id:
        meta["opportunityId"] = quotation.opportunity_id
    meta["revision"] = revision
    meta["version"] = int(meta.get("version") or quotation.current_version or 1)
    # The document payload is already canonical at this boundary. Preserve the
    # schema marker when older clients omit meta while editing an otherwise V1
    # block document; rich HTML is never reconstructed here.
    meta.setdefault("contentSchemaVersion", 1)
    return normalized


async def _load_canonical_quote_document_from_db(
    quotation_id: str,
    target_lang: str | None = None,
) -> tuple[Any | None, dict[str, Any] | None, str | None]:
    async with _get_db_session_factory()() as session:
        quotation_repo = QuotationRepository(session)
        document_repo = QuotationDocumentRepository(session)

        quotation = await quotation_repo.get_quotation_by_id(quotation_id)
        if quotation is None:
            return None, None, None

        effective_lang = target_lang or quotation.baseline_lang
        stored_document = await document_repo.get_current_document(quotation_id, effective_lang)
        if stored_document is None and effective_lang != quotation.baseline_lang:
            stored_document = await document_repo.get_current_document(quotation_id, quotation.baseline_lang)
            if stored_document is not None:
                effective_lang = quotation.baseline_lang
        if stored_document is None:
            return quotation, None, effective_lang

        document = _hydrate_canonical_quote_document(
            stored_document.document_json,
            quotation,
            lang=effective_lang,
            revision=stored_document.revision,
        )
        return quotation, document, effective_lang


async def _load_latest_quote_request_snapshot_from_db(quotation_id: str) -> dict[str, Any] | None:
    async with _get_db_session_factory()() as session:
        quotation_repo = QuotationRepository(session)
        request_row = await quotation_repo.get_latest_quotation_request(quotation_id)
        return copy.deepcopy(request_row.request_json) if request_row is not None else None


async def _sync_canonical_quote_document_to_ctx(
    quotation_id: str,
    target_lang: str,
    document: dict[str, Any],
    commit_message: str,
) -> dict[str, Any] | None:
    ctx_data = _load_ctx_data(quotation_id)
    if not ctx_data:
        return None
    _store_brochure_draft(ctx_data, target_lang, document)
    try:
        await _persist_ctx_data(quotation_id, ctx_data, commit_message)
    except Exception:
        log.warning(
            "[quotation-v2] Legacy ctx sync failed for %s (%s); canonical document remains in Postgres",
            quotation_id,
            target_lang,
            exc_info=True,
        )
    return ctx_data


def _is_asset_reference(value: Any) -> bool:
    return isinstance(value, dict) and bool(set(value.keys()) & {"assetId", "r2Key", "url", "status"})


def _is_transient_asset_reference(value: dict[str, Any]) -> bool:
    url = str(value.get("url") or "")
    status = str(value.get("status") or "")
    return url.startswith("blob:") or status in {"uploading", "error"}


def _sanitize_canonical_asset_state(document: Any, fallback_document: Any = None) -> Any:
    if isinstance(document, list):
        fallback_items = fallback_document if isinstance(fallback_document, list) else []
        return [
            _sanitize_canonical_asset_state(
                item,
                fallback_items[index] if index < len(fallback_items) else None,
            )
            for index, item in enumerate(document)
        ]

    if isinstance(document, dict):
        if _is_asset_reference(document):
            asset = {
                "assetId": document.get("assetId") or "",
                "r2Key": document.get("r2Key") or "",
                "url": document.get("url") or "",
                "status": document.get("status") or "ready",
                "altText": document.get("altText") or "",
            }
            if _is_transient_asset_reference(asset):
                fallback_asset = fallback_document if isinstance(fallback_document, dict) else None
                if fallback_asset and _is_asset_reference(fallback_asset):
                    return {
                        "assetId": fallback_asset.get("assetId") or "",
                        "r2Key": fallback_asset.get("r2Key") or "",
                        "url": fallback_asset.get("url") or "",
                        "status": fallback_asset.get("status") or "ready",
                        "altText": fallback_asset.get("altText") or "",
                    }
                return {"assetId": "", "r2Key": "", "url": "", "status": "ready", "altText": ""}
            return asset

        fallback_map = fallback_document if isinstance(fallback_document, dict) else {}
        return {
            key: _sanitize_canonical_asset_state(value, fallback_map.get(key))
            for key, value in document.items()
        }

    return document


def _hydrate_r2_asset_urls(document: Any) -> Any:
    """Derive render URLs from canonical r2Key values without changing identity."""
    if isinstance(document, list):
        return [_hydrate_r2_asset_urls(item) for item in document]
    if not isinstance(document, dict):
        return document
    if _is_asset_reference(document):
        asset = dict(document)
        r2_key = str(asset.get("r2Key") or "")
        if r2_key and settings.has_r2_configuration:
            asset["url"] = _get_media_library_service().storage.build_public_url(r2_key)
        return asset
    return {key: _hydrate_r2_asset_urls(value) for key, value in document.items()}


def _draft_asset_public_path(quotation_id: str, filename: str) -> str:
    return f"/published/{quotation_id}/draft_assets/{filename}"


def _iter_exception_chain(exc: BaseException):
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _is_database_unavailable_error(exc: BaseException) -> bool:
    for current in _iter_exception_chain(exc):
        module_name = current.__class__.__module__
        message = str(current).lower()
        if module_name.startswith("sqlalchemy") or module_name.startswith("asyncpg"):
            return True
        if isinstance(current, socket.gaierror):
            return True
        if isinstance(current, ConnectionRefusedError):
            return True
        if isinstance(current, OSError) and getattr(current, "errno", None) in {8, 16, 61, 111}:
            return True
        if any(
            token in message
            for token in (
                "nodename nor servname provided",
                "connection refused",
                "could not translate host name",
                "device or resource busy",
                "temporary failure in name resolution",
                "name or service not known",
            )
        ):
            return True
    return False


async def _store_uploaded_draft_asset(
    *,
    quotation_id: str,
    file_name: str,
    content: bytes,
    declared_mime_type: str | None,
) -> dict[str, Any]:
    ctx_data = _load_ctx_data(quotation_id)
    if not ctx_data:
        raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")

    media_service = _get_media_service()
    prepared = await media_service.prepare_upload(
        content=content,
        declared_mime_type=declared_mime_type,
    )
    safe_name = f"{uuid.uuid4().hex}.{prepared.extension}"
    rel_path = f"{quotation_id}/draft_assets/{safe_name}"
    local_path = os.path.join("published", rel_path)

    if os.getenv("ENVIRONMENT", "local") == "production":
        await publish_file_to_github(
            file_path=f"published/{rel_path}",
            html_content=prepared.content,
            commit_message=f"Upload brochure asset for quotation {quotation_id} ({safe_name})",
        )
    else:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(prepared.content)

    asset_url = _draft_asset_public_path(quotation_id, safe_name)
    return {
        "assetId": safe_name,
        "quotationId": quotation_id,
        "status": "ready",
        "url": asset_url,
        "originalUrl": asset_url,
        "previewUrl": asset_url,
        "width": prepared.width,
        "height": prepared.height,
        "storageMode": "draft_assets",
    }


# Router modules receive all legacy-compatible runtime hooks here.  Lambdas
# deliberately resolve attributes at request time so the established test and
# Compose override seams remain intact without a router importing ``main``.
configure_v2_runtime(
    media_service_provider=lambda: _get_media_service(),
    session_factory_provider=lambda: _get_db_session_factory(),
    load_context_provider=lambda quotation_id: _load_ctx_data(quotation_id),
    database_unavailable_predicate=lambda exc: _is_database_unavailable_error(exc),
    draft_asset_store=lambda **kwargs: _store_uploaded_draft_asset(**kwargs),
    travel_designer_serializer=lambda profile: _serialize_travel_designer(profile),
    quotation_workflow_loader=lambda quotation_id: _canonical_workflow(quotation_id),
)


def _build_itinerary_ctx(itinerary_id: str, payload: DetailItineraryPayload, hero_image_url: str, destinations: list[dict], lang: str = "en", template_name: str = "detail_itinerary_landingpage_template.html"):
    """Build rendering context for the detailed itinerary landing page."""
    default_img = "/assets/vietnam-safar-logo.png"
    seller = payload.seller
    seller_name  = (seller.companyName if seller else None) or "Vietnam Safar – Discovery Asia Travel Group"
    seller_email = (seller.email if seller else None) or "sales@vietnamsafar.vn"
    seller_phone = (seller.phone if seller else None) or "+84 911 538 738"

    tour_title    = truncate_text(payload.tourTitle, 70)
    prepared_for  = truncate_text(payload.preparedFor, 60)
    duration_lbl  = payload.duration.label or f"{payload.duration.days}D{payload.duration.nights}"
    travel_dates  = payload.travelDates.displayText or f"{payload.travelDates.startDate} – {payload.travelDates.endDate}"
    guests_txt    = truncate_text(payload.guests.displayText or f"{payload.guests.totalGuests} guests", 100)
    route_txt     = " – ".join(payload.route)
    nationality   = truncate_text(payload.nationality or "", 60)
    travel_style  = truncate_text(" | ".join(payload.travelStyle) if payload.travelStyle else "Private", 100)

    # Narrative overview
    overview_paras = [truncate_text(p, 500) for p in payload.programOverview.paragraphs] if payload.programOverview and payload.programOverview.paragraphs else []
    overview_heading = truncate_text(payload.programOverview.heading or "PROGRAM OVERVIEW", 60) if payload.programOverview else "PROGRAM OVERVIEW"
    lede = truncate_text(overview_paras[0] if overview_paras else "A detailed booking itinerary crafted for your journey.", 500)

    # Translate destinations name for multi-language
    translated_destinations = []
    for d in destinations:
        d_copy = d.copy()
        raw_name = d_copy.get("name", "")
        d_copy["name"] = translate_filter(raw_name, lang)
        translated_destinations.append(d_copy)
    destinations = translated_destinations

    # Translate destinations name for multi-language
    translated_destinations = []
    for d in destinations:
        d_copy = d.copy()
        raw_name = d_copy.get("name", "")
        d_copy["name"] = translate_filter(raw_name, lang)
        translated_destinations.append(d_copy)
    destinations = translated_destinations

    # Gallery helpers
    def _d_img(i): return destinations[i].get("image_url", default_img) if i < len(destinations) else default_img
    def _d_name(i): return truncate_text(destinations[i].get("name", ""), 40) if i < len(destinations) else ""

    img_0 = hero_image_url
    img_1 = _d_img(0)
    img_2 = _d_img(1)
    img_3 = _d_img(2)
    img_4 = _d_img(3)

    # Highlight experiences — first 3 itinerary days
    experiences = []
    for i, day in enumerate(payload.itinerary[:3]):
        title = day.title
        if not title or title.lower().startswith("explore "):
            city = day.destinations[0] if (day.destinations and day.destinations[0]) else (day.overnight or "Vietnam")
            title = get_luxury_day_title(city, day.dayNumber, lang)
        else:
            title = truncate_text(title, 80)
        desc = truncate_text(day.description[0] if day.description else f"{translate_filter('Day', lang)} {day.dayNumber} of the journey.", 160)
        experiences.append({"num": f"{i+1:02d}", "title": title, "desc": desc})
    while len(experiences) < 3:
        experiences.append({"num": f"{len(experiences)+1:02d}", "title": "Premium Experience",
                            "desc": "A carefully curated moment in this journey."})

    default_inclusions = [
        {"title": "Handpicked Accommodation", "desc": "Carefully selected hotels and stays as detailed in your journey proposal."},
        {"title": "Private Transportation", "desc": "Private ground transportation and scheduled transfers throughout the journey, as specified in the itinerary."},
        {"title": "Curated Experiences", "desc": "Entrance arrangements and experiences included as outlined in your itinerary."},
        {"title": "Expert Local Guidance", "desc": "Services of carefully selected, licensed local guides where specified."},
        {"title": "Dining Experiences", "desc": "Meals and dining arrangements as detailed in the itinerary."},
        {"title": "Journey Connections", "desc": "Domestic flights, rail journeys, ferries, or other transportation included where specifically stated in the itinerary."}
    ]
    default_exclusions = [
        "International flights",
        "Visa fees and travel documentation",
        "Travel insurance",
        "Personal expenses",
        "Optional experiences not specified in the itinerary",
        "Tips and gratuities",
        "Any services not expressly listed as included"
    ]

    if getattr(payload, "inclusions", None):
        inc_lines = [translate_filter(truncate_text(x, 120), lang) for x in payload.inclusions]
    else:
        inc_lines = [
            {
                "title": translate_filter(item["title"], lang),
                "desc": translate_filter(item["desc"], lang)
            } for item in default_inclusions
        ]
        
    if getattr(payload, "exclusions", None):
        exc_lines = [translate_filter(truncate_text(x, 120), lang) for x in payload.exclusions]
    else:
        exc_lines = [translate_filter(truncate_text(x, 120), lang) for x in default_exclusions]

    inclusions_title = translate_filter("What Your Journey Includes", lang)
    inclusions_lede = translate_filter("Your journey has been thoughtfully arranged to ensure a seamless and comfortable experience throughout.", lang)
    exclusions_title = translate_filter("Exclusions", lang)
    exclusions_lede = translate_filter("To keep your journey transparent and clearly defined, the following are not included unless specifically stated otherwise:", lang)

    # Pricing fields from payload
    main_option   = next((o for o in payload.pricing.priceOptions if o.isConfirmedMainOption), None) if payload.pricing else None
    currency      = payload.pricing.currency if payload.pricing else "USD"
    if main_option:
        price_per_pax = main_option.pricePerPerson.displayText or f"{currency} {main_option.pricePerPerson.amount:,.0f} / person"
        total_price   = main_option.totalPrice.displayText or f"{currency} {main_option.totalPrice.amount:,.0f}"
        grand_total_num = main_option.totalPrice.amount
    else:
        price_per_pax = ""
        total_price   = ""
        grand_total_num = 0.0

    # Map daily services
    days_list = []
    for day in payload.itinerary:
        day_date = day.date
        
        # Match hotels: check-in date <= day_date < check-out date
        day_hotels = []
        for idx, h in enumerate(payload.hotels):
            if h.checkInDate and h.checkOutDate and h.checkInDate <= day_date < h.checkOutDate:  # type: ignore
                h_dict = h.model_dump(mode="json")
                h_dict["_index"] = idx
                h_dict["name"] = truncate_text(h_dict.get("name"), 80)
                h_dict["roomType"] = truncate_text(h_dict.get("roomType"), 80)
                h_dict["destination"] = truncate_text(h_dict.get("destination"), 60)
                h_dict["notes"] = truncate_text(h_dict.get("notes"), 150)
                day_hotels.append(h_dict)
        
        # Match activities
        day_activities = []
        for idx, act in enumerate(payload.activities):
            if act.date == day_date:
                act_dict = act.model_dump(mode="json")
                act_dict["_index"] = idx
                act_dict["activityName"] = truncate_text(act_dict.get("activityName"), 80)
                act_dict["operator"] = truncate_text(act_dict.get("operator"), 80)
                act_dict["notes"] = truncate_text(act_dict.get("notes"), 150)
                day_activities.append(act_dict)

        # Match transfers
        day_transfers = []
        for idx, tx in enumerate(payload.transfers):
            if tx.date == day_date:
                tx_dict = tx.model_dump(mode="json")
                tx_dict["_index"] = idx
                tx_dict["vehicleRequirement"] = truncate_text(tx_dict.get("vehicleRequirement"), 80)
                tx_dict["fromLocation"] = truncate_text(tx_dict.get("fromLocation"), 60)
                tx_dict["toLocation"] = truncate_text(tx_dict.get("toLocation"), 60)
                tx_dict["notes"] = truncate_text(tx_dict.get("notes"), 150)
                day_transfers.append(tx_dict)

        # Match flights
        day_flights = []
        for idx, fl in enumerate(payload.flights):
            if fl.date == day_date:
                fl_dict = fl.model_dump(mode="json")
                fl_dict["_index"] = idx
                fl_dict["flightNumber"] = truncate_text(fl_dict.get("flightNumber"), 30)
                fl_dict["airline"] = truncate_text(fl_dict.get("airline"), 50)
                fl_dict["fromCity"] = truncate_text(fl_dict.get("fromCity"), 40)
                fl_dict["toCity"] = truncate_text(fl_dict.get("toCity"), 40)
                fl_dict["notes"] = truncate_text(fl_dict.get("notes"), 150)
                day_flights.append(fl_dict)

        # Match guides
        day_guides = []
        for idx, gd in enumerate(payload.guides):
            if gd.dates and day_date in gd.dates:
                gd_dict = gd.model_dump(mode="json")
                gd_dict["_index"] = idx
                gd_dict["guideName"] = truncate_text(gd_dict.get("guideName"), 60)
                gd_dict["destination"] = truncate_text(gd_dict.get("destination"), 60)
                gd_dict["notes"] = truncate_text(gd_dict.get("notes"), 150)
                day_guides.append(gd_dict)

        title = day.title
        if not title or title.lower().startswith("explore "):
            city = day.destinations[0] if (day.destinations and day.destinations[0]) else (day.overnight or "Vietnam")
            title = get_luxury_day_title(city, day.dayNumber, lang)
        else:
            title = truncate_text(title, 80)

        days_list.append({
            "dayNumber": day.dayNumber,
            "date": day_date,
            "title": title,
            "description": [truncate_text(d, 350) for d in day.description],
            "overnight": translate_filter(truncate_text(day.overnight, 40), lang),
            "meals": [truncate_text(m, 80) for m in (day.meals or [])],
            "destinations": [translate_filter(truncate_text(dest, 40), lang) for dest in (day.destinations or [])],
            "activities": [truncate_text(act, 120) for act in (day.activities or [])],
            "optionalActivities": [truncate_text(opt, 120) for opt in (day.optionalActivities or [])],
            "notes": [translate_filter(truncate_text(nt, 150), lang) for nt in (day.notes or [])],
            "booked_hotels": day_hotels,
            "booked_activities": day_activities,
            "booked_transfers": day_transfers,
            "booked_flights": day_flights,
            "booked_guides": day_guides,
        })

    # Multi-language support for dynamic itinerary subtitle
    days_cnt = len(payload.itinerary)
    if lang == "vi":
        itinerary_p_val = f"Hành trình riêng tư {duration_lbl} của bạn — {days_cnt} ngày, được thiết kế tỉ mỉ."
    elif lang == "ar":
        itinerary_p_val = f"رحلتك الخاصة {duration_lbl} — {days_cnt} يوماً، تم تصميمها بعناية."
    else:
        itinerary_p_val = f"Your private {duration_lbl} journey — {days_cnt} days, carefully crafted."

    # Journey investment header translation
    pricing_h2_title = translate_filter("Journey Investment", lang)
    pricing_h2_val = f"{pricing_h2_title}: {total_price}" if total_price else ""

    return {
        "itinerary_id":     itinerary_id,
        "img_0": img_0, "img_1": img_1, "img_2": img_2, "img_3": img_3, "img_4": img_4,
        "destinations":     destinations,
        # Hero / header
        "quotation_title":  truncate_text(payload.quotationTitle, 100),
        "tour_title":       tour_title,
        "kicker":           f"{translate_filter('Confirmed Booking Itinerary', lang)} • {duration_lbl} • {travel_dates}",
        "lede":             lede,
        # Guest & trip meta
        "customer_name":    prepared_for,
        "nationality":      nationality,
        "travel_style":     travel_style,
        "guests_txt":       guests_txt,
        "guests_adults":    payload.guests.adults,
        "guests_children":   payload.guests.children,
        "route_txt":        route_txt,
        "duration_label":   duration_lbl,
        "travel_dates":     travel_dates,
        # Seller / contact
        "seller_name":      seller_name,
        "seller_email":     seller_email,
        "contact":          seller_phone,
        "contact_web":      "www.vietnamsafar.vn",
        "contact_phone":    seller_phone,
        "quotation_number": payload.quotationNumber or itinerary_id,
        "valid_until":      "N/A",
        # Overview
        "overview_heading": translate_filter(overview_heading, lang),
        "overview_h2":      f"{prepared_for} — {tour_title}",
        "overview_p":       " ".join(overview_paras),
        "overview_paras":   overview_paras,
        # Experiences
        "experiences":      experiences,
        # Daily Itinerary with matched services
        "itinerary":        days_list,
        # Consolidated list of booked services (useful for summary tabs/cards!)
        "hotels":           [
            {
                **h.model_dump(mode="json"),
                "name": truncate_text(h.name, 80),
                "roomType": truncate_text(h.roomType, 80),
                "destination": truncate_text(h.destination, 60),
                "notes": truncate_text(h.notes, 150)
            } for h in payload.hotels
        ],
        "activities":       [
            {
                **act.model_dump(mode="json"),
                "activityName": truncate_text(act.activityName, 80),
                "operator": truncate_text(act.operator, 80),
                "notes": truncate_text(act.notes, 150)
            } for act in payload.activities
        ],
        "transfers":        [
            {
                **tx.model_dump(mode="json"),
                "vehicleRequirement": truncate_text(tx.vehicleRequirement, 80),
                "fromLocation": truncate_text(tx.fromLocation, 60),
                "toLocation": truncate_text(tx.toLocation, 60),
                "notes": truncate_text(tx.notes, 150)
            } for tx in payload.transfers
        ],
        "flights":          [
            {
                **fl.model_dump(mode="json"),
                "flightNumber": truncate_text(fl.flightNumber, 30),
                "airline": truncate_text(fl.airline, 50),
                "fromCity": truncate_text(fl.fromCity, 40),
                "toCity": truncate_text(fl.toCity, 40),
                "notes": truncate_text(fl.notes, 150)
            } for fl in payload.flights
        ],
        "guides":           [
            {
                **gd.model_dump(mode="json"),
                "guideName": truncate_text(gd.guideName, 60),
                "destination": truncate_text(gd.destination, 60),
                "notes": truncate_text(gd.notes, 150)
            } for gd in payload.guides
        ],
        # Inclusions / exclusions
        "inclusions":       inc_lines,
        "exclusions":       exc_lines,
        "inclusions_title": inclusions_title,
        "inclusions_lede": inclusions_lede,
        "exclusions_title": exclusions_title,
        "exclusions_lede": exclusions_lede,
        "notes":            [truncate_text(x, 200) for x in (payload.notes or [])],
        # Pricing section
        "currency":       currency,
        "pricing_title":  translate_filter(truncate_text(payload.pricing.pricingTitle or "Journey Investment" if payload.pricing else "", 100), lang),
        "pricing_basis":  translate_filter(truncate_text(payload.pricing.basis or "Indicative basis" if payload.pricing else "", 80), lang),
        "price_options":  [
            {
                **o.model_dump(mode="json"),
                "hotelCategory": truncate_text(o.hotelCategory, 80),
                "optionName": truncate_text(o.optionName, 80),
                "notes": [truncate_text(n, 150) for n in o.notes] if o.notes else []
            } for o in payload.pricing.priceOptions
        ] if payload.pricing else [],
        "price_per_pax":  price_per_pax,
        "total_price":    total_price,
        "grand_total":    grand_total_num,
        "subtotal":       payload.pricing.subtotal if payload.pricing else 0.0,
        "tax_total":      payload.pricing.taxTotal if payload.pricing else 0.0,
        "pricing_h2":     pricing_h2_val,
        "pricing_p":      f"{translate_filter('Total', lang)}: {guests_txt}. {translate_filter('Currency', lang)}: {currency}." if total_price else "",
        # Footer
        "footer_text":      f"{tour_title} — {translate_filter('Detailed booking itinerary prepared for', lang)} {prepared_for}.",
        "lang":             lang,
        "template_name":    template_name,
        "translation_status": _load_translation_status(itinerary_id, default_lang=lang),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.post("/quotations/b2c")
async def create_quotation_b2c(request: Request):
    """
    Receives structured B2C quotation data,
    renders a B2C Jinja2 landing page template, stores it, and returns the preview URL.
    """
    body = await request.json()
    log.debug("[/quotations/b2c] Incoming keys: %s", list(body.keys()))

    # Unwrap ChatGPT Action wrapper if present
    data = body.get("params", body)
    log.debug("[/quotations/b2c] Data keys after unwrap: %s", list(data.keys()))
    lang = data.get("language") or data.get("lang") or request.query_params.get("lang") or request.query_params.get("language") or "en"
    if lang not in ("en", "vi", "ar"):
        lang = "en"

    try:
        payload = TourQuotationPayload.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        log.error("[/quotations/b2c] Pydantic validation failed — %d error(s):\n%s",
                  len(errors), json.dumps(errors, indent=2, default=str))
        return JSONResponse(status_code=422, content={"detail": errors,
            "hint": "Field path is in 'loc'. Check which required field is missing."})

    quotation_id = f"quo_{uuid.uuid4().hex[:12]}"

    # ── Extract destinations from route + itinerary for the gallery ──────────
    route_list = []
    for d in payload.itinerary:
        if d.destination and d.destination not in route_list:
            route_list.append(d.destination)
    route_text = " ".join(route_list)
    itinerary_text = " ".join(
        (day.destination or "") + " " + (day.summary or "")
        for day in payload.itinerary
    )
    text_context = route_text + " " + itinerary_text

    from image_selector import extract_and_map_destinations, get_random_image_for_province, get_all_images_for_province
    destinations = await extract_and_map_destinations(text_context, max_items=None)
    
    # Resolve image urls for each destination
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))
        d["images"] = get_all_images_for_province(d.get("slug"))

    log.debug("[/quotations/b2c] Extracted destinations: %s", destinations)

    default_img = "/assets/vietnam-safar-logo.png"
    
    # Hero image: Pick a random image from the resolved destinations, or default
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/quotations/b2c] Hero image resolved: %s", hero_image_url)

    brand_config = resolve_brand(request, payload.model_dump(mode="json"))
    ctx = _build_ctx(quotation_id, payload, hero_image_url, destinations, lang=lang, template_name="vietnam_heritage_luxury_b2c.html", brand=brand_config)
    ctx["baseline_payload"] = payload.model_dump(mode="json")
    ctx["baseline_lang"] = lang
    ctx["brand"] = brand_config
    ctx["translations"] = {}
    ctx["available_langs"] = [lang]
    ctx["translation_status"] = {"baseline_lang": lang, "available_langs": [lang]}

    if "designer_img" in data:
        ctx["designer_img"] = data["designer_img"]

    # ── Render landing page HTML ───────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    tmpl_lp  = templates.get_template("vietnam_heritage_luxury_b2c.html")
    tmpl_pdf = templates.get_template("vietnam_heritage_luxury_b2c_pdf.html")

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render,  **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )
    initial_html_sync = _capture_html_sync_state(rendered_html)
    initial_html_sync["captured_from_version"] = 1
    ctx.setdefault("html_sync", {})[lang] = initial_html_sync

    # ── Update in-memory store ────────────────────────────────────────────
    quotations[quotation_id] = {
        "payload":       payload.model_dump(mode="json"),
        "ctx":           ctx,
        "html":          rendered_html,
        "pdf_html":      rendered_pdf,
        "status":        "pending",
        "published_url": None,
        "pdf_url":       None,
        "version":       0,
    }

    # ── Publish to GitHub or save locally with language suffix ──────────────
    sfx = f"_{lang}" if lang != "en" else ""
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

    if ENVIRONMENT == "production":
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            log.error("[/quotations/b2c] GITHUB_TOKEN or GITHUB_REPO not set — cannot persist on Vercel.")
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: GITHUB_TOKEN / GITHUB_REPO env vars are missing.",
            )
        try:
            # Publish landing page, PDF, ctx, and payload in parallel
            # Publish files sequentially to avoid 409 conflict
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/v1{sfx}.html",
                html_content=rendered_html,
                commit_message=f"Publish B2C quotation {quotation_id} v1{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/pdf{sfx}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish B2C PDF view for quotation {quotation_id} pdf{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/pdf_{lang}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish B2C PDF view for quotation {quotation_id} pdf_{lang}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/ctx.json",
                html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                commit_message=f"Publish B2C Context for {quotation_id}",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/payload.json",
                html_content=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
                commit_message=f"Publish B2C Payload for {quotation_id}",
            )
            # Initialize and save translation status
            await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
            
            quotations[quotation_id]["status"]        = "published"
            quotations[quotation_id]["published_url"] = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
            quotations[quotation_id]["pdf_url"]       = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf"
            quotations[quotation_id]["version"]       = 1
            log.info("[/quotations/b2c] ✓ v1{sfx} + pdf{sfx} committed to GitHub.")
        except Exception as exc:
            log.exception("[/quotations/b2c] GitHub publish FAILED for %s: %s", quotation_id, exc)
            raise HTTPException(
                status_code=502,
                detail=f"GitHub publish failed: {exc}. Check GITHUB_TOKEN permissions.",
            )

    else:
        # ── Localhost only: persist to disk ────────────────────────────────────
        quo_dir = os.path.join("published", quotation_id)
        os.makedirs(quo_dir, exist_ok=True)
        with open(os.path.join(quo_dir, f"v1{sfx}.html"),  "w", encoding="utf-8") as _f:
            _f.write(rendered_html)
        with open(os.path.join(quo_dir, f"pdf{sfx}.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(quo_dir, f"pdf_{lang}.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as _f:
            json.dump(ctx, _f, ensure_ascii=False, default=str)
        with open(os.path.join(quo_dir, "payload.json"), "w", encoding="utf-8") as _f:
            json.dump(payload.model_dump(mode="json"), _f, ensure_ascii=False)
        await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
        
        quotations[quotation_id]["status"]  = "published"
        quotations[quotation_id]["version"] = 1
        log.info("[/quotations/b2c] Localhost: v1{sfx}.html + pdf{sfx}.html + ctx.json written to disk.")

    log.info("[/quotations/b2c] ✓ id=%s  preparedFor=%s  days=%d",
             quotation_id, payload.journeyGlance.guestProfile, len(payload.itinerary))

    quotation_url = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
    return {
        "quotationId":  quotation_id,
        "status":       "published",
        "version":      1,
        "message":      "B2C Landing page published. Open quotationUrl to preview and edit inline.",
        "quotationUrl": quotation_url,
        "pdfUrl":       f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf",
    }


@app.post("/quotations")
async def create_quotation(request: Request):
    """
    Receives structured quotation data from a ChatGPT Custom GPT Action,
    renders a Jinja2 landing page template, stores it, and returns the preview URL.
    """
    body = await request.json()
    log.debug("[/quotations] Incoming keys: %s", list(body.keys()))

    # Unwrap ChatGPT Action wrapper if present
    data = body.get("params", body)
    log.debug("[/quotations] Data keys after unwrap: %s", list(data.keys()))
    lang = data.get("language") or data.get("lang") or request.query_params.get("lang") or request.query_params.get("language") or "en"
    if lang not in ("en", "vi", "ar"):
        lang = "en"
    template_name = data.get("template_name") or data.get("template")
    if template_name not in LEGACY_QUOTATION_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"/quotations only supports legacy templates: {', '.join(sorted(LEGACY_QUOTATION_TEMPLATES))}. Use /api/v2/quotations for brochure quotes.",
        )

    try:
        payload = TourQuotationPayload.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        log.error("[/quotations] Pydantic validation failed — %d error(s):\n%s",
                  len(errors), json.dumps(errors, indent=2, default=str))
        return JSONResponse(status_code=422, content={"detail": errors,
            "hint": "Field path is in 'loc'. Check which required field is missing."})

    quotation_id = f"quo_{uuid.uuid4().hex[:12]}"

    # ── Extract destinations from route + itinerary for the gallery ──────────
    route_list = []
    for d in payload.itinerary:
        if d.destination and d.destination not in route_list:
            route_list.append(d.destination)
    route_text = " ".join(route_list)
    itinerary_text = " ".join(
        (day.destination or "") + " " + (day.summary or "")
        for day in payload.itinerary
    )
    text_context = route_text + " " + itinerary_text

    from image_selector import extract_and_map_destinations, get_random_image_for_province, get_all_images_for_province
    destinations = await extract_and_map_destinations(text_context, max_items=None)
    
    # Resolve image urls for each destination
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))
        d["images"] = get_all_images_for_province(d.get("slug"))

    log.debug("[/quotations] Extracted destinations: %s", destinations)

    default_img = "/assets/vietnam-safar-logo.png"
    
    # Hero image: Pick a random image from the resolved destinations, or default
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/quotations] Hero image resolved: %s", hero_image_url)

    brand_config = resolve_brand(request, payload.model_dump(mode="json"))
    ctx = _build_ctx(quotation_id, payload, hero_image_url, destinations, lang=lang, template_name=template_name, brand=brand_config)
    ctx["baseline_payload"] = payload.model_dump(mode="json")
    ctx["baseline_lang"] = lang
    ctx["translations"] = {}
    ctx["available_langs"] = [lang]
    ctx["translation_status"] = {"baseline_lang": lang, "available_langs": [lang]}
    ctx["brand"] = brand_config
    ctx["quotation_id"] = quotation_id
    ctx["opportunity_id"] = payload.quotationNumber or payload.journeyGlance.tourCode or quotation_id

    if "designer_img" in data and data["designer_img"]:
        ctx["designer_img"] = data["designer_img"]
    else:
        ctx["designer_img"] = "/assets/dias_team/hieu.jpg"

    # ── Render landing page HTML ───────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    base_tmpl = ctx.get("template_name", "vietnam_luxury_brosure.html")
    tmpl_lp  = templates.get_template(base_tmpl)
    tmpl_pdf = templates.get_template(base_tmpl.replace(".html", "_pdf.html"))

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render,  **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )
    initial_html_sync = _capture_html_sync_state(rendered_html)
    initial_html_sync["captured_from_version"] = 1
    ctx.setdefault("html_sync", {})[lang] = initial_html_sync

    # ── Update in-memory store ────────────────────────────────────────────
    quotations[quotation_id] = {
        "payload":       payload.model_dump(mode="json"),
        "ctx":           ctx,
        "html":          rendered_html,
        "pdf_html":      rendered_pdf,
        "status":        "pending",
        "published_url": None,
        "pdf_url":       None,
        "version":       0,
    }

    # ── Publish to GitHub or save locally with language suffix ──────────────
    sfx = f"_{lang}" if lang != "en" else ""
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

    if ENVIRONMENT == "production":
        # Hard requirement: GITHUB_TOKEN and GITHUB_REPO must be configured.
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            log.error("[/quotations] GITHUB_TOKEN or GITHUB_REPO not set — cannot persist on Vercel.")
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: GITHUB_TOKEN / GITHUB_REPO env vars are missing.",
            )
        try:
            # Publish landing page, PDF, ctx, and payload in parallel
            # Publish files sequentially to avoid 409 conflict
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/v1{sfx}.html",
                html_content=rendered_html,
                commit_message=f"Publish quotation {quotation_id} v1{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/pdf{sfx}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish B2B PDF view for quotation {quotation_id} pdf{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/pdf_{lang}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish B2B PDF view for quotation {quotation_id} pdf_{lang}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/ctx.json",
                html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                commit_message=f"Publish B2B Context for {quotation_id}",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/payload.json",
                html_content=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
                commit_message=f"Publish B2B Payload for {quotation_id}",
            )
            # Initialize and save translation status
            await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
            
            quotations[quotation_id]["status"]        = "published"
            quotations[quotation_id]["published_url"] = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
            quotations[quotation_id]["pdf_url"]       = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf"
            quotations[quotation_id]["version"]       = 1
            log.info("[/quotations] ✓ v1{sfx} + pdf{sfx} committed to GitHub.")
        except Exception as exc:
            log.exception("[/quotations] GitHub publish FAILED for %s: %s", quotation_id, exc)
            raise HTTPException(
                status_code=502,
                detail=f"GitHub publish failed: {exc}. Check GITHUB_TOKEN permissions.",
            )

    else:
        # ── Localhost only: persist to disk ────────────────────────────────────
        quo_dir = os.path.join("published", quotation_id)
        os.makedirs(quo_dir, exist_ok=True)
        with open(os.path.join(quo_dir, f"v1{sfx}.html"),  "w", encoding="utf-8") as _f:
            _f.write(rendered_html)
        with open(os.path.join(quo_dir, f"pdf{sfx}.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(quo_dir, f"pdf_{lang}.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as _f:
            json.dump(ctx, _f, ensure_ascii=False, default=str)
        with open(os.path.join(quo_dir, "payload.json"), "w", encoding="utf-8") as _f:
            json.dump(payload.model_dump(mode="json"), _f, ensure_ascii=False)
        await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
        
        quotations[quotation_id]["status"]  = "published"
        quotations[quotation_id]["version"] = 1
        log.info("[/quotations] Localhost: v1{sfx}.html + pdf{sfx}.html + ctx.json written to disk.")

    log.info("[/quotations] ✓ id=%s  preparedFor=%s  days=%d  route=%s",
             quotation_id, payload.journeyGlance.guestProfile,
             len(payload.itinerary), " > ".join(route_list))

    # quotationUrl should be the stable permalink API endpoint
    quotation_url = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
    return {
        "quotationId":  quotation_id,
        "status":       "published",
        "version":      1,
        "message":      "Landing page published. Open quotationUrl to preview and edit inline.",
        "quotationUrl": quotation_url,
        "pdfUrl":       f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf",
    }


@app.post("/api/v2/legacy-create-quotations", include_in_schema=False)
async def create_quotation_v2_legacy(payload: CreateQuoteRequestV1):
    raise HTTPException(
        status_code=410,
        detail={
            "message": "This legacy V2 creation endpoint has been retired.",
            "use": "POST /api/v2/quotations",
        },
    )
    # Kept below temporarily for source-level migration reference only.  The
    # React V2 boundary must never execute this Jinja flow.
    payload, resolved_destination_refs = await _canonicalize_quote_destinations(payload)
    quotation_id = f"quo_{uuid.uuid4().hex[:12]}"
    generation_service = QuoteGenerationService()
    generated_document = await generation_service.generate(payload)
    document = generated_document.model_dump(mode="json")
    document = await _apply_create_fact_media_slots(document, payload.factMediaSlots)
    document.setdefault("meta", {})
    document["meta"]["quotationId"] = quotation_id
    document["meta"]["version"] = 1
    document["meta"]["status"] = "draft"
    document["meta"]["template"] = BROCHURE_TEMPLATE_NAME
    document["meta"]["resolvedDestinationRefs"] = resolved_destination_refs
    lang = payload.lang if payload.lang in ("en", "vi", "ar") else "en"
    document = _validate_quote_document_or_422(document)
    destinations = _build_seed_destinations_from_quote_document(document)
    ctx: dict[str, Any] = {
        "baseline_lang": lang,
        "translations": {},
        "available_langs": [lang],
        "translation_status": {"baseline_lang": lang, "available_langs": [lang]},
        "brand": _brand_config_from_quote_document(document),
        "quotation_id": quotation_id,
        "opportunity_id": payload.opportunity_id or quotation_id,
        "createQuoteRequestV1": payload.model_dump(mode="json"),
        "template_name": BROCHURE_TEMPLATE_NAME,
        "destinations": destinations,
        "route_stops": [],
    }
    document = _store_brochure_draft(ctx, lang, document)
    ctx = _merge_brochure_render_context(
        ctx,
        document,
        quotation_id,
        lang,
        latest_version=1,
        editor_mode=False,
        preview_mode=False,
    )
    ctx["createQuoteRequestV1"] = payload.model_dump(mode="json")
    ctx["template_name"] = BROCHURE_TEMPLATE_NAME
    ctx["destinations"] = destinations

    loop = asyncio.get_event_loop()
    tmpl_lp = templates.get_template(BROCHURE_TEMPLATE_NAME)
    tmpl_pdf = templates.get_template(BROCHURE_TEMPLATE_NAME.replace(".html", "_pdf.html"))
    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render, **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )
    initial_html_sync = _capture_html_sync_state(rendered_html)
    initial_html_sync["captured_from_version"] = 1
    ctx.setdefault("html_sync", {})[lang] = initial_html_sync

    quotations[quotation_id] = {
        "payload": None,
        "ctx": ctx,
        "html": rendered_html,
        "pdf_html": rendered_pdf,
        "status": "pending",
        "published_url": None,
        "pdf_url": None,
        "version": 0,
    }

    sfx = f"_{lang}" if lang != "en" else ""
    environment = os.getenv("ENVIRONMENT", "local")
    pdf_public_url = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf"
    if environment == "production":
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: GITHUB_TOKEN / GITHUB_REPO env vars are missing.",
            )
        try:
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/v1{sfx}.html",
                html_content=rendered_html,
                commit_message=f"Publish v2 quotation {quotation_id} v1{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/pdf{sfx}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish v2 PDF view for quotation {quotation_id} pdf{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/pdf_{lang}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish v2 PDF view for quotation {quotation_id} pdf_{lang}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/ctx.json",
                html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                commit_message=f"Publish v2 context for {quotation_id}",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/document.json",
                html_content=json.dumps(document, ensure_ascii=False),
                commit_message=f"Publish v2 canonical document for {quotation_id}",
            )
            await publish_file_to_github(
                file_path=f"published/{quotation_id}/create_request_v2.json",
                html_content=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
                commit_message=f"Publish v2 request snapshot for {quotation_id}",
            )
            await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
            quotations[quotation_id]["status"] = "published"
            quotations[quotation_id]["published_url"] = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
            quotations[quotation_id]["pdf_url"] = pdf_public_url
            quotations[quotation_id]["version"] = 1
        except Exception as exc:
            log.exception("[/api/v2/quotations] GitHub publish FAILED for %s: %s", quotation_id, exc)
            raise HTTPException(status_code=502, detail=f"GitHub publish failed: {exc}")
    else:
        quo_dir = os.path.join("published", quotation_id)
        os.makedirs(quo_dir, exist_ok=True)
        with open(os.path.join(quo_dir, f"v1{sfx}.html"), "w", encoding="utf-8") as f:
            f.write(rendered_html)
        with open(os.path.join(quo_dir, f"pdf{sfx}.html"), "w", encoding="utf-8") as f:
            f.write(rendered_pdf)
        with open(os.path.join(quo_dir, f"pdf_{lang}.html"), "w", encoding="utf-8") as f:
            f.write(rendered_pdf)
        with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as f:
            json.dump(ctx, f, ensure_ascii=False, default=str)
        with open(os.path.join(quo_dir, "document.json"), "w", encoding="utf-8") as f:
            json.dump(document, f, ensure_ascii=False)
        with open(os.path.join(quo_dir, "create_request_v2.json"), "w", encoding="utf-8") as f:
            json.dump(payload.model_dump(mode="json"), f, ensure_ascii=False)
        await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
        quotations[quotation_id]["status"] = "published"
        quotations[quotation_id]["version"] = 1

    quotation_url = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
    try:
        async with _get_db_session_factory()() as session:
            quotation_repository = QuotationRepository(session)
            document_repository = QuotationDocumentRepository(session)

            quotation = await quotation_repository.create_quotation(
                quotation_id=quotation_id,
                opportunity_id=payload.opportunity_id or quotation_id,
                brand_id=payload.brand_id,
                template_name=BROCHURE_TEMPLATE_NAME,
                baseline_lang=lang,
                customer_name=((payload.customer_facts or {}).customer_name if payload.customer_facts else None),
                title=document.get("trip", {}).get("title") or "Untitled journey",
                status="published",
                current_version=1,
            )
            await quotation_repository.create_quotation_request(
                quotation_id=quotation_id,
                request_json=payload.model_dump(mode="json"),
            )
            current_document = await document_repository.save_current_document(
                quotation_id=quotation_id,
                lang=lang,
                document_json=document,
                expected_revision=0,
                html_sync=initial_html_sync,
                generation_status=document.get("generationStatus") or {},
            )
            canonical_document = _hydrate_canonical_quote_document(
                current_document.document_json,
                quotation,
                lang=lang,
                revision=current_document.revision,
            )
            await document_repository.append_document_revision(
                quotation_id=quotation_id,
                lang=lang,
                revision=current_document.revision,
                document_json=canonical_document,
                change_source="create",
            )
            await session.commit()
    except Exception as exc:
        log.exception("[/api/v2/quotations] Postgres persistence FAILED for %s: %s", quotation_id, exc)
        raise HTTPException(status_code=500, detail=f"Postgres persistence failed: {exc}")
    return {
        "quotationId": quotation_id,
        "quotationUrl": quotation_url,
        "pdfUrl": pdf_public_url,
        "documentVersion": ((document.get("meta") or {}).get("version")) or 1,
        "status": "published",
    }


async def _resolve_v2_facts(payload: CreateQuoteRequestV1) -> tuple[CreateQuoteRequestV1, dict[str, Any]]:
    async with _get_db_session_factory()() as session:
        await _seed_destination_catalog(session)
        resolver = FactsResolver()
        try:
            canonical, resolved = await resolver.resolve(payload, DestinationRepository(session).resolve)
        except FactsResolutionError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc), "missingInputs": exc.missing_inputs}) from exc
        await session.commit()
        return canonical, resolved


async def _validate_selected_accommodations(payload: CreateQuoteRequestV1) -> None:
    """Ensure Intake snapshots originate from active accommodation profiles."""
    missing: list[str] = []
    async with _get_db_session_factory()() as session:
        repository = AccommodationRepository(session)
        for index, hotel in enumerate(payload.service_facts.hotels):
            profile = await repository.get_profile(hotel.accommodation_id or "")
            if profile is None or not profile.is_active:
                missing.append(f"service_facts.hotels[{index}].accommodation_id")
                continue
            selected_assets = {key for key in (hotel.hotel_asset, hotel.room_asset) if key}
            if any(not key.startswith(f"{profile.asset_prefix}/") for key in selected_assets):
                missing.extend((f"service_facts.hotels[{index}].hotel_asset", f"service_facts.hotels[{index}].room_asset"))
                continue
            profile_assets = {key for key in (profile.hotel_asset, profile.room_asset) if key}
            custom_assets = selected_assets - profile_assets
            if custom_assets:
                active_keys = await MediaLibraryRepository(session).get_active_media_keys(custom_assets)
                if custom_assets - active_keys:
                    missing.extend((f"service_facts.hotels[{index}].hotel_asset", f"service_facts.hotels[{index}].room_asset"))
    if missing:
        raise HTTPException(status_code=422, detail={"message": "Selected accommodation profile or asset is unavailable.", "missingInputs": sorted(set(missing))})


def _facts_response(*, quotation, request_json: dict[str, Any], document: dict[str, Any], resolved_facts: dict[str, Any]) -> dict[str, Any]:
    return {
        "facts": request_json,
        "resolvedFacts": resolved_facts,
        "source": {"kind": quotation.source_kind, "opportunityId": quotation.opportunity_id, "snapshotAt": quotation.source_snapshot_at.isoformat() if quotation.source_snapshot_at else None, "version": quotation.source_version},
        "currentRevision": ((document.get("meta") or {}).get("revision")) or quotation.current_revision,
        "baselineLang": quotation.baseline_lang,
        "missingInputs": resolved_facts.get("missingInputs", []),
    }


def _preserve_content_owned_values(current: dict[str, Any], rebuilt: dict[str, Any]) -> None:
    """A Facts save can rebuild only Facts/fact-derived values, never editorial copy."""
    for path in content_owned_targets():
        if path == "route.staySegments.*.mapSegmentDesc":
            previous_segments = ((current.get("route") or {}).get("staySegments") or [])
            rebuilt_segments = ((rebuilt.get("route") or {}).get("staySegments") or [])
            previous_by_hotel_id = {
                str(item.get("hotelSourceFactId")): item
                for item in previous_segments
                if item.get("hotelSourceFactId")
            }
            previous_by_fallback: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
            for item in previous_segments:
                key = (item.get("destinationId"), item.get("dayStart"), item.get("dayEnd"))
                previous_by_fallback.setdefault(key, []).append(item)
            for next_segment in rebuilt_segments:
                previous = previous_by_hotel_id.get(str(next_segment.get("hotelSourceFactId") or ""))
                if previous is None:
                    matches = previous_by_fallback.get((
                        next_segment.get("destinationId"),
                        next_segment.get("dayStart"),
                        next_segment.get("dayEnd"),
                    ), [])
                    previous = matches[0] if len(matches) == 1 else None
                if previous is not None and "mapSegmentDesc" in previous:
                    next_segment["mapSegmentDesc"] = copy.deepcopy(previous["mapSegmentDesc"])
            continue
        if path == "stays.hotels.*.editorialIntroduction":
            previous_hotels = ((current.get("stays") or {}).get("hotels") or [])
            rebuilt_hotels = ((rebuilt.get("stays") or {}).get("hotels") or [])
            previous_by_id = {
                str(hotel.get("sourceFactId") or hotel.get("id")): hotel
                for hotel in previous_hotels
                if hotel.get("sourceFactId") or hotel.get("id")
            }
            for next_hotel in rebuilt_hotels:
                previous = previous_by_id.get(str(next_hotel.get("sourceFactId") or next_hotel.get("id") or ""))
                if previous is None:
                    continue
                same_hotel = (
                    previous.get("name") == next_hotel.get("name")
                    and previous.get("city") == next_hotel.get("city")
                    and previous.get("destinationRef") == next_hotel.get("destinationRef")
                )
                if same_hotel and "editorialIntroduction" in previous:
                    next_hotel["editorialIntroduction"] = copy.deepcopy(previous["editorialIntroduction"])
            continue
        if path in {"itinerary.days.*.title", "itinerary.days.*.description", "itinerary.days.*.activities"}:
            current_days = ((current.get("itinerary") or {}).get("days") or [])
            rebuilt_days = ((rebuilt.get("itinerary") or {}).get("days") or [])
            current_by_id = {
                str(day.get("sourceFactId")): day
                for day in current_days
                if day.get("sourceFactId")
            }
            for next_day in rebuilt_days:
                previous = current_by_id.get(str(next_day.get("sourceFactId") or ""))
                if previous is None:
                    continue
                if any(previous.get(key) != next_day.get(key) for key in ("segmentCity", "overnight")):
                    continue
                for key in ("title", "description", "activities", "labelHighlights", "labelNotes"):
                    if key in previous:
                        next_day[key] = copy.deepcopy(previous[key])
            continue
        source: Any = current
        target: Any = rebuilt
        parts = path.split(".")
        for part in parts[:-1]:
            if not isinstance(source, dict) or part not in source:
                source = None
                break
            source = source[part]
            if not isinstance(target, dict):
                break
            target = target.setdefault(part, {})
        if isinstance(source, dict) and isinstance(target, dict) and parts[-1] in source:
            target[parts[-1]] = copy.deepcopy(source[parts[-1]])


@app.post("/api/v2/quotations")
async def create_canonical_quotation_v2(payload: CreateQuoteRequestV1, principal: Principal = Depends(require_editor)):
    if payload.source.kind != "manual":
        raise HTTPException(status_code=422, detail={"message": "Only manual quotations are supported in this phase.", "missingInputs": ["source.kind"]})
    missing_intake_inputs = quotation_intake_missing_inputs(payload)
    if missing_intake_inputs:
        raise HTTPException(status_code=422, detail={"message": "Required quotation intake facts are missing.", "missingInputs": missing_intake_inputs})
    canonical, resolved = await _resolve_v2_facts(payload)
    await _validate_selected_accommodations(canonical)
    await _require_active_v2_brand(canonical.brand_id)
    creator_designer = await _resolve_active_travel_designer(principal)
    if resolved["missingInputs"]:
        raise HTTPException(status_code=422, detail={"message": "Required quotation facts are missing.", "missingInputs": resolved["missingInputs"]})
    quotation_id, lang = f"quo_{uuid.uuid4().hex[:12]}", canonical.lang or "en"
    # New-model Facts own stable semantic identities from their first
    # persistence.  A successor can only carry itinerary Content safely when
    # it receives these exact IDs back through the immutable Facts snapshot.
    from core.rules.semantic_identity import assign_missing_source_fact_ids

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
    canonical, resolved = await _resolve_v2_facts(CreateQuoteRequestV1.model_validate(canonical_payload))
    document = SkeletonBuilder().build(quotation_id=quotation_id, payload=canonical, resolved_facts=resolved, template=V2_RENDERER_NAME)
    # The creation screen has no persisted document yet, so its Facts picker
    # sends selections as generic contract slots. Validate and materialize them
    # at the same canonical boundary as later /facts/media mutations.
    document = await _apply_create_fact_media_slots(document, canonical.factMediaSlots)
    selected_designer_id = canonical.presentation_options.travel_designer_id or creator_designer.id
    if selected_designer_id != creator_designer.id:
        async with _get_db_session_factory()() as session:
            selected = await TravelDesignerRepository(session).get_profile(selected_designer_id)
        if selected is None or not selected.is_active:
            raise HTTPException(status_code=422, detail={"message": "Travel Designer is unavailable.", "missingInputs": ["presentation_options.travel_designer_id"]})
        designer = selected
    else:
        designer = creator_designer
    # The quotation row and the facts snapshot must agree on the same selected
    # profile. Without this assignment a newly-created quote could snapshot a
    # designer into the document while Facts reloaded a null selector.
    canonical.presentation_options.travel_designer_id = designer.id
    # Designer identity is selected Fact data; editorial copy stays in document.designer.
    _apply_travel_designer_snapshot(document, _serialize_travel_designer(designer))
    document["meta"]["resolvedDestinationRefs"] = {key: resolved[key] for key in ("routeDestinationRefs", "itinerary", "hotels")}
    try:
        async with _get_db_session_factory()() as session:
            quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
            # Direct intake still enters the same provenance model as a staff
            # Request. It is intentionally internal and never impersonates a
            # customer-submitted Request.
            from repositories.quote_request_repository import QuoteRequestRepository
            internal_request_id = f"req_internal_{uuid.uuid4().hex[:12]}"
            internal_request = await QuoteRequestRepository(session).create_request(
                request_id=internal_request_id,
                role="traveller",
                customer_name=canonical.customer_facts.customer_name or "Internal quotation",
                email=f"{internal_request_id}@internal.invalid",
                destinations=canonical.trip_facts.destinations,
                start_date=canonical.trip_facts.start_date,
                end_date=canonical.trip_facts.end_date,
                adults=canonical.customer_facts.adults,
                children=canonical.customer_facts.children,
                kid_ages=canonical.customer_facts.kid_ages,
                travel_style=canonical.customer_facts.travel_style,
                special_requirements="\n".join(canonical.trip_facts.special_requirements),
                payload_json={**canonical.model_dump(mode="json"), "internal_intake": True},
                created_by_profile_id=creator_designer.id,
            )
            quotation = await quotes.create_quotation(quotation_id=quotation_id, opportunity_id=internal_request.id, brand_id=canonical.brand_id or "", template_name=V2_RENDERER_NAME, baseline_lang=lang, customer_name=canonical.customer_facts.customer_name, title="Untitled journey", status="draft", source_kind="manual", source_snapshot_at=datetime.now().astimezone(), designer_profile_id=designer.id, created_by_profile_id=creator_designer.id, quotation_family_id=quotation_id, business_version=1, source_request_id=internal_request.id, source_request_revision=1)
            await quotes.create_quotation_request(quotation_id=quotation_id, request_json=canonical.model_dump(mode="json"))
            await quotes.create_version_facts(quotation_id=quotation_id, canonical_facts_json=canonical.model_dump(mode="json"), resolved_facts_json=resolved, facts_hash=resolved["factsHash"], source_request_id=internal_request.id, source_request_revision=1)
            await QuoteRequestRepository(session).update_status(request_id=internal_request.id, status="quotation_created", linked_quotation_id=quotation_id)
            await _apply_missing_media_defaults(session, document, quotation_id, lang)
            saved = await documents.save_current_document(quotation_id=quotation_id, lang=lang, document_json=document, expected_revision=0)
            document["meta"]["revision"] = saved.revision
            await documents.append_document_revision(quotation_id=quotation_id, lang=lang, revision=saved.revision, document_json=document, change_source="create_facts")
            from services.quotation_change_plan_service import QuotationChangePlanService
            from repositories import ContentActionPlanRepository
            await QuotationChangePlanService.persist(
                repository=ContentActionPlanRepository(session),
                quotation_id=quotation_id,
                predecessor_quotation_id=None,
                facts_hash=resolved["factsHash"],
                correlation_id=f"create-{quotation_id}",
                actions=QuotationChangePlanService.build_initial(canonical.model_dump(mode="json")),
            )
            await session.commit()
    except Exception as exc:
        log.exception("[/api/v2/quotations] canonical draft persistence failed")
        raise HTTPException(status_code=500, detail="Unable to persist quotation draft.") from exc
    return {"quotationId": quotation_id, "status": "draft", "currentRevision": 1, "baselineLang": lang, "resolvedFacts": resolved}


from routers.v2.quotation_facts import (
    apply_quotation_media_defaults_v2,
    get_quotation_facts_v2,
    put_quotation_fact_designer_v2,
    put_quotation_fact_media_v2,
    put_quotation_facts_v2,
)


class ContentDraftCreateRequest(BaseModel):
    scope: str = Field(min_length=1, max_length=128)
    generationMode: Literal["storytelling", "detailed"] = "storytelling"
    instruction: str = Field(default="", max_length=2000)


class ContentDraftPatchRequest(BaseModel):
    candidate: dict[str, Any]


class ContentDraftManualCreateRequest(BaseModel):
    scope: str = Field(min_length=1, max_length=128)
    candidate: dict[str, Any]
    baseRevision: int


class ContentDraftApplyRequest(BaseModel):
    baseRevision: int


def _serialize_content_draft(draft) -> dict[str, Any]:
    return {"id": draft.id, "scope": draft.scope, "generationMode": draft.generation_mode, "status": draft.status, "candidate": draft.candidate_json, "missingInputs": draft.missing_inputs, "generation": draft.generation_metadata, "sourceDocumentRevision": draft.source_document_revision, "factsSnapshot": draft.facts_snapshot, "editor": content_registry_payload(draft.scope).get(draft.scope, {})}


async def _load_content_draft_context(quotation_id: str, lang: str):
    session = _get_db_session_factory()()
    quotes, documents, drafts = QuotationRepository(session), QuotationDocumentRepository(session), ContentDraftRepository(session)
    quotation = await quotes.get_quotation_by_id(quotation_id)
    request = await quotes.get_latest_quotation_request(quotation_id) if quotation else None
    document = await documents.get_current_document(quotation_id, lang) if quotation else None
    if quotation is None or request is None or document is None:
        await session.close()
        raise HTTPException(status_code=404, detail="Quotation content context was not found.")
    return session, quotation, CreateQuoteRequestV1.model_validate(normalize_legacy_facts_snapshot(request.request_json)), document, drafts


async def _resolve_v2_locale(quotation_id: str, requested_lang: str | None) -> tuple[Any, str]:
    """Resolve V2 locale from the quotation, never from a hard-coded fallback."""
    async with _get_db_session_factory()() as session:
        quotation = await QuotationRepository(session).get_quotation_by_id(quotation_id)
    if quotation is None:
        raise HTTPException(status_code=404, detail="Quotation was not found.")
    effective_lang = (requested_lang or quotation.baseline_lang or "").strip().lower()
    if effective_lang not in {"en", "vi", "ar"}:
        raise HTTPException(status_code=422, detail={"message": "Unsupported quotation locale.", "locale": effective_lang})
    return quotation, effective_lang


from routers.v2.quotation_document import (
    apply_content_draft_v2,
    create_content_drafts_v2,
    create_manual_content_draft_v2,
    discard_content_draft_v2,
    get_quotation_document,
    list_content_drafts_v2,
    patch_content_draft_v2,
    put_quotation_document,
    put_quotation_presentation_copy_overrides_v2,
    put_quotation_presentation_overrides_v2,
    put_quotation_presentation_v2,
)


# ── GET /published/{quotation_id}/version & /latest — Dynamic version & redirect ──

@app.get("/published/{quotation_id}/version")
async def get_published_version(quotation_id: Annotated[str, Path(description="Quotation ID")]):
    from github_publish import get_next_version
    try:
        next_ver = await get_next_version(quotation_id)
        latest_ver = max(1, next_ver - 1)
    except Exception:
        latest_ver = 1
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    return JSONResponse(
        content={
            "version": latest_ver, 
            "latest_url": f"/published/{quotation_id}/v{latest_ver}.html"
        },
        headers=no_cache_headers
    )

@app.get("/published/{quotation_id}")
@app.get("/published/{quotation_id}/latest")
async def redirect_to_latest_published(quotation_id: Annotated[str, Path(description="Quotation ID")]):
    from fastapi.responses import RedirectResponse
    from github_publish import get_next_version
    try:
        next_ver = await get_next_version(quotation_id)
        latest_ver = max(1, next_ver - 1)
    except Exception:
        latest_ver = 1
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    return RedirectResponse(
        url=f"/published/{quotation_id}/v{latest_ver}.html",
        status_code=307,
        headers=no_cache_headers
    )


# ── GET /published/{file_path:path} — Dynamic static files ────────────────────

@app.get("/published/{file_path:path}")
async def get_published_file(file_path: Annotated[str, Path(description="Relative path inside published directory")]):
    """
    Serve files from the local 'published' directory if they exist.
    If local file is missing, try fetching directly from GitHub API,
    cache it locally to VPS disk for future requests, and serve it.
    """
    import mimetypes
    from fastapi.responses import Response, FileResponse

    # Prevent directory traversal attacks
    safe_path = os.path.normpath(file_path).lstrip("/\\")
    if safe_path.startswith(".."):
        raise HTTPException(status_code=400, detail="Invalid file path.")

    local_path = os.path.join("published", safe_path)
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    if os.path.isfile(local_path):
        return FileResponse(local_path, headers=no_cache_headers)
        
    # File not found locally - attempt fetching from GitHub API
    import httpx
    repo = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")
    if repo:
        headers = {"Accept": "application/vnd.github.v3.raw"}
        if token:
            headers["Authorization"] = f"token {token}"
            
        gh_url = f"https://api.github.com/repos/{repo}/contents/published/{safe_path}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(gh_url, headers=headers)
            if resp.status_code == 401 and token:
                log.warning("[/published] GITHUB_TOKEN unauthorized (401), trying without token")
                resp = await client.get(gh_url, headers={"Accept": "application/vnd.github.v3.raw"})
            if resp.status_code == 200:
                log.info("[/published] Fetched %s from GitHub API", safe_path)
                # Cache on VPS disk so future requests serve instantly from local disk
                try:
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
                except Exception as exc:
                    log.warning("[/published] Could not save %s to local cache: %s", safe_path, exc)

                mt, _ = mimetypes.guess_type(safe_path)
                if not mt:
                    mt = "application/octet-stream"
                return Response(content=resp.content, media_type=mt, headers=no_cache_headers)
                    
    raise HTTPException(status_code=404, detail=f"File {file_path} not found.")



# ── GET /quotations/{id}/pdf — A4-optimised PDF view ─────────────────────
# IMPORTANT: must be registered BEFORE the {quotation_id} catch-all route.

from html.parser import HTMLParser

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

EMPTY_EDITABLE_TAG_RE = re.compile(
    r'<(?P<tag>p|div|li)[^>]*data-editable=["\'](?P<field>[^"\']+)["\'][^>]*>(?P<inner>\s*)</(?P=tag)>',
    flags=re.IGNORECASE | re.DOTALL,
)

WORD_PASTE_FRAGMENT_RE = re.compile(
    r"""
    \s*
    (?:
        <p\b[^>]*\bclass=["\'][^"\']*\bMso[a-zA-Z0-9_-]*[^"\']*["\'][^>]*>.*?</p>
        |
        <p\b[^>]*>.*?</p>
        |
        <span\b[^>]*\bmso-[^>]*>.*?</span>
        |
        <span\b[^>]*\bfont-family:(?:&quot;|")Garamond(?:&quot;|")[^>]*>.*?</span>
    )
    """,
    flags=re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

WORD_PASTE_MARKER_RE = re.compile(
    r'(?:\bMso[a-zA-Z0-9_-]*\b|\bmso-[a-z0-9-]+\b|font-family:(?:&quot;|")Garamond(?:&quot;|"))',
    flags=re.IGNORECASE,
)

WORD_PASTE_SPAN_RE = re.compile(
    r'<span\b[^>]*(?:\bMso[a-zA-Z0-9_-]*\b|\bmso-[a-z0-9-]+\b|font-family:(?:&quot;|")Garamond(?:&quot;|")|font-size:\s*12(?:\.0)?pt)[^>]*>',
    flags=re.IGNORECASE | re.DOTALL,
)

WORD_PASTE_PARAGRAPH_OPEN_RE = re.compile(
    r'<p\b[^>]*>',
    flags=re.IGNORECASE | re.DOTALL,
)

WORD_PASTE_PARAGRAPH_CLOSE_RE = re.compile(
    r'</p\s*>',
    flags=re.IGNORECASE,
)

WORD_PASTE_BREAK_RUN_RE = re.compile(
    r'(?:<br\s*/?>\s*){3,}',
    flags=re.IGNORECASE,
)

EMPTY_SPAN_RE = re.compile(
    r'<span>\s*</span>',
    flags=re.IGNORECASE,
)

PLAIN_SPAN_RE = re.compile(
    r'<span>(.*?)</span>',
    flags=re.IGNORECASE | re.DOTALL,
)


def _normalize_word_pasted_markup(value: str) -> str:
    if not value:
        return value

    text = str(value)
    if not WORD_PASTE_MARKER_RE.search(text):
        return text

    normalized = text.replace("\xa0", " ")
    normalized = re.sub(r'</?o:p[^>]*>', '', normalized, flags=re.IGNORECASE)
    normalized = WORD_PASTE_SPAN_RE.sub("<span>", normalized)
    normalized = WORD_PASTE_PARAGRAPH_OPEN_RE.sub("", normalized)
    normalized = WORD_PASTE_PARAGRAPH_CLOSE_RE.sub("<br><br>", normalized)

    while True:
        unwrapped = PLAIN_SPAN_RE.sub(r"\1", normalized)
        if unwrapped == normalized:
            break
        normalized = unwrapped

    normalized = EMPTY_SPAN_RE.sub("", normalized)
    normalized = re.sub(r'(?i)<p>\s*</p>', '', normalized)
    normalized = WORD_PASTE_BREAK_RUN_RE.sub("<br><br>", normalized)
    normalized = re.sub(r'[ \t\r\f\v]*\n[ \t\r\f\v]*', ' ', normalized)
    normalized = re.sub(r' {2,}', ' ', normalized)
    normalized = re.sub(r'\s*<br><br>\s*', '<br><br>', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'^(?:\s*<br\s*/?>\s*)+', '', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'(?:\s*<br\s*/?>\s*)+$', '', normalized, flags=re.IGNORECASE)
    return normalized.strip()


def _normalize_word_pasted_rich_text(field_name: str, value: str) -> str:
    if not value or not _field_supports_word_paste_typography_cleanup(field_name):
        return value
    return _normalize_word_pasted_markup(value)


def _repair_word_pasted_editable_blocks(html_content: str) -> str:
    if not html_content:
        return html_content

    repaired_parts: list[str] = []
    cursor = 0
    for match in EMPTY_EDITABLE_TAG_RE.finditer(html_content):
        repaired_parts.append(html_content[cursor:match.start()])
        original_block = match.group(0)
        field_name = match.group("field") or ""
        if not _field_supports_word_paste_recovery(field_name):
            repaired_parts.append(original_block)
            cursor = match.end()
            continue

        scan_pos = match.end()
        recovered_fragments: list[str] = []
        while True:
            fragment_match = WORD_PASTE_FRAGMENT_RE.match(html_content, scan_pos)
            if not fragment_match:
                break
            recovered_fragments.append(fragment_match.group(0))
            scan_pos = fragment_match.end()

        if recovered_fragments:
            tag = match.group('tag')
            if tag == 'p' and any('<p' in f.lower() for f in recovered_fragments):
                tag = 'div'
            repaired_parts.append(
                f"<{tag} data-editable=\"{field_name}\">"
                + "".join(recovered_fragments)
                + f"</{tag}>"
            )
            cursor = scan_pos
            continue

        repaired_parts.append(original_block)
        cursor = match.end()

    repaired_parts.append(html_content[cursor:])
    return "".join(repaired_parts)

class EditableFieldsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.edited_fields = {}
        self.stack = []

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        attrs_dict = dict(attrs)
        is_void = tag_lower in VOID_TAGS

        attr_str = "".join([f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs])
        for item in self.stack:
            if is_void:
                item['acc'].append(f"<{tag}{attr_str} />")
            else:
                item['acc'].append(f"<{tag}{attr_str}>")
                item['depth'] += 1

        if "data-editable" in attrs_dict and not is_void:
            field_name = attrs_dict["data-editable"]
            img_url = ""
            if "style" in attrs_dict:
                matches = re.findall(r'url\((["\']?)(.*?)\1\)', attrs_dict["style"])
                if matches:
                    # For editable day images the editor may temporarily carry both the
                    # original CSS var (--image) and the newly selected background image.
                    # Prefer the last URL so the freshly chosen image wins.
                    img_url = matches[-1][1]
            elif "src" in attrs_dict:
                img_url = attrs_dict["src"]

            self.stack.append({
                'field': field_name,
                'tag': tag_lower,
                'depth': 1,
                'acc': [],
                'img_url': img_url
            })

    def handle_startendtag(self, tag, attrs):
        tag_lower = tag.lower()
        attr_str = "".join([f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs])
        for item in self.stack:
            item['acc'].append(f"<{tag}{attr_str} />")

    def handle_data(self, data):
        for item in self.stack:
            item['acc'].append(data)

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in VOID_TAGS:
            return

        new_stack = []
        for item in self.stack:
            item['depth'] -= 1
            if item['depth'] == 0 and item['tag'] == tag_lower:
                val = "".join(item['acc']).strip()
                if not val and item.get('img_url'):
                    val = item['img_url']
                elif (
                    not _field_supports_rich_text(item['field'])
                    and not item['field'].startswith("day_img_")
                    and not item['field'].startswith("img_")
                ):
                    val = re.sub(r'<[^>]*>', '', str(val)).strip()
                elif _field_supports_rich_text(item['field']):
                    val = _normalize_word_pasted_rich_text(item['field'], val)
                self.edited_fields[item['field']] = val
            else:
                item['acc'].append(f"</{tag}>")
                new_stack.append(item)
        self.stack = new_stack

def parse_edited_fields(html_content: str) -> dict:
    parser = EditableFieldsParser()
    parser.feed(_repair_word_pasted_editable_blocks(html_content))
    return parser.edited_fields

def _normalize_visible_text(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r'<\s*br\s*/?>', '\n', value, flags=re.IGNORECASE)
    value = re.sub(r'</\s*(div|p|li|h[1-6])\s*>', '\n', value, flags=re.IGNORECASE)
    value = re.sub(r'<[^>]*>', '', value)
    value = html.unescape(value)
    value = value.replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in value.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def _split_itinerary_list_text(value: str) -> list[str]:
    normalized = _normalize_visible_text(value)
    if not normalized:
        return []
    return [
        item.strip()
        for item in re.split(r"\s*[·•]\s*|\n+", normalized)
        if item.strip()
    ]

def _normalize_image_ref(ref: str) -> str:
    if not ref:
        return ""

    normalized = str(ref).replace("\\/", "/").replace("\\", "").strip()
    for _ in range(4):
        unescaped = html.unescape(normalized).replace("\\/", "/").replace("\\", "").strip()
        if unescaped == normalized:
            break
        normalized = unescaped
    while len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        normalized = normalized[1:-1].strip()
    return normalized

def _dedupe_image_refs(refs: list[str] | None) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for ref in refs or []:
        normalized = _normalize_image_ref(ref)
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped

def _extract_editable_inner_html(html_content: str, field_name: str) -> str:
    pattern = rf'<(?P<tag>[a-zA-Z0-9]+)(?P<attrs>[^>]*?)data-editable=["\']{re.escape(field_name)}["\'](?P<attrs2>[^>]*)>(?P<body>.*?)</(?P=tag)>'
    match = re.search(pattern, html_content, flags=re.DOTALL)
    if match:
        return match.group("body").strip()
    return ""

def _extract_image_refs(value: str) -> list[str]:
    if not value:
        return []

    refs: list[str] = []
    for pattern, group_idx in (
        (r'url\((["\']?)(.*?)\1\)', 2),
        (r'src=["\']([^"\']+)["\']', 1),
    ):
        for match in re.finditer(pattern, value, flags=re.IGNORECASE | re.DOTALL):
            ref = _normalize_image_ref(match.group(group_idx) or "")
            if ref and ref not in refs:
                refs.append(ref)

    stripped = _normalize_image_ref(value.strip())
    if not refs and stripped and "<" not in stripped:
        refs.append(stripped)

    return refs

def _extract_editable_image_attr(html_content: str, field_name: str) -> str:
    if not html_content or not field_name:
        return ""

    patterns = (
        rf'data-editable=["\']{re.escape(field_name)}["\'][^>]*src=["\']([^"\']+)["\']',
        rf'src=["\']([^"\']+)["\'][^>]*data-editable=["\']{re.escape(field_name)}["\']',
        rf'data-editable=["\']{re.escape(field_name)}["\'][^>]*style=["\'][^"\']*url\((["\']?)(.*?)\1\)',
        rf'style=["\'][^"\']*url\((["\']?)(.*?)\1\)[^"\']*["\'][^>]*data-editable=["\']{re.escape(field_name)}["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, html_content, flags=re.IGNORECASE | re.DOTALL)
        if match:
            if len(match.groups()) > 1:
                return _normalize_image_ref(match.group(2) or "")
            return _normalize_image_ref(match.group(1) or "")
    return ""

def _extract_hotel_image_refs(html_content: str, hotel_indexes: list[int]) -> dict[str, dict[str, str]]:
    if not hotel_indexes:
        return {}

    main_matches = re.findall(
        r'<div[^>]*class=["\'][^"\']*\bimg-wrapper-main\b[^"\']*\bhotel-image-wrapper\b[^"\']*["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']',
        html_content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    room_matches = re.findall(
        r'<div[^>]*class=["\'][^"\']*\bimg-wrapper-sub\b[^"\']*\bhotel-image-wrapper\b[^"\']*["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']',
        html_content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    hotel_refs: dict[str, dict[str, str]] = {}
    for pos, idx in enumerate(hotel_indexes):
        hotel_entry: dict[str, str] = {}
        direct_main = _extract_editable_image_attr(html_content, f"hotel_img_{idx}")
        direct_room = _extract_editable_image_attr(html_content, f"hotel_room_img_{idx}")
        if direct_main:
            hotel_entry["hotel_img"] = direct_main
        elif pos < len(main_matches) and main_matches[pos]:
            hotel_entry["hotel_img"] = main_matches[pos].strip()
        if direct_room:
            hotel_entry["room_img"] = direct_room
        elif pos < len(room_matches) and room_matches[pos]:
            hotel_entry["room_img"] = room_matches[pos].strip()
        if hotel_entry:
            hotel_refs[str(idx)] = hotel_entry
    return hotel_refs

def _apply_segment_duration_override(segment: dict, raw_duration: str):
    clean_duration = (raw_duration or "").strip()
    if not clean_duration:
        segment["daysLabel"] = ""
        segment["nightsLabel"] = ""
        return

    parts = [part.strip() for part in clean_duration.split("•")]
    parts = [part for part in parts if part]
    if not parts:
        segment["daysLabel"] = ""
        segment["nightsLabel"] = ""
        return

    segment["daysLabel"] = parts[0]
    segment["nightsLabel"] = " • ".join(parts[1:]) if len(parts) > 1 else ""
    # Preserve a structured night count as well as the editable display text.
    # Static web and PDF renders do not always consume the same presentation
    # field, so leaving this stale causes a saved map edit to revert on refresh.
    nights_match = re.search(r"\b(\d+)\s*night(?:s)?\b", clean_duration, flags=re.IGNORECASE)
    if nights_match:
        segment["nights"] = int(nights_match.group(1))


def _normalize_map_segment_description(value: Any) -> str:
    """Preserve readable line breaks in map segment descriptions."""
    if value is None:
        return ""
    text = str(value)
    if "<" in text and ">" in text:
        return text
    text = html.unescape(text).strip()
    return re.sub(r"\s*(?=Day\s+\d+\s*:)", "<br>", text)

def _extract_itinerary_image_refs(edited_fields: dict, html_content: str) -> dict[str, dict[str, Any]]:
    day_numbers = sorted({
        int(idx)
        for idx in re.findall(r'data-editable=["\']day_img_(?:hero|small1|small2|carousel)_(\d+)["\']', html_content)
    })
    if not day_numbers:
        day_numbers = sorted({
            int(idx)
            for idx in re.findall(r'data-editable=["\']day_img_carousel_(\d+)["\']', html_content)
        })
    if not day_numbers:
        return {}

    itinerary_refs: dict[str, dict[str, Any]] = {}
    field_map = {
        "hero": "hero",
        "small1": "small-1",
        "small2": "small-2",
    }
    for day_num in day_numbers:
        entry: dict[str, Any] = {}
        for field_suffix, target_key in field_map.items():
            refs = _extract_image_refs(edited_fields.get(f"day_img_{field_suffix}_{day_num}", ""))
            if refs:
                entry[target_key] = refs[0]

        carousel_refs = _extract_image_refs(edited_fields.get(f"day_img_carousel_{day_num}", ""))
        pattern_block = rf'data-editable=["\']day_img_carousel_{day_num}["\'].*?(?=(?:data-editable=|</article>|<article|$))'
        match = re.search(pattern_block, html_content, flags=re.DOTALL | re.IGNORECASE)
        if match:
            block_html = match.group(0)
            direct_refs = _extract_image_refs(block_html)
            for ref in direct_refs:
                if ref not in carousel_refs:
                    carousel_refs.append(ref)
        carousel_refs = _dedupe_image_refs(carousel_refs)

        if carousel_refs:
            entry["carousel"] = carousel_refs
            entry["hero"] = carousel_refs[0]
            entry["small-1"] = carousel_refs[1] if len(carousel_refs) > 1 else carousel_refs[0]
            entry["small-2"] = carousel_refs[2] if len(carousel_refs) > 2 else (carousel_refs[1] if len(carousel_refs) > 1 else carousel_refs[0])

        if entry:
            itinerary_refs[str(day_num)] = entry

    return itinerary_refs


def _extract_visible_itinerary_day_meta(html_content: str) -> dict[str, dict[str, Any]]:
    itinerary_meta: dict[str, dict[str, Any]] = {}
    for match in re.finditer(r'<article class="day\b.*?</article>', html_content, flags=re.DOTALL | re.IGNORECASE):
        block_html = match.group(0)
        day_match = re.search(r'data-editable=["\']day_title_(\d+)["\']', block_html)
        if not day_match:
            continue
        destination_match = re.search(r'<span class="destination">\s*(.*?)\s*</span>', block_html, flags=re.DOTALL | re.IGNORECASE)
        if not destination_match:
            continue
        destination_text = _normalize_visible_text(destination_match.group(1))
        if not destination_text:
            continue
        itinerary_meta[day_match.group(1)] = {
            "segment_city": destination_text,
        }
    return itinerary_meta

def _extract_letter_intro_parts(letter_intro_text: str) -> dict:
    parts = {}
    if not letter_intro_text:
        return parts

    guest_match = re.search(r'created for\s+(.*?)\s+travelling from', letter_intro_text, flags=re.IGNORECASE | re.DOTALL)
    if guest_match:
        parts["guests_txt"] = " ".join(guest_match.group(1).split())

    route_match = re.search(r'The route unfolds from\s+(.*?)(?:\.|$)', letter_intro_text, flags=re.IGNORECASE | re.DOTALL)
    if route_match:
        parts["route_txt"] = " ".join(route_match.group(1).split())

    title_match = re.search(r'journey:\s+(.*?),\s+created for', letter_intro_text, flags=re.IGNORECASE | re.DOTALL)
    if title_match:
        parts["overview_heading"] = " ".join(title_match.group(1).split())

    return parts

def _capture_composite_sync_state(html_content: str) -> dict:
    edited_fields = parse_edited_fields(html_content)
    _, edited_fields, _ = _sanitize_html_sync_payload(set(), edited_fields)
    composite = {
        "top_level": {},
        "hotels": {},
        "itinerary_days": {},
    }

    top_fields = [
        "hero_meta_1",
        "letter_greeting",
        "letter_intro",
        "letter_body_p2",
        "letter_outro",
        "letter_sign_off",
        "letter_sender",
        "footer_text",
    ]
    for field_name in top_fields:
        value = edited_fields.get(field_name)
        if value:
            composite["top_level"][field_name] = value

    letter_greeting = composite["top_level"].get("letter_greeting", "")
    greeting_match = re.match(r'^Dear\s+(.*?)(?:,)?$', letter_greeting, flags=re.IGNORECASE | re.DOTALL)
    if greeting_match:
        composite["top_level"]["customer_name"] = " ".join(greeting_match.group(1).split())

    composite["top_level"].update(_extract_letter_intro_parts(composite["top_level"].get("letter_intro", "")))

    hotel_indexes = sorted({int(idx) for idx in re.findall(r'data-editable=["\']hotel_intro_(\d+)["\']', html_content)})
    room_type_label = re.compile(r'Room\s*type\s*:?\s*', flags=re.IGNORECASE)
    for idx in hotel_indexes:
        hotel_intro_html = _extract_editable_inner_html(html_content, f"hotel_intro_{idx}")
        hotel_intro_text = _normalize_visible_text(hotel_intro_html)
        room_type = ""

        room_match = room_type_label.search(hotel_intro_text)
        if room_match:
            intro_text = hotel_intro_text[:room_match.start()].strip()
            room_type_text = hotel_intro_text[room_match.end():].strip()
            if "\n" in room_type_text:
                room_type_text = room_type_text.split("\n", 1)[0].strip()
            hotel_intro_text = intro_text
            room_type = room_type_text

        explicit_room_type = edited_fields.get(f"hotel_room_type_{idx}")
        if explicit_room_type:
            room_type = explicit_room_type.strip()

        hotel_entry = {}
        if hotel_intro_text:
            hotel_entry["hotel_intro"] = hotel_intro_text
        if room_type:
            hotel_entry["room_type"] = room_type
        if hotel_entry:
            composite["hotels"][str(idx)] = hotel_entry

    for hotel_idx, image_entry in _extract_hotel_image_refs(html_content, hotel_indexes).items():
        composite["hotels"].setdefault(hotel_idx, {}).update(image_entry)

    itinerary_image_refs = _extract_itinerary_image_refs(edited_fields, html_content)
    if itinerary_image_refs:
        composite["itinerary_days"].update(itinerary_image_refs)
    for day_num, day_meta in _extract_visible_itinerary_day_meta(html_content).items():
        composite["itinerary_days"].setdefault(day_num, {}).update(day_meta)

    if not composite["top_level"]:
        composite.pop("top_level")
    if not composite["hotels"]:
        composite.pop("hotels")
    if not composite["itinerary_days"]:
        composite.pop("itinerary_days")
    return composite

def get_existing_editable_keys(html_content: str) -> set[str]:
    import re
    return set(re.findall(r'data-editable=["\']([^"\']+)["\']', html_content))

def extract_editor_components(rendered_html: str) -> str:
    """
    Extracts the publish-bar, loading overlay, translation-status,
    and editor-scripts from the rendered Jinja2 template.
    """
    idx_bar = rendered_html.find('id="publish-bar"')
    if idx_bar == -1:
        idx_bar = rendered_html.find("id='publish-bar'")
    if idx_bar == -1:
        return ""
        
    idx_start = rendered_html.rfind('<div', 0, idx_bar)
    if idx_start == -1:
        idx_start = idx_bar
        
    idx_scripts = rendered_html.find('id="editor-scripts"')
    if idx_scripts == -1:
        idx_scripts = rendered_html.find("id='editor-scripts'")
    if idx_scripts == -1:
        return ""
        
    idx_end_script = rendered_html.find('</script>', idx_scripts)
    if idx_end_script == -1:
        return ""
    idx_end = idx_end_script + len('</script>')
    
    return rendered_html[idx_start:idx_end]

def make_itinerary_editor_visible(html_content: str) -> str:
    import re
    # Strip style="display: none;" from #publish-bar
    pattern = r'(<div[^>]*id=["\']publish-bar["\'][^>]*style=["\']display:\s*none;?["\'][^>]*>)'
    def repl(match):
        tag = match.group(1)
        tag = re.sub(r'style=["\']display:\s*none;?["\']', '', tag)
        return tag
    return re.sub(pattern, repl, html_content)

def sync_itinerary_deletions_to_payloads(ctx: dict, active_days: set[int], active_cards: dict):
    if "itinerary" in ctx:
        ctx["itinerary"] = [day for day in ctx["itinerary"] if day.get("dayNumber") in active_days]
    if "hotels" in ctx:
        ctx["hotels"] = [h for i, h in enumerate(ctx["hotels"]) if i in active_cards["hotel"]]
    if "activities" in ctx:
        ctx["activities"] = [act for i, act in enumerate(ctx["activities"]) if i in active_cards["activity"]]
    if "transfers" in ctx:
        ctx["transfers"] = [tx for i, tx in enumerate(ctx["transfers"]) if i in active_cards["transfer"]]
    if "flights" in ctx:
        ctx["flights"] = [fl for i, fl in enumerate(ctx["flights"]) if i in active_cards["flight"]]
    if "guides" in ctx:
        ctx["guides"] = [gd for i, gd in enumerate(ctx["guides"]) if i in active_cards["guide"]]

    def filter_payload(p_dict):
        if not p_dict:
            return
        if "itinerary" in p_dict:
            p_dict["itinerary"] = [day for day in p_dict["itinerary"] if day.get("dayNumber") in active_days]
        if "hotels" in p_dict:
            p_dict["hotels"] = [h for i, h in enumerate(p_dict["hotels"]) if i in active_cards["hotel"]]
        if "activities" in p_dict:
            p_dict["activities"] = [act for i, act in enumerate(p_dict["activities"]) if i in active_cards["activity"]]
        if "transfers" in p_dict:
            p_dict["transfers"] = [tx for i, tx in enumerate(p_dict["transfers"]) if i in active_cards["transfer"]]
        if "flights" in p_dict:
            p_dict["flights"] = [fl for i, fl in enumerate(p_dict["flights"]) if i in active_cards["flight"]]
        if "guides" in p_dict:
            p_dict["guides"] = [gd for i, gd in enumerate(p_dict["guides"]) if i in active_cards["guide"]]

    if "baseline_payload" in ctx:
        filter_payload(ctx["baseline_payload"])

    if "translations" in ctx:
        for lang_key in ctx["translations"]:
            filter_payload(ctx["translations"][lang_key])

def _sync_indexed_html_list(
    lang_ctx: dict,
    existing_keys: set[str],
    edited_fields: dict,
    *,
    list_key: str,
    field_prefix: str,
    fallback_single_key: str | None = None,
):
    source_items = copy.deepcopy(lang_ctx.get(list_key) or [])
    indexed_keys = {
        key
        for key in set(existing_keys or set()) | set((edited_fields or {}).keys())
        if key.startswith(f"{field_prefix}_")
    }
    has_fallback = bool(
        fallback_single_key
        and (
            fallback_single_key in (existing_keys or set())
            or fallback_single_key in (edited_fields or {})
        )
    )
    if not indexed_keys and not has_fallback:
        return

    rebuilt_items = []
    idx = 0
    while True:
        item_key = f"{field_prefix}_{idx}"
        if item_key in edited_fields:
            rebuilt_items.append(edited_fields[item_key])
            idx += 1
            continue
        if item_key in existing_keys:
            rebuilt_items.append(source_items[idx] if idx < len(source_items) else "")
            idx += 1
            continue
        break

    if not rebuilt_items and fallback_single_key:
        if fallback_single_key in edited_fields:
            rebuilt_items = [edited_fields[fallback_single_key]]
        elif fallback_single_key in existing_keys:
            rebuilt_items = [source_items[0] if source_items else ""]

    lang_ctx[list_key] = rebuilt_items

def filter_and_override_ctx(lang_ctx: dict, existing_keys: set[str], edited_fields: dict, override_text: bool = True):
    """
    Filters out deleted blocks and optionally overrides text content of remaining blocks
    based on the saved editable state.
    """
    existing_keys, edited_fields, _ = _sanitize_html_sync_payload(existing_keys, edited_fields)

    # Simple variables
    if override_text:
        for key in HTML_DIRECT_SYNC_FIELDS:
            if key in edited_fields:
                lang_ctx[key] = edited_fields[key]

        # The landing-page template stores booking terms as indexed editable
        # blocks, while the PDF template renders the named term_* fields.
        # Keep both projections in sync so a saved landing-page edit cannot
        # leave a stale payment-policy section in the generated PDF.
        booking_terms = copy.deepcopy(lang_ctx.get("booking_terms") or [])
        booking_term_fields = (
            ("term_deposit", "payment_label_deposit"),
            ("term_balance", "payment_label_balance"),
            ("term_cancellation", "payment_label_cancellation"),
            ("term_confirmation", "payment_label_confirmation"),
        )
        for index, (term_key, label_key) in enumerate(booking_term_fields):
            body_field = f"booking_term_body_{index}"
            label_field = f"booking_term_label_{index}"
            if body_field not in edited_fields and label_field not in edited_fields:
                continue
            while len(booking_terms) <= index:
                booking_terms.append({"label": "", "body": ""})
            item = booking_terms[index]
            if not isinstance(item, dict):
                item = {"label": "", "body": ""}
                booking_terms[index] = item
            if body_field in edited_fields:
                lang_ctx[term_key] = edited_fields[body_field]
                item["body"] = edited_fields[body_field]
            if label_field in edited_fields:
                lang_ctx[label_key] = edited_fields[label_field]
                item["label"] = edited_fields[label_field]
        if booking_terms:
            lang_ctx["booking_terms"] = booking_terms

        if "inc_exc_h2" in edited_fields:
            lang_ctx["inclusions_title"] = edited_fields["inc_exc_h2"]

        if "price_cond_first" in edited_fields:
            price_cond_paras = copy.deepcopy(lang_ctx.get("price_cond_paras") or [])
            if price_cond_paras:
                price_cond_paras[0] = edited_fields["price_cond_first"]
            else:
                price_cond_paras = [edited_fields["price_cond_first"]]
            lang_ctx["price_cond_paras"] = price_cond_paras
            
    # 1. Filter and update itinerary days
    new_itinerary = []
    for idx, day in enumerate(lang_ctx.get('itinerary', []), 1):
        t_key = f"day_title_{idx}"
        if t_key in existing_keys:
            if override_text:
                if t_key in edited_fields:
                    day['title_html'] = edited_fields[t_key]
                    day['title'] = _normalize_visible_text(edited_fields[t_key])
                
                badge_key = f"day_badge_{idx}"
                if badge_key in edited_fields:
                    day['day_badge_text'] = edited_fields[badge_key]

                num_key = f"day_num_{idx}"
                if num_key in edited_fields:
                    day['day_num_text'] = edited_fields[num_key]

                lh_key = f"day_label_highlights_{idx}"
                if lh_key in edited_fields:
                    day['label_highlights'] = edited_fields[lh_key]

                ln_key = f"day_label_notes_{idx}"
                if ln_key in edited_fields:
                    day['label_notes'] = edited_fields[ln_key]

                lo_key = f"day_label_overnight_{idx}"
                if lo_key in edited_fields:
                    day['label_overnight'] = edited_fields[lo_key]

                lm_key = f"day_label_meals_{idx}"
                if lm_key in edited_fields:
                    day['label_meals'] = edited_fields[lm_key]
                    
                # Rebuild day description paragraphs
                any_desc_edited = any(f"day_desc_{idx}_{p}" in edited_fields for p in range(20))
                if any_desc_edited:
                    desc_paras = []
                    desc_paras_html = []
                    p = 0
                    while True:
                        p_key = f"day_desc_{idx}_{p}"
                        if p_key in edited_fields:
                            desc_paras_html.append(edited_fields[p_key])
                            desc_paras.append(_normalize_visible_text(edited_fields[p_key]))
                            p += 1
                        elif p_key in existing_keys:
                            orig_desc = day.get('description', [])
                            orig_desc_html = day.get('description_html', [])
                            if p < len(orig_desc):
                                desc_paras.append(orig_desc[p])
                            else:
                                desc_paras.append("")
                            if p < len(orig_desc_html):
                                desc_paras_html.append(orig_desc_html[p])
                            elif p < len(orig_desc):
                                desc_paras_html.append(orig_desc[p])
                            else:
                                desc_paras_html.append("")
                            p += 1
                        else:
                            break
                    day['description'] = desc_paras
                    day['description_html'] = desc_paras_html

                # Update Overnight & Meals even if description itself was unchanged.
                o_key = f"day_overnight_{idx}"
                if o_key in edited_fields:
                    day['overnight'] = edited_fields[o_key]
                m_key = f"day_meals_{idx}"
                if m_key in edited_fields:
                    day['meals'] = [m.strip() for m in re.split(r'[·•\-,/]', edited_fields[m_key]) if m.strip()]

                # Update Highlights (activities)
                h_key = f"day_highlights_{idx}"
                if h_key in edited_fields:
                    day['activities_html'] = edited_fields[h_key]
                    day['activities'] = _split_itinerary_list_text(edited_fields[h_key])

                # Update Notes list
                any_notes_edited = any(f"day_note_{idx}_{p}" in edited_fields for p in range(20))
                if any_notes_edited:
                    notes_list = []
                    notes_list_html = []
                    p = 0
                    while True:
                        n_key = f"day_note_{idx}_{p}"
                        if n_key in edited_fields:
                            notes_list_html.append(edited_fields[n_key])
                            notes_list.append(_normalize_visible_text(edited_fields[n_key]))
                            p += 1
                        elif n_key in existing_keys:
                            orig_notes = day.get('notes', [])
                            orig_notes_html = day.get('notes_html', [])
                            if p < len(orig_notes):
                                notes_list.append(orig_notes[p])
                            else:
                                notes_list.append("")
                            if p < len(orig_notes_html):
                                notes_list_html.append(orig_notes_html[p])
                            elif p < len(orig_notes):
                                notes_list_html.append(orig_notes[p])
                            else:
                                notes_list_html.append("")
                            p += 1
                        else:
                            break
                    day['notes'] = notes_list
                    day['notes_html'] = notes_list_html

            new_itinerary.append(day)
    lang_ctx['itinerary'] = new_itinerary
    
    # 1b. Update chapter layout images if edited_fields contains day_img_*
    for chapter in lang_ctx.get('chapters', []):
        for day in chapter.get('days', []):
            d_num = day.get('dayNumber')
            if d_num:
                layout_imgs = day.setdefault('layout_images', {})
                if edited_fields.get(f"day_img_hero_{d_num}"):
                    layout_imgs['hero'] = edited_fields[f"day_img_hero_{d_num}"]
                if edited_fields.get(f"day_img_small1_{d_num}"):
                    layout_imgs['small-1'] = edited_fields[f"day_img_small1_{d_num}"]
                if edited_fields.get(f"day_img_small2_{d_num}"):
                    layout_imgs['small-2'] = edited_fields[f"day_img_small2_{d_num}"]
    
    visible_hotel_names = {
        hotel.get("name")
        for idx, hotel in enumerate(lang_ctx.get("hotels", []), 1)
        if f"hotel_name_{idx}" in existing_keys
    }

    # 2. Filter and update hotels
    new_hotels = []
    updated_hotel_dates: list[tuple[str, str]] = []
    for h_idx, hotel in enumerate(lang_ctx.get('hotels', []), 1):
        name_key = f"hotel_name_{h_idx}"
        keep_hidden_duplicate = (
            name_key not in existing_keys
            and hotel.get("name")
            and hotel.get("name") in visible_hotel_names
        )
        if name_key in existing_keys or keep_hidden_duplicate:
            # Preserve the original HTML-backed hotel index after dedup/filtering.
            hotel["_html_sync_index"] = h_idx
            if override_text and name_key in existing_keys:
                city_key = f"hotel_city_{h_idx}"
                date_key = f"hotel_date_{h_idx}"
                tel_key = f"hotel_tel_{h_idx}"
                intro_key = f"hotel_intro_{h_idx}"
                info_key = f"hotel_info_name_{h_idx}"
                
                if name_key in edited_fields:
                    hotel['name'] = edited_fields[name_key]
                    hotel['hotel_name'] = edited_fields[name_key]
                if city_key in edited_fields:
                    hotel['city_country'] = edited_fields[city_key]
                if date_key in edited_fields:
                    # The landing page used check_in_out while the PDF hotel
                    # cards use date_range. Keep both render aliases in sync
                    # so a saved hotel-date edit cannot disappear on download.
                    hotel_date = edited_fields[date_key]
                    hotel['check_in_out'] = hotel_date
                    hotel['date_range'] = hotel_date
                    updated_hotel_dates.append((hotel.get('name') or hotel.get('hotel_name') or "", hotel_date))
                if tel_key in edited_fields:
                    tel_value = re.sub(r'^\s*TEL:\s*', '', edited_fields[tel_key], flags=re.IGNORECASE)
                    hotel['tel'] = tel_value
                    hotel['telephone'] = tel_value
                if intro_key in edited_fields:
                    hotel['introduction'] = edited_fields[intro_key]
                    hotel['hotel_intro'] = edited_fields[intro_key]
                if info_key in edited_fields:
                    hotel['room_name'] = edited_fields[info_key]
                    hotel['room_type'] = edited_fields[info_key]
            new_hotels.append(hotel)
    lang_ctx['hotels'] = new_hotels

    # Route cards retain their own hotel date field. Mirror the hotel edit to
    # its matching stay so map/PDF data cannot retain a conflicting old range.
    for hotel_name, hotel_date in updated_hotel_dates:
        normalized_hotel_name = _normalize_visible_text(hotel_name).casefold()
        if not normalized_hotel_name:
            continue
        for segment in lang_ctx.get("stay_segments", []):
            segment_name = _normalize_visible_text(segment.get("hotelName") or "").casefold()
            if segment_name == normalized_hotel_name:
                segment["hotelDateRange"] = hotel_date
    
    # 3. Filter and update inclusions
    new_inclusions = []
    for inc_idx, item in enumerate(lang_ctx.get('inclusions', []), 1):
        key = f"inc_{inc_idx}"
        if key in existing_keys:
            if override_text and key in edited_fields:
                new_inclusions.append(edited_fields[key])
            else:
                new_inclusions.append(item)
    lang_ctx['inclusions'] = new_inclusions
    
    # 4. Filter and update exclusions
    new_exclusions = []
    for exc_idx, item in enumerate(lang_ctx.get('exclusions', []), 1):
        key = f"exc_{exc_idx}"
        if key in existing_keys:
            if override_text and key in edited_fields:
                new_exclusions.append(edited_fields[key])
            else:
                new_exclusions.append(item)
    lang_ctx['exclusions'] = new_exclusions

    if override_text:
        _sync_indexed_html_list(
            lang_ctx,
            existing_keys,
            edited_fields,
            list_key="final_req",
            field_prefix="final_req",
            fallback_single_key="final_req_text",
        )
        _sync_indexed_html_list(
            lang_ctx,
            existing_keys,
            edited_fields,
            list_key="final_after",
            field_prefix="final_after",
        )
    
    # 5. Filter and update pricing per pax
    new_price_options = []
    for p_idx, opt in enumerate(lang_ctx.get('price_options', []), 1):
        key = f"price_pax_{p_idx}"
        key_total = f"price_total_{p_idx}"
        key_cat = f"price_opt_cat_{p_idx}"
        key_name = f"price_opt_name_{p_idx}"
        if key in existing_keys or key_total in existing_keys or key_cat in existing_keys or key_name in existing_keys:
            if override_text:
                if key in edited_fields:
                    clean_val = re.sub(r'<[^>]*>', '', str(edited_fields[key])).strip()
                    if 'pricePerPerson' in opt and isinstance(opt['pricePerPerson'], dict):
                        opt['pricePerPerson']['displayText'] = clean_val
                if key_total in edited_fields:
                    clean_val = re.sub(r'<[^>]*>', '', str(edited_fields[key_total])).strip()
                    if 'totalPrice' in opt and isinstance(opt['totalPrice'], dict):
                        opt['totalPrice']['displayText'] = clean_val
                if key_cat in edited_fields:
                    clean_val = re.sub(r'<[^>]*>', '', str(edited_fields[key_cat])).strip()
                    opt['hotelCategory'] = clean_val
                if key_name in edited_fields:
                    clean_val = re.sub(r'<[^>]*>', '', str(edited_fields[key_name])).strip()
                    opt['optionName'] = clean_val

            # Guarantee sanitization of existing displayText values
            if 'pricePerPerson' in opt and isinstance(opt['pricePerPerson'], dict) and opt['pricePerPerson'].get('displayText'):
                opt['pricePerPerson']['displayText'] = re.sub(r'<[^>]*>', '', str(opt['pricePerPerson']['displayText'])).strip()
            if 'totalPrice' in opt and isinstance(opt['totalPrice'], dict) and opt['totalPrice'].get('displayText'):
                opt['totalPrice']['displayText'] = re.sub(r'<[^>]*>', '', str(opt['totalPrice']['displayText'])).strip()
            if opt.get('hotelCategory'):
                opt['hotelCategory'] = re.sub(r'<[^>]*>', '', str(opt['hotelCategory'])).strip()
            if opt.get('optionName'):
                opt['optionName'] = re.sub(r'<[^>]*>', '', str(opt['optionName'])).strip()

            new_price_options.append(opt)
    lang_ctx['price_options'] = new_price_options
    
    # 6. Filter and update map segment descriptions and sidebar fields
    if "stay_segments" in lang_ctx:
        # The prototype map creates these fields in JavaScript. Literal
        # placeholders such as map_segment_title_${idx} are not persisted
        # bindings and must not make all route segments disappear.
        has_route_segment_bindings = any(
            re.fullmatch(r"map_segment_(?:desc|duration|title|hotel)_\d+", key)
            for key in existing_keys | set(edited_fields.keys())
        )
        new_stay_segments = []
        for s_idx, segment in enumerate(lang_ctx["stay_segments"]):
            desc_key = f"map_segment_desc_{s_idx}"
            duration_key = f"map_segment_duration_{s_idx}"
            title_key = f"map_segment_title_{s_idx}"
            hotel_key = f"map_segment_hotel_{s_idx}"
            if has_route_segment_bindings and not any(
                key in existing_keys for key in (desc_key, duration_key, title_key, hotel_key)
            ):
                continue
            
            if desc_key in edited_fields and override_text:
                segment["mapSegmentDesc"] = _normalize_map_segment_description(edited_fields[desc_key])
            
            if duration_key in edited_fields and override_text:
                _apply_segment_duration_override(segment, edited_fields[duration_key])
                
            if title_key in edited_fields and override_text:
                segment["displayName"] = edited_fields[title_key]
                
            if hotel_key in edited_fields and override_text:
                segment["hotelName"] = edited_fields[hotel_key]
                
            new_stay_segments.append(segment)
        for idx, segment in enumerate(new_stay_segments):
            segment["order"] = idx + 1
            if idx == 0:
                segment["transportFromPrevious"] = ""
            else:
                previous = new_stay_segments[idx - 1]
                segment["transportFromPrevious"] = f"{previous['displayName']} → {segment['displayName']}"
        if has_route_segment_bindings:
            lang_ctx["stay_segments"] = new_stay_segments

    if "itinerary_days" in lang_ctx and "itinerary" in lang_ctx:
        existing_flat_days = {
            day.get("dayNumber"): day
            for day in lang_ctx.get("itinerary_days", [])
            if day.get("dayNumber")
        }
        rebuilt_flat_days = []
        for flat_idx, timeline_day in enumerate(lang_ctx.get("itinerary", [])):
            day_number = timeline_day.get("dayNumber")
            flat_day = copy.deepcopy(existing_flat_days.get(day_number, {}))
            if not flat_day:
                flat_day = {
                    "dayNumber": day_number,
                    "layout_type": "single",
                    "layout_images": {},
                    "is_alternate": bool(flat_idx % 2),
                }
            flat_day.update({
                "dayNumber": day_number,
                "date": timeline_day.get("date"),
                "lang": timeline_day.get("lang", lang_ctx.get("lang", "en")),
                "title": timeline_day.get("title", ""),
                "title_html": timeline_day.get("title_html", ""),
                "description": copy.deepcopy(timeline_day.get("description", [])),
                "description_html": copy.deepcopy(timeline_day.get("description_html", [])),
                "overnight": timeline_day.get("overnight", ""),
                "meals": copy.deepcopy(timeline_day.get("meals", [])),
                "activities": copy.deepcopy(timeline_day.get("activities", [])),
                "activities_html": timeline_day.get("activities_html", ""),
                "notes": copy.deepcopy(timeline_day.get("notes", [])),
                "notes_html": copy.deepcopy(timeline_day.get("notes_html", [])),
                "destinations": copy.deepcopy(timeline_day.get("destinations", [])),
                "label_highlights": timeline_day.get("label_highlights"),
                "label_notes": timeline_day.get("label_notes"),
                "label_overnight": timeline_day.get("label_overnight"),
                "label_meals": timeline_day.get("label_meals"),
            })
            if not flat_day.get("segment_city"):
                destinations = timeline_day.get("destinations") or []
                flat_day["segment_city"] = destinations[0] if destinations else timeline_day.get("overnight", "Vietnam")
            rebuilt_flat_days.append(flat_day)
        lang_ctx["itinerary_days"] = rebuilt_flat_days

def filter_and_override_ctx_by_html(lang_ctx: dict, html_content: str, override_text: bool = True):
    """
    Backward-compatible wrapper that derives editable state from HTML.
    """
    existing_keys = get_existing_editable_keys(html_content)
    edited_fields = parse_edited_fields(html_content)
    composite_fields = _capture_composite_sync_state(html_content)
    existing_keys, edited_fields, composite_fields = _sanitize_html_sync_payload(existing_keys, edited_fields, composite_fields)
    filter_and_override_ctx(
        lang_ctx,
        existing_keys,
        edited_fields,
        override_text=override_text,
    )
    _apply_composite_html_sync(lang_ctx, composite_fields)
    custom_images = _extract_custom_images_from_html(html_content)
    if custom_images.get("designer_img"):
        lang_ctx["designer_img"] = custom_images["designer_img"]
    if custom_images.get("hero_img"):
        lang_ctx["hero_img_custom"] = custom_images["hero_img"]
        lang_ctx["img_0"] = custom_images["hero_img"]
    if custom_images.get("img_hotel_divider"):
        lang_ctx["img_hotel_divider"] = custom_images["img_hotel_divider"]
    if custom_images.get("img_itinerary_divider"):
        lang_ctx["img_itinerary_divider"] = custom_images["img_itinerary_divider"]
    if "itinerary" in lang_ctx:
        lang_ctx["route_stops"] = _build_route_stops_from_timeline(lang_ctx.get("itinerary", []))
    lang = lang_ctx.get("lang", "en")
    if lang == "ar":
        lang_ctx.update(canonicalize_place_names_in_data(lang_ctx, lang))

def _get_lang_sync_key(target_lang: str | None, baseline_lang: str) -> str:
    if target_lang in ("en", "vi", "ar"):
        return target_lang
    return baseline_lang

def _extract_custom_images_from_html(html_content: str) -> dict:
    extracted = {}
    
    # Extract --designer-img
    designer_match = re.search(r'--designer-img:\s*url\((["\']?)(.*?)\1\)', html_content)
    if designer_match:
        extracted["designer_img"] = designer_match.group(2)
        
    # Extract --hero-img
    hero_match = re.search(r'--hero-img:\s*url\((["\']?)(.*?)\1\)', html_content)
    if hero_match:
        extracted["hero_img"] = hero_match.group(2)

    # Extract img_hotel_divider
    hotel_div_match = re.search(r'data-editable=["\']img_hotel_divider["\'][^>]*src=["\']([^"\']+)["\']', html_content)
    if not hotel_div_match:
        hotel_div_match = re.search(r'src=["\']([^"\']+)["\'][^>]*data-editable=["\']img_hotel_divider["\']', html_content)
    if hotel_div_match:
        extracted["img_hotel_divider"] = hotel_div_match.group(1)

    # Extract img_itinerary_divider
    iti_div_match = re.search(r'data-editable=["\']img_itinerary_divider["\'][^>]*url\((["\']?)(.*?)\1\)', html_content)
    if not iti_div_match:
        iti_div_match = re.search(r'data-editable=["\']img_itinerary_divider["\'][^>]*src=["\']([^"\']+)["\']', html_content)
    if iti_div_match:
        extracted["img_itinerary_divider"] = iti_div_match.group(2 if len(iti_div_match.groups()) > 1 else 1)
        
    return extracted

def _capture_html_sync_state(html_content: str) -> dict:
    existing_keys = get_existing_editable_keys(html_content)
    edited_fields = parse_edited_fields(html_content)
    existing_keys, edited_fields, composite_fields = _sanitize_html_sync_payload(
        existing_keys,
        edited_fields,
        _capture_composite_sync_state(html_content),
    )
    return {
        "existing_keys": sorted(existing_keys),
        "edited_fields": edited_fields,
        "composite_fields": composite_fields,
    }

def _save_ctx_html_sync_state(ctx_data: dict, target_lang: str | None, html_content: str, captured_from_version: int | None = None) -> str:
    baseline_lang = ctx_data.get("baseline_lang", "en")
    lang_key = _get_lang_sync_key(target_lang, baseline_lang)
    html_sync = ctx_data.setdefault("html_sync", {})
    html_sync_state = _capture_html_sync_state(html_content)
    if captured_from_version is not None:
        html_sync_state["captured_from_version"] = captured_from_version
    html_sync[lang_key] = html_sync_state
    return lang_key

def _sync_ctx_data_before_publish(ctx_data: dict, rendered_html: str, target_lang: str | None, version: int | None = None) -> dict:
    """Ensures ctx_data html_sync and itinerary_days image arrays match the rendered HTML version."""
    if not ctx_data or not rendered_html:
        return ctx_data
    _save_ctx_html_sync_state(ctx_data, target_lang, rendered_html, captured_from_version=version)
    filter_and_override_ctx_by_html(ctx_data, rendered_html, override_text=True)
    composite_sync = _capture_composite_sync_state(rendered_html)
    itinerary_img_map = composite_sync.get("itinerary_days", {})
    itinerary_list = ctx_data.get("itinerary_days") or ctx_data.get("itinerary") or []
    if itinerary_img_map and itinerary_list:
        for idx, day_obj in enumerate(itinerary_list, 1):
            day_img_info = itinerary_img_map.get(str(idx))
            if day_img_info:
                layout_images = {
                    "hero": day_img_info.get("hero", ""),
                    "small-1": day_img_info.get("small-1", ""),
                    "small-2": day_img_info.get("small-2", ""),
                }
                normalized_carousel = _dedupe_image_refs(day_img_info.get("carousel") or [])
                if normalized_carousel:
                    layout_images["carousel"] = normalized_carousel
                    day_obj["carousel"] = normalized_carousel
                day_obj["layout_images"] = layout_images
    return ctx_data

def _apply_composite_html_sync(lang_ctx: dict, composite_fields: dict):
    if not composite_fields:
        return

    top_level = composite_fields.get("top_level", {})
    for key, value in top_level.items():
        if key not in BRAND_OWNED_CTX_FIELDS and value:
            lang_ctx[key] = value

    hotels = composite_fields.get("hotels", {})
    if hotels:
        for idx, hotel in enumerate(lang_ctx.get("hotels", []), 1):
            source_idx = hotel.get("_html_sync_index", idx)
            hotel_sync = hotels.get(str(source_idx))
            if not hotel_sync:
                continue
            if hotel_sync.get("hotel_intro"):
                intro_text = html.unescape(hotel_sync["hotel_intro"])
                hotel["introduction"] = intro_text
                hotel["hotel_intro"] = intro_text
            if hotel_sync.get("room_type"):
                room_type = html.unescape(hotel_sync["room_type"])
                hotel["room_type"] = room_type
                hotel["room_name"] = room_type
            if hotel_sync.get("hotel_img"):
                hotel["hotel_img"] = hotel_sync["hotel_img"]
            if hotel_sync.get("room_img"):
                hotel["room_img"] = hotel_sync["room_img"]

    itinerary_days = composite_fields.get("itinerary_days", {})
    if itinerary_days:
        def apply_day_sync(day_entry: dict):
            day_number = day_entry.get("dayNumber")
            if not day_number:
                return
            day_sync = itinerary_days.get(str(day_number))
            if not day_sync:
                return
            layout_images = copy.deepcopy(day_entry.get("layout_images") or {})
            for key in ("hero", "small-1", "small-2"):
                if day_sync.get(key):
                    layout_images[key] = day_sync[key]
            if day_sync.get("carousel"):
                layout_images["carousel"] = _dedupe_image_refs(day_sync["carousel"])
            day_entry["layout_images"] = layout_images
            if day_sync.get("segment_city"):
                segment_city = html.unescape(day_sync["segment_city"])
                day_entry["segment_city"] = segment_city
                existing_destinations = [
                    html.unescape(str(dest)).strip()
                    for dest in (day_entry.get("destinations") or [])
                    if str(dest).strip()
                ]
                if segment_city and len(existing_destinations) <= 1:
                    day_entry["destinations"] = [segment_city]

        for day in lang_ctx.get("itinerary", []):
            apply_day_sync(day)
        for day in lang_ctx.get("itinerary_days", []):
            apply_day_sync(day)

        for chapter in lang_ctx.get("chapters", []):
            for day in chapter.get("days", []):
                apply_day_sync(day)

def _apply_ctx_html_sync(
    lang_ctx: dict,
    ctx_data: dict,
    target_lang: str,
    baseline_lang: str,
) -> bool:
    html_sync = ctx_data.get("html_sync", {})
    applied = False

    lang_sync = html_sync.get(target_lang)
    if lang_sync:
        filter_and_override_ctx(
            lang_ctx,
            set(lang_sync.get("existing_keys", [])),
            lang_sync.get("edited_fields", {}),
            override_text=True,
        )
        _apply_composite_html_sync(lang_ctx, lang_sync.get("composite_fields", {}))
        if "itinerary" in lang_ctx:
            lang_ctx["route_stops"] = _build_route_stops_from_timeline(lang_ctx.get("itinerary", []))
        if target_lang == "ar":
            lang_ctx.update(canonicalize_place_names_in_data(lang_ctx, target_lang))
        return True

    if target_lang != baseline_lang:
        baseline_sync = html_sync.get(baseline_lang)
        if baseline_sync:
            filter_and_override_ctx(
                lang_ctx,
                set(baseline_sync.get("existing_keys", [])),
                {},
                override_text=False,
            )
            _apply_composite_html_sync(lang_ctx, baseline_sync.get("composite_fields", {}))
            if "itinerary" in lang_ctx:
                lang_ctx["route_stops"] = _build_route_stops_from_timeline(lang_ctx.get("itinerary", []))
            if target_lang == "ar":
                lang_ctx.update(canonicalize_place_names_in_data(lang_ctx, target_lang))
            applied = True

    return applied


async def _build_quotation_lang_ctx(
    ctx_data: dict,
    quotation_id: str,
    target_lang: str,
    request: Request = None,
    *,
    ignore_published_html: bool = False,
    force_editor_draft: bool = False,
):
    baseline_lang = ctx_data.get("baseline_lang", "en")
    effective_lang = target_lang if target_lang in ("en", "vi", "ar") else baseline_lang
    base_tmpl = ctx_data.get("template_name", BROCHURE_TEMPLATE_NAME)

    if _is_brochure_template(base_tmpl):
        document = _get_stored_brochure_draft(ctx_data, effective_lang)
        if not document:
            _, canonical_document, canonical_lang = await _load_canonical_quote_document_from_db(
                quotation_id,
                effective_lang,
            )
            if canonical_document:
                document = _store_brochure_draft(ctx_data, canonical_lang or effective_lang, canonical_document)
                effective_lang = canonical_lang or effective_lang
        if not document:
            persisted_document = _load_persisted_quote_document(quotation_id)
            if persisted_document:
                persisted_lang = ((persisted_document.get("meta") or {}).get("lang")) or effective_lang
                document = _store_brochure_draft(ctx_data, persisted_lang, persisted_document)
                effective_lang = persisted_lang
        if not document:
            payload_dict = (
                ctx_data.get("baseline_payload")
                if effective_lang == baseline_lang
                else ctx_data.get("translations", {}).get(effective_lang)
            )
            if not payload_dict:
                payload_dict = ctx_data.get("baseline_payload")
                effective_lang = baseline_lang
            if payload_dict:
                payload_obj = TourQuotationPayload.model_validate(payload_dict)
                brand_config = resolve_brand(request, payload_dict)
                default_brand_logo = _default_brand_logo(brand_config)
                hero_image_url = ctx_data.get("hero_img") or ctx_data.get("img_0") or default_brand_logo
                legacy_ctx = _build_ctx(
                    quotation_id=quotation_id,
                    payload=payload_obj,
                    hero_image_url=hero_image_url,
                    destinations=ctx_data.get("destinations", []),
                    lang=effective_lang,
                    template_name=base_tmpl,
                    brand=brand_config,
                )
                latest_lang = None if effective_lang == baseline_lang else effective_lang
                latest_html = await _get_latest_published_html(
                    quotation_id,
                    lang=latest_lang,
                    fallback=False,
                )
                if latest_html:
                    filter_and_override_ctx_by_html(legacy_ctx, latest_html, override_text=True)
                elif effective_lang != baseline_lang:
                    baseline_html = await _get_latest_published_html(
                        quotation_id,
                        lang=None,
                        fallback=False,
                    )
                    if baseline_html:
                        filter_and_override_ctx_by_html(legacy_ctx, baseline_html, override_text=False)
                    else:
                        _apply_ctx_html_sync(legacy_ctx, ctx_data, effective_lang, baseline_lang)
                else:
                    _apply_ctx_html_sync(legacy_ctx, ctx_data, effective_lang, baseline_lang)
                document = _store_brochure_draft(
                    ctx_data,
                    effective_lang,
                    _build_brochure_draft_from_lang_ctx(legacy_ctx, quotation_id, effective_lang),
                )
            else:
                raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' is missing brochure document data.")
        try:
            from github_publish import get_next_version
            next_ver = await get_next_version(quotation_id)
            latest_version = max(1, next_ver - 1)
        except Exception:
            latest_version = 1
        lang_ctx = _merge_brochure_render_context(
            ctx_data,
            document,
            quotation_id,
            effective_lang,
            latest_version=latest_version,
            preview_mode=False,
            editor_mode=force_editor_draft,
        )
        if not ignore_published_html:
            latest_lang = None if effective_lang == baseline_lang else effective_lang
            html_content = await _get_latest_published_html(quotation_id, lang=latest_lang, fallback=False)
            if html_content:
                filter_and_override_ctx_by_html(lang_ctx, html_content, override_text=True)
            elif effective_lang != baseline_lang:
                baseline_html = await _get_latest_published_html(quotation_id, lang=None, fallback=False)
                if baseline_html:
                    filter_and_override_ctx_by_html(lang_ctx, baseline_html, override_text=False)
                else:
                    _apply_ctx_html_sync(lang_ctx, ctx_data, effective_lang, baseline_lang)
            else:
                _apply_ctx_html_sync(lang_ctx, ctx_data, effective_lang, baseline_lang)
        else:
            _apply_ctx_html_sync(lang_ctx, ctx_data, effective_lang, baseline_lang)
        return lang_ctx, effective_lang, base_tmpl

    payload_dict = (
        ctx_data.get("baseline_payload")
        if effective_lang == baseline_lang
        else ctx_data.get("translations", {}).get(effective_lang)
    )
    if not payload_dict:
        payload_dict = ctx_data.get("baseline_payload")
        effective_lang = baseline_lang

    payload_obj = TourQuotationPayload.model_validate(payload_dict)
    brand_config = resolve_brand(request, payload_dict)
    default_brand_logo = _default_brand_logo(brand_config)
    hero_image_url = ctx_data.get("hero_img") or ctx_data.get("img_0") or default_brand_logo
    if _is_brand_placeholder_image(hero_image_url):
        for day in ctx_data.get("itinerary_days", []) or ctx_data.get("itinerary", []):
            day_hero = day.get("layout_images", {}).get("hero")
            if day_hero and not _is_brand_placeholder_image(day_hero):
                hero_image_url = day_hero
                break
        else:
            hero_image_url = default_brand_logo

    lang_ctx = _build_ctx(
        quotation_id=quotation_id,
        payload=payload_obj,
        hero_image_url=hero_image_url,
        destinations=ctx_data.get("destinations", []),
        lang=effective_lang,
        template_name=base_tmpl,
        brand=brand_config,
    )
    # Published HTML only records editable fields. Keep the persisted route
    # arrays as the structural source of truth so a PDF render cannot rebuild
    # the final Siem Reap stay from the older payload.
    for structural_key in (
        "itinerary",
        "timeline_days",
        "route_stops",
        "stay_segments",
        "itinerary_days",
    ):
        if structural_key in ctx_data:
            lang_ctx[structural_key] = copy.deepcopy(ctx_data[structural_key])
    brand_locked_fields = _capture_brand_owned_fields(lang_ctx)
    brand_switched = _is_brand_switched(ctx_data, brand_config)
    lang_ctx["brand"] = brand_config
    if ctx_data.get("designer_img"):
        lang_ctx["designer_img"] = ctx_data.get("designer_img")
    if ctx_data.get("hero_img"):
        lang_ctx["hero_img_custom"] = ctx_data.get("hero_img")
        lang_ctx["img_0"] = ctx_data.get("hero_img")
    elif hero_image_url != default_brand_logo:
        lang_ctx["hero_img_custom"] = hero_image_url
        lang_ctx["img_0"] = hero_image_url
    if ctx_data.get("img_itinerary_divider"):
        lang_ctx["img_itinerary_divider"] = ctx_data.get("img_itinerary_divider")
    if ctx_data.get("img_hotel_divider"):
        lang_ctx["img_hotel_divider"] = ctx_data.get("img_hotel_divider")
    lang_ctx["translations"] = ctx_data.get("translations", {})
    lang_ctx["baseline_lang"] = baseline_lang
    lang_ctx["translation_status"] = ctx_data.get(
        "translation_status",
        {"baseline_lang": baseline_lang, "available_langs": [baseline_lang]},
    )
    try:
        from github_publish import get_next_version
        next_ver = await get_next_version(quotation_id)
        lang_ctx["latest_version"] = max(1, next_ver - 1)
    except Exception:
        lang_ctx["latest_version"] = 1

    if not ignore_published_html:
        latest_lang = None if effective_lang == baseline_lang else effective_lang
        html_content = await _get_latest_published_html(quotation_id, lang=latest_lang, fallback=False)
        if html_content:
            filter_and_override_ctx_by_html(lang_ctx, html_content, override_text=True)
        elif effective_lang != baseline_lang:
            baseline_html = await _get_latest_published_html(quotation_id, lang=None, fallback=False)
            if baseline_html:
                filter_and_override_ctx_by_html(lang_ctx, baseline_html, override_text=False)
            else:
                _apply_ctx_html_sync(lang_ctx, ctx_data, effective_lang, baseline_lang)
        else:
            _apply_ctx_html_sync(lang_ctx, ctx_data, effective_lang, baseline_lang)

        # html_sync is the persisted editor state for this quotation. A
        # versioned landing-page snapshot is only a presentation artifact and
        # may predate a saved edit, so it must not overwrite html_sync.
        _apply_ctx_html_sync(lang_ctx, ctx_data, effective_lang, baseline_lang)

    if brand_switched:
        _restore_brand_owned_fields(lang_ctx, brand_locked_fields)
    elif ignore_published_html:
        _apply_ctx_html_sync(lang_ctx, ctx_data, effective_lang, baseline_lang)

    return lang_ctx, effective_lang, base_tmpl

async def _render_quotation_doc_from_ctx(
    ctx_data: dict,
    quotation_id: str,
    target_lang: str,
    request: Request = None,
    is_pdf: bool = True,
    ignore_published_html: bool = False,
    preview_mode: bool = False,
    editor_mode: bool = False,
) -> tuple[str, str]:
    lang_ctx, effective_lang, base_tmpl = await _build_quotation_lang_ctx(
        ctx_data,
        quotation_id,
        target_lang,
        request,
        ignore_published_html=ignore_published_html,
        force_editor_draft=editor_mode,
    )
    tmpl_name = base_tmpl.replace(".html", "_pdf.html") if is_pdf else base_tmpl
    tmpl = templates.get_template(tmpl_name)
    lang_ctx["brochure_preview_mode"] = bool(preview_mode)
    lang_ctx["use_shared_draft_editor"] = bool(editor_mode and _is_brochure_template(base_tmpl))

    rendered_html = tmpl.render(**lang_ctx)
    return rendered_html, effective_lang

async def _get_latest_published_html(quotation_id: str, lang: str = None, fallback: bool = True) -> str | None:
    """Gets the latest published HTML content from memory, disk, or GitHub."""
    from github_publish import get_next_version
    next_version = await get_next_version(quotation_id)
    if next_version <= 1:
        if not lang:
            entry = quotations.get(quotation_id)
            if entry and entry.get("html"):
                return entry["html"]
        return None
    current_version = next_version - 1
    
    # Try language specific published file first (e.g. v1_ar.html)
    lang_suffix = f"_{lang}" if lang else ""
    file_options = [
        f"{quotation_id}/v{current_version}{lang_suffix}.html"
    ]
    if fallback and lang:
        file_options.append(f"{quotation_id}/v{current_version}.html")
    
    for file_path in file_options:
        local_path = os.path.join("published", file_path)
        if os.path.isfile(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass

        # Fetch from GitHub if production
        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            repo = os.getenv("GITHUB_REPO")
            token = os.getenv("GITHUB_TOKEN")
            if repo and token:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    headers = {
                        "Authorization": f"token {token}", 
                        "Accept": "application/vnd.github.v3.raw"
                    }
                    gh_url = f"https://api.github.com/repos/{repo}/contents/published/{file_path}"
                    resp = await client.get(gh_url, headers=headers)
                    if resp.status_code == 200:
                        return resp.text

    if not lang:
        entry = quotations.get(quotation_id)
        if entry and entry.get("html"):
            return entry["html"]
    return None

async def _get_latest_published_pdf_html(quotation_id: str, lang: str = None) -> str | None:
    """Gets the latest published static PDF HTML content from disk or GitHub."""
    lang_suffix = f"_{lang}" if lang else ""
    file_options = [
        f"{quotation_id}/pdf{lang_suffix}.html",
        f"{quotation_id}/pdf.html",
    ]
    try:
        from github_publish import get_next_version
        next_ver = await get_next_version(quotation_id)
        if next_ver > 1:
            ver = next_ver - 1
            file_options.insert(0, f"{quotation_id}/v{ver}_pdf{lang_suffix}.html")
            file_options.insert(1, f"{quotation_id}/v{ver}_pdf.html")
    except Exception:
        pass

    for file_path in file_options:
        local_path = os.path.join("published", file_path)
        if os.path.isfile(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content and len(content) > 100:
                        return content
            except Exception:
                pass

        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            repo = os.getenv("GITHUB_REPO")
            token = os.getenv("GITHUB_TOKEN")
            if repo and token:
                import httpx
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        headers = {
                            "Authorization": f"token {token}", 
                            "Accept": "application/vnd.github.v3.raw"
                        }
                        gh_url = f"https://api.github.com/repos/{repo}/contents/published/{file_path}"
                        resp = await client.get(gh_url, headers=headers)
                        if resp.status_code == 200 and len(resp.text) > 100:
                            return resp.text
                except Exception:
                    pass
    return None

@app.get("/quotations/{quotation_id}/pdf", response_class=HTMLResponse)
async def get_quotation_pdf(quotation_id: str, request: Request):
    """
    Dynamically renders PDF HTML for a quotation in target language.
    Auto-triggers the browser print dialog.
    """
    lang = request.query_params.get("lang") or request.query_params.get("language")
    if lang not in ("en", "vi", "ar"):
        lang = None
        
    ctx_data = _load_ctx_data(quotation_id)
    if not ctx_data:
        raise HTTPException(status_code=404, detail=f"PDF for quotation '{quotation_id}' not found.")
        
    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = lang or baseline_lang
    preview_mode = request.query_params.get("preview") in {"1", "true", "yes"}
    requested_brand = request.query_params.get("brand")
    template_name = ctx_data.get("template_name", BROCHURE_TEMPLATE_NAME)
    # A published PDF artifact is brand-specific. It cannot safely satisfy a
    # URL which asks the renderer to resolve a different brand at request time.
    # In that case render from the canonical context and current template.
    use_static_pdf_cache = (
        not preview_mode
        and not requested_brand
        and template_name not in LEGACY_QUOTATION_TEMPLATES
    )

    if use_static_pdf_cache:
        published_pdf = await _get_latest_published_pdf_html(quotation_id, target_lang)
        if published_pdf:
            return HTMLResponse(content=published_pdf)
    
    # Trigger lazy translation if not available
    if target_lang != baseline_lang:
        available_langs = ctx_data.get("available_langs", [])
        if target_lang not in available_langs:
            success = await _translate_item_on_demand(quotation_id, target_lang, is_itinerary=False)
            if success:
                ctx_data = _load_ctx_data(quotation_id) or ctx_data
                
    # Extract appropriate payload dict
    if target_lang == baseline_lang:
        payload_dict = ctx_data.get("baseline_payload")
    else:
        payload_dict = ctx_data.get("translations", {}).get(target_lang)
        
    if not payload_dict:
        payload_dict = ctx_data.get("baseline_payload")
        target_lang = baseline_lang
        
    try:
        rendered_html, effective_lang = await _render_quotation_doc_from_ctx(
            ctx_data,
            quotation_id,
            target_lang,
            request,
            is_pdf=True,
            preview_mode=preview_mode,
        )
        if _is_brochure_template(ctx_data.get("template_name", "vietnam_luxury_brosure.html")):
            lang_ctx, _, _ = await _build_quotation_lang_ctx(
                ctx_data,
                quotation_id,
                effective_lang,
                request,
                ignore_published_html=True,
                force_editor_draft=preview_mode,
            )
            draft = _ensure_brochure_draft(ctx_data, quotation_id, effective_lang, lang_ctx, force_brand_from_ctx=preview_mode)
            _store_brochure_draft(ctx_data, effective_lang, draft)
        return HTMLResponse(content=rendered_html)
    except Exception as err:
        log.exception("[/quotations] Dynamic PDF render failed for %s: %s", quotation_id, err)
        raise HTTPException(status_code=500, detail=f"PDF render error: {err}")


@app.post("/api/v1/quotations/{quotation_id}/translate")
async def translate_quotation_endpoint(quotation_id: str, lang: str):
    """Triggers on-demand translation for a quotation."""
    if lang not in ("en", "vi", "ar"):
        raise HTTPException(status_code=400, detail="Unsupported language")
    success = await _translate_item_on_demand(quotation_id, lang, is_itinerary=False)
    if not success:
        raise HTTPException(status_code=500, detail="Translation failed")
    status = _load_translation_status(quotation_id)
    return status

@app.post("/api/v1/itineraries/{itinerary_id}/translate")
async def translate_itinerary_endpoint(itinerary_id: str, lang: str):
    """Triggers on-demand translation for an itinerary."""
    if lang not in ("en", "vi", "ar"):
        raise HTTPException(status_code=400, detail="Unsupported language")
    success = await _translate_item_on_demand(itinerary_id, lang, is_itinerary=True)
    if not success:
        raise HTTPException(status_code=500, detail="Translation failed")
    status = _load_translation_status(itinerary_id)
    return status

@app.get("/api/v1/quotations/{quotation_id}/translation-status")
async def get_quotation_translation_status(quotation_id: str):
    """Returns the translation status of a quotation."""
    status = _load_translation_status(quotation_id)
    try:
        from github_publish import get_next_version
        next_ver = await get_next_version(quotation_id)
        status["latest_version"] = max(1, next_ver - 1)
    except Exception:
        status["latest_version"] = 1
    return status

@app.get("/api/v1/itineraries/{itinerary_id}/translation-status")
async def get_itinerary_translation_status(itinerary_id: str):
    """Returns the translation status of an itinerary."""
    status = _load_translation_status(itinerary_id)
    try:
        from github_publish import get_next_version
        next_ver = await get_next_version(itinerary_id)
        status["latest_version"] = max(1, next_ver - 1)
    except Exception:
        status["latest_version"] = 1
    return status


class TranslateBlockRequest(BaseModel):
    text: str
    target_lang: str


class DraftUpsertRequest(BaseModel):
    draft: dict[str, Any]


class QuoteDocumentUpsertRequest(BaseModel):
    document: dict[str, Any]
    baseRevision: Optional[int] = None


class QuoteDocumentPublishRequest(BaseModel):
    document: Optional[dict[str, Any]] = None
    template_name: Optional[str] = None
    baseRevision: Optional[int] = None


class MediaLibraryLocationRequest(BaseModel):
    kind: Literal["destination", "accommodation", "team"]
    destinationId: str | None = None
    destinationName: str | None = None
    accommodationName: str | None = None
    accommodationKind: Literal["hotel", "cruise"] | None = None
    accommodationId: str | None = None
    accommodationAssetCategory: Literal["exteriors", "interiors"] | None = None
    travelDesignerId: str | None = None


class TravelDesignerProfileRequest(BaseModel):
    name: str
    email: str
    phone: str = ""
    imageR2Key: str | None = None


class AccommodationProfileRequest(BaseModel):
    destinationId: str
    name: str
    room_type: str | None = None
    intro: str | None = None
    phone: str | None = None
    display_city: str | None = None
    display_date: str | None = None
    hotel_asset: str | None = None
    room_asset: str | None = None


class AccommodationStatusRequest(BaseModel):
    isActive: bool


class DestinationCatalogRequest(BaseModel):
    canonicalName: str
    slug: str
    aliases: list[str] = Field(default_factory=list)
    countrySlug: str | None = None
    regionSlug: str | None = None
    provinceSlug: str | None = None
    latitude: float
    longitude: float

    @field_validator("canonicalName", "slug")
    @classmethod
    def require_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("must be between -180 and 180")
        return value


class DestinationStatusRequest(BaseModel):
    isActive: bool


class TravelDesignerBrandDefaultRequest(BaseModel):
    designerProfileId: str


def _apply_travel_designer_snapshot(document: dict[str, Any], profile: dict[str, Any] | None) -> None:
    """Apply only profile-owned designer fields, preserving editorial copy.

    A designer profile supplies identity/contact/image.  The quotation itself
    owns narrative fields such as quote, kicker, and experience, so changing a
    profile must never erase an editor's copy.
    """
    designer = document.setdefault("designer", {})
    profile_fields = ("profileId", "name", "email", "phone", "image", "signatureInitial")
    if profile is None:
        for field in profile_fields:
            designer.pop(field, None)
        return
    designer.update(
        {
            "profileId": profile["id"],
            "name": profile.get("name") or "",
            "email": profile.get("email") or "",
            "phone": profile.get("phone") or "",
            "signatureInitial": profile.get("signatureInitial") or None,
            "image": {
                "assetId": profile.get("imageAssetId") or "",
                "r2Key": profile.get("imageR2Key") or "",
                "url": profile.get("imageUrl") or "",
                "status": "ready" if (profile.get("imageAssetId") or profile.get("imageR2Key") or profile.get("imageUrl")) else "empty",
            },
        }
    )


async def _seed_destination_catalog(session) -> None:
    from destination_catalog_seed import get_seed_destination_profiles

    repository = DestinationRepository(session)
    for profile in get_seed_destination_profiles():
        await repository.upsert(
            destination_id=f"dst_{profile['slug']}",
            canonical_name=profile["canonical_name"],
            slug=profile["slug"],
            aliases=profile["aliases"],
            country_slug=profile["country_slug"],
            region_slug=profile["region_slug"],
            province_slug=profile["province_slug"],
            latitude=profile["latitude"],
            longitude=profile["longitude"],
        )


async def _canonicalize_quote_destinations(payload: CreateQuoteRequestV1) -> tuple[CreateQuoteRequestV1, dict[str, Any]]:
    """Resolve every user-facing destination before a quotation is generated or persisted."""
    missing: list[str] = []
    refs: dict[str, Any] = {"routeDestinationRefs": [], "itinerary": [], "hotels": []}
    async with _get_db_session_factory()() as session:
        await _seed_destination_catalog(session)
        repository = DestinationRepository(session)

        async def resolve(value: str, path: str):
            item = await repository.resolve(value)
            if item is None:
                missing.append(path)
                return None
            default_prefix = destination_default_media_prefix(item)
            return {
                "id": item.id,
                "name": item.canonical_name,
                "slug": item.slug,
                "mediaPrefix": item.media_prefix,
                "defaultMediaPrefix": default_prefix,
            }

        route: list[str] = []
        for index, value in enumerate(payload.trip_facts.destinations):
            ref = await resolve(value, f"trip_facts.destinations[{index}]")
            if ref:
                route.append(ref["name"]); refs["routeDestinationRefs"].append(ref)
        payload.trip_facts.destinations = route
        for index, day in enumerate(payload.trip_facts.itinerary):
            ref = await resolve(day.destination, f"trip_facts.itinerary[{index}].destination") if day.destination else None
            if ref: day.destination = ref["name"]
            refs["itinerary"].append({"dayNumber": day.day_number, "destinationRef": ref})
        for index, hotel in enumerate(payload.service_facts.hotels):
            ref = await resolve(hotel.destination, f"service_facts.hotels[{index}].destination") if hotel.destination else None
            if ref: hotel.destination = ref["name"]
            refs["hotels"].append({"index": index, "destinationRef": ref})
        if missing:
            raise HTTPException(status_code=422, detail={"message": "Destination not found in catalog.", "missingInputs": missing})
        await session.commit()
    return payload, refs


async def _resolve_media_location(session, payload: MediaLibraryLocationRequest):
    await _seed_destination_catalog(session)
    destinations = DestinationRepository(session)
    if payload.kind == "team":
        if not payload.travelDesignerId:
            raise HTTPException(status_code=422, detail={"missingInputs": ["travelDesignerId"]})
        profile = await TravelDesignerRepository(session).get_profile(payload.travelDesignerId)
        if profile is None:
            raise HTTPException(status_code=404, detail="Travel Designer profile was not found.")
        return team_location(profile)
    if payload.kind == "accommodation" and payload.accommodationId:
        profile = await AccommodationRepository(session).get_profile(payload.accommodationId)
        if profile is None:
            raise HTTPException(status_code=404, detail="Accommodation profile was not found.")
        if payload.accommodationAssetCategory is None:
            raise HTTPException(status_code=422, detail={"missingInputs": ["accommodationAssetCategory"]})
        try:
            return accommodation_asset_location(
                asset_prefix=profile.asset_prefix,
                profile_id=profile.id,
                destination_id=profile.destination_id,
                accommodation_slug=profile.storage_slug,
                asset_category=payload.accommodationAssetCategory,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc), "missingInputs": ["accommodationId"]}) from exc
    destination = await session.get(__import__("db.models.destination", fromlist=["DestinationCatalog"]).DestinationCatalog, payload.destinationId) if payload.destinationId else await destinations.resolve(payload.destinationName or "")
    if destination is None:
        raise HTTPException(status_code=422, detail={"missingInputs": ["destinationId"]})
    try:
        if payload.kind == "destination":
            return destination_location(destination)
        if not payload.accommodationName or not payload.accommodationKind:
            raise HTTPException(status_code=422, detail={"missingInputs": ["accommodationName", "accommodationKind"]})
        return accommodation_location(destination, payload.accommodationName, payload.accommodationKind)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "missingInputs": ["destination geographic mapping"]}) from exc


from routers.v1.translations import (
    get_itinerary_translation_status,
    get_quotation_translation_status,
    translate_block_endpoint,
    translate_itinerary_endpoint,
    translate_quotation_endpoint,
)


@app.get("/api/v1/quotations/{quotation_id}/draft")
async def get_quotation_draft(quotation_id: str, request: Request, lang: str | None = None, language: str | None = None):
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    ctx_data = _load_ctx_data(quotation_id)
    if not ctx_data:
        raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")

    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = target_lang or baseline_lang
    template_name = ctx_data.get("template_name", "vietnam_luxury_brosure.html")
    if not _is_brochure_template(template_name):
        raise HTTPException(status_code=400, detail="Draft editor is only available for brochure quotations.")

    lang_ctx, effective_lang, _ = await _build_quotation_lang_ctx(
        ctx_data,
        quotation_id,
        target_lang,
        request,
        ignore_published_html=True,
        force_editor_draft=True,
    )
    draft = _ensure_brochure_draft(ctx_data, quotation_id, effective_lang, lang_ctx, force_brand_from_ctx=True)
    # GET must remain read-only. Persist only through PUT /draft or publish;
    # otherwise merely opening or refreshing the editor writes ctx.json and
    # creates a GitHub commit on every request.
    return {"draft": draft, "lang": effective_lang}


@app.put("/api/v1/quotations/{quotation_id}/draft")
async def put_quotation_draft(
    quotation_id: str,
    payload: DraftUpsertRequest,
    request: Request,
    lang: str | None = None,
    language: str | None = None,
):
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    ctx_data = _load_ctx_data(quotation_id)
    if not ctx_data:
        raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")

    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = target_lang or baseline_lang
    template_name = ctx_data.get("template_name", "vietnam_luxury_brosure.html")
    if not _is_brochure_template(template_name):
        raise HTTPException(status_code=400, detail="Draft editor is only available for brochure quotations.")

    draft = copy.deepcopy(payload.draft or {})
    draft.setdefault("meta", {})
    draft["meta"]["quotationId"] = quotation_id
    draft["meta"]["lang"] = target_lang
    draft["meta"]["template"] = template_name
    draft["meta"]["revision"] = int(draft["meta"].get("revision") or 0) + 1

    _store_brochure_draft(ctx_data, target_lang, draft)
    await _persist_ctx_data(quotation_id, ctx_data, f"Autosave brochure draft for quotation {quotation_id} ({target_lang})")
    return {"ok": True, "draft": draft}


@app.get("/api/v2/quotations/{quotation_id}/document")
async def get_quotation_document(quotation_id: str, request: Request, lang: str | None = None, language: str | None = None, principal: Principal = Depends(require_editor), _owned=Depends(require_owned_quotation)):
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    quotation, document, effective_lang = await _load_canonical_quote_document_from_db(quotation_id, target_lang)
    if quotation is None:
        raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")
    if quotation.template_name != V2_RENDERER_NAME:
        raise HTTPException(status_code=400, detail="Document is not a React V2 quotation.")
    if document is None:
        raise HTTPException(status_code=404, detail="No quote document available.")
    brand = await _require_active_v2_brand(quotation.brand_id)
    return {
        "document": _hydrate_r2_asset_urls(document),
        "lang": effective_lang,
        "documentVersion": ((document.get("meta") or {}).get("version")) or 1,
        "currentRevision": ((document.get("meta") or {}).get("revision")) or 1,
        "sectionRegistry": {key: value.model_dump(mode="json") for key, value in SECTION_REGISTRY.items()},
        "contentRegistry": content_registry_for_document_payload(document),
        "contentEditorState": content_editor_state_payload(document),
        "editableContract": editable_contract_payload(),
        "brandProfile": _serialize_brand_render_profile(brand),
    }


@app.put("/api/v2/quotations/{quotation_id}/document")
async def put_quotation_document(
    quotation_id: str,
    payload: QuoteDocumentUpsertRequest,
    request: Request,
    lang: str | None = None,
    language: str | None = None,
    principal: Principal = Depends(require_editor),
    _owned=Depends(require_owned_quotation),
):
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    document = copy.deepcopy(payload.document or {})
    try:
        async with _get_db_session_factory()() as session:
            quotation_repository = QuotationRepository(session)
            document_repository = QuotationDocumentRepository(session)

            quotation = await quotation_repository.get_quotation_by_id(quotation_id)
            if quotation is None:
                raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")

            effective_lang = target_lang or quotation.baseline_lang
            if quotation.template_name != V2_RENDERER_NAME:
                raise HTTPException(status_code=400, detail="Document is not a React V2 quotation.")

            current_document = await document_repository.get_current_document(quotation_id, effective_lang)
            sanitized_document = _sanitize_canonical_asset_state(
                document,
                current_document.document_json if current_document is not None else None,
            )
            # V2 resolves mutable brand identity through brands.id, never document JSON.
            sanitized_document["brand"] = {}
            sanitized_document = _hydrate_r2_asset_urls(sanitized_document)
            document = _hydrate_canonical_quote_document(
                sanitized_document,
                quotation,
                lang=effective_lang,
                revision=payload.baseRevision or int(((document.get("meta") or {}).get("revision")) or 1),
            )
            validated_document = _validate_quote_document_or_422(document)
            saved_document = await document_repository.save_current_document(
                quotation_id=quotation_id,
                lang=effective_lang,
                document_json=validated_document,
                expected_revision=payload.baseRevision,
            )
            canonical_document = _hydrate_canonical_quote_document(
                saved_document.document_json,
                quotation,
                lang=effective_lang,
                revision=saved_document.revision,
            )
            await document_repository.append_document_revision(
                quotation_id=quotation_id,
                lang=effective_lang,
                revision=saved_document.revision,
                document_json=canonical_document,
                change_source="autosave",
            )
            await session.commit()
    except DocumentRevisionConflictError as exc:
        quotation, _, effective_lang = await _load_canonical_quote_document_from_db(quotation_id, target_lang)
        current_document = None
        if quotation is not None and exc.current_document is not None:
            current_document = _hydrate_canonical_quote_document(
                exc.current_document,
                quotation,
                lang=effective_lang or target_lang or quotation.baseline_lang,
                revision=exc.current_revision or 0,
            )
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Document revision conflict.",
                "currentRevision": exc.current_revision,
                "currentDocument": current_document,
            },
        ) from exc

    return {
        "ok": True,
        "document": canonical_document,
        "documentVersion": ((canonical_document.get("meta") or {}).get("version")) or 1,
        "currentRevision": ((canonical_document.get("meta") or {}).get("revision")) or 1,
        "sectionRegistry": {key: value.model_dump(mode="json") for key, value in SECTION_REGISTRY.items()},
    }


class PresentationUpsertRequest(BaseModel):
    """Allowlisted presentation controls for a canonical React V2 document."""
    model_config = ConfigDict(extra="forbid")
    baseRevision: int
    themeId: Literal["brochure"] = "brochure"
    layoutVersion: Literal[1] = 1


class PresentationCopyOverridesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseRevision: int
    overrides: dict[str, str]


class PresentationOverridesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseRevision: int
    copyOverrides: dict[str, str] = Field(default_factory=dict)
    identityOverrides: dict[str, Any] = Field(default_factory=dict)


class PresentationMediaDefaultsRequest(BaseModel):
    baseRevision: int
    dryRun: bool = True


def _validate_v2_fact_media_slots(slots: Any) -> dict[str, Any]:
    if not isinstance(slots, list) or not slots:
        raise HTTPException(status_code=422, detail={"message": "facts media slots must be a non-empty list."})
    normalized: dict[str, Any] = {}
    for slot in slots:
        if not isinstance(slot, dict) or not isinstance(slot.get("fieldId"), str):
            raise HTTPException(status_code=422, detail={"message": "Each media slot needs a fieldId and value."})
        field_id, value = slot["fieldId"], slot.get("value")
        descriptor = media_slot_descriptor(field_id)
        if not is_fact_media_field(field_id) or descriptor is None:
            raise HTTPException(status_code=422, detail={"message": "Unknown or non-Fact media field.", "invalidKeys": [field_id]})
        if field_id in normalized:
            raise HTTPException(status_code=422, detail={"message": "A media slot can only be updated once.", "invalidKeys": [field_id]})
        if value is None:
            normalized[field_id] = None
            continue
        items = value if is_gallery_field(field_id) else [value]
        max_items = int(descriptor["maxItems"])
        if not isinstance(items, list) or (not items and not is_gallery_field(field_id)) or len(items) > max_items:
            raise HTTPException(status_code=422, detail={"message": "Invalid media selection cardinality.", "invalidKeys": [field_id]})
        result: list[dict[str, str]] = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("r2Key"), str) or not item["r2Key"] or not is_allowed_prefix(item["r2Key"]):
                raise HTTPException(status_code=422, detail={"message": "Media asset is outside approved media prefixes.", "invalidKeys": [field_id]})
            alt = item.get("altText", "")
            if not isinstance(alt, str) or len(alt) > 500:
                raise HTTPException(status_code=422, detail={"message": "Media alt text is invalid.", "invalidKeys": [field_id]})
            result.append({"r2Key": item["r2Key"], "status": "ready", "altText": alt.strip(), "source": "manual"})
        if len({item["r2Key"] for item in result}) != len(result):
            raise HTTPException(status_code=422, detail={"message": "Duplicate gallery media is not allowed.", "invalidKeys": [field_id]})
        normalized[field_id] = result if is_gallery_field(field_id) else result[0]
    return normalized


# Transitional test/helper alias; production callers use the slots payload.
def _validate_v2_fact_media_fields(fields: Any) -> dict[str, Any]:
    if not isinstance(fields, dict):
        raise HTTPException(status_code=422, detail={"message": "facts media fields must be an object."})
    return _validate_v2_fact_media_slots([{"fieldId": field_id, "value": value} for field_id, value in fields.items()])


def _set_fact_media_field(document: dict[str, Any], field_id: str, value: Any) -> None:
    if field_id == "brand.logo":
        document.setdefault("brand", {})["logo"] = value or {"status": "empty"}
    elif field_id in {"assets.hero", "assets.itineraryDivider", "assets.staysDivider", "assets.hotelDivider"}:
        document.setdefault("assets", {})[field_id.rsplit(".", 1)[-1]] = value or {"status": "empty"}
    elif field_id.startswith("itinerary.days."):
        index = int(field_id.split(".")[2]); days = document.setdefault("itinerary", {}).setdefault("days", [])
        if index >= len(days): raise HTTPException(status_code=422, detail={"message": "Itinerary image no longer matches a day.", "invalidKeys": [field_id]})
        days[index].setdefault("images", {})["carousel"] = value or []
    elif field_id.startswith("stays.hotels."):
        parts = field_id.split("."); index, key = int(parts[2]), parts[3]; hotels = document.setdefault("stays", {}).setdefault("hotels", [])
        if index >= len(hotels): raise HTTPException(status_code=422, detail={"message": "Stay image no longer matches a hotel.", "invalidKeys": [field_id]})
        hotels[index][key] = value or {"status": "empty"}
        if key == "hotelImage":
            hotel_source_fact_id = str(
                hotels[index].get("sourceFactId") or hotels[index].get("id") or ""
            ).strip()
            if not hotel_source_fact_id:
                return
            for seg in (document.get("route") or {}).get("staySegments") or []:
                if str(seg.get("hotelSourceFactId") or "").strip() == hotel_source_fact_id:
                    seg["hotelImage"] = value or {"status": "empty"}
    elif field_id == "designer.image":
        document.setdefault("designer", {})["image"] = value or {"status": "empty"}
    elif field_id.startswith("assets.themeOrnaments."):
        document.setdefault("assets", {}).setdefault("themeOrnaments", {})[field_id.rsplit(".", 1)[-1]] = value or {"status": "empty"}


def _get_fact_media_field(document: dict[str, Any], field_id: str) -> Any:
    if field_id == "brand.logo": return (document.get("brand") or {}).get("logo")
    if field_id.startswith("assets.themeOrnaments."): return ((document.get("assets") or {}).get("themeOrnaments") or {}).get(field_id.rsplit(".", 1)[-1])
    if field_id.startswith("assets."): return (document.get("assets") or {}).get(field_id.rsplit(".", 1)[-1])
    if field_id == "designer.image": return (document.get("designer") or {}).get("image")
    parts = field_id.split(".")
    if field_id.startswith("itinerary.days.") and len(parts) >= 4:
        days = ((document.get("itinerary") or {}).get("days") or []); index = int(parts[2])
        return ((days[index].get("images") or {}).get("carousel")) if index < len(days) else None
    if field_id.startswith("stays.hotels.") and len(parts) >= 4:
        hotels = ((document.get("stays") or {}).get("hotels") or []); index = int(parts[2])
        return hotels[index].get(parts[3]) if index < len(hotels) else None
    return None


def _copy_fact_media_slots(source: dict[str, Any], target: dict[str, Any]) -> None:
    # Stable document IDs, rather than mutable array indexes, own media during
    # a Facts rebase. This avoids moving Day/Hotel images onto the next item
    # when an editor removes or reorders a repeatable fact card.
    for field_id in expand_media_slot_field_ids(source):
        value = _get_fact_media_field(source, field_id)
        if not ((isinstance(value, dict) and value.get("r2Key")) or (isinstance(value, list) and value)):
            continue
        target_field_id = field_id
        parts = field_id.split(".")
        if field_id.startswith("itinerary.days."):
            source_days = ((source.get("itinerary") or {}).get("days") or [])
            target_days = ((target.get("itinerary") or {}).get("days") or [])
            source_day = source_days[int(parts[2])] if int(parts[2]) < len(source_days) else {}
            target_index = next((index for index, day in enumerate(target_days) if day.get("id") == source_day.get("id")), None)
            if target_index is None:
                continue
            target_field_id = field_id.replace(f".{parts[2]}.", f".{target_index}.", 1)
        elif field_id.startswith("stays.hotels."):
            source_hotels = ((source.get("stays") or {}).get("hotels") or [])
            target_hotels = ((target.get("stays") or {}).get("hotels") or [])
            source_hotel = source_hotels[int(parts[2])] if int(parts[2]) < len(source_hotels) else {}
            target_index = next((index for index, hotel in enumerate(target_hotels) if hotel.get("id") == source_hotel.get("id")), None)
            if target_index is None:
                continue
            target_field_id = field_id.replace(f".{parts[2]}.", f".{target_index}.", 1)
        _set_fact_media_field(target, target_field_id, copy.deepcopy(value))


def _missing_required_fact_media(document: dict[str, Any]) -> list[str]:
    """Evaluate publish readiness from the registry, never JSX or a second policy."""
    missing: list[str] = []
    for field_id in expand_media_slot_field_ids(document):
        descriptor = media_slot_descriptor(field_id)
        if not descriptor or not descriptor.get("requiredForPublish"):
            continue
        value = _get_fact_media_field(document, field_id)
        values = value if isinstance(value, list) else [value] if isinstance(value, dict) and value.get("r2Key") else []
        usable_values = [item for item in values if isinstance(item, dict) and isinstance(item.get("r2Key"), str) and item["r2Key"].strip()]
        if len(usable_values) < int(descriptor["minItems"]) or len(usable_values) > int(descriptor["maxItems"]):
            missing.append(field_id)
    return missing


def _pdf_layout_preflight(document: dict[str, Any]) -> list[str]:
    """Reject content that cannot fit the fixed A4 compositor without shrinking.

    The limits are deliberately based on the compositor's fixed printable
    regions, not viewport breakpoints.  Keeping this server-side makes a PDF
    release fail before Chromium can silently clip a page.
    """
    from core.rules.content_budgets import get_content_budget_registry

    ceilings = get_content_budget_registry("v1").get_pdf_ceilings_map()
    errors: list[str] = []
    itinerary = (document.get("itinerary") or {}).get("days") or []
    for index, day in enumerate(itinerary):
        if not isinstance(day, dict):
            errors.append(f"/itinerary/days/{index}")
            continue
        title = str(day.get("title") or "").strip()
        description = day.get("description") or []
        description_text = " ".join(str(item) for item in description if isinstance(item, str)) if isinstance(description, list) else str(description)
        if len(title) > ceilings.get("day_title", 170):
            errors.append(f"/itinerary/days/{index}/title")
        if len(description_text) > ceilings.get("day_description", 1150):
            errors.append(f"/itinerary/days/{index}/description")
    hotels = (document.get("stays") or {}).get("hotels") or []
    for index, hotel in enumerate(hotels):
        if not isinstance(hotel, dict):
            errors.append(f"/stays/hotels/{index}")
            continue
        copy_length = sum(len(str(hotel.get(key) or "")) for key in ("name", "city", "hotelDate", "tel", "roomType"))
        copy_length += len(str(hotel.get("editorialIntroduction") or hotel.get("introduction") or ""))
        if copy_length > ceilings.get("hotel_total_copy", 2100):
            errors.append(f"/stays/hotels/{index}")

    narrative = document.get("narrative") or {}
    if isinstance(narrative, dict):
        highlight = str(narrative.get("letterHighlight") or "")
        if len(highlight) > ceilings.get("overview_highlight", 500):
            errors.append("/narrative/letterHighlight")
        letter_keys = ("journeyOverviewTitle", "letterGreeting", "letterIntro", "letterBody2", "letterOutro", "letterSignOff", "letterSender", "letterHighlight")
        total_letter_length = sum(len(str(narrative.get(k) or "")) for k in letter_keys)
        if total_letter_length > ceilings.get("overview_letter_total", 4000):
            errors.append("/narrative")

    route = document.get("route") or {}
    if isinstance(route, dict):
        map_segment_descs = route.get("mapSegmentDescriptions") or []
        if isinstance(map_segment_descs, list):
            for index, desc in enumerate(map_segment_descs):
                if len(str(desc or "")) > ceilings.get("route_stop_description", 500):
                    errors.append(f"/route/mapSegmentDescriptions/{index}")
        stay_segments = route.get("staySegments") or []
        if isinstance(stay_segments, list):
            for index, seg in enumerate(stay_segments):
                if isinstance(seg, dict) and len(str(seg.get("mapSegmentDesc") or "")) > ceilings.get("route_stop_description", 500):
                    errors.append(f"/route/staySegments/{index}/mapSegmentDesc")

    booking_terms = (document.get("booking") or {}).get("items") or (document.get("booking") or {}).get("terms") or (document.get("booking_facts") or {}).get("items") or document.get("booking_terms") or []
    if isinstance(booking_terms, list) and len(booking_terms) > ceilings.get("payment_terms_max_count", 4):
        errors.append("/booking/items")
    if isinstance(booking_terms, list):
        for index, term in enumerate(booking_terms):
            if isinstance(term, dict) and len(str(term.get("body") or term.get("bodyRichText") or "")) > ceilings.get("payment_term_body", 1600):
                errors.append(f"/booking/items/{index}/body")

    return errors


async def _require_active_media_overrides(session, overrides: dict[str, Any]) -> None:
    keys: set[str] = set()
    for value in overrides.values():
        if isinstance(value, list):
            keys.update(str(item.get("r2Key") or "") for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            keys.add(str(value.get("r2Key") or ""))
    keys.discard("")
    active = await MediaLibraryRepository(session).get_active_media_keys(keys)
    missing = sorted(keys - active)
    if missing:
        raise HTTPException(status_code=422, detail={"message": "Selected media is no longer active in the R2 catalogue.", "invalidKeys": missing})


def _apply_media_default_patch(document: dict[str, Any], patch: dict[str, Any]) -> None:
    MediaDefaultService.apply_patch(document, patch)


async def _apply_missing_media_defaults(
    session,
    document: dict[str, Any],
    quotation_id: str,
    lang: str,
) -> dict[str, Any]:
    return await MediaDefaultService(session).apply_missing(
        document=document,
        quotation_id=quotation_id,
        lang=lang,
    )


@app.put("/api/v2/quotations/{quotation_id}/presentation")
async def put_quotation_presentation_v2(
    quotation_id: str,
    payload: PresentationUpsertRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
    _owned=Depends(require_owned_quotation),
):
    """Persist presentation choices under the same revision lock as the document."""
    async with _get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        if quotation is None:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        if quotation.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=400, detail="Presentation controls are only available for React V2 quotations.")
        effective_lang = lang or quotation.baseline_lang
        current = await documents.get_current_document(quotation_id, effective_lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Canonical document was not found.")
        next_document = copy.deepcopy(current.document_json)
        current_presentation = next_document.get("presentation") or {}
        next_document["presentation"] = {
            "renderer": V2_RENDERER_NAME,
            "themeId": payload.themeId,
            "layoutVersion": payload.layoutVersion,
            "copyOverrides": current_presentation.get("copyOverrides") or {},
            "mediaOverrides": current_presentation.get("mediaOverrides") or {},
            "mediaDefaults": current_presentation.get("mediaDefaults") or {},
            "identityOverrides": current_presentation.get("identityOverrides") or {},
        }
        try:
            validated = _validate_quote_document_or_422(_hydrate_canonical_quote_document(next_document, quotation, lang=effective_lang, revision=payload.baseRevision))
            saved = await documents.save_current_document(quotation_id=quotation_id, lang=effective_lang, document_json=validated, expected_revision=payload.baseRevision)
        except DocumentRevisionConflictError as exc:
            raise HTTPException(status_code=409, detail={"message": "Presentation revision conflict.", "currentRevision": exc.current_revision}) from exc
        canonical = _hydrate_canonical_quote_document(saved.document_json, quotation, lang=effective_lang, revision=saved.revision)
        await documents.append_document_revision(quotation_id=quotation_id, lang=effective_lang, revision=saved.revision, document_json=canonical, change_source="update_presentation")
        await session.commit()
    return {"ok": True, "document": canonical, "currentRevision": saved.revision}


@app.put("/api/v2/quotations/{quotation_id}/presentation/copy-overrides")
async def put_quotation_presentation_copy_overrides_v2(
    quotation_id: str,
    payload: PresentationCopyOverridesRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
    _owned=Depends(require_owned_quotation),
):
    """Patch only allowlisted display copy under the normal document revision lock."""
    overrides = _validate_v2_copy_overrides(payload.overrides)
    async with _get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        if quotation is None or quotation.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        effective_lang = lang or quotation.baseline_lang
        current = await documents.get_current_document(quotation_id, effective_lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Canonical document was not found.")
        next_document = copy.deepcopy(current.document_json)
        presentation = next_document.setdefault("presentation", {})
        current_overrides = presentation.get("copyOverrides") or {}
        if not isinstance(current_overrides, dict):
            current_overrides = {}
        # Validate the complete persisted object too: a legacy malformed key
        # must not survive merely because this request patches a different key.
        presentation["copyOverrides"] = _validate_v2_copy_overrides({**current_overrides, **overrides})
        try:
            validated = _validate_quote_document_or_422(
                _hydrate_canonical_quote_document(next_document, quotation, lang=effective_lang, revision=payload.baseRevision)
            )
            saved = await documents.save_current_document(
                quotation_id=quotation_id,
                lang=effective_lang,
                document_json=validated,
                expected_revision=payload.baseRevision,
            )
        except DocumentRevisionConflictError as exc:
            raise HTTPException(status_code=409, detail={"message": "Presentation copy revision conflict.", "currentRevision": exc.current_revision}) from exc
        canonical = _hydrate_canonical_quote_document(saved.document_json, quotation, lang=effective_lang, revision=saved.revision)
        await documents.append_document_revision(
            quotation_id=quotation_id,
            lang=effective_lang,
            revision=saved.revision,
            document_json=canonical,
            change_source="update_presentation_copy",
        )
        await session.commit()
    return {"ok": True, "document": canonical, "currentRevision": saved.revision}


@app.put("/api/v2/quotations/{quotation_id}/presentation/overrides")
async def put_quotation_presentation_overrides_v2(
    quotation_id: str,
    payload: PresentationOverridesRequest,
    lang: str | None = None,
    principal: Principal = Depends(require_editor),
    _owned=Depends(require_owned_quotation),
):
    """Atomically persist Design-owned copy, identity and media overrides."""
    copy_overrides = _validate_v2_copy_overrides(payload.copyOverrides)
    identity = _validate_v2_identity_overrides(payload.identityOverrides)

    async with _get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        if quotation is None or quotation.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        effective_lang = lang or quotation.baseline_lang
        current = await documents.get_current_document(quotation_id, effective_lang)
        if current is None:
            raise HTTPException(status_code=404, detail="Canonical document was not found.")
        next_document = copy.deepcopy(current.document_json)
        presentation = next_document.setdefault("presentation", {})
        current_copy = presentation.get("copyOverrides") or {}
        current_identity = presentation.get("identityOverrides") or {}
        presentation["copyOverrides"] = _validate_v2_copy_overrides({**current_copy, **copy_overrides})
        # Preserve frozen legacy media for display compatibility, but never
        # mutate it through a presentation request.
        presentation["mediaOverrides"] = presentation.get("mediaOverrides") or {}
        presentation["identityOverrides"] = {**current_identity, **identity}
        try:
            validated = _validate_quote_document_or_422(
                _hydrate_canonical_quote_document(next_document, quotation, lang=effective_lang, revision=payload.baseRevision)
            )
            saved = await documents.save_current_document(
                quotation_id=quotation_id,
                lang=effective_lang,
                document_json=validated,
                expected_revision=payload.baseRevision,
            )
        except DocumentRevisionConflictError as exc:
            raise HTTPException(status_code=409, detail={"message": "Presentation override revision conflict.", "currentRevision": exc.current_revision}) from exc
        canonical = _hydrate_canonical_quote_document(saved.document_json, quotation, lang=effective_lang, revision=saved.revision)
        await documents.append_document_revision(
            quotation_id=quotation_id,
            lang=effective_lang,
            revision=saved.revision,
            document_json=canonical,
            change_source="update_presentation_overrides",
        )
        await session.commit()
    return {"ok": True, "document": canonical, "currentRevision": saved.revision}


def _serialize_media_sync_run(run) -> dict[str, Any]:
    return {
        "id": run.id,
        "status": run.status,
        "roots": run.prefixes,
        "scannedCount": run.scanned_count,
        "indexedCount": run.indexed_count,
        "previewCount": run.preview_count,
        "errorCount": run.error_count,
        "errorMessage": run.error_message,
    }


async def _apply_create_fact_media_slots(document: dict[str, Any], slots) -> dict[str, Any]:
    if not slots:
        return document
    normalized = _validate_v2_fact_media_slots([
        {"fieldId": slot.fieldId, "value": slot.value}
        for slot in slots
    ])
    keys: set[str] = set()
    for value in normalized.values():
        values = value if isinstance(value, list) else [value]
        keys.update(str(item.get("r2Key") or "") for item in values if isinstance(item, dict))
    keys.discard("")
    async with _get_db_session_factory()() as session:
        valid_keys = await MediaLibraryRepository(session).get_active_media_keys(keys)
    missing = sorted(keys - valid_keys)
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Selected media is no longer available in the media library.",
                "missingInputs": [f"factMediaSlots.{key}" for key in missing],
            },
        )
    for field_id, value in normalized.items():
        _set_fact_media_field(document, field_id, value)
    return document


@app.post("/api/v2/media-library/sync", status_code=202)
async def sync_media_library(background_tasks: BackgroundTasks, principal: Principal = Depends(require_editor)):
    service = _get_media_library_service()
    async with _get_db_session_factory()() as session:
        repository = MediaLibraryRepository(session)
        active_run = await repository.get_active_sync_run()
    if active_run is not None:
        return {**_serialize_media_sync_run(active_run), "reused": True}
    try:
        run_id = await service.create_run()
    except IntegrityError:
        async with _get_db_session_factory()() as session:
            active_run = await MediaLibraryRepository(session).get_active_sync_run()
        if active_run is None:
            raise
        return {**_serialize_media_sync_run(active_run), "reused": True}
    background_tasks.add_task(service.process_run, run_id)
    async with _get_db_session_factory()() as session:
        run = await MediaLibraryRepository(session).get_sync_run(run_id)
    return {**_serialize_media_sync_run(run), "reused": False}


@app.get("/api/v2/media-library/sync/{run_id}")
async def get_media_library_sync(run_id: str, principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        run = await MediaLibraryRepository(session).get_sync_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Media library sync run not found.")
        return _serialize_media_sync_run(run)


@app.post("/api/v2/media-library/resolve-location")
async def resolve_media_library_location(payload: MediaLibraryLocationRequest, principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        location = await _resolve_media_location(session, payload)
        await session.commit()
    return {"kind": location.kind, "leafPrefix": location.leaf_prefix, "breadcrumbs": location.leaf_prefix.split("/"), "uploadAllowed": True}


@app.post("/api/v2/media-library/uploads")
async def upload_media_library_asset(
    file: UploadFile = File(...), kind: Literal["destination", "accommodation", "team"] = Form(...), destinationId: str | None = Form(None), destinationName: str | None = Form(None), accommodationName: str | None = Form(None), accommodationKind: Literal["hotel", "cruise"] | None = Form(None), accommodationId: str | None = Form(None), accommodationAssetCategory: Literal["exteriors", "interiors"] | None = Form(None), travelDesignerId: str | None = Form(None), principal: Principal = Depends(require_editor),
):
    payload = MediaLibraryLocationRequest(kind=kind, destinationId=destinationId, destinationName=destinationName, accommodationName=accommodationName, accommodationKind=accommodationKind, accommodationId=accommodationId, accommodationAssetCategory=accommodationAssetCategory, travelDesignerId=travelDesignerId)
    media_service = _get_media_service()
    prepared = await media_service.prepare_upload(content=await file.read(), declared_mime_type=file.content_type)
    async with _get_db_session_factory()() as session:
        location = await _resolve_media_location(session, payload)
        await session.commit()
    item = await _get_media_library_service().create_library_asset(location=location, prepared=prepared)
    storage = _get_media_library_service().storage
    return {"r2Key": item.r2_key, "previewUrl": storage.build_public_url(item.preview_r2_key), "width": item.width, "height": item.height, "location": location.leaf_prefix}


@app.get("/api/v2/media-library/children")
async def get_media_library_children(prefix: str = "", cursor: int = 0, limit: int = 60, search: str = "", principal: Principal = Depends(require_editor)):
    requested = normalize_library_prefix(prefix)
    allowed = settings.media_library_roots
    if not requested:
        return {"prefix": "", "folders": [{"prefix": item, "name": item.split("/")[-1]} for item in allowed], "items": [], "nextCursor": None}
    if not is_allowed_prefix(requested, allowed):
        raise HTTPException(status_code=422, detail="Media library prefix is not allowed.")
    async with _get_db_session_factory()() as session:
        repository = MediaLibraryRepository(session)
        items = await repository.list_children(prefix=requested, cursor=max(cursor, 0), limit=min(max(limit, 1), 100), search=search.strip())
        folders = await repository.list_child_prefixes(prefix=requested)
    storage = _get_media_library_service().storage
    folder_prefixes = tuple(
        dict.fromkeys(
            item for item in folders if item.rsplit("/", 1)[-1] != "preview"
        )
    )
    return {"prefix": requested, "folders": [{"prefix": item, "name": item.rsplit("/", 1)[-1]} for item in folder_prefixes], "items": [{"r2Key": item.r2_key, "fileName": item.file_name, "previewStatus": item.preview_status, "previewUrl": storage.build_public_url(item.preview_r2_key) if item.preview_r2_key else None, "width": item.width, "height": item.height, "classification": _media_classification(item), "mediaKind": item.media_kind} for item in items[:limit]], "nextCursor": cursor + limit if len(items) > limit else None}


@app.get("/api/v2/media-library/search")
async def search_media_library(prefix: str, query: str, cursor: int = 0, limit: int = 60, principal: Principal = Depends(require_editor)):
    requested = normalize_library_prefix(prefix)
    allowed = settings.media_library_roots
    if not is_allowed_prefix(requested, allowed):
        raise HTTPException(status_code=422, detail="Media library prefix is not allowed.")
    async with _get_db_session_factory()() as session:
        items = await MediaLibraryRepository(session).search(prefix=requested, query=query.strip(), cursor=max(cursor, 0), limit=min(max(limit, 1), 100))
    storage = _get_media_library_service().storage
    return {"items": [{"r2Key": item.r2_key, "fileName": item.file_name, "previewUrl": storage.build_public_url(item.preview_r2_key) if item.preview_r2_key else None, "width": item.width, "height": item.height, "classification": _media_classification(item), "mediaKind": item.media_kind} for item in items[:limit]], "nextCursor": cursor + limit if len(items) > limit else None}


async def _serialize_destination(repository: DestinationRepository, item, *, matched_from: str | None = None) -> dict[str, Any]:
    geo_parts = [item.country_slug, item.region_slug, item.province_slug, item.slug]
    default_media_prefix = "/".join(p for p in geo_parts if p) or item.slug
    payload = {
        "id": item.id,
        "name": item.canonical_name,
        "slug": item.slug,
        "countrySlug": item.country_slug,
        "regionSlug": item.region_slug,
        "provinceSlug": item.province_slug,
        "latitude": float(item.latitude) if item.latitude is not None else None,
        "longitude": float(item.longitude) if item.longitude is not None else None,
        "isActive": item.is_active,
        "mediaPrefix": item.media_prefix,
        "defaultMediaPrefix": default_media_prefix,
        "aliases": await repository.aliases_for(item.id),
    }
    if matched_from is not None:
        payload["matchedFrom"] = matched_from
    return payload


async def _save_destination(session, payload: DestinationCatalogRequest, item=None):
    repository = DestinationRepository(session)
    alias_conflict = await repository.conflicting_alias(
        [payload.canonicalName, payload.slug, *payload.aliases],
        destination_id=item.id if item is not None else None,
    )
    if alias_conflict is not None:
        raise HTTPException(status_code=409, detail={"message": "Destination slug or alias already exists.", "alias": alias_conflict})
    if item is None:
        return await repository.create(
            destination_id=f"dst_{uuid.uuid4().hex[:12]}",
            canonical_name=payload.canonicalName,
            slug=payload.slug,
            aliases=payload.aliases,
            country_slug=payload.countrySlug,
            region_slug=payload.regionSlug,
            province_slug=payload.provinceSlug,
            latitude=payload.latitude,
            longitude=payload.longitude,
            media_prefix=payload.mediaPrefix,
        )
    if payload.slug != item.slug:
        raise HTTPException(status_code=422, detail={"message": "Destination slug is immutable.", "missingInputs": ["slug"]})
    return await repository.update(
        item,
        canonical_name=payload.canonicalName,
        aliases=payload.aliases,
        country_slug=payload.countrySlug,
        region_slug=payload.regionSlug,
        province_slug=payload.provinceSlug,
        latitude=payload.latitude,
        longitude=payload.longitude,
        media_prefix=payload.mediaPrefix,
    )


from routers.v2.destinations import (
    create_destination,
    get_destination,
    search_destinations,
    update_destination,
    update_destination_status,
)


def _serialize_travel_designer(profile) -> dict[str, Any]:
    image_url = profile.image_url
    if profile.image_r2_key:
        try:
            image_url = _get_media_library_service().storage.build_public_url(profile.image_r2_key)
        except HTTPException:
            pass
    return {"id": profile.id, "name": profile.name, "email": profile.email, "phone": profile.phone, "imageAssetId": profile.image_asset_id, "imageUrl": image_url, "imageR2Key": profile.image_r2_key, "signatureInitial": profile.signature_initial, "isActive": profile.is_active}


async def _serialize_accommodation(profile, session) -> dict[str, Any]:
    destination = await session.get(__import__("db.models.destination", fromlist=["DestinationCatalog"]).DestinationCatalog, profile.destination_id)
    return {
        "id": profile.id,
        "destination_id": profile.destination_id,
        "destination": destination.canonical_name if destination else "",
        "destination_ref": {"id": destination.id, "name": destination.canonical_name, "slug": destination.slug} if destination else None,
        "storage_slug": profile.storage_slug,
        "asset_prefix": profile.asset_prefix,
        "name": profile.name,
        "room_type": profile.room_type,
        "intro": profile.intro,
        "phone": profile.phone,
        "display_city": profile.display_city,
        "display_date": profile.display_date,
        "hotel_asset": profile.hotel_asset,
        "room_asset": profile.room_asset,
        "is_active": profile.is_active,
    }


async def _validate_accommodation_assets(session, *, asset_prefix: str, hotel_asset: str | None, room_asset: str | None, legacy_keys: set[str] | None = None) -> None:
    normalized_prefix = asset_prefix.strip().strip("/")
    slot_prefixes = {
        "hotel_asset": f"{normalized_prefix}/exteriors/",
        "room_asset": f"{normalized_prefix}/interiors/",
    }
    supplied = {"hotel_asset": hotel_asset, "room_asset": room_asset}
    permitted_legacy_keys = legacy_keys or set()
    invalid = [
        field for field, key in supplied.items()
        if key and not key.startswith(slot_prefixes[field]) and key not in permitted_legacy_keys
    ]
    if invalid:
        raise HTTPException(status_code=422, detail={"message": "Hotel images must be in /exteriors and room images in /interiors for this accommodation.", "missingInputs": invalid})
    keys = {key for key in supplied.values() if key}
    active_keys = await MediaLibraryRepository(session).get_active_media_keys(keys)
    if keys - active_keys:
        raise HTTPException(status_code=422, detail={"message": "Accommodation asset is not active in the R2 catalogue.", "missingInputs": ["hotel_asset", "room_asset"]})


async def _save_accommodation_profile(session, payload: AccommodationProfileRequest, profile=None):
    await _seed_destination_catalog(session)
    destination = await session.get(__import__("db.models.destination", fromlist=["DestinationCatalog"]).DestinationCatalog, payload.destinationId)
    if destination is None or not destination.is_active:
        raise HTTPException(status_code=422, detail={"missingInputs": ["destinationId"]})
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail={"missingInputs": ["name"]})
    if profile is None:
        location = accommodation_location(destination, name, "hotel")
        storage_slug_value, asset_prefix = location.accommodation_slug, location.leaf_prefix
    else:
        # A stored R2 root is an immutable storage identity, not a derivative of
        # mutable catalogue fields. This allows correcting names/destinations.
        storage_slug_value, asset_prefix = profile.storage_slug, profile.asset_prefix
    await _validate_accommodation_assets(
        session,
        asset_prefix=asset_prefix,
        hotel_asset=payload.hotel_asset,
        room_asset=payload.room_asset,
        legacy_keys={key for key in (profile.hotel_asset, profile.room_asset) if key} if profile is not None else None,
    )
    values = {"destination_id": destination.id, "storage_slug": storage_slug_value, "asset_prefix": asset_prefix, "name": name, "room_type": payload.room_type, "intro": payload.intro, "phone": payload.phone, "display_city": payload.display_city or destination.canonical_name, "display_date": payload.display_date, "hotel_asset": payload.hotel_asset, "room_asset": payload.room_asset}
    repository = AccommodationRepository(session)
    saved = await repository.update_profile(profile, **values) if profile is not None else await repository.create_profile(id=f"acc_{uuid.uuid4().hex[:12]}", **values)
    return await _serialize_accommodation(saved, session)


@app.get("/api/v2/accommodations")
async def list_accommodations(active: Literal["true", "false", "all"] = "true", query: str = "", destinationId: str | None = None, destination: str | None = None, principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        await _seed_destination_catalog(session)
        dest_repo = DestinationRepository(session)
        resolved_dest_id = destinationId
        if destinationId:
            direct = await dest_repo.get(destinationId)
            if direct is None:
                clean_target = destinationId.removeprefix("dst_").replace("-", " ")
                resolved = await dest_repo.resolve(clean_target)
                if resolved is not None:
                    resolved_dest_id = resolved.id
        elif destination:
            resolved = await dest_repo.resolve(destination)
            if resolved is not None:
                resolved_dest_id = resolved.id
        items = await AccommodationRepository(session).list_profiles(active_only={"true": True, "false": False, "all": None}[active], search=query, destination_id=resolved_dest_id)
        return {"items": [await _serialize_accommodation(item, session) for item in items]}


@app.get("/api/v2/accommodations/{profile_id}")
async def get_accommodation(profile_id: str, principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        profile = await AccommodationRepository(session).get_profile(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Accommodation profile was not found.")
        return await _serialize_accommodation(profile, session)


@app.post("/api/v2/accommodations", status_code=201)
async def create_accommodation(payload: AccommodationProfileRequest, principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        saved = await _save_accommodation_profile(session, payload)
        await session.commit()
        return saved


@app.put("/api/v2/accommodations/{profile_id}")
async def update_accommodation(profile_id: str, payload: AccommodationProfileRequest, principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        profile = await AccommodationRepository(session).get_profile(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Accommodation profile was not found.")
        saved = await _save_accommodation_profile(session, payload, profile)
        await session.commit()
        return saved


@app.patch("/api/v2/accommodations/{profile_id}/status")
async def update_accommodation_status(profile_id: str, payload: AccommodationStatusRequest, principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        profile = await AccommodationRepository(session).get_profile(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Accommodation profile was not found.")
        saved = await AccommodationRepository(session).set_status(profile, is_active=payload.isActive)
        await session.commit()
        return await _serialize_accommodation(saved, session)


@app.get("/api/v2/travel-designers")
async def list_travel_designers(request: Request, active: Literal["true", "false", "all"] = "true", search: str = "", principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        items = await TravelDesignerRepository(session).list_profiles(active_only={"true": True, "false": False, "all": None}[active], search=search)
        return {"items": [_serialize_travel_designer(item) for item in items]}


@app.post("/api/v2/travel-designers", status_code=201)
async def create_travel_designer(payload: TravelDesignerProfileRequest, principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        repository = TravelDesignerRepository(session)
        if await repository.get_by_email(payload.email):
            raise HTTPException(status_code=409, detail="A Travel Designer already uses this email.")
        profile = await repository.create_profile(profile_id=f"td_{uuid.uuid4().hex[:12]}", email=payload.email, name=payload.name, phone=payload.phone, storage_slug=storage_slug(payload.email.split("@", 1)[0]), image_r2_key=payload.imageR2Key)
        await session.commit()
        await session.refresh(profile)
        return _serialize_travel_designer(profile)


@app.put("/api/v2/travel-designers/{profile_id}")
async def update_travel_designer(profile_id: str, payload: TravelDesignerProfileRequest, principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        repository = TravelDesignerRepository(session)
        profile = await repository.get_profile(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Travel Designer profile was not found.")
        profile = await repository.update_profile(profile, email=payload.email, name=payload.name, phone=payload.phone, storage_slug=storage_slug(payload.email.split("@", 1)[0]), image_r2_key=payload.imageR2Key)
        await session.commit()
        await session.refresh(profile)
        return _serialize_travel_designer(profile)


@app.patch("/api/v2/travel-designers/{profile_id}/status")
async def set_travel_designer_status(
    profile_id: str,
    payload: dict[str, bool],
    principal: Principal = Depends(require_editor),
):
    if "isActive" not in payload:
        raise HTTPException(status_code=422, detail="isActive is required")
    async with _get_db_session_factory()() as session:
        repository = TravelDesignerRepository(session)
        profile = await repository.get_profile(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Travel Designer profile was not found.")
        profile = await repository.set_status(profile, is_active=bool(payload["isActive"]))
        await session.commit()
        await session.refresh(profile)
        return _serialize_travel_designer(profile)


@app.put("/api/v2/brands/{brand_id}/travel-designer-default")
async def set_travel_designer_brand_default(
    brand_id: str,
    payload: TravelDesignerBrandDefaultRequest,
    principal: Principal = Depends(require_editor),
):
    """Persist the optional designer fallback without copying it into quotes."""
    async with _get_db_session_factory()() as session:
        designers = TravelDesignerRepository(session)
        try:
            default = await designers.set_brand_default(
                brand_id=brand_id,
                profile_id=payload.designerProfileId,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        await session.commit()
        return {"brandId": default.brand_id, "designerProfileId": default.designer_profile_id}


@app.post("/api/v1/assets")
async def upload_brochure_asset(
    quotation_id: str = Form(...),
    file: UploadFile = File(...),
):
    content = await file.read()
    payload = await _store_uploaded_draft_asset(
        quotation_id=quotation_id,
        file_name=file.filename or "upload",
        content=content,
        declared_mime_type=file.content_type,
    )
    return {
        "assetId": payload["assetId"],
        "url": payload["url"],
        "status": payload["status"],
    }



@app.get("/quotations/{quotation_id}", response_class=HTMLResponse)
async def get_quotation(quotation_id: str, request: Request):
    """
    Stable permalink for a quotation.
    Loads Single JSON context (ctx.json), extracts language-specific payload,
    builds the localized context, and renders dynamically.
    """
    lang = request.query_params.get("lang") or request.query_params.get("language")
    if lang not in ("en", "vi", "ar"):
        lang = None # fallback to baseline
    async with _get_db_session_factory()() as session:
        quotation = await QuotationRepository(session).get_quotation_by_id(quotation_id)
        if quotation is not None and quotation.template_name == V2_RENDERER_NAME:
            target = await PublicationTargetRepository(session).get_target(
                quotation_id=quotation_id,
                brand_id=quotation.brand_id,
                locale=lang or quotation.baseline_lang,
            )
            brand = await BrandRepository(session).get(quotation.brand_id)
            if target is not None and target.status == "published" and brand is not None:
                return RedirectResponse(
                    url=f"https://{brand.hostname}/{target.locale}/q/{target.public_slug}",
                    status_code=301,
                )
        
    ctx_data = _load_ctx_data(quotation_id)
    if not ctx_data:
        raise HTTPException(
            status_code=404,
            detail=f"Quotation '{quotation_id}' not found. It may still be deploying, please refresh in 30 seconds."
        )
        
    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = lang or baseline_lang
    
    # Trigger lazy translation if not available
    if target_lang != baseline_lang:
        available_langs = ctx_data.get("available_langs", [])
        if target_lang not in available_langs:
            success = await _translate_item_on_demand(quotation_id, target_lang, is_itinerary=False)
            if success:
                ctx_data = _load_ctx_data(quotation_id) or ctx_data
                
    # Extract appropriate payload dict
    if target_lang == baseline_lang:
        payload_dict = ctx_data.get("baseline_payload")
    else:
        payload_dict = ctx_data.get("translations", {}).get(target_lang)
        
    # Fallback to general context if payload extraction failed
    if not payload_dict:
        log.warning("[get_quotation] Localized payload for %s not found, using baseline", target_lang)
        payload_dict = ctx_data.get("baseline_payload")
        target_lang = baseline_lang
        
    try:
        tmpl_name = ctx_data.get("template_name", BROCHURE_TEMPLATE_NAME)
        if _is_brochure_template(tmpl_name):
            rendered_html, effective_lang = await _render_quotation_doc_from_ctx(
                ctx_data,
                quotation_id,
                target_lang,
                request=request,
                is_pdf=False,
                ignore_published_html=True,
                editor_mode=False,
            )
            return HTMLResponse(content=rendered_html, headers=no_cache_headers)
        payload_obj = TourQuotationPayload.model_validate(payload_dict)
        tmpl = templates.get_template(tmpl_name)

        # Resolve brand from request and payload
        brand_config = resolve_brand(request, payload_dict)
        
        # Build clean context for target lang
        default_brand_logo = _default_brand_logo(brand_config)
        hero_image_url = ctx_data.get("hero_img") or ctx_data.get("img_0") or default_brand_logo
        if _is_brand_placeholder_image(hero_image_url):
            for day in ctx_data.get("itinerary_days", []) or ctx_data.get("itinerary", []):
                day_hero = day.get("layout_images", {}).get("hero")
                if day_hero and not _is_brand_placeholder_image(day_hero):
                    hero_image_url = day_hero
                    break
            else:
                hero_image_url = default_brand_logo
        destinations = ctx_data.get("destinations", [])
        translations = ctx_data.get("translations", {})

        lang_ctx = _build_ctx(
            quotation_id=quotation_id,
            payload=payload_obj,
            hero_image_url=hero_image_url,
            destinations=destinations,
            lang=target_lang,
            template_name=tmpl_name,
            brand=brand_config,
        )
        brand_locked_fields = _capture_brand_owned_fields(lang_ctx)
        brand_switched = _is_brand_switched(ctx_data, brand_config)
        lang_ctx["brand"] = brand_config
        lang_ctx["translations"] = translations
        lang_ctx["baseline_lang"] = baseline_lang
        lang_ctx["translation_status"] = ctx_data.get("translation_status", {"baseline_lang": baseline_lang, "available_langs": [baseline_lang]})
        if ctx_data.get("designer_img"):
            lang_ctx["designer_img"] = ctx_data.get("designer_img")
        if ctx_data.get("hero_img"):
            lang_ctx["hero_img_custom"] = ctx_data.get("hero_img")
            lang_ctx["img_0"] = ctx_data.get("hero_img")
        if ctx_data.get("img_itinerary_divider"):
            lang_ctx["img_itinerary_divider"] = ctx_data.get("img_itinerary_divider")
        if ctx_data.get("img_hotel_divider"):
            lang_ctx["img_hotel_divider"] = ctx_data.get("img_hotel_divider")
        try:
            from github_publish import get_next_version
            next_ver = await get_next_version(quotation_id)
            lang_ctx["latest_version"] = max(1, next_ver - 1)
        except Exception:
            lang_ctx["latest_version"] = 1
        
        # Try to load language-specific published HTML (no fallback)
        latest_lang = None if target_lang == baseline_lang else target_lang
        html_content = await _get_latest_published_html(quotation_id, lang=latest_lang, fallback=False)
        if html_content:
            # Strip the old editor block entirely if it exists in the static HTML to avoid duplicate DOM elements and duplicate IDs (e.g. duplicate domain-modal)
            idx_bar = html_content.find('id="publish-bar"')
            if idx_bar == -1:
                idx_bar = html_content.find("id='publish-bar'")
            if idx_bar != -1:
                idx_start = html_content.rfind('<div', 0, idx_bar)
                if idx_start != -1:
                    idx_scripts = html_content.find('id="editor-scripts"')
                    if idx_scripts == -1:
                        idx_scripts = html_content.find("id='editor-scripts'")
                    if idx_scripts != -1:
                        idx_end_script = html_content.find('</script>', idx_scripts)
                        if idx_end_script != -1:
                            idx_end = idx_end_script + len('</script>')
                            html_content = html_content[:idx_start] + html_content[idx_end:]

            # Re-inject brand data dynamically into the static HTML to support brand switching
            import json
            brand_json = json.dumps(brand_config, ensure_ascii=False)
            import re
            html_content = re.sub(
                r'<script[^>]*id=["\']brand-data["\'][^>]*>.*?</script>',
                f'<script id="brand-data" type="application/json">{brand_json}</script>',
                html_content,
                flags=re.DOTALL
            )
            # Re-inject editor components
            editor_block = extract_editor_components(tmpl.render(**lang_ctx))
            if editor_block:
                # Strip old script blocks containing translateBlock to avoid variable redeclaration SyntaxErrors (let/const)
                import re
                html_content = re.sub(
                    r'<script[^>]*>(?:(?!<\/script>).)*translateBlock(?:(?!<\/script>).)*<\/script>',
                    '',
                    html_content,
                    flags=re.DOTALL
                )
                # Strip auto-version-checker from editor mode
                html_content = re.sub(
                    r'<script[^>]*id=["\']auto-version-checker["\'][^>]*>.*?</script>',
                    '',
                    html_content,
                    flags=re.DOTALL
                )
                idx_body = html_content.rfind('</body>')
                if idx_body != -1:
                    html_content = html_content[:idx_body] + editor_block + html_content[idx_body:]
                else:
                    html_content += editor_block
            return HTMLResponse(content=html_content, headers=no_cache_headers)
            
        # If language-specific published HTML is missing, check if baseline published HTML exists
        # so we can filter out deleted blocks and override baseline edits when rendering fallback JINJA2
        if target_lang != baseline_lang:
            baseline_html = await _get_latest_published_html(quotation_id, lang=None, fallback=False)
            if baseline_html:
                filter_and_override_ctx_by_html(lang_ctx, baseline_html, override_text=False)
                
        rendered_html = tmpl.render(**lang_ctx)
        return HTMLResponse(content=rendered_html, headers=no_cache_headers)
    except Exception as err:
        log.exception("[/quotations] Dynamic HTML render failed for %s: %s", quotation_id, err)
        raise HTTPException(status_code=500, detail=f"Render error: {err}")



# ── POST /quotations/{id}/publish — commit to GitHub → Vercel ─────────────────

class PublishRequest(BaseModel):
    html: Optional[str] = None
    draft: Optional[dict[str, Any]] = None
    template_name: Optional[str] = None

class ApproveRequest(BaseModel):
    html: Optional[str] = None
    token: str

@app.post("/quotations/{quotation_id}/publish")
async def publish_quotation(quotation_id: str, body: PublishRequest, request: Request, lang: str = None, language: str = None):
    """
    Commit the edited HTML (sent from browser) to GitHub published/ folder.
    Does NOT require the in-memory store — quotation_id + html come from the request.
    This makes the endpoint resilient across Vercel serverless instances.
    """
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    log.info("[publish] Received publish for quotation_id=%s, template_name=%s, target_lang=%s", quotation_id, body.template_name, target_lang)

    # Fetch the next version from GitHub directly to ensure it works across serverless instances
    from github_publish import get_next_version, publish_to_github
    version = await get_next_version(quotation_id)

    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    
    ctx_data = _load_ctx_data(quotation_id)
    baseline_lang = "en"
    rendered_pdf = None
    effective_lang = target_lang
    if ctx_data:
        baseline_lang = ctx_data.get("baseline_lang", "en")
        active_template = body.template_name or ctx_data.get("template_name") or BROCHURE_TEMPLATE_NAME
        if _is_brochure_template(active_template) and body.draft:
            draft = copy.deepcopy(body.draft)
            draft.setdefault("meta", {})
            draft["meta"]["quotationId"] = quotation_id
            draft["meta"]["lang"] = target_lang or baseline_lang
            draft["meta"]["template"] = active_template
            draft["meta"]["revision"] = int(draft["meta"].get("revision") or 0) + 1
            ctx_data["template_name"] = active_template
            _store_brochure_draft(ctx_data, target_lang or baseline_lang, _validate_quote_document_or_422(draft))

            rendered_html, effective_lang = await _render_quotation_doc_from_ctx(
                ctx_data,
                quotation_id,
                target_lang or baseline_lang,
                request=request,
                is_pdf=False,
                ignore_published_html=True,
            )
            rendered_pdf, effective_lang = await _render_quotation_doc_from_ctx(
                ctx_data,
                quotation_id,
                target_lang or baseline_lang,
                request=request,
                is_pdf=True,
                ignore_published_html=True,
            )

            _sync_ctx_data_before_publish(ctx_data, rendered_html, target_lang or baseline_lang, version)

            lang_suffix = f"_{target_lang}" if target_lang and target_lang != baseline_lang else ""
            filename = f"v{version}{lang_suffix}.html"

            if ENVIRONMENT == "production":
                try:
                    published_url = await publish_to_github(
                        quotation_id=quotation_id,
                        html_content=rendered_html,
                        version=version,
                        lang=target_lang,
                        baseline_lang=baseline_lang
                    )
                    pdf_suffix = "" if effective_lang == baseline_lang else f"_{effective_lang}"
                    pdf_files = {f"published/{quotation_id}/pdf{pdf_suffix}.html"}
                    if effective_lang == baseline_lang:
                        pdf_files.add(f"published/{quotation_id}/pdf_{effective_lang}.html")
                    for pdf_path in sorted(pdf_files):
                        await publish_file_to_github(
                            file_path=pdf_path,
                            html_content=rendered_pdf,
                            commit_message=f"Update PDF view for quotation {quotation_id} {os.path.basename(pdf_path)} (version {version})",
                        )
                    await publish_file_to_github(
                        file_path=f"published/{quotation_id}/ctx.json",
                        html_content=json.dumps(ctx_data, ensure_ascii=False, default=str),
                        commit_message=f"Update context for quotation {quotation_id} (version {version})",
                    )
                    await publish_file_to_github(
                        file_path=f"published/{quotation_id}/document.json",
                        html_content=json.dumps(draft, ensure_ascii=False),
                        commit_message=f"Update canonical brochure document for quotation {quotation_id} (version {version})",
                    )
                except Exception as exc:
                    log.exception("[publish] Failed for %s", quotation_id)
                    raise HTTPException(status_code=502, detail=str(exc))
            else:
                quo_dir = os.path.join("published", quotation_id)
                os.makedirs(quo_dir, exist_ok=True)
                with open(os.path.join(quo_dir, filename), "w", encoding="utf-8") as f:
                    f.write(rendered_html)
                with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as f:
                    json.dump(ctx_data, f, ensure_ascii=False, default=str)
                with open(os.path.join(quo_dir, "document.json"), "w", encoding="utf-8") as f:
                    json.dump(draft, f, ensure_ascii=False)
                pdf_suffix = "" if effective_lang == baseline_lang else f"_{effective_lang}"
                pdf_paths = {os.path.join(quo_dir, f"pdf{pdf_suffix}.html")}
                if effective_lang == baseline_lang:
                    pdf_paths.add(os.path.join(quo_dir, f"pdf_{effective_lang}.html"))
                for pdf_path in pdf_paths:
                    with open(pdf_path, "w", encoding="utf-8") as f:
                        f.write(rendered_pdf)
                published_url = f"{PUBLIC_BASE_URL}/published/{quotation_id}/{filename}"

            entry = quotations.get(quotation_id)
            if entry:
                entry["status"] = "published"
                entry["published_url"] = published_url
                entry["html"] = rendered_html
                entry["ctx"] = ctx_data
                entry["pdf_html"] = rendered_pdf
                entry["version"] = version

            log.info("[publish] ✓ %s v%d (lang=%s) [draft] → %s", quotation_id, version, target_lang, published_url)
            return {"published_url": published_url, "version": version, "status": "published"}
        if _is_brochure_template(active_template):
            raise HTTPException(
                status_code=400,
                detail="Brochure publish requires a canonical document draft. Raw HTML publish is only supported for legacy v1 templates.",
            )
        
        if body.html:
            body.html = _repair_word_pasted_editable_blocks(body.html)

        # Extract custom images and store in ctx_data
        custom_images = _extract_custom_images_from_html(body.html or "")
        ctx_data.update(custom_images)
        
        if body.template_name and ctx_data.get("template_name") != body.template_name:
            ctx_data["template_name"] = body.template_name
            ctx_data["html_sync"] = {}
            new_html, _ = await _render_quotation_doc_from_ctx(
                ctx_data,
                quotation_id,
                target_lang or baseline_lang,
                request=request,
                is_pdf=False,
                ignore_published_html=True,
            )
            _sync_ctx_data_before_publish(ctx_data, new_html, target_lang, version=version)
            # Strip editor scripts before publishing
            idx_bar = new_html.find('id="publish-bar"')
            if idx_bar == -1:
                idx_bar = new_html.find("id='publish-bar'")
            if idx_bar != -1:
                idx_start = new_html.rfind('<div', 0, idx_bar)
                if idx_start != -1:
                    idx_scripts = new_html.find('id="editor-scripts"')
                    if idx_scripts == -1:
                        idx_scripts = new_html.find("id='editor-scripts'")
                    if idx_scripts != -1:
                        idx_end_script = new_html.find('</script>', idx_scripts)
                        if idx_end_script != -1:
                            idx_end = idx_end_script + len('</script>')
                            new_html = new_html[:idx_start] + new_html[idx_end:]
            body.html = new_html
        else:
            _sync_ctx_data_before_publish(ctx_data, body.html or "", target_lang or baseline_lang, version)

        rendered_pdf, effective_lang = await _render_quotation_doc_from_ctx(
            ctx_data,
            quotation_id,
            target_lang or baseline_lang,
            request=request,
            is_pdf=True,
            ignore_published_html=True,
        )

        if quotation_id in quotations:
            quotations[quotation_id]["ctx"] = ctx_data

    lang_suffix = f"_{target_lang}" if target_lang and target_lang != baseline_lang else ""
    filename = f"v{version}{lang_suffix}.html"

    if ENVIRONMENT == "production":
        try:
            # Publish files sequentially to avoid 409 conflict
            published_url = await publish_to_github(
                quotation_id=quotation_id,
                html_content=body.html,
                version=version,
                lang=target_lang,
                baseline_lang=baseline_lang
            )
            if ctx_data and rendered_pdf is not None:
                pdf_suffix = "" if effective_lang == baseline_lang else f"_{effective_lang}"
                pdf_files = {f"published/{quotation_id}/pdf{pdf_suffix}.html"}
                if effective_lang == baseline_lang:
                    pdf_files.add(f"published/{quotation_id}/pdf_{effective_lang}.html")
                for pdf_path in sorted(pdf_files):
                    await publish_file_to_github(
                        file_path=pdf_path,
                        html_content=rendered_pdf,
                        commit_message=f"Update PDF view for quotation {quotation_id} {os.path.basename(pdf_path)} (version {version})",
                    )
                await publish_file_to_github(
                    file_path=f"published/{quotation_id}/ctx.json",
                    html_content=json.dumps(ctx_data, ensure_ascii=False, default=str),
                    commit_message=f"Update context for quotation {quotation_id} (version {version})",
                )
        except Exception as exc:
            log.exception("[publish] Failed for %s", quotation_id)
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        # Localhost: write to disk
        quo_dir = os.path.join("published", quotation_id)
        os.makedirs(quo_dir, exist_ok=True)
        file_path = os.path.join(quo_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body.html)
        if ctx_data and rendered_pdf is not None:
            with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as f:
                json.dump(ctx_data, f, ensure_ascii=False, default=str)
            pdf_suffix = "" if effective_lang == baseline_lang else f"_{effective_lang}"
            pdf_paths = {os.path.join(quo_dir, f"pdf{pdf_suffix}.html")}
            if effective_lang == baseline_lang:
                pdf_paths.add(os.path.join(quo_dir, f"pdf_{effective_lang}.html"))
            for pdf_path in pdf_paths:
                with open(pdf_path, "w", encoding="utf-8") as f:
                    f.write(rendered_pdf)
        published_url = f"{PUBLIC_BASE_URL}/published/{quotation_id}/{filename}"
        log.info("[publish] Localhost: wrote to disk %s", file_path)

    # Update in-memory store if entry exists (same instance flow)
    entry = quotations.get(quotation_id)
    if entry:
        entry["status"]        = "published"
        entry["published_url"] = published_url
        entry["html"]          = body.html
        if ctx_data:
            entry["ctx"] = ctx_data
        if rendered_pdf is not None:
            entry["pdf_html"] = rendered_pdf
        entry["version"]       = version

    log.info("[publish] ✓ %s v%d (lang=%s) → %s", quotation_id, version, target_lang, published_url)
    return {"published_url": published_url, "version": version, "status": "published"}


class CanonicalPublishRequest(BaseModel):
    baseRevision: int
    brandId: str | None = None


class BrandUpsertRequest(BaseModel):
    displayName: str
    hostname: str
    status: Literal["active", "disabled"]
    logoAssetKey: str | None = None
    sellerProfile: dict[str, Any] = Field(default_factory=dict)
    renderProfile: BrandRenderProfileContract


def _build_release_asset_manifest(document: Any) -> dict[str, str]:
    manifest: dict[str, str] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            r2_key = value.get("r2Key")
            url = value.get("url")
            if isinstance(url, str) and url.startswith(("http://", "https://")) and not r2_key:
                raise HTTPException(status_code=422, detail={"message": "Published assets must use an approved R2 key, not a direct URL."})
            if isinstance(r2_key, str) and r2_key and r2_key not in manifest.values():
                if not is_allowed_prefix(r2_key):
                    raise HTTPException(status_code=422, detail={"message": f"Asset key is outside approved media prefixes: {r2_key}"})
                manifest[secrets.token_urlsafe(18)] = r2_key
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)
    return manifest


async def _validate_release_asset_manifest(document: Any) -> dict[str, dict[str, str]]:
    """Freeze only existing, approved R2 media into a release manifest."""
    manifest = _build_release_asset_manifest(document)
    try:
        storage = R2Storage()
    except R2StorageConfigurationError as exc:
        raise HTTPException(status_code=422, detail={"message": "R2 storage must be configured before publishing."}) from exc
    validated: dict[str, dict[str, str]] = {}
    for token, r2_key in manifest.items():
        try:
            metadata = await asyncio.to_thread(storage.head_object, r2_key)
        except Exception as exc:
            raise HTTPException(status_code=422, detail={"message": f"Published asset is missing from R2: {r2_key}"}) from exc
        validated[token] = {
            "r2Key": r2_key,
            "contentType": str(metadata.get("ContentType") or "application/octet-stream"),
        }
    return validated


async def _inspect_asset_readiness(document: Any) -> dict[str, Any]:
    """Inspect persisted media references for workflow/review readiness."""
    required_missing = _missing_required_fact_media(document) if isinstance(document, dict) else []
    try:
        manifest = _build_release_asset_manifest(document)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        return {"ready": False, "missing": required_missing, "invalid": [detail], "checkedAt": datetime.now(timezone.utc).isoformat()}
    if not manifest:
        return {"ready": not required_missing, "missing": required_missing, "invalid": [], "checkedAt": datetime.now(timezone.utc).isoformat()}
    try:
        storage = R2Storage()
    except R2StorageConfigurationError as exc:
        return {"ready": False, "missing": required_missing, "invalid": [{"message": str(exc)}], "checkedAt": datetime.now(timezone.utc).isoformat()}
    semaphore = asyncio.Semaphore(8)
    missing: list[str] = []

    async def check(key: str) -> None:
        async with semaphore:
            try:
                await asyncio.to_thread(storage.head_object, key)
            except Exception:
                missing.append(key)

    await asyncio.gather(*(check(key) for key in manifest.values()))
    return {
        "ready": not missing and not required_missing,
        "missing": sorted({*missing, *required_missing}),
        "invalid": [],
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }


def _manifest_r2_key(value: Any) -> str:
    return value.get("r2Key", "") if isinstance(value, dict) else value if isinstance(value, str) else ""


def _apply_branded_media_urls(document: Any, *, hostname: str, release_id: str, asset_manifest: dict[str, Any], media_origin: str | None = None) -> Any:
    reverse_manifest = {_manifest_r2_key(entry): token for token, entry in asset_manifest.items()}
    effective_media_origin = media_origin if media_origin is not None else settings.public_media_origin

    def transform(value: Any) -> Any:
        if isinstance(value, list):
            return [transform(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: transform(child) for key, child in value.items()}
        r2_key = result.get("r2Key")
        token = reverse_manifest.get(r2_key) if isinstance(r2_key, str) else None
        if token:
            base_url = effective_media_origin.rstrip("/") if effective_media_origin is not None else f"https://{hostname}"
            result["url"] = f"{base_url}/media/{release_id}/{token}"
        return result

    return transform(document)


async def _legacy_purge_public_url(urls: str | list[str]) -> None:
    files = [urls] if isinstance(urls, str) else sorted(set(urls))
    if not files:
        return
    zone_id, token = os.getenv("CLOUDFLARE_ZONE_ID", ""), os.getenv("CLOUDFLARE_API_TOKEN", "")
    if not zone_id or not token:
        raise RuntimeError("Cloudflare cache purge credentials are not configured.")
    import urllib.request

    payload = json.dumps({"files": files}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        response = await asyncio.to_thread(urllib.request.urlopen, request, timeout=10)
        body = json.loads(response.read().decode("utf-8"))
        if not body.get("success"):
            raise RuntimeError(f"Cloudflare cache purge rejected: {body.get('errors') or body}")
    except Exception as exc:
        log.exception("Cloudflare cache purge failed for %s", files)
        raise RuntimeError("Cloudflare cache purge failed") from exc


def _release_cache_urls(*, hostname: str, target: Any, release: Any) -> list[str]:
    base = f"https://{hostname}/{target.locale}/q/{target.public_slug}"
    urls = [base, f"{base}/pdf/download"]
    manifest = release.asset_manifest or {}
    for token in manifest:
        urls.append(f"https://{hostname}/media/{release.id}/{token}")
    return urls


def _fallback_public_url(target: Any) -> str:
    slug = getattr(target, "fallback_slug", None) or getattr(target, "public_slug", "")
    return f"https://{settings.public_fallback_hostname}/p/{slug}"


def _fallback_release_cache_urls(*, target: Any, release: Any) -> list[str]:
    base = _fallback_public_url(target)
    urls = [base, f"{base}/pdf/download"]
    manifest = release.asset_manifest or {}
    for token in manifest:
        urls.append(f"https://{settings.public_fallback_hostname}/media/{release.id}/{token}")
    return urls


def _release_transition_cache_urls(*, hostnames: list[str], target: Any, releases: list[Any | None]) -> list[str]:
    """Purge both sides of a release-pointer transition, including immutable media URLs."""
    return _publication_release_transition_cache_urls(
        hostnames=hostnames,
        target=target,
        releases=releases,
        fallback_hostname=settings.public_fallback_hostname,
    )


async def _enqueue_release_purge(
    repository: PublicationTargetRepository,
    *,
    target: Any,
    releases: list[Any | None],
    hostnames: list[str],
    event: str,
) -> None:
    urls = _release_transition_cache_urls(hostnames=hostnames, target=target, releases=releases)
    if not urls:
        return
    release = next((item for item in releases if item is not None), None)
    if release is None:
        return
    await repository.create_job(
        release_id=release.id,
        job_type="purge_cache",
        event_key=f"{event}-{uuid.uuid4().hex}",
        payload_json={"urls": sorted(set(urls))},
        max_attempts=settings.publication_job_max_attempts,
    )


async def _canonical_review_status(quotation_id: str, lang: str | None = None) -> dict[str, Any]:
    _quotation, lang = await _resolve_v2_locale(quotation_id, lang)
    async with _get_db_session_factory()() as session:
        quotes, documents, drafts, targets = QuotationRepository(session), QuotationDocumentRepository(session), ContentDraftRepository(session), PublicationTargetRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        request_row = await quotes.get_latest_quotation_request(quotation_id) if quotation else None
        document = await documents.get_current_document(quotation_id, lang) if quotation else None
        if quotation is None or request_row is None or document is None:
            raise HTTPException(status_code=404, detail="Quotation review state was not found.")
        facts, resolved = await _resolve_v2_facts(CreateQuoteRequestV1.model_validate(normalize_legacy_facts_snapshot(request_row.request_json)))
        content = await drafts.list(quotation_id, lang)
        pending_impacts = await QuotationVersionImpactRepository(session).list(quotation_id, pending_only=True)
        # A pending AI candidate is not a publish blocker by itself. Publish
        # readiness is determined from the canonical document: every enabled
        pending_drafts = sorted({item.scope for item in content if item.status == "draft"})
        content_readiness = resolve_content_readiness(document.document_json, resolved["missingInputs"])
        content_blockers = [
            {"sectionId": item["sectionId"], "sectionType": item["sectionType"], "path": missing["path"], "message": missing["message"]}
            for item in content_readiness if item["status"] is not None
            for missing in item["missing"]
        ]
        presentation_errors: list[str] = []
        try:
            presentation = QuoteDocumentV1.model_validate(document.document_json).presentation
            if presentation.renderer != V2_RENDERER_NAME:
                presentation_errors.append("presentation.renderer")
            if presentation.themeId != "brochure":
                presentation_errors.append("presentation.themeId")
            if presentation.layoutVersion != 1:
                presentation_errors.append("presentation.layoutVersion")
            try:
                _validate_v2_copy_overrides(presentation.copyOverrides)
            except HTTPException:
                presentation_errors.append("presentation.copyOverrides")
        except ValidationError:
            presentation_errors.append("presentation")
        asset_readiness = await _inspect_asset_readiness(document.document_json)
        pdf_layout_errors = _pdf_layout_preflight(document.document_json)
        presentation_errors.extend(pdf_layout_errors)
        publications = await targets.list_targets(quotation_id, locale=lang)
        summary = [{"targetId": item.id, "brandId": item.brand_id, "status": item.status, "activeReleaseId": item.active_release_id} for item in publications]
        impact_blockers = [f"impact:{item.stage}:{item.scope}" for item in pending_impacts]
        return {"ready": not resolved["missingInputs"] and not content_blockers and asset_readiness["ready"] and not presentation_errors and not impact_blockers, "missingInputs": resolved["missingInputs"], "blockingDrafts": pending_drafts, "contentBlockers": content_blockers, "contentReadiness": content_readiness, "presentationErrors": presentation_errors, "assetReadiness": asset_readiness, "impactBlockers": impact_blockers, "currentRevision": document.revision, "publicationTargets": summary}


@app.get("/api/v2/quotations/{quotation_id}/review-status")
async def get_canonical_review_status(quotation_id: str, lang: str | None = None, principal: Principal = Depends(require_editor), _owned=Depends(require_owned_quotation)):
    return await _canonical_review_status(quotation_id, lang)


async def _canonical_workflow(quotation_id: str, lang: str | None = None) -> dict[str, Any]:
    """The server-owned transition contract for Facts -> Content -> Design -> Review."""
    async with _get_db_session_factory()() as session:
        quote = await QuotationRepository(session).get_quotation_by_id(quotation_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quotation workflow was not found.")
    effective_lang = (lang or quote.baseline_lang or "").strip().lower()
    if effective_lang not in {"en", "vi", "ar"}:
        raise HTTPException(status_code=422, detail={"message": "Unsupported quotation locale.", "locale": effective_lang})
    review = await _canonical_review_status(quotation_id, effective_lang)
    unresolved = review["contentBlockers"]
    facts_ready = not review["missingInputs"]
    return {
        "quotationId": quotation_id,
        "locale": effective_lang,
        "currentRevision": review["currentRevision"],
        "facts": {"ready": facts_ready, "missingInputs": review["missingInputs"]},
        "content": {"ready": not unresolved, "blockingDrafts": review["blockingDrafts"], "contentBlockers": unresolved, "generationOptional": True},
        # Design is a read/annotate canvas with hand-offs for Fact-owned media.
        # Missing publish media must still block review/publish, but must not
        # prevent staff from opening the canvas to see and correct the owner.
        "design": {"ready": facts_ready and not unresolved and not review["presentationErrors"], "presentationErrors": review["presentationErrors"], "assetReadiness": review["assetReadiness"]},
        "review": {"ready": review["ready"], "blockers": [*review["missingInputs"], *(item["path"] for item in unresolved), *review["presentationErrors"], *review["assetReadiness"]["missing"], *review["assetReadiness"]["invalid"], *review.get("impactBlockers", [])]},
        "publicationTargets": review["publicationTargets"],
    }


@app.get("/api/v2/quotations/{quotation_id}/workflow")
async def get_canonical_workflow(quotation_id: str, lang: str | None = None, principal: Principal = Depends(require_editor), _owned=Depends(require_owned_quotation)):
    return await _canonical_workflow(quotation_id, lang)


@app.get("/api/internal/v2/quotations/{quotation_id}/workflow")
async def get_internal_canonical_workflow(
    quotation_id: str,
    lang: str | None = None,
    principal: Principal = Depends(require_editor_or_service),
):
    """Server-component bootstrap endpoint; never exposed to the browser."""
    if not principal.is_service:
        raise HTTPException(status_code=403, detail="Service authentication is required.")
    return await _canonical_workflow(quotation_id, lang)


@app.get("/api/v2/brands")
async def list_v2_brands(principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        rows = await BrandRepository(session).list_active()
    return {"brands": [{"id": row.id, "displayName": row.display_name, "hostname": row.hostname, "status": row.status, "logoAssetKey": row.logo_asset_key, "renderProfile": _serialize_brand_render_profile(row)} for row in rows]}


@app.get("/api/internal/v2/brands/editor-bootstrap")
async def get_editor_brand_bootstrap(principal: Principal = Depends(require_editor_or_service)):
    if not principal.is_service:
        raise HTTPException(status_code=403, detail="Service authentication is required.")
    async with _get_db_session_factory()() as session:
        brands = await BrandRepository(session).list_active()
    if not brands:
        raise HTTPException(status_code=404, detail="No active brand is available for the editor.")
    return {"brandProfile": _serialize_brand_render_profile(brands[0])}


@app.put("/api/v2/brands/{brand_id}")
async def update_v2_brand(brand_id: str, body: BrandUpsertRequest, principal: Principal = Depends(require_editor)):
    normalized_hostname = body.hostname.lower().strip().rstrip(".")
    if not re.fullmatch(r"[a-z0-9.-]+", normalized_hostname):
        raise HTTPException(status_code=422, detail="hostname is invalid")
    async with _get_db_session_factory()() as session:
        brands, targets = BrandRepository(session), PublicationTargetRepository(session)
        brand = await brands.get(brand_id)
        if brand is None:
            raise HTTPException(status_code=404, detail="Brand was not found.")
        old_hostname = brand.hostname
        brand.display_name = body.displayName.strip()
        brand.hostname = normalized_hostname
        brand.status = body.status
        brand.logo_asset_key = body.logoAssetKey
        brand.seller_profile = body.sellerProfile
        brand.render_profile = body.renderProfile.model_dump(mode="json")
        try:
            # Brand identity and cache invalidation form one transaction.  A
            # hostname/status change must never commit without its durable
            # purge outbox event.
            contexts = await targets.list_active_release_contexts_for_brand(brand_id)
            for target, release in contexts:
                await targets.lock_target_for_update(target.id)
                await _enqueue_release_purge(
                    targets,
                    target=target,
                    releases=[release],
                    hostnames=[old_hostname, normalized_hostname],
                    event="brand-change",
                )
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(status_code=409, detail="hostname is already assigned to another brand") from exc
    return {"id": brand.id, "displayName": brand.display_name, "hostname": brand.hostname, "status": brand.status}


@app.post("/api/v2/quotations/{quotation_id}/publish")
async def publish_canonical_quotation_v2(quotation_id: str, body: CanonicalPublishRequest, lang: str | None = None, principal: Principal = Depends(require_editor), _owned=Depends(require_owned_quotation)):
    _quotation, effective_lang = await _resolve_v2_locale(quotation_id, lang)
    review = await _canonical_review_status(quotation_id, effective_lang)
    if not review["ready"]:
        raise HTTPException(status_code=422, detail={"message": "Quotation is not ready to publish.", "review": review})
    if review["currentRevision"] != body.baseRevision:
        raise HTTPException(status_code=409, detail={"message": "Document revision conflict.", "currentRevision": review["currentRevision"]})
    async with _get_db_session_factory()() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        target_repository, brands = PublicationTargetRepository(session), BrandRepository(session)
        quotation = await quotes.get_quotation_by_id(quotation_id)
        if quotation is None:
            raise HTTPException(status_code=404, detail="Quotation was not found.")
        brand_id = body.brandId or quotation.brand_id
        if session.bind.dialect.name == "postgresql":
            await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:publication_key))"), {"publication_key": f"{quotation_id}:{brand_id}:{effective_lang}"})
        document = await documents.get_current_document(quotation_id, effective_lang)
        if document is None:
            raise HTTPException(status_code=404, detail="Canonical quotation document was not found.")
        if document.revision != body.baseRevision:
            raise HTTPException(status_code=409, detail={"message": "Document revision conflict.", "currentRevision": document.revision})
        brand = await brands.get_active(brand_id)
        if brand is None:
            raise HTTPException(status_code=422, detail={"message": "Brand is unavailable for publishing.", "missingInputs": ["brandId"]})
        target = await target_repository.create_or_get_target(
            quotation_id=quotation_id,
            brand_id=brand.id,
            locale=effective_lang,
            public_slug=secrets.token_urlsafe(12).lower(),
        )
        release = await target_repository.create_release(
            target=target,
            document_revision=document.revision,
            render_profile_snapshot=_serialize_brand_render_profile(brand),
            asset_manifest=await _validate_release_asset_manifest(document.document_json),
        )
        public_url = f"https://{brand.hostname}/{effective_lang}/q/{target.public_slug}"
        fallback_url = _fallback_public_url(target)
        pdf_key = f"quotations/{quotation_id}/react/{release.id}.pdf"
        job = await target_repository.create_pdf_job(
            release_id=release.id,
            artifact_key=pdf_key,
            max_attempts=settings.publication_job_max_attempts,
        )
        await session.commit()
    return JSONResponse(status_code=202, content={"status": "queued", "version": release.release_number, "published_url": public_url, "fallback_url": fallback_url, "targetId": target.id, "releaseId": release.id, "jobId": job.id})


@app.get("/api/v2/publication-jobs/{job_id}")
async def get_publication_job(job_id: str, principal: Principal = Depends(require_editor)):
    async with _get_db_session_factory()() as session:
        repository = PublicationTargetRepository(session)
        job = await repository.get_job(job_id)
        context = await repository.get_release_context(job.release_id) if job else None
    if job is None:
        raise HTTPException(status_code=404, detail="Publication job was not found.")
    if context is None:
        raise HTTPException(status_code=404, detail="Publication job was not found.")
    _brand, target, _release = context
    await require_owned_quotation(target.quotation_id, principal)
    return {"id": job.id, "releaseId": job.release_id, "type": job.job_type, "status": job.status, "attempts": job.attempts, "maxAttempts": job.max_attempts, "lockedAt": job.locked_at.isoformat() if job.locked_at else None, "lastError": job.last_error}


@app.get("/api/internal/v2/public-quotations/resolve")
async def resolve_public_quotation_v2(
    hostname: str,
    locale: str,
    slug: str,
    principal: Principal = Depends(require_editor_or_service),
):
    if not principal.is_service:
        raise HTTPException(status_code=403, detail="Service authentication is required.")
    if locale not in ("en", "vi", "ar"):
        raise HTTPException(status_code=404, detail="Published quotation was not found.")
    async with _get_db_session_factory()() as session:
        targets, documents = PublicationTargetRepository(session), QuotationDocumentRepository(session)
        resolved = await targets.get_public_target(hostname=hostname, locale=locale, slug=slug)
        if resolved is None:
            raise HTTPException(status_code=404, detail="Published quotation was not found.")
        brand, target, release = resolved
        revision = await documents.get_document_revision(target.quotation_id, lang=locale, revision=release.document_revision)
        if revision is None:
            raise HTTPException(status_code=404, detail="Published quotation revision was not found.")
        return {
            "document": _apply_branded_media_urls(
                revision.document_json,
                hostname=brand.hostname,
                release_id=release.id,
                asset_manifest=release.asset_manifest or {},
                media_origin=settings.public_media_origin if settings.public_media_origin is not None else "",
            ),
            "brandProfile": release.render_profile_snapshot,
            "release": {"id": release.id, "number": release.release_number, "documentRevision": release.document_revision},
        }


@app.get("/api/internal/v2/public-quotations/fallback/{fallback_slug}")
async def resolve_public_fallback_quotation_v2(
    fallback_slug: str,
    principal: Principal = Depends(require_editor_or_service),
):
    if not principal.is_service:
        raise HTTPException(status_code=403, detail="Service authentication is required.")
    async with _get_db_session_factory()() as session:
        targets, documents = PublicationTargetRepository(session), QuotationDocumentRepository(session)
        resolved = await targets.get_public_fallback_target(fallback_slug=fallback_slug)
        if resolved is None:
            raise HTTPException(status_code=404, detail="Published quotation was not found.")
        brand, target, release = resolved
        revision = await documents.get_document_revision(target.quotation_id, lang=target.locale, revision=release.document_revision)
        if revision is None:
            raise HTTPException(status_code=404, detail="Published quotation revision was not found.")
        return {
            "document": _apply_branded_media_urls(
                revision.document_json,
                hostname=settings.public_fallback_hostname,
                release_id=release.id,
                asset_manifest=release.asset_manifest or {},
                media_origin=settings.public_media_origin if settings.public_media_origin is not None else "",
            ),
            "brandProfile": release.render_profile_snapshot,
            "release": {"id": release.id, "number": release.release_number, "documentRevision": release.document_revision},
            "locale": target.locale,
        }


@app.get("/api/internal/v2/public-quotations/releases/{release_id}")
async def resolve_public_quotation_release_v2(release_id: str, principal: Principal = Depends(require_editor_or_service)):
    if not principal.is_service:
        raise HTTPException(status_code=403, detail="Service authentication is required.")
    async with _get_db_session_factory()() as session:
        targets, documents = PublicationTargetRepository(session), QuotationDocumentRepository(session)
        resolved = await targets.get_release_context(release_id)
        if resolved is None:
            raise HTTPException(status_code=404, detail="Publication release was not found.")
        brand, target, release = resolved
        revision = await documents.get_document_revision(target.quotation_id, lang=target.locale, revision=release.document_revision)
        if revision is None:
            raise HTTPException(status_code=404, detail="Published quotation revision was not found.")
        return {"document": _apply_branded_media_urls(revision.document_json, hostname=brand.hostname, release_id=release.id, asset_manifest=release.asset_manifest or {}, media_origin=os.getenv("QUOTE_GENERATOR_INTERNAL_URL", "http://quote-generator:8115")), "brandProfile": release.render_profile_snapshot, "locale": target.locale}


@app.get("/api/internal/v2/public-media/{release_id}/{token}")
async def resolve_public_media_v2(
    release_id: str,
    token: str,
    hostname: str,
    principal: Principal = Depends(require_editor_or_service),
):
    if not principal.is_service:
        raise HTTPException(status_code=403, detail="Service authentication is required.")
    async with _get_db_session_factory()() as session:
        resolved = await PublicationTargetRepository(session).get_public_media_context(
            release_id,
            hostname=hostname,
            fallback_hostname=settings.public_fallback_hostname,
        )
        if resolved is None:
            raise HTTPException(status_code=404, detail="Published media was not found.")
        _brand, _target, release = resolved
        r2_key = _manifest_r2_key((release.asset_manifest or {}).get(token))
    if not r2_key:
        raise HTTPException(status_code=404, detail="Published media was not found.")
    try:
        body = await asyncio.to_thread(R2Storage().download_bytes, r2_key)
    except Exception as exc:
        log.exception("Unable to load published media %s", release_id)
        raise HTTPException(status_code=502, detail="Published media is unavailable.") from exc
    entry = (release.asset_manifest or {}).get(token)
    content_type = entry.get("contentType") if isinstance(entry, dict) else "application/octet-stream"
    return Response(content=body, media_type=content_type or "application/octet-stream", headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/api/internal/v2/public-pdfs/{release_id}")
async def resolve_public_pdf_v2(release_id: str, principal: Principal = Depends(require_editor_or_service)):
    if not principal.is_service:
        raise HTTPException(status_code=403, detail="Service authentication is required.")
    async with _get_db_session_factory()() as session:
        resolved = await PublicationTargetRepository(session).get_release_context(release_id)
        if resolved is None:
            raise HTTPException(status_code=404, detail="Published PDF was not found.")
        brand, target, release = resolved
        if brand.status != "active" or target.status != "published" or release.status != "published" or not release.is_current or not release.pdf_r2_key:
            raise HTTPException(status_code=404, detail="Published PDF was not found.")
        r2_key = release.pdf_r2_key
    try:
        body = await asyncio.to_thread(R2Storage().download_bytes, r2_key)
    except Exception as exc:
        log.exception("Unable to load published PDF %s", release_id)
        raise HTTPException(status_code=502, detail="Published PDF is unavailable.") from exc
    return Response(content=body, media_type="application/pdf", headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/api/v2/quotations/{quotation_id}/publications")
async def list_canonical_publications(quotation_id: str, lang: str | None = None, principal: Principal = Depends(require_editor), _owned=Depends(require_owned_quotation)):
    _quotation, lang = await _resolve_v2_locale(quotation_id, lang)
    async with _get_db_session_factory()() as session:
        targets = await PublicationTargetRepository(session).list_targets(quotation_id, locale=lang)
        brands = BrandRepository(session)
        result = []
        for target in targets:
            brand = await brands.get(target.brand_id)
            releases = await PublicationTargetRepository(session).list_releases(target.id)
            release = next((item for item in releases if item.id == target.active_release_id), None)
            result.append({"targetId": target.id, "brandId": target.brand_id, "hostname": brand.hostname if brand else None, "locale": target.locale, "slug": target.public_slug, "fallbackUrl": _fallback_public_url(target), "status": target.status, "release": {"id": release.id, "number": release.release_number, "documentRevision": release.document_revision} if release else None, "releases": [{"id": item.id, "number": item.release_number, "status": item.status, "documentRevision": item.document_revision, "isCurrent": item.is_current, "job": (lambda job: {"id": job.id, "type": job.job_type, "status": job.status, "attempts": job.attempts, "maxAttempts": job.max_attempts, "lastError": job.last_error} if job else None)(await PublicationTargetRepository(session).get_latest_job(item.id))} for item in releases]})
        return {"publications": result}


@app.post("/api/v2/quotations/{quotation_id}/publication-targets/{target_id}/releases/{release_number}/restore")
async def restore_canonical_publication(quotation_id: str, target_id: str, release_number: int, principal: Principal = Depends(require_editor), _owned=Depends(require_owned_quotation)):
    async with _get_db_session_factory()() as session:
        repository, brands = PublicationTargetRepository(session), BrandRepository(session)
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:target_key))"), {"target_key": target_id})
        target = await repository.lock_target_for_update(target_id, quotation_id=quotation_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Publication target was not found.")
        restored = await repository.restore_release(target=target, release_number=release_number)
        brand = await brands.get(target.brand_id)
        if restored is None or brand is None:
            raise HTTPException(status_code=404, detail="Publication release was not found.")
        release, previous_release = restored
        await _enqueue_release_purge(repository, target=target, releases=[previous_release, release], hostnames=[brand.hostname], event="restore")
        await session.commit()
    public_url = f"https://{brand.hostname}/{target.locale}/q/{target.public_slug}"
    return {"status": "published", "release": release.release_number, "publishedUrl": public_url, "fallbackUrl": _fallback_public_url(target)}


@app.post("/api/v2/quotations/{quotation_id}/publication-targets/{target_id}/unpublish")
async def unpublish_canonical_target(quotation_id: str, target_id: str, principal: Principal = Depends(require_editor), _owned=Depends(require_owned_quotation)):
    async with _get_db_session_factory()() as session:
        repository, brands = PublicationTargetRepository(session), BrandRepository(session)
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:target_key))"), {"target_key": target_id})
        target = await repository.lock_target_for_update(target_id, quotation_id=quotation_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Publication target was not found.")
        brand = await brands.get(target.brand_id)
        active_release = await repository.get_release(target.active_release_id) if target.active_release_id else None
        target.status = "unpublished"
        target.active_release_id = None
        if brand is not None and active_release is not None:
            await _enqueue_release_purge(repository, target=target, releases=[active_release], hostnames=[brand.hostname], event="unpublish")
        await session.commit()
    return {"status": "unpublished"}


@app.get("/quotations/{quotation_id}/versions/{version}/pdf")
async def download_canonical_publication_pdf(quotation_id: str, version: int, lang: str = "en"):
    if _pdf_render_semaphore.locked():
        raise HTTPException(status_code=503, detail="PDF renderer is busy. Please retry shortly.")
    async with _pdf_render_semaphore:
        async with _get_db_session_factory()() as session:
            publications, documents, quotes = PublicationRepository(session), QuotationDocumentRepository(session), QuotationRepository(session)
            publication = await publications.get_publication(quotation_id=quotation_id, version=version, lang=lang)
            quotation = await quotes.get_quotation_by_id(quotation_id)
            if quotation is not None and quotation.template_name == V2_RENDERER_NAME:
                raise HTTPException(status_code=410, detail="React V2 PDFs are available only from the branded publication target.")
            revision = await documents.get_document_revision(quotation_id, lang=lang, revision=publication.document_revision) if publication else None
            if publication is None or quotation is None or revision is None or publication.status not in {"published", "superseded"}:
                raise HTTPException(status_code=404, detail="Published quotation version was not found.")
            print_html = _render_canonical_document_html(revision.document_json, quotation, lang=lang, view="print", version=version)
        try:
            pdf = await asyncio.wait_for(asyncio.to_thread(_render_pdf_bytes, print_html), timeout=60)
        except TimeoutError as exc:
            raise HTTPException(status_code=503, detail="PDF renderer timed out.") from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail="PDF renderer is unavailable.") from exc
        return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="quotation-{quotation_id}-v{version}.pdf"', "Cache-Control": "private, no-store"})


@app.post("/api/v2/legacy-quotations/{quotation_id}/publish", include_in_schema=False)
async def publish_quotation_document_legacy(
    quotation_id: str,
    body: QuoteDocumentPublishRequest,
    request: Request,
    lang: str | None = None,
    language: str | None = None,
):
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    ctx_data = _load_ctx_data(quotation_id)
    if not ctx_data:
        raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")

    quotation, canonical_document, effective_lang = await _load_canonical_quote_document_from_db(quotation_id, target_lang)
    if quotation is None:
        raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")
    if quotation.template_name == V2_RENDERER_NAME:
        raise HTTPException(status_code=410, detail="React V2 quotations publish only through publication targets.")

    effective_lang = effective_lang or quotation.baseline_lang
    template_name = body.template_name or quotation.template_name or ctx_data.get("template_name") or "vietnam_luxury_brosure.html"
    if not _is_brochure_template(template_name):
        raise HTTPException(status_code=400, detail="Document publish is only available for brochure quotations.")

    if body.document is not None:
        current_document_payload = canonical_document
        sanitized_document = _sanitize_canonical_asset_state(
            copy.deepcopy(body.document),
            current_document_payload,
        )
        draft = _hydrate_canonical_quote_document(
            sanitized_document,
            quotation,
            lang=effective_lang,
            revision=body.baseRevision or int((((body.document or {}).get("meta") or {}).get("revision")) or 1),
        )
        validated_document = _validate_quote_document_or_422(draft)
        try:
            async with _get_db_session_factory()() as session:
                quotation_repository = QuotationRepository(session)
                document_repository = QuotationDocumentRepository(session)

                persisted_quotation = await quotation_repository.get_quotation_by_id(quotation_id)
                saved_document = await document_repository.save_current_document(
                    quotation_id=quotation_id,
                    lang=effective_lang,
                    document_json=validated_document,
                    expected_revision=body.baseRevision,
                )
                canonical_document = _hydrate_canonical_quote_document(
                    saved_document.document_json,
                    persisted_quotation,
                    lang=effective_lang,
                    revision=saved_document.revision,
                )
                await document_repository.append_document_revision(
                    quotation_id=quotation_id,
                    lang=effective_lang,
                    revision=saved_document.revision,
                    document_json=canonical_document,
                    change_source="publish",
                )
                await session.commit()
        except DocumentRevisionConflictError as exc:
            current_document = None
            if exc.current_document is not None:
                current_document = _hydrate_canonical_quote_document(
                    exc.current_document,
                    quotation,
                    lang=effective_lang,
                    revision=exc.current_revision or 0,
                )
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Document revision conflict.",
                    "currentRevision": exc.current_revision,
                    "currentDocument": current_document,
                },
            ) from exc
        await _sync_canonical_quote_document_to_ctx(
            quotation_id,
            effective_lang,
            canonical_document,
            f"Prepare canonical brochure document for publish {quotation_id} ({effective_lang})",
        )

    if not canonical_document:
        raise HTTPException(status_code=400, detail="No quote document available to publish.")

    normalized = _store_brochure_draft(ctx_data, effective_lang, _validate_quote_document_or_422(canonical_document))
    publish_body = PublishRequest(draft=normalized, template_name=template_name)
    publish_result = await publish_quotation(
        quotation_id,
        publish_body,
        request,
        lang=effective_lang,
        language=effective_lang,
    )
    version = int(publish_result.get("version") or 1)
    html_r2_key, pdf_r2_key = _build_publication_storage_keys(quotation_id, effective_lang, version)
    async with _get_db_session_factory()() as session:
        publication_repository = PublicationRepository(session)
        document_repository = QuotationDocumentRepository(session)

        await publication_repository.create_publication(
            quotation_id=quotation_id,
            version=version,
            lang=effective_lang,
            html_r2_key=html_r2_key,
            pdf_r2_key=pdf_r2_key,
            published_url=publish_result.get("published_url"),
            pdf_url=f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf",
        )
        if body.document is None:
            latest_document = await document_repository.get_current_document(quotation_id, effective_lang)
            if latest_document is not None:
                publication_document = _hydrate_canonical_quote_document(
                    latest_document.document_json,
                    quotation,
                    lang=effective_lang,
                    revision=latest_document.revision,
                )
                await document_repository.append_document_revision(
                    quotation_id=quotation_id,
                    lang=effective_lang,
                    revision=latest_document.revision,
                    document_json=publication_document,
                    change_source="publish",
                )
        await session.commit()
    return publish_result



# ── Detailed Itinerary Endpoints ─────────────────────────────────────────────

@app.post("/itineraries")
async def create_itinerary(request: Request):
    """
    Receives structured itinerary data, renders a Jinja2 template with booked services,
    stores it locally or on GitHub, and returns the preview/PDF URLs.
    """
    body = await request.json()
    log.debug("[/itineraries] Incoming keys: %s", list(body.keys()))

    # Unwrap ChatGPT Action wrapper if present
    data = body.get("params", body)
    log.debug("[/itineraries] Data keys after unwrap: %s", list(data.keys()))
    lang = data.get("language") or data.get("lang") or request.query_params.get("lang") or request.query_params.get("language") or "en"
    if lang not in ("en", "vi", "ar"):
        lang = "en"

    try:
        payload = DetailItineraryPayload.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        log.error("[/itineraries] Pydantic validation failed — %d error(s):\n%s",
                  len(errors), json.dumps(errors, indent=2, default=str))
        return JSONResponse(status_code=422, content={"detail": errors,
            "hint": "Field path is in 'loc'. Check which required field is missing."})

    itinerary_id = f"iti_{uuid.uuid4().hex[:12]}"

    # Extract destinations from route + itinerary for the gallery
    route_text = " ".join(payload.route)
    itinerary_text = " ".join(
        " ".join(day.destinations or []) + " " + day.title
        for day in payload.itinerary
    )
    text_context = route_text + " " + itinerary_text
    if payload.notes:
        text_context += " " + " ".join(payload.notes)

    from image_selector import (
        extract_and_map_destinations,
        get_random_image_for_province,
        get_province_slug_for_location,
        resolve_slug_locally,
        resolve_slug_from_known,
        get_all_images_for_province,
    )
    destinations = await extract_and_map_destinations(text_context, max_items=None)

    # Resolve image urls for each destination
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))
        d["images"] = get_all_images_for_province(d.get("slug"))

    log.debug("[/itineraries] Extracted destinations: %s", destinations)

    default_img = "/assets/vietnam-safar-logo.png"

    # Hero image: Pick a random image from the resolved destinations, or default
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/itineraries] Hero image resolved: %s", hero_image_url)

    # ── Smart slug resolver for hotels & activities ───────────────────────────
    # Tái sử dụng kết quả đã extract — KHÔNG gọi OpenAI thêm nếu không cần thiết.
    #
    # Thứ tự ưu tiên:
    #   1. resolve_slug_locally()     → tra KEYWORD_MAP tĩnh (không cần mạng)
    #   2. resolve_slug_from_known()  → tra bảng destinations đã extract (không cần mạng)
    #   3. random.choice(extracted_slugs) → fallback ngẫu nhiên từ tour này (không cần mạng)
    #   4. get_province_slug_for_location() → last resort: gọi OpenAI (hiếm khi cần)
    #
    extracted_slugs = [d["slug"] for d in destinations if d.get("slug")]
    known_slugs = {d["name"].lower(): d["slug"] for d in destinations if d.get("name") and d.get("slug")}

    async def _resolve_slug_smart(location: str | None) -> str | None:
        """3-tier resolver: local map → known slugs → random fallback → OpenAI last resort."""
        if not location:
            return random.choice(extracted_slugs) if extracted_slugs else None
        # Tầng 1: local keyword map (pure Python)
        slug = resolve_slug_locally(location)
        if slug:
            log.debug("[slug] '%s' → '%s' (local map)", location, slug)
            return slug
        # Tầng 2: từ bảng destinations đã extract (pure Python)
        slug = resolve_slug_from_known(location, known_slugs)
        if slug:
            log.debug("[slug] '%s' → '%s' (known slugs)", location, slug)
            return slug
        # Tầng 3: chọn ngẫu nhiên từ slugs đã biết trong tour (pure Python)
        if extracted_slugs:
            slug = random.choice(extracted_slugs)
            log.debug("[slug] '%s' → '%s' (random fallback)", location, slug)
            return slug
        # Tầng 4: last resort — gọi OpenAI (chỉ khi không có bất kỳ thông tin nào)
        log.warning("[slug] '%s' → calling OpenAI (last resort)", location)
        return await get_province_slug_for_location(location)

    # Hotels — resolve tất cả song song (asyncio.gather)
    hotels_without_img = [h for h in payload.hotels if not h.imageUrl]
    if hotels_without_img:
        hotel_slugs = await asyncio.gather(
            *[_resolve_slug_smart(h.destination or h.addressArea) for h in hotels_without_img]  # type: ignore
        )
        for h, slug in zip(hotels_without_img, hotel_slugs):
            h.imageUrl = get_random_image_for_province(slug)

    # Activities — resolve tất cả song song (asyncio.gather)
    activities_without_img = [act for act in payload.activities if not act.imageUrl]
    if activities_without_img:
        activity_slugs = await asyncio.gather(
            *[_resolve_slug_smart(act.area or act.activityName) for act in activities_without_img]
        )
        for act, slug in zip(activities_without_img, activity_slugs):
            act.imageUrl = get_random_image_for_province(slug)

    ctx = _build_itinerary_ctx(itinerary_id, payload, hero_image_url, destinations, lang=lang, template_name="detail_itinerary_landingpage_template.html")
    ctx["baseline_payload"] = payload.model_dump(mode="json")
    ctx["baseline_lang"] = lang
    ctx["translations"] = {}
    ctx["available_langs"] = [lang]
    ctx["translation_status"] = {"baseline_lang": lang, "available_langs": [lang]}
    ctx["brand"] = resolve_brand(request, payload.model_dump(mode="json"))

    # Render landing page HTML and PDF
    loop = asyncio.get_event_loop()
    tmpl_lp  = templates.get_template("detail_itinerary_landingpage_template.html")
    tmpl_pdf = templates.get_template("detail_itinerary_landingpage_template_pdf.html")

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render,  **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )

    # Update in-memory store
    itineraries[itinerary_id] = {
        "payload":       payload.model_dump(mode="json"),
        "ctx":           ctx,
        "html":          rendered_html,
        "pdf_html":      rendered_pdf,
        "status":        "pending",
        "published_url": None,
        "pdf_url":       None,
        "version":       0,
    }

    sfx = f"_{lang}" if lang != "en" else ""
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

    if ENVIRONMENT == "production":
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            log.error("[/itineraries] GITHUB_TOKEN or GITHUB_REPO not set — cannot persist on Vercel.")
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: GITHUB_TOKEN / GITHUB_REPO env vars are missing.",
            )
        try:
            # Commit to GitHub
            # Publish files sequentially to avoid 409 conflict
            await publish_file_to_github(
                file_path=f"published/{itinerary_id}/v1{sfx}.html",
                html_content=rendered_html,
                commit_message=f"Publish itinerary {itinerary_id} v1{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{itinerary_id}/pdf{sfx}.html",
                html_content=rendered_pdf,
                commit_message=f"Publish PDF view for itinerary {itinerary_id} pdf{sfx}.html",
            )
            await publish_file_to_github(
                file_path=f"published/{itinerary_id}/ctx.json",
                html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                commit_message=f"Publish itinerary context for {itinerary_id}",
            )
            await publish_file_to_github(
                file_path=f"published/{itinerary_id}/payload.json",
                html_content=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
                commit_message=f"Publish itinerary payload for {itinerary_id}",
            )
            # Initialize and save translation status
            await _save_translation_status(itinerary_id, {"baseline_lang": lang, "available_langs": [lang]})
            
            itineraries[itinerary_id]["status"]        = "published"
            itineraries[itinerary_id]["published_url"] = f"{PUBLIC_BASE_URL}/itineraries/{itinerary_id}"
            itineraries[itinerary_id]["pdf_url"]       = f"{PUBLIC_BASE_URL}/itineraries/{itinerary_id}/pdf"
            itineraries[itinerary_id]["version"]       = 1
            log.info("[/itineraries] ✓ v1{sfx} + pdf{sfx} committed to GitHub.")
        except Exception as exc:
            log.exception("[/itineraries] GitHub publish FAILED for %s: %s", itinerary_id, exc)
            raise HTTPException(
                status_code=502,
                detail=f"GitHub publish failed: {exc}.",
            )
    else:
        # Localhost: write to disk
        iti_dir = os.path.join("published", itinerary_id)
        os.makedirs(iti_dir, exist_ok=True)
        with open(os.path.join(iti_dir, f"v1{sfx}.html"),  "w", encoding="utf-8") as _f:
            _f.write(rendered_html)
        with open(os.path.join(iti_dir, f"pdf{sfx}.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(iti_dir, "ctx.json"), "w", encoding="utf-8") as _f:
            json.dump(ctx, _f, ensure_ascii=False, default=str)
        with open(os.path.join(iti_dir, "payload.json"), "w", encoding="utf-8") as _f:
            json.dump(payload.model_dump(mode="json"), _f, ensure_ascii=False)
        await _save_translation_status(itinerary_id, {"baseline_lang": lang, "available_langs": [lang]})
        
        itineraries[itinerary_id]["status"]  = "published"
        itineraries[itinerary_id]["version"] = 1
        log.info("[/itineraries] Localhost: v1{sfx}.html + pdf{sfx}.html + ctx.json written to disk.")

    log.info("[/itineraries] ✓ id=%s  preparedFor=%s  days=%d",
             itinerary_id, payload.preparedFor, payload.duration.days)

    itinerary_url = f"{PUBLIC_BASE_URL}/itineraries/{itinerary_id}"
    return {
        "itineraryId":  itinerary_id,
        "status":       "published",
        "version":      1,
        "message":      "Itinerary page published. Open itineraryUrl to preview and edit inline.",
        "itineraryUrl": itinerary_url,
        "pdfUrl":       f"{PUBLIC_BASE_URL}/itineraries/{itinerary_id}/pdf",
    }


@app.get("/itineraries/{itinerary_id}", response_class=HTMLResponse)
async def get_itinerary(itinerary_id: str, request: Request):
    """
    Stable permalink for an itinerary.
    Loads Single JSON context (ctx.json), extracts language-specific payload,
    builds the localized context, and renders dynamically.
    """
    lang = request.query_params.get("lang") or request.query_params.get("language")
    if lang not in ("en", "vi", "ar"):
        lang = None # fallback to baseline
        
    ctx_data = _load_ctx_data(itinerary_id)
    if not ctx_data:
        raise HTTPException(
            status_code=404,
            detail=f"Itinerary '{itinerary_id}' not found. It may still be deploying, please refresh in 30 seconds."
        )
        
    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = lang or baseline_lang
    
    # Trigger lazy translation if not available
    if target_lang != baseline_lang:
        available_langs = ctx_data.get("available_langs", [])
        if target_lang not in available_langs:
            success = await _translate_item_on_demand(itinerary_id, target_lang, is_itinerary=True)
            if success:
                ctx_data = _load_ctx_data(itinerary_id) or ctx_data
                
    # Extract appropriate payload dict
    if target_lang == baseline_lang:
        payload_dict = ctx_data.get("baseline_payload")
    else:
        payload_dict = ctx_data.get("translations", {}).get(target_lang)
        
    # Fallback to general context if payload extraction failed
    if not payload_dict:
        log.warning("[get_itinerary] Localized payload for %s not found, using baseline", target_lang)
        payload_dict = ctx_data.get("baseline_payload")
        target_lang = baseline_lang
        
    try:
        payload_obj = DetailItineraryPayload.model_validate(payload_dict)
        tmpl_name = ctx_data.get("template_name", "detail_itinerary_landingpage_template.html")
        tmpl = templates.get_template(tmpl_name)
        
        # Build clean context for target lang
        hero_image_url = ctx_data.get("img_0", "/assets/vietnam-safar-logo.png")
        destinations = ctx_data.get("destinations", [])
        translations = ctx_data.get("translations", {})
        
        # Resolve brand from request and payload
        brand_config = resolve_brand(request, payload_dict)

        lang_ctx = _build_itinerary_ctx(
            itinerary_id=itinerary_id,
            payload=payload_obj,
            hero_image_url=hero_image_url,
            destinations=destinations,
            lang=target_lang,
            template_name=tmpl_name
        )
        lang_ctx["brand"] = brand_config
        lang_ctx["translations"] = translations
        lang_ctx["baseline_lang"] = baseline_lang
        lang_ctx["translation_status"] = ctx_data.get("translation_status", {"baseline_lang": baseline_lang, "available_langs": [baseline_lang]})
        try:
            from github_publish import get_next_version
            next_ver = await get_next_version(itinerary_id)
            lang_ctx["latest_version"] = max(1, next_ver - 1)
        except Exception:
            lang_ctx["latest_version"] = 1
        
        # Try to load language-specific published HTML (no fallback)
        latest_lang = None if target_lang == baseline_lang else target_lang
        html_content = await _get_latest_published_html(itinerary_id, lang=latest_lang, fallback=False)
        if html_content:
            # Re-inject brand data dynamically into the static HTML to support brand switching
            import json
            brand_json = json.dumps(brand_config, ensure_ascii=False)
            import re
            html_content = re.sub(
                r'<script[^>]*id=["\']brand-data["\'][^>]*>.*?</script>',
                f'<script id="brand-data" type="application/json">{brand_json}</script>',
                html_content,
                flags=re.DOTALL
            )
            # Re-enable editor publish bar by making it visible
            html_content = make_itinerary_editor_visible(html_content)
            return HTMLResponse(content=html_content)
            
        # If language-specific published HTML is missing, check if baseline published HTML exists
        # so we can filter out deleted blocks when rendering fallback JINJA2
        if target_lang != baseline_lang:
            baseline_html = await _get_latest_published_html(itinerary_id, lang=None, fallback=False)
            if baseline_html:
                from html.parser import HTMLParser
                class ActiveParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.active_days = set()
                        self.active_cards = {"hotel": set(), "activity": set(), "transfer": set(), "flight": set(), "guide": set()}
                    def handle_starttag(self, tag, attrs):
                        attrs_dict = dict(attrs)
                        if tag == 'div' and 'data-day-number' in attrs_dict:
                            try: self.active_days.add(int(attrs_dict['data-day-number']))
                            except ValueError: pass
                        if 'class' in attrs_dict and 'service-card' in attrs_dict['class']:
                            c_type = attrs_dict.get("data-type")
                            idx_str = attrs_dict.get("data-index")
                            if c_type in self.active_cards and idx_str is not None:
                                try: self.active_cards[c_type].add(int(idx_str))
                                except ValueError: pass
                p = ActiveParser()
                p.feed(baseline_html)
                sync_itinerary_deletions_to_payloads(lang_ctx, p.active_days, p.active_cards)
                
        rendered_html = tmpl.render(**lang_ctx)
        return HTMLResponse(content=rendered_html)
    except Exception as err:
        log.exception("[/itineraries] Dynamic HTML render failed for %s: %s", itinerary_id, err)
        raise HTTPException(status_code=500, detail=f"Render error: {err}")


@app.get("/itineraries/{itinerary_id}/pdf", response_class=HTMLResponse)
async def get_itinerary_pdf(itinerary_id: str, request: Request):
    """
    Dynamically renders PDF HTML for an itinerary in target language.
    Auto-triggers the browser print dialog.
    """
    lang = request.query_params.get("lang") or request.query_params.get("language")
    if lang not in ("en", "vi", "ar"):
        lang = None
        
    ctx_data = _load_ctx_data(itinerary_id)
    if not ctx_data:
        raise HTTPException(status_code=404, detail=f"PDF for itinerary '{itinerary_id}' not found.")
        
    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = lang or baseline_lang
    
    # Trigger lazy translation if not available
    if target_lang != baseline_lang:
        available_langs = ctx_data.get("available_langs", [])
        if target_lang not in available_langs:
            success = await _translate_item_on_demand(itinerary_id, target_lang, is_itinerary=True)
            if success:
                ctx_data = _load_ctx_data(itinerary_id) or ctx_data
                
    # Extract appropriate payload dict
    if target_lang == baseline_lang:
        payload_dict = ctx_data.get("baseline_payload")
    else:
        payload_dict = ctx_data.get("translations", {}).get(target_lang)
        
    if not payload_dict:
        payload_dict = ctx_data.get("baseline_payload")
        target_lang = baseline_lang
        
    try:
        payload_obj = DetailItineraryPayload.model_validate(payload_dict)
        base_tmpl = ctx_data.get("template_name", "detail_itinerary_landingpage_template.html")
        tmpl_name = base_tmpl.replace(".html", "_pdf.html")
        tmpl = templates.get_template(tmpl_name)
        
        hero_image_url = ctx_data.get("img_0", "/assets/vietnam-safar-logo.png")
        destinations = ctx_data.get("destinations", [])
        translations = ctx_data.get("translations", {})
        
        # Resolve brand from request and payload
        brand_config = resolve_brand(request, payload_dict)

        lang_ctx = _build_itinerary_ctx(
            itinerary_id=itinerary_id,
            payload=payload_obj,
            hero_image_url=hero_image_url,
            destinations=destinations,
            lang=target_lang,
            template_name=base_tmpl
        )
        lang_ctx["brand"] = brand_config
        lang_ctx["translations"] = translations
        lang_ctx["baseline_lang"] = baseline_lang
        lang_ctx["translation_status"] = ctx_data.get("translation_status", {"baseline_lang": baseline_lang, "available_langs": [baseline_lang]})
        try:
            from github_publish import get_next_version
            next_ver = await get_next_version(itinerary_id)
            lang_ctx["latest_version"] = max(1, next_ver - 1)
        except Exception:
            lang_ctx["latest_version"] = 1
        
        rendered_html = tmpl.render(**lang_ctx)
        return HTMLResponse(content=rendered_html)
    except Exception as err:
        log.exception("[/itineraries] Dynamic PDF render failed for %s: %s", itinerary_id, err)
        raise HTTPException(status_code=500, detail=f"PDF render error: {err}")


@app.post("/itineraries/{itinerary_id}/publish")
async def publish_itinerary(itinerary_id: str, body: PublishRequest, lang: str = None, language: str = None):
    """ Saves inline edits back to the system. """
    from github_publish import get_next_version, publish_to_github
    version = await get_next_version(itinerary_id)

    # Update ctx.json and pdf.html using values from the edited HTML
    from html.parser import HTMLParser
    
    class ServiceCardParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cards = []
            self.active_days = set()
            self.active_cards = {"hotel": set(), "activity": set(), "transfer": set(), "flight": set(), "guide": set()}
            
        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if tag == 'div' and 'data-day-number' in attrs_dict:
                try:
                    self.active_days.add(int(attrs_dict['data-day-number']))
                except ValueError:
                    pass
            if 'class' in attrs_dict and 'service-card' in attrs_dict['class']:  # type: ignore
                self.cards.append(attrs_dict)
                c_type = attrs_dict.get("data-type")
                idx_str = attrs_dict.get("data-index")
                if c_type in self.active_cards and idx_str is not None:
                    try:
                        self.active_cards[c_type].add(int(idx_str))
                    except ValueError:
                        pass

    parser = ServiceCardParser()
    parser.feed(body.html)
    
    ctx = _load_itinerary_ctx(itinerary_id)
    if ctx:
        sync_itinerary_deletions_to_payloads(ctx, parser.active_days, parser.active_cards)
    rendered_pdf = None
    if ctx:
        for card in parser.cards:
            card_type = card.get("data-type")
            idx_str = card.get("data-index")
            if idx_str is None:
                continue
            idx = int(idx_str)
            
            if card_type == "hotel":
                if idx < len(ctx.get("hotels", [])):
                    h = ctx["hotels"][idx]
                    h["pricePerNightUsd"] = float(card.get("data-price-per-night", 0))
                    h["nights"] = int(card.get("data-nights", 0))
                    h["rooms"] = int(card.get("data-rooms", 1))
            elif card_type == "activity":
                if idx < len(ctx.get("activities", [])):
                    act = ctx["activities"][idx]
                    act["pricePerAdultUsd"] = float(card.get("data-price-adult", 0))
                    act["pricePerChildUsd"] = float(card.get("data-price-child", 0))
                    adults = int(card.get("data-adults", ctx.get("guests_adults") or 0))
                    children = int(card.get("data-children", ctx.get("guests_children") or 0))
                    act["totalEstimateUsd"] = (act["pricePerAdultUsd"] * adults) + (act["pricePerChildUsd"] * children)
            elif card_type == "transfer":
                if idx < len(ctx.get("transfers", [])):
                    tx = ctx["transfers"][idx]
                    base = float(card.get("data-base-cost", 0))
                    tolls = float(card.get("data-tolls", 0))
                    overnight = float(card.get("data-overnight", 0))
                    surcharges = float(card.get("data-surcharges", 0))
                    vat = float(card.get("data-vat", 0))
                    tx["priceUsd"] = base + tolls + overnight + surcharges + vat
            elif card_type == "flight":
                if idx < len(ctx.get("flights", [])):
                    fl = ctx["flights"][idx]
                    fl["priceUsd"] = float(card.get("data-price-ticket", 0))
            elif card_type == "guide":
                if idx < len(ctx.get("guides", [])):
                    gd = ctx["guides"][idx]
                    gd["pricePerDayUsd"] = float(card.get("data-price-day", 0))
                    gd["days"] = int(card.get("data-days", 0))
                    gd["totalEstimateUsd"] = gd["pricePerDayUsd"] * gd["days"]

        # Recalculate Grand Total in ctx
        grand_total = 0.0
        for h in ctx.get("hotels", []):
            grand_total += (h.get("pricePerNightUsd") or 0.0) * (h.get("nights") or 0) * (h.get("rooms") or 1)
        for act in ctx.get("activities", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (act.get("pricePerAdultUsd") or 0.0) * adults + (act.get("pricePerChildUsd") or 0.0) * children
        for tx in ctx.get("transfers", []):
            grand_total += tx.get("priceUsd") or 0.0
        for fl in ctx.get("flights", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (fl.get("priceUsd") or 0.0) * (adults + children)
        for gd in ctx.get("guides", []):
            grand_total += (gd.get("pricePerDayUsd") or 0.0) * (gd.get("days") or 0)

        ctx["grand_total"] = grand_total
        
        if ctx.get("price_options"):
            for opt in ctx["price_options"]:
                if opt.get("isConfirmedMainOption"):
                    opt["totalPrice"]["amount"] = grand_total
                    opt["totalPrice"]["displayText"] = f"${grand_total:,.0f} total"
                    guests_adults = ctx.get("guests_adults") or 1
                    per_person = grand_total / guests_adults
                    opt["pricePerPerson"]["amount"] = per_person
                    opt["pricePerPerson"]["displayText"] = f"${per_person:,.0f} per adult"
            
            main_option = next((o for o in ctx["price_options"] if o.get("isConfirmedMainOption")), None)
            if main_option:
                ctx["total_price"] = main_option["totalPrice"]["displayText"]
                ctx["price_per_pax"] = main_option["pricePerPerson"]["displayText"]
                ctx["pricing_h2"] = f"Indicative Price: {ctx['total_price']}"
                ctx["pricing_p"] = f"Grand total for {ctx['guests_txt']}. Currency: {ctx['currency']}."

        loop = asyncio.get_event_loop()
        tmpl_pdf = templates.get_template("detail_itinerary_landingpage_template_pdf.html")
        rendered_pdf = await loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx))
        
        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            from github_publish import publish_file_to_github
            try:
                # Publish files sequentially to avoid 409 conflict
                await publish_file_to_github(
                    file_path=f"published/{itinerary_id}/pdf.html",
                    html_content=rendered_pdf,
                    commit_message=f"Update PDF view for itinerary {itinerary_id} (version {version})",
                )
                await publish_file_to_github(
                    file_path=f"published/{itinerary_id}/ctx.json",
                    html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                    commit_message=f"Update context for itinerary {itinerary_id} (version {version})",
                )
            except Exception as e:
                log.warning("Failed to publish updated PDF/ctx to GitHub: %s", e)
        else:
            iti_dir = os.path.join("published", itinerary_id)
            os.makedirs(iti_dir, exist_ok=True)
            with open(os.path.join(iti_dir, "ctx.json"), "w", encoding="utf-8") as _f:
                json.dump(ctx, _f, ensure_ascii=False, default=str)
            with open(os.path.join(iti_dir, "pdf.html"), "w", encoding="utf-8") as _f:
                _f.write(rendered_pdf)

    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    target_lang = lang or language
    if target_lang not in ("en", "vi", "ar"):
        target_lang = None

    baseline_lang = "en"
    if ctx:
        baseline_lang = ctx.get("baseline_lang", "en")

    lang_suffix = f"_{target_lang}" if target_lang and target_lang != baseline_lang else ""
    filename = f"v{version}{lang_suffix}.html"

    if ENVIRONMENT == "production":
        try:
            published_url = await publish_to_github(
                quotation_id=itinerary_id,
                html_content=body.html,
                version=version,
                lang=target_lang,
                baseline_lang=baseline_lang
            )
        except Exception as exc:
            log.exception("[publish_itinerary] Failed for %s", itinerary_id)
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        # Localhost: write to disk
        iti_dir = os.path.join("published", itinerary_id)
        os.makedirs(iti_dir, exist_ok=True)
        file_path = os.path.join(iti_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body.html)
        published_url = f"{PUBLIC_BASE_URL}/published/{itinerary_id}/{filename}"
        log.info("[publish_itinerary] Localhost: wrote to disk %s", file_path)

    entry = itineraries.get(itinerary_id)
    if entry:
        entry["status"]        = "published"
        entry["published_url"] = published_url
        entry["html"]          = body.html
        if ctx:
            entry["ctx"]       = ctx
            entry["pdf_html"]  = rendered_pdf
        entry["version"]       = version

    log.info("[publish_itinerary] ✓ %s v%d → %s", itinerary_id, version, published_url)
    return {"published_url": published_url, "version": version, "status": "published"}


@app.post("/itineraries/{itinerary_id}/approve")
async def approve_itinerary(itinerary_id: str, body: ApproveRequest):
    """
    Saves inline edits back to the system, recalculates ctx/PDF,
    and calls the DMC Core webhook with the JWT token.
    """
    from github_publish import get_next_version, publish_to_github
    version = await get_next_version(itinerary_id)

    # 1. Update ctx.json and pdf.html using values from the edited HTML
    from html.parser import HTMLParser
    
    class ServiceCardParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cards = []
            self.active_days = set()
            self.active_cards = {"hotel": set(), "activity": set(), "transfer": set(), "flight": set(), "guide": set()}
            
        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if tag == 'div' and 'data-day-number' in attrs_dict:
                try:
                    self.active_days.add(int(attrs_dict['data-day-number']))
                except ValueError:
                    pass
            if 'class' in attrs_dict and 'service-card' in attrs_dict['class']:  # type: ignore
                self.cards.append(attrs_dict)
                c_type = attrs_dict.get("data-type")
                idx_str = attrs_dict.get("data-index")
                if c_type in self.active_cards and idx_str is not None:
                    try:
                        self.active_cards[c_type].add(int(idx_str))
                    except ValueError:
                        pass

    parser = ServiceCardParser()
    parser.feed(body.html)
    
    ctx = _load_itinerary_ctx(itinerary_id)
    if ctx:
        sync_itinerary_deletions_to_payloads(ctx, parser.active_days, parser.active_cards)
    rendered_pdf = None
    if ctx:
        for card in parser.cards:
            card_type = card.get("data-type")
            idx_str = card.get("data-index")
            if idx_str is None:
                continue
            idx = int(idx_str)
            
            if card_type == "hotel":
                if idx < len(ctx.get("hotels", [])):
                    h = ctx["hotels"][idx]
                    h["pricePerNightUsd"] = float(card.get("data-price-per-night", 0))
                    h["nights"] = int(card.get("data-nights", 0))
                    h["rooms"] = int(card.get("data-rooms", 1))
            elif card_type == "activity":
                if idx < len(ctx.get("activities", [])):
                    act = ctx["activities"][idx]
                    act["pricePerAdultUsd"] = float(card.get("data-price-adult", 0))
                    act["pricePerChildUsd"] = float(card.get("data-price-child", 0))
                    adults = int(card.get("data-adults", ctx.get("guests_adults") or 0))
                    children = int(card.get("data-children", ctx.get("guests_children") or 0))
                    act["totalEstimateUsd"] = (act["pricePerAdultUsd"] * adults) + (act["pricePerChildUsd"] * children)
            elif card_type == "transfer":
                if idx < len(ctx.get("transfers", [])):
                    tx = ctx["transfers"][idx]
                    base = float(card.get("data-base-cost", 0))
                    tolls = float(card.get("data-tolls", 0))
                    overnight = float(card.get("data-overnight", 0))
                    surcharges = float(card.get("data-surcharges", 0))
                    vat = float(card.get("data-vat", 0))
                    tx["priceUsd"] = base + tolls + overnight + surcharges + vat
            elif card_type == "flight":
                if idx < len(ctx.get("flights", [])):
                    fl = ctx["flights"][idx]
                    fl["priceUsd"] = float(card.get("data-price-ticket", 0))
            elif card_type == "guide":
                if idx < len(ctx.get("guides", [])):
                    gd = ctx["guides"][idx]
                    gd["pricePerDayUsd"] = float(card.get("data-price-day", 0))
                    gd["days"] = int(card.get("data-days", 0))
                    gd["totalEstimateUsd"] = gd["pricePerDayUsd"] * gd["days"]

        # Recalculate Grand Total in ctx
        grand_total = 0.0
        for h in ctx.get("hotels", []):
            grand_total += (h.get("pricePerNightUsd") or 0.0) * (h.get("nights") or 0) * (h.get("rooms") or 1)
        for act in ctx.get("activities", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (act.get("pricePerAdultUsd") or 0.0) * adults + (act.get("pricePerChildUsd") or 0.0) * children
        for tx in ctx.get("transfers", []):
            grand_total += tx.get("priceUsd") or 0.0
        for fl in ctx.get("flights", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (fl.get("priceUsd") or 0.0) * (adults + children)
        for gd in ctx.get("guides", []):
            grand_total += (gd.get("pricePerDayUsd") or 0.0) * (gd.get("days") or 0)

        ctx["grand_total"] = grand_total
        
        if ctx.get("price_options"):
            for opt in ctx["price_options"]:
                if opt.get("isConfirmedMainOption"):
                    opt["totalPrice"]["amount"] = grand_total
                    opt["totalPrice"]["displayText"] = f"${grand_total:,.0f} total"
                    guests_adults = ctx.get("guests_adults") or 1
                    per_person = grand_total / guests_adults
                    opt["pricePerPerson"]["amount"] = per_person
                    opt["pricePerPerson"]["displayText"] = f"${per_person:,.0f} per adult"
            
            main_option = next((o for o in ctx["price_options"] if o.get("isConfirmedMainOption")), None)
            if main_option:
                ctx["total_price"] = main_option["totalPrice"]["displayText"]
                ctx["price_per_pax"] = main_option["pricePerPerson"]["displayText"]
                ctx["pricing_h2"] = f"Indicative Price: {ctx['total_price']}"
                ctx["pricing_p"] = f"Grand total for {ctx['guests_txt']}. Currency: {ctx['currency']}."

        loop = asyncio.get_event_loop()
        tmpl_pdf = templates.get_template("detail_itinerary_landingpage_template_pdf.html")
        rendered_pdf = await loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx))
        
        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            from github_publish import publish_file_to_github
            try:
                # Publish files sequentially to avoid 409 conflict
                await publish_file_to_github(
                    file_path=f"published/{itinerary_id}/pdf.html",
                    html_content=rendered_pdf,
                    commit_message=f"Update PDF view for approved itinerary {itinerary_id} (version {version})",
                )
                await publish_file_to_github(
                    file_path=f"published/{itinerary_id}/ctx.json",
                    html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                    commit_message=f"Update context for approved itinerary {itinerary_id} (version {version})",
                )
            except Exception as e:
                log.warning("Failed to publish approved PDF/ctx to GitHub: %s", e)
        else:
            iti_dir = os.path.join("published", itinerary_id)
            os.makedirs(iti_dir, exist_ok=True)
            with open(os.path.join(iti_dir, "ctx.json"), "w", encoding="utf-8") as _f:
                json.dump(ctx, _f, ensure_ascii=False, default=str)
            with open(os.path.join(iti_dir, "pdf.html"), "w", encoding="utf-8") as _f:
                _f.write(rendered_pdf)

    # 2. Save the edited HTML
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        try:
            published_url = await publish_to_github(
                quotation_id=itinerary_id,
                html_content=body.html,
                version=version,
            )
        except Exception as exc:
            log.exception("[approve_itinerary] Failed to publish HTML for %s", itinerary_id)
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        # Localhost: write to disk
        iti_dir = os.path.join("published", itinerary_id)
        os.makedirs(iti_dir, exist_ok=True)
        filename = f"v{version}.html"
        file_path = os.path.join(iti_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body.html)
        published_url = f"{PUBLIC_BASE_URL}/published/{itinerary_id}/{filename}"
        log.info("[approve_itinerary] Localhost: wrote to disk %s", file_path)

    # Update in-memory
    entry = itineraries.get(itinerary_id)
    if entry:
        entry["status"]        = "approved"
        entry["published_url"] = published_url
        entry["html"]          = body.html
        if ctx:
            entry["ctx"]       = ctx
            entry["pdf_html"]  = rendered_pdf
        entry["version"]       = version

    # 3. Webhook callback to DMC Core
    dmc_core_url = (os.environ.get("DMC_CORE_URL") or "http://localhost:8000").rstrip("/")
    webhook_url = f"{dmc_core_url}/webhooks/landing-page/approve"
    log.info("[approve_itinerary] Triggering callback to DMC Core: %s", webhook_url)
    
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {body.token}"}
            payload = {
                "itinerary_id": itinerary_id,
                "status": "approved",
                "grand_total": grand_total if ctx else 0.0
            }
            resp = await client.post(webhook_url, json=payload, headers=headers)
            log.info("[approve_itinerary] DMC Core response status: %d, body: %s", resp.status_code, resp.text)
            if resp.status_code not in (200, 201):
                log.error("[approve_itinerary] DMC Core webhook returned error status %d", resp.status_code)
                raise HTTPException(status_code=502, detail=f"DMC Core webhook callback failed: status {resp.status_code}")
    except Exception as exc:
        log.exception("[approve_itinerary] DMC Core callback failed: %s", exc)
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=502, detail=f"DMC Core callback failed: {exc}")

    log.info("[approve_itinerary] ✓ %s approved v%d → %s", itinerary_id, version, published_url)
    return {"published_url": published_url, "version": version, "status": "approved"}


# ── Landing page (static demo) ───────────────────────────────────────────────

@app.get("/")
async def serve_landing_page():
    return RedirectResponse(url="/workspace", status_code=307)



@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("assets/vietnam-safar-logo.png", media_type="image/png")


@app.get("/assets/{file_path:path}", include_in_schema=False)
async def serve_asset(file_path: str):
    asset_path = os.path.abspath(os.path.join(ASSETS_ROOT, file_path))
    if not asset_path.startswith(ASSETS_ROOT + os.sep) and asset_path != ASSETS_ROOT:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not os.path.isfile(asset_path):
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(asset_path, headers=NO_CACHE_HEADERS)


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    from fastapi.responses import Response
    content = """// Service Worker for Vietnam Safar PWA
const CACHE_NAME = 'vietnam-safar-v4';
const ASSETS = [
  '/',
  '/favicon.ico',
  '/assets/vietnam-safar-logo.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if (!event.request.url.startsWith('http') || event.request.method !== 'GET') return;

  const url = new URL(event.request.url);
  const isSameOrigin = url.origin === self.location.origin;
  const isLocalAsset = isSameOrigin && url.pathname.startsWith('/assets/');
  const isExternalStatic =
    url.hostname === 'unpkg.com' ||
    url.hostname === 'basemaps.cartocdn.com';

  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(event.request) || caches.match('/');
      })
    );
    return;
  }

  if (isLocalAsset) {
    event.respondWith(
      fetch(event.request).then(networkResponse => {
        if (networkResponse && networkResponse.status === 200) {
          const cacheCopy = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, cacheCopy);
          });
        }
        return networkResponse;
      }).catch(() => {
        return caches.match(event.request);
      })
    );
    return;
  }

  if (isExternalStatic) {
    event.respondWith(
      caches.match(event.request).then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request).then(networkResponse => {
          if (networkResponse && networkResponse.status === 200) {
            const cacheCopy = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, cacheCopy);
            });
          }
          return networkResponse;
        });
      })
    );
    return;
  }

  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request).then(cachedResponse => cachedResponse || Response.error());
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const urlToOpen = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
      for (let i = 0; i < windowClients.length; i++) {
        const client = windowClients[i];
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});
"""
    return Response(content=content, media_type="application/javascript", headers=NO_CACHE_HEADERS)


@app.get("/manifest.json", include_in_schema=False)
async def web_manifest(id: str = None, type: str = None, brand: str = None):
    brand_config = BRANDS.get(brand, BRANDS["vietnam_safar"])
    brand_name = brand_config.get("name", "Vietnam Safar")
    brand_logo = brand_config.get("logo", "/assets/vietnam-safar-logo.png")
    brand_primary = brand_config.get("color_primary", "#17412e")

    name = f"{brand_name} - Luxury Travel"
    start_url = "/"
    if id and type:
        start_url = f"/{type}/{id}"
        if brand:
            start_url = f"{start_url}?brand={brand}"
        if type == "quotations":
            entry = quotations.get(id)
            if entry and entry.get("ctx"):
                q_title = entry["ctx"].get("quotation_title") or entry["ctx"].get("tour_title")
                if q_title:
                    name = f"Itinerary: {q_title}"
        elif type == "itineraries":
            entry = itineraries.get(id)
            if entry and entry.get("ctx"):
                i_title = entry["ctx"].get("tour_title") or entry["ctx"].get("quotation_title")
                if i_title:
                    name = f"Itinerary: {i_title}"
                    
    manifest_data = {
        "name": name,
        "short_name": brand_name,
        "description": f"Your luxury travel itinerary and quotation custom-tailored by {brand_name}.",
        "start_url": start_url,
        "display": "standalone",
        "background_color": "#f8f3e9",
        "theme_color": brand_primary,
        "orientation": "any",
        "icons": [
            {
                "src": brand_logo,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": brand_logo,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return manifest_data


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Privacy Policy – Vietnam Safar Quotation API</title>
  <style>
    :root {
      --ivory: #f8f3e9;
      --emerald: #17412e;
      --gold: #b8860b;
      --gold-2: #daa520;
      --ink: #11130f;
      --muted: #706a5d;
      --line: rgba(183,137,75,.22);
      --card: #fffaf1;
      --serif: Georgia, 'Times New Roman', serif;
      --sans: system-ui, Arial, Helvetica, sans-serif;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      background: var(--ivory);
      color: var(--ink);
      font-family: var(--sans);
      line-height: 1.75;
    }
    header {
      background: var(--emerald);
      color: #fff;
      padding: 48px 0 40px;
      text-align: center;
    }
    header .kicker {
      color: var(--gold-2);
      font-size: 11px;
      letter-spacing: .22em;
      text-transform: uppercase;
      font-weight: 700;
      margin-bottom: 14px;
    }
    header h1 {
      font-family: var(--serif);
      font-size: clamp(28px, 5vw, 52px);
      font-weight: 500;
      letter-spacing: -.04em;
    }
    header p {
      margin-top: 12px;
      color: rgba(255,255,255,.7);
      font-size: 14px;
    }
    .container { width: min(820px, 92%); margin: 0 auto; }
    main { padding: 56px 0 80px; }
    section {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 32px 36px;
      margin-bottom: 20px;
    }
    h2 {
      font-family: var(--serif);
      font-size: 22px;
      font-weight: 500;
      color: var(--emerald);
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--line);
    }
    p { color: var(--muted); font-size: 15px; margin-bottom: 12px; }
    p:last-child { margin-bottom: 0; }
    ul { color: var(--muted); font-size: 15px; padding-left: 22px; margin-bottom: 12px; }
    ul li { margin-bottom: 6px; }
    a { color: var(--gold); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .badge {
      display: inline-block;
      background: rgba(183,137,75,.12);
      border: 1px solid var(--line);
      color: var(--gold);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .14em;
      text-transform: uppercase;
      border-radius: 999px;
      padding: 4px 14px;
      margin-bottom: 20px;
    }
    footer {
      text-align: center;
      font-size: 13px;
      color: var(--muted);
      padding: 24px 0 40px;
    }
  </style>
</head>
<body>
  <header>
    <div class="container">
      <div class="kicker">Legal</div>
      <h1>Privacy Policy</h1>
      <p>Vietnam Safar – Discovery Asia Travel Group &nbsp;|&nbsp; Quotation API</p>
    </div>
  </header>

  <main>
    <div class="container">
      <div class="badge">Effective date: May 13, 2026</div>

      <section>
        <h2>1. Overview</h2>
        <p>
          This Privacy Policy describes how <strong>Vietnam Safar – Discovery Asia Travel Group</strong>
          ("we", "our", or "us") handles information submitted through the Vietnam Safar Quotation API,
          which powers the Custom GPT integration for generating travel quotation documents.
        </p>
        <p>
          By using this API or the associated Custom GPT, you agree to the practices described in this policy.
        </p>
      </section>

      <section>
        <h2>2. Information We Collect</h2>
        <p>Through the Quotation API, we may receive the following data submitted by the GPT or user:</p>
        <ul>
          <li>Quotation metadata (quotation number, date, validity period, currency)</li>
          <li>Customer information (company name, contact name, email, phone, address)</li>
          <li>Seller / issuer information (company name, contact details)</li>
          <li>Line items (product or service names, quantities, pricing)</li>
          <li>Payment terms, delivery terms, and notes</li>
          <li>Source identifier (e.g. "custom-gpt", "ChatGPT upload")</li>
        </ul>
      </section>

      <section>
        <h2>3. How We Use This Information</h2>
        <p>Submitted quotation data is used solely for the following purposes:</p>
        <ul>
          <li>Generating and storing travel quotation records for B2B partners</li>
          <li>Enabling the Custom GPT to produce accurate quotation landing pages and documents</li>
          <li>Internal logging and debugging to ensure system reliability</li>
        </ul>
        <p>
          We do <strong>not</strong> use this data for advertising, profiling, or any purpose
          unrelated to the quotation workflow.
        </p>
      </section>

      <section>
        <h2>4. Data Sharing</h2>
        <p>
          We do not sell, rent, or share submitted data with third parties, except as required
          to operate the service (e.g. hosting infrastructure) or comply with applicable law.
        </p>
        <p>
          Data transmitted through the Custom GPT integration is subject to
          <a href="https://openai.com/policies/privacy-policy" target="_blank" rel="noopener">
            OpenAI's Privacy Policy
          </a> for the processing performed on OpenAI's platform.
        </p>
      </section>

      <section>
        <h2>5. Data Retention</h2>
        <p>
          Quotation records are retained for as long as necessary to fulfil the business purpose
          for which they were created, or as required by applicable regulations.
          Internal debug logs are purged on a rolling basis.
        </p>
      </section>

      <section>
        <h2>6. Security</h2>
        <p>
          All data is transmitted over HTTPS. We implement reasonable technical and organisational
          measures to protect submitted information against unauthorised access, loss, or disclosure.
        </p>
      </section>

      <section>
        <h2>7. Your Rights</h2>
        <p>
          You may request access to, correction of, or deletion of any personal data submitted
          through this API by contacting us at the address below.
        </p>
      </section>

      <section>
        <h2>8. Contact</h2>
        <p>
          <strong>Vietnam Safar – Discovery Asia Travel Group</strong><br />
          Email: <a href="mailto:safa@vietnamsafar.vn">safa@vietnamsafar.vn</a><br />
          Phone: <a href="tel:+84911538738">+84 911 538 738</a><br />
          Website: <a href="https://vietnamsafar.vn" target="_blank" rel="noopener">vietnamsafar.vn</a>
        </p>
      </section>
    </div>
  </main>

  <footer>
    <div class="container">
      &copy; 2026 Vietnam Safar – Discovery Asia Travel Group. All rights reserved.
    </div>
  </footer>
</body>
</html>"""
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8111, reload=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Agent-Facing Endpoints — Simplified for Hermes Pool multi-agent pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def _build_agent_ctx(
    session_id: str,
    tour_brief: dict,
    pricing: dict,
    services: dict,
    customer_name: str,
    destinations: list[dict],
    hero_image_url: str,
) -> dict:
    """Build Jinja2 template context from simplified agent workspace data.

    Maps sparse agent output (services, pricing, tour_brief) into the full
    template context dict expected by vietnam_heritage_luxury_b2c.html.
    Missing fields get empty defaults — no UndefinedError at render time.
    """
    # ── Seller info ─────────────────────────────────────────────────
    seller_name = os.getenv("SELLER_NAME", "Vietnam Safar \u2013 Discovery Asia Travel Group")
    seller_email = os.getenv("SELLER_EMAIL", "sales@vietnamsafar.vn")
    seller_phone = os.getenv("SELLER_PHONE", "+84 911 538 738")

    # ── Tour brief fields ────────────────────────────────────────────
    title = tour_brief.get("title", "") or tour_brief.get("tour_name", "")
    subtitle = tour_brief.get("subtitle", "") or tour_brief.get("description", "")
    dests_list = tour_brief.get("destinations", [])
    pax_adults = tour_brief.get("adults", 2)
    pax_children = tour_brief.get("children", 0)
    pax_total = pax_adults + pax_children
    days = tour_brief.get("days", 0) or tour_brief.get("duration_days", 0)
    nights = max(0, days - 1) if days else 0
    duration_lbl = f"{days}D{nights}N" if days else ""
    route_txt = " \u2013 ".join(dests_list)
    guests_txt = f"{pax_adults} Adults" + (f" + {pax_children} Children" if pax_children else "")
    nationality = tour_brief.get("nationality", "") or tour_brief.get("market", "")
    travel_dates = tour_brief.get("travel_dates", "") or tour_brief.get("dates", "")
    travel_style = tour_brief.get("travel_style", "") or tour_brief.get("style", "")
    hotel_standard = tour_brief.get("hotel_standard", "") or tour_brief.get("hotelStandard", "")
    meal_pref = tour_brief.get("meal_preference", "") or tour_brief.get("mealPreference", "")
    tour_code = tour_brief.get("tour_code", "") or tour_brief.get("tourCode", "")

    # ── Pricing ──────────────────────────────────────────────────────
    currency = pricing.get("currency", "USD")
    hotel_price = float(pricing.get("hotel", 0) or 0)
    guide_price = float(pricing.get("guide", 0) or 0)
    transport_price = float(pricing.get("transport", 0) or 0)
    activity_price = float(pricing.get("activity", 0) or 0)
    total = hotel_price + guide_price + transport_price + activity_price
    price_per_person = total / max(1, pax_adults)

    p_pax_txt = f"{currency} {price_per_person:,.0f} / person" if total > 0 else ""
    total_txt = f"{currency} {total:,.0f}" if total > 0 else ""

    price_options = [{
        "hotelCategory": hotel_standard or "Standard",
        "optionName": "Main option",
        "pricePerPerson": {
            "amount": price_per_person,
            "currency": currency,
            "displayText": p_pax_txt,
            "isFromPrice": False,
        },
        "totalPrice": {
            "amount": total,
            "currency": currency,
            "displayText": total_txt,
            "isFromPrice": False,
        },
        "isConfirmedMainOption": True,
        "isAlternativeOption": False,
        "notes": ["Calculated from agent workspace data"],
    }] if total > 0 else []

    # ── Hotels (from services) ───────────────────────────────────────
    hotel_data = services.get("hotel", {}) or {}
    hotel_plan_items = [{
        "destination": hotel_data.get("destination", ""),
        "checkInDate": hotel_data.get("check_in", ""),
        "checkOutDate": hotel_data.get("check_out", ""),
        "hotelArrangement": hotel_data.get("name", ""),
        "status": "confirmed",
    }] if hotel_data else []
    hotel_room_notes = hotel_data.get("notes", "")

    # ── Services ─────────────────────────────────────────────────────
    guide_data = services.get("guide", {}) or {}
    transport_data = services.get("transport", {}) or {}
    activities_data = services.get("activities", []) or []

    # ── Itinerary ────────────────────────────────────────────────────
    days_list = tour_brief.get("itinerary", [])
    if not days_list and days:
        # Build a simple day-by-day from destinations
        for i, dest in enumerate(dests_list or ["Destination"]):
            days_list.append({
                "dayNumber": i + 1,
                "title": f"Explore {dest}",
                "date": "",
                "overnight": dest,
                "meals": [],
                "activities": ["Sightseeing and exploration"],
                "notes": [],
                "description": f"Discover the beauty of {dest}.",
                "destinations": [dest],
            })

    mapped_itinerary = []
    for d in days_list:
        title = d.get("title", "")
        if not title or title.lower().startswith("explore "):
            dest = d.get("overnight") or (d.get("destinations")[0] if d.get("destinations") else "Vietnam")
            title = get_luxury_day_title(dest, d.get("dayNumber", 1), "en")
        mapped_itinerary.append({
            "dayNumber": d.get("dayNumber", 0),
            "title": title,
            "date": d.get("date", ""),
            "overnight": d.get("overnight", ""),
            "meals": d.get("meals", []) or [],
            "activities": d.get("activities", []) or [],
            "notes": d.get("notes", []) or [],
            "description": d.get("description", ""),
            "destinations": [d.get("destination", "")] if d.get("destination") else [],
        })

    # ── Destinations for gallery ─────────────────────────────────────
    gallery_destinations = []
    for i, dest in enumerate(destinations or []):
        img_url = dest.get("image_url", "") or hero_image_url
        gallery_destinations.append({
            "name": dest.get("name", ""),
            "image_url": img_url,
        })

    # ── Why works section ────────────────────────────────────────────
    why_private = (
        "Your personal sanctuary on the move \u2014 private guides, dedicated transport, "
        "and experiences curated exclusively for you."
    )
    why_comfort = (
        "Handpicked accommodations, seamless logistics, and a pace that lets you "
        "truly absorb each destination."
    )
    why_muslim = (
        "Dietary requests, meal planning, and specific preferences are carefully "
        "coordinated to suit all travelers."
    )
    why_balanced = (
        "A carefully balanced rhythm of discovery, relaxation, and cultural ",
        "immersion \u2014 crafted for meaningful travel.",
    )

    # Set image CSS variables
    img_vars = {}
    for i, dest in enumerate(gallery_destinations[:5]):
        img_vars[f"img_{i}"] = dest["image_url"]

    return {
        "quotation_id": session_id,
        "destinations": gallery_destinations,
        "tour_title": title,
        "quotation_title": title,
        "kicker": f"Private Luxury Quotation \u2012 {duration_lbl} \u2012 {travel_dates}" if duration_lbl else "Private Luxury Quotation",
        "lede": subtitle,
        "customer_name": customer_name,
        "nationality": nationality,
        "travel_style": travel_style,
        "guests_txt": guests_txt,
        "route_txt": route_txt,
        "travel_dates": travel_dates,
        "duration_label": duration_lbl,
        # Pricing
        "currency": currency,
        "total_price": total_txt,
        "price_per_pax": p_pax_txt,
        "grand_total": total,
        "subtotal": total,
        "tax_total": 0.0,
        "pricing_title": "PRICE QUOTATION \u2013 INDICATIVE",
        "pricing_basis": "Indicative pricing, subject to reconfirmation",
        "price_options": price_options,
        "pricing_h2": f"Total: {total_txt}" if total_txt else "",
        "pricing_p": f"Grand total for {guests_txt}. Currency: {currency}. Final rates subject to reconfirmation.",
        # Itinerary
        "itinerary_h2": "Day-by-Day Journey",
        "itinerary_p": f"Your private journey \u2014 {len(mapped_itinerary)} days of exploration." if mapped_itinerary else "",
        "itinerary": mapped_itinerary,
        # Overview
        "overview_heading": "Journey Overview",
        "overview_h2": f"{customer_name} \u2014 {title}",
        "overview_p": subtitle,
        "overview_paras": [subtitle] if subtitle else [],
        # Why works
        "why_private": why_private,
        "why_comfort": why_comfort,
        "why_muslim": why_muslim,
        "why_balanced": why_balanced,
        # Hotels
        "hotels": hotel_plan_items,
        "room_notes": hotel_room_notes,
        "optional_enhancements": [],
        # Contact
        "contact": seller_name,
        "contact_phone": seller_phone,
        "contact_web": "www.vietnamsafar.vn",
        "seller_email": seller_email,
        "seller_name": seller_name,
        # Inclusions / exclusions
        "inclusions": [],
        "exclusions": [],
        # Payment terms
        "payment_terms": "Refer to Booking & Payment terms.",
        "term_deposit": "",
        "term_balance": "",
        "term_cancellation": "",
        "term_confirmation": "",
        "final_req": "",
        "final_after": "",
        "cta_h2": "Confirm your travel dates to finalize.",
        "cta_p": "Share any additional requirements \u2014 we will reconfirm availability and return a finalized quotation.",
        # Price conditions
        "price_cond_paras": [""],
        "terms_p": "",
        # Footer
        "footer_text": f"{title} \u2014 Luxury quotation prepared for {customer_name}." if title else "Luxury quotation.",
        # Journey glance
        "show_muslim_care": True,
        "glance_market": nationality,
        "glance_profile": guests_txt,
        "glance_standard": hotel_standard,
        "glance_meals": meal_pref,
        "glance_price_type": "Indicative",
        "glance_tour_code": tour_code,
        "glance_flights": "",
        "glance_basis": "Indicative pricing, subject to reconfirmation",
        "glance_partner_note": "",
        "glance_validity": "Subject to confirmation at time of booking",
        # Raw
        "raw_quotation": "",
        # Images
        **img_vars,
    }


@app.post("/api/v1/landing-page")
async def create_landing_page_agent(request: Request):
    """Simplified landing page endpoint for Hermes Pool multi-agent pipeline.

    Accepts workspace data from session.md instead of full TourQuotationPayload.
    Uses existing template rendering + file persistence infrastructure.

    Request body:
    {
        "session_id": "session-xxx",
        "tour_brief": { "title", "destinations", "adults", "children", "days", ... },
        "pricing": { "hotel", "guide", "transport", "activity", "currency" },
        "services": { "hotel": {...}, "guide": {...}, "transport": {...}, "activities": [...] },
        "customer_name": "...",
        "agent_notes": "..."
    }

    Returns:
    {
        "quotationId": "...",
        "quotationUrl": "...",
        "pdfUrl": "...",
        "localPath": "...",
        "status": "published"
    }
    """
    body = await request.json()

    session_id = body.get("session_id", f"quo_{uuid.uuid4().hex[:12]}")
    tour_brief = body.get("tour_brief", {})
    pricing = body.get("pricing", {})
    services = body.get("services", {})
    customer_name = body.get("customer_name", "Valued Customer")
    agent_notes = body.get("agent_notes", "")

    log.info("[/api/v1/landing-page] session=%s customer=%s", session_id, customer_name)

    # ── 1. Image selection ──────────────────────────────────────────────
    route_list = tour_brief.get("destinations", [])
    route_text = " ".join(route_list)
    itinerary_text = " ".join(
        d.get("title", "") or d.get("destination", "")
        for d in (tour_brief.get("itinerary", []) or [])
    )
    text_context = route_text + " " + itinerary_text

    from image_selector import extract_and_map_destinations, get_random_image_for_province, get_all_images_for_province

    destinations = await extract_and_map_destinations(text_context, max_items=None) if text_context.strip() else []
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))
        d["images"] = get_all_images_for_province(d.get("slug"))
    default_img = "/assets/vietnam-safar-logo.png"
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/api/v1/landing-page] destinations=%d hero=%s", len(destinations), hero_image_url)

    # ── 2. Build template context ───────────────────────────────────────
    ctx = _build_agent_ctx(session_id, tour_brief, pricing, services, customer_name, destinations, hero_image_url)

    # ── 3. Render templates ─────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    tmpl_lp = templates.get_template("vietnam_heritage_luxury_b2c.html")
    tmpl_pdf = templates.get_template("vietnam_heritage_luxury_b2c_pdf.html")

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render, **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )

    # ── 4. Write to disk (always — both local and production) ───────────
    quo_dir = os.path.join("published", session_id)
    os.makedirs(quo_dir, exist_ok=True)

    v1_path = os.path.join(quo_dir, "v1.html")
    pdf_path = os.path.join(quo_dir, "pdf.html")
    ctx_path = os.path.join(quo_dir, "ctx.json")

    with open(v1_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    with open(pdf_path, "w", encoding="utf-8") as f:
        f.write(rendered_pdf)
    with open(ctx_path, "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, default=str)

    log.info("[/api/v1/landing-page] Written: %s, %s, %s", v1_path, pdf_path, ctx_path)

    # ── 5. Optional GitHub publish (production only) ────────────────────
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    published_url: str | None = None
    pdf_static_url: str | None = None

    if ENVIRONMENT == "production" and os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_REPO"):
        try:
            from github_publish import publish_file_to_github, publish_to_github

            # Publish files sequentially to avoid 409 conflict
            published_url = await publish_to_github(session_id, rendered_html, version=1)
            pdf_static_url = await publish_file_to_github(
                file_path=f"published/{session_id}/pdf.html",
                html_content=rendered_pdf,
                commit_message=f"Publish PDF for quotation {session_id}",
            )
            log.info("[/api/v1/landing-page] GitHub published: %s", published_url)
        except Exception as exc:
            log.warning("[/api/v1/landing-page] GitHub publish skipped: %s", exc)

    # ── 6. Build response URL ───────────────────────────────────────────
    base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8111")
    quotation_url = published_url or f"{base_url}/published/{session_id}/v1.html"
    pdf_url = pdf_static_url or f"{base_url}/published/{session_id}/pdf.html"
    local_path = str(v1_path)

    return {
        "quotationId": session_id,
        "quotationUrl": quotation_url,
        "pdfUrl": pdf_url,
        "localPath": local_path,
        "status": "published",
        "version": 1,
    }


def format_hotel_dates(checkin: str, checkout: str, lang: str = "en") -> str:
    return format_display_date_range_for_lang(checkin, checkout, lang)


# ── Dynamic hotel details fuzzy resolver (Fusion Search + info.json) ──────────
def strip_accents(text: str) -> str:
    import unicodedata
    if not text:
        return ""
    normalized = unicodedata.normalize('NFD', text)
    stripped = "".join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return stripped.replace('Đ', 'D').replace('đ', 'd')

HOTEL_STOP_WORDS = {
    'hotel', 'resort', 'cruise', 'spa', 'villas', 'luxury', 'premium', 
    'boutique', 'stay', 'suites', 'center', 'ocean', 'safi', 'premium',
    'classic', 'legend', 'metropole', 'retreat', 'lodge', 'palace',
    'khach', 'san', 'khachsan', 'nha', 'du', 'thuyen', 'duthuyen'
}

def tokenize_hotel_name(text: str) -> set:
    import re
    if not text:
        return set()
    clean = re.sub(r'[^a-zA-Z0-9\s-]', '', strip_accents(text)).lower()
    tokens = set(re.split(r'[\s-]', clean))
    return {t for t in tokens if t and t not in HOTEL_STOP_WORDS}

def char_similarity(str1: str, str2: str) -> float:
    import difflib
    return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def calculate_match_score(hotel_name: str, city_name: str, city_dir: str, hotel_dir: str) -> float:
    score = 0.0
    norm_city_input = strip_accents(city_name).lower().replace(" ", "").replace("-", "")
    norm_city_dir = strip_accents(city_dir).lower().replace(" ", "").replace("-", "")
    
    city_aliases = {
        "saigon": {"saigon", "hochiminh", "hochiminhcity", "hcmc"},
        "hanoi": {"hanoi"},
        "halong": {"halong", "halongbay", "quangninh"},
        "dalat": {"dalat", "lamdong"},
        "danang": {"danang"},
        "sapa": {"sapa", "laocai"}
    }
    
    city_matched = False
    if norm_city_input == norm_city_dir:
        city_matched = True
    else:
        for key, aliases in city_aliases.items():
            if norm_city_input in aliases and norm_city_dir in aliases:
                city_matched = True
                break
                
    if city_matched:
        score += 2.0
        
    input_tokens = tokenize_hotel_name(hotel_name)
    dir_tokens = tokenize_hotel_name(hotel_dir)
    
    matched_tokens = set()
    for it in input_tokens:
        for dt in dir_tokens:
            if it == dt or char_similarity(it, dt) >= 0.8:
                matched_tokens.add(it)
                break
                
    if input_tokens and dir_tokens:
        jaccard = len(matched_tokens) / len(input_tokens.union(dir_tokens))
        score += jaccard * 3.0
        
        for dt in dir_tokens:
            for it in input_tokens:
                if dt in it or it in dt:
                    score += 0.5
                    break
    else:
        sim = char_similarity(hotel_name, hotel_dir)
        score += sim * 2.0
            
    return score

def resolve_hotel_details(hotel_name: str, city_name: str, base_dir: str = "assets/hotels", index: int = 0, lang: str = "en") -> dict | None:
    if not os.path.exists(base_dir):
        return None
        
    best_score = -1.0
    best_match = None
    
    for city_dir in os.listdir(base_dir):
        city_path = os.path.join(base_dir, city_dir)
        if not os.path.isdir(city_path):
            continue
            
        for hotel_dir in os.listdir(city_path):
            hotel_path = os.path.join(city_path, hotel_dir)
            if not os.path.isdir(hotel_path):
                continue
                
            score = calculate_match_score(hotel_name, city_name, city_dir, hotel_dir)
            if score > best_score:
                best_score = score
                best_match = (city_dir, hotel_dir, hotel_path)
                
    city_matched_bool = False
    if best_match:
        norm_input = city_name.lower().replace(" ", "").replace("-", "")
        norm_dir = best_match[0].lower().replace(" ", "").replace("-", "")
        city_matched_bool = (norm_input == norm_dir)
        
    threshold = 2.2 if city_matched_bool else 1.5
    
    # Token matching check (protection against same-city false matches)
    input_tokens = tokenize_hotel_name(hotel_name)
    dir_tokens = tokenize_hotel_name(best_match[1]) if best_match else set()
    matched_tokens = set()
    for it in input_tokens:
        for dt in dir_tokens:
            if it == dt or char_similarity(it, dt) >= 0.8:
                matched_tokens.add(it)
                break
    has_token_match = len(matched_tokens) > 0
    
    if best_match and best_score >= threshold and has_token_match:
        city_dir, hotel_dir, matched_path = best_match
        
        name = hotel_name.split("(")[0].strip() if hotel_name else "Luxury Hotel"
        tel = "+84 28 3933 3226"
        suffix = translate_filter("offers refined luxury accommodations, personalized service, and modern comforts.", lang)
        intro = f"{name} {suffix}"
        
        info_path = os.path.join(matched_path, "info.json")
        if os.path.exists(info_path):
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                    name = info.get("name", name)
                    tel = info.get("tel", tel)
                    intro = info.get("introduction", intro)
            except Exception:
                pass
                
        ext_dir = os.path.join(matched_path, "exterior")
        ext_imgs = []
        if os.path.exists(ext_dir) and os.path.isdir(ext_dir):
            ext_imgs = sorted([f for f in os.listdir(ext_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
            
        int_dir = os.path.join(matched_path, "interior")
        int_imgs = []
        if os.path.exists(int_dir) and os.path.isdir(int_dir):
            int_imgs = sorted([f for f in os.listdir(int_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
            
        root_imgs = sorted([f for f in os.listdir(matched_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
        
        # Translate introduction
        if "offers refined luxury accommodations" in intro:
            suffix = translate_filter("offers refined luxury accommodations, personalized service, and modern comforts.", lang)
            intro = f"{name} {suffix}"
        else:
            intro = translate_filter(intro, lang)

        # Resolve exterior image using modulo on index to rotate/shuffle images
        if ext_imgs:
            ext_idx = index % len(ext_imgs)
            ext_img = f"/assets/hotels/{city_dir}/{hotel_dir}/exterior/{ext_imgs[ext_idx]}"
        elif int_imgs:
            ext_idx = index % len(int_imgs)
            ext_img = f"/assets/hotels/{city_dir}/{hotel_dir}/interior/{int_imgs[ext_idx]}"
        elif root_imgs:
            ext_idx = index % len(root_imgs)
            ext_img = f"/assets/hotels/{city_dir}/{hotel_dir}/{root_imgs[ext_idx]}"
        else:
            ext_img = ""

        # Resolve interior image (offsetting index by 1 to get a different picture)
        if int_imgs:
            int_idx = (index + 1) % len(int_imgs)
            int_img = f"/assets/hotels/{city_dir}/{hotel_dir}/interior/{int_imgs[int_idx]}"
        elif ext_imgs:
            int_idx = (index + 1) % len(ext_imgs)
            int_img = f"/assets/hotels/{city_dir}/{hotel_dir}/exterior/{ext_imgs[int_idx]}"
        elif root_imgs:
            int_idx = (index + 1) % len(root_imgs)
            int_img = f"/assets/hotels/{city_dir}/{hotel_dir}/{root_imgs[int_idx]}"
        else:
            int_img = ""
            
        return {
            "name": name,
            "tel": tel,
            "introduction": intro,
            "hotel_img": ext_img,
            "room_img": int_img
        }
        
    return None


def get_luxury_hotel_details(hotel_name_or_arr: str, destination: str, checkin: str, checkout: str, index: int = 0, lang: str = "en") -> dict:
    name_lower = hotel_name_or_arr.lower() if hotel_name_or_arr else ""
    date_range = format_hotel_dates(checkin, checkout, lang)
    city_country = f"{destination.upper()}, VIETNAM" if destination else "VIETNAM"
    
    # Parse name, room type, and notes from hotelArrangement
    raw_name = hotel_name_or_arr
    room_type = ""
    notes = ""
    
    if hotel_name_or_arr:
        parts = [p.strip() for p in hotel_name_or_arr.split(" - ") if p.strip()]
        if len(parts) > 0:
            raw_name = parts[0]
        if len(parts) > 1:
            room_type = parts[1]
        if len(parts) > 2:
            notes = " - ".join(parts[2:])
        if not room_type:
            paren_match = re.search(r'\(([^()]+)\)\s*$', hotel_name_or_arr)
            if paren_match:
                room_type = paren_match.group(1).strip()
            
    requested_name = raw_name.split("(")[0].strip() if raw_name else "Luxury Hotel"
    name = requested_name
    tel = "+84 28 3933 3226"
    suffix = translate_filter("offers refined luxury accommodations, personalized service, and modern comforts.", lang)
    intro = f"{name} {suffix}"
    hotel_img = ""
    room_img = ""
    
    # 1. Try resolving dynamically from the local database (Fusion Search + info.json)
    resolved = resolve_hotel_details(requested_name, destination, index=index, lang=lang)
    if resolved:
        input_tokens = tokenize_hotel_name(requested_name)
        resolved_tokens = tokenize_hotel_name(resolved["name"])
        location_stopwords = {
            "hotel", "resort", "spa", "vietnam", "and", "the", "luxury", "boutique", "villa", "villas", "suites", "suite",
            "danang", "da", "nang", "hoian", "hoi", "an", "hanoi", "ha", "noi", "sapa", "halong", "saigon", "ninhbinh", "ninh", "binh"
        }
        core_input = {t for t in input_tokens if t not in location_stopwords}
        core_resolved = {t for t in resolved_tokens if t not in location_stopwords}
        
        # Only overwrite name/intro if there is core token overlap
        if core_input and core_resolved and core_input.intersection(core_resolved):
            name = resolved["name"]
            intro = resolved["introduction"]
        else:
            name = requested_name
            intro = f"{requested_name} {suffix}"
            
        tel = resolved.get("tel", tel)
        hotel_img = resolved.get("hotel_img", "")
        room_img = resolved.get("room_img", "")
    else:
        # 2. Legacy static overrides (No destination fallback here, only name-based override)
        if "metropole" in name_lower:
            name = "Sofitel Legend Metropole Hanoi"
            tel = "+84 24 3826 6919"
            intro = "A historic landmark since 1901, the Sofitel Legend Metropole Hanoi features French colonial grandeur blended with contemporary luxury. Located in the heart of Hanoi, it has welcomed playwrights, ambassadors, and heads of state. The hotel offers guestrooms adorned with rich wood, classic elegance, and refined Vietnamese touches. Indulge in culinary excellence at Le Beaulieu or relax at the heritage-rich Bamboo Bar by the garden pool, experiencing timeless colonial prestige."
            hotel_img = "/assets/hotels/metropole_facade.jpg"
            room_img = "/assets/hotels/metropole_room.jpg"
        elif "orchid" in name_lower:
            name = "Orchid Classic Cruise"
            tel = "+84 96 123 4567"
            intro = "Cruising the pristine waters of Lan Ha Bay and Halong Bay, Orchid Classic Cruise offers an intimate boutique experience with charter-level luxury. Featuring elegant Indochine architecture combined with modern wooden furnishings, the cruise hosts spacious suites, each featuring a private ocean-view balcony and a walk-in shower. Guests can relax in the outdoor jacuzzi, enjoy sunset cocktails on the sundeck, and savor fine dining showcasing local seafood delicacies."
            hotel_img = "/assets/hotels/orchid_cruise.jpg"
            room_img = "/assets/hotels/orchid_room.jpg"
        elif "four seasons" in name_lower or "nam hai" in name_lower:
            name = "Four Seasons Resort The Nam Hai"
            tel = "+84 235 394 0000"
            intro = "An oasis of luxury along a pristine portal of Hoi An's coastline, Four Seasons Resort The Nam Hai offers a sleek, design-led sanctuary. Inspired by traditional wind-and-water principles, the villas are designed with high ceilings, central platforms, and private terrace views. Guests can lounge by three infinity pools, experience holistic therapies at the floating spa pavilions, and relish exceptional Vietnamese culinary artistry under the shade of mature coconut palms."
            hotel_img = "/assets/hotels/nam_hai_facade.jpg"
            room_img = "/assets/hotels/nam_hai_room.jpg"
        elif "ylang" in name_lower:
            name = "Heritage Line Ylang"
            tel = "+84 28 3933 3226"
            intro = "Cruising Lan Ha Bay, part of Vietnam's famous Halong Bay, Ylang has a length of 57 meters, a draft of 1.9 meters and a cruise speed of around 10 nautical knots. Launched in 2019, the vessel is a mix of Indochinese-Vietnamese design, comprised of 10 suites divided into two room categories, both of which feature private balconies, separate lounge areas, walk-in showers and separate bathtubs, large sliding doors, air conditioning and beautiful wood panels. Facilities include the reception-lobby area, a boutique, spa and sauna areas, a wellness studio, a library lounge, a restaurant and bar, as well as a terrace deck with a pool."
            hotel_img = "/assets/hotels/orchid_cruise.jpg"
            room_img = "/assets/hotels/orchid_room.jpg"

    return {
        "city_country": city_country,
        "name": name,
        "introduction": intro,
        "hotel_img": hotel_img,
        "room_img": room_img,
        "room_type": room_type,
        "room_name": room_type,
        "notes": notes,
        "date_range": date_range,
        "tel": tel,
        "destination": destination,
        "checkInDate": checkin,
        "checkOutDate": checkout
    }

# Reload trigger comment to refresh cached templates and routing logic v2

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, path_name: str):
    if path_name.startswith("api/") or request.url.path.startswith("/api/"):
        raise HTTPException(status_code=404, detail=f"API endpoint '{request.url.path}' not found.")
    return {"url_path": request.url.path, "path_name": path_name, "scope_path": request.scope.get("path")}
