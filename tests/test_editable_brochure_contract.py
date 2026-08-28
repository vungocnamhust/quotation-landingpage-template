import unittest
from copy import deepcopy
from pathlib import Path

import main
from editable_brochure_contract import (
    EDITABLE_BROCHURE_CONTRACT,
    EDITABLE_BROCHURE_FIELDS,
    MEDIA_SLOT_REGISTRY,
    _normalized_fields,
    _source_templates_intersect,
    content_write_allowlist,
    editable_contract_payload,
    expand_media_slot_field_ids,
    is_content_writable_source,
    is_design_copy_field,
    is_fact_media_field,
    resolve_id_keyed_source,
)
from core.config import settings


class EditableBrochureContractTests(unittest.TestCase):
    def test_contract_has_versioned_unique_field_ids(self):
        field_ids = [field["fieldId"] for field in EDITABLE_BROCHURE_FIELDS]
        self.assertEqual(len(field_ids), len(set(field_ids)))
        self.assertTrue(is_design_copy_field("carousel.previousImage"))
        self.assertTrue(is_fact_media_field("itinerary.days.0.gallery"))
        self.assertTrue(is_fact_media_field("assets.hero"))

    def test_media_slot_registry_owns_cardinality_and_expansion(self):
        self.assertTrue(all(slot["editorRoute"].startswith("facts.") and 0 <= slot["minItems"] <= slot["maxItems"] for slot in MEDIA_SLOT_REGISTRY))
        slots = expand_media_slot_field_ids({"itinerary": {"days": [{}, {}]}, "stays": {"hotels": [{}]}})
        self.assertIn("itinerary.days.0.gallery", slots)
        self.assertIn("itinerary.days.1.gallery", slots)
        self.assertIn("stays.hotels.0.hotelImage", slots)
        self.assertNotIn("assets.themeOrnaments.lantern", slots)

    def test_media_registry_and_field_descriptors_have_one_publish_policy(self):
        for slot in MEDIA_SLOT_REGISTRY:
            descriptor = next(
                field for field in EDITABLE_BROCHURE_FIELDS
                if field["fieldId"] == slot["fieldTemplate"]
            )
            self.assertEqual(
                descriptor["requiredForPublish"],
                slot["requiredForPublish"],
                slot["fieldTemplate"],
            )

    def test_design_override_validation_rejects_fact_and_unknown_fields(self):
        self.assertEqual(main._validate_v2_copy_overrides({"hero.primaryCta": "Explore"}), {"hero.primaryCta": "Explore"})
        with self.assertRaises(Exception):
            main._validate_v2_copy_overrides({"trip.title": "Not a Design write"})
        with self.assertRaises(Exception):
            main._validate_v2_media_overrides({"assets.hero": {"r2Key": "published/not-allowed.jpg"}})

    def test_design_descriptor_controls_and_identity_allowlist_share_one_registry(self):
        descriptors = {item["fieldId"]: item for item in editable_contract_payload()["fields"]}
        self.assertEqual(descriptors["identity.logoAlt"]["inspectorControl"], "text")
        self.assertEqual(descriptors["trip.title"]["editMode"], "handoff")
        self.assertEqual(descriptors["trip.title"]["inspectorControl"], "none")
        for field_id in ("designer.kicker", "designer.title", "designer.subtitle", "designer.quote", "designer.signature", "designer.experience", "designer.ctaBody"):
            self.assertEqual(descriptors[field_id]["owner"], "fact")
            self.assertEqual(descriptors[field_id]["editorSurface"], "design-inspector")
            self.assertEqual(descriptors[field_id]["editMode"], "inspector")
            self.assertIn(descriptors[field_id]["inspectorControl"], {"text", "textarea"})
        self.assertEqual(descriptors["trip.title"]["handoff"], {"stage": "content", "section": "hero"})
        self.assertEqual(descriptors["itinerary.days.*.dayNumber"]["owner"], "fact-derived")
        self.assertEqual(descriptors["itinerary.days.*.dayNumber"]["handoff"], {"stage": "facts", "section": "programme", "anchor": "day", "item": "day", "indexFromSource": 2})
        self.assertEqual(descriptors["route.staySegments.*.displayName"]["handoff"]["item"], "routeSegment")
        self.assertEqual(descriptors["labels.classic"]["editMode"], "readonly")
        self.assertNotIn("handoff", descriptors["labels.classic"])
        self.assertNotIn("handoffStage", descriptors["labels.classic"])
        self.assertEqual(main._validate_v2_identity_overrides({"logoAlt": "Capella logo"}), {"logoAlt": "Capella logo"})
        with self.assertRaises(Exception):
            main._validate_v2_identity_overrides({"logo": {"r2Key": "library/media/logo.jpg"}})

    def test_presentation_override_request_rejects_media_and_unknown_payload_keys(self):
        with self.assertRaises(Exception):
            main.PresentationOverridesRequest.model_validate({"baseRevision": 7, "mediaOverrides": {}})
        with self.assertRaises(Exception):
            main.PresentationCopyOverridesRequest.model_validate({"baseRevision": 7, "overrides": {}, "content": {}})

    def test_fact_media_slots_are_atomic_and_registry_limited(self):
        prefix = settings.media_library_roots[0]
        value = main._validate_v2_fact_media_slots([{"fieldId": "itinerary.days.0.gallery", "value": [{"r2Key": f"{prefix}/one.jpg"}, {"r2Key": f"{prefix}/two.jpg"}, {"r2Key": f"{prefix}/three.jpg"}]}])
        self.assertEqual(len(value["itinerary.days.0.gallery"]), 3)
        with self.assertRaises(Exception):
            main._validate_v2_fact_media_slots([{"fieldId": "assets.hero", "value": [{"r2Key": f"{prefix}/one.jpg"}, {"r2Key": f"{prefix}/two.jpg"}]}])

    def test_fact_media_slots_below_min_items_are_rejected(self):
        prefix = settings.media_library_roots[0]
        with self.assertRaises(Exception):
            main._validate_v2_fact_media_slots([{"fieldId": "itinerary.days.0.gallery", "value": [{"r2Key": f"{prefix}/one.jpg"}, {"r2Key": f"{prefix}/two.jpg"}]}])

    def test_fact_media_validation_preserves_gallery_order(self):
        prefix = settings.media_library_roots[0]
        value = main._validate_v2_fact_media_fields({"itinerary.days.0.gallery": [
            {"r2Key": f"{prefix}/one.jpg", "altText": "One"},
            {"r2Key": f"{prefix}/two.jpg", "altText": "Two"},
            {"r2Key": f"{prefix}/three.jpg", "altText": "Three"},
        ]})
        self.assertEqual(
            [item["r2Key"] for item in value["itinerary.days.0.gallery"]],
            [f"{prefix}/one.jpg", f"{prefix}/two.jpg", f"{prefix}/three.jpg"],
        )

    def test_fact_media_supports_clear_and_enforces_gallery_limit(self):
        prefix = settings.media_library_roots[0]
        self.assertEqual(main._validate_v2_fact_media_fields({"assets.hero": None}), {"assets.hero": None})
        with self.assertRaises(Exception):
            main._validate_v2_fact_media_fields({"itinerary.days.0.gallery": [{"r2Key": f"{prefix}/{index}.jpg"} for index in range(4)]})

    def test_publish_media_requirements_are_resolved_only_from_registry(self):
        document = {"assets": {}, "designer": {}, "itinerary": {"days": [{"images": {}}]}, "stays": {"hotels": [{"hotelImage": {}, "roomImage": {}}]}}
        self.assertEqual(
            main._missing_required_fact_media(document),
            ["assets.hero", "itinerary.days.0.gallery", "stays.hotels.0.hotelImage", "stays.hotels.0.roomImage"],
        )

    def test_pdf_preflight_rejects_oversized_fixed_a4_cards(self):
        document = {
            "itinerary": {"days": [{"title": "x" * 171, "description": ["brief"]}]},
            "stays": {"hotels": [{"name": "x" * 2_101}]},
            "narrative": {"letterHighlight": "x" * 501, "letterIntro": "x" * 4_000},
            "route": {"mapSegmentDescriptions": ["x" * 501]},
            "booking": {"items": [{"body": "x" * 1601}, {}, {}, {}, {}]},
        }
        self.assertEqual(
            main._pdf_layout_preflight(document),
            [
                "/itinerary/days/0/title",
                "/stays/hotels/0",
                "/narrative/letterHighlight",
                "/narrative",
                "/route/mapSegmentDescriptions/0",
                "/booking/items",
                "/booking/items/0/body",
            ],
        )

    def test_pdf_media_registry_requires_three_usable_day_images_without_optional_designer_media(self):
        document = {
            "assets": {"hero": {"r2Key": "library/media/hero.jpg"}},
            "designer": {},
            "itinerary": {"days": [{"images": {"carousel": [{"r2Key": "library/media/one.jpg"}, {"r2Key": "library/media/two.jpg"}]}}]},
            "stays": {"hotels": []},
        }
        self.assertEqual(main._missing_required_fact_media(document), ["itinerary.days.0.gallery"])

    def test_fact_media_rebase_matches_repeatable_items_by_stable_id(self):
        source = {
            "itinerary": {"days": [
                {"id": "day-1", "images": {"carousel": [{"r2Key": "library/media/day-1.jpg"}]}},
                {"id": "day-2", "images": {"carousel": [{"r2Key": "library/media/day-2.jpg"}]}},
            ]},
            "stays": {"hotels": []},
        }
        target = {"itinerary": {"days": [{"id": "day-2", "images": {}}]}, "stays": {"hotels": []}}
        main._copy_fact_media_slots(source, target)
        self.assertEqual(target["itinerary"]["days"][0]["images"]["carousel"][0]["r2Key"], "library/media/day-2.jpg")

    def test_media_mutations_accept_structurally_valid_content_drafts(self):
        document = {
            "meta": {"quotationId": "quo_media_draft", "brandId": "capella_travel"},
            "assets": {"hero": {"r2Key": "library/media/hero.jpg", "status": "ready"}},
            "trip": {"title": "Draft only"},
        }
        with self.assertRaises(Exception):
            main._validate_quote_document_or_422(document)
        self.assertEqual(
            main._normalize_quote_document_structure_or_422(document)["assets"]["hero"]["r2Key"],
            "library/media/hero.jpg",
        )

    def test_runtime_uses_canonical_gallery_before_legacy_slots(self):
        # Plan 16.1 D1/M3.1: canonical fact media always wins; the frozen
        # `presentation.mediaOverrides` is only a fallback for documents that
        # predate the single-store model.
        source = (Path(__file__).resolve().parents[1] / "quote-generator/display/runtimePageBuilder.ts").read_text()
        self.assertIn("const canonicalGallery = recordList(images.carousel)", source)
        self.assertIn("const galleryAssets = canonicalGallery.length ? canonicalGallery : galleryOverride.length ? galleryOverride : [images.hero, images.small1, images.small2].filter(Boolean)", source)

    def test_runtime_emits_the_registry_owned_inclusion_heading_descriptors(self):
        source = (Path(__file__).resolve().parents[1] / "quote-generator/display/runtimePageBuilder.ts").read_text()
        self.assertIn("designCopy(overrides, 'inclusions.inclusionsTitle'", source)
        self.assertIn("designCopy(overrides, 'inclusions.exclusionsTitle'", source)

    def test_first_drift_group_has_canonical_content_design_and_media_paths(self):
        descriptors = {item["fieldId"]: item for item in EDITABLE_BROCHURE_FIELDS}
        for field_id in (
            "hero.metaPrimary", "hero.metaSecondary", "routeMap.segmentDescription",
            "nav.brochureTheme", "a11y.routeMapOverview", "pdf.whitespaceSlogan",
            "stays.pdfTitle", "pricing.confirmedMainOption", "hotels.telephonePrefix",
            "assets.hero.altText", "assets.itineraryDivider.altText", "assets.hotelDivider.altText",
            "designer.image.altText", "itinerary.days.*.gallery.altText",
            "stays.hotels.*.hotelImage.altText", "stays.hotels.*.roomImage.altText",
        ):
            self.assertIn(field_id, descriptors)
        self.assertTrue(is_design_copy_field("pdf.whitespaceSlogan"))
        self.assertTrue(is_design_copy_field("stays.pdfTitle"))

    def test_audited_source_matrix_has_one_explicit_owner_and_handoff_policy(self):
        descriptors = {item["source"]: item for item in EDITABLE_BROCHURE_FIELDS}
        expected = {
            "/narrative/letterSignOff": ("content", "content", "overview_letter"),
            "/narrative/letterSender": ("content", "content", "overview_letter"),
            "/presentation/copyOverrides/a11y.brochureSections": ("design", None, None),
            "/presentation/identityOverrides/logoAlt": ("design", None, None),
            "/assets/hero/altText": ("fact", "facts", "trip"),
            "/itinerary/days/*/images/carousel/*/altText": ("fact", "facts", "programme"),
            "/stays/hotels/*/hotelImage/altText": ("fact", "facts", "services"),
            "/designer/name": ("fact-derived", "facts", "trip"),
            "/stays/hotels/*/roomType": ("fact", "facts", "services"),
            "/pricing/options/*/groupTotalAmountMinor": ("fact", "facts", "commercial"),
            "/itinerary/days/*/dayNumber": ("fact-derived", "facts", "programme"),
            "/route/staySegments/*/displayName": ("fact-derived", "facts", "programme"),
            "/content/sections/booking_terms/blocks/*/items/*/body": ("fact", "facts", "seller"),
            "/brand/displayName": ("fact-derived", "facts", "trip"),
            "/labels/sendEmail": ("system", None, None),
        }
        for source, (owner, stage, section) in expected.items():
            descriptor = descriptors[source]
            self.assertEqual(descriptor["owner"], owner, source)
            if stage is None:
                self.assertEqual(descriptor["editMode"], "inspector" if owner == "design" else "readonly", source)
                self.assertNotIn("handoff", descriptor, source)
            else:
                self.assertEqual(descriptor["editMode"], "handoff", source)
                self.assertEqual(descriptor["handoff"]["stage"], stage, source)
                self.assertEqual(descriptor["handoff"]["section"], section, source)

    def test_repeated_fact_handoffs_use_an_explicit_index_resolver(self):
        descriptors = {item["fieldId"]: item for item in EDITABLE_BROCHURE_FIELDS}
        for field_id in (
            "itinerary.days.*.dayNumber",
            "itinerary.days.*.meals",
            "stays.hotels.*.name",
            "pricing.options.*.label",
            "bookingTerms.item",
            "route.staySegments.*.displayName",
        ):
            handoff = descriptors[field_id]["handoff"]
            self.assertIn("item", handoff, field_id)
            self.assertIn("indexFromSource", handoff, field_id)

    def test_itinerary_meals_field_resolves_to_programme_facts_handoff(self):
        descriptors = {item["fieldId"]: item for item in EDITABLE_BROCHURE_FIELDS}
        descriptor = descriptors["itinerary.days.*.meals"]
        self.assertEqual(descriptor["owner"], "fact")
        self.assertEqual(descriptor["source"], "/itinerary/days/*/meals")
        self.assertEqual(descriptor["handoff"], {
            "stage": "facts",
            "section": "programme",
            "anchor": "day",
            "item": "day",
            "indexFromSource": 2,
        })

    def test_contract_validator_rejects_invalid_wildcards_and_owner_handoffs(self):
        invalid_wildcard = deepcopy(EDITABLE_BROCHURE_CONTRACT)
        invalid_wildcard["fields"][0]["source"] = "/presentation/*bad/brandName"
        with self.assertRaisesRegex(ValueError, "wildcard syntax"):
            _normalized_fields(invalid_wildcard)

        missing_handoff = deepcopy(EDITABLE_BROCHURE_CONTRACT)
        missing_handoff["handoffs"].pop("trip.title")
        with self.assertRaisesRegex(ValueError, "requires an explicit valid handoff"):
            _normalized_fields(missing_handoff)

        system_handoff = deepcopy(EDITABLE_BROCHURE_CONTRACT)
        system_handoff["handoffs"]["labels.classic"] = {"stage": "content", "section": "hero"}
        with self.assertRaisesRegex(ValueError, "System field"):
            _normalized_fields(system_handoff)

        invalid_editor_surface = deepcopy(EDITABLE_BROCHURE_CONTRACT)
        invalid_editor_surface["fields"][0]["editorSurface"] = "design-inspector"
        with self.assertRaisesRegex(ValueError, "invalid editor surface"):
            _normalized_fields(invalid_editor_surface)

    def test_contract_validator_rejects_intersecting_sources_and_invalid_handoff_shape(self):
        duplicate_exact = deepcopy(EDITABLE_BROCHURE_CONTRACT)
        duplicate_exact["fields"].append({**duplicate_exact["fields"][0], "fieldId": "duplicate.exact"})
        with self.assertRaisesRegex(ValueError, "source overlaps descriptor"):
            _normalized_fields(duplicate_exact)

        wildcard_exact_overlap = deepcopy(EDITABLE_BROCHURE_CONTRACT)
        wildcard_exact_overlap["fields"].append({
            **wildcard_exact_overlap["fields"][0],
            "fieldId": "duplicate.wildcard-exact",
            "source": "/itinerary/days/0/images/carousel/0/altText",
        })
        with self.assertRaisesRegex(ValueError, "source overlaps descriptor"):
            _normalized_fields(wildcard_exact_overlap)

        invalid_item = deepcopy(EDITABLE_BROCHURE_CONTRACT)
        invalid_item["handoffs"]["itinerary.days.*.title"]["item"] = "anything"
        with self.assertRaisesRegex(ValueError, "invalid handoff item"):
            _normalized_fields(invalid_item)

        invalid_anchor = deepcopy(EDITABLE_BROCHURE_CONTRACT)
        invalid_anchor["handoffs"]["itinerary.days.*.title"]["anchor"] = 7
        with self.assertRaisesRegex(ValueError, "invalid handoff anchor"):
            _normalized_fields(invalid_anchor)

        missing_repeater_resolver = deepcopy(EDITABLE_BROCHURE_CONTRACT)
        missing_repeater_resolver["handoffs"]["itinerary.days.*.title"].pop("indexFromSource")
        with self.assertRaisesRegex(ValueError, "requires a wildcard index resolver"):
            _normalized_fields(missing_repeater_resolver)


    def test_content_write_allowlist_matches_every_content_owned_source(self):
        allowlist = content_write_allowlist()
        expected = {field["source"] for field in EDITABLE_BROCHURE_FIELDS if field["owner"] == "content"}
        self.assertEqual(set(allowlist), expected)
        self.assertEqual(len(allowlist), len(expected))
        self.assertTrue(is_content_writable_source("/trip/title"))
        self.assertTrue(is_content_writable_source("/itinerary/days/3/title"))
        self.assertFalse(is_content_writable_source("/pricing_facts/options"))
        self.assertFalse(is_content_writable_source("/trip/startDate"))

    def test_param_segment_is_treated_as_a_wildcard_for_overlap_detection(self):
        self.assertTrue(_source_templates_intersect("/itinerary/days/*/title", "/itinerary/days/{dayId}/title"))
        self.assertTrue(_source_templates_intersect("/itinerary/days/{dayId}/title", "/itinerary/days/3/title"))
        self.assertFalse(_source_templates_intersect("/itinerary/days/{dayId}/title", "/itinerary/days/{dayId}/description"))

    def test_resolve_id_keyed_source_matches_entity_by_id_or_index(self):
        document = {
            "itinerary": {"days": [
                {"sourceFactId": "day-1", "dayNumber": 1},
                {"sourceFactId": "day-2", "dayNumber": 2},
            ]},
            "stays": {"hotels": [{"sourceFactId": "hotel-1"}]},
            "route": {"staySegments": [{"id": "seg-1"}]},
        }
        self.assertEqual(resolve_id_keyed_source("/itinerary/days/day-2/title", document), ("/itinerary/days/1/title", "itinerary:day:day-2"))
        self.assertEqual(resolve_id_keyed_source("/itinerary/days/1/title", document), ("/itinerary/days/1/title", "itinerary:day:day-2"))
        self.assertEqual(resolve_id_keyed_source("/stays/hotels/hotel-1/editorialIntroduction", document), ("/stays/hotels/0/editorialIntroduction", "hotel_plan"))
        self.assertEqual(resolve_id_keyed_source("/route/staySegments/seg-1/mapSegmentDesc", document), ("/route/staySegments/0/mapSegmentDesc", "route"))
        self.assertEqual(resolve_id_keyed_source("/trip/title", document), ("/trip/title", "hero"))

    def test_resolve_id_keyed_source_returns_none_for_deleted_or_non_content_targets(self):
        document = {"itinerary": {"days": [{"sourceFactId": "day-1", "dayNumber": 1}]}}
        self.assertIsNone(resolve_id_keyed_source("/itinerary/days/day-9/title", document))
        self.assertIsNone(resolve_id_keyed_source("/itinerary/days/9/title", document))
        self.assertIsNone(resolve_id_keyed_source("/pricing_facts/options", document))


if __name__ == "__main__":
    unittest.main()
