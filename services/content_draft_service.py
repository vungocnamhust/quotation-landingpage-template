from __future__ import annotations

import json
import time
import uuid
from hashlib import sha256
from typing import Any

from quote_document import BrandProfile, CreateQuoteRequestV1, QuoteDocumentV1, validate_quote_content_block
from repositories.quotation_repository import ContentDraftRepository
from services.content_registry import CONTENT_SECTION_REGISTRY, scope_spec
from services.section_content_generator import BRAND_POLICY_VERSION, ContentGenerationError, SectionContentGenerator, default_instruction, normalize_instruction


PROMPT_VERSION = "content-studio-v3"


def _fact_value(payload: CreateQuoteRequestV1, path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        value = getattr(value, part, None)
        if value is None:
            return None
    return _json_fact_value(value)


def _clean_none_values(val: Any) -> Any:
    if isinstance(val, dict):
        cleaned = {}
        for k, v in val.items():
            res = _clean_none_values(v)
            if res is not None and res != "" and res != [] and res != {}:
                cleaned[k] = res
        return cleaned
    if isinstance(val, list):
        cleaned = [_clean_none_values(item) for item in val]
        return [item for item in cleaned if item is not None and item != "" and item != [] and item != {}]
    return val


def _json_fact_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _clean_none_values(value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, list):
        return _clean_none_values([_json_fact_value(item) for item in value])
    if isinstance(value, dict):
        return _clean_none_values({str(key): _json_fact_value(item) for key, item in value.items()})
    return value


def _fingerprint(*, spec, lang: str, mode: str, facts_hash: str, instruction: str) -> str:
    payload = {
        "promptVersion": PROMPT_VERSION,
        "recipeVersion": spec.recipe_version,
        "schemaVersion": spec.schema_version,
        "brandPolicyVersion": BRAND_POLICY_VERSION,
        "lang": lang,
        "mode": mode,
        "factsHash": facts_hash,
        "instructionHash": sha256(instruction.encode("utf-8")).hexdigest(),
    }
    return f"cs3-{sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()[:60]}"


REQUEST_BRIEF_KEYS = [
    "occasion",
    "primary_theme",
    "travel_pace",
    "interests",
    "must_have",
    "avoid",
    "dietary",
    "halal",
    "mobility",
    "dining_level",
    "client_context",
]


def extract_request_brief(request_payload: dict[str, Any] | None) -> dict[str, Any]:
    request_brief: dict[str, Any] = {}
    if not request_payload or not isinstance(request_payload, dict):
        return request_brief
    for key in REQUEST_BRIEF_KEYS:
        val = request_payload.get(key)
        if val is not None and val != "" and val != [] and val != {}:
            request_brief[key] = val
    return request_brief


class ContentDraftService:
    def __init__(self, repository: ContentDraftRepository, brand_profile: BrandProfile) -> None:
        self.repository = repository
        self.brand_profile = brand_profile
        self.generator = SectionContentGenerator()

    @staticmethod
    def valid_scope(scope: str) -> bool:
        try:
            scope_spec(scope)
            return True
        except ValueError:
            return False

    @staticmethod
    def missing_for_scope(payload: CreateQuoteRequestV1, scope: str) -> list[dict[str, str]]:
        spec = scope_spec(scope)
        if scope in {"hero", "overview_letter"}:
            return [{"path": "trip_facts.destinations", "reason": "Select at least one destination before generating this section."}] if not payload.trip_facts.destinations else []
        if scope.startswith("itinerary:day:"):
            number = int(scope.rsplit(":", 1)[-1])
            day = next((item for item in payload.trip_facts.itinerary if item.day_number == number), None)
            if day is None:
                return [{"path": "trip_facts.itinerary", "reason": f"Day {number} no longer exists."}]
            missing = []
            if not day.destination:
                missing.append({"path": f"trip_facts.itinerary[{number - 1}].destination", "reason": "Select a destination."})
            if not (day.summary or day.highlights):
                missing.append({"path": f"trip_facts.itinerary[{number - 1}].summary", "reason": "Add a summary or highlights before generating the day narrative."})
            return missing
        return [{"path": path, "reason": "Required Facts are missing for this section."} for path in spec.required_facts if not _fact_value(payload, path)]

    @staticmethod
    def facts_snapshot(payload: CreateQuoteRequestV1, scope: str, request_brief: dict[str, Any] | None = None) -> dict[str, Any]:
        if scope.startswith("itinerary:day:"):
            number = int(scope.rsplit(":", 1)[-1])
            day = next((item for item in payload.trip_facts.itinerary if item.day_number == number), None)
            snapshot = {"itineraryDay": {"dayNumber": number, "destination": day.destination if day else "", "summary": day.summary if day else "", "highlights": day.highlights if day else [], "meals": day.meals if day else [], "overnight": day.overnight if day else ""}}
            if request_brief:
                snapshot["request_brief"] = request_brief
            return snapshot
        spec = scope_spec(scope)
        snapshot = {"facts": {path: _fact_value(payload, path) for path in spec.fact_allowlist}}
        if request_brief:
            snapshot["request_brief"] = request_brief
        return snapshot

    @staticmethod
    def deterministic_rich_candidate(payload: CreateQuoteRequestV1, scope: str) -> dict[str, Any]:
        if scope != "finalization":
            raise ValueError(f"{scope} is Fact-owned and cannot create a Content candidate.")
        groups = []
        if payload.finalization_facts.required_items:
            groups.append({"title": payload.finalization_facts.required_title or "Final Details Required", "items": list(payload.finalization_facts.required_items)})
        if payload.finalization_facts.after_confirmation_items:
            groups.append({"title": payload.finalization_facts.after_confirmation_title or "After Confirmation", "items": list(payload.finalization_facts.after_confirmation_items)})
        return {"content": {"sections": {scope: {"blocks": [{"type": "checklistGroups", "groups": groups}]}}}}

    @staticmethod
    def validate_candidate(scope: str, candidate: dict[str, Any]) -> dict[str, Any]:
        spec = scope_spec(scope)
        if spec.owner != "content":
            raise ValueError(f"{scope} is Fact-owned and has no editable Content candidate.")
        allowed = {
            "hero": {"trip", "narrative"}, "overview_letter": {"narrative"}, "route": {"route"},
            "itinerary": {"itinerary"}, "finalization": {"content"},
        }
        if scope.startswith("itinerary:day:"):
            allowed[scope] = {"dayNumber", "title", "description", "activities"}
        if set(candidate) != allowed.get(scope, set()):
            raise ValueError("Candidate contains fields not owned by this content scope.")
        if scope == "finalization":
            sections = ((candidate.get("content") or {}).get("sections") or {})
            blocks = ((sections.get(scope) or {}).get("blocks") or [])
            if set(sections) != {scope}:
                raise ValueError("Candidate may only update its own rich-content section.")
            for block in blocks:
                validate_quote_content_block(block)
        else:
            # Validate manual edits against the exact typed contract used for generation.
            from services.section_content_generator import DayOutput, HeroOutput, ItineraryOutput, OverviewOutput, RouteOutput
            if scope == "hero":
                trip, narrative = candidate.get("trip"), candidate.get("narrative")
                if not isinstance(trip, dict) or not isinstance(narrative, dict):
                    raise ValueError("Hero candidate must contain plain-text trip and narrative fields.")
                raw = {"title": trip.get("title"), "lede": trip.get("lede"), **narrative}
            else:
                raw = candidate if scope.startswith("itinerary:day:") else next(iter(candidate.values()))
            model = DayOutput if scope.startswith("itinerary:day:") else {"hero": HeroOutput, "overview_letter": OverviewOutput, "route": RouteOutput, "itinerary": ItineraryOutput}[scope]
            if scope.startswith("itinerary:day:"):
                raw = {key: value for key, value in raw.items() if key != "dayNumber"}
            model.model_validate(raw)
        return candidate

    @staticmethod
    def apply_candidate(document: dict[str, Any], scope: str, candidate: dict[str, Any]) -> dict[str, Any]:
        ContentDraftService.validate_candidate(scope, candidate)
        merged = dict(document)
        if scope.startswith("itinerary:day:"):
            number = int(scope.rsplit(":", 1)[-1])
            days = ((merged.get("itinerary") or {}).get("days") or [])
            day = next((item for item in days if item.get("dayNumber") == number), None)
            if day is None:
                raise ValueError("Itinerary day no longer exists.")
            day.update({key: candidate[key] for key in ("title", "description", "activities")})
        elif scope == "finalization":
            merged.setdefault("content", {}).setdefault("sections", {})[scope] = candidate["content"]["sections"][scope]
        else:
            for key in ("trip", "narrative", "route", "itinerary"):
                if key in candidate:
                    if scope == "route" and key == "route":
                        route_candidate = dict(candidate["route"])
                        descriptions = route_candidate.pop("mapSegmentDescriptions", [])
                        merged.setdefault("route", {}).update(route_candidate)
                        for index, description in enumerate(descriptions):
                            segments = merged["route"].get("staySegments") or []
                            if index < len(segments):
                                segments[index]["mapSegmentDesc"] = description
                    else:
                        merged.setdefault(key, {}).update(candidate[key])
        return QuoteDocumentV1.model_validate(merged).model_dump(mode="json")

    async def create(
        self,
        *,
        quotation_id: str,
        payload: CreateQuoteRequestV1,
        facts_hash: str,
        document_revision: int,
        lang: str,
        scope: str,
        mode: str,
        instruction: str = "",
        request_payload: dict[str, Any] | None = None,
    ) -> list[Any]:
        spec = scope_spec(scope)
        if spec.owner != "content":
            raise ValueError(f"{scope} is Fact-owned and cannot be generated or edited in Content Studio.")
        normalized_instruction = normalize_instruction(instruction)
        effective_instruction = normalized_instruction or default_instruction(scope, mode)
        prompt_version = _fingerprint(spec=spec, lang=lang, mode=mode, facts_hash=facts_hash, instruction=effective_instruction)
        cached = await self.repository.find_cached(quotation_id=quotation_id, lang=lang, scope=scope, mode=mode, facts_hash=facts_hash, prompt_version=prompt_version)
        if cached:
            cached.generation_metadata = {**cached.generation_metadata, "cached": True}
            return [cached]
        request_brief = extract_request_brief(request_payload)
        snapshot = self.facts_snapshot(payload, scope, request_brief=request_brief)
        missing = self.missing_for_scope(payload, scope)
        metadata = {"mode": mode, "recipeVersion": spec.recipe_version, "schemaVersion": spec.schema_version, "brandPolicyVersion": BRAND_POLICY_VERSION, "instructionSource": "custom" if normalized_instruction else "default", "instructionHash": sha256(effective_instruction.encode("utf-8")).hexdigest()[:16]}
        if missing:
            return [await self.repository.create(id=f"cd_{uuid.uuid4().hex[:20]}", quotation_id=quotation_id, lang=lang, scope=scope, generation_mode=mode, status="draft", facts_hash=facts_hash, source_document_revision=document_revision, prompt_version=prompt_version, facts_snapshot=snapshot, candidate_json={}, missing_inputs=missing, generation_metadata={**metadata, "llmCalled": False, "generationStatus": "missing_inputs", "warnings": []})]
        if scope == "finalization":
            candidate = self.deterministic_rich_candidate(payload, scope)
            self.validate_candidate(scope, candidate)
            return [await self.repository.create(id=f"cd_{uuid.uuid4().hex[:20]}", quotation_id=quotation_id, lang=lang, scope=scope, generation_mode=mode, status="draft", facts_hash=facts_hash, source_document_revision=document_revision, prompt_version=prompt_version, facts_snapshot=snapshot, candidate_json=candidate, missing_inputs=[], generation_metadata={**metadata, "llmCalled": False, "generationStatus": "deterministic", "warnings": []})]
        started = time.perf_counter()
        candidate, generation = await self.generator.generate(spec=spec, brand=self.brand_profile, facts_snapshot=snapshot, mode=mode, instruction=normalized_instruction)
        self.validate_candidate(scope, candidate)
        return [await self.repository.create(id=f"cd_{uuid.uuid4().hex[:20]}", quotation_id=quotation_id, lang=lang, scope=scope, generation_mode=mode, status="draft", facts_hash=facts_hash, source_document_revision=document_revision, prompt_version=prompt_version, facts_snapshot=snapshot, candidate_json=candidate, missing_inputs=[], generation_metadata={**metadata, "instructionSource": generation["instructionSource"], "systemPrompt": generation.get("systemPrompt", ""), "userPrompt": generation.get("userPrompt", ""), "promptVersion": generation.get("promptVersion", "v1"), "llmCalled": True, "generationStatus": "generated", "latencyMs": round((time.perf_counter() - started) * 1000), "warnings": []})]

    async def create_batch(
        self,
        *,
        quotation_id: str,
        payload: CreateQuoteRequestV1,
        facts_hash: str,
        document_revision: int,
        lang: str,
        mode: str,
        instruction: str = "",
        request_payload: dict[str, Any] | None = None,
    ) -> list[Any]:
        import asyncio
        request_brief = extract_request_brief(request_payload)

        # 1. Prepare Narrative facts snapshot
        narrative_snapshot = {
            "trip": {
                "destinations": payload.trip_facts.destinations,
                "start_date": payload.trip_facts.start_date,
                "end_date": payload.trip_facts.end_date,
                "duration_days": payload.trip_facts.duration_days,
                "duration_nights": payload.trip_facts.duration_nights,
            },
            "customer": {
                "customer_name": payload.customer_facts.customer_name,
                "adults": payload.customer_facts.adults,
                "children": payload.customer_facts.children,
            },
            "itinerary_overview": [
                {
                    "day_number": day.day_number,
                    "destination": day.destination,
                    "summary": day.summary,
                    "overnight": day.overnight,
                }
                for day in payload.trip_facts.itinerary
            ],
        }
        # Travel pace belongs to the originating Request brief, not immutable
        # quotation Facts.  It is optional prompt context, never a Fact field.
        if request_brief.get("travel_pace"):
            narrative_snapshot["trip"]["travel_pace"] = request_brief["travel_pace"]
        if request_brief:
            narrative_snapshot["request_brief"] = request_brief

        # 2. Prepare Days facts snapshot
        days_snapshot = {
            "itinerary_days": [
                {
                    "day_number": day.day_number,
                    "destination": day.destination,
                    "summary": day.summary,
                    "highlights": day.highlights,
                    "meals": day.meals,
                    "overnight": day.overnight,
                    "accommodation_name": getattr(day, "accommodation_name", None),
                }
                for day in payload.trip_facts.itinerary
            ]
        }
        if request_brief:
            days_snapshot["request_brief"] = request_brief

        # 3. Launch both tasks in parallel with asyncio.gather
        started = time.perf_counter()
        tasks = [
            self.generator.generate_narrative_batch(
                brand=self.brand_profile,
                facts_snapshot=narrative_snapshot,
                mode=mode,
                instruction=instruction,
            )
        ]
        has_itinerary_days = bool(payload.trip_facts.itinerary)
        if has_itinerary_days:
            tasks.append(
                self.generator.generate_itinerary_days_batch(
                    brand=self.brand_profile,
                    facts_snapshot=days_snapshot,
                    mode=mode,
                    instruction=instruction,
                )
            )

        results = await asyncio.gather(*tasks)
        narrative_candidates, narrative_gen = results[0]
        days_candidates, days_gen = results[1] if has_itinerary_days else ([], {})
        duration_ms = round((time.perf_counter() - started) * 1000)

        created_drafts = []

        # 4. Save Narrative scopes: hero, overview_letter, route, itinerary
        for scope_key, candidate in narrative_candidates.items():
            spec = scope_spec(scope_key)
            self.validate_candidate(scope_key, candidate)
            prompt_version = _fingerprint(
                spec=spec, lang=lang, mode=mode, facts_hash=facts_hash, instruction=instruction or default_instruction("brochure_narrative_batch", mode)
            )
            draft = await self.repository.create(
                id=f"cd_{uuid.uuid4().hex[:20]}",
                quotation_id=quotation_id,
                lang=lang,
                scope=scope_key,
                generation_mode=mode,
                status="draft",
                facts_hash=facts_hash,
                source_document_revision=document_revision,
                prompt_version=prompt_version,
                facts_snapshot=self.facts_snapshot(payload, scope_key, request_brief=request_brief),
                candidate_json=candidate,
                missing_inputs=[],
                generation_metadata={
                    "mode": mode,
                    "recipeVersion": spec.recipe_version,
                    "schemaVersion": spec.schema_version,
                    "brandPolicyVersion": BRAND_POLICY_VERSION,
                    "instructionSource": narrative_gen.get("instructionSource", "default"),
                    "systemPrompt": narrative_gen.get("systemPrompt", ""),
                    "userPrompt": narrative_gen.get("userPrompt", ""),
                    "promptVersion": narrative_gen.get("promptVersion", "v1"),
                    "llmCalled": True,
                    "batchGeneration": True,
                    "generationStatus": "generated",
                    "latencyMs": duration_ms,
                    "warnings": [],
                },
            )
            created_drafts.append(draft)

        # 5. Save Itinerary Days scopes: itinerary:day:1 .. itinerary:day:N
        for day_candidate in days_candidates:
            day_num = day_candidate.get("dayNumber", 1)
            scope_key = f"itinerary:day:{day_num}"
            spec = scope_spec(scope_key)
            self.validate_candidate(scope_key, day_candidate)
            prompt_version = _fingerprint(
                spec=spec, lang=lang, mode=mode, facts_hash=facts_hash, instruction=instruction or default_instruction("itinerary_days_batch", mode)
            )
            draft = await self.repository.create(
                id=f"cd_{uuid.uuid4().hex[:20]}",
                quotation_id=quotation_id,
                lang=lang,
                scope=scope_key,
                generation_mode=mode,
                status="draft",
                facts_hash=facts_hash,
                source_document_revision=document_revision,
                prompt_version=prompt_version,
                facts_snapshot=self.facts_snapshot(payload, scope_key, request_brief=request_brief),
                candidate_json=day_candidate,
                missing_inputs=[],
                generation_metadata={
                    "mode": mode,
                    "recipeVersion": spec.recipe_version,
                    "schemaVersion": spec.schema_version,
                    "brandPolicyVersion": BRAND_POLICY_VERSION,
                    "instructionSource": days_gen.get("instructionSource", "default"),
                    "systemPrompt": days_gen.get("systemPrompt", ""),
                    "userPrompt": days_gen.get("userPrompt", ""),
                    "promptVersion": days_gen.get("promptVersion", "v1"),
                    "llmCalled": True,
                    "batchGeneration": True,
                    "generationStatus": "generated",
                    "latencyMs": duration_ms,
                    "warnings": [],
                },
            )
            created_drafts.append(draft)

        return created_drafts

    def preview_prompt(
        self,
        payload: CreateQuoteRequestV1,
        scope: str,
        mode: str,
        instruction: str = "",
        request_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        spec = scope_spec(scope)
        if spec.owner != "content":
            raise ValueError(f"{scope} is Fact-owned and has no prompt preview.")
        request_brief = extract_request_brief(request_payload)
        snapshot = self.facts_snapshot(payload, scope, request_brief=request_brief)
        bundle = self.generator.build_prompt_bundle(
            scope=spec.scope,
            brand=self.brand_profile,
            facts_snapshot=snapshot,
            mode=mode,
            instruction=instruction,
        )
        return bundle.public_payload()

    async def create_manual(self, *, quotation_id: str, payload: CreateQuoteRequestV1, facts_hash: str, document_revision: int, lang: str, scope: str, candidate: dict[str, Any]) -> Any:
        spec = scope_spec(scope)
        if spec.owner != "content":
            raise ValueError(f"{scope} is Fact-owned and cannot be edited in Content Studio.")
        validated = self.validate_candidate(scope, candidate)
        candidate_hash = sha256(json.dumps(validated, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
        return await self.repository.create(
            id=f"cd_{uuid.uuid4().hex[:20]}", quotation_id=quotation_id, lang=lang,
            scope=scope, generation_mode="manual", status="draft", facts_hash=facts_hash,
            source_document_revision=document_revision, prompt_version=f"manual:{spec.schema_version}:{candidate_hash}",
            facts_snapshot=self.facts_snapshot(payload, scope), candidate_json=validated, missing_inputs=[],
            generation_metadata={"generationStatus": "manual", "llmCalled": False, "warnings": [], "recipeVersion": spec.recipe_version, "schemaVersion": spec.schema_version, "brandPolicyVersion": BRAND_POLICY_VERSION, "instructionSource": "manual"},
        )
