"""Synchronize the current approved legacy quotation HTML into its source state."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main


QUOTE_ID = "quo_f7175e110605ab"
QUOTE_DIR = ROOT / "published" / QUOTE_ID


def _latest_html() -> tuple[int, Path]:
    candidates = []
    for path in QUOTE_DIR.glob("v*.html"):
        match = re.fullmatch(r"v(\d+)\.html", path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    if not candidates:
        raise RuntimeError(f"No published HTML found for {QUOTE_ID}")
    return max(candidates, key=lambda item: item[0])


def main_entry() -> None:
    version, html_path = _latest_html()
    html = html_path.read_text(encoding="utf-8")
    required = (
        "Anantara Hoi An Resort",
        "The Myst Dong Khoi",
        'data-editable="hotel_date_1"',
        'data-editable="booking_term_body_0"',
    )
    missing = [value for value in required if value not in html]
    if missing:
        raise RuntimeError(f"Current quotation HTML is missing required state: {missing}")

    ctx_path = QUOTE_DIR / "ctx.json"
    payload_path = QUOTE_DIR / "payload.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    main._sync_ctx_data_before_publish(ctx, html, "en", version=version)

    hotel_plan = (ctx.get("baseline_payload") or {}).get("hotelPlan", {}).get("hotels", [])
    if len(hotel_plan) != 7:
        raise RuntimeError(f"Expected seven canonical hotels, found {len(hotel_plan)}")
    if not {"Anantara Hoi An Resort", "The Myst Dong Khoi"}.issubset(
        {item.get("hotelArrangement", "").split(" (")[0] for item in hotel_plan}
    ):
        raise RuntimeError("Requested hotels are not present in canonical payload")

    ctx_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload_path.write_text(
        json.dumps(ctx["baseline_payload"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main_entry()
