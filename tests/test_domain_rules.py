"""Comprehensive unit tests for Clean Architecture Domain Rules."""

import pytest
from core.rules import (
    apply_child_preset_ratio,
    calculate_duration,
    calculate_tri_pricing,
    consolidate_stays_from_day_accommodations,
    currency_divisor,
    date_for_itinerary_day,
    format_travel_dates_label,
    generate_party_label,
    get_default_meals_for_lang,
    infer_default_currency,
    infer_greeting_name,
    infer_rates_from_group_total,
    parse_iso_date,
    resolve_client_display_name,
    sync_travel_style_facts,
    validate_hotel_boundaries,
    PublishReadinessGate,
)


class TestDatesRules:
    def test_calculate_duration_normal(self):
        days, nights = calculate_duration("2026-11-01", "2026-11-12")
        assert days == 12
        assert nights == 11

    def test_calculate_duration_same_day(self):
        days, nights = calculate_duration("2026-11-01", "2026-11-01")
        assert days == 1
        assert nights == 0

    def test_calculate_duration_invalid(self):
        assert calculate_duration("2026-11-12", "2026-11-01") == (None, None)
        assert calculate_duration(None, "2026-11-01") == (None, None)

    def test_date_for_itinerary_day(self):
        assert date_for_itinerary_day("2026-11-01", 1) == "2026-11-01"
        assert date_for_itinerary_day("2026-11-01", 5) == "2026-11-05"
        assert date_for_itinerary_day("2026-11-01", 0) is None

    def test_format_travel_dates_label(self):
        label = format_travel_dates_label("2026-11-01", "2026-11-12")
        assert label == "01 Nov 2026 – 12 Nov 2026"


class TestStaysRules:
    def test_consolidate_contiguous_stays(self):
        itinerary = [
            {"day_number": 1, "destination": "Hanoi", "accommodation_id": "hotel-a", "accommodation_name": "Hotel A", "room_type": "Suite"},
            {"day_number": 2, "destination": "Hanoi", "accommodation_id": "hotel-a", "accommodation_name": "Hotel A", "room_type": "Suite"},
            {"day_number": 3, "destination": "Halong", "accommodation_id": "cruise-b", "accommodation_name": "Cruise B", "room_type": "Cabin"},
            {"day_number": 4, "destination": "Hanoi", "accommodation_id": None},  # Departure day
        ]
        stays = consolidate_stays_from_day_accommodations(itinerary, "2026-11-01")
        assert len(stays) == 2
        assert stays[0]["name"] == "Hotel A"
        assert stays[0]["check_in"] == "2026-11-01"
        assert stays[0]["check_out"] == "2026-11-03"
        assert stays[1]["name"] == "Cruise B"
        assert stays[1]["check_in"] == "2026-11-03"
        assert stays[1]["check_out"] == "2026-11-04"

    def test_validate_hotel_boundaries(self):
        valid, _ = validate_hotel_boundaries("2026-11-01", "2026-11-05", "2026-11-01", "2026-11-10")
        assert valid is True

        invalid_before, msg = validate_hotel_boundaries("2026-10-30", "2026-11-05", "2026-11-01", "2026-11-10")
        assert invalid_before is False
        assert "before tour start date" in (msg or "")


class TestPricingRules:
    def test_calculate_tri_pricing(self):
        # 2 Adults ($4,000 = 400000 minor) + 1 Child ($2,500 = 250000 minor) = $10,500 = 1050000 minor
        total = calculate_tri_pricing(400000, 250000, adults=2, children=1)
        assert total == 1050000

    def test_child_preset_ratios(self):
        per_adult = 400000
        assert apply_child_preset_ratio(per_adult, 0.5) == 200000
        assert apply_child_preset_ratio(per_adult, 0.75) == 300000
        assert apply_child_preset_ratio(per_adult, 1.0) == 400000
        assert apply_child_preset_ratio(per_adult, 0.0) == 0

    def test_infer_rates_from_group_total(self):
        # Total $11,000 (1100000 minor) with 2 Adults + 1 Child at 75% ratio (2 + 0.75 = 2.75 units)
        # 1100000 / 2.75 = 400000 ($4,000/adult), Child = 300000 ($3,000/child)
        per_adult, per_child = infer_rates_from_group_total(1100000, adults=2, children=1, child_ratio=0.75)
        assert per_adult == 400000
        assert per_child == 300000

    def test_currency_divisors(self):
        assert currency_divisor("USD") == 100
        assert currency_divisor("EUR") == 100
        assert currency_divisor("VND") == 1


class TestPartyRules:
    def test_resolve_client_display_name(self):
        # B2C
        assert resolve_client_display_name("traveller", "Alexander Vance") == "Alexander Vance"
        # B2B with client_name
        assert resolve_client_display_name("advisor", "John Smith", client_name="Mr. Vance") == "Mr. Vance"
        # B2B without client_name
        assert resolve_client_display_name("advisor", "John Smith", client_name="") == "John Smith"

    def test_generate_party_label(self):
        assert generate_party_label(2, 1, lang="en") == "2 Adults, 1 Child"
        assert generate_party_label(2, 0, customer_name="David Jenkins", lang="en") == "David Jenkins & Party (2 Adults)"
        assert generate_party_label(2, 2, lang="vi") == "2 Người lớn, 2 Trẻ em"

    def test_infer_greeting_name(self):
        assert infer_greeting_name("David Jenkins", lang="en") == "Dear David Jenkins"
        assert infer_greeting_name("Dear David Jenkins", lang="en") == "Dear David Jenkins"
        assert infer_greeting_name("Anh Nam", lang="vi") == "Kính gửi Anh Nam"


class TestTaxonomyRules:
    def test_get_default_meals_for_lang(self):
        assert get_default_meals_for_lang("en") == ["Breakfast"]
        assert get_default_meals_for_lang("vi") == ["Bữa sáng"]
        assert get_default_meals_for_lang("ar") == ["الإفطار"]

    def test_infer_default_currency(self):
        assert infer_default_currency("selvara", "UK & Ireland") == "GBP"
        assert infer_default_currency("selvara", "Germany") == "EUR"
        assert infer_default_currency("selvara", "Vietnam") == "VND"
        assert infer_default_currency("selvara", "United States") == "USD"

    def test_sync_travel_style_facts(self):
        data = {"travel_style": "Living Heritage"}
        synced = sync_travel_style_facts(data)
        assert synced["guest_profile"] == "Living Heritage"


class TestPublishReadinessGate:
    def test_ready_document_passes_publish_gate(self):
        gate = PublishReadinessGate()
        doc = {
            "trip": {
                "title": "Grand Cultural Expedition",
                "lede": "An unforgettable journey across Vietnam.",
                "start_date": "2026-11-01",
                "end_date": "2026-11-12",
                "itinerary": [{"day_number": 1, "destination": "Hanoi"}],
            },
            "pricing": {
                "options": [{"id": "opt-1", "group_total_amount_minor": 1000000}],
            },
        }
        result = gate.evaluate(doc)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_unready_document_fails_publish_gate(self):
        gate = PublishReadinessGate()
        doc = {
            "trip": {
                "title": "",  # Empty title
                "start_date": None,
            },
            "pricing": {"options": []},
        }
        result = gate.evaluate(doc)
        assert result.passed is False
        assert any(e.code == "HERO_TITLE_EMPTY" for e in result.errors)
        assert any(e.code == "MISSING_TOUR_DATES" for e in result.errors)
