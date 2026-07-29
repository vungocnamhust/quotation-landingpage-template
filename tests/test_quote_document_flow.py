import unittest

from quote_document import build_default_sections
from quote_document_adapter import apply_quote_document_to_lang_ctx, normalize_quote_document


class QuoteDocumentFlowTests(unittest.TestCase):
    def test_normalize_quote_document_keeps_layout_and_booking_term_items(self):
        document = normalize_quote_document(
            {
                "meta": {"quotationId": "quo_test", "lang": "en", "brandId": "vietnam_safar"},
                "bookingTerms": {
                    "items": [
                        {"id": "deposit", "key": "deposit", "label": "Deposit", "body": "30% deposit"},
                        {"id": "visa", "key": "visa", "label": "Visa", "body": "Visa support on request"},
                    ]
                },
                "layout": {
                    "sections": [
                        {"id": "hero", "type": "hero", "enabled": True, "order": 2},
                        {"id": "booking_terms", "type": "booking_terms", "enabled": True, "order": 1},
                    ]
                },
            },
            "quo_test",
            "en",
        )

        self.assertEqual(document["layout"]["sections"][0]["type"], "booking_terms")
        self.assertEqual(document["layout"]["sections"][1]["type"], "hero")
        self.assertEqual(document["bookingTerms"]["items"][1]["key"], "visa")

    def test_apply_quote_document_to_lang_ctx_exposes_canonical_arrays(self):
        layout = [section.model_dump(mode="json") for section in build_default_sections()]
        document = normalize_quote_document(
            {
                "meta": {"quotationId": "quo_test", "lang": "en", "brandId": "vietnam_safar"},
                "bookingTerms": {
                    "kicker": "Important Notes",
                    "title": "Booking Terms",
                    "description": "Conditions",
                    "items": [
                        {"id": "deposit", "key": "deposit", "label": "Deposit", "body": "30% deposit"},
                        {"id": "visa", "key": "visa", "label": "Visa", "body": "Visa support on request"},
                    ],
                },
                "narrative": {
                    "journeyOverviewTitle": "A Journey Shaped Around Your Group",
                    "letterHighlight": "This journey was designed to leave room for both discovery and rest.",
                },
                "pricing": {
                    "ctaLabel": "Approve & Book Now",
                },
                "designer": {
                    "kicker": "Your Journey Designer",
                    "ctaBody": "I will remain your personal point of contact as we refine your journey.",
                    "subtitle": "(Trung Hieu Pham)",
                },
                "finalization": {
                    "requiredTitle": "Final Details Required",
                    "afterConfirmationTitle": "After Confirmation",
                    "requiredItems": [{"id": "final-req-1", "text": "Passport copies"}],
                    "afterConfirmation": [{"id": "final-after-1", "text": "Vouchers issued"}],
                },
                "layout": {"sections": layout},
            },
            "quo_test",
            "en",
        )
        lang_ctx = {"brand": {"id": "vietnam_safar"}}

        apply_quote_document_to_lang_ctx(lang_ctx, document)

        self.assertEqual(lang_ctx["booking_terms_items"][1]["label"], "Visa")
        self.assertEqual(lang_ctx["final_req"], ["Passport copies"])
        self.assertEqual(lang_ctx["final_after"], ["Vouchers issued"])
        self.assertEqual(lang_ctx["journey_overview_title"], "A Journey Shaped Around Your Group")
        self.assertEqual(lang_ctx["letter_highlight"], "This journey was designed to leave room for both discovery and rest.")
        self.assertEqual(lang_ctx["payment_cta"], "Approve & Book Now")
        self.assertEqual(lang_ctx["designer_kicker"], "Your Journey Designer")
        self.assertEqual(lang_ctx["cta_h2"], "I will remain your personal point of contact as we refine your journey.")
        self.assertEqual(lang_ctx["seller_subtitle"], "(Trung Hieu Pham)")
        self.assertTrue(lang_ctx["section_enabled"]["finalization"])


if __name__ == "__main__":
    unittest.main()
