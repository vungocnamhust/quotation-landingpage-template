from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EditableEditorCoverageTests(unittest.TestCase):
    def test_fact_editor_has_typed_brochure_controls_without_json_escape_hatch(self):
        source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "quote-generator/components/quotation-workspace").rglob("*.tsx"))
        self.assertNotIn("Advanced brochure fields", source)
        self.assertNotIn("Advanced brochure fact fields JSON", source)
        for control in (
            "Pricing options", "Pricing note", "Booking term details",
        ):
            self.assertIn(control, source)

    def test_fact_factory_owns_brochure_defaults_and_derivations(self):
        source = (ROOT / "quote-generator/components/quotation-workspace/factsTypes.ts").read_text(encoding="utf-8")
        for symbol in (
            "BROCHURE_DEFAULT_INCLUSIONS", "BROCHURE_DEFAULT_EXCLUSIONS",
            "BROCHURE_DEFAULT_BOOKING_TERMS",
            "createBrochureFacts", "serializeDraftMediaSelections",
            "createItineraryDay", "createPricingOption", "MAX_COMMERCIAL_OPTIONS",
        ):
            self.assertIn(symbol, source)
        self.assertEqual(source.count('"Any services not expressly listed as included",'), 1)

    def test_new_quotation_booking_defaults_and_serialization_match_the_plain_text_contract(self):
        types = (ROOT / "quote-generator/components/quotation-workspace/factsTypes.ts").read_text(encoding="utf-8")
        ws = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "quote-generator/components/quotation-workspace").rglob("*.tsx"))
        client = (ROOT / "quote-generator/components/quotation-workspace/NewQuotationClient.tsx").read_text(encoding="utf-8")
        defaults = types.split("export const BROCHURE_DEFAULT_BOOKING_TERMS", 1)[1].split("export function", 1)[0]
        self.assertNotIn("<ul", defaults)
        self.assertNotIn("<li", defaults)
        self.assertNotIn("<div", defaults)
        self.assertNotIn('"- > ', defaults)
        self.assertNotIn('"- < ', defaults)
        self.assertIn("assertBookingFactsArePlainText(facts.booking_facts.items)", types)
        self.assertIn("Term body (plain text)", ws)
        self.assertIn("HTML is not supported.", ws)
        self.assertIn("catch (error)", client)

    def test_multiline_fact_drafts_preserve_typing_until_save(self):
        ws = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "quote-generator/components/quotation-workspace").rglob("*.tsx"))
        types = (ROOT / "quote-generator/components/quotation-workspace/factsTypes.ts").read_text(encoding="utf-8")
        self.assertIn('const toLines = (value: string) => value.split("\\n");', ws)
        self.assertIn("const normalizedLines = (items: string[]) => items.map((item) => item.trim()).filter(Boolean);", types)
        self.assertIn("highlights: normalizedLines(day.highlights)", types)

    def test_new_quotation_wires_intake_media_selections_into_the_create_payload(self):
        create = (ROOT / "quote-generator/components/quotation-workspace/NewQuotationClient.tsx").read_text(encoding="utf-8")
        intake = (ROOT / "quote-generator/components/quotation-workspace/QuotationIntakeForm.tsx").read_text(encoding="utf-8")
        self.assertIn("handleCreateQuotation", create)
        self.assertIn("draftMediaSelections", intake)
        self.assertNotIn("FactsForm", create)
        self.assertIn("MediaSlotRenderer", intake)
        self.assertIn("BrochureAssetsEditor", intake)
        for control in ("Quotation Options", "Brief Route", "Accommodations", "Pricing", "TravelDesignerSelect", "AccommodationSelect", "DestinationSelect"):
            self.assertIn(control, intake)

    def test_fact_media_exposes_default_source_rationale_and_explicit_regeneration(self):
        media = (ROOT / "quote-generator/components/quotation-workspace/MediaSlotRenderer.tsx").read_text(encoding="utf-8")
        ws = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "quote-generator/components/quotation-workspace").rglob("*.tsx"))
        self.assertIn("resolverRationale", media)
        self.assertIn("R2 default", media)
        self.assertIn("Generate missing media", media)
        self.assertIn("Derived route", ws)
        self.assertIn("Trip title and brochure narrative are created and reviewed in Content Studio", ws)
        self.assertNotIn("AiGroupSection", ws)
        self.assertNotIn("day_asset", (ROOT / "quote-generator/components/quotation-workspace/factsTypes.ts").read_text(encoding="utf-8"))

    def test_media_defaults_uses_the_revision_locked_backend_route(self):
        ws = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "quote-generator/components/quotation-workspace").rglob("*.ts*"))
        self.assertIn("/facts/media-defaults?lang=", ws)
        self.assertNotIn("/facts/media/defaults?lang=", ws)

    def test_route_and_selected_designer_hydrate_without_a_second_editor_source(self):
        facts_types = (ROOT / "quote-generator/components/quotation-workspace/factsTypes.ts").read_text(encoding="utf-8")
        intake = (ROOT / "quote-generator/components/quotation-workspace/QuotationIntakeForm.tsx").read_text(encoding="utf-8")
        self.assertIn("resolvedDayRefs", facts_types)
        self.assertIn("syncHotelsFromItineraryOvernights", intake)

    def test_design_canvas_has_no_media_mutation_or_picker(self):
        design = (ROOT / "quote-generator/components/quotation-workspace/DesignCanvas.tsx").read_text(encoding="utf-8")
        boundary = (ROOT / "quote-generator/components/quotation-workspace/BoundaryCanvas.tsx").read_text(encoding="utf-8")
        inspector = (ROOT / "quote-generator/components/quotation-workspace/ContextualInspector.tsx").read_text(encoding="utf-8")
        self.assertNotIn("MediaPicker", design)
        self.assertNotIn("/facts/media", design)
        self.assertIn("<DisplayPage documentModel={model}", boundary)
        self.assertIn("onPointerMoveCapture", boundary)
        self.assertIn("onKeyDownCapture", boundary)
        self.assertIn("inspectorControl", inspector)

    def test_designer_fact_fields_are_editable_only_through_the_design_inspector(self):
        ws = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "quote-generator/components/quotation-workspace").rglob("*.tsx"))
        design_canvas = (ROOT / "quote-generator/components/quotation-workspace/DesignCanvas.tsx").read_text(encoding="utf-8")
        inspector = (ROOT / "quote-generator/components/quotation-workspace/ContextualInspector.tsx").read_text(encoding="utf-8")
        workspace = (ROOT / "quote-generator/components/quotation-workspace/QuotationWorkspaceClient.tsx").read_text(encoding="utf-8")
        self.assertNotIn('label="Designer signature"', ws)
        self.assertNotIn('label="Designer subtitle"', ws)
        self.assertNotIn("DesignerPresentationFields", design_canvas)
        self.assertIn("DESIGNER_FACT_FIELD_BY_DESCRIPTOR", design_canvas)
        self.assertIn("'designer.subtitle': 'seller_subtitle'", design_canvas)
        self.assertIn("editorSurface === 'design-inspector'", design_canvas)
        self.assertIn("directFactInspector", inspector)
        self.assertIn("Designer copy (saved to Facts)", inspector)
        self.assertIn("workspace.saveFacts(", workspace)

    def test_design_canvas_resolves_typed_handoffs_and_facts_urls(self):
        handoff = (ROOT / "quote-generator/components/quotation-workspace/editableHandoff.ts").read_text(encoding="utf-8")
        boundary = (ROOT / "quote-generator/components/quotation-workspace/BoundaryCanvas.tsx").read_text(encoding="utf-8")
        workspace = (ROOT / "quote-generator/components/quotation-workspace/QuotationWorkspaceClient.tsx").read_text(encoding="utf-8")
        self.assertIn("function matchEditableSource", handoff)
        self.assertIn("function resolveEditableHandoff", handoff)
        self.assertIn("function serializeFactsFocus", handoff)
        self.assertIn("function parseFactsDeepLink", handoff)
        self.assertIn("resolveInspectorDescriptor", boundary)
        self.assertIn("resolveEditableHandoff", boundary)
        self.assertIn('params.set("factsSection", target.section)', workspace)
        self.assertIn('search.get("focus")', workspace)
        self.assertIn("deepLink={factsDeepLink}", workspace)

    def test_runtime_preserves_content_letter_ownership_and_actual_booking_paths(self):
        runtime = (ROOT / "quote-generator/display/runtimePageBuilder.ts").read_text(encoding="utf-8")
        letter = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "quote-generator/components/display").rglob("*.tsx"))
        self.assertIn("signOff: contentCopy(stringValue(narrative.letterSignOff)", runtime)
        self.assertIn("'/narrative/letterSignOff'", runtime)
        self.assertIn("sender: contentCopy(stringValue(narrative.letterSender)", runtime)
        self.assertIn("'/narrative/letterSender'", runtime)
        self.assertIn("bookingTermItems(bookingBlocks)", runtime)
        self.assertIn("blocks/${blockIndex}/items/${itemIndex}", runtime)
        self.assertNotIn("textValue(viewModel.signatureRole).toUpperCase()", letter)

    def test_nav_logo_alt_and_derived_values_preserve_marker_ownership(self):
        runtime = (ROOT / "quote-generator/display/runtimePageBuilder.ts").read_text(encoding="utf-8")
        nav = (ROOT / "quote-generator/components/display/BrochureNavBar.tsx").read_text(encoding="utf-8")
        atoms = (ROOT / "quote-generator/components/display/atoms.tsx").read_text(encoding="utf-8")
        self.assertIn("function derivedCopy", runtime)
        self.assertIn("'fact-derived'", runtime)
        self.assertIn("editableProps(viewModel.brandLogoAlt ?? viewModel.brandName)", nav)
        self.assertIn("export function editableProps", atoms)

    def test_content_editor_round_trips_the_entire_candidate(self):
        source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "quote-generator/components/content-studio").rglob("*.tsx"))
        source += "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "quote-generator/components/content-studio").rglob("*.ts"))
        fields = (ROOT / "quote-generator/components/content-studio/SectionContentFields.tsx").read_text(encoding="utf-8")
        self.assertIn("function FieldEditor", fields)
        self.assertIn("function writeValue", fields)
        self.assertIn("resources.documentData?.contentRegistry", source)
        self.assertIn("FactOwnedNotice", source)
        self.assertIn("ContentGenerationPanel", source)
        self.assertNotIn("<pre>", fields)


if __name__ == "__main__":
    unittest.main()

