import unittest

from quote_document import QuoteDocumentV1, QuoteTermItem


class BrochureDisplayContractTests(unittest.TestCase):
    def test_presentation_copy_overrides_are_canonical_and_default_empty(self):
        document = QuoteDocumentV1.model_validate({
            "meta": {"quotationId": "quo_display_contract", "contentSchemaVersion": 1},
            "content": {"sections": {}},
            "presentation": {"copyOverrides": {"hero.primaryCta": "Discover"}},
        })
        self.assertEqual(document.presentation.copyOverrides, {"hero.primaryCta": "Discover"})

    def test_term_rich_text_drops_scripts_and_unsafe_urls(self):
        term = QuoteTermItem.model_validate({
            "id": "term-1",
            "body": '<p>Safe <strong>copy</strong></p><script>alert(1)</script><a href="javascript:alert(1)">bad</a>',
        })
        self.assertEqual(term.body, '<p>Safe <strong>copy</strong></p>alert(1)<a>bad</a>')
