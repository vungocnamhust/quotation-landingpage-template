import unittest

from pydantic import ValidationError

from quote_document import CreateQuoteRequestV1
from services.pricing_contract import normalize_legacy_pricing_facts


class PricingContractTests(unittest.TestCase):
    def test_new_option_requires_both_typed_amounts_and_rejects_legacy_keys(self):
        with self.assertRaises(ValidationError):
            CreateQuoteRequestV1.model_validate({
                "pricing_facts": {"options": [{"label": "Option 01", "currency": "USD", "per_traveler_amount_minor": 250_000}]},
            })
        with self.assertRaises(ValidationError):
            CreateQuoteRequestV1.model_validate({
                "pricing_facts": {"currency": "USD", "options": []},
            })
        with self.assertRaises(ValidationError):
            CreateQuoteRequestV1.model_validate({
                "pricing_facts": {"options": [{
                    "label": "Option 01", "currency": "USD",
                    "per_traveler_amount_minor": 250_000,
                    "group_total_amount_minor": 500_000,
                    "is_alternative_option": True,
                }]},
            })

    def test_new_options_are_limited_to_four(self):
        option = {
            "label": "Option", "currency": "USD",
            "per_traveler_amount_minor": 250_000,
            "group_total_amount_minor": 500_000,
        }
        with self.assertRaises(ValidationError):
            CreateQuoteRequestV1.model_validate({
                "pricing_facts": {"options": [option] * 5},
            })

    def test_legacy_request_normalizes_only_parseable_option_values(self):
        normalized = normalize_legacy_pricing_facts({
            "pricing_facts": {
                "currency": "USD",
                "display_title": "Legacy title",
                "options": [{"category": "Legacy", "name": "Classic", "per_person_text": "USD 2,500", "total_text": "USD 5,000"}],
            },
        })
        option = normalized["pricing_facts"]["options"][0]
        self.assertEqual(option["label"], "Classic")
        self.assertEqual(option["per_traveler_amount_minor"], 250_000)
        self.assertEqual(option["group_total_amount_minor"], 500_000)
