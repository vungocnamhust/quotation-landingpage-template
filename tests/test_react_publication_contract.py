import unittest
from types import SimpleNamespace

import main
from pydantic import ValidationError
from db.base import Base
from quote_document import QuoteDocumentV1
from services.skeleton_builder import SkeletonBuilder


class ReactPublicationContractTests(unittest.TestCase):
    def test_brands_and_react_publication_tables_are_registered(self):
        self.assertTrue({"brands", "publication_targets", "publication_releases"}.issubset(Base.metadata.tables))

    def test_quote_document_preserves_react_presentation_contract(self):
        document = QuoteDocumentV1.model_validate({
            "meta": {"quotationId": "quo_test", "brandId": "capella_travel", "contentSchemaVersion": 1},
            "content": {"sections": {}},
            "presentation": {"renderer": "quote-generator", "themeId": "brochure", "layoutVersion": 1},
        }).model_dump(mode="json")
        self.assertEqual(document["presentation"], {
            "renderer": "quote-generator",
            "themeId": "brochure",
            "layoutVersion": 1,
            "copyOverrides": {},
            "mediaOverrides": {},
            "mediaDefaults": {},
            "identityOverrides": {},
        })

    def test_release_manifest_rewrites_media_to_brand_domain(self):
        document = {"assets": {"hero": {"r2Key": "vietnam/hero.jpg", "url": "https://r2.example/hero.jpg"}}}
        manifest = main._build_release_asset_manifest(document)
        self.assertEqual(set(manifest.values()), {"vietnam/hero.jpg"})
        token = next(iter(manifest))
        rendered = main._apply_branded_media_urls(document, hostname="journeys.capellatravel.com", release_id="pr_1", asset_manifest=manifest)
        self.assertEqual(rendered["assets"]["hero"]["url"], f"https://journeys.capellatravel.com/media/pr_1/{token}")

    def test_release_manifest_rewrites_media_to_relative_url(self):
        document = {"assets": {"hero": {"r2Key": "vietnam/hero.jpg", "url": "https://r2.example/hero.jpg"}}}
        manifest = main._build_release_asset_manifest(document)
        token = next(iter(manifest))
        rendered = main._apply_branded_media_urls(document, hostname="journeys.capellatravel.com", release_id="pr_1", asset_manifest=manifest, media_origin="")
        self.assertEqual(rendered["assets"]["hero"]["url"], f"/media/pr_1/{token}")

    def test_presentation_controls_only_accept_the_v2_allowlist(self):
        request = main.PresentationUpsertRequest.model_validate({"baseRevision": 7, "themeId": "brochure", "layoutVersion": 1})
        self.assertEqual(request.themeId, "brochure")
        with self.assertRaises(ValidationError):
            main.PresentationUpsertRequest.model_validate({"baseRevision": 7, "themeId": "legacy-jinja", "layoutVersion": 1})
        with self.assertRaises(ValidationError):
            main.PresentationUpsertRequest.model_validate({"baseRevision": 7, "themeId": "brochure", "layoutVersion": 2})
        with self.assertRaises(ValidationError):
            main.PresentationUpsertRequest.model_validate({"baseRevision": 7, "heroR2Key": "library/media/hero.jpg"})
        with self.assertRaises(Exception):
            main._validate_v2_media_overrides({"assets.hero": {"r2Key": "library/media/hero.jpg"}})

    def test_release_transition_purge_covers_old_and_new_media_manifests(self):
        target = SimpleNamespace(locale="en", public_slug="opaque-slug")
        old_release = SimpleNamespace(id="pr_old", asset_manifest={"old-token": {"r2Key": "vietnam/old.jpg"}})
        new_release = SimpleNamespace(id="pr_new", asset_manifest={"new-token": {"r2Key": "vietnam/new.jpg"}})
        urls = main._release_transition_cache_urls(
            hostnames=["journeys.capellatravel.com"],
            target=target,
            releases=[old_release, new_release],
        )
        self.assertEqual(urls, sorted(urls))
        self.assertIn("https://journeys.capellatravel.com/media/pr_old/old-token", urls)
        self.assertIn("https://journeys.capellatravel.com/media/pr_new/new-token", urls)
        self.assertIn("https://journeys.capellatravel.com/en/q/opaque-slug/pdf/download", urls)

    def test_r2_asset_is_a_valid_hero_source_before_public_url_resolution(self):
        document = QuoteDocumentV1.model_validate({
            "meta": {"quotationId": "quo_test", "brandId": "capella_travel", "contentSchemaVersion": 1},
            "content": {"sections": {}},
            "trip": {"title": "Test", "lede": "Canonical content"},
            "assets": {"hero": {"r2Key": "vietnam/hero.jpg", "status": "ready"}},
        })
        errors = main.validate_quote_document_sections(document)
        self.assertFalse(any(error.path == "assets.hero" for error in errors), errors)

    def test_skeleton_builder_derives_route_segments_from_facts(self):
        segments = SkeletonBuilder._build_stay_segments(
            [
                {"dayNumber": 1, "segmentCity": "Hanoi", "overnight": "Hanoi", "destinationRef": {"id": "dst_hanoi", "name": "Hanoi", "coordinates": [21.0285, 105.8542]}},
                {"dayNumber": 2, "segmentCity": "Hanoi", "overnight": "Hanoi", "destinationRef": {"id": "dst_hanoi", "name": "Hanoi", "coordinates": [21.0285, 105.8542]}},
                {"dayNumber": 3, "segmentCity": "Hue", "overnight": "Hue", "destinationRef": {"id": "dst_hue", "name": "Hue", "coordinates": [16.4637, 107.5909]}},
            ],
            [{"city": "Hanoi", "name": "Hotel Hanoi", "hotelDate": "01–03 Oct"}],
        )
        self.assertEqual([item["displayName"] for item in segments], ["Hanoi", "Hue"])
        self.assertEqual(segments[0]["hotelName"], "Hotel Hanoi")
        self.assertEqual(segments[0]["coords"], [21.0285, 105.8542])
        self.assertEqual((segments[0]["dayStart"], segments[0]["dayEnd"]), (1, 2))
        self.assertEqual(segments[0]["mapSegmentDesc"], "Days 1–2 — Hanoi. Stay at Hotel Hanoi.")


if __name__ == "__main__":
    unittest.main()
