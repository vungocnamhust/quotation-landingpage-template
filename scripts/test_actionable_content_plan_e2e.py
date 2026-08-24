#!/usr/bin/env python3
"""Real Compose/API acceptance for immutable successor Actionable Content Plans.

Run inside the disposable ``e2e`` Compose service.  This runner intentionally
does not mock the content provider: selected ``auto`` and ``bypass`` actions
exercise the same FastAPI, Postgres, outbox and document-revision boundaries
used by the staff workspace.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.models.outbox import OutboxEvent
from repositories.travel_designer_repository import TravelDesignerRepository
from scripts.test_v2_brochure_workflow import CurlApi, WorkflowFailure, make_facts, prepare_workflow_intake, require


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write_report(path: str | None, report: dict[str, Any]) -> None:
    if not path:
        return
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def action_headers(correlation_id: str, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {"X-Correlation-ID": correlation_id}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def successor_fixture(brand_id: str, lang: str) -> dict[str, Any]:
    """Five-day Hoi An predecessor which becomes Hanoi Day 5 plus Day 6."""
    facts = make_facts(brand_id, lang, f"action-plan-{uuid.uuid4().hex}")
    trip = facts["trip_facts"]
    trip.update({"destinations": ["Hanoi", "Ninh Binh", "Hoi An"], "end_date": "2026-10-05", "duration_days": 5, "duration_nights": 4})
    trip["itinerary"].append({
        "day_number": 5,
        "destination": "Hoi An",
        "summary": "ACP_SENTINEL Hoi An lantern quarter",
        "overnight": "Hoi An",
        "meals": ["Breakfast", "Dinner"],
        "highlights": ["ACP_SENTINEL Hoi An lanterns"],
        "notes": ["ACP_SENTINEL Hoi An prose must not cross to Hanoi"],
    })
    facts["service_facts"]["hotels"].append({
        "destination": "Hoi An", "name": "ACP_SENTINEL Hoi An Hotel", "room_type": "Suite",
        "check_in": "2026-10-04", "check_out": "2026-10-05", "intro": "ACP Hoi An hotel",
        "phone": "+84005", "display_city": "HOI AN", "display_date": "04–05 Oct",
    })
    facts["pricing_facts"]["options"][0]["group_total_amount_minor"] = 1_050_000
    return facts


def apply_predecessor_day_copy(api: CurlApi, quotation_id: str, lang: str, document: dict[str, Any], revision: int) -> tuple[dict[str, Any], int]:
    day = document["itinerary"]["days"][4]
    scope = f"itinerary:day:{day['sourceFactId']}"
    candidate = {
        "sourceFactId": day["sourceFactId"],
        "dayNumber": 5,
        "title": "ACP_SENTINEL Hoi An narrative",
        "description": ["ACP_SENTINEL Hoi An narrative must never be inherited by Hanoi."],
        "activities": ["ACP_SENTINEL Hoi An lantern activity"],
    }
    created = api.request("POST", f"/api/v2/quotations/{quotation_id}/content-drafts/manual", query={"lang": lang}, body={"scope": scope, "candidate": candidate, "baseRevision": revision})
    applied = api.request("POST", f"/api/v2/quotations/{quotation_id}/content-drafts/{created['draft']['id']}/apply", body={"baseRevision": revision})
    return applied["document"], applied["currentRevision"]


def successor_facts(predecessor_facts: dict[str, Any]) -> dict[str, Any]:
    facts = copy.deepcopy(predecessor_facts)
    trip = facts["trip_facts"]
    trip.update({"destinations": ["Hanoi", "Ninh Binh"], "end_date": "2026-10-06", "duration_days": 6, "duration_nights": 5})
    day_five = trip["itinerary"][4]
    day_five.update({
        "destination": "Hanoi",
        "overnight": "Hanoi",
        "summary": "ACP_SENTINEL Hanoi day five",
        "highlights": ["ACP_SENTINEL Hanoi museum"],
        "notes": ["ACP_SENTINEL Hanoi prose"],
    })
    trip["itinerary"].append({
        "day_number": 6,
        "destination": "Hanoi",
        "summary": "ACP_SENTINEL Hanoi day six new content",
        "overnight": "Hanoi",
        "meals": ["Breakfast"],
        "highlights": ["ACP_SENTINEL Hanoi farewell"],
        "notes": ["ACP new day must begin empty"],
    })
    facts["pricing_facts"]["options"][0]["group_total_amount_minor"] = 1_250_000
    return facts


async def outbox_events(quotation_id: str) -> list[dict[str, Any]]:
    database_url = os.environ.get("DATABASE_URL")
    require(bool(database_url), "DATABASE_URL is required for outbox acceptance.")
    engine = create_async_engine(str(database_url))
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            rows = await session.scalars(select(OutboxEvent).where(OutboxEvent.aggregate_id == quotation_id).order_by(OutboxEvent.created_at.asc()))
            return [{"id": row.id, "type": row.event_type, "correlationId": row.correlation_id, "payload": row.payload_json} for row in rows]
    finally:
        await engine.dispose()


async def ensure_editor_profile(email: str) -> None:
    """Provision the disposable E2E actor before exercising HTTP ownership.

    Workspace identity intentionally fails closed when a designer profile does
    not exist.  This is test-fixture setup only; quotation, plan, draft and
    document mutations remain exclusively on the public HTTP contract.
    """
    database_url = os.environ.get("DATABASE_URL")
    require(bool(database_url), "DATABASE_URL is required for E2E actor setup.")
    engine = create_async_engine(str(database_url))
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            repository = TravelDesignerRepository(session)
            if await repository.get_active_by_email(email) is None:
                await repository.create_profile(
                    profile_id=f"td_acp_{uuid.uuid4().hex[:16]}",
                    email=email,
                    name="Action Plan E2E Designer",
                    phone="+84900000001",
                    storage_slug=f"action-plan-e2e-{uuid.uuid4().hex[:12]}",
                )
                await session.commit()
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default=os.getenv("WORKFLOW_API_BASE") or os.getenv("E2E_API_BASE_URL") or "http://localhost:8111")
    parser.add_argument("--editor-email", default=os.getenv("WORKFLOW_EDITOR_EMAIL", "action-plan-ci@example.test"))
    parser.add_argument("--brand-id", default=os.getenv("WORKFLOW_BRAND_ID", "vietnam_safar"))
    parser.add_argument("--lang", default="en", choices=("en", "vi", "ar"))
    parser.add_argument("--report-file", default=os.getenv("ACTION_PLAN_REPORT_FILE"))
    return parser.parse_args()


def main() -> int:
    report: dict[str, Any] = {"status": "running", "requestLogAssertions": []}
    args = parse_args()
    try:
        require(os.getenv("ENABLE_LLM_QUOTE_GENERATION", "1").lower() not in {"0", "false", "no"}, "ENABLE_LLM_QUOTE_GENERATION must be enabled for actionable Content acceptance.")
        # Auth-disabled Compose resolves every editor request as local@localhost
        # regardless of the illustrative X-DMC-Email header. Provision both so
        # this runner also stays valid when an auth-enabled profile fixture is
        # used outside the local-bypass stack.
        asyncio.run(ensure_editor_profile("local@localhost"))
        asyncio.run(ensure_editor_profile(args.editor_email))
        api = CurlApi(args.api_base, args.editor_email, os.getenv("QUOTE_SERVICE_TOKEN"))
        facts = successor_fixture(args.brand_id, args.lang)
        prepare_workflow_intake(api, facts)
        predecessor_id = api.request("POST", "/api/v2/quotations", body=facts)["quotationId"]
        predecessor = api.request("GET", f"/api/v2/quotations/{predecessor_id}/document", query={"lang": args.lang})
        predecessor_document, predecessor_revision = predecessor["document"], predecessor["currentRevision"]
        predecessor_document, predecessor_revision = apply_predecessor_day_copy(api, predecessor_id, args.lang, predecessor_document, predecessor_revision)
        # Hash the reloaded canonical row, not the mutation response.  The
        # latter includes transport revision metadata which is deliberately
        # normalized when the document is persisted.
        predecessor = api.request("GET", f"/api/v2/quotations/{predecessor_id}/document", query={"lang": args.lang})
        predecessor_document, predecessor_revision = predecessor["document"], predecessor["currentRevision"]
        predecessor_hash = stable_hash(predecessor_document)
        preserved_day_hashes = [stable_hash(day) for day in predecessor_document["itinerary"]["days"][:4]]
        predecessor_facts = api.request("GET", f"/api/v2/quotations/{predecessor_id}/facts")["facts"]

        created = api.request("POST", f"/api/v2/quotations/{predecessor_id}/versions", body={"facts": successor_facts(predecessor_facts), "baseRevision": predecessor_revision})
        successor_id = created["quotationId"]
        successor = api.request("GET", f"/api/v2/quotations/{successor_id}/document", query={"lang": args.lang})
        successor_document, successor_revision = successor["document"], successor["currentRevision"]
        require(stable_hash(api.request("GET", f"/api/v2/quotations/{predecessor_id}/document", query={"lang": args.lang})["document"]) == predecessor_hash, "Predecessor document mutated during successor creation.")
        require([stable_hash(day) for day in successor_document["itinerary"]["days"][:4]] == preserved_day_hashes, "Unchanged Day 1–4 content was not preserved.")
        require("ACP_SENTINEL Hoi An" not in json.dumps(successor_document["itinerary"]["days"][4]), "Hoi An narrative/media crossed into successor Day 5 Hanoi.")
        require(not successor_document["itinerary"]["days"][5]["title"] and not successor_document["itinerary"]["days"][5]["description"], "New Day 6 inherited narrative.")
        for field in ("hero", "itineraryDivider", "hotelDivider"):
            require(bool((successor_document.get("assets") or {}).get(field, {}).get("r2Key")), f"Media default missing assets.{field}.")
        require(all(day.get("images", {}).get("carousel") for day in successor_document["itinerary"]["days"]), "A successor itinerary day has no default carousel media.")

        plan = api.request("GET", f"/api/v2/quotations/{successor_id}/content-actions")
        actions = plan["actions"]
        auto = [item for item in actions if item["automationPolicy"] == "auto"]
        bypass = [item for item in actions if item["automationPolicy"] == "bypass"]
        require(auto and bypass, f"Action plan must expose both auto and bypass scopes: {actions}")
        require(any(item["scope"].startswith("itinerary:day:") for item in auto), "Day-level action is missing from plan.")
        before_accept_drafts = api.request("GET", f"/api/v2/quotations/{successor_id}/content-drafts", query={"lang": args.lang})["drafts"]
        accept_correlation = f"acp-accept-{uuid.uuid4().hex}"
        api.request("POST", f"/api/v2/quotations/{successor_id}/content-actions/accept", body={"note": "E2E accepted"}, headers=action_headers(accept_correlation))
        require(api.request("GET", f"/api/v2/quotations/{successor_id}/document", query={"lang": args.lang})["currentRevision"] == successor_revision, "Accept mutated the document.")
        require(api.request("GET", f"/api/v2/quotations/{successor_id}/content-drafts", query={"lang": args.lang})["drafts"] == before_accept_drafts, "Accept created a Content draft.")

        selected_auto = [auto[0]["id"]]
        auto_result = api.request("POST", f"/api/v2/quotations/{successor_id}/content-actions/generate-drafts", body={"planId": plan["id"], "actionIds": selected_auto, "writingStyle": "storytelling"}, headers=action_headers(f"acp-auto-{uuid.uuid4().hex}"))
        require(auto_result["documentRevision"] == successor_revision, "Auto generation changed the document revision.")
        require(len(auto_result["draftIds"]) == 1, "Auto generation did not create exactly one draft.")

        selected_bypass = [bypass[0]["id"]]
        bypass_key = f"acp-bypass-{uuid.uuid4().hex}"
        bypass_headers = action_headers(f"acp-bypass-{uuid.uuid4().hex}", bypass_key)
        bypass_result = api.request("POST", f"/api/v2/quotations/{successor_id}/content-actions/generate-and-apply", body={"planId": plan["id"], "actionIds": selected_bypass, "writingStyle": "storytelling", "expectedRevision": successor_revision}, headers=bypass_headers)
        require(bypass_result["documentRevision"] == successor_revision + 1, "Bypass did not create exactly one document revision.")
        replay = api.request("POST", f"/api/v2/quotations/{successor_id}/content-actions/generate-and-apply", body={"planId": plan["id"], "actionIds": selected_bypass, "writingStyle": "storytelling", "expectedRevision": successor_revision}, headers=bypass_headers)
        require(replay == bypass_result, "Idempotent bypass retry did not replay its original result.")
        remaining_bypass = [item for item in bypass if item["id"] not in selected_bypass]
        if remaining_bypass:
            stale = api.request_status("POST", f"/api/v2/quotations/{successor_id}/content-actions/generate-and-apply", expected_status=409, body={"planId": plan["id"], "actionIds": [remaining_bypass[0]["id"]], "writingStyle": "storytelling", "expectedRevision": successor_revision}, headers=action_headers(f"acp-stale-{uuid.uuid4().hex}", f"acp-stale-{uuid.uuid4().hex}"))
            require(stale.get("detail", {}).get("code") == "document_revision_conflict", f"Stale bypass has no structured conflict: {stale}")

        events = asyncio.run(outbox_events(successor_id))
        event_types = [event["type"] for event in events]
        for event_type in ("quotation.version.created", "quotation.content_plan.created", "quotation.content_plan.accepted", "quotation.content_action.drafts_created", "quotation.content_action.applied"):
            require(event_type in event_types, f"Outbox event missing: {event_type}")
        report.update({
            "status": "passed",
            "quotationFamilyId": api.request("GET", f"/api/v2/quotations/{successor_id}/facts")["businessVersion"]["familyId"],
            "predecessorId": predecessor_id,
            "successorId": successor_id,
            "planId": plan["id"],
            "selectedAutoActionIds": selected_auto,
            "selectedBypassActionIds": selected_bypass,
            "predecessorDocumentHash": predecessor_hash,
            "successorDocumentHashes": {"before": stable_hash(successor_document), "afterBypass": stable_hash(api.request("GET", f"/api/v2/quotations/{successor_id}/document", query={"lang": args.lang})["document"])},
            "outboxEventIds": [event["id"] for event in events],
            "requestLogAssertions": ["accept-no-ai-no-draft-no-document-write", "auto-draft-only", "bypass-one-revision", "bypass-idempotent-replay", "no-batch-generate", "no-apply-all", "no-fast-track", "no-retired-impact-execution"],
        })
        write_report(args.report_file, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as error:
        report.update({"status": "failed", "error": str(error)})
        write_report(args.report_file, report)
        print(f"ACTIONABLE CONTENT PLAN E2E FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
