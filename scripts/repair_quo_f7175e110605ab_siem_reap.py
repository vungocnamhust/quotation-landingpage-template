"""Rebuild the legacy quote artifacts from the persisted quotation state."""

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
SIEM_DURATION = "DAYS 14-16 • 2 NIGHTS"


def _build_render_context(ctx: dict) -> dict:
    payload = main.TourQuotationPayload.model_validate(ctx["baseline_payload"])
    lang_ctx = main._build_ctx(
        QUOTE_ID,
        payload,
        ctx.get("img_0"),
        ctx.get("destinations", []),
        lang="en",
        template_name="prototype_itinerary_imagery.html",
        brand=main.resolve_brand(None, ctx["baseline_payload"]),
    )
    main._apply_ctx_html_sync(lang_ctx, ctx, "en", "en")
    for key in ("itinerary", "timeline_days", "route_stops", "stay_segments", "itinerary_days"):
        lang_ctx[key] = copy.deepcopy(ctx[key])
    return lang_ctx


def _render(ctx: dict, template_name: str) -> str:
    return main.templates.get_template(template_name).render(**_build_render_context(ctx))


def _next_version() -> int:
    versions = [
        int(match.group(1))
        for path in QUOTE_DIR.glob("v*.html")
        if (match := re.fullmatch(r"v(\d+)(?:_[a-z]+)?\.html", path.name))
    ]
    return max(versions, default=0) + 1


def _assert_rendered_state(content: str) -> None:
    if "16 Sep – 18 Sep 2026" not in content:
        raise RuntimeError("Hanoi hotel date did not render from html_sync.")
    if "29 Sep – 01 Oct 2026" not in content:
        raise RuntimeError("Siem Reap hotel date did not render from html_sync.")
    match = re.search(r'<script id="stay-segments-data"[^>]*>(.*?)</script>', content, re.DOTALL)
    segments = json.loads(match.group(1)) if match else []
    siem_reap = next((segment for segment in segments if segment.get("city") == "Siem Reap"), {})
    if siem_reap.get("mapSegmentDuration") != SIEM_DURATION:
        raise RuntimeError("Siem Reap duration did not render from structured state.")


def main_entry() -> None:
    ctx_path = QUOTE_DIR / "ctx.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    web = _render(ctx, "prototype_itinerary_imagery.html")
    pdf = _render(ctx, "prototype_itinerary_imagery_pdf.html")
    _assert_rendered_state(web)
    _assert_rendered_state(pdf)

    (QUOTE_DIR / f"v{_next_version()}.html").write_text(web, encoding="utf-8")
    (QUOTE_DIR / "pdf.html").write_text(pdf, encoding="utf-8")
    (QUOTE_DIR / "pdf_en.html").write_text(pdf, encoding="utf-8")


if __name__ == "__main__":
    main_entry()
