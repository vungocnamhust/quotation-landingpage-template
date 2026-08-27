"""Fail-closed unit test suite ensuring all landingpage text preview fields on tab Design are covered by Inspector."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from editable_brochure_contract import (
    EDITABLE_BROCHURE_FIELDS,
    editable_contract_payload,
    is_design_copy_field,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "editable-brochure-coverage-manifest.json"
CONTEXTUAL_INSPECTOR_PATH = ROOT / "quote-generator/components/quotation-workspace/ContextualInspector.tsx"


def _is_wildcard_segment(segment: str) -> bool:
    return segment == "*" or (segment.startswith("{") and segment.endswith("}") and len(segment) > 2)


def _source_matches(template: str, source: str) -> bool:
    template_parts = template.strip("/").split("/")
    source_parts = source.strip("/").split("/")
    return len(template_parts) == len(source_parts) and all(
        _is_wildcard_segment(expected) or expected == actual
        for expected, actual in zip(template_parts, source_parts)
    )


class DesignInspectorTextCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = editable_contract_payload()
        self.fields = self.payload["fields"]

    def test_every_landingpage_text_field_has_valid_contract_descriptor(self):
        text_fields = [
            field for field in self.fields
            if field.get("kind") in {"text", "richText", "aria", "altText"}
        ]
        self.assertGreater(len(text_fields), 0, "Contract must define text preview fields.")

        for field in text_fields:
            field_id = field["fieldId"]
            source = field["source"]
            owner = field["owner"]
            kind = field["kind"]
            edit_mode = field["editMode"]

            self.assertTrue(field_id, "Text descriptor must have a non-empty fieldId.")
            self.assertTrue(source.startswith("/"), f"Field {field_id} source must start with slash: {source}")
            self.assertIn(owner, {"design", "content", "fact", "fact-derived", "system"}, f"Field {field_id} invalid owner.")
            self.assertIn(kind, {"text", "richText", "aria", "altText"}, f"Field {field_id} invalid kind.")
            self.assertIn(edit_mode, {"inspector", "handoff", "readonly"}, f"Field {field_id} invalid editMode.")

            if owner == "design" or field.get("editorSurface") == "design-inspector":
                self.assertEqual(edit_mode, "inspector", f"Field {field_id} must have editMode 'inspector'.")
                self.assertIn(
                    field.get("inspectorControl"),
                    {"text", "textarea"},
                    f"Direct inspector text field {field_id} must declare 'text' or 'textarea' control.",
                )
            else:
                self.assertEqual(
                    field.get("inspectorControl"),
                    "none",
                    f"Non-direct text field {field_id} inspectorControl should be 'none'.",
                )

    def test_all_runtime_builder_emitted_text_paths_are_mapped_to_contract_descriptors(self):
        contract_sources = [item["source"] for item in self.fields]

        # Emitted text path samples across all brochure landing page components
        sample_emitted_paths = [
            "/presentation/copyOverrides/hero.primaryCta",
            "/narrative/heroMeta1",
            "/narrative/heroMeta2",
            "/presentation/copyOverrides/inclusions.inclusionsTitle",
            "/presentation/copyOverrides/inclusions.exclusionsTitle",
            "/route/staySegments/0/mapSegmentDesc",
            "/presentation/copyOverrides/nav.brochureTheme",
            "/presentation/copyOverrides/a11y.routeMapOverview",
            "/presentation/copyOverrides/pdf.whitespaceSlogan",
            "/presentation/copyOverrides/stays.pdfTitle",
            "/presentation/identityOverrides/logoAlt",
            "/presentation/copyOverrides/a11y.brochureSections",
            "/content/sections/booking_terms/title",
            "/content/sections/booking_terms/blocks/0/text",
            "/customer/greetingName",
            "/customer/partyLabel",
            "/designer/kicker",
            "/designer/title",
            "/designer/subtitle",
            "/designer/signature",
            "/designer/quote",
            "/designer/experience",
            "/designer/ctaBody",
            "/narrative/letterSignOff",
            "/narrative/letterSender",
            "/itinerary/days/0/title",
            "/itinerary/days/0/description/0",
            "/itinerary/days/0/notes/0",
            "/itinerary/days/0/dayNumber",
            "/stays/hotels/0/name",
            "/stays/hotels/0/introduction",
            "/pricing/options/0/label",
            "/pricing/conditions",
            "/content/sections/booking_terms/blocks/0/items/0/body",
            "/brand/displayName",
            "/designer/name",
            "/route/staySegments/0/displayName",
            "/labels/classic",
            "/labels/sendEmail",
        ]

        unmapped = []
        for path in sample_emitted_paths:
            if not any(_source_matches(template, path) for template in contract_sources):
                unmapped.append(path)

        self.assertEqual(unmapped, [], f"Landingpage text paths must all map to contract descriptors: {unmapped}")

    def test_inspector_direct_text_fields_use_valid_input_controls(self):
        direct_inspector_fields = [
            field for field in self.fields
            if field["owner"] == "design" or field.get("editorSurface") == "design-inspector"
        ]
        self.assertGreater(len(direct_inspector_fields), 0, "Must have direct inspector text fields.")

        textarea_fields = {"bookingTerms.body", "designer.quote", "designer.ctaBody"}

        for field in direct_inspector_fields:
            field_id = field["fieldId"]
            kind = field["kind"]
            control = field.get("inspectorControl")

            self.assertIn(control, {"text", "textarea"}, f"Direct inspector field {field_id} missing valid input control.")

            if field_id in textarea_fields or kind == "richText":
                self.assertEqual(
                    control, "textarea",
                    f"Multi-line/richText field {field_id} should use 'textarea' control.",
                )
            else:
                self.assertEqual(
                    control, "text",
                    f"Single-line text field {field_id} should use 'text' control.",
                )

    def test_inspector_handoff_text_fields_resolve_canonical_target_and_focus(self):
        handoff_fields = [
            field for field in self.fields
            if field.get("editMode") == "handoff" and field.get("kind") in {"text", "richText", "aria", "altText"}
        ]
        self.assertGreater(len(handoff_fields), 0, "Must have handoff text fields.")

        for field in handoff_fields:
            field_id = field["fieldId"]
            handoff = field.get("handoff")
            self.assertIsInstance(handoff, dict, f"Handoff text field {field_id} must have handoff config.")
            self.assertIn(handoff.get("stage"), {"facts", "content"}, f"Field {field_id} invalid handoff stage.")
            self.assertTrue(handoff.get("section"), f"Field {field_id} invalid handoff section.")

            if "*" in field["source"] and handoff.get("item"):
                self.assertIsNotNone(
                    handoff.get("indexFromSource"),
                    f"Repeater handoff text field {field_id} with item must specify indexFromSource.",
                )

    def test_inspector_system_copy_fields_are_marked_readonly(self):
        system_fields = [
            field for field in self.fields
            if field.get("owner") == "system"
        ]
        self.assertGreater(len(system_fields), 0, "Must have system copy fields.")

        for field in system_fields:
            field_id = field["fieldId"]
            self.assertEqual(field["editMode"], "readonly", f"System field {field_id} must be readonly.")
            self.assertEqual(field.get("inspectorControl"), "none", f"System field {field_id} inspectorControl must be none.")
            self.assertNotIn("handoff", field, f"System field {field_id} cannot have handoff.")

    def test_contextual_inspector_component_handles_all_field_owners(self):
        source = CONTEXTUAL_INSPECTOR_PATH.read_text(encoding="utf-8")

        # Verify Inspector handles direct inspector fact fields
        self.assertIn("directFactInspector = owner === 'fact' && selected?.editorSurface === 'design-inspector'", source)

        # Verify Inspector uses DesignControl for direct inspector fields
        self.assertIn("<DesignControl", source)
        self.assertIn("control={control === 'textarea' || selected.fieldId === 'bookingTerms.body' ? 'textarea' : 'text'}", source)

        # Verify auto-generation helpers for greeting name & party label
        self.assertIn("isGreetingField = selected?.fieldId === 'customer.greetingName'", source)
        self.assertIn("isPartyField = selected?.fieldId === 'customer.partyLabel'", source)
        self.assertIn("inferGreetingName(customerName)", source)
        self.assertIn("inferPartyLabel(customerName, adults, children)", source)

        # Verify Open Facts / Open Content Studio handoff routing
        self.assertIn("Open {resolvedHandoff.stage === 'facts' ? 'Facts' : 'Content Studio'}", source)

        # Verify system copy read-only message
        self.assertIn("System copy has no quotation-level editor.", source)

    def test_contract_and_manifest_text_fields_parity(self):
        manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        manifest_fields = {item["fieldId"]: item for item in manifest_data["fields"]}

        contract_text_fields = {
            field["fieldId"]: field
            for field in self.fields
            if field.get("kind") in {"text", "richText", "aria", "altText"}
        }

        for field_id, descriptor in contract_text_fields.items():
            self.assertIn(field_id, manifest_fields, f"Text field {field_id} missing from coverage manifest.")
            manifest_entry = manifest_fields[field_id]

            self.assertEqual(manifest_entry["source"], descriptor["source"], f"Source mismatch for {field_id}")
            self.assertEqual(manifest_entry["owner"], descriptor["owner"], f"Owner mismatch for {field_id}")
            self.assertEqual(manifest_entry["kind"], descriptor["kind"], f"Kind mismatch for {field_id}")
            self.assertEqual(manifest_entry["behavior"], descriptor["editMode"], f"Behavior mismatch for {field_id}")


if __name__ == "__main__":
    unittest.main()

