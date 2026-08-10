"""Fail-closed migration of V2 legacy rich content into canonical blocks.

Run without ``--apply`` first.  Any unsupported HTML is reported with its
quotation, language and JSON path; it must be corrected before cutover.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from db.models.quotation import QuotationDocument, QuotationDocumentRevision, QuotationRequest
from db.session import get_session_factory
from quote_document import CreateQuoteRequestV1, LEGACY_RICH_DOCUMENT_FIELDS, QuoteDocumentV1, build_rich_content_from_legacy, legacy_html_to_plain_text, strip_legacy_rich_document_fields


LEGACY_TRIP_COPY_PATHS = {
    "title": "trip.title",
    "subtitle": "trip.lede",
    "cover_kicker": "narrative.coverKicker",
    "hero_meta_1": "narrative.heroMeta1",
    "hero_meta_2": "narrative.heroMeta2",
    "footer_text": "narrative.footerText",
    "overview_title": "narrative.journeyOverviewTitle",
    "journey_overview_title": "narrative.journeyOverviewTitle",
    "letter_highlight": "narrative.letterHighlight",
    "letter_greeting": "narrative.letterGreeting",
    "letter_intro": "narrative.letterIntro",
    "letter_body": "narrative.letterBody2",
    "letter_outro": "narrative.letterOutro",
    "letter_sign_off": "narrative.letterSignOff",
    "letter_sender": "narrative.letterSender",
    "route_title": "route.title",
    "route_description": "route.description",
    "itinerary_title": "itinerary.title",
    "itinerary_description": "itinerary.description",
}


def _set_path(payload: dict[str, Any], path: str, value: Any) -> None:
    target = payload
    parts = path.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def _migrate_legacy_trip_copy(document: dict[str, Any], request_json: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    next_document = copy.deepcopy(document)
    next_request = copy.deepcopy(request_json)
    trip = dict(next_request.get("trip_facts") or {})
    provenance = dict((next_document.get("meta") or {}).get("contentProvenance") or {})
    for legacy_key, target in LEGACY_TRIP_COPY_PATHS.items():
        value = trip.pop(legacy_key, None)
        if isinstance(value, str) and value.strip():
            _set_path(next_document, target, value.strip())
            provenance[target] = "legacy-migrated"
    legacy_days = trip.get("itinerary") or []
    canonical_days = ((next_document.get("itinerary") or {}).get("days") or [])
    for index, day in enumerate(legacy_days):
        if not isinstance(day, dict):
            continue
        title = day.pop("display_title", None)
        day.pop("label_highlights", None)
        day.pop("label_notes", None)
        if isinstance(title, str) and title.strip():
            number = day.get("day_number") or index + 1
            canonical_day = next((item for item in canonical_days if item.get("dayNumber") == number), None)
            if canonical_day is None:
                raise ValueError(f"trip_facts.itinerary[{index}].display_title has no matching canonical itinerary day")
            canonical_day["title"] = title.strip()
            provenance[f"itinerary.days.{number}.title"] = "legacy-migrated"
    next_request["trip_facts"] = trip
    booking = dict(next_request.get("booking_facts") or {})
    for index, item in enumerate(booking.get("items") or []):
        if isinstance(item, dict) and isinstance(item.get("body"), str) and ("<" in item["body"] or ">" in item["body"]):
            item["body"] = legacy_html_to_plain_text(item["body"])
    if isinstance(booking.get("description"), str) and ("<" in booking["description"] or ">" in booking["description"]):
        booking["description"] = legacy_html_to_plain_text(booking["description"])
    next_request["booking_facts"] = booking
    next_document.setdefault("meta", {})["contentProvenance"] = provenance
    return next_document, next_request


def migrate(document: dict[str, Any], request_json: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    next_document, next_request = _migrate_legacy_trip_copy(document, request_json)
    if any(key in next_document for key in LEGACY_RICH_DOCUMENT_FIELDS):
        next_document["content"] = build_rich_content_from_legacy(next_document)
        next_document = strip_legacy_rich_document_fields(next_document)
    meta = dict(next_document.get("meta") or {})
    meta["contentSchemaVersion"] = 1
    next_document["meta"] = meta
    # Verify both the block shape and the final canonical document before any
    # database write. Runtime deliberately has no compatibility adapter.
    QuoteDocumentV1.model_validate(next_document)
    CreateQuoteRequestV1.model_validate(next_request)
    return next_document, next_request


async def run(apply: bool) -> int:
    report: list[dict[str, str]] = []
    changed = 0
    async with get_session_factory()() as session:
        request_rows = list((await session.scalars(select(QuotationRequest))).all())
        requests_by_quote = {str(row.quotation_id): row for row in request_rows}
        current_rows = list((await session.scalars(select(QuotationDocument))).all())
        revision_rows = list((await session.scalars(select(QuotationDocumentRevision))).all())
        for row in [*current_rows, *revision_rows]:
            quotation_id = str(row.quotation_id)
            language = str(row.lang)
            request_row = requests_by_quote.get(quotation_id)
            if request_row is None:
                report.append({"quotationId": quotation_id, "lang": language, "path": "quotation_requests", "error": "No request snapshot is available for ownership migration."})
                continue
            try:
                converted, converted_request = migrate(row.document_json, request_row.request_json)
            except Exception as exc:  # report every bad document, not only the first
                report.append({"quotationId": quotation_id, "lang": language, "path": "content.sections", "error": str(exc)})
                continue
            if converted != row.document_json or converted_request != request_row.request_json:
                changed += 1
                if apply:
                    row.document_json = converted
                    request_row.request_json = converted_request
        if report:
            print(json.dumps({"ok": False, "unsupported": report}, indent=2))
            await session.rollback()
            return 1
        if apply:
            await session.commit()
    print(json.dumps({"ok": True, "changed": changed, "applied": apply}, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="persist only after a clean preflight")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.apply)))


if __name__ == "__main__":
    main()
