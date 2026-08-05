"""Repair the persisted Siem Reap stay segment for quo_f7175e110605ab.

This is an idempotent data migration for the legacy quote state. It aligns the
structured segment, the HTML-sync state, and the cached PDF source so refresh
and a subsequent publish cannot restore the former one-night value.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main


QUOTE_ID = "quo_f7175e110605ab"
QUOTE_DIR = ROOT / "published" / QUOTE_ID
DURATION = "DAYS 14-16 • 2 NIGHTS"


def _repair_segment(segment: dict) -> None:
    segment.update(
        {
            "city": "Siem Reap",
            "displayName": "Siem Reap",
            "dayStart": 14,
            "dayEnd": 16,
            "daysLabel": "DAYS 14-16",
            "nights": 2,
            "nightsLabel": "2 NIGHTS",
            "mapSegmentDuration": DURATION,
        }
    )


def _render(ctx: dict, template_name: str) -> str:
    payload = main.TourQuotationPayload.model_validate(ctx["baseline_payload"])
    lang_ctx = main._build_ctx(
        QUOTE_ID,
        payload,
        ctx.get("img_0"),
        ctx.get("destinations", []),
        lang="en",
        template_name=template_name,
        brand=main.resolve_brand(None, ctx["baseline_payload"]),
    )
    main._apply_ctx_html_sync(lang_ctx, ctx, "en", "en")
    for key in ("itinerary", "timeline_days", "route_stops", "stay_segments", "itinerary_days"):
        lang_ctx[key] = copy.deepcopy(ctx[key])
    return main.templates.get_template(template_name).render(**lang_ctx)


def main_entry() -> None:
    ctx_path = QUOTE_DIR / "ctx.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))

    segment = next(
        (item for item in ctx.get("stay_segments", []) if item.get("city") == "Siem Reap"),
        None,
    )
    if segment is None:
        raise RuntimeError("Siem Reap stay segment is missing from the quotation context.")
    _repair_segment(segment)

    sync = ctx.setdefault("html_sync", {}).setdefault("en", {})
    sync.setdefault("edited_fields", {})["map_segment_duration_6"] = DURATION
    existing_keys = set(sync.get("existing_keys", []))
    existing_keys.add("map_segment_duration_6")
    sync["existing_keys"] = sorted(existing_keys)

    web = _render(ctx, "prototype_itinerary_imagery.html")
    pdf = _render(ctx, "prototype_itinerary_imagery_pdf.html")
    for content in (web, pdf):
        match = re.search(r'<script id="stay-segments-data"[^>]*>(.*?)</script>', content, re.DOTALL)
        segments = json.loads(match.group(1)) if match else []
        rendered_siem = next((item for item in segments if item.get("displayName") == "Siem Reap"), {})
        if (
            rendered_siem.get("mapSegmentDuration") != DURATION
            or rendered_siem.get("daysLabel") != "DAYS 14-16"
            or rendered_siem.get("nights") != 2
        ):
            raise RuntimeError("The repaired Siem Reap segment was not rendered into both outputs.")

    ctx_path.write_text(json.dumps(ctx, ensure_ascii=False) + "\n", encoding="utf-8")
    versions = [
        int(match.group(1))
        for path in QUOTE_DIR.glob("v*.html")
        if (match := re.fullmatch(r"v(\d+)(?:_[a-z]+)?\.html", path.name))
    ]
    next_version = max(versions, default=0) + 1
    (QUOTE_DIR / f"v{next_version}.html").write_text(web, encoding="utf-8")
    (QUOTE_DIR / "pdf.html").write_text(pdf, encoding="utf-8")
    (QUOTE_DIR / "pdf_en.html").write_text(pdf, encoding="utf-8")


if __name__ == "__main__":
    main_entry()
