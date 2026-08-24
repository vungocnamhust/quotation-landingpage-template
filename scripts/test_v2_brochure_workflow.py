#!/usr/bin/env python3
"""Fail-fast curl integration gate for the V2 brochure workflow.

This runner deliberately uses the curl binary for every HTTP request.  It is
intended for a disposable local/CI tenant: it creates and publishes a quote.
Set ENABLE_LLM_QUOTE_GENERATION=1 and provide working model credentials; an
LLM fallback is a failure because this is an integration, not a mock test.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal
from urllib.parse import urlencode, urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Allow `python scripts/test_v2_brochure_workflow.py` from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from quote_document import QuoteDocumentV1, SECTION_REGISTRY
from repositories.media_library_repository import MediaLibraryRepository
from services.storage.r2_storage import R2Storage


Owner = Literal["fact", "content", "design", "publish"]
EditableOwner = Literal["fact", "fact-derived", "content", "design", "system"]
EditableMode = Literal["plainText", "richText", "altText", "ariaLabel", "actionLabel"]


class WorkflowFailure(RuntimeError):
    """A request or contract assertion failed; callers must stop immediately."""


def write_tier_report(path: str | None, report: dict[str, Any]) -> None:
    """Persist compact cross-tier state without leaking provider credentials."""
    if not path:
        return
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


@dataclass(frozen=True)
class CoverageEntry:
    path: str
    owner: Owner
    assertion: str


@dataclass(frozen=True)
class EditableFieldExpectation:
    """A stable representative marker for every public brochure data group."""

    path: str
    owner: EditableOwner
    mode: EditableMode


@dataclass(frozen=True)
class WorkflowScenario:
    """Explicit test-pyramid inventory; full scenarios stay opt-in in CI."""

    id: str
    tier: Literal["contract", "api", "ssr", "full"]
    requires_llm: bool
    requires_r2: bool
    description: str


WORKFLOW_SCENARIOS: tuple[WorkflowScenario, ...] = (
    WorkflowScenario("field-contract", "contract", False, False, "Canonical paths, owners, modes, and locale defaults."),
    WorkflowScenario("fact-lifecycle", "api", False, False, "Required facts, derived values, and stale draft invalidation."),
    WorkflowScenario("content-lifecycle", "api", True, False, "Draft, review, apply, discard, and stale candidate transitions."),
    WorkflowScenario("design-validation", "api", False, False, "Revision-locked copy overrides and presentation preservation."),
    WorkflowScenario("ssr-parity", "ssr", False, False, "Public/PDF markers, locale defaults, and resolved release revision."),
    WorkflowScenario("happy-path", "full", True, True, "Facts → real LLM content → design assets → async publish."),
    WorkflowScenario("stale-content", "full", True, False, "Facts change after generation; stale candidate must never Apply."),
    WorkflowScenario("revision-conflict", "full", False, False, "Concurrent design writers receive a revision-locked 409."),
    WorkflowScenario("asset-failure", "full", False, False, "Invalid media blocks review and publish with diagnostics."),
    WorkflowScenario("release-immutability", "full", False, True, "A frozen release remains unchanged after later edits."),
)


# These span every public section plus every special text mode. The values are
# intentionally canonical pointers rather than renderer implementation details.
SSR_EDITABLE_FIELD_EXPECTATIONS: tuple[EditableFieldExpectation, ...] = (
    EditableFieldExpectation("/brand/displayName", "fact-derived", "plainText"),
    EditableFieldExpectation("/trip/title", "content", "plainText"),
    EditableFieldExpectation("/narrative/coverKicker", "content", "plainText"),
    EditableFieldExpectation("/presentation/copyOverrides/stays.title", "design", "plainText"),
    EditableFieldExpectation("/route/title", "content", "plainText"),
    EditableFieldExpectation("/itinerary/title", "content", "plainText"),
    EditableFieldExpectation("/itinerary/days/0/title", "content", "plainText"),
    EditableFieldExpectation("/itinerary/days/0/description/0", "content", "plainText"),
    EditableFieldExpectation("/stays/hotels/0/name", "fact", "plainText"),
    EditableFieldExpectation("/pricing/options/0/groupTotalAmountMinor", "fact", "plainText"),
    EditableFieldExpectation("/content/sections/inclusions_exclusions/blocks/0/leftItems/0", "fact", "plainText"),
    EditableFieldExpectation("/content/sections/booking_terms/blocks/0/text", "fact", "richText"),
    EditableFieldExpectation("/designer/quote", "content", "plainText"),
    EditableFieldExpectation("/designer/name", "fact-derived", "plainText"),
    EditableFieldExpectation("/labels/chatWhatsapp", "system", "actionLabel"),
    EditableFieldExpectation("/presentation/copyOverrides/a11y.routeMapOverview", "design", "ariaLabel"),
)


# This is intentionally explicit.  A schema-only walk cannot decide whether a
# field is Fact, generated Content, or a presentation decision.
COVERAGE_MANIFEST: tuple[CoverageEntry, ...] = (
    CoverageEntry("presentation", "design", "PUT document round-trip"),
    CoverageEntry("assets", "design", "PUT document asset round-trip"),
    CoverageEntry("traveler", "fact", "Facts -> canonical document"),
    CoverageEntry("trip", "content", "Content copy plus Fact-derived display values -> canonical document"),
    CoverageEntry("narrative", "content", "LLM candidate -> applied document"),
    CoverageEntry("route", "content", "Content copy plus Fact-derived route model -> canonical document"),
    CoverageEntry("itinerary", "content", "Content copy plus Fact-derived itinerary model -> canonical document"),
    CoverageEntry("stays", "fact", "Facts -> canonical document"),
    CoverageEntry("pricing", "fact", "Facts -> canonical document"),
    CoverageEntry("content", "content", "Typed rich-content blocks -> applied document"),
    CoverageEntry("designer", "fact", "Facts -> canonical document"),
    CoverageEntry("layout", "design", "PUT document layout round-trip"),
    CoverageEntry("viewOverrides", "design", "PUT document round-trip"),
)

NON_RENDERED_TOP_LEVELS = {"meta", "brand", "generationStatus"}


def canonical_renderable_top_levels() -> set[str]:
    """Return all quote-document groups that the brochure contract renders."""
    return set(QuoteDocumentV1.model_fields) - NON_RENDERED_TOP_LEVELS


def validate_coverage_manifest(entries: Iterable[CoverageEntry] = COVERAGE_MANIFEST) -> None:
    entries = tuple(entries)
    by_path = {entry.path: entry for entry in entries}
    if len(by_path) != len(entries):
        raise WorkflowFailure("Coverage manifest has duplicate document paths.")
    unknown = set(by_path) - canonical_renderable_top_levels()
    missing = canonical_renderable_top_levels() - set(by_path)
    invalid_owner = [entry.path for entry in entries if entry.owner not in {"fact", "content", "design", "publish"}]
    if unknown or missing or invalid_owner:
        parts = []
        if unknown:
            parts.append(f"unknown={sorted(unknown)}")
        if missing:
            parts.append(f"unowned={sorted(missing)}")
        if invalid_owner:
            parts.append(f"invalid_owner={invalid_owner}")
        raise WorkflowFailure("Coverage manifest is incomplete: " + "; ".join(parts))
    if set(SECTION_REGISTRY) != {"hero", "overview_letter", "route_map", "itinerary", "hotel_plan", "pricing", "inclusions_exclusions", "booking_terms", "designer"}:
        raise WorkflowFailure("Section registry changed; update the workflow coverage manifest.")


def validate_test_pyramid_contracts(
    scenarios: Iterable[WorkflowScenario] = WORKFLOW_SCENARIOS,
    fields: Iterable[EditableFieldExpectation] = SSR_EDITABLE_FIELD_EXPECTATIONS,
) -> None:
    scenarios, fields = tuple(scenarios), tuple(fields)
    ids = [item.id for item in scenarios]
    if len(ids) != len(set(ids)) or {item.tier for item in scenarios} != {"contract", "api", "ssr", "full"}:
        raise WorkflowFailure("Test pyramid must contain unique scenarios in contract, api, ssr, and full tiers.")
    paths = [item.path for item in fields]
    valid_owners = {"fact", "fact-derived", "content", "design", "system"}
    valid_modes = {"plainText", "richText", "altText", "ariaLabel", "actionLabel"}
    if len(paths) != len(set(paths)) or any(not item.path.startswith("/") or item.owner not in valid_owners or item.mode not in valid_modes for item in fields):
        raise WorkflowFailure("SSR editable field contract contains an invalid path, owner, mode, or duplicate.")
    covered_sections = {item.path.split("/")[1] for item in fields}
    required_sections = {"brand", "trip", "narrative", "presentation", "route", "itinerary", "stays", "pricing", "content", "designer", "labels"}
    if not required_sections.issubset(covered_sections):
        raise WorkflowFailure(f"SSR editable field contract is incomplete: missing={sorted(required_sections - covered_sections)}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowFailure(message)


def get_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise WorkflowFailure(f"Missing asserted path: {path}")
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                raise WorkflowFailure(f"Missing asserted list item: {path}")
            current = current[index]
        else:
            raise WorkflowFailure(f"Cannot resolve asserted path: {path}")
    return current


def assert_paths_exist(document: dict[str, Any], paths: Iterable[str]) -> None:
    for path in paths:
        get_path(document, path)


_EDITABLE_ATTR = re.compile(r'data-editable="(?P<path>[^"]+)"(?P<attrs>[^>]*)')


def assert_ssr_editable_contract(html: str, expectations: Iterable[EditableFieldExpectation] = SSR_EDITABLE_FIELD_EXPECTATIONS) -> None:
    """Require exact marker triples and reject the retired boolean marker."""
    require('data-editable="true"' not in html, "SSR contains the retired data-editable=true marker.")
    markers = {
        match.group("path"): match.group("attrs")
        for match in _EDITABLE_ATTR.finditer(html)
    }
    require(bool(markers), "SSR contains no editable markers.")
    for path, attrs in markers.items():
        require('data-edit-owner="' in attrs and 'data-edit-mode="' in attrs, f"SSR marker {path} is missing owner or mode.")
    for expected in expectations:
        attrs = markers.get(expected.path)
        require(attrs is not None, f"SSR is missing editable path {expected.path}.")
        require(f'data-edit-owner="{expected.owner}"' in attrs, f"SSR editable owner drifted at {expected.path}.")
        require(f'data-edit-mode="{expected.mode}"' in attrs, f"SSR editable mode drifted at {expected.path}.")


class CurlApi:
    def __init__(self, base_url: str, editor_email: str, service_token: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self.editor_email = editor_email
        self.service_token = service_token

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str | int] | None = None,
        headers: dict[str, str] | None = None,
        service: bool = False,
    ) -> dict[str, Any]:
        url = self.base_url + path
        if query:
            url += "?" + urlencode(query)
        command = ["curl", "--silent", "--show-error", "--fail-with-body", "--request", method, url, "--header", "Accept: application/json"]
        if service:
            require(bool(self.service_token), "--service-token is required for internal release verification.")
            command += ["--header", f"X-Quote-Service-Token: {self.service_token}"]
        else:
            command += ["--header", f"X-DMC-Email: {self.editor_email}"]
        for name, value in (headers or {}).items():
            command += ["--header", f"{name}: {value}"]
        if body is not None:
            command += ["--header", "Content-Type: application/json", "--data", json.dumps(body)]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode:
            detail = (completed.stdout or completed.stderr).strip()
            raise WorkflowFailure(f"curl {method} {path} failed (exit {completed.returncode}): {detail}")
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise WorkflowFailure(f"curl {method} {path} returned invalid JSON: {completed.stdout[:500]!r}") from exc
        if not isinstance(response, dict):
            raise WorkflowFailure(f"curl {method} {path} returned a non-object JSON payload.")
        return response

    def request_status(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str | int] | None = None,
        headers: dict[str, str] | None = None,
        expected_status: int,
        service: bool = False,
    ) -> dict[str, Any]:
        """Assert an expected HTTP failure without weakening normal fail-fast calls."""
        url = self.base_url + path
        if query:
            url += "?" + urlencode(query)
        command = ["curl", "--silent", "--show-error", "--request", method, url, "--header", "Accept: application/json", "--write-out", "\n%{http_code}"]
        if service:
            require(bool(self.service_token), "--service-token is required for internal release verification.")
            command += ["--header", f"X-Quote-Service-Token: {self.service_token}"]
        else:
            command += ["--header", f"X-DMC-Email: {self.editor_email}"]
        for name, value in (headers or {}).items():
            command += ["--header", f"{name}: {value}"]
        if body is not None:
            command += ["--header", "Content-Type: application/json", "--data", json.dumps(body)]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode:
            raise WorkflowFailure(f"curl {method} {path} failed before receiving an HTTP response: {(completed.stderr or completed.stdout).strip()}")
        raw_body, separator, raw_status = completed.stdout.rpartition("\n")
        require(bool(separator) and raw_status.isdigit(), f"curl {method} {path} did not return an HTTP status.")
        status = int(raw_status)
        require(status == expected_status, f"curl {method} {path} expected HTTP {expected_status}, got {status}: {raw_body[:500]}")
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise WorkflowFailure(f"curl {method} {path} returned invalid error JSON: {raw_body[:500]!r}") from exc
        require(isinstance(payload, dict), f"curl {method} {path} returned a non-object error payload.")
        return payload

    def get_text(self, url: str, *, host: str | None = None) -> str:
        """Fetch server-rendered display HTML without relying on a browser."""
        command = ["curl", "--silent", "--show-error", "--fail-with-body", url]
        if host:
            command += ["--header", f"Host: {host}"]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode:
            detail = (completed.stdout or completed.stderr).strip()
            raise WorkflowFailure(f"curl GET {url} failed (exit {completed.returncode}): {detail}")
        return completed.stdout


def make_facts(brand_id: str, lang: str, opportunity_id: str) -> dict[str, Any]:
    """Use two records in each repeated brochure group to exercise all slots."""
    return {
        "source": {"kind": "manual"}, "opportunity_id": opportunity_id, "brand_id": brand_id, "lang": lang,
        "presentation_options": {"template_id": "quote-generator", "renderer": "quote-generator", "theme_id": "brochure", "layout_version": 1},
        "trip_facts": {
            "destinations": ["Hanoi", "Ninh Binh"],
            "start_date": "2026-10-01", "end_date": "2026-10-04", "duration_days": 4, "duration_nights": 3,
            "display_route_text": "WF_SENTINEL route", "display_travel_dates": "WF_SENTINEL dates",
            "itinerary": [
                {"day_number": 1, "destination": "Hanoi", "summary": "WF_SENTINEL Hanoi arrival", "overnight": "Hanoi", "meals": ["Breakfast"], "highlights": ["WF_SENTINEL Temple"], "notes": ["WF_SENTINEL relaxed"]},
                {"day_number": 2, "destination": "Ninh Binh", "summary": "WF_SENTINEL Ninh Binh landscapes", "overnight": "Ninh Binh", "meals": ["Breakfast", "Lunch"], "highlights": ["WF_SENTINEL Trang An"], "notes": ["WF_SENTINEL unhurried"]},
                {"day_number": 3, "destination": "Ninh Binh", "summary": "WF_SENTINEL Ninh Binh river morning", "overnight": "Ninh Binh", "meals": ["Breakfast"], "highlights": ["WF_SENTINEL limestone waterways"], "notes": ["WF_SENTINEL considered"]},
                {"day_number": 4, "destination": "Hanoi", "summary": "WF_SENTINEL Hanoi departure", "overnight": "Hanoi", "meals": ["Breakfast"], "highlights": ["WF_SENTINEL private transfer"], "notes": ["WF_SENTINEL seamless"]},
            ], "special_requirements": ["WF_SENTINEL dietary requirement"],
        },
        "customer_facts": {"customer_name": "WF_SENTINEL Ada and Lin", "adults": 2, "children": 1, "nationality": "Singaporean", "guest_profile": "WF_SENTINEL family", "market": "Singapore", "party_label": "WF_SENTINEL party", "greeting_name": "Ada"},
        "service_facts": {"hotels": [
            {"destination": "Hanoi", "name": "WF_SENTINEL Hanoi Hotel", "room_type": "Suite", "check_in": "2026-10-01", "check_out": "2026-10-02", "intro": "WF_SENTINEL Hanoi intro", "phone": "+84001", "display_city": "HANOI", "display_date": "01 Oct"},
            {"destination": "Ninh Binh", "name": "WF_SENTINEL Ninh Binh Hotel", "room_type": "Villa", "check_in": "2026-10-02", "check_out": "2026-10-04", "intro": "WF_SENTINEL Ninh Binh intro", "phone": "+84002", "display_city": "NINH BINH", "display_date": "02–04 Oct"},
        ], "inclusions": ["WF_SENTINEL inclusion one", "WF_SENTINEL inclusion two"], "exclusions": ["WF_SENTINEL exclusion one", "WF_SENTINEL exclusion two"], "room_notes": "WF_SENTINEL room note"},
        "pricing_facts": {"conditions": ["WF_SENTINEL condition one", "WF_SENTINEL condition two"], "options": [{"id": "wf-signature", "label": "WF_SENTINEL option", "currency": "USD", "per_traveler_amount_minor": 300_000, "group_total_amount_minor": 900_000}]},
        "booking_facts": {"title": "WF_SENTINEL booking title", "description": "WF_SENTINEL booking description", "items": [{"key": "deposit", "label": "WF_SENTINEL deposit", "body": "WF_SENTINEL deposit body"}, {"key": "balance", "label": "WF_SENTINEL balance", "body": "WF_SENTINEL balance body"}]},
        "finalization_facts": {"required_title": "WF_SENTINEL required title", "after_confirmation_title": "WF_SENTINEL after title", "required_items": ["WF_SENTINEL passport"], "after_confirmation_items": ["WF_SENTINEL vouchers"]},
        "seller_facts": {"seller_name": "WF_SENTINEL Seller", "seller_subtitle": "WF_SENTINEL seller subtitle", "seller_email": "seller@example.test", "seller_phone": "+84003", "contact_web": "https://example.test", "designer_name": "WF_SENTINEL Designer", "designer_signature": "WF_SENTINEL signature", "designer_kicker": "WF_SENTINEL designer kicker", "designer_quote": "WF_SENTINEL designer quote", "designer_experience": "WF_SENTINEL experience", "designer_title": "WF_SENTINEL title", "cta_body": "WF_SENTINEL CTA body", "designer_email": "designer@example.test", "designer_phone": "+84004"},
    }


def prepare_workflow_intake(api: CurlApi, facts: dict[str, Any]) -> None:
    """Resolve the disposable fixture through the same editor APIs as Intake.

    A quotation creation is deliberately strict: its selected designer and
    accommodation snapshots must be real, active catalogue records.  Keep the
    curl runner black-box by creating/reusing those records over HTTP rather
    than bypassing the contract with a database fixture.
    """
    workspace = api.request("GET", "/api/v2/workspace/me")
    profile_id = get_path(workspace, "profile.id")
    require(isinstance(profile_id, str) and profile_id, "Workspace identity did not resolve an active Travel Designer.")
    facts["presentation_options"]["travel_designer_id"] = profile_id

    destinations: dict[str, str] = {}
    for hotel in facts["service_facts"]["hotels"]:
        destination_name = hotel["destination"]
        destination_id = destinations.get(destination_name)
        if destination_id is None:
            found = api.request("GET", "/api/v2/destinations", query={"query": destination_name})
            matches = [
                item for item in found.get("items", [])
                if isinstance(item, dict) and item.get("name") == destination_name and isinstance(item.get("id"), str)
            ]
            require(len(matches) == 1, f"Expected exactly one canonical destination for {destination_name!r}: {found}")
            destination_id = matches[0]["id"]
            destinations[destination_name] = destination_id

        existing = api.request(
            "GET",
            "/api/v2/accommodations",
            query={"destinationId": destination_id, "query": hotel["name"]},
        )
        matches = [
            item for item in existing.get("items", [])
            if isinstance(item, dict) and item.get("name") == hotel["name"] and item.get("destination_id") == destination_id
        ]
        if matches:
            accommodation_id = matches[0].get("id")
        else:
            created = api.request(
                "POST",
                "/api/v2/accommodations",
                body={
                    "destinationId": destination_id,
                    **{key: hotel.get(key) for key in ("name", "room_type", "check_in", "check_out", "intro", "phone", "display_city", "display_date")},
                },
            )
            accommodation_id = created.get("id")
        require(isinstance(accommodation_id, str) and accommodation_id, f"Accommodation selection did not return an id for {hotel['name']!r}.")
        hotel["accommodation_id"] = accommodation_id


def assert_fact_step(api: CurlApi, quotation_id: str, facts: dict[str, Any], lang: str) -> tuple[dict[str, Any], int]:
    returned = api.request("GET", f"/api/v2/quotations/{quotation_id}/facts")
    require(returned["facts"]["trip_facts"]["destinations"] == facts["trip_facts"]["destinations"], "Fact route did not round-trip.")
    require(returned["resolvedFacts"]["durationDays"] == 4 and returned["resolvedFacts"]["durationNights"] == 3, "Fact duration interpolation is incorrect.")
    require(returned["resolvedFacts"]["routeLabel"] == "Hanoi · Ninh Binh", "Fact route interpolation is incorrect.")
    require(returned["resolvedFacts"]["partyLabel"] == "2 adults, 1 child", "Fact party interpolation is incorrect.")
    document_response = api.request("GET", f"/api/v2/quotations/{quotation_id}/document", query={"lang": lang})
    document, revision = document_response["document"], document_response["currentRevision"]
    assert_paths_exist(document, (
        "traveler.customerName", "traveler.guestProfile", "traveler.nationality", "traveler.adults", "traveler.children",
        "trip.title", "trip.lede", "trip.durationText", "trip.routeText", "trip.travelDates", "trip.priceBasis",
        "route.title", "route.description", "route.staySegments.0.displayName", "route.staySegments.1.hotelName",
        "itinerary.title", "itinerary.description", "itinerary.days.0.segmentCity", "itinerary.days.0.notes.0", "itinerary.days.1.segmentCity",
        "stays.hotels.0.name", "stays.hotels.0.introduction", "stays.hotels.0.hotelDate", "stays.hotels.0.tel", "stays.hotels.1.name", "stays.roomNotes",
        "pricing.kicker", "pricing.title", "pricing.description", "pricing.ctaLabel", "pricing.options.0.label", "pricing.options.0.groupTotalAmountMinor", "pricing.conditions.0.text",
        "designer.name", "designer.signature", "designer.email",
    ))
    require(get_path(document, "trip.title") == "", "Content-owned trip title was populated before Content Apply.")
    require(get_path(document, "trip.durationText") == "4 days / 3 nights", "Derived duration was not mapped into the brochure document.")
    require(get_path(document, "narrative.letterIntro") == "", "Content field is populated before Content step.")
    return document, revision


def assert_content_candidate(scope: str, draft: dict[str, Any], facts: dict[str, Any]) -> None:
    require(draft["status"] == "draft", f"{scope}: candidate is not a draft.")
    require(not draft["missingInputs"], f"{scope}: generator reported missing inputs: {draft['missingInputs']}")
    if scope == "finalization":
        require(draft["generation"].get("llmCalled") is False, "finalization: deterministic checklist must not call the LLM.")
        require(draft["generation"].get("generationStatus") == "deterministic", "finalization: generation status is not deterministic.")
    else:
        require(draft["generation"].get("llmCalled") is True, f"{scope}: LLM fallback is not accepted by this integration gate.")
        require(draft["generation"].get("generationStatus") == "generated", f"{scope}: generation status is not generated.")
    candidate = draft["candidate"]
    snapshot = draft.get("factsSnapshot") or {}
    if scope == "hero":
        require(bool(get_path(candidate, "trip.lede")) and bool(get_path(candidate, "narrative.coverKicker")), "hero: required generated fields are empty.")
    elif scope == "overview_letter":
        require(all(bool(get_path(candidate, path)) for path in ("narrative.letterIntro", "narrative.letterBody2")), "overview: required generated fields are empty.")
    elif scope in {"route", "itinerary"}:
        require(bool(get_path(candidate, f"{scope}.title")), f"{scope}: generated title is empty.")
    elif scope == "finalization":
        require(bool(get_path(candidate, f"content.sections.{scope}.blocks")), f"{scope}: required canonical blocks are empty.")
    else:
        day = facts["trip_facts"]["itinerary"][int(scope.rsplit(":", 1)[1]) - 1]
        require(get_path(snapshot, "itineraryDay.destination") == day["destination"], f"{scope}: draft provenance lost its destination fact.")
        require(get_path(snapshot, "itineraryDay.summary") == day["summary"], f"{scope}: draft provenance lost its programme fact.")
        require(candidate.get("dayNumber") == day["day_number"], f"{scope}: generated day number drifted.")
        require(bool(candidate.get("description")) and bool(candidate.get("activities")), f"{scope}: required generated fields are empty.")
        require(day["destination"] in " ".join(candidate["description"] + candidate["activities"]), f"{scope}: generated copy lost its destination fact.")
    if not scope.startswith("itinerary:day:"):
        scoped_facts = snapshot.get("facts") or {}
        require(bool(scoped_facts), f"{scope}: draft provenance is empty.")
        if scope in {"hero", "overview_letter", "route"}:
            snapshot_destinations = scoped_facts.get("trip_facts.destinations") or []
            require(snapshot_destinations and snapshot_destinations[0] == facts["trip_facts"]["destinations"][0], f"{scope}: draft provenance lost its route facts.")
        elif scope == "itinerary":
            snapshot_days = scoped_facts.get("trip_facts.itinerary") or []
            expected_days = facts["trip_facts"]["itinerary"]
            require(
                [day.get("destination") for day in snapshot_days] == [day["destination"] for day in expected_days],
                "itinerary: draft provenance lost its itinerary destinations.",
            )
            require(
                [day.get("summary") for day in snapshot_days] == [day["summary"] for day in expected_days],
                "itinerary: draft provenance lost its itinerary programme.",
            )
        elif scope == "finalization":
            require("finalization_facts.required_items" in scoped_facts, "finalization: draft provenance lost its scoped facts.")


def run_content_step(api: CurlApi, quotation_id: str, facts: dict[str, Any], lang: str, revision: int) -> tuple[dict[str, Any], int]:
    scopes = ["hero", "overview_letter", "route", "itinerary", "finalization"] + [f"itinerary:day:{day['day_number']}" for day in facts["trip_facts"]["itinerary"]]
    document: dict[str, Any] = {}
    for scope in scopes:
        created = api.request("POST", f"/api/v2/quotations/{quotation_id}/content-drafts", query={"lang": lang}, body={"scope": scope, "generationMode": "storytelling", "instruction": "ONE_SHOT_WORKFLOW_GUIDANCE"})
        require(bool(created.get("draft")), f"{scope}: expected one content candidate.")
        draft = created["draft"]
        assert_content_candidate(scope, draft, facts)
        review = api.request("GET", f"/api/v2/quotations/{quotation_id}/review-status", query={"lang": lang})
        require(review.get("ready") is False, f"{scope}: incomplete canonical document unexpectedly became publishable.")
        applied = api.request("POST", f"/api/v2/quotations/{quotation_id}/content-drafts/{draft['id']}/apply", body={"baseRevision": revision})
        revision, document = applied["currentRevision"], applied["document"]
        require(applied["draft"]["status"] == "applied", f"{scope}: candidate was not applied.")
        if scope == "hero":
            require(bool(get_path(document, "trip.lede")) and bool(get_path(document, "narrative.coverKicker")), "hero: Apply did not update canonical content.")
        elif scope == "overview_letter":
            require(bool(get_path(document, "narrative.letterIntro")), "overview: Apply did not update canonical content.")
        elif scope in {"route", "itinerary"}:
            require(bool(get_path(document, f"{scope}.title")), f"{scope}: Apply did not update canonical content.")
        elif scope == "finalization":
            require(bool(get_path(document, f"content.sections.{scope}.blocks")), f"{scope}: Apply did not update canonical blocks.")
        elif scope.startswith("itinerary:day:"):
            index = int(scope.rsplit(":", 1)[1]) - 1
            require(bool(get_path(document, f"itinerary.days.{index}.description")), f"{scope}: Apply did not update canonical content.")
    return document, revision


def run_smoke_tier(api: CurlApi, brand_id: str, lang: str, opportunity_prefix: str) -> dict[str, Any]:
    """Fast real API/PostgreSQL proof with no generation, publication, or PDF."""
    quotation_id, _facts, document, revision = create_workflow_quote(api, brand_id, lang, opportunity_prefix)
    review = api.request("GET", f"/api/v2/quotations/{quotation_id}/review-status", query={"lang": lang})
    require(review.get("ready") is False, "A new quotation unexpectedly bypassed the content readiness gate.")
    return {
        "tier": "smoke",
        "quotationId": quotation_id,
        "revision": revision,
        "documentRevision": document.get("meta", {}).get("revision"),
        "assertions": ["facts-save-reload", "canonical-document", "publish-gate"],
    }


def run_workflow_tier(api: CurlApi, brand_id: str, lang: str, opportunity_prefix: str) -> dict[str, Any]:
    """Prove one real LLM request and revision semantics, not every brochure scope."""
    state = run_smoke_tier(api, brand_id, lang, opportunity_prefix)
    quotation_id, revision = state["quotationId"], state["revision"]
    facts = api.request("GET", f"/api/v2/quotations/{quotation_id}/facts")["facts"]
    created = api.request(
        "POST",
        f"/api/v2/quotations/{quotation_id}/content-drafts",
        query={"lang": lang},
        body={"scope": "hero", "generationMode": "storytelling", "instruction": "ONE_SHOT_WORKFLOW_GUIDANCE"},
    )
    draft = created.get("draft")
    require(isinstance(draft, dict), f"hero: expected one draft: {created}")
    assert_content_candidate("hero", draft, facts)
    require("ONE_SHOT_WORKFLOW_GUIDANCE" not in json.dumps(draft.get("generation", {})), "One-shot instruction leaked into draft history.")

    # PATCH is deliberately exercised before Apply.  This proves typed manual
    # review follows the same contract as model output.
    candidate = copy.deepcopy(draft["candidate"])
    candidate["trip"]["lede"] = f"{candidate['trip']['lede']} Reviewed for workflow acceptance."
    patched = api.request(
        "PATCH",
        f"/api/v2/quotations/{quotation_id}/content-drafts/{draft['id']}",
        body={"candidate": candidate},
    )
    require(patched.get("draft", {}).get("candidate", {}).get("trip", {}).get("lede") == candidate["trip"]["lede"], "Typed draft PATCH did not persist.")

    # Advance canonical revision through a real Facts save, then require the
    # stale Apply to fail before retrying with the current revision.  A Design
    # write is intentionally blocked until every section is content-complete.
    advanced = api.request(
        "PUT",
        f"/api/v2/quotations/{quotation_id}/facts",
        query={"baseRevision": revision},
        body=facts,
    )
    current_revision = advanced["currentRevision"]
    conflict = api.request_status(
        "POST",
        f"/api/v2/quotations/{quotation_id}/content-drafts/{draft['id']}/apply",
        body={"baseRevision": revision},
        expected_status=409,
    )
    require(conflict.get("detail", {}).get("currentRevision") == current_revision, f"Stale Apply did not return current revision: {conflict}")
    applied = api.request(
        "POST",
        f"/api/v2/quotations/{quotation_id}/content-drafts/{draft['id']}/apply",
        body={"baseRevision": current_revision},
    )
    revision, document = applied["currentRevision"], applied["document"]
    require(document["trip"]["title"] and document["trip"]["lede"] == candidate["trip"]["lede"], "Hero Apply did not persist the reviewed canonical content.")
    reloaded = api.request("GET", f"/api/v2/quotations/{quotation_id}/content-drafts", query={"lang": lang})
    require("ONE_SHOT_WORKFLOW_GUIDANCE" not in json.dumps(reloaded), "One-shot instruction persisted after reload.")
    manual_candidate = copy.deepcopy(candidate)
    manual_candidate["narrative"]["footerText"] = f"{manual_candidate['narrative']['footerText']} Manually reviewed for workflow acceptance."
    manual_created = api.request(
        "POST",
        f"/api/v2/quotations/{quotation_id}/content-drafts/manual",
        query={"lang": lang},
        body={"scope": "hero", "candidate": manual_candidate, "baseRevision": revision},
    )
    manual_draft = manual_created.get("draft")
    require(isinstance(manual_draft, dict), f"Manual draft was not created: {manual_created}")
    require(manual_draft.get("generationMode") == "manual" and manual_draft.get("generation", {}).get("llmCalled") is False, f"Manual draft unexpectedly called the LLM: {manual_created}")
    manual_applied = api.request(
        "POST",
        f"/api/v2/quotations/{quotation_id}/content-drafts/{manual_draft['id']}/apply",
        body={"baseRevision": revision},
    )
    revision, document = manual_applied["currentRevision"], manual_applied["document"]
    require(document["narrative"]["footerText"] == manual_candidate["narrative"]["footerText"], "Manual draft Apply did not persist canonical content.")
    state.update({
        "tier": "workflow",
        "revision": revision,
        "draftIds": [draft["id"], manual_draft["id"]],
        "assertions": state["assertions"] + ["one-real-llm-scope", "typed-patch", "apply-reload", "expected-409", "instruction-non-persistence", "manual-draft-apply"],
    })
    return state


def run_full_tier(api: CurlApi, brand_id: str, lang: str, opportunity_prefix: str, display_base: str, internal_display_base: str) -> dict[str, Any]:
    """Prepare one publishable release for the separate browser/PDF evidence tier."""
    quotation_id, facts, document, revision = create_workflow_quote(api, brand_id, lang, opportunity_prefix)
    document, revision = run_content_step(api, quotation_id, facts, lang, revision)
    document, revision = run_fact_media_step(api, quotation_id, lang, document, revision)
    document, revision = run_design_step(api, quotation_id, lang, document, revision)
    publication = run_publish_step(api, quotation_id, lang, document, revision, display_base, internal_display_base)
    published = publication["published"]
    return {
        "tier": "full",
        "quotationId": quotation_id,
        "revision": revision,
        "releaseId": published["releaseId"],
        "publishedUrl": published["published_url"],
        "draftIds": [],
        "assertions": ["all-content-scopes", "design-save", "publish-worker", "public-ssr"],
    }


def apply_design_sentinels(document: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(document)
    updated["presentation"].update({"themeId": "brochure", "layoutVersion": 1})
    updated["presentation"].setdefault("copyOverrides", {}).update({"stays.title": "WF_DESIGN Stays", "letter.kicker": "WF_DESIGN Letter"})
    for index, day in enumerate(updated["itinerary"]["days"], 1):
        day["layoutType"] = f"workflow-layout-{index}"
    updated["viewOverrides"] = {"web": {"workflowSentinel": "WF_WEB"}, "pdf": {"workflowSentinel": "WF_PDF"}}
    return updated


_WORKFLOW_PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cfc0000003010185c3e21b0000000049454e44ae426082")


async def _index_workflow_media(keys: list[str]) -> None:
    """Index real disposable R2 objects before selecting them through Facts."""
    database_url = os.environ.get("DATABASE_URL")
    require(bool(database_url), "DATABASE_URL is required to index disposable E2E media.")
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            catalogue = MediaLibraryRepository(session)
            for key in keys:
                await catalogue.upsert_object(
                    run_id=None,
                    bucket="quotation-v2",
                    r2_key=key,
                    parent_prefix=key.rsplit("/", 1)[0],
                    file_name=key.rsplit("/", 1)[-1],
                    content_type="image/png",
                    size_bytes=len(_WORKFLOW_PNG),
                    etag=None,
                    source_modified_at=None,
                )
            await session.commit()
    finally:
        await engine.dispose()


def run_fact_media_step(api: CurlApi, quotation_id: str, lang: str, document: dict[str, Any], revision: int) -> tuple[dict[str, Any], int]:
    """Seed real R2 objects, then select every Fact-owned slot through its API."""
    prefix = f"shared/media/workflow/{quotation_id}"
    slots: list[dict[str, Any]] = []
    assets = (
        ("assets.hero", "hero", "WF_E2E hero image"),
        ("assets.itineraryDivider", "itinerary-divider", "WF_E2E itinerary divider"),
        ("assets.hotelDivider", "hotel-divider", "WF_E2E hotel divider"),
        ("designer.image", "designer", "WF_E2E travel designer"),
    )
    for field_id, name, alt_text in assets:
        slots.append({"fieldId": field_id, "value": {"r2Key": f"{prefix}/{name}.png", "altText": alt_text}})
    for index, _day in enumerate(document["itinerary"]["days"]):
        slots.append({
            "fieldId": f"itinerary.days.{index}.gallery",
            "value": [
                {"r2Key": f"{prefix}/day-{index + 1}-gallery-{image_index}.png", "altText": f"WF_E2E day {index + 1} gallery image {image_index}"}
                for image_index in range(1, 4)
            ],
        })
    for index, _hotel in enumerate(document["stays"]["hotels"]):
        slots.extend((
            {"fieldId": f"stays.hotels.{index}.hotelImage", "value": {"r2Key": f"{prefix}/hotel-{index + 1}.png", "altText": f"WF_E2E hotel {index + 1}"}},
            {"fieldId": f"stays.hotels.{index}.roomImage", "value": {"r2Key": f"{prefix}/room-{index + 1}.png", "altText": f"WF_E2E room {index + 1}"}},
        ))
    keys = [item["value"]["r2Key"] for item in slots if isinstance(item["value"], dict)]
    keys.extend(asset["r2Key"] for item in slots if isinstance(item["value"], list) for asset in item["value"])
    storage = R2Storage()
    for key in keys:
        storage.upload_bytes(key, _WORKFLOW_PNG, "image/png")
    asyncio.run(_index_workflow_media(keys))
    saved = api.request(
        "PUT",
        f"/api/v2/quotations/{quotation_id}/facts/media",
        query={"lang": lang},
        body={"baseRevision": revision, "slots": slots},
    )
    current, next_revision = saved["document"], saved["currentRevision"]
    require(get_path(current, "assets.hero.altText") == "WF_E2E hero image", "Fact media hero alt text did not persist.")
    require(len(get_path(current, "itinerary.days.0.images.carousel")) == 3, "Fact media day gallery did not persist with its required cardinality.")
    require(get_path(current, "stays.hotels.0.hotelImage.r2Key").startswith(prefix), "Fact media hotel image did not persist.")
    return current, next_revision


def run_design_step(api: CurlApi, quotation_id: str, lang: str, document: dict[str, Any], revision: int) -> tuple[dict[str, Any], int]:
    designed = apply_design_sentinels(document)
    saved = api.request("PUT", f"/api/v2/quotations/{quotation_id}/document", query={"lang": lang}, body={"document": designed, "baseRevision": revision})
    current, revision = saved["document"], saved["currentRevision"]
    require(get_path(current, "assets.hero.r2Key") == get_path(document, "assets.hero.r2Key"), "Design save mutated Fact-owned hero media.")
    require(get_path(current, "itinerary.days.0.images.carousel.0.r2Key") == get_path(document, "itinerary.days.0.images.carousel.0.r2Key"), "Design save mutated Fact-owned day media.")
    require(get_path(current, "viewOverrides.pdf.workflowSentinel") == "WF_PDF", "Design PDF override did not persist.")
    require(not any("blob:" in json.dumps(asset) for asset in current.get("assets", {}).values()), "A transient blob asset URL reached canonical state.")
    return current, revision


def run_publish_step(api: CurlApi, quotation_id: str, lang: str, document: dict[str, Any], revision: int, display_base: str, internal_display_base: str) -> dict[str, Any]:
    review = api.request("GET", f"/api/v2/quotations/{quotation_id}/review-status", query={"lang": lang})
    require(review.get("ready") is True and not review.get("missingInputs") and not review.get("contentBlockers"), f"Review is not publishable: {review}")
    published = api.request("POST", f"/api/v2/quotations/{quotation_id}/publish", query={"lang": lang}, body={"baseRevision": revision})
    require(published.get("status") == "queued" and published.get("jobId") and published.get("releaseId") and published.get("published_url"), f"Publish did not queue a complete release: {published}")
    deadline = time.monotonic() + 180
    job: dict[str, Any] = {}
    while time.monotonic() < deadline:
        job = api.request("GET", f"/api/v2/publication-jobs/{published['jobId']}")
        if job.get("status") == "succeeded":
            break
        if job.get("status") == "failed":
            raise WorkflowFailure(f"Publication job failed: {job.get('lastError') or job}")
        time.sleep(1)
    require(job.get("status") == "succeeded", f"Publication job did not finish before timeout: {job}")
    resolved = api.request("GET", f"/api/internal/v2/public-quotations/releases/{published['releaseId']}", service=True)
    # The release resolver returns the frozen document rather than release
    # metadata. Its meta revision is therefore the public proof of the exact
    # revision the release selected.
    require(get_path(resolved["document"], "meta.revision") == revision, "Published release did not use the current document revision.")
    require(get_path(resolved["document"], "assets.hero.r2Key") == get_path(document, "assets.hero.r2Key"), "Published release used stale canonical document assets.")
    # The public URL is deliberately routed through the local/CI Next server
    # with its real brand Host header, so this asserts public SSR rather than a
    # backend-only release resolver.
    public = urlparse(published["published_url"])
    require(bool(public.hostname and public.path), f"Invalid published URL: {published['published_url']}")
    public_html = api.get_text(f"{display_base.rstrip('/')}{public.path}", host=public.hostname)
    # The public Nginx host must deny /internal; assert the dedicated PDF SSR
    # on the service-only Next origin instead of weakening that boundary.
    pdf_html = api.get_text(f"{internal_display_base.rstrip('/')}/internal/releases/{published['releaseId']}/pdf")
    # RouteMapExperience is a client-only island on public web, so its ARIA
    # marker cannot exist in server HTML. PDF uses the same model directly.
    client_only_public_markers = {"/presentation/copyOverrides/a11y.routeMapOverview"}
    for name, html, expectations in (
        ("public", public_html, tuple(item for item in SSR_EDITABLE_FIELD_EXPECTATIONS if item.path not in client_only_public_markers)),
        ("pdf", pdf_html, SSR_EDITABLE_FIELD_EXPECTATIONS),
    ):
        # Trip title is generated Content and must remain free to differ from
        # the fact wording. Hotel identity is a stable Fact-owned SSR proof.
        require("WF_SENTINEL Hanoi Hotel" in html, f"{name} SSR did not render fact sentinel.")
        require("WF_DESIGN Letter" in html, f"{name} SSR did not render shared design copy override.")
        assert_ssr_editable_contract(html, expectations)
    require('data-render-ready="true"' in pdf_html, "Internal PDF SSR did not signal render readiness.")
    print(json.dumps({"status": "passed", "quotationId": quotation_id, "releaseId": published["releaseId"], "version": published["version"], "coverage": [{"path": item.path, "owner": item.owner} for item in COVERAGE_MANIFEST]}, indent=2))
    return {"published": published, "release": resolved}


def create_workflow_quote(api: CurlApi, brand_id: str, lang: str, opportunity_prefix: str) -> tuple[str, dict[str, Any], dict[str, Any], int]:
    facts = make_facts(brand_id, lang, f"{opportunity_prefix}-{uuid.uuid4().hex}")
    prepare_workflow_intake(api, facts)
    created = api.request("POST", "/api/v2/quotations", body=facts)
    quotation_id = created.get("quotationId")
    require(isinstance(quotation_id, str) and quotation_id.startswith("quo_"), f"Invalid create response: {created}")
    document, revision = assert_fact_step(api, quotation_id, facts, lang)
    return quotation_id, facts, document, revision


def run_stale_content_scenario(api: CurlApi, brand_id: str, lang: str) -> None:
    quotation_id, facts, _document, revision = create_workflow_quote(api, brand_id, lang, "stale-content")
    created = api.request("POST", f"/api/v2/quotations/{quotation_id}/content-drafts", query={"lang": lang}, body={"scope": "hero", "generationMode": "storytelling"})
    draft = created["draft"]
    assert_content_candidate("hero", draft, facts)
    updated_facts = copy.deepcopy(facts)
    updated_facts["trip_facts"]["special_requirements"].append("WF_STALE_FACT changed requirement")
    saved = api.request("PUT", f"/api/v2/quotations/{quotation_id}/facts", query={"baseRevision": revision}, body=updated_facts)
    current_revision = saved["currentRevision"]
    require(current_revision > revision, "Fact update did not create a new revision.")
    conflict = api.request_status("POST", f"/api/v2/quotations/{quotation_id}/content-drafts/{draft['id']}/apply", body={"baseRevision": revision}, expected_status=409)
    require("stale" in json.dumps(conflict).lower(), f"Stale content Apply has no diagnostic: {conflict}")
    drafts = api.request("GET", f"/api/v2/quotations/{quotation_id}/content-drafts", query={"lang": lang})["drafts"]
    require(next(item for item in drafts if item["id"] == draft["id"])["status"] == "stale", "Fact update did not persist stale draft status.")


def run_revision_conflict_scenario(api: CurlApi, brand_id: str, lang: str) -> None:
    quotation_id, _facts, _document, revision = create_workflow_quote(api, brand_id, lang, "revision-conflict")
    first = api.request("PUT", f"/api/v2/quotations/{quotation_id}/presentation/overrides", query={"lang": lang}, body={"baseRevision": revision, "copyOverrides": {"nav.routeMap": "WF_WRITER_ONE"}, "identityOverrides": {}})
    conflict = api.request_status("PUT", f"/api/v2/quotations/{quotation_id}/presentation/overrides", query={"lang": lang}, body={"baseRevision": revision, "copyOverrides": {"nav.routeMap": "WF_WRITER_TWO"}, "identityOverrides": {}}, expected_status=409)
    require(conflict.get("detail", {}).get("currentRevision") == first["currentRevision"], f"Revision conflict omitted current revision: {conflict}")
    current = api.request("GET", f"/api/v2/quotations/{quotation_id}/document", query={"lang": lang})
    require(get_path(current["document"], "presentation.copyOverrides.nav.routeMap") == "WF_WRITER_ONE", "Stale writer overwrote the first design copy update.")


def run_asset_failure_scenario(api: CurlApi, brand_id: str, lang: str) -> None:
    quotation_id, _facts, document, revision = create_workflow_quote(api, brand_id, lang, "asset-failure")
    invalid = copy.deepcopy(document)
    invalid["assets"]["hero"] = {"r2Key": "unapproved/workflow/missing.jpg", "status": "ready"}
    saved = api.request("PUT", f"/api/v2/quotations/{quotation_id}/document", query={"lang": lang}, body={"document": invalid, "baseRevision": revision})
    review = api.request("GET", f"/api/v2/quotations/{quotation_id}/review-status", query={"lang": lang})
    require(review["ready"] is False and review["assetReadiness"]["ready"] is False, f"Invalid asset unexpectedly passed review: {review}")
    rejected = api.request_status("POST", f"/api/v2/quotations/{quotation_id}/publish", query={"lang": lang}, body={"baseRevision": saved["currentRevision"]}, expected_status=422)
    require("not ready" in json.dumps(rejected).lower(), f"Publish did not report asset blocker: {rejected}")


def run_release_immutability_scenario(api: CurlApi, brand_id: str, lang: str, display_base: str, internal_display_base: str) -> None:
    quotation_id, _facts, document, revision = create_workflow_quote(api, brand_id, lang, "release-immutability")
    document, revision = run_design_step(api, quotation_id, lang, document, revision)
    published = run_publish_step(api, quotation_id, lang, document, revision, display_base, internal_display_base)
    release_id = published["published"]["releaseId"]
    frozen_title = get_path(published["release"], "document.trip.title")
    changed = api.request("PUT", f"/api/v2/quotations/{quotation_id}/presentation/overrides", query={"lang": lang}, body={"baseRevision": revision, "copyOverrides": {"stays.title": "WF_MUTATED_AFTER_PUBLISH"}, "identityOverrides": {}})
    require(changed["currentRevision"] > revision, "Post-publish mutation did not create a new revision.")
    old_release = api.request("GET", f"/api/internal/v2/public-quotations/releases/{release_id}", service=True)
    require(get_path(old_release, "document.trip.title") == frozen_title, "Published release changed after a later canonical mutation.")
    require(get_path(old_release, "document.presentation.copyOverrides.stays.title") == "WF_DESIGN Stays", "Published release design copy drifted after a later mutation.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    # Browser/PDF acceptance uses E2E_API_BASE_URL, while this curl runner
    # historically used WORKFLOW_API_BASE.  Prefer the explicit workflow
    # override but accept the Compose-wide API contract so an e2e container
    # never resolves its own localhost instead of the app service.
    parser.add_argument("--api-base", default=os.getenv("WORKFLOW_API_BASE") or os.getenv("E2E_API_BASE_URL") or "http://localhost:8111")
    parser.add_argument("--display-base", default=os.getenv("WORKFLOW_DISPLAY_BASE", "http://localhost:8115"))
    parser.add_argument("--internal-display-base", default=os.getenv("WORKFLOW_INTERNAL_DISPLAY_BASE", "http://localhost:8115"))
    parser.add_argument("--editor-email", default=os.getenv("WORKFLOW_EDITOR_EMAIL", "workflow-ci@example.test"))
    parser.add_argument("--service-token", default=os.getenv("QUOTE_SERVICE_TOKEN"))
    parser.add_argument("--brand-id", default=os.getenv("WORKFLOW_BRAND_ID", "vietnam_safar"))
    parser.add_argument("--lang", default=os.getenv("WORKFLOW_LANG", "en"), choices=("en", "vi", "ar"))
    parser.add_argument("--opportunity-id", default=None)
    parser.add_argument("--tier", choices=("smoke", "workflow", "full"), help="Run one fast real-service tier. Omit to use the legacy full scenario selector.")
    parser.add_argument("--report-file", help="Write a compact JSON report for a later tier; contains no credentials or prompt text.")
    parser.add_argument("--scenario", action="append", choices=tuple(item.id for item in WORKFLOW_SCENARIOS if item.tier == "full") + ("nightly",), help="Repeat to run selected full scenarios; nightly runs the full matrix.")
    return parser.parse_args()


def select_scenarios(requested: Iterable[str] | None) -> tuple[WorkflowScenario, ...]:
    requested = tuple(requested or ("happy-path",))
    available = {item.id: item for item in WORKFLOW_SCENARIOS}
    selected_ids = tuple(item.id for item in WORKFLOW_SCENARIOS if item.tier == "full") if "nightly" in requested else requested
    unknown = set(selected_ids) - set(available)
    require(not unknown, f"Unknown workflow scenarios: {sorted(unknown)}")
    selected = tuple(available[item] for item in selected_ids)
    require(all(item.tier == "full" for item in selected), "The curl runner executes full scenarios only; contract/API/SSR tiers run in pytest.")
    return selected


def main() -> int:
    report: dict[str, Any] = {"status": "running"}
    try:
        validate_coverage_manifest()
        validate_test_pyramid_contracts()
        args = parse_args()
        api = CurlApi(args.api_base, args.editor_email, args.service_token)
        if args.tier:
            if args.tier in {"workflow", "full"}:
                require(os.getenv("ENABLE_LLM_QUOTE_GENERATION", "1").lower() not in {"0", "false", "no"}, "ENABLE_LLM_QUOTE_GENERATION must be enabled for this tier.")
            prefix = args.opportunity_id or f"{args.tier}-tier"
            if args.tier == "smoke":
                report = run_smoke_tier(api, args.brand_id, args.lang, prefix)
            elif args.tier == "workflow":
                report = run_workflow_tier(api, args.brand_id, args.lang, prefix)
            else:
                report = run_full_tier(api, args.brand_id, args.lang, prefix, args.display_base, args.internal_display_base)
            report["status"] = "passed"
            write_tier_report(args.report_file, report)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0
        scenarios = select_scenarios(args.scenario)
        if any(item.requires_llm for item in scenarios):
            require(os.getenv("ENABLE_LLM_QUOTE_GENERATION", "1").lower() not in {"0", "false", "no"}, "ENABLE_LLM_QUOTE_GENERATION must be enabled for the selected scenarios.")
        for scenario in scenarios:
            if scenario.id == "happy-path":
                quotation_id, facts, document, revision = create_workflow_quote(api, args.brand_id, args.lang, args.opportunity_id or "happy-path")
                document, revision = run_content_step(api, quotation_id, facts, args.lang, revision)
                document, revision = run_fact_media_step(api, quotation_id, args.lang, document, revision)
                document, revision = run_design_step(api, quotation_id, args.lang, document, revision)
                run_publish_step(api, quotation_id, args.lang, document, revision, args.display_base, args.internal_display_base)
            elif scenario.id == "stale-content":
                run_stale_content_scenario(api, args.brand_id, args.lang)
            elif scenario.id == "revision-conflict":
                run_revision_conflict_scenario(api, args.brand_id, args.lang)
            elif scenario.id == "asset-failure":
                run_asset_failure_scenario(api, args.brand_id, args.lang)
            elif scenario.id == "release-immutability":
                run_release_immutability_scenario(api, args.brand_id, args.lang, args.display_base, args.internal_display_base)
            else:
                raise WorkflowFailure(f"Scenario {scenario.id} has no executable runner.")
        report = {"status": "passed", "tier": "legacy-full-scenarios", "scenarios": [item.id for item in scenarios]}
        write_tier_report(args.report_file, report)
        return 0
    except WorkflowFailure as exc:
        report.update({"status": "failed", "error": str(exc)})
        write_tier_report(getattr(locals().get("args", None), "report_file", None), report)
        print(f"WORKFLOW FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        report.update({"status": "failed", "error": str(exc)})
        write_tier_report(getattr(locals().get("args", None), "report_file", None), report)
        print(f"WORKFLOW FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
