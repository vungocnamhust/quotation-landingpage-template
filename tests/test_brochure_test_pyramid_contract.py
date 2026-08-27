"""Fast PR gate for the brochure test-pyramid contracts.

These tests deliberately do not need a database, R2, an LLM, or a Next server.
The full runner proves the same contracts against a disposable tenant nightly.
"""
from pathlib import Path
import re
import unittest

from scripts.test_v2_brochure_workflow import (
    SSR_EDITABLE_FIELD_EXPECTATIONS,
    WORKFLOW_SCENARIOS,
    validate_test_pyramid_contracts,
)


ROOT = Path(__file__).resolve().parents[1]


class BrochureTestPyramidContractTests(unittest.TestCase):
    def test_locale_catalog_has_all_default_and_accessibility_keys(self):
        source = (ROOT / "quote-generator/display/labels.ts").read_text(encoding="utf-8")
        for locale in ("en", "vi", "ar"):
            locale_body = re.search(rf"\b{locale}: \{{(?P<body>.*?)\n  \}},", source, re.DOTALL)
            self.assertIsNotNone(locale_body, locale)
            for key in (
                "journeyOverviewTitle", "routeMapDescription", "itineraryTitle", "pricingTitle",
                "bookingTermsTitle", "footerText", "routeMapOverview",
                "loading", "errorTitle", "notFoundTitle", "previousImage", "nextImage",
            ):
                self.assertRegex(locale_body.group("body"), rf"\b{key}:\s*['\"]")

    def test_runtime_builder_contains_every_representative_canonical_marker_path(self):
        source = (ROOT / "quote-generator/display/runtimePageBuilder.ts").read_text(encoding="utf-8")
        renderer_source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "quote-generator/components/display").glob("*.tsx")
        )
        # Dynamic collection indexes are template literals in the builder; their
        # stable parent path is the contract we can prove statically.
        for item in SSR_EDITABLE_FIELD_EXPECTATIONS:
            if item.path.startswith("/presentation/copyOverrides/"):
                needle = item.path.rsplit("/", 1)[-1]
            else:
                # Rich blocks include a fixed first block and fixed checklist
                # groups. Only list-item indexes are dynamic in the builder.
                if item.path.startswith("/content/sections/booking_terms/blocks/"):
                    # Paragraph placement is block-type driven, so its index
                    # is intentionally dynamic rather than hard-coded to 0.
                    parent = "/content/sections/booking_terms/blocks/"
                else:
                    parent = re.sub(r"/items/0$", "/items", item.path) if "/content/sections/" in item.path else re.sub(r"/0(?=/|$)", "", item.path)
                needle = parent.rsplit("/", 1)[0]
            self.assertIn(needle, source + renderer_source, item.path)

    def test_full_scenarios_are_not_pr_default(self):
        validate_test_pyramid_contracts()
        full = [item for item in WORKFLOW_SCENARIOS if item.tier == "full"]
        self.assertEqual({item.id for item in full}, {"happy-path", "stale-content", "revision-conflict", "asset-failure", "release-immutability"})


if __name__ == "__main__":
    unittest.main()
