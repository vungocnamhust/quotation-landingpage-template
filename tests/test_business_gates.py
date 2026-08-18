"""Unit tests for Business Rule Gates (Clean Architecture)."""

import pytest
from core.rules import (
    FieldOwnershipGate,
    GateIssue,
    QuotationTransitionGate,
    RequestIntakeGate,
    Severity,
)


class TestRequestIntakeGate:
    def test_valid_request_passes_gate_1(self):
        gate = RequestIntakeGate()
        payload = {
            "customer_name": "Alexander Vance",
            "email": "alex@example.com",
            "destinations": ["Vietnam", "Cambodia"],
            "adults": 2,
        }
        result = gate.evaluate(payload)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_missing_name_fails_gate_1(self):
        gate = RequestIntakeGate()
        payload = {
            "customer_name": "",
            "email": "alex@example.com",
            "destinations": ["Vietnam"],
        }
        result = gate.evaluate(payload)
        assert result.passed is False
        assert any(e.code == "NAME_REQUIRED" for e in result.errors)

    def test_missing_contact_fails_gate_1(self):
        gate = RequestIntakeGate()
        payload = {
            "customer_name": "Alexander Vance",
            "email": "",
            "phone": "",
            "destinations": ["Vietnam"],
        }
        result = gate.evaluate(payload)
        assert result.passed is False
        assert any(e.code == "CONTACT_REQUIRED" for e in result.errors)

    def test_bot_honeypot_detection(self):
        gate = RequestIntakeGate()
        payload = {
            "customer_name": "Spam Bot",
            "email": "bot@spam.com",
            "website": "http://spam.com",
        }
        result = gate.evaluate(payload)
        assert result.passed is False
        assert any(e.code == "BOT_DETECTED" for e in result.errors)


class TestQuotationTransitionGate:
    def test_valid_quotation_passes_gate_2(self):
        gate = QuotationTransitionGate()
        context = {
            "customer_name": "Mr. David Jenkins",
            "adults": 2,
            "children": 1,
            "kid_ages": [7],
            "start_date": "2026-11-01",
            "end_date": "2026-11-03",
            "itinerary_with_stays": [
                {"day_number": 1, "destination": "Hanoi"},
                {"day_number": 2, "destination": "Hanoi"},
                {"day_number": 3, "destination": "Halong Bay"},
            ],
            "pricing": {
                "per_adult_amount_minor": 400000,
                "group_total_amount_minor": 1000000,
            },
            "brand_id": "selvara",
        }
        result = gate.evaluate(context)
        assert result.passed is True
        assert len(result.errors) == 0
        assert result.derived_data["duration_days"] == 3
        assert result.derived_data["duration_nights"] == 2

    def test_invalid_dates_fails_gate_2(self):
        gate = QuotationTransitionGate()
        context = {
            "customer_name": "David",
            "adults": 2,
            "start_date": "2026-11-05",
            "end_date": "2026-11-01",  # End before start
            "itinerary_with_stays": [{"day_number": 1, "destination": "Hanoi"}],
            "pricing": {"per_adult_amount_minor": 400000},
            "brand_id": "selvara",
        }
        result = gate.evaluate(context)
        assert result.passed is False
        assert any(e.code == "END_DATE_BEFORE_START" for e in result.errors)

    def test_missing_daily_destination_fails_gate_2(self):
        gate = QuotationTransitionGate()
        context = {
            "customer_name": "David",
            "adults": 2,
            "start_date": "2026-11-01",
            "end_date": "2026-11-02",
            "itinerary_with_stays": [
                {"day_number": 1, "destination": "Hanoi"},
                {"day_number": 2, "destination": ""},  # Missing dest
            ],
            "pricing": {"per_adult_amount_minor": 400000},
            "brand_id": "selvara",
        }
        result = gate.evaluate(context)
        assert result.passed is False
        assert any(e.code == "MISSING_DESTINATIONS" for e in result.errors)

    def test_zero_pricing_fails_gate_2(self):
        gate = QuotationTransitionGate()
        context = {
            "customer_name": "David",
            "adults": 2,
            "start_date": "2026-11-01",
            "end_date": "2026-11-02",
            "itinerary_with_stays": [
                {"day_number": 1, "destination": "Hanoi"},
                {"day_number": 2, "destination": "Hanoi"},
            ],
            "pricing": {"per_adult_amount_minor": 0, "group_total_amount_minor": 0},
            "brand_id": "selvara",
        }
        result = gate.evaluate(context)
        assert result.passed is False
        assert any(e.code == "PRICING_REQUIRED" for e in result.errors)


class TestFieldOwnershipGate:
    def test_ai_mutation_allowed_on_content_only(self):
        gate = FieldOwnershipGate()
        mutations = ["hero_lede", "overview_letter", "day_storytelling"]
        result = gate.evaluate_ai_mutation(mutations)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_ai_mutation_blocked_on_facts(self):
        gate = FieldOwnershipGate()
        mutations = ["customer_name", "pricing", "day_storytelling"]
        result = gate.evaluate_ai_mutation(mutations)
        assert result.passed is False
        assert any(e.code == "FACTS_MUTATION_FORBIDDEN" and e.field == "customer_name" for e in result.errors)
        assert any(e.code == "FACTS_MUTATION_FORBIDDEN" and e.field == "pricing" for e in result.errors)

    def test_ai_mutation_blocked_on_design(self):
        gate = FieldOwnershipGate()
        mutations = ["brand_id", "color_palette"]
        result = gate.evaluate_ai_mutation(mutations)
        assert result.passed is False
        assert any(e.code == "DESIGN_MUTATION_FORBIDDEN" for e in result.errors)
