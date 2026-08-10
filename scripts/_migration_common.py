from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quote_document import build_rich_content_from_legacy, strip_legacy_rich_document_fields
from quote_document_adapter import normalize_quote_document

BROCHURE_TEMPLATE_NAME = "vietnam_luxury_brosure.html"
PUBLICATION_HTML_PATTERN = re.compile(r"^v(?P<version>\d+)(?:_(?P<lang>[a-z]{2,5}))?\.html$", re.IGNORECASE)


@dataclass(frozen=True)
class PublicationCandidate:
    html_path: Path
    version: int
    lang: str
    pdf_path: Path | None = None


def load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def discover_quotation_dirs(root: str | Path, quotation_ids: list[str] | None = None) -> list[Path]:
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"Published root does not exist: {root_path}")

    filters = {item.strip() for item in quotation_ids or [] if item and item.strip()}
    directories = []
    for candidate in sorted(root_path.iterdir()):
        if not candidate.is_dir():
            continue
        if not candidate.name.startswith("quo_"):
            continue
        if filters and candidate.name not in filters:
            continue
        directories.append(candidate)
    return directories


def build_publication_storage_keys(quotation_id: str, lang: str, version: int) -> tuple[str, str]:
    return (
        f"quotations/{quotation_id}/publish/{lang}/v{version}.html",
        f"quotations/{quotation_id}/publish/{lang}/v{version}.pdf",
    )


def parse_publication_candidates(quotation_dir: Path, baseline_lang: str) -> list[PublicationCandidate]:
    candidates: list[PublicationCandidate] = []
    pdf_candidates = _parse_pdf_candidates(quotation_dir, baseline_lang)
    for file_path in sorted(quotation_dir.iterdir()):
        if not file_path.is_file():
            continue
        match = PUBLICATION_HTML_PATTERN.match(file_path.name)
        if match is None:
            continue
        lang = (match.group("lang") or baseline_lang or "en").lower()
        candidates.append(
            PublicationCandidate(
                html_path=file_path,
                version=int(match.group("version")),
                lang=lang,
                pdf_path=pdf_candidates.get(lang) or pdf_candidates.get("__baseline__"),
            )
        )
    return sorted(candidates, key=lambda item: (item.version, item.lang, item.html_path.name))


def _parse_pdf_candidates(quotation_dir: Path, baseline_lang: str) -> dict[str, Path]:
    pdf_pattern = re.compile(r"^pdf(?:_(?P<lang>[a-z]{2,5}))?(?:_(?P<suffix>\d+))?\.html$", re.IGNORECASE)
    matches: dict[str, list[tuple[int, int, Path]]] = {}
    for file_path in sorted(quotation_dir.iterdir()):
        if not file_path.is_file():
            continue
        match = pdf_pattern.match(file_path.name)
        if match is None:
            continue
        lang = (match.group("lang") or baseline_lang or "en").lower()
        suffix = int(match.group("suffix") or 0)
        rank = 0 if suffix == 0 else 1
        matches.setdefault(lang, []).append((rank, suffix, file_path))

    selected: dict[str, Path] = {}
    for lang, entries in matches.items():
        best = sorted(entries, key=lambda item: (item[0], item[1], item[2].name))[0]
        selected[lang] = best[2]
    if baseline_lang in selected:
        selected["__baseline__"] = selected[baseline_lang]
    return selected


def first_text(*values: Any, default: str | None = None) -> str | None:
    for value in values:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
    return default


def first_dict(*values: Any) -> dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def first_int(*values: Any, default: int = 0) -> int:
    for value in values:
        if value in (None, ""):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return default


def extract_brand_id(
    ctx_data: dict[str, Any] | None,
    document_json: dict[str, Any] | None,
    request_json: dict[str, Any] | None,
) -> str:
    ctx_brand = first_dict((ctx_data or {}).get("brand"))
    document_meta = first_dict((document_json or {}).get("meta"))
    return first_text(
        ctx_brand.get("id"),
        document_meta.get("brandId"),
        (request_json or {}).get("brand_id"),
        (request_json or {}).get("brandId"),
        default="vietnam_safar",
    ) or "vietnam_safar"


def extract_template_name(
    ctx_data: dict[str, Any] | None,
    document_json: dict[str, Any] | None,
    request_json: dict[str, Any] | None,
) -> str:
    document_meta = first_dict((document_json or {}).get("meta"))
    return first_text(
        (ctx_data or {}).get("template_name"),
        document_meta.get("template"),
        (request_json or {}).get("template_name"),
        (request_json or {}).get("templateName"),
        default=BROCHURE_TEMPLATE_NAME,
    ) or BROCHURE_TEMPLATE_NAME


def extract_baseline_lang(
    ctx_data: dict[str, Any] | None,
    document_json: dict[str, Any] | None,
    request_json: dict[str, Any] | None,
) -> str:
    document_meta = first_dict((document_json or {}).get("meta"))
    return first_text(
        (ctx_data or {}).get("baseline_lang"),
        document_meta.get("lang"),
        (request_json or {}).get("lang"),
        (request_json or {}).get("language"),
        default="en",
    ) or "en"


def extract_available_langs(
    ctx_data: dict[str, Any] | None,
    *,
    baseline_lang: str,
) -> list[str]:
    candidates = (
        (ctx_data or {}).get("available_langs"),
        ((ctx_data or {}).get("translation_status") or {}).get("available_langs"),
    )
    normalized: list[str] = []
    seen: set[str] = set()
    for values in candidates:
        if not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, str):
                continue
            lang = value.strip().lower()
            if not lang or lang in seen:
                continue
            normalized.append(lang)
            seen.add(lang)
    baseline = (baseline_lang or "en").strip().lower() or "en"
    if baseline not in seen:
        normalized.insert(0, baseline)
    return normalized or [baseline]


def extract_translation_status(
    ctx_data: dict[str, Any] | None,
    *,
    baseline_lang: str,
    available_langs: list[str],
) -> dict[str, Any]:
    status = copy.deepcopy((ctx_data or {}).get("translation_status") or {})
    status["baseline_lang"] = status.get("baseline_lang") or baseline_lang
    status["available_langs"] = status.get("available_langs") or available_langs
    return status


def extract_opportunity_id(
    ctx_data: dict[str, Any] | None,
    document_json: dict[str, Any] | None,
    request_json: dict[str, Any] | None,
) -> str | None:
    document_meta = first_dict((document_json or {}).get("meta"))
    customer = first_dict((request_json or {}).get("customer"))
    return first_text(
        (ctx_data or {}).get("opportunity_id"),
        document_meta.get("opportunityId"),
        (request_json or {}).get("opportunity_id"),
        (request_json or {}).get("opportunityId"),
        customer.get("opportunity_id"),
        customer.get("opportunityId"),
    )


def extract_customer_name(
    ctx_data: dict[str, Any] | None,
    document_json: dict[str, Any] | None,
    request_json: dict[str, Any] | None,
) -> str | None:
    traveler = first_dict((document_json or {}).get("traveler"))
    customer = first_dict((request_json or {}).get("customer"))
    trip_facts = first_dict((request_json or {}).get("trip_facts"))
    return first_text(
        traveler.get("customerName"),
        (ctx_data or {}).get("customer_name"),
        (request_json or {}).get("customer_name"),
        customer.get("name"),
        trip_facts.get("customer_name"),
    )


def extract_title(
    ctx_data: dict[str, Any] | None,
    document_json: dict[str, Any] | None,
    request_json: dict[str, Any] | None,
) -> str | None:
    trip = first_dict((document_json or {}).get("trip"))
    trip_facts = first_dict((request_json or {}).get("trip_facts"))
    return first_text(
        trip.get("title"),
        (ctx_data or {}).get("tour_title"),
        (ctx_data or {}).get("title"),
        trip_facts.get("title"),
        (request_json or {}).get("title"),
    )


def extract_html_sync(
    ctx_data: dict[str, Any] | None,
    *,
    lang: str,
) -> dict[str, Any] | None:
    html_sync = (ctx_data or {}).get("html_sync") or {}
    if not isinstance(html_sync, dict):
        return None
    payload = html_sync.get(lang)
    return copy.deepcopy(payload) if isinstance(payload, dict) else None


def extract_payload_for_lang(
    ctx_data: dict[str, Any] | None,
    *,
    lang: str,
    baseline_lang: str,
    fallback_payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if lang == baseline_lang:
        payload = (ctx_data or {}).get("baseline_payload") or fallback_payload
    else:
        payload = ((ctx_data or {}).get("translations") or {}).get(lang)
    return copy.deepcopy(payload) if isinstance(payload, dict) else None


def extract_stored_quote_document(
    ctx_data: dict[str, Any] | None,
    *,
    lang: str,
) -> dict[str, Any] | None:
    quote_documents = (ctx_data or {}).get("quoteDocuments") or {}
    if isinstance(quote_documents, dict) and isinstance(quote_documents.get(lang), dict):
        return copy.deepcopy(quote_documents[lang])

    brochure_drafts = (ctx_data or {}).get("brochureDrafts") or {}
    if isinstance(brochure_drafts, dict) and isinstance(brochure_drafts.get(lang), dict):
        return copy.deepcopy(brochure_drafts[lang])

    single_quote_document = (ctx_data or {}).get("quoteDocument")
    if isinstance(single_quote_document, dict) and (ctx_data or {}).get("quoteDocumentLang") == lang:
        return copy.deepcopy(single_quote_document)

    single_brochure_draft = (ctx_data or {}).get("brochureDraft")
    if isinstance(single_brochure_draft, dict) and (ctx_data or {}).get("brochureDraftLang") == lang:
        return copy.deepcopy(single_brochure_draft)

    return None


def normalize_document_for_migration(
    document_json: dict[str, Any],
    *,
    quotation_id: str,
    lang: str,
    template_name: str,
    brand_id: str,
    current_version: int,
) -> dict[str, Any]:
    # This is an explicit artifact-migration boundary.  Runtime adapters reject
    # pre-cutover documents; migration is the only place where legacy rich
    # fields are translated into strict canonical blocks.
    source = copy.deepcopy(document_json)
    source["content"] = build_rich_content_from_legacy(source)
    source = strip_legacy_rich_document_fields(source)
    source.setdefault("meta", {})["contentSchemaVersion"] = 1
    normalized = normalize_quote_document(
        source,
        quotation_id,
        lang,
        template_name=template_name,
        brand_id=brand_id,
    )
    meta = normalized.setdefault("meta", {})
    meta["quotationId"] = quotation_id
    meta["lang"] = lang
    meta["brandId"] = brand_id
    meta["template"] = template_name
    meta["revision"] = 1
    meta["version"] = max(first_int(meta.get("version"), default=1), current_version, 1)
    meta["status"] = "draft"
    return normalized


def hydrate_canonical_document(
    document_json: dict[str, Any],
    *,
    quotation_id: str,
    lang: str,
    template_name: str,
    brand_id: str,
    opportunity_id: str | None,
    revision: int,
    version: int,
) -> dict[str, Any]:
    hydrated = copy.deepcopy(document_json)
    meta = hydrated.setdefault("meta", {})
    meta["quotationId"] = quotation_id
    meta["lang"] = lang
    meta["template"] = template_name
    meta["brandId"] = brand_id
    if opportunity_id:
        meta["opportunityId"] = opportunity_id
    meta["revision"] = revision
    meta["version"] = max(first_int(meta.get("version"), default=1), version, 1)
    return hydrated


def build_document_from_legacy_payload(
    *,
    quotation_id: str,
    lang: str,
    baseline_lang: str,
    ctx_data: dict[str, Any],
    payload_dict: dict[str, Any],
    template_name: str,
) -> dict[str, Any]:
    import main

    payload_obj = main.TourQuotationPayload.model_validate(payload_dict)
    brand_config = copy.deepcopy((ctx_data.get("brand") if isinstance(ctx_data.get("brand"), dict) else None) or {})
    resolved_brand = main.resolve_brand(None, payload_dict)
    if not brand_config:
        brand_config = copy.deepcopy(resolved_brand)
    else:
        brand_config.setdefault("id", resolved_brand.get("id") or "vietnam_safar")
        for key, value in resolved_brand.items():
            brand_config.setdefault(key, value)

    hero_image_url = ctx_data.get("hero_img") or ctx_data.get("img_0") or main._default_brand_logo(brand_config)
    legacy_ctx = main._build_ctx(
        quotation_id=quotation_id,
        payload=payload_obj,
        hero_image_url=hero_image_url,
        destinations=ctx_data.get("destinations", []),
        lang=lang,
        template_name=template_name,
        brand=brand_config,
    )
    legacy_ctx["brand"] = brand_config
    if ctx_data.get("designer_img"):
        legacy_ctx["designer_img"] = ctx_data.get("designer_img")
    if ctx_data.get("hero_img"):
        legacy_ctx["hero_img_custom"] = ctx_data.get("hero_img")
        legacy_ctx["img_0"] = ctx_data.get("hero_img")
    elif hero_image_url:
        legacy_ctx["hero_img_custom"] = hero_image_url
        legacy_ctx["img_0"] = hero_image_url
    if ctx_data.get("img_itinerary_divider"):
        legacy_ctx["img_itinerary_divider"] = ctx_data.get("img_itinerary_divider")
    if ctx_data.get("img_hotel_divider"):
        legacy_ctx["img_hotel_divider"] = ctx_data.get("img_hotel_divider")
    legacy_ctx["translations"] = copy.deepcopy(ctx_data.get("translations", {}))
    legacy_ctx["baseline_lang"] = baseline_lang
    legacy_ctx["translation_status"] = extract_translation_status(
        ctx_data,
        baseline_lang=baseline_lang,
        available_langs=extract_available_langs(ctx_data, baseline_lang=baseline_lang),
    )
    main._apply_ctx_html_sync(legacy_ctx, ctx_data, lang, baseline_lang)
    return main._build_brochure_draft_from_lang_ctx(legacy_ctx, quotation_id, lang)
