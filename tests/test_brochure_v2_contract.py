import asyncio
import copy
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import create_quotation_api_v2
import main
from db.base import Base
from quote_document import AssetSelectionResult, validate_quote_document_sections
from quote_document_adapter import normalize_quote_document
from quote_generation import (
    BRAND_PROFILES,
    NarrativeGenerationResult,
    NarrativeGenerator,
    apply_narrative_result_to_document,
)
from repositories import PublicationRepository, QuotationDocumentRepository, QuotationRepository


def _sample_document() -> dict:
    return normalize_quote_document(
        {
            "meta": {
                "quotationId": "quo_test",
                "lang": "en",
                "brandId": "vietnam_safar",
                "opportunityId": "OPP-1",
            },
            "trip": {
                "title": "Vietnam Private Journey",
                "lede": "Curated for two guests.",
            },
            "assets": {
                "hero": {"url": "/assets/vietnam-safar-logo.png"},
            },
            "narrative": {
                "letterIntro": "An elegant journey through Vietnam.",
                "letterBody2": "Balanced pacing and premium service.",
            },
            "route": {
                "staySegments": [
                    {"id": "stay-1", "displayName": "Hanoi"},
                ]
            },
            "itinerary": {
                "days": [
                    {
                        "id": "day-1",
                        "dayNumber": 1,
                        "segmentCity": "Hanoi",
                        "title": "Arrival in Hanoi",
                        "description": ["Private arrival and transfer."],
                    }
                ]
            },
            "stays": {
                "hotels": [{"id": "hotel-1", "city": "Hanoi", "name": "Capella Hanoi"}],
            },
            "pricing": {
                "options": [{"id": "price-1", "name": "Main option"}],
            },
            "inclusions": [{"id": "inc-1", "text": "Private transfers"}],
            "exclusions": [{"id": "exc-1", "text": "International flights"}],
            "bookingTerms": {
                "items": [
                    {"id": "deposit", "key": "deposit", "label": "Deposit", "body": "30% deposit"},
                    {"id": "balance", "key": "balance", "label": "Balance", "body": "Balance before travel"},
                    {"id": "cancellation", "key": "cancellation", "label": "Cancellation", "body": "Supplier terms apply"},
                    {"id": "confirmation", "key": "confirmation", "label": "Confirmation", "body": "Subject to availability"},
                ]
            },
            "designer": {"name": "Vietnam Safar"},
            "finalization": {
                "requiredItems": [{"id": "req-1", "text": "Passport copy"}],
                "afterConfirmation": [{"id": "after-1", "text": "Final vouchers issued"}],
            },
        },
        "quo_test",
        "en",
    )


class QuoteDocumentValidationTests(unittest.TestCase):
    def test_unknown_section_type_is_reported(self):
        document = _sample_document()
        document["layout"]["sections"][0]["type"] = "mystery"

        errors = validate_quote_document_sections(document)

        self.assertEqual(errors[0].code, "unknown_section_type")
        self.assertEqual(errors[0].path, "layout.sections.0.type")

    def test_normalize_quote_document_dedupes_double_escaped_day_carousel_urls(self):
        document = _sample_document()
        duplicate_url = "/published/quo_f7175e110605/draft_assets/e17a0f2b9d5c4f50a91502fd4fa2ca17.jpg"
        document["itinerary"]["days"][0]["images"] = {
            "hero": {"url": "/assets/quang-nam/hoian3.jpg"},
            "small1": {"url": "/assets/quang-nam/hero/hero3.jpg"},
            "small2": {"url": duplicate_url},
            "carousel": [
                {"url": "/assets/quang-nam/hoian3.jpg"},
                {"url": "/assets/quang-nam/hero/hero3.jpg"},
                {"url": duplicate_url},
                {"url": f"&quot;{duplicate_url}&quot;"},
                {"url": f"&amp;quot;{duplicate_url}&amp;quot;"},
            ],
        }

        normalized = normalize_quote_document(document, "quo_test", "en")

        self.assertEqual(
            [item["url"] for item in normalized["itinerary"]["days"][0]["images"]["carousel"]],
            [
                "/assets/quang-nam/hoian3.jpg",
                "/assets/quang-nam/hero/hero3.jpg",
                duplicate_url,
            ],
        )

    def test_apply_narrative_result_only_overwrites_requested_scopes(self):
        document = _sample_document()
        original_intro = document["narrative"]["letterIntro"]
        narrative = NarrativeGenerationResult(
            lede="Fresh hero lede",
            coverKicker="A New Invitation",
            heroMeta1="9 Days / 8 Nights",
            heroMeta2="2026-09-01 - 2026-09-09",
            letterIntro="New overview intro",
        )

        updated = apply_narrative_result_to_document(document, narrative, ["hero"])

        self.assertEqual(updated["trip"]["lede"], "Fresh hero lede")
        self.assertEqual(updated["narrative"]["coverKicker"], "A New Invitation")
        self.assertEqual(updated["narrative"]["letterIntro"], original_intro)

    def test_html_sync_dedupe_image_refs_removes_double_escaped_quotes(self):
        duplicate_url = "/published/quo_f7175e110605/draft_assets/e17a0f2b9d5c4f50a91502fd4fa2ca17.jpg"

        deduped = main._dedupe_image_refs([
            duplicate_url,
            f"&quot;{duplicate_url}&quot;",
            f"&amp;quot;{duplicate_url}&amp;quot;",
        ])

        self.assertEqual(deduped, [duplicate_url])


class NarrativeGeneratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_generated_copy_changes_with_brand_profile(self):
        request = main.CreateQuoteRequestV1.model_validate(
            {
                "brand_id": "capella_travel",
                "trip_facts": {
                    "title": "Northern Vietnam Escape",
                    "itinerary": [{"day_number": 1, "destination": "Hanoi", "summary": "Arrival"}],
                },
            }
        )

        class FakeAgent:
            async def run(self, prompt):
                if "Capella Travel" in prompt:
                    output = NarrativeGenerationResult(lede="Editorial arrival in Hanoi.", letterIntro="An editorial, polished introduction.")
                else:
                    output = NarrativeGenerationResult(lede="Sanctuary arrival in Hanoi.", letterIntro="A serene sanctuary introduction.")
                return type("Result", (), {"output": output})()

        generator = NarrativeGenerator()
        with patch.object(generator, "_get_agent", return_value=FakeAgent()):
            capella_result, capella_status, _ = await generator.generate(request, BRAND_PROFILES["capella_travel"])
            selvara_result, selvara_status, _ = await generator.generate(
                request.model_copy(update={"brand_id": "selvara"}),
                BRAND_PROFILES["selvara"],
            )

        self.assertEqual(capella_status, "generated")
        self.assertEqual(selvara_status, "generated")
        self.assertNotEqual(capella_result.lede, selvara_result.lede)
        self.assertNotEqual(capella_result.letterIntro, selvara_result.letterIntro)

    async def test_generation_falls_back_when_model_fails(self):
        request = main.CreateQuoteRequestV1.model_validate(
            {
                "brand_id": "vietnam_safar",
                "trip_facts": {
                    "title": "Vietnam Escape",
                    "itinerary": [{"day_number": 1, "destination": "Hanoi", "summary": "Arrival"}],
                },
            }
        )

        class BrokenAgent:
            async def run(self, prompt):
                raise RuntimeError("model timeout")

        generator = NarrativeGenerator()
        with patch.object(generator, "_get_agent", return_value=BrokenAgent()):
            result, status, warnings = await generator.generate(request, BRAND_PROFILES["vietnam_safar"])

        self.assertEqual(status, "fallback")
        self.assertTrue(result.lede)
        self.assertIn("fallback", warnings[0].lower())

    async def test_generation_preserves_live_parity_facts(self):
        request = main.CreateQuoteRequestV1.model_validate(
            {
                "brand_id": "capella_travel",
                "trip_facts": {
                    "title": "Tina's Vietnam Birthday Escape",
                    "subtitle": "A refined private journey.",
                    "hero_meta_1": "14 DAYS • 13 NIGHTS • luxury boutique",
                    "hero_meta_2": "27 MAR – 09 APR 2027",
                    "journey_overview_title": "A Journey Shaped Around Your Group",
                    "letter_highlight": "This journey was designed to leave room for both discovery and rest.",
                    "letter_greeting": "Dear Tina & Friends,",
                    "letter_intro": "I am delighted to present this privately arranged journey: Tina's Vietnam Birthday Escape.",
                    "letter_body": "The programme has been considered around a gentler friendly rhythm.",
                    "letter_outro": "Please review the journey as a starting point for a personal conversation.",
                    "letter_sign_off": "Eddie",
                    "letter_sender": "Travel Designer",
                    "footer_text": "Capella Travel - Tina's Vietnam Birthday Escape",
                    "route_title": "Your Journey, Mapped",
                    "route_description": "Follow Tina's curated path through Vietnam.",
                    "itinerary_title": "Day-by-Day Journey Program",
                    "itinerary_description": "Your private 14D13N journey — 14 days, carefully crafted.",
                    "itinerary": [
                        {
                            "day_number": 1,
                            "destination": "Hanoi",
                            "summary": "Arrival in Hanoi",
                            "display_title": "Day 1 — Hanoi",
                            "highlights": ["Private airport welcome"],
                            "notes": ["Sense of Pace: Relaxed"],
                        }
                    ],
                },
                "pricing_facts": {
                    "display_title": "Journey Investment:",
                    "display_subtitle": "Currency: USD. Final rates subject to reconfirmation.",
                    "cta_label": "Approve & Book Now",
                    "options": [
                        {
                            "category": "Luxury boutique",
                            "name": "Package 14D13N",
                            "per_person_text": "USD 4,450 per person",
                            "total_text": "USD 48,950 total",
                            "is_total": False,
                            "is_confirmed_main_option": True,
                        }
                    ],
                },
                "booking_facts": {
                    "title": "Booking & Payment Terms",
                    "description": "Commercial conditions, deposits, and cancellation policy for this booking.",
                    "items": [{"key": "deposit", "label": "Deposit", "body": "A 30% deposit is required."}],
                },
                "finalization_facts": {
                    "required_title": "Final Details Required",
                    "after_confirmation_title": "After Confirmation",
                    "required_items": ["Copy of passport valid for 6 months."],
                    "after_confirmation_items": ["24/7 dedicated local concierge support."],
                },
                "seller_facts": {
                    "seller_name": "Eddie",
                    "seller_subtitle": "(Trung Hieu Pham)",
                    "designer_signature": "Travel Designer",
                    "designer_kicker": "Your Journey Designer",
                    "designer_quote": "I believe the desire to travel is contagious.",
                    "designer_title": "Let Us Shape the Final Details Together",
                    "cta_body": "I will remain your personal point of contact as we refine your journey.",
                },
            }
        )

        async def fake_assets(_request):
            return AssetSelectionResult(
                hero="/assets/hero.jpg",
                destinations={"Hanoi": ["/assets/hanoi.jpg"]},
                hotels={},
                dividers={"itinerary": "/assets/itinerary.jpg", "hotel": "/assets/hotel.jpg"},
            )

        async def fake_narrative(self, _request, _brand_profile, **kwargs):
            return (
                NarrativeGenerationResult(
                    lede="Fallback lede",
                    journeyOverviewTitle="Generated but should not override",
                    letterGreeting="Generated greeting",
                    letterIntro="Generated intro",
                    letterBody2="Generated body",
                    letterOutro="Generated outro",
                    letterSignOff="Generated sign off",
                    letterSender="Generated sender",
                ),
                "generated",
                [],
            )

        service = main.QuoteGenerationService()
        with patch("quote_generation.select_assets", new=fake_assets):
            with patch.object(service.narrative_generator, "generate", new=fake_narrative.__get__(service.narrative_generator, type(service.narrative_generator))):
                document = await service.generate(request)

        self.assertEqual(document.narrative.journeyOverviewTitle, "A Journey Shaped Around Your Group")
        self.assertEqual(document.narrative.letterGreeting, "Dear Tina & Friends,")
        self.assertEqual(document.narrative.letterIntro, "I am delighted to present this privately arranged journey: Tina's Vietnam Birthday Escape.")
        self.assertEqual(document.narrative.letterSignOff, "Eddie")
        self.assertEqual(document.narrative.letterSender, "Travel Designer")
        self.assertEqual(document.pricing.title, "Journey Investment:")
        self.assertEqual(document.pricing.description, "Currency: USD. Final rates subject to reconfirmation.")
        self.assertEqual(document.pricing.ctaLabel, "Approve & Book Now")
        self.assertEqual(document.designer.kicker, "Your Journey Designer")
        self.assertEqual(document.designer.ctaBody, "I will remain your personal point of contact as we refine your journey.")
        self.assertEqual(document.designer.subtitle, "(Trung Hieu Pham)")
        self.assertEqual(document.finalization.afterConfirmation[0].text, "24/7 dedicated local concierge support.")


class CreateQuotationApiV2PayloadTests(unittest.TestCase):
    def test_build_payload_prefers_live_editable_texts(self):
        ctx = {
            "quotation_number": "VN-2027-LUX",
            "tour_title": "Ctx Title",
            "hero_meta_1": "CTX META 1",
            "travel_dates": "CTX DATES",
            "route_map_h2": "Ctx Route",
            "route_map_p": "Ctx Route Description",
            "itinerary_h2": "Ctx Itinerary",
            "itinerary_p": "Ctx Itinerary Description",
            "pricing_h2": "Ctx Pricing",
            "pricing_p": "Ctx Pricing Description",
            "payment_title": "Ctx Terms",
            "payment_desc": "Ctx Terms Description",
            "seller_name": "Ctx Seller",
            "itinerary_days": [{"dayNumber": 1, "segment_city": "Hanoi", "title": "Day 1 — Hanoi", "description": ["Arrival"]}],
            "price_options": [],
            "hotels": [],
            "final_req": [],
            "final_after": [],
        }
        live_html = """
        <div data-editable="tour_title">Live Title</div>
        <div data-editable="hero_meta_1">LIVE META 1</div>
        <div data-editable="hero_meta_2">27 MAR – 09 APR 2027</div>
        <div data-editable="journey_overview_title">A Journey Shaped Around Your Group</div>
        <div data-editable="letter_intro">Live intro</div>
        <div data-editable="pricing_h2">Journey Investment:</div>
        <div data-editable="pricing_p">Currency: USD. Final rates subject to reconfirmation.</div>
        <div data-editable="payment_cta">Approve &amp; Book Now</div>
        <div data-editable="seller_name">Eddie</div>
        <div data-editable="seller_subtitle">(Trung Hieu Pham)</div>
        <div data-editable="designer_kicker">Your Journey Designer</div>
        <div data-editable="cta_h2">Live CTA body</div>
        """

        with patch.object(create_quotation_api_v2, "_load_json", return_value=ctx):
            with patch.object(create_quotation_api_v2, "_load_source_html", return_value=live_html):
                payload = create_quotation_api_v2.build_payload()

        self.assertEqual(payload["trip_facts"]["title"], "Live Title")
        self.assertEqual(payload["trip_facts"]["hero_meta_1"], "LIVE META 1")
        self.assertEqual(payload["trip_facts"]["journey_overview_title"], "A Journey Shaped Around Your Group")
        self.assertEqual(payload["trip_facts"]["letter_intro"], "Live intro")
        self.assertEqual(payload["pricing_facts"]["display_title"], "Journey Investment:")
        self.assertEqual(payload["pricing_facts"]["cta_label"], "Approve & Book Now")
        self.assertEqual(payload["seller_facts"]["seller_name"], "Eddie")
        self.assertEqual(payload["seller_facts"]["seller_subtitle"], "(Trung Hieu Pham)")
        self.assertEqual(payload["seller_facts"]["designer_kicker"], "Your Journey Designer")
        self.assertEqual(payload["seller_facts"]["cta_body"], "Live CTA body")


class BrochureRouteContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._init_db())
        cls.session_patch = patch.object(main, "_get_db_session_factory", return_value=cls.session_factory)
        cls.session_patch.start()
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        cls.session_patch.stop()
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.db_file.name)

    @classmethod
    async def _init_db(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    @classmethod
    async def _reset_db(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    @classmethod
    async def _seed_brochure_document(cls, quotation_id: str, document: dict):
        async with cls.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            document_repo = QuotationDocumentRepository(session)
            quotation = await quotation_repo.create_quotation(
                quotation_id=quotation_id,
                brand_id="vietnam_safar",
                template_name=main.BROCHURE_TEMPLATE_NAME,
                baseline_lang="en",
                opportunity_id="OPP-1",
                current_version=1,
            )
            saved_document = await document_repo.save_current_document(
                quotation_id=quotation_id,
                lang="en",
                document_json=document,
                expected_revision=0,
                generation_status=document.get("generationStatus") or {},
            )
            canonical_document = main._hydrate_canonical_quote_document(
                saved_document.document_json,
                quotation,
                lang="en",
                revision=saved_document.revision,
            )
            await document_repo.append_document_revision(
                quotation_id=quotation_id,
                lang="en",
                revision=saved_document.revision,
                document_json=canonical_document,
                change_source="create",
            )
            await session.commit()

    def setUp(self):
        main.quotations.pop("quo_test", None)
        asyncio.run(self._reset_db())

    def tearDown(self):
        test_dir = os.path.join("published", "quo_test")
        if os.path.isdir(test_dir):
            shutil.rmtree(test_dir)

    def test_v1_route_rejects_brochure_template(self):
        response = self.client.post("/quotations", json={"template_name": "vietnam_luxury_brosure.html"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("/api/v2/quotations", response.json()["detail"])

    def test_put_document_rejects_invalid_section_contract(self):
        document = _sample_document()
        asyncio.run(self._seed_brochure_document("quo_test", copy.deepcopy(document)))
        main.quotations["quo_test"] = {"ctx": {
            "template_name": main.BROCHURE_TEMPLATE_NAME,
            "baseline_lang": "en",
            "available_langs": ["en"],
            "translation_status": {"baseline_lang": "en", "available_langs": ["en"]},
            "quoteDocuments": {"en": copy.deepcopy(document)},
            "quoteDocument": copy.deepcopy(document),
            "quoteDocumentLang": "en",
            "brand": {"id": "vietnam_safar"},
        }}
        invalid_document = copy.deepcopy(document)
        invalid_document["layout"]["sections"][0]["type"] = "mystery"

        response = self.client.put(
            "/api/v2/quotations/quo_test/document",
            json={"document": invalid_document, "baseRevision": 1},
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()["detail"]["errors"][0]
        self.assertEqual(payload["code"], "unknown_section_type")

    def test_v2_create_does_not_call_legacy_build_ctx(self):
        sample_document = _sample_document()
        created_id = None

        async def fake_generate(self, request):
            return main.QuoteDocumentV1.model_validate(sample_document)

        with patch.object(main.QuoteGenerationService, "generate", new=fake_generate):
            with patch.object(main, "_build_ctx", side_effect=AssertionError("_build_ctx should not run for brochure v2")):
                response = self.client.post(
                    "/api/v2/quotations",
                    json={
                        "opportunity_id": "OPP-V2",
                        "brand_id": "vietnam_safar",
                        "lang": "en",
                        "trip_facts": {
                            "title": "Vietnam Private Journey",
                            "itinerary": [{"day_number": 1, "destination": "Hanoi", "summary": "Arrival"}],
                        },
                    },
                )
        self.assertEqual(response.status_code, 200)
        created_id = response.json()["quotationId"]
        stored_ctx = main.quotations[created_id]["ctx"]
        self.assertIn("quoteDocuments", stored_ctx)
        self.assertIn("en", stored_ctx["quoteDocuments"])
        quotation, canonical_document, canonical_lang = asyncio.run(
            main._load_canonical_quote_document_from_db(created_id, "en")
        )
        self.assertIsNotNone(quotation)
        self.assertEqual(canonical_lang, "en")
        self.assertEqual(canonical_document["meta"]["quotationId"], created_id)

        async def _assert_no_publications():
            async with self.session_factory() as session:
                publication_repo = PublicationRepository(session)
                publications = await publication_repo.list_publications(created_id, lang="en")
                self.assertEqual(publications, [])

        asyncio.run(_assert_no_publications())
        created_dir = os.path.join("published", created_id)
        if os.path.isdir(created_dir):
            shutil.rmtree(created_dir)

    def test_get_brochure_bootstraps_from_document_file_when_ctx_lost_document(self):
        document = _sample_document()
        quo_dir = os.path.join("published", "quo_test")
        os.makedirs(quo_dir, exist_ok=True)
        with open(os.path.join(quo_dir, "document.json"), "w", encoding="utf-8") as f:
            json.dump(document, f, ensure_ascii=False)

        main.quotations["quo_test"] = {
            "ctx": {
                "template_name": main.BROCHURE_TEMPLATE_NAME,
                "baseline_lang": "en",
                "available_langs": ["en"],
                "translation_status": {"baseline_lang": "en", "available_langs": ["en"]},
                "brand": {"id": "vietnam_safar"},
            }
        }

        response = self.client.get("/quotations/quo_test")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Vietnam Private Journey", response.text)
        stored_ctx = main.quotations["quo_test"]["ctx"]
        self.assertIn("quoteDocuments", stored_ctx)
        self.assertIn("en", stored_ctx["quoteDocuments"])

    def test_get_document_reads_canonical_postgres_document(self):
        document = _sample_document()
        asyncio.run(self._seed_brochure_document("quo_test", copy.deepcopy(document)))

        response = self.client.get("/api/v2/quotations/quo_test/document")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["document"]["trip"]["title"], "Vietnam Private Journey")
        self.assertEqual(response.json()["currentRevision"], 1)

    def test_put_document_returns_409_when_base_revision_is_stale(self):
        document = _sample_document()
        asyncio.run(self._seed_brochure_document("quo_test", copy.deepcopy(document)))
        main.quotations["quo_test"] = {"ctx": {
            "template_name": main.BROCHURE_TEMPLATE_NAME,
            "baseline_lang": "en",
            "available_langs": ["en"],
            "translation_status": {"baseline_lang": "en", "available_langs": ["en"]},
            "quoteDocuments": {"en": copy.deepcopy(document)},
            "quoteDocument": copy.deepcopy(document),
            "quoteDocumentLang": "en",
            "brand": {"id": "vietnam_safar"},
        }}

        first_document = copy.deepcopy(document)
        first_document["trip"]["title"] = "Writer One"
        first_response = self.client.put(
            "/api/v2/quotations/quo_test/document",
            json={"document": first_document, "baseRevision": 1},
        )
        self.assertEqual(first_response.status_code, 200)

        stale_document = copy.deepcopy(document)
        stale_document["trip"]["title"] = "Writer Two"
        stale_response = self.client.put(
            "/api/v2/quotations/quo_test/document",
            json={"document": stale_document, "baseRevision": 1},
        )

        self.assertEqual(stale_response.status_code, 409)
        self.assertEqual(stale_response.json()["detail"]["currentRevision"], 2)
        self.assertEqual(
            stale_response.json()["detail"]["currentDocument"]["trip"]["title"],
            "Writer One",
        )

    def test_put_document_succeeds_when_legacy_ctx_sync_fails_after_db_commit(self):
        document = _sample_document()
        asyncio.run(self._seed_brochure_document("quo_test", copy.deepcopy(document)))
        main.quotations["quo_test"] = {"ctx": {
            "template_name": main.BROCHURE_TEMPLATE_NAME,
            "baseline_lang": "en",
            "available_langs": ["en"],
            "translation_status": {"baseline_lang": "en", "available_langs": ["en"]},
            "quoteDocuments": {"en": copy.deepcopy(document)},
            "quoteDocument": copy.deepcopy(document),
            "quoteDocumentLang": "en",
            "brand": {"id": "vietnam_safar"},
        }}
        updated_document = copy.deepcopy(document)
        updated_document["trip"]["title"] = "Saved Despite Ctx Failure"

        with patch.object(main, "_persist_ctx_data", side_effect=RuntimeError("ctx sync failed")):
            response = self.client.put(
                "/api/v2/quotations/quo_test/document",
                json={"document": updated_document, "baseRevision": 1},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["currentRevision"], 2)

        async def _assert_saved():
            quotation, saved_document, _ = await main._load_canonical_quote_document_from_db("quo_test", "en")
            self.assertIsNotNone(quotation)
            self.assertEqual(saved_document["trip"]["title"], "Saved Despite Ctx Failure")
            self.assertEqual(saved_document["meta"]["revision"], 2)

        asyncio.run(_assert_saved())

    def test_put_document_drops_transient_blob_asset_urls_from_canonical_state(self):
        document = _sample_document()
        document["assets"]["hero"] = {
            "assetId": "med_existing",
            "url": "https://cdn.test/existing-hero.jpg",
            "status": "ready",
        }
        asyncio.run(self._seed_brochure_document("quo_test", copy.deepcopy(document)))

        uploaded_document = copy.deepcopy(document)
        uploaded_document["assets"]["hero"] = {
            "assetId": "",
            "url": "blob:https://example.test/preview-123",
            "status": "uploading",
        }

        response = self.client.put(
            "/api/v2/quotations/quo_test/document",
            json={"document": uploaded_document, "baseRevision": 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["document"]["assets"]["hero"]["url"],
            "https://cdn.test/existing-hero.jpg",
        )
        self.assertEqual(
            response.json()["document"]["assets"]["hero"]["assetId"],
            "med_existing",
        )

    def test_publish_document_reads_canonical_postgres_document_and_creates_publication(self):
        document = _sample_document()
        document["trip"]["title"] = "Canonical Publish Title"
        asyncio.run(self._seed_brochure_document("quo_test", copy.deepcopy(document)))

        stale_ctx_document = _sample_document()
        stale_ctx_document["trip"]["title"] = "Stale Ctx Title"
        main.quotations["quo_test"] = {"ctx": {
            "template_name": main.BROCHURE_TEMPLATE_NAME,
            "baseline_lang": "en",
            "available_langs": ["en"],
            "translation_status": {"baseline_lang": "en", "available_langs": ["en"]},
            "quoteDocuments": {"en": stale_ctx_document},
            "quoteDocument": stale_ctx_document,
            "quoteDocumentLang": "en",
            "brand": {"id": "vietnam_safar"},
        }}

        response = self.client.post("/api/v2/quotations/quo_test/publish", json={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "published")
        self.assertEqual(
            main.quotations["quo_test"]["ctx"]["quoteDocuments"]["en"]["trip"]["title"],
            "Canonical Publish Title",
        )

        with open(os.path.join("published", "quo_test", "document.json"), "r", encoding="utf-8") as f:
            published_document = json.load(f)
        self.assertEqual(published_document["trip"]["title"], "Canonical Publish Title")

        async def _assert_publication():
            async with self.session_factory() as session:
                publication_repo = PublicationRepository(session)
                publications = await publication_repo.list_publications("quo_test", lang="en")
                self.assertEqual(len(publications), 1)
                self.assertEqual(publications[0].version, 1)
                self.assertEqual(
                    publications[0].html_r2_key,
                    "quotations/quo_test/publish/en/v1.html",
                )

        asyncio.run(_assert_publication())


if __name__ == "__main__":
    unittest.main()
