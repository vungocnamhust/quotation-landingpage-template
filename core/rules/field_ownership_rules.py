"""Gate 4: 1-Ownership of Fields, Brand Isolation, and Mutation Boundaries."""

from __future__ import annotations

from enum import Enum
from typing import Any
from core.rules.base import GateIssue, GateResult, Severity


class FieldPartition(str, Enum):
    FACTS = "facts"      # Controlled by Sale & Client Agreement. Read-only for AI.
    CONTENT = "content"  # Controlled by AI Content Studio & Sale Editor.
    DESIGN = "design"    # Controlled by Brand & Theme Engine.


FACTS_FIELDS: frozenset[str] = frozenset({
    "customer_name",
    "adults",
    "children",
    "kid_ages",
    "market",
    "nationality",
    "start_date",
    "end_date",
    "duration_days",
    "duration_nights",
    "itinerary",
    "destinations",
    "hotels",
    "pricing",
    "inclusions",
    "exclusions",
    "booking_items",
})

CONTENT_FIELDS: frozenset[str] = frozenset({
    "hero_lede",
    "overview_letter",
    "day_storytelling",
    "day_highlights",
    "day_meal_notes",
    "hotel_intro",
    "media_assets",
    "room_notes",
})

DESIGN_FIELDS: frozenset[str] = frozenset({
    "brand_id",
    "template_id",
    "theme_id",
    "color_palette",
    "typography_tokens",
    "view_mode",
    "pdf_layout",
})

# Brand-protected fields that cannot be overwritten during presentation HTML synchronization
BRAND_PROTECTED_FIELDS: frozenset[str] = frozenset({
    "brand_id",
    "brand_name",
    "brand_logo",
    "brand_accent",
    "brand_contact_email",
    "brand_contact_phone",
    "brand_website",
})


class FieldOwnershipGate:
    """Evaluates whether a mutation payload respects field boundaries and brand protections."""

    def evaluate_ai_mutation(self, mutated_fields: list[str]) -> GateResult:
        """Ensures AI Content Studio cannot mutate immutable facts or brand design settings."""
        issues: list[GateIssue] = []

        for field in mutated_fields:
            if field in FACTS_FIELDS:
                issues.append(
                    GateIssue(
                        field=field,
                        code="FACTS_MUTATION_FORBIDDEN",
                        message=f"AI Content Agent is not allowed to mutate factual field '{field}'.",
                        severity=Severity.ERROR,
                    )
                )
            elif field in DESIGN_FIELDS:
                issues.append(
                    GateIssue(
                        field=field,
                        code="DESIGN_MUTATION_FORBIDDEN",
                        message=f"AI Content Agent is not allowed to mutate design configuration '{field}'.",
                        severity=Severity.ERROR,
                    )
                )

        passed = len([i for i in issues if i.severity == Severity.ERROR]) == 0
        return GateResult(passed=passed, issues=issues)

    def is_field_mutable_by(self, field_name: str, actor: str) -> bool:
        """Check if a specific actor ('sale', 'ai', 'designer', 'sync') is permitted to mutate the field."""
        actor_clean = actor.strip().lower()
        if actor_clean in ("sale", "staff"):
            return True
        if actor_clean == "ai":
            return field_name in CONTENT_FIELDS
        if actor_clean == "designer":
            return field_name in DESIGN_FIELDS or field_name in CONTENT_FIELDS
        if actor_clean == "sync":
            return field_name not in BRAND_PROTECTED_FIELDS and field_name not in FACTS_FIELDS
        return False
