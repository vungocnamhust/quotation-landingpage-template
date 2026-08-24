"""Typed, scope-limited LLM generation for Content Studio drafts."""
from __future__ import annotations

import json
from typing import Any, Type

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from pydantic_ai import Agent

import llm_client
from quote_document import BrandProfile
from services.content_registry import ContentSectionSpec, scope_spec


BRAND_POLICY_VERSION = "luxury-premium-en-v1"


class ContentGenerationError(RuntimeError):
    """The provider did not yield a valid candidate; no draft is persisted."""


class _CopyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def _clean_text(cls, value: Any, info: ValidationInfo) -> Any:
        if isinstance(value, str):
            value = " ".join(value.split())
            if info.field_name in {"heroMeta1", "heroMeta2"}:
                if "<" in value or ">" in value:
                    raise ValueError("Copy must not contain HTML.")
                return value
            if not value or "<" in value or ">" in value:
                raise ValueError("Copy must be non-empty plain text without HTML.")
        return value


from core.rules.content_budgets import get_content_budget_registry

_budget_reg = get_content_budget_registry("v1")


class HeroOutput(_CopyModel):
    title: str = Field(
        min_length=_budget_reg.get_spec("hero", "trip_title").min_chars if _budget_reg.get_spec("hero", "trip_title") else 1,
        max_length=_budget_reg.get_max_chars("hero", "trip_title", 160),
    )
    lede: str = Field(
        min_length=_budget_reg.get_spec("hero", "trip_lede").min_chars if _budget_reg.get_spec("hero", "trip_lede") else 1,
        max_length=_budget_reg.get_max_chars("hero", "trip_lede", 500),
    )
    coverKicker: str = Field(
        min_length=_budget_reg.get_spec("hero", "cover_kicker").min_chars if _budget_reg.get_spec("hero", "cover_kicker") else 1,
        max_length=_budget_reg.get_max_chars("hero", "cover_kicker", 120),
    )
    heroMeta1: str = Field(default="", max_length=_budget_reg.get_max_chars("hero", "hero_meta_1", 160))
    heroMeta2: str = Field(default="", max_length=_budget_reg.get_max_chars("hero", "hero_meta_2", 160))
    footerText: str = Field(
        min_length=_budget_reg.get_spec("hero", "footer_text").min_chars if _budget_reg.get_spec("hero", "footer_text") else 1,
        max_length=_budget_reg.get_max_chars("hero", "footer_text", 500),
    )


class OverviewOutput(_CopyModel):
    journeyOverviewTitle: str = Field(
        min_length=_budget_reg.get_spec("overview_letter", "overview_title").min_chars if _budget_reg.get_spec("overview_letter", "overview_title") else 1,
        max_length=_budget_reg.get_max_chars("overview_letter", "overview_title", 160),
    )
    letterHighlight: str = Field(
        min_length=_budget_reg.get_spec("overview_letter", "letter_highlight").min_chars if _budget_reg.get_spec("overview_letter", "letter_highlight") else 1,
        max_length=_budget_reg.get_max_chars("overview_letter", "letter_highlight", 500),
    )
    letterGreeting: str = Field(
        min_length=_budget_reg.get_spec("overview_letter", "letter_greeting").min_chars if _budget_reg.get_spec("overview_letter", "letter_greeting") else 1,
        max_length=_budget_reg.get_max_chars("overview_letter", "letter_greeting", 160),
    )
    letterIntro: str = Field(
        min_length=_budget_reg.get_spec("overview_letter", "letter_intro").min_chars if _budget_reg.get_spec("overview_letter", "letter_intro") else 1,
        max_length=_budget_reg.get_max_chars("overview_letter", "letter_intro", 1600),
    )
    letterBody2: str = Field(
        min_length=_budget_reg.get_spec("overview_letter", "letter_body").min_chars if _budget_reg.get_spec("overview_letter", "letter_body") else 1,
        max_length=_budget_reg.get_max_chars("overview_letter", "letter_body", 1600),
    )
    letterOutro: str = Field(
        min_length=_budget_reg.get_spec("overview_letter", "letter_outro").min_chars if _budget_reg.get_spec("overview_letter", "letter_outro") else 1,
        max_length=_budget_reg.get_max_chars("overview_letter", "letter_outro", 1600),
    )
    letterSignOff: str = Field(
        min_length=_budget_reg.get_spec("overview_letter", "letter_signoff").min_chars if _budget_reg.get_spec("overview_letter", "letter_signoff") else 1,
        max_length=_budget_reg.get_max_chars("overview_letter", "letter_signoff", 160),
    )
    letterSender: str = Field(
        min_length=_budget_reg.get_spec("overview_letter", "letter_sender").min_chars if _budget_reg.get_spec("overview_letter", "letter_sender") else 1,
        max_length=_budget_reg.get_max_chars("overview_letter", "letter_sender", 160),
    )


class RouteOutput(_CopyModel):
    title: str = Field(
        min_length=_budget_reg.get_spec("route", "route_title").min_chars if _budget_reg.get_spec("route", "route_title") else 1,
        max_length=_budget_reg.get_max_chars("route", "route_title", 160),
    )
    description: str = Field(
        min_length=_budget_reg.get_spec("route", "route_description").min_chars if _budget_reg.get_spec("route", "route_description") else 1,
        max_length=_budget_reg.get_max_chars("route", "route_description", 1600),
    )
    mapSegmentDescriptions: list[str] = Field(default_factory=list, max_length=64)


class ItineraryOutput(RouteOutput):
    pass


class DayOutput(_CopyModel):
    title: str = Field(
        min_length=_budget_reg.get_spec("itinerary_day", "title").min_chars if _budget_reg.get_spec("itinerary_day", "title") else 1,
        max_length=_budget_reg.get_max_chars("itinerary_day", "title", 160),
    )
    description: list[str] = Field(min_length=1, max_length=6)
    activities: list[str] = Field(
        default_factory=list,
        max_length=_budget_reg.get_spec("itinerary_day", "activities").max_items if _budget_reg.get_spec("itinerary_day", "activities") else 12,
    )

    @field_validator("description", "activities", mode="after")
    @classmethod
    def _clean_items(cls, value: list[str]) -> list[str]:
        cleaned = [" ".join(item.split()) for item in value]
        if any(not item or "<" in item or ">" in item for item in cleaned):
            raise ValueError("List copy must contain non-empty plain-text items.")
        return cleaned


class BrochureNarrativeBatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hero: HeroOutput
    overview_letter: OverviewOutput
    route: RouteOutput
    itinerary: ItineraryOutput


class ItineraryDaysBatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days: list[DayOutput] = Field(min_length=1, max_length=64)


def normalize_instruction(instruction: str) -> str:
    return " ".join(instruction.split())


def default_instruction(scope: str, mode: str) -> str:
    from prompts.loader import get_prompt_loader
    return get_prompt_loader().get_default_instruction(scope, mode)


class SectionContentGenerator:
    """One typed Pydantic AI request per scope, or parallel dual-stream batch generation."""

    _models: dict[str, Type[_CopyModel]] = {
        "hero": HeroOutput,
        "overview_letter": OverviewOutput,
        "route": RouteOutput,
        "itinerary": ItineraryOutput,
    }

    def _output_model(self, scope: str) -> Type[_CopyModel]:
        return DayOutput if scope.startswith("itinerary:day:") else self._models[scope]

    @staticmethod
    def build_prompt_bundle(
        *,
        scope: str,
        brand: BrandProfile,
        facts_snapshot: dict[str, Any],
        mode: str,
        instruction: str,
    ) -> PromptBundle:
        from prompts.loader import get_prompt_loader
        loader = get_prompt_loader()
        policy = brand.content_policy
        effective_instruction = normalize_instruction(instruction) or default_instruction(scope, mode)
        return loader.build_prompt_bundle(
            scope=scope,
            brand_name=brand.display_name,
            brand_tone=policy.tone,
            vocabulary=list(policy.vocabulary),
            avoid=list(policy.avoid),
            mode=mode,
            effective_instruction=effective_instruction,
            facts_snapshot=facts_snapshot,
            brand_id=brand.brand_id,
        )

    @staticmethod
    def _system_prompt(brand: BrandProfile, scope: str = "hero") -> str:
        from prompts.loader import get_prompt_loader
        policy = brand.content_policy
        return get_prompt_loader().build_system_prompt(
            scope=scope,
            brand_name=brand.display_name,
            brand_tone=policy.tone,
            vocabulary=list(policy.vocabulary),
            avoid=list(policy.avoid),
        )

    @staticmethod
    def _prompt(*, scope: str, mode: str, effective_instruction: str, facts_snapshot: dict[str, Any]) -> str:
        mode_contract = (
            "Detailed mode: prefer exact sequence and restrained language; do not add operational detail."
            if mode == "detailed"
            else "Storytelling mode: add sensory cadence only when it is supported by the facts; remain restrained."
        )
        return (
            f"Scope: {scope}\n"
            f"Mode contract: {mode_contract}\n"
            f"Writing instruction: {effective_instruction}\n"
            "Input data (authoritative JSON):\n"
            f"{json.dumps(facts_snapshot, ensure_ascii=False, sort_keys=True)}\n"
            "Return only the structured response requested by the schema."
        )

    @staticmethod
    def _candidate(scope: str, output: _CopyModel) -> dict[str, Any]:
        data = output.model_dump(mode="json")
        if scope == "hero":
            return {"trip": {"title": data["title"], "lede": data["lede"]}, "narrative": {"coverKicker": data["coverKicker"], "heroMeta1": data["heroMeta1"], "heroMeta2": data["heroMeta2"], "footerText": data["footerText"]}}
        if scope == "overview_letter":
            return {"narrative": data}
        if scope == "route":
            return {"route": data}
        if scope == "itinerary":
            return {"itinerary": data}
        return {"sourceFactId": scope.rsplit(":", 1)[-1], **data}

    async def generate(
        self,
        *,
        spec: ContentSectionSpec,
        brand: BrandProfile,
        facts_snapshot: dict[str, Any],
        mode: str,
        instruction: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        effective_instruction = normalize_instruction(instruction) or default_instruction(spec.scope, mode)
        source = "custom" if normalize_instruction(instruction) else "default"
        bundle = self.build_prompt_bundle(
            scope=spec.scope,
            brand=brand,
            facts_snapshot=facts_snapshot,
            mode=mode,
            instruction=effective_instruction,
        )
        model = self._output_model(spec.scope)
        agent = Agent(
            model=llm_client.get_model(),
            output_type=model,
            system_prompt=bundle.system_prompt,
            retries=2,
        )
        try:
            result = await agent.run(bundle.user_prompt)
        except Exception as exc:
            raise ContentGenerationError("Content generation did not return a valid draft. Please retry.") from exc
        return self._candidate(spec.scope, result.output), {
            "instructionSource": source,
            "effectiveInstruction": effective_instruction,
            "brandPolicyVersion": BRAND_POLICY_VERSION,
            "systemPrompt": bundle.system_prompt,
            "userPrompt": bundle.user_prompt,
            "promptVersion": bundle.version,
        }

    async def generate_narrative_batch(
        self,
        *,
        brand: BrandProfile,
        facts_snapshot: dict[str, Any],
        mode: str,
        instruction: str = "",
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        effective_instruction = normalize_instruction(instruction) or default_instruction("brochure_narrative_batch", mode)
        source = "custom" if normalize_instruction(instruction) else "default"
        bundle = self.build_prompt_bundle(
            scope="brochure_narrative_batch",
            brand=brand,
            facts_snapshot=facts_snapshot,
            mode=mode,
            instruction=effective_instruction,
        )
        agent = Agent(
            model=llm_client.get_model(),
            output_type=BrochureNarrativeBatchOutput,
            system_prompt=bundle.system_prompt,
            retries=2,
        )
        try:
            result = await agent.run(bundle.user_prompt)
        except Exception as exc:
            raise ContentGenerationError("Narrative batch generation did not return valid copy. Please retry.") from exc

        output: BrochureNarrativeBatchOutput = result.output
        candidates = {
            "hero": self._candidate("hero", output.hero),
            "overview_letter": self._candidate("overview_letter", output.overview_letter),
            "route": self._candidate("route", output.route),
            "itinerary": self._candidate("itinerary", output.itinerary),
        }
        metadata = {
            "instructionSource": source,
            "effectiveInstruction": effective_instruction,
            "brandPolicyVersion": BRAND_POLICY_VERSION,
            "systemPrompt": bundle.system_prompt,
            "userPrompt": bundle.user_prompt,
            "promptVersion": bundle.version,
        }
        return candidates, metadata

    async def generate_itinerary_days_batch(
        self,
        *,
        brand: BrandProfile,
        facts_snapshot: dict[str, Any],
        mode: str,
        instruction: str = "",
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        effective_instruction = normalize_instruction(instruction) or default_instruction("itinerary_days_batch", mode)
        source = "custom" if normalize_instruction(instruction) else "default"
        bundle = self.build_prompt_bundle(
            scope="itinerary_days_batch",
            brand=brand,
            facts_snapshot=facts_snapshot,
            mode=mode,
            instruction=effective_instruction,
        )
        agent = Agent(
            model=llm_client.get_model(),
            output_type=ItineraryDaysBatchOutput,
            system_prompt=bundle.system_prompt,
            retries=2,
        )
        try:
            result = await agent.run(bundle.user_prompt)
        except Exception as exc:
            raise ContentGenerationError("Itinerary days batch generation did not return valid copy. Please retry.") from exc

        output: ItineraryDaysBatchOutput = result.output
        input_days = facts_snapshot.get("itinerary_days") or facts_snapshot.get("itinerary") or []
        candidates = []
        for idx, day_model in enumerate(output.days):
            input_day = input_days[idx] if idx < len(input_days) and isinstance(input_days[idx], dict) else {}
            day_num = input_day.get("day_number") or input_day.get("dayNumber") or idx + 1
            day_data = day_model.model_dump(mode="json")
            source_fact_id = input_day.get("source_fact_id") or input_day.get("sourceFactId") or str(day_num)
            candidates.append({"sourceFactId": source_fact_id, "dayNumber": day_num, **day_data})

        metadata = {
            "instructionSource": source,
            "effectiveInstruction": effective_instruction,
            "brandPolicyVersion": BRAND_POLICY_VERSION,
            "systemPrompt": bundle.system_prompt,
            "userPrompt": bundle.user_prompt,
            "promptVersion": bundle.version,
        }
        return candidates, metadata
