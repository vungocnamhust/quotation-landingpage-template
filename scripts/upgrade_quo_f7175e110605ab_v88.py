"""Create v88 as a minimal extension of the approved v87 quotation.

The legacy quote renderer still uses positional HTML fields.  This upgrade keeps
the approved v87 markup intact and appends only the two requested hotel cards.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main


QUOTE_ID = "quo_f7175e110605ab"
QUOTE_DIR = ROOT / "published" / QUOTE_ID
SOURCE_HTML = QUOTE_DIR / "v87.html"
OUTPUT_HTML = QUOTE_DIR / "v88.html"

HOTELS = [
    ("Hanoi", "2026-09-15", "2026-09-17", "Peridot Grand Luxury Boutique Hotel (Grand Deluxe)"),
    ("Ninh Binh", "2026-09-17", "2026-09-18", "Emeralda Resort Ninh Binh (Deluxe Room)"),
    ("Ha Long", "2026-09-18", "2026-09-19", "Heritage Line Ginger Cruise (Junior Suite)"),
    ("Sapa", "2026-09-19", "2026-09-20", "Chapa Express (Suite Twin Cabin)"),
    ("Sapa", "2026-09-20", "2026-09-22", "Topas Ecolodge (Deluxe Room)"),
    ("Hoi An", "2026-09-22", "2026-09-25", "Anantara Hoi An Resort (Deluxe Balcony)"),
    ("Ho Chi Minh City", "2026-09-25", "2026-09-28", "The Myst Dong Khoi (Deluxe Room)"),
]


def _matching_div_end(content: str, start: int) -> int:
    """Return the character after the div beginning at ``start``."""
    depth = 0
    for match in re.finditer(r"</?div\b[^>]*>", content[start:], re.IGNORECASE):
        tag = match.group(0)
        depth += -1 if tag.startswith("</") else 1
        if depth == 0:
            return start + match.end()
    raise ValueError("Unclosed div in quotation HTML")


def _hotel_cards(content: str) -> list[str]:
    cards: list[str] = []
    marker = 'class="hotel-card-editorial"'
    position = 0
    while True:
        marker_at = content.find(marker, position)
        if marker_at == -1:
            return cards
        start = content.rfind("<div", 0, marker_at)
        end = _matching_div_end(content, start)
        cards.append(content[start:end])
        position = end


def _hotel_container_end(content: str) -> int:
    marker_at = content.find('class="hotel-plan-container"')
    if marker_at == -1:
        raise ValueError("Missing Selected Hotels container in v87")
    start = content.rfind("<div", 0, marker_at)
    return _matching_div_end(content, start)


def _render_current_hotel_cards(ctx: dict) -> list[str]:
    payload = main.TourQuotationPayload.model_validate(ctx["baseline_payload"])
    brand = main.resolve_brand(None, ctx["baseline_payload"])
    render_ctx = main._build_ctx(
        QUOTE_ID,
        payload,
        ctx.get("img_0"),
        ctx.get("destinations", []),
        lang="en",
        template_name="prototype_itinerary_imagery.html",
        brand=brand,
    )
    main._apply_ctx_html_sync(render_ctx, ctx, "en", "en")
    rendered = main.templates.get_template("prototype_itinerary_imagery.html").render(**render_ctx)
    return _hotel_cards(rendered)


def _update_canonical_data(ctx: dict, payload: dict, source_html: str) -> None:
    hotel_plan = {
        "hotels": [
            {
                "destination": destination,
                "checkInDate": check_in,
                "checkOutDate": check_out,
                "hotelArrangement": arrangement,
            }
            for destination, check_in, check_out, arrangement in HOTELS
        ],
        "roomNotes": (payload.get("hotelPlan") or {}).get("roomNotes", ""),
    }
    payload["hotelPlan"] = copy.deepcopy(hotel_plan)
    ctx["baseline_payload"]["hotelPlan"] = copy.deepcopy(hotel_plan)

    sync = ctx.setdefault("html_sync", {}).setdefault("en", {})
    fields = sync.setdefault("edited_fields", {})
    fields.update(
        {
            key: value
            for key, value in main.parse_edited_fields(source_html).items()
            if key.startswith("hotel_")
        }
    )
    fields.update(
        {
            "hotel_name_6": "Anantara Hoi An Resort",
            "hotel_city_6": "HOI AN, VIETNAM",
            "hotel_date_6": "22 - 25 Sep 2026",
            "hotel_room_type_6": "Deluxe Balcony",
            "hotel_name_7": "The Myst Dong Khoi",
            "hotel_city_7": "HO CHI MINH CITY, VIETNAM",
            "hotel_date_7": "25 - 28 Sep 2026",
            "hotel_room_type_7": "Deluxe Room",
        }
    )
    existing = set(sync.get("existing_keys") or [])
    for index in range(1, 8):
        existing.update(
            f"hotel_{field}_{index}"
            for field in ("name", "city", "date", "tel", "intro", "room_type", "img", "room_img")
        )
    sync["existing_keys"] = sorted(existing)


def _verify(content: str) -> None:
    cards = _hotel_cards(content)
    if len(cards) != 7:
        raise ValueError(f"Expected 7 hotel cards, found {len(cards)}")
    required = {
        "Anantara Hoi An Resort",
        "22 - 25 Sep 2026",
        "The Myst Dong Khoi",
        "25 - 28 Sep 2026",
    }
    missing = [value for value in required if value not in content]
    if missing:
        raise ValueError(f"Missing v88 hotel content: {missing}")


def main_entry() -> None:
    source_html = SOURCE_HTML.read_text(encoding="utf-8")
    ctx_path = QUOTE_DIR / "ctx.json"
    payload_path = QUOTE_DIR / "payload.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    _update_canonical_data(ctx, payload, source_html)

    generated_cards = _render_current_hotel_cards(ctx)
    if len(generated_cards) != 7:
        raise ValueError(f"Renderer did not produce 7 hotel cards: {len(generated_cards)}")
    container_end = _hotel_container_end(source_html)
    closing_div_at = source_html.rfind("</div>", 0, container_end)
    if closing_div_at == -1:
        raise ValueError("Missing closing tag for Selected Hotels container")
    v88 = source_html[:closing_div_at] + "\n" + "\n".join(generated_cards[5:]) + "\n" + source_html[closing_div_at:]
    _verify(v88)

    # Capture the actual approved page as the legacy editor's canonical state.
    # This keeps rich Booking Payment Terms and hotel dates available to both
    # refresh renders and PDF renders after future inline saves.
    main._sync_ctx_data_before_publish(ctx, v88, "en", version=88)
    ctx_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_HTML.write_text(v88, encoding="utf-8")


if __name__ == "__main__":
    main_entry()
