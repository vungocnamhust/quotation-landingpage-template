"""Gate 2: Quotation Transition & Fact Feasibility Rules."""

from datetime import date
from typing import Any
from core.rules.base import GateIssue, GateResult, Severity


def parse_iso_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


class QuotationTransitionGate:
    """Evaluates whether facts & overrides satisfy Gate 2 before generating a Quotation Document."""

    def evaluate(self, context: dict[str, Any]) -> GateResult:
        issues: list[GateIssue] = []
        derived_data: dict[str, Any] = {}

        # 1. Identity Gate
        customer_name = (context.get("customer_name") or "").strip()
        if not customer_name or len(customer_name) < 2:
            issues.append(
                GateIssue(
                    field="customer_name",
                    code="CUSTOMER_NAME_REQUIRED",
                    message="Client or Family display name is required (minimum 2 characters).",
                    severity=Severity.ERROR,
                )
            )

        # 2. Party Gate
        adults = context.get("adults")
        if adults is None or adults < 1:
            issues.append(
                GateIssue(
                    field="adults",
                    code="INVALID_ADULTS",
                    message="Adult count must be at least 1.",
                    severity=Severity.ERROR,
                )
            )

        children = context.get("children") or 0
        if children < 0:
            issues.append(
                GateIssue(
                    field="children",
                    code="INVALID_CHILDREN",
                    message="Children count cannot be negative.",
                    severity=Severity.ERROR,
                )
            )
        elif children > 0:
            kid_ages = context.get("kid_ages") or []
            if len(kid_ages) != children:
                issues.append(
                    GateIssue(
                        field="kid_ages",
                        code="KID_AGES_MISMATCH",
                        message=f"Please specify ages for all {children} children (provided {len(kid_ages)}).",
                        severity=Severity.WARNING,
                        suggestion="Enter child ages to ensure accurate room bedding & policy calculation.",
                    )
                )

        # 3. Dates & Duration Gate
        start_date_str = context.get("start_date")
        end_date_str = context.get("end_date")
        start_date = parse_iso_date(start_date_str)
        end_date = parse_iso_date(end_date_str)

        if not start_date:
            issues.append(
                GateIssue(
                    field="start_date",
                    code="START_DATE_REQUIRED",
                    message="A valid start date (YYYY-MM-DD) is required for quotation scheduling.",
                    severity=Severity.ERROR,
                )
            )
        if not end_date:
            issues.append(
                GateIssue(
                    field="end_date",
                    code="END_DATE_REQUIRED",
                    message="A valid end date (YYYY-MM-DD) is required for quotation scheduling.",
                    severity=Severity.ERROR,
                )
            )

        duration_days: int | None = None
        if start_date and end_date:
            if end_date < start_date:
                issues.append(
                    GateIssue(
                        field="end_date",
                        code="END_DATE_BEFORE_START",
                        message="End date must be on or after start date.",
                        severity=Severity.ERROR,
                    )
                )
            else:
                duration_days = (end_date - start_date).days + 1
                derived_data["duration_days"] = duration_days
                derived_data["duration_nights"] = max(0, duration_days - 1)

        # 4. Itinerary Route Gate
        itinerary = context.get("itinerary_with_stays") or context.get("itinerary") or []
        if not isinstance(itinerary, list) or len(itinerary) == 0:
            issues.append(
                GateIssue(
                    field="itinerary",
                    code="ITINERARY_EMPTY",
                    message="Daily itinerary cannot be empty.",
                    severity=Severity.ERROR,
                )
            )
        else:
            if duration_days and len(itinerary) != duration_days:
                issues.append(
                    GateIssue(
                        field="itinerary",
                        code="ITINERARY_LENGTH_MISMATCH",
                        message=f"Itinerary has {len(itinerary)} days, but date range spans {duration_days} days.",
                        severity=Severity.WARNING,
                        suggestion="Align itinerary length with start and end dates.",
                    )
                )

            missing_dest_days: list[int] = []
            for idx, day in enumerate(itinerary):
                dest = day.get("destination") if isinstance(day, dict) else getattr(day, "destination", None)
                if not dest or not str(dest).strip():
                    day_num = day.get("day_number", idx + 1) if isinstance(day, dict) else idx + 1
                    missing_dest_days.append(day_num)

            if missing_dest_days:
                issues.append(
                    GateIssue(
                        field="itinerary.destination",
                        code="MISSING_DESTINATIONS",
                        message=f"Days without destination: {', '.join(str(d) for d in missing_dest_days)}.",
                        severity=Severity.ERROR,
                        suggestion="Enter at least a city or region name for each day.",
                    )
                )

        # 5. Commercial Pricing Gate
        pricing = context.get("pricing") or {}
        per_adult = pricing.get("per_adult_amount_minor") or pricing.get("per_traveler_amount_minor")
        group_total = pricing.get("group_total_amount_minor")

        if (not per_adult or per_adult <= 0) and (not group_total or group_total <= 0):
            issues.append(
                GateIssue(
                    field="pricing",
                    code="PRICING_REQUIRED",
                    message="Commercial pricing must have at least Per Adult Price or Group Total Price > 0.",
                    severity=Severity.ERROR,
                )
            )

        # 6. Brand & Ownership Gate
        brand_id = context.get("brand_id")
        if not brand_id:
            issues.append(
                GateIssue(
                    field="brand_id",
                    code="BRAND_REQUIRED",
                    message="Publishing brand must be specified.",
                    severity=Severity.ERROR,
                )
            )

        passed = len([i for i in issues if i.severity == Severity.ERROR]) == 0
        return GateResult(passed=passed, issues=issues, derived_data=derived_data)
