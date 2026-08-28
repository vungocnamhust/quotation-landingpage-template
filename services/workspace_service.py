"""Workspace read model; independent from FastAPI route registration."""
from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any, Awaitable, Callable, Literal

from fastapi import HTTPException

from repositories import PublicationTargetRepository, QuotationDocumentRepository, QuotationRepository


WorkflowLane = Literal["facts", "content", "review", "published"]
WorkflowLoader = Callable[[str], Awaitable[dict[str, Any]]]


def default_workflow_summary() -> dict[str, dict[str, bool]]:
    """Fail closed for legacy rows that do not yet have a canonical workflow."""
    return {
        "facts": {"ready": False},
        "content": {"ready": False},
        "design": {"ready": False},
        "review": {"ready": False},
    }


def workflow_summary(workflow: dict[str, Any]) -> dict[str, dict[str, bool]]:
    return {
        stage: {"ready": bool((workflow.get(stage) or {}).get("ready"))}
        for stage in ("facts", "content", "design", "review")
    }


def classify_workflow_lane(*, status: str, workflow: dict[str, dict[str, bool]]) -> WorkflowLane:
    """Keep the workspace board's ordering tied to server-owned readiness."""
    if status == "published":
        return "published"
    if not workflow["facts"]["ready"]:
        return "facts"
    if not workflow["content"]["ready"]:
        return "content"
    return "review"


def commercial_summary(document: dict[str, Any]) -> dict[str, Any]:
    pricing = document.get("pricing") if isinstance(document.get("pricing"), dict) else {}
    options = pricing.get("options") if isinstance(pricing.get("options"), list) else []
    valid_options = [option for option in options if isinstance(option, dict)]
    option = next((item for item in valid_options if item.get("isConfirmedMainOption") is True), None)
    if option is None:
        option = next((item for item in valid_options if item.get("isAlternativeOption") is not True), None)
    if option is None:
        option = valid_options[0] if valid_options else {}
    total = option.get("groupTotalAmountMinor")
    return {
        "label": option.get("label") if isinstance(option.get("label"), str) else None,
        "currency": option.get("currency") if isinstance(option.get("currency"), str) else None,
        "groupTotalAmountMinor": total if isinstance(total, int) and total > 0 else None,
    }


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
    workflow_lane: WorkflowLane | None = None,
    workflow_loader: WorkflowLoader | None = None,
) -> dict[str, Any]:
    updated_before, id_before = parse_cursor(cursor)
    page_size = min(max(limit, 1), 100)
    async with session_factory() as session:
        summary = await QuotationRepository(session).status_summary_workspace()

    result: list[dict[str, Any]] = []
    scan_updated_before, scan_id_before = updated_before, id_before
    has_more = False
    last_visible: Any | None = None

    while not has_more:
        async with session_factory() as session:
            quotes, documents = QuotationRepository(session), QuotationDocumentRepository(session)
            candidates = await quotes.list_for_designer(
                status=status,
                search=query,
                updated_before=scan_updated_before,
                id_before=scan_id_before,
                limit=100,
            )
            docs_map: dict[str, dict[str, Any]] = {}
            for item in candidates:
                document = await documents.get_current_document(item.id, item.baseline_lang)
                if document and isinstance(document.document_json, dict):
                    docs_map[item.id] = document.document_json

        if not candidates:
            break

        for item in candidates:
            # SQLite's timezone-less test storage can return the boundary row
            # again after decoding an otherwise valid keyset cursor. The row ID
            # is part of the cursor contract, so never emit that boundary twice.
            if id_before is not None and item.id == id_before:
                continue
            document = docs_map.get(item.id, {})
            workflow = default_workflow_summary()
            if workflow_loader is not None:
                try:
                    workflow = workflow_summary(await workflow_loader(item.id))
                except HTTPException as error:
                    if error.status_code != 404:
                        raise

            lane = classify_workflow_lane(status=item.status, workflow=workflow)
            if workflow_lane is not None and lane != workflow_lane:
                continue
            if len(result) == page_size:
                has_more = True
                break

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
                "workflow": workflow,
                "commercial": commercial_summary(document),
                "workflowLane": lane,
            })
            last_visible = item

        if has_more or len(candidates) < 100:
            break
        scan_updated_before, scan_id_before = candidates[-1].updated_at, candidates[-1].id

    return {
        "items": result,
        "nextCursor": workspace_cursor(last_visible) if has_more and last_visible is not None else None,
        "summary": summary,
    }


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
