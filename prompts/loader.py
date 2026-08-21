"""Versioned Prompt Loader & Aggregator for Content Generation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROMPTS_DIR = Path(__file__).parent

@dataclass(frozen=True)
class PromptBundle:
    version: str
    scope: str
    mode: str
    system_prompt: str
    user_prompt: str
    mode_contract: str
    effective_instruction: str
    facts_snapshot: dict[str, Any]

    def public_payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "scope": self.scope,
            "mode": self.mode,
            "systemPrompt": self.system_prompt,
            "userPrompt": self.user_prompt,
            "modeContract": self.mode_contract,
            "effectiveInstruction": self.effective_instruction,
            "factsSnapshot": self.facts_snapshot,
        }


class PromptLoader:
    def __init__(self, version: str = "v1") -> None:
        self.version = version
        self.version_dir = PROMPTS_DIR / version
        if not self.version_dir.exists():
            raise ValueError(f"Prompt version directory not found: {self.version_dir}")
        self._ground_rules = self._load_yaml(self.version_dir / "ground_rules.yaml")
        self._system_base = self._load_yaml(self.version_dir / "system_base.yaml")
        self._recipes = self._load_yaml(self.version_dir / "prompt_recipes.yaml")
        self._section_cache: dict[str, dict[str, Any]] = {}
        self._mode_cache: dict[str, dict[str, Any]] = {}
        self._brand_cache: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def get_recipes(self) -> dict[str, Any]:
        return self._recipes.get("recipes", {})

    def get_recipe(self, scope: str) -> dict[str, Any]:
        base_scope = "itinerary_day" if scope.startswith("itinerary:day:") else scope
        recipes = self.get_recipes()
        return recipes.get(base_scope, {})

    def get_section_config(self, scope: str) -> dict[str, Any]:
        base_scope = "itinerary_day" if scope.startswith("itinerary:day:") else scope
        if base_scope not in self._section_cache:
            path = self.version_dir / "sections" / f"{base_scope}.yaml"
            self._section_cache[base_scope] = self._load_yaml(path)
        return self._section_cache[base_scope]

    def get_mode_config(self, mode: str) -> dict[str, Any]:
        if mode not in self._mode_cache:
            path = self.version_dir / "modes" / f"{mode}.yaml"
            self._mode_cache[mode] = self._load_yaml(path)
        return self._mode_cache[mode]

    def get_brand_config(self, brand_id: str) -> dict[str, Any]:
        if brand_id not in self._brand_cache:
            path = self.version_dir / "brands" / f"{brand_id}.yaml"
            self._brand_cache[brand_id] = self._load_yaml(path)
        return self._brand_cache[brand_id]

    def get_active_ground_rules(
        self,
        scope: str,
        facts_snapshot: dict[str, Any] | None = None,
        disabled_rule_ids: list[str] | set[str] | None = None,
    ) -> list[dict[str, Any]]:
        matching_scopes = {scope}
        if scope.startswith("itinerary:day:") or scope == "itinerary_days_batch":
            matching_scopes.add("itinerary_day")
        if scope == "brochure_narrative_batch":
            matching_scopes.update(["hero", "overview_letter", "route", "itinerary"])

        rules_list = self._ground_rules.get("rules", [])
        active = []
        disabled_set = set(disabled_rule_ids or [])

        # Analyze facts snapshot for smart rule filtering if present
        is_tour = False
        is_city_only = False
        is_free_day = False
        has_accommodation = False

        if facts_snapshot and "itinerary_day" in matching_scopes and scope != "itinerary_days_batch":
            acts = facts_snapshot.get("activities") or facts_snapshot.get("highlights") or []
            dest = facts_snapshot.get("destination") or facts_snapshot.get("summary")
            summary_lower = str(facts_snapshot.get("summary", "")).lower()

            if "free day" in summary_lower or "at leisure" in summary_lower:
                is_free_day = True
            elif len(acts) > 0:
                is_tour = True
            elif dest:
                is_city_only = True

            if facts_snapshot.get("hotel") or facts_snapshot.get("accommodation"):
                has_accommodation = True

        for r in rules_list:
            r_id = r.get("id")
            if r_id in disabled_set:
                continue
            target_scopes = r.get("scopes", [])
            if not any(s in target_scopes for s in matching_scopes):
                continue

            # Smart Filtering for single itinerary_day rules
            if "itinerary_day" in matching_scopes and scope != "itinerary_days_batch" and facts_snapshot:
                if r_id == "GR-TOUR-FULLDAY" and not is_tour and (is_city_only or is_free_day):
                    continue
                if r_id == "GR-CITY-INTRO" and not is_city_only and (is_tour or is_free_day):
                    continue
                if r_id == "GR-FREE-FULL-DAY" and not is_free_day and (is_tour or is_city_only):
                    continue
                if r_id == "GR-ACCOMMODATION" and not has_accommodation:
                    # Keep GR-ACCOMMODATION as general unless explicitly omitted
                    pass

            active.append(r)
        return active

    def get_default_instruction(self, scope: str, mode: str) -> str:
        mode_cfg = self.get_mode_config(mode)
        default_insts = mode_cfg.get("default_instructions", {})
        base_scope = "itinerary_day" if scope.startswith("itinerary:day:") else scope
        if base_scope in default_insts:
            return default_insts[base_scope]
        return f"Write only the {scope} content."

    def build_system_prompt(
        self,
        scope: str,
        brand_name: str,
        brand_tone: str,
        vocabulary: list[str],
        avoid: list[str],
        brand_id: str | None = None,
        mode: str | None = None,
        facts_snapshot: dict[str, Any] | None = None,
        disabled_rule_ids: list[str] | set[str] | None = None,
        disabled_components: list[str] | set[str] | None = None,
    ) -> str:
        sec_config = self.get_section_config(scope)
        section_rules = sec_config.get("rules", [])
        dis_comps = set(disabled_components or [])

        # Fallback to YAML brand profile if brand_tone/vocabulary/avoid are empty or None
        b_cfg = self.get_brand_config(brand_id) if brand_id else {}
        effective_tone = (brand_tone or "").strip() or b_cfg.get("tone", "")
        effective_vocab = [v for v in (vocabulary or b_cfg.get("vocabulary", [])) if v]
        effective_avoid = [a for a in (avoid or b_cfg.get("avoid", [])) if a]

        # 1. Static Prefix: Role, Brand, Tone, Vocab, Goal
        prompt_parts = []
        if "role_base" not in dis_comps:
            prompt_parts.append(f"Role: {self._system_base.get('role', 'senior luxury travel copywriter')}.")
            tone_str = f" Tone: {effective_tone}" if effective_tone else ""
            prompt_parts.append(f"Brand: {brand_name}.{tone_str}".strip())

            vocab_parts = []
            if effective_vocab:
                vocab_parts.append(f"Preferred vocabulary: {', '.join(effective_vocab)}.")
            if effective_avoid:
                vocab_parts.append(f"Avoid: {', '.join(effective_avoid)}.")
            if vocab_parts:
                prompt_parts.append(" ".join(vocab_parts))

            prompt_parts.append(f"Goal: {self._system_base.get('goal', 'return brochure-ready plain-text fields')}")

        # 2. Brand Voice Guidelines (Static per Brand)
        if brand_id and "brand_voice" not in dis_comps:
            b_rules = b_cfg.get("brand_voice_rules", [])
            if b_rules:
                prompt_parts.append("- Brand Voice Guidelines:\n  " + "\n  ".join([f"• {r}" for r in b_rules]))

        # 3. Writing Mode Rules (Static per Mode)
        if mode and "mode_style" not in dis_comps:
            m_cfg = self.get_mode_config(mode)
            m_rules = m_cfg.get("style_rules", [])
            if m_rules:
                prompt_parts.append("- Writing Mode Rules:\n  " + "\n  ".join([f"• {r}" for r in m_rules]))

        # 4. Scope-Filtered Ground Rules
        if "ground_rules" not in dis_comps:
            active_grs = self.get_active_ground_rules(scope, facts_snapshot, disabled_rule_ids=disabled_rule_ids)
            if active_grs:
                gr_items = [f"• [{r.get('id')}] {r.get('name')}: {r.get('text', '').strip()}" for r in active_grs]
                prompt_parts.append("- Ground Rules:\n  " + "\n  ".join(gr_items))

        # 5. Section Specific Rules
        if section_rules and "section_rules" not in dis_comps:
            prompt_parts.append("- Section Rules:\n  " + "\n  ".join([f"• {r}" for r in section_rules]))

        # 6. Base Constraints & Validation
        if "base_constraints" not in dis_comps:
            prompt_parts.append("Constraints: " + " ".join(self._system_base.get("constraints", [])))
        if "validation" not in dis_comps:
            prompt_parts.append(f"Validation: {self._system_base.get('validation', 'satisfy the structured output schema exactly.')}")

        return "\n".join(prompt_parts)

    def build_prompt_bundle(
        self,
        *,
        scope: str,
        brand_name: str,
        brand_tone: str,
        vocabulary: list[str],
        avoid: list[str],
        mode: str,
        effective_instruction: str,
        facts_snapshot: dict[str, Any],
        brand_id: str | None = None,
        disabled_rule_ids: list[str] | set[str] | None = None,
        disabled_components: list[str] | set[str] | None = None,
    ) -> PromptBundle:
        system_prompt = self.build_system_prompt(
            scope,
            brand_name,
            brand_tone,
            vocabulary,
            avoid,
            brand_id=brand_id,
            mode=mode,
            facts_snapshot=facts_snapshot,
            disabled_rule_ids=disabled_rule_ids,
            disabled_components=disabled_components,
        )

        mode_cfg = self.get_mode_config(mode)
        mode_contract = mode_cfg.get(
            "mode_contract",
            "Detailed mode: prefer exact sequence and restrained language." if mode == "detailed" else "Storytelling mode: add sensory cadence supported by facts.",
        ).strip()

        from services.content_draft_service import _clean_none_values
        clean_facts = _clean_none_values(facts_snapshot)

        user_prompt = (
            f"Scope: {scope}\n"
            f"Writing instruction: {effective_instruction}\n\n"
            "Input Facts (JSON):\n"
            f"{json.dumps(clean_facts, ensure_ascii=False, sort_keys=True)}"
        )

        return PromptBundle(
            version=self.version,
            scope=scope,
            mode=mode,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            mode_contract=mode_contract,
            effective_instruction=effective_instruction,
            facts_snapshot=facts_snapshot,
        )


_default_loader = PromptLoader("v1")

def get_prompt_loader(version: str = "v1") -> PromptLoader:
    if version == "v1":
        return _default_loader
    return PromptLoader(version)
