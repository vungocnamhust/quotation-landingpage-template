import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PdfDisplayContractTests(unittest.TestCase):
    def test_pdf_uses_a_dedicated_compositor_not_the_screen_registry(self):
        source = (ROOT / "quote-generator/components/DisplayPage.tsx").read_text(encoding="utf-8")
        self.assertIn("documentModel.viewMode === 'pdf' ? <PdfBrochureDocument", source)

    def test_pdf_itinerary_pairs_days_and_uses_static_three_image_grid(self):
        source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        self.assertIn("Math.ceil(days.length / 2)", source)
        self.assertIn("slogan={pair.length === 1}", source)
        self.assertIn("slice(0, 3)", source)
        self.assertNotIn("ItineraryCarousel", source)

    def test_pdf_section_order_places_dividers_around_hotels(self):
        source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        itinerary_divider = source.index('scope="itineraryDivider"')
        hotels = source.index("<PdfHotels")
        hotel_divider = source.index('scope="staysDivider"')
        self.assertLess(itinerary_divider, hotels)
        self.assertLess(hotels, hotel_divider)

    def test_pdf_does_not_render_interactive_controls_or_avatar_fallback(self):
        pdf_source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        runtime_source = (ROOT / "quote-generator/display/runtimePageBuilder.ts").read_text(encoding="utf-8")
        self.assertNotIn("ActionButton", pdf_source)
        self.assertNotIn("hieu.jpg", runtime_source)
        self.assertIn("textValue(item.telephone)", (ROOT / "quote-generator/components/display/molecules.tsx").read_text(encoding="utf-8"))

    def test_pdf_consumes_the_shared_letter_and_media_text_values(self):
        pdf_source = (ROOT / "quote-generator/components/display/PdfBrochureDocument.tsx").read_text(encoding="utf-8")
        atoms = (ROOT / "quote-generator/components/display/atoms.tsx").read_text(encoding="utf-8")
        self.assertIn("{letter.signatureName}", pdf_source)
        self.assertIn("{letter.signatureRole}", pdf_source)
        self.assertIn("alt={textValue(alt)} {...editableProps(alt)}", atoms)


if __name__ == "__main__":
    unittest.main()
