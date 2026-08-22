"""Unified Content Budgets & Metric Specification (Single Source of Truth Loader)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


@dataclass(frozen=True)
class ContentBudgetSpec:
    field_id: str
    label: str
    path: tuple[str | int, ...]
    control: str = "input"
    required: bool = True
    min_chars: int = 1
    max_chars: int = 1600
    pdf_ceiling_chars: int = 1600
    target_words: str | None = None
    target_paragraphs: int | None = None
    target_formula: str | None = None
    prompt_rule: str | None = None
    buffer_chars: int | None = None
    buffer_rationale: str | None = None
    max_items: int | None = None
    pdf_max_items: int | None = None

    def public_payload(self) -> dict[str, Any]:
        return {
            "fieldId": self.field_id,
            "label": self.label,
            "path": list(self.path),
            "control": self.control,
            "required": self.required,
            "minChars": self.min_chars,
            "maxChars": self.max_chars,
            "pdfCeilingChars": self.pdf_ceiling_chars,
            "targetWords": self.target_words,
            "targetParagraphs": self.target_paragraphs,
            "targetFormula": self.target_formula,
            "promptRule": self.prompt_rule,
            "bufferChars": self.buffer_chars,
            "maxItems": self.max_items,
            "pdfMaxItems": self.pdf_max_items,
        }


class ContentBudgetRegistry:
    def __init__(self, version: str = "v1") -> None:
        self.version = version
        self.file_path = PROMPTS_DIR / version / "content_budgets.yaml"
        self._raw_data: dict[str, Any] = {}
        self._specs: dict[str, dict[str, ContentBudgetSpec]] = {}
        self._pdf_ceilings: dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            return
        with open(self.file_path, "r", encoding="utf-8") as f:
            self._raw_data = yaml.safe_load(f) or {}

        budgets_map = self._raw_data.get("budgets", {})
        for scope, fields_dict in budgets_map.items():
            if not isinstance(fields_dict, dict):
                continue
            self._specs[scope] = {}
            for field_name, spec_dict in fields_dict.items():
                if not isinstance(spec_dict, dict):
                    continue
                path_raw = spec_dict.get("path", [field_name])
                path = tuple(path_raw) if isinstance(path_raw, list) else (str(path_raw),)
                spec = ContentBudgetSpec(
                    field_id=str(spec_dict.get("field_id") or field_name),
                    label=str(spec_dict.get("label") or field_name),
                    path=path,
                    control=str(spec_dict.get("control") or "input"),
                    required=bool(spec_dict.get("required", True)),
                    min_chars=int(spec_dict.get("min_chars", 1)),
                    max_chars=int(spec_dict.get("max_chars", 1600)),
                    pdf_ceiling_chars=int(spec_dict.get("pdf_ceiling_chars", 1600)),
                    target_words=spec_dict.get("target_words"),
                    target_paragraphs=spec_dict.get("target_paragraphs"),
                    target_formula=spec_dict.get("target_formula"),
                    prompt_rule=spec_dict.get("prompt_rule"),
                    buffer_chars=spec_dict.get("buffer_chars"),
                    buffer_rationale=spec_dict.get("buffer_rationale"),
                    max_items=spec_dict.get("max_items"),
                    pdf_max_items=spec_dict.get("pdf_max_items"),
                )
                self._specs[scope][field_name] = spec

                # Index PDF ceilings
                self._pdf_ceilings[spec.field_id] = spec.pdf_ceiling_chars
                if field_name != spec.field_id:
                    self._pdf_ceilings[field_name] = spec.pdf_ceiling_chars

        # Add metric aliases for PDF preflight
        self._pdf_ceilings.update({
            "day_title": self.get_pdf_ceiling("itinerary_day", "title", 170),
            "day_description": self.get_pdf_ceiling("itinerary_day", "description", 1150),
            "hotel_intro": self.get_pdf_ceiling("hotel_plan", "hotel_intro", 300),
            "hotel_total_copy": self.get_pdf_ceiling("hotel_plan", "hotel_total_copy", 2100),
            "hero_title": self.get_pdf_ceiling("hero", "trip_title", 160),
            "hero_lede": self.get_pdf_ceiling("hero", "trip_lede", 500),
            "overview_highlight": self.get_pdf_ceiling("overview_letter", "letter_highlight", 500),
            "overview_letter_total": self.get_pdf_ceiling("overview_letter", "total_letter", 4000),
            "route_stop_description": self.get_pdf_ceiling("route", "map_segment_descriptions", 500),
            "payment_terms_max_count": int(self.get_spec("payment_terms", "items_count").pdf_max_items or 4) if self.get_spec("payment_terms", "items_count") else 4,
            "payment_term_body": self.get_pdf_ceiling("payment_terms", "item_body", 1600),
        })

    def get_spec(self, scope: str, field_key: str) -> ContentBudgetSpec | None:
        base_scope = "itinerary_day" if scope.startswith("itinerary:day:") else scope
        return self._specs.get(base_scope, {}).get(field_key)

    def get_max_chars(self, scope: str, field_key: str, default: int = 1600) -> int:
        spec = self.get_spec(scope, field_key)
        return spec.max_chars if spec else default

    def get_pdf_ceiling(self, scope_or_metric: str, field_key: str | None = None, default: int = 1600) -> int:
        if field_key is not None:
            spec = self.get_spec(scope_or_metric, field_key)
            return spec.pdf_ceiling_chars if spec else default
        return self._pdf_ceilings.get(scope_or_metric, default)

    def get_pdf_ceilings_map(self) -> dict[str, int]:
        return dict(self._pdf_ceilings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "pdfCeilings": self.get_pdf_ceilings_map(),
            "budgets": {
                scope: {f_name: spec.public_payload() for f_name, spec in fields.items()}
                for scope, fields in self._specs.items()
            },
        }


_default_registry = ContentBudgetRegistry("v1")


def get_content_budget_registry(version: str = "v1") -> ContentBudgetRegistry:
    if version == "v1":
        return _default_registry
    return ContentBudgetRegistry(version)
