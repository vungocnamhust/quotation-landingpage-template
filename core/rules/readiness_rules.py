"""Gate 3 & 4: Content Completeness and Public Release Readiness Gates."""

from __future__ import annotations

from typing import Any
from core.rules.base import GateIssue, GateResult, Severity


class PublishReadinessGate:
    """Evaluates whether a Quotation Document is 100% ready for public release & PDF rendering."""

    def evaluate(self, document_context: dict[str, Any]) -> GateResult:
        issues: list[GateIssue] = []

        # 1. Facts Readiness
        trip = document_context.get("trip") or document_context.get("trip_facts") or {}
        customer = document_context.get("customer") or document_context.get("customer_facts") or {}
        pricing = document_context.get("pricing") or document_context.get("pricing_facts") or {}

        if not trip.get("start_date") or not trip.get("end_date"):
            issues.append(
                GateIssue(
                    field="trip.dates",
                    code="MISSING_TOUR_DATES",
                    message="Tour start and end dates must be configured before publishing.",
                    severity=Severity.ERROR,
                )
            )

        itinerary = trip.get("itinerary") or []
        if not itinerary or len(itinerary) == 0:
            issues.append(
                GateIssue(
                    field="trip.itinerary",
                    code="EMPTY_ITINERARY",
                    message="Quotation must contain at least 1 itinerary day.",
                    severity=Severity.ERROR,
                )
            )

        options = pricing.get("options") or []
        if not options or len(options) == 0:
            issues.append(
                GateIssue(
                    field="pricing.options",
                    code="MISSING_PRICING_TIER",
                    message="At least one commercial pricing tier must be set before release.",
                    severity=Severity.ERROR,
                )
            )

        # 2. Content Completeness (Hero & Narrative)
        narrative = document_context.get("narrative") or {}
        hero_title = (trip.get("title") or "").strip()
        hero_lede = (trip.get("lede") or "").strip()

        if not hero_title:
            issues.append(
                GateIssue(
                    field="trip.title",
                    code="HERO_TITLE_EMPTY",
                    message="Hero trip title is required for brochure presentation.",
                    severity=Severity.ERROR,
                )
            )

        if not hero_lede:
            issues.append(
                GateIssue(
                    field="trip.lede",
                    code="HERO_LEDE_EMPTY",
                    message="Hero lede / trip overview sentence is required.",
                    severity=Severity.WARNING,
                    suggestion="Add a captivating 1-2 sentence overview in Content Studio.",
                )
            )

        passed = len([i for i in issues if i.severity == Severity.ERROR]) == 0
        return GateResult(passed=passed, issues=issues)
