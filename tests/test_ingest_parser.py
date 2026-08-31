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
