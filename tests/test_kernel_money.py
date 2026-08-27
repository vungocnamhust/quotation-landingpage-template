import unittest

from core.kernel import SUPPORTED_CURRENCIES, currency_divisor, validate_amount_minor, validate_currency
from core.rules import pricing_rules


class KernelMoneyReexportTests(unittest.TestCase):
    def test_supported_currencies_matches_pricing_rules_ssot(self):
        self.assertEqual(SUPPORTED_CURRENCIES, pricing_rules.SUPPORTED_CURRENCIES)

    def test_currency_divisor_matches_pricing_rules_ssot(self):
        for currency in SUPPORTED_CURRENCIES:
            self.assertEqual(currency_divisor(currency), pricing_rules.currency_divisor(currency))


class ValidateCurrencyTests(unittest.TestCase):
    def test_accepts_and_uppercases_supported_currency(self):
        self.assertEqual(validate_currency("usd"), "USD")

    def test_rejects_unsupported_currency(self):
        with self.assertRaises(ValueError):
            validate_currency("XYZ")


class ValidateAmountMinorTests(unittest.TestCase):
    def test_accepts_zero_and_positive_integers(self):
        self.assertEqual(validate_amount_minor(0), 0)
        self.assertEqual(validate_amount_minor(100), 100)

    def test_rejects_negative_amount(self):
        with self.assertRaises(ValueError):
            validate_amount_minor(-1)

    def test_rejects_non_integer_amount(self):
        with self.assertRaises(ValueError):
            validate_amount_minor(1.5)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
