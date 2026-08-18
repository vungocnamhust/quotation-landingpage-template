"""Gate 1: Request Intake & Scoping Rules."""

import re
from typing import Any
from core.rules.base import GateIssue, GateResult, Severity

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RequestIntakeGate:
    """Evaluates whether a newly submitted Quote Request satisfies Gate 1 (Lead Capture)."""

    def evaluate(self, payload: dict[str, Any]) -> GateResult:
        issues: list[GateIssue] = []
        derived_data: dict[str, Any] = {}

        # 1. Anti-bot honeypot check
        website = payload.get("website")
        if website:
            issues.append(
                GateIssue(
                    field="website",
                    code="BOT_DETECTED",
                    message="Anti-bot honeypot field must be empty.",
                    severity=Severity.ERROR,
                )
            )

        # 2. Identity Check
        customer_name = (payload.get("customer_name") or "").strip()
        if not customer_name or len(customer_name) < 2:
            issues.append(
                GateIssue(
                    field="customer_name",
                    code="NAME_REQUIRED",
                    message="Customer or Advisor name is required (at least 2 characters).",
                    severity=Severity.ERROR,
                )
            )

        # 3. Contact Channel Check
        email = (payload.get("email") or "").strip()
        phone = (payload.get("phone") or "").strip()
        has_valid_email = bool(email and EMAIL_REGEX.match(email))
        has_phone = bool(phone and len(phone) >= 6)

        if not has_valid_email and not has_phone:
            issues.append(
                GateIssue(
                    field="email",
                    code="CONTACT_REQUIRED",
                    message="At least a valid email or phone number is required to save request.",
                    severity=Severity.ERROR,
                )
            )

        # 4. Scoping Signal Check
        destinations = payload.get("destinations") or []
        special_reqs = (payload.get("special_requirements") or "").strip()
        message = (payload.get("message") or "").strip()
        raw_dates = (payload.get("raw_dates_text") or "").strip()

        has_scoping = bool(
            (isinstance(destinations, list) and len(destinations) > 0 and any(str(d).strip() for d in destinations))
            or special_reqs
            or message
            or raw_dates
        )

        if not has_scoping:
            issues.append(
                GateIssue(
                    field="destinations",
                    code="SCOPING_SIGNAL_REQUIRED",
                    message="Provide at least one target destination or a brief inquiry message.",
                    severity=Severity.WARNING,
                    suggestion="Add a target destination (e.g. 'Vietnam') or note from client.",
                )
            )

        # 5. Party composition warning
        adults = payload.get("adults")
        if adults is not None and adults < 1:
            issues.append(
                GateIssue(
                    field="adults",
                    code="INVALID_ADULTS",
                    message="Adult count must be at least 1.",
                    severity=Severity.ERROR,
                )
            )

        passed = len([i for i in issues if i.severity == Severity.ERROR]) == 0
        return GateResult(passed=passed, issues=issues, derived_data=derived_data)
