"""Workspace read model; independent from FastAPI route registration."""
from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from repositories import PublicationTargetRepository, QuotationDocumentRepository, QuotationRepository


def parse_cursor(cursor: str | None) -> tuple[datetime | None, str | None]:
    if not cursor:
        return None, None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        return datetime.fromisoformat(payload["updatedAt"]), str(payload["id"])
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="Invalid workspace cursor") from None


def workspace_cursor(quotation: Any) -> str:
    payload = json.dumps({"updatedAt": quotation.updated_at.isoformat(), "id": quotation.id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


async def list_workspace_quotations(
    session_factory: Any,
    *,
    status: str | None,
    query: str,
    cursor: str | None,
    limit: int,
) -> dict[str, Any]:
    updated_before, id_before = parse_cursor(cursor)
    page_size = min(max(limit, 1), 100)
    async with session_factory() as session:
        quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
        items = await quotes.list_for_designer(
            status=status, search=query, updated_before=updated_before, id_before=id_before, limit=page_size + 1,
        )
        summary = await quotes.status_summary_workspace()
        visible, docs_map = items[:page_size], {}
        for item in visible:
            document = await documents.get_current_document(item.id, item.baseline_lang)
            if document and isinstance(document.document_json, dict):
                docs_map[item.id] = document.document_json

    result = []
    for item in visible:
        document = docs_map.get(item.id, {})
        trip = document.get("trip") if isinstance(document.get("trip"), dict) else {}
        traveler = document.get("traveler") if isinstance(document.get("traveler"), dict) else {}
        route = document.get("route") if isinstance(document.get("route"), dict) else {}
        destinations = [
            segment.get("displayName") for segment in route.get("staySegments", [])
            if isinstance(segment, dict) and segment.get("displayName")
        ]
        result.append({
            "id": item.id, "title": trip.get("title") or item.title,
            "customerName": item.customer_name or traveler.get("customerName") or traveler.get("customer_name") or None,
            "brandId": item.brand_id, "status": item.status, "locale": item.baseline_lang,
            "createdAt": item.created_at.isoformat(), "updatedAt": item.updated_at.isoformat(),
            "currentRevision": item.current_revision, "currentVersion": item.current_version,
            "tripFacts": {
                "destinations": destinations, "startDate": None, "endDate": None,
                "durationDays": None, "durationNights": None,
                "displayTravelDates": trip.get("travelDates") or None,
                "displayRouteText": trip.get("routeText") or (" → ".join(destinations) if destinations else None),
                "durationText": trip.get("durationText") or None,
            },
            "customerFacts": {
                "adults": traveler.get("adults") if isinstance(traveler.get("adults"), int) else None,
                "children": traveler.get("children") if isinstance(traveler.get("children"), int) else None,
                "nationality": traveler.get("nationality") if isinstance(traveler.get("nationality"), str) else None,
                "guestProfile": traveler.get("travelStyle") or traveler.get("guestProfile") or None,
                "travelStyle": traveler.get("travelStyle") or traveler.get("guestProfile") or None,
            },
        })
    return {"items": result, "nextCursor": workspace_cursor(visible[-1]) if len(items) > page_size and visible else None, "summary": summary}


async def get_workspace_overview(session_factory: Any, quotation_id: str, workflow: dict[str, Any]) -> dict[str, Any]:
    async with session_factory() as session:
        quote = await QuotationRepository(session).get_quotation_by_id(quotation_id)
        targets = await PublicationTargetRepository(session).list_targets(quotation_id, locale=quote.baseline_lang)
    return {
        "quotation": {
            "id": quote.id, "title": quote.title, "customerName": quote.customer_name, "brandId": quote.brand_id,
            "status": quote.status, "locale": quote.baseline_lang, "updatedAt": quote.updated_at.isoformat(),
            "currentRevision": quote.current_revision, "currentVersion": quote.current_version,
        },
        "workflow": workflow,
        "publications": [
            {"targetId": target.id, "brandId": target.brand_id, "status": target.status, "activeReleaseId": target.active_release_id}
            for target in targets
        ],
    }
