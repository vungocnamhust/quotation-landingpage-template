import tempfile
import unittest
from pathlib import Path

from scripts.clone_legacy_quote import (
    _select_source_html_path,
    build_payload,
    clone_source_overrides_to_target_html,
)


class CloneLegacyQuoteTests(unittest.TestCase):
    def test_select_source_html_path_uses_latest_versioned_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "v2.html").write_text("old", encoding="utf-8")
            (base / "v10.html").write_text("latest", encoding="utf-8")
            (base / "pdf.html").write_text("ignore", encoding="utf-8")

            selected = _select_source_html_path(base)

            self.assertEqual(selected.name, "v10.html")

    def test_build_payload_applies_template_and_contact_overrides(self):
        payload = {
            "template_name": "old.html",
            "seller": {
                "companyName": "Vietnam Safar",
                "contactName": "Legacy Seller",
            },
        }
        ctx = {"designer_img": "/assets/dias_team/hieu.jpg"}

        updated = build_payload(
            source_payload=payload,
            source_ctx=ctx,
            target_template="prototype_itinerary_imagery.html",
            target_brand="capella_travel",
            target_contact_name="Nam",
        )

        self.assertEqual(updated["template_name"], "prototype_itinerary_imagery.html")
        self.assertEqual(updated["template"], "prototype_itinerary_imagery.html")
        self.assertEqual(updated["seller"]["companyName"], "Capella Travel")
        self.assertEqual(updated["seller"]["contactName"], "Nam")

    def test_clone_skips_inline_data_images_but_keeps_text_overrides(self):
        target_html = """
        <html><body>
          <div data-editable="day_title_1">Target Title</div>
          <div data-editable="day_img_hero_1" style="background-image:url('/assets/new.jpg')"></div>
        </body></html>
        """
        source_html = """
        <html style="--hero-img: url('data:image/png;base64,AAA')"><body>
          <div data-editable="day_title_1"><b>Source Title</b></div>
          <div data-editable="day_img_hero_1" style="background-image:url('data:image/png;base64,BBB')"></div>
        </body></html>
        """

        merged = clone_source_overrides_to_target_html(
            target_html=target_html,
            source_html=source_html,
            source_ctx={"hotels": []},
            source_payload={},
        )

        self.assertIn("<b>Source Title</b>", merged)
        self.assertIn("/assets/new.jpg", merged)
        self.assertNotIn("data:image/png;base64,BBB", merged)


if __name__ == "__main__":
    unittest.main()
