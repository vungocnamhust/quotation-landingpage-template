import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PdfDisplayContractTests(unittest.TestCase):
    def test_pdf_uses_a_dedicated_compositor_not_the_screen_registry(self):
        source = (ROOT / "quote-generator/components/DisplayPage.tsx").read_text(encoding="utf-8")
        self.assertIn("documentModel.viewMode === 'pdf' ? <PdfBrochureDocument", source)

    def test_pdf_itinerary_pairs_days_and_uses_static_three_image_grid(self):
        source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        self.assertIn("chunkItineraryDaysForPdf", source)
        self.assertIn("day-media-thumbs", source)
        self.assertNotIn("ItineraryCarousel", source)

    def test_pdf_section_order_places_dividers_around_hotels(self):
        source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        itinerary_divider = source.index('scope="itineraryDivider"')
        stays_divider = source.index('scope="staysDivider"')
        hotels = source.index("<PdfHotels")
        journey_divider = source.index('scope="journeyTogetherDivider"')
        pricing = source.index("<PdfPricing")
        self.assertLess(itinerary_divider, stays_divider)
        self.assertLess(stays_divider, hotels)
        self.assertLess(hotels, journey_divider)
        self.assertLess(journey_divider, pricing)

    def test_pdf_does_not_render_interactive_controls_or_avatar_fallback(self):
        pdf_source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        runtime_source = (ROOT / "quote-generator/display/runtimePageBuilder.ts").read_text(encoding="utf-8")
        self.assertNotIn("ActionButton", pdf_source)
        self.assertNotIn("hieu.jpg", runtime_source)
        self.assertNotIn("hieu.jpg", pdf_source)

    def test_pdf_consumes_the_shared_letter_and_media_text_values(self):
        pdf_source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        atoms = (ROOT / "quote-generator/components/display/atoms.tsx").read_text(encoding="utf-8")
        self.assertIn("{letter.signatureName}", pdf_source)
        self.assertIn("{letter.signatureRole}", pdf_source)
        self.assertIn("alt={textValue(alt)} {...editableProps(alt)}", atoms)

    def test_pdf_itinerary_renders_footer_when_last_page_has_single_day(self):
        source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        itinerary_chunk = source[source.index("function PdfItinerary"):source.index("function PdfHotels")]
        self.assertIn("shouldShowTier3OnLastPage = isLastPage && pair.length === 1", itinerary_chunk)
        self.assertIn("<PdfFooterTier3 documentModel={documentModel} />", itinerary_chunk)

    def test_pdf_route_map_renders_full_bleed_single_canvas_without_separate_tiers(self):
        source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        route_map_chunk = source[source.index("function PdfRouteMap"):source.index("function PdfChapterDivider")]
        self.assertIn("pdf-route-page--fullbleed", route_map_chunk)
        self.assertNotIn("pdf-route__mid-tier", route_map_chunk)

    def test_pdf_map_is_pinned_to_google_classic_and_exposes_a_render_state(self):
        canvas = (ROOT / "quote-generator/components/display/map/LuxuryMapGeoCanvas.tsx").read_text(encoding="utf-8")
        island = (ROOT / "quote-generator/components/display/RouteMapClientIsland.tsx").read_text(encoding="utf-8")
        full_page = (ROOT / "quote-generator/components/display/map/FullPageEditorialJourneyMap.tsx").read_text(encoding="utf-8")
        route = (ROOT / "quote-generator/app/api/map-tiles/[z]/[x]/[y]/route.ts").read_text(encoding="utf-8")

        self.assertIn("google-classic-pdf-v1", full_page)
        self.assertIn("tileLayer.once('load'", canvas)
        self.assertIn("tileLayer.once('tileerror'", canvas)
        self.assertIn("data-map-render-state", island)
        self.assertIn("resolveMapTileProviders", route)
        self.assertIn("Unsupported map tile style.", route)

    def test_publisher_waits_for_map_terminal_state_and_rejects_tile_failure(self):
        source = (ROOT / "services/publication_runtime.py").read_text(encoding="utf-8")

        self.assertIn("[data-map-render-state]", source)
        self.assertIn("page.wait_for_function", source)
        self.assertIn("map_state == 'failed'", source)
        self.assertIn("PDF map tiles failed to render", source)


if __name__ == "__main__":
    unittest.main()
