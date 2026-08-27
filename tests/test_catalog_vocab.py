import unittest

from core.rules.catalog_vocab import (
    CATEGORY,
    DEFAULT_CHARGE_UNIT_BY_CATEGORY,
    SUBCATEGORY_BY_CATEGORY,
    TIME_BASIS,
    UNIT,
)

EXPECTED_CATEGORY = {
    "accommodation",
    "transportation",
    "ticket",
    "flights",
    "guide",
    "guide_expense",
    "experience",
    "meal",
    "visa",
    "others",
}


class CategoryVocabTests(unittest.TestCase):
    def test_category_matches_spec_d0(self):
        self.assertEqual(CATEGORY, EXPECTED_CATEGORY)

    def test_category_has_exactly_ten_values(self):
        self.assertEqual(len(CATEGORY), 10)


class DefaultChargeUnitTests(unittest.TestCase):
    def test_covers_all_ten_categories(self):
        self.assertEqual(set(DEFAULT_CHARGE_UNIT_BY_CATEGORY.keys()), CATEGORY)

    def test_every_default_unit_and_time_basis_is_in_vocab(self):
        for category, (unit, time_basis) in DEFAULT_CHARGE_UNIT_BY_CATEGORY.items():
            with self.subTest(category=category):
                self.assertIn(unit, UNIT)
                self.assertIn(time_basis, TIME_BASIS)


class SubcategoryVocabTests(unittest.TestCase):
    def test_covers_all_ten_categories(self):
        self.assertEqual(set(SUBCATEGORY_BY_CATEGORY.keys()), CATEGORY)

    def test_every_category_has_an_other_safety_valve(self):
        for category, subcategories in SUBCATEGORY_BY_CATEGORY.items():
            with self.subTest(category=category):
                has_other = any(value.startswith("other_") for value in subcategories)
                self.assertTrue(has_other, f"category '{category}' is missing an other_* subcategory")


if __name__ == "__main__":
    unittest.main()
