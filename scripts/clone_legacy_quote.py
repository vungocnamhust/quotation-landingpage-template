import argparse
import copy
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_API_URL = "http://localhost:8111/quotations"
DEFAULT_TEMPLATE = "prototype_itinerary_imagery.html"
ASSET_PREFIX = "/assets/"
ROOT_STYLE_URL_RE = re.compile(r"(?P<name>--[\w-]+)\s*:\s*url\((?P<quote>['\"]?)(?P<url>.*?)(?P=quote)\)")
VERSIONED_HTML_RE = re.compile(r"^v(\d+)\.html$")

BRAND_COMPANY_NAMES = {
    "capella_travel": "Capella Travel",
    "selvara": "Selvara",
    "vietnam_safar": "Vietnam Safar",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _is_data_url(url: str | None) -> bool:
    return bool(url and url.strip().startswith("data:"))


def _split_url(url: str) -> tuple[str, str]:
    if not url:
        return "", ""
    for separator in ("?", "#"):
        if separator in url:
            index = url.index(separator)
            return url[:index], url[index:]
    return url, ""


def _normalize_asset_url(url: str) -> str:
    if not url or _is_data_url(url) or not url.startswith(ASSET_PREFIX):
        return url

    clean_url, suffix = _split_url(url)
    asset_path = BASE_DIR / clean_url.lstrip("/")
    if asset_path.exists():
        return url

    parent_dir = asset_path.parent
    if not parent_dir.exists():
        return url

    candidates = sorted(
        child for child in parent_dir.iterdir()
        if child.is_file() and not child.name.startswith(".")
    )
    if not candidates:
        return url

    desired_ext = asset_path.suffix.lower()
    same_ext = [child for child in candidates if child.suffix.lower() == desired_ext]
    preferred_pool = same_ext or candidates

    folder_name = parent_dir.name.lower()
    folder_matches = [
        child for child in preferred_pool
        if child.stem.lower().startswith(f"{folder_name}_")
    ]
    chosen = folder_matches[0] if folder_matches else preferred_pool[0]
    normalized = "/" + chosen.relative_to(BASE_DIR).as_posix()
    return f"{normalized}{suffix}"


def _normalize_ctx_assets(ctx_data: dict) -> dict:
    normalized = copy.deepcopy(ctx_data)
    for field in ("hero_img", "designer_img", "img_itinerary_divider", "img_hotel_divider"):
        if normalized.get(field) and not _is_data_url(normalized[field]):
            normalized[field] = _normalize_asset_url(normalized[field])

    for hotel in normalized.get("hotels") or []:
        for field in ("hotel_img", "room_img"):
            if hotel.get(field) and not _is_data_url(hotel[field]):
                hotel[field] = _normalize_asset_url(hotel[field])
    return normalized


def _replace_inner_html(tag, html_fragment: str) -> None:
    if "<" not in (html_fragment or "") and ">" not in (html_fragment or ""):
        tag.clear()
        tag.append(html_fragment or "")
        return
    fragment = BeautifulSoup(html_fragment or "", "html.parser")
    tag.clear()
    for node in list(fragment.contents):
        tag.append(node)


def _extract_room_type(hotel_arrangement: str) -> str:
    match = re.search(r"\(([^()]+)\)\s*$", hotel_arrangement or "")
    return match.group(1).strip() if match else ""


def _extract_visible_editables(source_html: str) -> dict[str, dict]:
    soup = BeautifulSoup(source_html, "html.parser")
    records: dict[str, dict] = {}
    for element in soup.select("[data-editable]"):
        key = (element.get("data-editable") or "").strip()
        if not key:
            continue
        records[key] = {
            "tag": element.name,
            "html": element.decode_contents(),
            "src": element.get("src"),
            "style": element.get("style"),
        }
    return records


def _extract_root_style_urls(source_html: str) -> dict[str, str]:
    html_tag = BeautifulSoup(source_html, "html.parser").find("html")
    style_text = html_tag.get("style", "") if html_tag else ""
    return {
        match.group("name"): match.group("url")
        for match in ROOT_STYLE_URL_RE.finditer(style_text)
    }


def _set_css_url(style_text: str, prop_name: str, url: str) -> str:
    style_text = style_text or ""
    replacement = f"{prop_name}: url('{url}')"
    pattern = re.compile(rf"{re.escape(prop_name)}\s*:\s*url\((['\"]?).*?\1\)")
    if pattern.search(style_text):
        return pattern.sub(replacement, style_text)
    suffix = "" if not style_text.strip() or style_text.strip().endswith(";") else ";"
    return f"{style_text}{suffix} {replacement};".strip()


def _latest_versioned_html_path(quote_dir: Path) -> Path:
    candidates: list[tuple[int, Path]] = []
    for path in quote_dir.iterdir():
        if not path.is_file():
            continue
        match = VERSIONED_HTML_RE.match(path.name)
        if not match:
            continue
        candidates.append((int(match.group(1)), path))
    if not candidates:
        raise FileNotFoundError(f"No versioned HTML snapshot found in {quote_dir}")
    return max(candidates, key=lambda item: item[0])[1]


def _select_source_html_path(quote_dir: Path, explicit_version: int | None = None) -> Path:
    if explicit_version is None:
        return _latest_versioned_html_path(quote_dir)
    path = quote_dir / f"v{explicit_version}.html"
    if not path.exists():
        raise FileNotFoundError(f"Missing source HTML snapshot: {path}")
    return path


def _resolve_brand_company_name(target_brand: str | None, payload: dict) -> str | None:
    if target_brand:
        return BRAND_COMPANY_NAMES.get(target_brand)
    seller = payload.get("seller") or {}
    company_name = seller.get("companyName")
    return company_name if isinstance(company_name, str) and company_name.strip() else None


def build_payload(
    source_payload: dict,
    source_ctx: dict,
    target_template: str,
    target_brand: str | None = None,
    target_contact_name: str | None = None,
) -> dict:
    payload = copy.deepcopy(source_payload)
    payload["template_name"] = target_template
    payload["template"] = target_template

    seller = copy.deepcopy(payload.get("seller") or {})
    company_name = _resolve_brand_company_name(target_brand, payload)
    if company_name:
        seller["companyName"] = company_name
    if target_contact_name:
        seller["contactName"] = target_contact_name
    if seller:
        payload["seller"] = seller

    designer_img = source_ctx.get("designer_img")
    if designer_img and not _is_data_url(designer_img):
        payload["designer_img"] = _normalize_asset_url(designer_img)
    return payload


def _patch_local_ctx(quotation_id: str, source_ctx: dict) -> None:
    ctx_path = BASE_DIR / "published" / quotation_id / "ctx.json"
    if not ctx_path.exists():
        return

    ctx_data = _load_json(ctx_path)
    normalized_source_ctx = _normalize_ctx_assets(source_ctx)

    for field in ("hero_img", "designer_img", "img_itinerary_divider", "img_hotel_divider"):
        source_value = normalized_source_ctx.get(field)
        if source_value and not _is_data_url(source_value):
            ctx_data[field] = source_value

    source_hotels = normalized_source_ctx.get("hotels") or []
    target_hotels = ctx_data.get("hotels") or []
    for source_hotel, target_hotel in zip(source_hotels, target_hotels):
        for field in ("hotel_img", "room_img"):
            source_value = source_hotel.get(field)
            if source_value and not _is_data_url(source_value):
                target_hotel[field] = source_value

    ctx_path.write_text(json.dumps(ctx_data, ensure_ascii=False, indent=2), encoding="utf-8")


def _clone_html_style_urls(style_text: str) -> str:
    if not style_text or "url(" not in style_text:
        return style_text

    def replace(match: re.Match) -> str:
        quote = match.group(1) or ""
        url = match.group(2) or ""
        if _is_data_url(url):
            return match.group(0)
        normalized = _normalize_asset_url(url)
        return f"url({quote}{normalized}{quote})"

    return re.sub(r"url\((['\"]?)(.*?)\1\)", replace, style_text)


def _clone_media_editable(target_element, record: dict) -> None:
    src = record.get("src")
    style = record.get("style") or ""
    html = record.get("html") or ""

    if src and not _is_data_url(src):
        target_element["src"] = _normalize_asset_url(src)
        return

    if "data:" in html or "data:" in style:
        return

    if style:
        target_element["style"] = _clone_html_style_urls(style)
    if html:
        _replace_inner_html(target_element, html)


def clone_source_overrides_to_target_html(
    target_html: str,
    source_html: str,
    source_ctx: dict,
    source_payload: dict,
) -> str:
    target_soup = BeautifulSoup(target_html, "html.parser")
    source_records = _extract_visible_editables(source_html)
    source_root_urls = _extract_root_style_urls(source_html)
    target_keys = {
        (element.get("data-editable") or "").strip()
        for element in target_soup.select("[data-editable]")
    }

    html_tag = target_soup.find("html")
    if html_tag:
        style_text = html_tag.get("style", "")
        for name, url in source_root_urls.items():
            if (name == "--hero-img" or name.startswith("--img-")) and not _is_data_url(url):
                style_text = _set_css_url(style_text, name, _normalize_asset_url(url))
        html_tag["style"] = style_text

    for key, record in source_records.items():
        if key not in target_keys:
            continue
        element = target_soup.select_one(f'[data-editable="{key}"]')
        if element is None:
            continue

        if element.name == "img" or key.startswith("day_img_") or key in {"designer_img"}:
            _clone_media_editable(element, record)
            continue

        _replace_inner_html(element, record.get("html", ""))

    seller_name2 = BeautifulSoup(source_html, "html.parser").select_one('[data-editable="seller_name2"]')
    seller_subtitle = ""
    if seller_name2:
        subtitle_node = seller_name2.find("div")
        seller_subtitle = subtitle_node.get_text(" ", strip=True) if subtitle_node else ""
    if seller_subtitle and "seller_subtitle" in target_keys:
        element = target_soup.select_one('[data-editable="seller_subtitle"]')
        if element is not None:
            _replace_inner_html(element, seller_subtitle)

    source_hotels = (_normalize_ctx_assets(source_ctx).get("hotels") or [])
    hotel_plan = ((source_payload.get("hotelPlan") or {}).get("hotels") or [])
    for index, hotel in enumerate(source_hotels, start=1):
        hotel_img = target_soup.select_one(f'[data-editable="hotel_img_{index}"]')
        if hotel_img and hotel.get("hotel_img") and not _is_data_url(hotel["hotel_img"]):
            hotel_img["src"] = hotel["hotel_img"]

        room_img = target_soup.select_one(f'[data-editable="hotel_room_img_{index}"]')
        if room_img and hotel.get("room_img") and not _is_data_url(hotel["room_img"]):
            room_img["src"] = hotel["room_img"]

        room_type_el = target_soup.select_one(f'[data-editable="hotel_room_type_{index}"]')
        if room_type_el and index - 1 < len(hotel_plan):
            room_type = _extract_room_type(hotel_plan[index - 1].get("hotelArrangement", ""))
            if room_type:
                _replace_inner_html(room_type_el, room_type)

    return str(target_soup)


def _fetch_target_html(quotation_id: str, web_base_url: str, target_brand: str | None) -> str:
    query = urlencode({"brand": target_brand}) if target_brand else ""
    url = f"{web_base_url}/quotations/{quotation_id}"
    if query:
        url = f"{url}?{query}"
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    return response.text


def _publish_html(quotation_id: str, web_base_url: str, html: str, lang: str) -> dict:
    response = requests.post(
        f"{web_base_url}/quotations/{quotation_id}/publish?lang={lang}",
        json={"html": html},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clone a legacy quotation into a fresh quote using the current itinerary imagery template.",
    )
    parser.add_argument("--source-quote-id", required=True, help="Existing legacy quote id, e.g. quo_2fe22ee6b227")
    parser.add_argument("--source-version", type=int, help="Optional source HTML snapshot version, defaults to latest v*.html")
    parser.add_argument("--api-url", default=os.getenv("QUOTATION_API_URL", DEFAULT_API_URL))
    parser.add_argument("--target-template", default=DEFAULT_TEMPLATE)
    parser.add_argument("--target-brand", help="Brand query param to use when previewing/publishing the new quote")
    parser.add_argument("--target-contact-name", help="Optional seller contact name override")
    parser.add_argument("--lang", default="en", choices=("en", "vi", "ar"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    web_base_url = args.api_url.rsplit("/quotations", 1)[0]

    source_quote_dir = BASE_DIR / "published" / args.source_quote_id
    source_payload_path = source_quote_dir / "payload.json"
    source_ctx_path = source_quote_dir / "ctx.json"
    source_html_path = _select_source_html_path(source_quote_dir, args.source_version)

    source_payload = _load_json(source_payload_path)
    source_ctx = _load_json(source_ctx_path)
    source_html = _load_text(source_html_path)
    payload = build_payload(
        source_payload=source_payload,
        source_ctx=source_ctx,
        target_template=args.target_template,
        target_brand=args.target_brand,
        target_contact_name=args.target_contact_name,
    )

    create_url = args.api_url
    if args.target_brand:
        create_url = f"{create_url}?{urlencode({'brand': args.target_brand})}"

    print(
        f"Creating new quote from source '{args.source_quote_id}' "
        f"using snapshot '{source_html_path.name}' and template '{args.target_template}'..."
    )
    create_response = requests.post(create_url, json=payload, timeout=120)
    create_response.raise_for_status()
    create_data = create_response.json()
    quotation_id = create_data.get("quotationId")
    if not quotation_id:
        raise RuntimeError(f"Unexpected create response: {json.dumps(create_data, ensure_ascii=False)}")

    _patch_local_ctx(quotation_id, source_ctx)
    target_html = _fetch_target_html(quotation_id, web_base_url, args.target_brand)
    merged_html = clone_source_overrides_to_target_html(
        target_html=target_html,
        source_html=source_html,
        source_ctx=source_ctx,
        source_payload=source_payload,
    )
    publish_data = _publish_html(quotation_id, web_base_url, merged_html, args.lang)
    _patch_local_ctx(quotation_id, source_ctx)

    preview_url = f"{web_base_url}/quotations/{quotation_id}"
    if args.target_brand:
        preview_url = f"{preview_url}?{urlencode({'brand': args.target_brand})}"

    print(json.dumps({
        "sourceQuoteId": args.source_quote_id,
        "newQuotationId": quotation_id,
        "previewUrl": preview_url,
        "publish": publish_data,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
