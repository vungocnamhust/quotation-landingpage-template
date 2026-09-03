from core.rules.ingest_parser import (
    parse_amount_text,
    parse_cancellation_policy_text,
    parse_tier_pax_text,
    parse_validity_text,
)


class TestParseAmountText:
    def test_vnd_dot_thousands_separator(self):
        result = parse_amount_text("1.250.000", "VND")
        assert result.ambiguous is False
        assert result.currency == "VND"
        assert result.minor_units == 1_250_000

    def test_usd_comma_thousands_dot_decimal(self):
        result = parse_amount_text("1,250.00", "USD")
        assert result.ambiguous is False
        assert result.currency == "USD"
        assert result.minor_units == 125_000

    def test_currency_symbol_in_amount_text(self):
        result = parse_amount_text("1.250.000đ")
        assert result.ambiguous is False
        assert result.currency == "VND"
        assert result.minor_units == 1_250_000

    def test_eur_decimal_comma(self):
        result = parse_amount_text("1.250,50", "EUR")
        assert result.ambiguous is False
        assert result.currency == "EUR"
        assert result.minor_units == 125_050

    def test_plus_plus_suffix_is_ambiguous(self):
        result = parse_amount_text("85++", "USD")
        assert result.ambiguous is True
        assert result.minor_units is None

    def test_trieu_abbreviation_is_ambiguous(self):
        result = parse_amount_text("1.2tr", "VND")
        assert result.ambiguous is True

    def test_tu_starting_price_is_ambiguous(self):
        result = parse_amount_text("từ 500.000", "VND")
        assert result.ambiguous is True

    def test_lien_he_contact_us_is_ambiguous(self):
        result = parse_amount_text("liên hệ")
        assert result.ambiguous is True
        assert result.minor_units is None

    def test_empty_text_is_ambiguous(self):
        result = parse_amount_text("")
        assert result.ambiguous is True

    def test_missing_currency_is_ambiguous(self):
        result = parse_amount_text("1250000")
        assert result.ambiguous is True
        assert "currency" in (result.reason or "")

    def test_zero_amount_is_ambiguous(self):
        result = parse_amount_text("0", "VND")
        assert result.ambiguous is True

    # --- C1: currency alias "d" must never match inside "usd"/"dollars" ---------------

    def test_usd_with_trailing_word_is_not_misdetected_as_vnd(self):
        result = parse_amount_text("500 USD net")
        assert result.ambiguous is False
        assert result.currency == "USD"
        assert result.minor_units == 50_000

    def test_usd_with_slash_suffix_is_not_misdetected_as_vnd(self):
        result = parse_amount_text("150 usd/pax")
        assert result.ambiguous is False
        assert result.currency == "USD"

    def test_word_containing_d_is_not_misdetected_as_vnd(self):
        result = parse_amount_text("120 dollars")
        assert result.ambiguous is True
        assert "currency" in (result.reason or "")

    def test_vnd_no_space_before_symbol_still_detected(self):
        result = parse_amount_text("500.000đ")
        assert result.ambiguous is False
        assert result.currency == "VND"
        assert result.minor_units == 500_000

    def test_eur_alias_still_detected(self):
        result = parse_amount_text("35 eur")
        assert result.ambiguous is False
        assert result.currency == "EUR"

    # --- C2: must not silently grab the FIRST number when several are present --------

    def test_leading_pax_count_does_not_win_over_the_price(self):
        result = parse_amount_text("2 pax: 500.000 VND")
        assert result.ambiguous is False
        assert result.currency == "VND"
        assert result.minor_units == 500_000

    def test_leading_multiplier_does_not_win_over_the_price(self):
        result = parse_amount_text("1 x 500.000 đ")
        assert result.ambiguous is False
        assert result.minor_units == 500_000

    def test_ambiguous_price_range_is_flagged_not_guessed(self):
        result = parse_amount_text("50.000 - 80.000 VND")
        assert result.ambiguous is True
        assert result.minor_units is None

    def test_single_numeric_group_unaffected(self):
        result = parse_amount_text("1.250.000 (2 pax)", "VND")
        assert result.ambiguous is False
        assert result.minor_units == 1_250_000

    def test_free_text_resolves_to_zero_with_a_real_currency(self):
        result = parse_amount_text("miễn phí", "VND")
        assert result.ambiguous is False
        assert result.minor_units == 0
        assert result.currency == "VND"
        assert result.is_percent is False

    def test_free_of_charge_english_variant(self):
        result = parse_amount_text("Free of charge")
        assert result.ambiguous is False
        assert result.minor_units == 0
        assert result.currency == "VND"  # no currency signal anywhere -> domain default

    def test_percent_amount_is_typed_as_percent_not_money(self):
        """A discount/uplift percentage (e.g. a 'giảm 5%' group discount) is not a money
        amount: it must never carry a fabricated '%' currency or a minor_units value derived
        from the percentage, or a caller that only understands money (a rate price line) could
        silently persist it as a real price (regression guard for the bug this replaced)."""
        result = parse_amount_text("giảm 5%")
        assert result.ambiguous is False
        assert result.is_percent is True
        assert result.percent_value == 5.0
        assert result.minor_units is None
        assert result.currency is None

    def test_negative_percent_amount_is_typed_as_percent(self):
        result = parse_amount_text("-10%")
        assert result.is_percent is True
        assert result.percent_value == -10.0
        assert result.minor_units is None
        assert result.currency is None

    def test_percent_amount_never_produces_a_percent_currency_code(self):
        result = parse_amount_text("phụ thu 10% dịp lễ", "VND")
        assert result.currency != "%"
        assert result.currency is None


class TestParseValidityText:
    def test_full_date_range_with_years(self):
        result = parse_validity_text("15/12/2026 - 20/12/2026")
        assert result.kind == "date_range"
        assert result.ambiguous is False
        assert result.date_from == "2026-12-15"
        assert result.date_to == "2026-12-20"

    def test_season_window_without_years_crossing_year_boundary(self):
        result = parse_validity_text("01/10-30/04")
        assert result.kind == "season_window"
        assert result.ambiguous is False
        assert result.season_from_md == "10-01"
        assert result.season_to_md == "04-30"

    def test_single_date_missing_year_is_ambiguous(self):
        result = parse_validity_text("15/12")
        assert result.kind == "single_date"
        assert result.ambiguous is True
        assert "year" in (result.reason or "")

    def test_single_date_with_year(self):
        result = parse_validity_text("15/12/2026")
        assert result.ambiguous is False
        assert result.date_from == "2026-12-15"

    def test_iso_date(self):
        result = parse_validity_text("2026-12-15")
        assert result.ambiguous is False
        assert result.date_from == "2026-12-15"

    def test_text_month_date(self):
        result = parse_validity_text("15 Dec 2026")
        assert result.ambiguous is False
        assert result.date_from == "2026-12-15"

    def test_empty_text_is_ambiguous(self):
        result = parse_validity_text("")
        assert result.ambiguous is True

    def test_mismatched_year_presence_is_ambiguous(self):
        result = parse_validity_text("15/12/2026 - 30/04")
        assert result.ambiguous is True

    # --- H5: a calendar-impossible date must never claim to be valid -----------------

    def test_february_31_range_is_ambiguous_not_a_crash(self):
        result = parse_validity_text("31/02/2025 - 15/03/2025")
        assert result.ambiguous is True
        assert result.date_from is None

    def test_february_30_single_date_is_ambiguous(self):
        result = parse_validity_text("30/02/2025")
        assert result.ambiguous is True

    def test_april_31_single_date_is_ambiguous(self):
        result = parse_validity_text("31/04/2025")
        assert result.ambiguous is True

    def test_february_29_leap_year_is_valid(self):
        result = parse_validity_text("29/02/2024")
        assert result.ambiguous is False
        assert result.date_from == "2024-02-29"

    def test_february_29_non_leap_year_is_ambiguous(self):
        result = parse_validity_text("29/02/2025")
        assert result.ambiguous is True

    def test_season_window_february_29_without_year_is_permitted(self):
        result = parse_validity_text("29/02-15/03")
        assert result.kind == "season_window"
        assert result.ambiguous is False


class TestParseCancellationPolicyText:
    def test_multi_tier_policy_shape_a(self):
        text = "Hủy trước 30 ngày: miễn phí; 15-29 ngày: phạt 50%; dưới 15 ngày: phạt 100%; no-show: 100%"
        result = parse_cancellation_policy_text(text)
        assert result.ambiguous is False
        assert result.no_show_penalty_percent == 100
        by_days = {t.days_before_service_min: t.penalty_percent for t in result.tiers}
        assert by_days[30] == 0
        assert by_days[15] == 50

    def test_english_policy(self):
        text = "Free cancellation up to 30 days before; 50% penalty 15-29 days; 100% penalty within 15 days"
        result = parse_cancellation_policy_text(text)
        assert result.ambiguous is False
        by_days = {t.days_before_service_min: t.penalty_percent for t in result.tiers}
        assert by_days[30] == 0
        assert by_days[0] == 100

    def test_no_parseable_tiers_is_ambiguous_zero_fabrication(self):
        result = parse_cancellation_policy_text("Standard supplier terms apply.")
        assert result.ambiguous is True
        assert result.tiers == []

    def test_empty_text_is_ambiguous(self):
        result = parse_cancellation_policy_text("")
        assert result.ambiguous is True

    def test_decreasing_penalty_as_days_decrease_is_ambiguous(self):
        text = "30 ngày: phạt 80%; 15 ngày: phạt 20%"
        result = parse_cancellation_policy_text(text)
        assert result.ambiguous is True


class TestParseTierPaxText:
    def test_range(self):
        result = parse_tier_pax_text("nhóm 10-15 khách")
        assert result.ambiguous is False
        assert result.tier_min == 10
        assert result.tier_max == 15

    def test_single_value(self):
        result = parse_tier_pax_text("15 khách")
        assert result.ambiguous is False
        assert result.tier_min == 15
        assert result.tier_max == 15

    def test_empty_is_ambiguous(self):
        result = parse_tier_pax_text("")
        assert result.ambiguous is True

    def test_seat_count_wording_is_recognized(self):
        result = parse_tier_pax_text("16 chỗ")
        assert result.ambiguous is False
        assert result.tier_min == 16
        assert result.tier_max == 16

    def test_seats_english_wording_is_recognized(self):
        result = parse_tier_pax_text("29 seats")
        assert result.ambiguous is False
        assert result.tier_min == 29
        assert result.tier_max == 29

    def test_child_age_band_is_not_mistaken_for_a_pax_headcount_tier(self):
        """'5-10 tuổi' is a child age range, not a booking size of 5-15 guests — before this
        guard, the plain '(\\d+)-(\\d+)' tier regex matched it anyway and would have written a
        nonsensical 5-10 person tier onto a product that has nothing to do with group size."""
        result = parse_tier_pax_text("5-10 tuổi")
        assert result.ambiguous is False
        assert result.tier_min is None
        assert result.tier_max is None

    def test_months_age_band_is_not_mistaken_for_a_pax_headcount_tier(self):
        result = parse_tier_pax_text("6-24 months")
        assert result.ambiguous is False
        assert result.tier_min is None
        assert result.tier_max is None
