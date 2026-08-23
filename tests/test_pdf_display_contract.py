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

    def test_pdf_map_uses_no_label_raster_and_exposes_a_render_state(self):
        canvas = (ROOT / "quote-generator/components/display/map/pdf/LuxuryMapGeoCanvas.tsx").read_text(encoding="utf-8")
        island = (ROOT / "quote-generator/components/display/RouteMapClientIsland.tsx").read_text(encoding="utf-8")
        full_page = (ROOT / "quote-generator/components/display/map/pdf/FullPageEditorialJourneyMap.tsx").read_text(encoding="utf-8")
        route = (ROOT / "quote-generator/app/api/map-tiles/[z]/[x]/[y]/route.ts").read_text(encoding="utf-8")

        self.assertIn("carto-parchment-nolabels-pdf-v1", full_page)
        self.assertIn("tileLayer.once('load'", canvas)
        self.assertIn("tileLayer.once('tileerror'", canvas)
        self.assertIn("data-map-render-state", island)
        self.assertIn("resolveMapTileProviders", route)
        self.assertIn("prepareMapTileRaster", route)
        self.assertIn("runtime = 'nodejs'", route)
        self.assertIn("Unsupported map tile style.", route)
        overlays = (ROOT / "quote-generator/components/display/map/pdf/MapFloatingOverlays.tsx").read_text(encoding="utf-8")
        self.assertIn("visibility={isPdf ? 'islands' : 'all'}", overlays)
        labels = (ROOT / "quote-generator/components/display/map/pdf/MapGeoLabels.tsx").read_text(encoding="utf-8")
        self.assertIn("geo-hoang-sa", labels)
        self.assertIn("geo-truong-sa", labels)
        self.assertIn("visibility === 'islands' && item.type !== 'island'", labels)
        self.assertIn("luxury-map-header-block--pdf", overlays)
        self.assertIn("luxury-map-bottom-overlay--pdf", overlays)

    def test_map_raster_treatment_is_scoped_to_style_specific_tile_layers(self):
        css = (ROOT / "quote-generator/app/globals.css").read_text(encoding="utf-8")
        theme_tokens = (ROOT / "quote-generator/config/themeTokens.ts").read_text(encoding="utf-8")
        full_page = (ROOT / "quote-generator/components/display/map/pdf/FullPageEditorialJourneyMap.tsx").read_text(encoding="utf-8")

        self.assertIn("--filter-map-tiles", theme_tokens)
        self.assertIn("--color-map-canvas-veil", theme_tokens)
        self.assertIn(".map-tile-raster--google-prototype-v1 img.leaflet-tile", css)
        self.assertIn(".map-tile-raster--parchment-pdf-v1 img.leaflet-tile", css)
        self.assertIn("img.leaflet-tile", css)
        self.assertIn("mix-blend-mode: normal !important", css)
        self.assertIn(".display-route-map__leaflet", css)
        self.assertNotIn(".luxury-map-geo-canvas {\n  filter:", css)
        self.assertNotIn(".display-route-map__leaflet {\n  /* Scope the theme-resolved treatment", css)
        self.assertNotIn('html[data-view-mode="pdf"] .leaflet-tile', css)
        self.assertNotRegex(css, r"(?m)^\\.leaflet-tile\\s*\\{\\s*\\n\\s*filter:")
        self.assertIn("luxury-map-canvas-veil", full_page)

    def test_web_and_pdf_map_layout_engines_are_isolated_from_domain_rules(self):
        web_root = ROOT / "quote-generator/components/display/map/web"
        pdf_root = ROOT / "quote-generator/components/display/map/pdf"
        for source_path in web_root.rglob("*.ts*"):
            source = source_path.read_text(encoding="utf-8")
            self.assertNotIn("/map/pdf/", source)
            self.assertNotIn("../pdf/", source)
        for source_path in pdf_root.rglob("*.ts*"):
            source = source_path.read_text(encoding="utf-8")
            self.assertNotIn("/map/web/", source)
            self.assertNotIn("../web/", source)
        self.assertFalse((ROOT / "quote-generator/lib/rules/mapMarkerLayoutRules.ts").exists())
        self.assertFalse((ROOT / "quote-generator/lib/rules/routeDrawingRules.ts").exists())
        self.assertFalse((ROOT / "quote-generator/lib/rules/jointRouteMarkerOptimizer.ts").exists())

    def test_pdf_letter_renders_indochine_line_divider_above_highlight(self):
        source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        css = (ROOT / "quote-generator/app/globals.css").read_text(encoding="utf-8")

        self.assertIn("line_divider.svg", source)
        self.assertIn("pdf-letter__highlight-block", source)
        self.assertIn("pdf-letter__divider", source)
        self.assertIn(".pdf-letter__highlight-block", css)
        self.assertIn(".pdf-letter__divider", css)

    def test_pdf_pricing_1_option_layout_contract(self):
        source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        css = (ROOT / "quote-generator/app/globals.css").read_text(encoding="utf-8")

        self.assertIn("pdf-pricing-basis__divider", source)
        self.assertIn("cleanGroupTotal", source)
        self.assertIn(".pdf-pricing-basis__divider", css)
        self.assertIn(".pdf-pricing-page-inner--hero", css)
        self.assertIn(".pdf-pricing-page .pdf-brochure-page__content", css)
        self.assertNotIn("pdf-pricing__header--centered", source)
        self.assertNotIn("pdf-pricing-basis--centered", source)


if __name__ == "__main__":
    unittest.main()
