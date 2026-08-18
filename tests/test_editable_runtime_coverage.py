"""Fail-closed coverage for the registry, runtime builder, and renderer consumers."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from editable_brochure_contract import EDITABLE_BROCHURE_FIELDS


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "editable-brochure-coverage-manifest.json").read_text(encoding="utf-8"))
RUNTIME = (ROOT / "quote-generator/display/runtimePageBuilder.ts").read_text(encoding="utf-8")


def _source_matches(template: str, source: str) -> bool:
    template_parts = template.strip("/").split("/")
    source_parts = source.strip("/").split("/")
    return len(template_parts) == len(source_parts) and all(
        expected == "*" or expected == actual
        for expected, actual in zip(template_parts, source_parts)
    )


class EditableRuntimeCoverageTests(unittest.TestCase):
    def test_manifest_is_a_complete_exact_copy_of_registry_ownership(self):
        registry = {item["fieldId"]: item for item in EDITABLE_BROCHURE_FIELDS}
        entries = {item["fieldId"]: item for item in MANIFEST["fields"]}
        self.assertEqual(set(entries), set(registry))
        self.assertEqual(len(entries), len(MANIFEST["fields"]))
        for field_id, descriptor in registry.items():
            entry = entries[field_id]
            self.assertEqual(entry["source"], descriptor["source"], field_id)
            self.assertEqual(entry["owner"], descriptor["owner"], field_id)
            self.assertEqual(entry["kind"], descriptor["kind"], field_id)
            self.assertEqual(entry["behavior"], descriptor["editMode"], field_id)
            self.assertIn(entry["renderer"], {
                "quote-generator/display/runtimePageBuilder.ts",
                "quote-generator/components/display/BrochureNavBar.tsx",
                "quote-generator/components/DisplayStateScreen.tsx",
                "quote-generator/components/display/PdfBrochureDocument.tsx",
            }, field_id)
            expected_attribute = "alt" if descriptor["kind"] == "altText" else "aria-label" if descriptor["kind"] == "aria" else "data-editable"
            self.assertEqual(entry["domAttribute"], expected_attribute, field_id)

    def test_runtime_static_paths_are_declared_by_the_registry(self):
        # These calls contain a direct JSON pointer. Dynamic repeaters are
        # covered separately below because their final index is runtime data.
        paths = re.findall(
            r"(?:editable|factCopy|contentCopy|derivedCopy|assetAlt)\([^\n]*?[,\s](['\"])(/[^'\"`$]+)\1",
            RUNTIME,
        )
        declared = [item["source"] for item in EDITABLE_BROCHURE_FIELDS]
        unexpected = sorted({path for _, path in paths if not any(_source_matches(template, path) for template in declared)})
        self.assertEqual(unexpected, [])

    def test_dynamic_repeater_paths_and_owners_are_registry_declared(self):
        # The builder owns the three `base` templates; an index may vary, but
        # its field family and owner must remain declared by the registry.
        cases = (
            ("/route/staySegments/0/displayName", "fact-derived"),
            ("/route/staySegments/0/mapSegmentDesc", "content"),
            ("/itinerary/days/0/title", "content"),
            ("/itinerary/days/0/notes/0", "fact"),
            ("/itinerary/days/0/images/carousel/0/altText", "fact"),
            ("/stays/hotels/0/name", "fact"),
            ("/stays/hotels/0/hotelImage/altText", "fact"),
            ("/pricing/options/0/label", "fact"),
            ("/content/sections/booking_terms/blocks/1/items/1/body", "fact"),
            ("/content/sections/inclusions_exclusions/blocks/0/leftItems/0", "fact"),
        )
        for source, owner in cases:
            descriptor = next((item for item in EDITABLE_BROCHURE_FIELDS if _source_matches(item["source"], source)), None)
            self.assertIsNotNone(descriptor, source)
            self.assertEqual(descriptor["owner"], owner, source)

    def test_alt_and_aria_descriptors_have_attribute_consumers_in_both_compositors_when_applicable(self):
        screen = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "quote-generator/components").rglob("*.tsx"))
        pdf = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        alt_fields = [item for item in EDITABLE_BROCHURE_FIELDS if item["kind"] == "altText"]
        aria_fields = [item for item in EDITABLE_BROCHURE_FIELDS if item["kind"] == "aria"]
        self.assertTrue(alt_fields)
        self.assertTrue(aria_fields)
        self.assertIn("alt={textValue(alt)} {...editableProps(alt)}", screen)
        self.assertIn("aria-label={textValue(viewModel.sectionAriaLabel)}", screen)
        self.assertIn("viewModel={route}", pdf)
        self.assertIn("<ImageFrame src={hotel.hotelImage} alt={hotel.hotelImageAlt}", pdf)
        self.assertIn("<ImageFrame src={images[0]?.src ?? ''} alt={images[0]?.alt ?? day.title}", pdf)

    def test_content_signature_and_design_a11y_overrides_have_real_screen_and_pdf_consumers(self):
        screen = (ROOT / "quote-generator/components/display/sections.tsx").read_text(encoding="utf-8")
        nav = (ROOT / "quote-generator/components/display/BrochureNavBar.tsx").read_text(encoding="utf-8")
        pdf = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        self.assertIn("signatureName", screen)
        self.assertIn("signatureRole", screen)
        self.assertIn("{letter.signatureName}", pdf)
        self.assertIn("{letter.signatureRole}", pdf)
        self.assertIn("aria-label={textValue(viewModel.sectionAriaLabel)}", nav)
        self.assertIn("alt={textValue(viewModel.brandLogoAlt ?? viewModel.brandName)}", nav)
        self.assertIn("viewModel={route}", pdf)

    def test_empty_designer_cta_has_a_canvas_only_editable_affordance(self):
        page = (ROOT / "quote-generator/components/DisplayPage.tsx").read_text(encoding="utf-8")
        canvas = (ROOT / "quote-generator/components/quotation-workspace/BoundaryCanvas.tsx").read_text(encoding="utf-8")
        sections = (ROOT / "quote-generator/components/display/sections.tsx").read_text(encoding="utf-8")
        self.assertIn("workspaceCanvas={workspaceCanvas}", page)
        self.assertIn("<DisplayPage documentModel={model} workspaceCanvas />", canvas)
        self.assertIn('data-editable="/designer/ctaBody"', sections)
        self.assertIn('data-workspace-editor-value=""', sections)

    def test_browser_evidence_runner_exercises_owner_handoffs_without_direct_canvas_writes(self):
        browser = (ROOT / "e2e/browser_pdf_compose_v2.py").read_text(encoding="utf-8")
        self.assertIn("def assert_canvas_handoff", browser)
        self.assertIn("def save_designer_fact_from_canvas", browser)
        self.assertIn("def assert_system_canvas_target_is_read_only", browser)
        for source in (
            "/narrative/letterSignOff",
            "/narrative/letterSender",
            "/content/sections/inclusions_exclusions/blocks/0/leftItems/0",
            "/itinerary/days/0/title",
            "/itinerary/days/0/labelHighlights",
            "/stays/hotels/0/name",
            "/pricing/options/0/label",
            "/designer/name",
            "/route/staySegments/0/displayName",
            "/labels/classic",
        ):
            self.assertIn(source, browser)
        self.assertIn("focus=day:{day_id}", browser)
        self.assertIn("focus=hotel:{hotel_id}", browser)
        self.assertIn("focus=pricingOption:{pricing_id}", browser)
        for source in (
            "/designer/kicker",
            "/designer/title",
            "/designer/subtitle",
            "/designer/quote",
            "/designer/signature",
            "/designer/experience",
            "/designer/ctaBody",
        ):
            self.assertIn(source, browser)


if __name__ == "__main__":
    unittest.main()
