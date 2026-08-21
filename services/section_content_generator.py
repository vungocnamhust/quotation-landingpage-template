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


class HeroOutput(_CopyModel):
    title: str = Field(min_length=1, max_length=160)
    lede: str = Field(min_length=1, max_length=500)
    coverKicker: str = Field(min_length=1, max_length=120)
    heroMeta1: str = Field(default="", max_length=160)
    heroMeta2: str = Field(default="", max_length=160)
    footerText: str = Field(min_length=1, max_length=500)


class OverviewOutput(_CopyModel):
    journeyOverviewTitle: str = Field(min_length=1, max_length=160)
    letterHighlight: str = Field(min_length=1, max_length=500)
    letterGreeting: str = Field(min_length=1, max_length=160)
    letterIntro: str = Field(min_length=1, max_length=1600)
    letterBody2: str = Field(min_length=1, max_length=1600)
    letterOutro: str = Field(min_length=1, max_length=1600)
    letterSignOff: str = Field(min_length=1, max_length=160)
    letterSender: str = Field(min_length=1, max_length=160)


class RouteOutput(_CopyModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1600)
    mapSegmentDescriptions: list[str] = Field(default_factory=list, max_length=64)


class ItineraryOutput(RouteOutput):
    pass


class DayOutput(_CopyModel):
    title: str = Field(min_length=1, max_length=160)
    description: list[str] = Field(min_length=1, max_length=6)
    activities: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("description", "activities", mode="after")
    @classmethod
    def _clean_items(cls, value: list[str]) -> list[str]:
        cleaned = [" ".join(item.split()) for item in value]
        if any(not item or "<" in item or ">" in item for item in cleaned):
            raise ValueError("List copy must contain non-empty plain-text items.")
        return cleaned


def normalize_instruction(instruction: str) -> str:
    return " ".join(instruction.split())


def default_instruction(scope: str, mode: str) -> str:
    from prompts.loader import get_prompt_loader
    return get_prompt_loader().get_default_instruction(scope, mode)


class SectionContentGenerator:
    """One typed Pydantic AI request per scope, never a broad narrative result."""

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
        return {"dayNumber": int(scope.rsplit(":", 1)[-1]), **data}

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

