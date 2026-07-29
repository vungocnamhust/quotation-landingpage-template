import copy
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
SOURCE_QUOTE_ID = "quo_d8bbe1c59a8a"
SOURCE_QUOTE_DIR = BASE_DIR / "published" / SOURCE_QUOTE_ID
SOURCE_PAYLOAD_PATH = SOURCE_QUOTE_DIR / "payload.json"
SOURCE_CTX_PATH = SOURCE_QUOTE_DIR / "ctx.json"
SOURCE_HTML_PATH = SOURCE_QUOTE_DIR / "v27.html"

URL = os.getenv("QUOTATION_API_URL", "http://localhost:8111/quotations")
WEB_BASE_URL = URL.rsplit("/quotations", 1)[0]
TARGET_TEMPLATE = "prototype_itinerary_imagery.html"
TARGET_BRAND = "capella_travel"
TARGET_CONTACT_NAME = "Eddie"

ROOT_STYLE_URL_RE = re.compile(r"(?P<name>--[\w-]+)\s*:\s*url\((?P<quote>['\"]?)(?P<url>.*?)(?P=quote)\)")
HOTEL_ROOM_RE = re.compile(r"\(([^()]+)\)\s*$")
ASSET_PREFIX = "/assets/"
JSON_SCRIPT_IDS = (
    "itinerary-data",
    "route-stops-data",
    "stay-segments-data",
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _replace_inner_html(tag, html_fragment: str) -> None:
    if "<" not in (html_fragment or "") and ">" not in (html_fragment or ""):
        tag.clear()
        tag.append(html_fragment or "")
        return
    fragment = BeautifulSoup(html_fragment or "", "html.parser")
    tag.clear()
    for node in list(fragment.contents):
        tag.append(node)


def _split_url(url: str) -> tuple[str, str]:
    if not url:
        return "", ""
    for separator in ("?", "#"):
        if separator in url:
            index = url.index(separator)
            return url[:index], url[index:]
    return url, ""


def _normalize_asset_url(url: str) -> str:
    if not url or not url.startswith(ASSET_PREFIX):
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
        if normalized.get(field):
            normalized[field] = _normalize_asset_url(normalized[field])

    for hotel in normalized.get("hotels") or []:
        for field in ("hotel_img", "room_img"):
            if hotel.get(field):
                hotel[field] = _normalize_asset_url(hotel[field])
    return normalized


def _extract_room_type(hotel_arrangement: str) -> str:
    match = HOTEL_ROOM_RE.search(hotel_arrangement or "")
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


def _extract_json_scripts(source_html: str) -> dict[str, str]:
    soup = BeautifulSoup(source_html, "html.parser")
    scripts: dict[str, str] = {}
    for script_id in JSON_SCRIPT_IDS:
        element = soup.find("script", id=script_id)
        if element is not None:
            scripts[script_id] = element.string if element.string is not None else element.get_text()
    return scripts


def _set_css_url(style_text: str, prop_name: str, url: str) -> str:
    style_text = style_text or ""
    replacement = f"{prop_name}: url('{url}')"
    pattern = re.compile(rf"{re.escape(prop_name)}\s*:\s*url\((['\"]?).*?\1\)")
    if pattern.search(style_text):
        return pattern.sub(replacement, style_text)
    suffix = "" if not style_text.strip() or style_text.strip().endswith(";") else ";"
    return f"{style_text}{suffix} {replacement};".strip()


def _patch_local_ctx_assets(quotation_id: str, source_ctx: dict, source_html: str | None = None) -> None:
    ctx_path = BASE_DIR / "published" / quotation_id / "ctx.json"
    if not ctx_path.exists():
        return

    ctx_data = _load_json(ctx_path)
    normalized_source_ctx = _normalize_ctx_assets(source_ctx)
    source_records = _extract_visible_editables(source_html) if source_html else {}
    for field in ("hero_img", "designer_img", "img_itinerary_divider", "img_hotel_divider"):
        if normalized_source_ctx.get(field):
            ctx_data[field] = normalized_source_ctx[field]
    hotel_divider_record = source_records.get("img_hotel_divider") or {}
    if hotel_divider_record.get("src"):
        ctx_data["img_hotel_divider"] = _normalize_asset_url(hotel_divider_record["src"])
    ctx_path.write_text(json.dumps(ctx_data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_payload() -> dict:
    source_payload = _load_json(SOURCE_PAYLOAD_PATH)
    source_ctx = _normalize_ctx_assets(_load_json(SOURCE_CTX_PATH))
    payload = copy.deepcopy(source_payload)

    payload["template_name"] = TARGET_TEMPLATE
    payload["quotationNumber"] = (
        payload.get("quotationNumber")
        or source_ctx.get("quotation_number")
        or "VN-2027-LUX"
    )
    payload["seller"] = {
        "companyName": "Capella Travel",
        "contactName": TARGET_CONTACT_NAME,
        "email": "sales@capellatravel.com",
        "phone": "+84 913 393 119",
        "website": "https://capellatravel.com",
    }
    payload["designer_img"] = source_ctx.get("designer_img") or "/assets/dias_team/hieu.jpg"

    payload["inclusions"] = [
        "Private airport transfer, International arrival fast-track assistance and Vietnam visa services",
        "All private transfer with english-speaking guides mentioned in the itinerary",
        "Experiences, admission fee, and exclusive arrangements throughout the journey of Hanoi, Ha Long, Hoi An, Da Nang, Hue, Ho Chi Minh City",
        "All meals mentioned in the itinerary",
        "Domestic flights"
    ]
    payload["exclusions"] = [
        "International flights",
        "Travel insurance",
        "Personal expenses",
        "Optional experiences not specified in the itinerary",
        "Tips and gratuities",
        "Any services not expressly listed as included"
    ]
    payload["inclusions_lede"] = "Your journey has been thoughtfully arranged to ensure a seamless and comfortable experience throughout."
    payload["exclusions_lede"] = "To keep your journey transparent and clearly defined, the following are not included unless specifically stated otherwise:"

    itinerary = payload.setdefault("itinerary", [])
    for day in itinerary:
        if day.get("destination") == "Ninh Binh":
            day["destination"] = "Hanoi"
            day["summary"] = "Enjoy a flexible day in Hanoi to further explore at your own pace. Wander through the Old Quarter's hidden alleys, discover local artisanal crafts, or simply relax at your luxury accommodation. A private vehicle and guide remain at your disposal for any spontaneous excursions."
            day["mainInclusions"] = "Private guide and vehicle at disposal."
            day["senseOfPace"] = "Relaxed"

    payload.setdefault("candidateBlocks", [])
    return payload


def _normalize_stay_segments_json(raw_text: str) -> str:
    segments = json.loads(raw_text or "[]")
    if not isinstance(segments, list):
        return raw_text
    
    new_segments = []
    for segment in segments:
        city = (segment.get("city") or "").lower().strip()
        display_name = (segment.get("displayName") or "").lower().strip()
        if "ninh binh" in city or "ninh binh" in display_name or segment.get("segmentId") == "stay-2":
            continue

        if not display_name or display_name == "\\n" or city == "departure" or display_name == "departure":
            continue
        
        if "hanoi" in city or "hanoi" in display_name or segment.get("segmentId") == "stay-1":
            segment["dayEnd"] = 3
            segment["daysLabel"] = "DAYS 1-3"
            segment["mapSegmentDuration"] = "DAYS 1-3 • 3 NIGHTS"
            
        if segment.get("transportFromPrevious") == "Ninh Binh → Halong Bay":
            segment["transportFromPrevious"] = "Hanoi → Halong Bay"
            
        hotel_image = segment.get("hotelImage")
        if hotel_image:
            segment["hotelImage"] = _normalize_asset_url(hotel_image)
        segment["activityPreviews"] = []
        new_segments.append(segment)
        
    for idx, seg in enumerate(new_segments, start=1):
        seg["order"] = idx
        seg["segmentId"] = f"stay-{idx}"

    return json.dumps(new_segments, ensure_ascii=False, separators=(",", ":"))


def _normalize_route_stops_json(raw_text: str) -> str:
    stops = json.loads(raw_text or "[]")
    if not isinstance(stops, list):
        return raw_text
    for stop in stops:
        if stop.get("dayNumber") == 3 or (stop.get("destination") or "").lower() == "ninh binh":
            stop["destination"] = "Hanoi"
            stop["displayName"] = "Hanoi"
            stop["mapTitle"] = "Day 3 — Hanoi"
            stop["kind"] = "overnight"
    return json.dumps(stops, ensure_ascii=False, separators=(",", ":"))


def _normalize_itinerary_json(raw_text: str) -> str:
    items = json.loads(raw_text or "[]")
    if not isinstance(items, list):
        return raw_text
    for item in items:
        if item.get("dayNumber") == 3 or "Ninh Binh" in item.get("destinations", []):
            item["destinations"] = ["Hanoi"]
            item["title"] = "Day 3 — Hanoi"
            item["overnight"] = "Hanoi"
            item["activities"] = ["Private guide and vehicle at disposal."]
            item["notes"] = ["Sense of Pace: Relaxed"]
            item["meals"] = ["Breakfast, Lunch, Dinner"]
            item["description"] = [
                "Enjoy a flexible day in Hanoi to further explore at your own pace. Wander through the Old Quarter's hidden alleys, discover local artisanal crafts, or simply relax at your luxury accommodation. A private vehicle and guide remain at your disposal for any spontaneous excursions."
            ]
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"))


def _clone_source_overrides_to_target_html(
    target_html: str,
    source_html: str,
    source_ctx: dict,
    source_payload: dict,
) -> str:
    target_soup = BeautifulSoup(target_html, "html.parser")
    source_records = _extract_visible_editables(source_html)
    source_root_urls = _extract_root_style_urls(source_html)
    source_json_scripts = _extract_json_scripts(source_html)
    target_keys = {
        (element.get("data-editable") or "").strip()
        for element in target_soup.select("[data-editable]")
    }

    html_tag = target_soup.find("html")
    if html_tag:
        style_text = html_tag.get("style", "")
        for name, url in source_root_urls.items():
            if name == "--hero-img" or name.startswith("--img-"):
                style_text = _set_css_url(style_text, name, url)
        html_tag["style"] = style_text

    for key, record in source_records.items():
        if key not in target_keys:
            continue
        element = target_soup.select_one(f'[data-editable="{key}"]')
        if element is None:
            continue

        if key == "designer_img":
            image_url = _normalize_asset_url(source_ctx.get("designer_img"))
            style_text = element.get("style", "")
            if image_url:
                style_text = _set_css_url(style_text, "--designer-img", image_url)
                style_text = _set_css_url(style_text, "background-image", image_url)
                element["style"] = style_text
            continue

        if element.name == "img":
            if record.get("src"):
                element["src"] = _normalize_asset_url(record["src"])
            continue

        if key.startswith("day_img_"):
            # We skip cloning from source_html because we will inject a hardcoded array of images below.
            continue

        _replace_inner_html(element, record.get("html", ""))

    DAY_IMAGES = [
        ['/assets/ha-noi/hero/hero1.jpg', '/assets/ha-noi/hero/hero2.webp'],
        ['/assets/ha-noi/hero/hero3.jpg'],
        ['/assets/ha-noi/hero/hero4.jpg', '/assets/ha-noi/hero/hero5.jpg'],
        ['/assets/quang-ninh/hero/hero5.jpg', '/assets/quang-ninh/hero/hero2.jpg', '/assets/quang-ninh/hero/hero1.jpg'],
        ['/assets/quang-nam/hero/hero1.jpg', '/assets/quang-nam/hoian2.jpg'],
        ['/assets/quang-nam/myson.jpg', '/assets/quang-nam/hoian1.jpg', '/assets/quang-nam/thuyen-thung.jpg'],
        ['/assets/quang-nam/hoian3.jpg', '/assets/quang-nam/hero/hero3.jpg'],
        ['/assets/da-nang/hero/hero3.jpg', '/assets/da-nang/hero/hero4.jpg', '/assets/da-nang/hero/hero1.jpg'],
        ['/assets/da-nang/danang2.jpg', '/assets/da-nang/danang3.jpg', '/assets/da-nang/danang1.jpg'],
        ['/assets/thua-thien-hue/hero/hero3.webp', '/assets/thua-thien-hue/hero/hero1.jpg', '/assets/thua-thien-hue/hue1.jpg', '/assets/thua-thien-hue/hero/hero2.jpg'],
        ['/assets/da-nang/dn-beach1.jpg', '/assets/da-nang/hyatt-regency-danang-resort-spa-3.jpg'],
        ['/assets/ho-chi-minh/hero/hero2.jpg', '/assets/ho-chi-minh/hero/hero4.jpg'],
        ['/assets/mekong/pexels-quang-nguyen-vinh-222549-8280885.jpg', '/assets/mekong/hero/hero2.jpg'],
        ['/assets/ho-chi-minh/hero/hero1.jpg'],
    ]

    for key in target_keys:
        if key.startswith("day_img_"):
            match = re.search(r"day_img_(?:carousel|hero)_(\d+)", key)
            if not match:
                continue
            day_idx = int(match.group(1)) - 1
            if day_idx < 0 or day_idx >= len(DAY_IMAGES):
                continue

            images = DAY_IMAGES[day_idx].copy()
            if len(images) > 3:
                images = images[:3]
            elif len(images) < 3:
                while len(images) < 3:
                    images.append(images[-1])
                    
            element = target_soup.select_one(f'[data-editable="{key}"]')
            if element is None:
                continue

            classes = element.get("class", [])
            if "carousel-container" not in classes:
                element["class"] = classes + ["carousel-container"]
            
            style_text = element.get("style", "")
            style_text = re.sub(r"(?:background-image|--image)\s*:\s*url\((['\"]?)(.*?)\1\);?", "", style_text).strip()
            if "overflow" not in style_text:
                style_text += " overflow: hidden;"
            if "position" not in style_text:
                style_text += " position: relative;"
            if "border-radius" not in style_text:
                style_text += " border-radius: 4px;"
            element["style"] = style_text.strip()

            slides_html = ""
            for img in images:
                normalized_img = _normalize_asset_url(img)
                slides_html += f"""<div class="carousel-slide" style="flex: 0 0 100%; height: 100%; background: url('{normalized_img}') center/cover no-repeat;"></div>"""
            
            inner_html = f"""<div class="carousel-inner" style="position: absolute; inset: 0px; display: flex; transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); transform: translateX(0%);">{slides_html}</div>"""
            _replace_inner_html(element, inner_html)

            # Ensure buttons exist for the carousel
            parent = element.parent
            if parent:
                has_buttons = parent.find("button", class_="carousel-control")
                if not has_buttons:
                    btn_prev = BeautifulSoup("""<button aria-label="Previous image" class="carousel-control prev no-print" style="position: absolute; left: -20px; top: 50%; transform: translateY(-50%); width: 44px; height: 44px; border-radius: 50%; border: 1px solid rgba(0,0,0,0.06); background: #ffffff; color: #333; cursor: pointer; display: flex; align-items: center; justify-content: center; z-index: 3; font-size: 20px; line-height: 1; transition: background 0.2s, opacity 0.2s; box-shadow: 0 4px 14px rgba(0,0,0,0.1); padding-bottom: 2px;">‹</button>""", "html.parser").button
                    btn_next = BeautifulSoup("""<button aria-label="Next image" class="carousel-control next no-print" style="position: absolute; right: -20px; top: 50%; transform: translateY(-50%); width: 44px; height: 44px; border-radius: 50%; border: 1px solid rgba(0,0,0,0.06); background: #ffffff; color: #333; cursor: pointer; display: flex; align-items: center; justify-content: center; z-index: 3; font-size: 20px; line-height: 1; transition: background 0.2s, opacity 0.2s; box-shadow: 0 4px 14px rgba(0,0,0,0.1); padding-bottom: 2px;">›</button>""", "html.parser").button
                    parent.append(btn_prev)
                    parent.append(btn_next)

    # Old template stored seller subtitle inside seller_name2.
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
        if hotel_img and hotel.get("hotel_img"):
            hotel_img["src"] = hotel["hotel_img"]

        room_img = target_soup.select_one(f'[data-editable="hotel_room_img_{index}"]')
        if room_img and hotel.get("room_img"):
            room_img["src"] = hotel["room_img"]

        room_type_el = target_soup.select_one(f'[data-editable="hotel_room_type_{index}"]')
        if room_type_el and index - 1 < len(hotel_plan):
            room_type = _extract_room_type(hotel_plan[index - 1].get("hotelArrangement", ""))
            if room_type:
                _replace_inner_html(room_type_el, room_type)

    for script_id, raw_text in source_json_scripts.items():
        target_script = target_soup.find("script", id=script_id)
        if target_script is None:
            continue
        if script_id == "stay-segments-data":
            target_script.string = _normalize_stay_segments_json(raw_text)
        elif script_id == "route-stops-data":
            target_script.string = _normalize_route_stops_json(raw_text)
        elif script_id == "itinerary-data":
            target_script.string = _normalize_itinerary_json(raw_text)
        else:
            target_script.string = raw_text

    # Preserve source divider and designer assets in the published HTML.
    itinerary_divider_url = _normalize_asset_url(source_ctx.get("img_itinerary_divider"))
    if itinerary_divider_url:
        section = target_soup.select_one("#divider-itinerary")
        if section is not None:
            section["style"] = _set_css_url(section.get("style", ""), "background-image", itinerary_divider_url)

    hotel_divider_url = None
    hotel_divider_record = source_records.get("img_hotel_divider") or {}
    if hotel_divider_record.get("src"):
        hotel_divider_url = _normalize_asset_url(hotel_divider_record["src"])
    elif source_ctx.get("img_hotel_divider"):
        hotel_divider_url = _normalize_asset_url(source_ctx.get("img_hotel_divider"))
    # Final cleanup of remaining Ninh Binh references in static DOM elements
    sidebar = target_soup.select_one("#map-sidebar")
    if sidebar:
        for item in list(sidebar.select(".timeline-item")):
            title_el = item.select_one(".item-title")
            title_text = title_el.get_text().strip() if title_el else ""
            if not title_text or "ninh binh" in title_text.lower() or title_text.lower() == "departure":
                item.decompose()
            elif title_text.lower() == "hanoi":
                dur = item.select_one(".item-duration")
                if dur:
                    dur.string = "DAYS 1-3 • 3 NIGHTS"

    day3_title = target_soup.select_one('[data-editable="day_title_3"]')
    if day3_title:
        _replace_inner_html(day3_title, "Day 3 — Hanoi")
        if day3_title.parent:
            dest_span = day3_title.parent.select_one(".destination")
            if dest_span:
                dest_span.string = "Hanoi"

    for el in list(target_soup.find_all(string=re.compile(r"Ninh Binh", re.IGNORECASE))):
        parent = el.parent
        if parent and parent.name not in ("script", "style"):
            new_text = re.sub(r"\s*[–-]\s*Ninh Binh", "", el, flags=re.IGNORECASE)
            new_text = re.sub(r"Ninh Binh,\s*", "", new_text, flags=re.IGNORECASE)
            new_text = re.sub(r"Ninh Binh", "Hanoi", new_text, flags=re.IGNORECASE)
            el.replace_with(new_text)

    return str(target_soup)


def _fetch_target_html(quotation_id: str) -> str:
    query = urlencode({"brand": TARGET_BRAND})
    response = requests.get(
        f"{WEB_BASE_URL}/quotations/{quotation_id}?{query}",
        timeout=120,
    )
    response.raise_for_status()
    return response.text


def _publish_html(quotation_id: str, html: str) -> dict:
    response = requests.post(
        f"{WEB_BASE_URL}/quotations/{quotation_id}/publish?lang=en",
        json={"html": html},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    source_payload = _load_json(SOURCE_PAYLOAD_PATH)
    source_ctx = _load_json(SOURCE_CTX_PATH)
    source_html = _load_text(SOURCE_HTML_PATH)
    payload = build_payload()

    print(
        f"Sending POST request to {URL} using source quote '{SOURCE_QUOTE_ID}' "
        f"with template '{TARGET_TEMPLATE}'..."
    )
    try:
        create_response = requests.post(URL, json=payload, timeout=120)
    except requests.exceptions.ConnectionError:
        print(f"Failed to connect to {URL}. Is the server running?")
        return

    print("Response status code:", create_response.status_code)
    try:
        create_data = create_response.json()
    except ValueError:
        print("Response text:", create_response.text)
        return

    print("Response JSON:", json.dumps(create_data, indent=2, ensure_ascii=False))
    quotation_id = create_data.get("quotationId")
    if not quotation_id:
        return

    # Patch local ctx first so PDF render during publish sees the source assets.
    _patch_local_ctx_assets(quotation_id, source_ctx, source_html)

    target_html = _fetch_target_html(quotation_id)
    merged_html = _clone_source_overrides_to_target_html(
        target_html=target_html,
        source_html=source_html,
        source_ctx=source_ctx,
        source_payload=source_payload,
    )
    publish_data = _publish_html(quotation_id, merged_html)
    _patch_local_ctx_assets(quotation_id, source_ctx, source_html)

    print("\nPublish Response:", json.dumps(publish_data, indent=2, ensure_ascii=False))
    print(
        "\n=> Quotation created and replayed from v27 successfully! "
        f"Open: {WEB_BASE_URL}/quotations/{quotation_id}?brand={TARGET_BRAND}"
    )


if __name__ == "__main__":
    main()
