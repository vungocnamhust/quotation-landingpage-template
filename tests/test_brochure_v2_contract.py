import asyncio
import copy
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import scripts.clone_legacy_quote as create_quotation_api_v2
import main
from db.base import Base
from db.models.brand import Brand
from db.models.publication import PublicationTarget
from quote_document import AssetSelectionResult, validate_quote_document_sections
from quote_document_adapter import apply_quote_document_to_lang_ctx, normalize_quote_document
from quote_generation import (
    BRAND_PROFILES,
    LIVE_V1_PARITY_SPEC,
    NarrativeGenerationResult,
    NarrativeGenerator,
    apply_narrative_result_to_document,
)
from repositories import PublicationRepository, PublicationTargetRepository, QuotationDocumentRepository, QuotationRepository
from repositories.travel_designer_repository import TravelDesignerRepository
from repositories.accommodation_repository import AccommodationRepository


def _sample_document() -> dict:
    return normalize_quote_document(
        {
            "meta": {
                "quotationId": "quo_test",
                "lang": "en",
                "brandId": "vietnam_safar",
                "opportunityId": "OPP-1",
                "contentSchemaVersion": 1,
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
                "title": "Your route",
                "description": "A considered route through Vietnam.",
                "staySegments": [
                    {"id": "stay-1", "displayName": "Hanoi"},
                ]
            },
            "itinerary": {
                "title": "Day by day",
                "description": "A considered day-by-day journey.",
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
            "designer": {"name": "Vietnam Safar"},
            "content": {
                "sections": {
                    "inclusions_exclusions": {"blocks": [{"type": "twoColumnList", "leftTitle": "Inclusions", "leftItems": ["Private transfers"], "rightTitle": "Exclusions", "rightItems": ["International flights"]}]},
                    "booking_terms": {"blocks": [{"type": "termList", "items": [{"label": "Deposit", "body": "30% deposit"}, {"label": "Balance", "body": "Balance before travel"}, {"label": "Cancellation", "body": "Supplier terms apply"}, {"label": "Confirmation", "body": "Subject to availability"}]}]},
                    "finalization": {"blocks": [{"type": "checklistGroups", "groups": [{"title": "Final Details Required", "items": ["Passport copy"]}, {"title": "After Confirmation", "items": ["Final vouchers issued"]}]}]},
                },
            },
        },
        "quo_test",
        "en",
    )


class BrandSectionBackgroundContractTests(unittest.TestCase):
    def test_button_radius_cannot_be_a_pill(self):
        with self.assertRaisesRegex(ValueError, "component radius"):
            main.BrandRenderProfileContract(
                palette={
                    "canvas": "#f9f6f0", "paper": "#fffaf1", "ink": "#1d1d1b", "mutedInk": "#67635b",
                    "accent": "#cba135", "accentAlt": "#333333", "contrast": "#333333", "onContrast": "#ffffff", "focus": "#8a6500",
                },
                radii={"card": "0.5rem", "button": "999px", "frame": "0.625rem", "pill": "999px"},
            )

    def test_explicit_investment_surface_requires_readable_text(self):
        palette = {
            "canvas": "#f9f6f0",
            "paper": "#fffaf1",
            "ink": "#1d1d1b",
            "mutedInk": "#67635b",
            "accent": "#cba135",
            "accentAlt": "#333333",
            "contrast": "#333333",
            "onContrast": "#ffffff",
            "focus": "#8a6500",
            "storyContrast": "#17412e",
            "investmentSurface": "#17412e",
            "investmentText": "#ffffff",
        }
        profile = main.BrandRenderProfileContract(
            palette=palette,
            radii={"card": "1rem", "button": "1rem", "frame": "1rem", "pill": "999px"},
        )

        self.assertEqual(profile.palette["investmentSurface"], "#17412e")

    def test_partial_section_background_palette_is_rejected(self):
        palette = {
            "canvas": "#f9f6f0",
            "paper": "#fffaf1",
            "ink": "#1d1d1b",
            "mutedInk": "#67635b",
            "accent": "#cba135",
            "accentAlt": "#333333",
            "contrast": "#333333",
            "onContrast": "#ffffff",
            "focus": "#8a6500",
            "storyContrast": "#17412e",
        }

        with self.assertRaises(ValueError):
            main.BrandRenderProfileContract(
                palette=palette,
                radii={"card": "1rem", "button": "1rem", "frame": "1rem", "pill": "999px"},
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
        carousel_urls = main._dedupe_image_refs([item["url"] for item in normalized["itinerary"]["days"][0]["images"]["carousel"]])

        self.assertEqual(
            carousel_urls,
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

    def test_normalize_quote_document_preserves_itinerary_rich_text_fields(self):
        document = _sample_document()
        document["itinerary"]["days"][0].update({
            "title": 'Arrival in <strong>Hanoi</strong>',
            "description": ['Private <span style="font-size:18px;font-weight:700">arrival</span> and transfer.'],
            "activities": ['<strong>Highlights:</strong> Fast-track arrival · Private transfer'],
            "notes": ['<span style="font-size:16px">Sense of Pace: Relaxed</span>'],
        })

        normalized = normalize_quote_document(document, "quo_test", "en")
        day = normalized["itinerary"]["days"][0]

        self.assertEqual(day["title"], 'Arrival in <strong>Hanoi</strong>')
        self.assertEqual(
            day["description"],
            ['Private <span style="font-size:18px;font-weight:700">arrival</span> and transfer.'],
        )
        self.assertEqual(
            day["activities"],
            ['<strong>Highlights:</strong> Fast-track arrival · Private transfer'],
        )
        self.assertEqual(
            day["notes"],
            ['<span style="font-size:16px">Sense of Pace: Relaxed</span>'],
        )

    def test_apply_quote_document_to_lang_ctx_keeps_itinerary_rich_text_for_rendering(self):
        document = _sample_document()
        document["itinerary"]["days"][0].update({
            "title": 'Arrival in <strong>Hanoi</strong>',
            "description": ['Private <span style="font-size:18px">arrival</span> and transfer.'],
            "activities": ['<span style="font-size:15px"><strong>Fast-track arrival</strong> · Private transfer</span>'],
            "notes": ['<span style="font-size:16px">Sense of Pace: Relaxed</span>'],
        })

        lang_ctx: dict = {}
        apply_quote_document_to_lang_ctx(lang_ctx, document)
        day = lang_ctx["itinerary_days"][0]

        self.assertEqual(day["title"], 'Arrival in <strong>Hanoi</strong>')
        self.assertEqual(
            day["description"],
            ['Private <span style="font-size:18px">arrival</span> and transfer.'],
        )
        self.assertEqual(
            day["activities"],
            ['<span style="font-size:15px"><strong>Fast-track arrival</strong> · Private transfer</span>'],
        )
        self.assertEqual(
            day["notes"],
            ['<span style="font-size:16px">Sense of Pace: Relaxed</span>'],
        )

    def test_parse_edited_fields_keeps_itinerary_html_markup(self):
        html = """
        <h4 data-editable="day_title_1">Arrival in <strong>Hanoi</strong></h4>
        <p data-editable="day_desc_1_0">Private <span style="font-size:18px">arrival</span> and transfer.</p>
        <span data-editable="day_highlights_1"><strong>Fast-track arrival</strong> · Private transfer</span>
        <li data-editable="day_note_1_0"><span style="font-size:16px">Sense of Pace: Relaxed</span></li>
        """

        edited_fields = main.parse_edited_fields(html)

        self.assertEqual(edited_fields["day_title_1"], "Arrival in <strong>Hanoi</strong>")
        self.assertEqual(
            edited_fields["day_desc_1_0"],
            'Private <span style="font-size:18px">arrival</span> and transfer.',
        )
        self.assertEqual(
            edited_fields["day_highlights_1"],
            "<strong>Fast-track arrival</strong> · Private transfer",
        )
        self.assertEqual(
            edited_fields["day_note_1_0"],
            '<span style="font-size:16px">Sense of Pace: Relaxed</span>',
        )

    def test_parse_edited_fields_recovers_word_pasted_day_description_after_empty_editable(self):
        html = """
        <div class="day-copy">
          <p data-editable="day_desc_1_0" spellcheck="false"></p>
          <p class="MsoNormal"><span style="font-size:12.0pt;line-height:115%;font-family:&quot;Garamond&quot;,serif;mso-bidi-font-family:&quot;Quire Sans&quot;">Upon arrival at <b>Noi Bai International Airport</b>, you are welcomed by a dedicated concierge representative.</span></p>
          <p style="font-size:13px;color: var(--text-muted);margin-top:8px" data-deletable="day_activities_1">
            <strong data-editable="day_label_highlights_1">Highlights:</strong>
            <span data-editable="day_highlights_1">Private airport pickup</span>
          </p>
        </div>
        """

        edited_fields = main.parse_edited_fields(html)

        self.assertIn("Upon arrival at <b>Noi Bai International Airport</b>", edited_fields["day_desc_1_0"])
        self.assertNotIn("MsoNormal", edited_fields["day_desc_1_0"])
        self.assertNotIn("font-size:12.0pt", edited_fields["day_desc_1_0"])
        self.assertEqual(edited_fields["day_highlights_1"], "Private airport pickup")

    def test_filter_and_override_ctx_by_html_recovers_word_pasted_day_description(self):
        lang_ctx = {
            "itinerary": [
                {
                    "dayNumber": 1,
                    "title": "Day 1 — Hanoi",
                    "description": ["Original description"],
                    "notes": ["Sense of Pace: Relaxed"],
                    "activities": ["Private airport pickup"],
                }
            ]
        }
        html = """
        <article class="day">
          <h4 data-editable="day_title_1">Day 1 — Hanoi</h4>
          <div class="day-copy">
            <p data-editable="day_desc_1_0" spellcheck="false"></p>
            <p class="MsoNormal"><span style="font-size:12.0pt;line-height:115%;font-family:&quot;Garamond&quot;,serif;mso-bidi-font-family:&quot;Quire Sans&quot;">Recovered <b>Word paste</b> description.</span></p>
          </div>
        </article>
        """

        main.filter_and_override_ctx_by_html(lang_ctx, html, override_text=True)

        self.assertEqual(lang_ctx["itinerary"][0]["description"], ["Recovered Word paste description."])
        self.assertIn("<b>Word paste</b>", lang_ctx["itinerary"][0]["description_html"][0])
        self.assertNotIn("font-size:12.0pt", lang_ctx["itinerary"][0]["description_html"][0])

    def test_brand_switch_ignores_javascript_map_placeholder_keys(self):
        lang_ctx = {
            "itinerary": [],
            "stay_segments": [
                {"city": "Ho Chi Minh City", "displayName": "Ho Chi Minh City", "order": 1, "transportFromPrevious": ""},
                {"city": "Siem Reap", "displayName": "Siem Reap", "order": 2, "transportFromPrevious": "Ho Chi Minh City → Siem Reap"},
            ],
        }

        # The prototype emits these literal strings in JavaScript. They are
        # not persisted map fields and must never be interpreted as deleted
        # numeric segment bindings during a brand-switch render.
        main.filter_and_override_ctx(
            lang_ctx,
            {"map_segment_desc_${idx}", "map_segment_title_${idx}"},
            {},
        )

        self.assertEqual([segment["city"] for segment in lang_ctx["stay_segments"]], ["Ho Chi Minh City", "Siem Reap"])

    def test_map_duration_edit_updates_structured_nights_for_pdf_and_refresh(self):
        segment = {"nights": 1, "nightsLabel": "1 NIGHT"}

        main._apply_segment_duration_override(segment, "DAYS 14-15 • 2 NIGHT")

        self.assertEqual(segment["mapSegmentDuration"], "DAYS 14-15 • 2 NIGHT")
        self.assertEqual(segment["nightsLabel"], "2 NIGHT")
        self.assertEqual(segment["nights"], 2)

    def test_pdf_route_overview_has_server_rendered_stay_segments(self):
        with open("templates/prototype_itinerary_imagery_pdf.html", encoding="utf-8") as template_file:
            template = template_file.read()

        self.assertIn("{% for segment in stay_segments %}", template)
        self.assertIn("timelineContainer.innerHTML = ''", template)

    def test_pdf_map_uses_stay_segment_coordinates_for_every_journey_leg(self):
        with open("templates/prototype_itinerary_imagery_pdf.html", encoding="utf-8") as template_file:
            template = template_file.read()

        self.assertIn("const journeyLinePoints = mapSegments.map(segment => segment.coords);", template)
        self.assertIn("const linePoints = journeyLinePoints.length > 1 ? journeyLinePoints : coordPoints;", template)

    def test_pdf_route_footer_resolves_requested_brand_at_render_time(self):
        with open("templates/prototype_itinerary_imagery_pdf.html", encoding="utf-8") as template_file:
            template = template_file.read()

        self.assertIn("“{{ (brand.name if brand else '') or 'Vietnam Safar' }} · {{ quotation_number }}”", template)

    def test_brand_specific_pdf_bypasses_static_pdf_cache(self):
        request = main.Request({
            "type": "http",
            "method": "GET",
            "path": "/quotations/quo_test/pdf",
            "query_string": b"lang=en&brand=capella_travel",
            "headers": [],
        })
        ctx_data = {"baseline_lang": "en", "template_name": "custom.html"}
        cached_pdf = AsyncMock(return_value="stale static PDF")
        dynamic_pdf = AsyncMock(return_value=("brand-resolved PDF", "en"))

        with (
            patch.object(main, "_load_ctx_data", return_value=ctx_data),
            patch.object(main, "_get_latest_published_pdf_html", cached_pdf),
            patch.object(main, "_render_quotation_doc_from_ctx", dynamic_pdf),
        ):
            response = asyncio.run(main.get_quotation_pdf("quo_test", request))

        self.assertEqual(response.body, b"brand-resolved PDF")
        cached_pdf.assert_not_awaited()
        dynamic_pdf.assert_awaited_once()
    def test_parse_edited_fields_strips_word_typography_but_keeps_semantic_markup(self):
        html = """
        <div class="day-copy">
          <p data-editable="day_desc_10_0" spellcheck="false"></p>
          <p class="MsoNormal"><span style="font-family:&quot;Garamond&quot;,serif;mso-bidi-font-family:&quot;Quire Sans&quot;">Depart from <b>Da Nang City</b> toward <b>Hue</b> for a scenic coastal route.</span></p>
          <span style="font-size:12.0pt;line-height:115%;font-family:&quot;Garamond&quot;,serif;mso-bidi-font-family:&quot;Quire Sans&quot;">In the afternoon, explore the <b>Hue Imperial City</b>.</span><p></p>
        </div>
        """

        edited_fields = main.parse_edited_fields(html)

        self.assertEqual(
            edited_fields["day_desc_10_0"],
            "Depart from <b>Da Nang City</b> toward <b>Hue</b> for a scenic coastal route.<br><br>In the afternoon, explore the <b>Hue Imperial City</b>.",
        )

    def test_parse_edited_fields_strips_word_typography_from_highlights_and_notes(self):
        html = """
        <div class="day-copy">
          <span data-editable="day_highlights_10"><span style="font-size:12.0pt;line-height:115%;font-family:&quot;Garamond&quot;,serif;mso-bidi-font-family:&quot;Quire Sans&quot;">Hai Van Pass, <b>Lang Co Beach</b></span></span>
          <li data-editable="day_note_10_0"><span style="font-size:12.0pt;line-height:115%;font-family:&quot;Garamond&quot;,serif;mso-bidi-font-family:&quot;Quire Sans&quot;">Starts at <b>08:00am</b></span></li>
        </div>
        """

        edited_fields = main.parse_edited_fields(html)

        self.assertEqual(
            edited_fields["day_highlights_10"],
            "Hai Van Pass, <b>Lang Co Beach</b>",
        )
        self.assertEqual(
            edited_fields["day_note_10_0"],
            "Starts at <b>08:00am</b>",
        )

    def test_render_rich_text_filter_strips_word_typography_at_render_time(self):
        rendered = main.render_rich_text_filter(
            '<span style="font-size:12.0pt;line-height:115%;font-family:&quot;Garamond&quot;,serif;mso-bidi-font-family:&quot;Quire Sans&quot;">Hai Van Pass, <b>Lang Co Beach</b></span>',
            "en",
        )

        self.assertEqual(str(rendered), "Hai Van Pass, <b>Lang Co Beach</b>")




class NarrativeGeneratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_generated_copy_changes_with_brand_profile(self):
        request = main.CreateQuoteRequestV1.model_validate(
            {
                "brand_id": "capella_travel",
                "trip_facts": {
                    "destinations": ["Hanoi"],
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
                    "destinations": ["Hanoi"],
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

    async def test_generation_keeps_editorial_copy_content_owned(self):
        request = main.CreateQuoteRequestV1.model_validate(
            {
                "brand_id": "capella_travel",
                "trip_facts": {
                    "destinations": ["Hanoi"],
                    "itinerary": [
                        {
                            "day_number": 1,
                            "destination": "Hanoi",
                            "summary": "Arrival in Hanoi",
                            "highlights": ["Private airport welcome"],
                            "notes": ["Sense of Pace: Relaxed"],
                        }
                    ],
                },
                "pricing_facts": {
                    "options": [
                        {
                            "id": "price-1",
                            "label": "Package 14D13N",
                            "currency": "USD",
                            "per_traveler_amount_minor": 445_000,
                            "group_total_amount_minor": 4_895_000,
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
                "designer_facts": {
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
                    tripTitle="Tina's Vietnam Birthday Escape",
                    lede="A refined private journey.",
                    journeyOverviewTitle="A Journey Shaped Around Your Group",
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

        self.assertEqual(document.trip.title, "Tina's Vietnam Birthday Escape")
        self.assertEqual(document.narrative.journeyOverviewTitle, "A Journey Shaped Around Your Group")
        self.assertEqual(document.narrative.letterGreeting, "Generated greeting")
        self.assertEqual(document.narrative.letterIntro, "Generated intro")
        self.assertEqual(document.narrative.letterSignOff, "Generated sign off")
        self.assertEqual(document.narrative.letterSender, "Generated sender")
        self.assertEqual(document.pricing.title, LIVE_V1_PARITY_SPEC.pricing_heading)
        self.assertEqual(document.pricing.options[0].label, "Package 14D13N")
        self.assertEqual(document.pricing.options[0].groupTotalAmountMinor, 4_895_000)
        self.assertEqual(document.designer.kicker, "Your Journey Designer")
        self.assertEqual(document.designer.ctaBody, "I will remain your personal point of contact as we refine your journey.")
        self.assertEqual(document.designer.subtitle, "(Trung Hieu Pham)")
        finalization = document.content.sections["finalization"].blocks[0]
        self.assertEqual(finalization.groups[1].items[0], "24/7 dedicated local concierge support.")


class CreateQuotationApiV2PayloadTests(unittest.TestCase):
    def test_build_payload_prefers_live_editable_texts(self):
        ctx = {
            "quotation_number": "VN-2027-LUX",
            "tour_title": "Ctx Title",
            "hero_meta_1": "CTX META 1",
            "travel_dates": "CTX DATES",
            "seller_name": "Ctx Seller",
            "itinerary_days": [{"dayNumber": 1, "segment_city": "Hanoi", "title": "Day 1 — Hanoi", "description": ["Arrival"]}],
            "price_options": [],
            "hotels": [],
        }
        payload = create_quotation_api_v2.build_payload(ctx, ctx, "vietnam_luxury_brosure.html", target_brand="capella_travel")
        self.assertEqual(payload["template_name"], "vietnam_luxury_brosure.html")
        self.assertEqual(payload["seller"]["companyName"], "Capella Travel")


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
        cls.env_patch = patch.dict(os.environ, {"DMC_GATEWAY_ENABLED": "true"})
        cls.env_patch.start()
        cls.client = TestClient(main.app, headers={"X-DMC-Email": "editor@test.com"})

    @classmethod
    def tearDownClass(cls):
        cls.env_patch.stop()
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
        sample_profile = {
            "palette": {
                "canvas": "#ffffff",
                "paper": "#f8fafc",
                "ink": "#0f172a",
                "mutedInk": "#64748b",
                "accent": "#0284c7",
                "accentAlt": "#0369a1",
                "contrast": "#0f172a",
                "onContrast": "#ffffff",
                "focus": "#0284c7",
            },
            "radii": {
                "card": "12px",
                "button": "8px",
                "frame": "16px",
                "pill": "9999px",
            },
            "themeId": "brochure",
            "layoutVersion": 1,
        }
        async with cls.session_factory() as session:
            await main._seed_destination_catalog(session)
            session.add(Brand(id="vietnam_safar", display_name="Vietnam Safar", hostname="safar.test", status="active", render_profile=sample_profile))
            session.add(Brand(id="vietnam_safari", display_name="Vietnam Safari", hostname="safari.test", status="active", render_profile=sample_profile))
            await TravelDesignerRepository(session).create_profile(
                profile_id="td_test",
                email="editor@test.com",
                name="Test Editor",
            )
            await AccommodationRepository(session).create_profile(
                id="acc_test",
                destination_id="dst_ha-noi",
                storage_slug="test-hotel",
                asset_prefix="accommodations/vietnam/north/hanoi/test-hotel",
                name="Test Hotel",
                room_type="Deluxe",
                intro="A test stay.",
                phone="",
                display_city="Hanoi",
                display_date=None,
                hotel_asset=None,
                room_asset=None,
            )
            await session.commit()

    @classmethod
    async def _seed_brochure_document(cls, quotation_id: str, document: dict):
        async with cls.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            document_repo = QuotationDocumentRepository(session)
            quotation = await quotation_repo.create_quotation(
                quotation_id=quotation_id,
                brand_id="vietnam_safar",
                template_name=main.V2_RENDERER_NAME,
                baseline_lang="en",
                opportunity_id="OPP-1",
                current_version=1,
                designer_profile_id="td_test",
            )
            await quotation_repo.create_quotation_request(
                quotation_id=quotation_id,
                request_json={
                    "brand_id": "vietnam_safar",
                    "opportunity_id": "OPP-1",
                    "lang": "en",
                    "trip_facts": {
                        "itinerary": [{"day_number": 1, "destination": "Hanoi", "summary": "Arrival"}],
                    },
                },
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

    def test_accommodation_catalog_crud_is_available_to_an_editor(self):
        payload = {
            "destinationId": "dst_ha-noi",
            "name": "Intake Test Hotel",
            "room_type": "Suite",
            "check_in": "2026-11-01",
            "check_out": "2026-11-02",
            "intro": "A private test stay.",
            "phone": "+84 1",
            "display_city": "Hanoi",
            "display_date": None,
            "hotel_asset": None,
            "room_asset": None,
        }
        created = self.client.post("/api/v2/accommodations", json=payload)
        self.assertEqual(created.status_code, 201)
        item = created.json()
        self.assertEqual(item["destination"], "Hanoi")
        self.assertEqual(item["asset_prefix"], "accommodations/vietnam/north/hanoi/ha-noi/intake-test-hotel")
        updated_payload = {**payload, "name": "Renamed Intake Hotel"}
        updated = self.client.put(f"/api/v2/accommodations/{item['id']}", json=updated_payload)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Renamed Intake Hotel")
        self.assertEqual(updated.json()["asset_prefix"], item["asset_prefix"])
        exterior_location = self.client.post("/api/v2/media-library/resolve-location", json={
            "kind": "accommodation",
            "accommodationId": item["id"],
            "accommodationAssetCategory": "exteriors",
        })
        self.assertEqual(exterior_location.status_code, 200)
        self.assertEqual(exterior_location.json()["leafPrefix"], f"{item['asset_prefix']}/exteriors")
        listed = self.client.get("/api/v2/accommodations?query=Intake")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([row["id"] for row in listed.json()["items"]], [item["id"]])
        status = self.client.patch(f"/api/v2/accommodations/{item['id']}/status", json={"isActive": False})
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json()["is_active"])

    def test_existing_accommodation_prefix_is_reused_for_uploads_and_edits(self):
        # This fixture intentionally predates the taxonomy-derived root. A
        # profile with existing R2 media must remain editable instead of being
        # rejected because a newer algorithm would derive another prefix.
        payload = {
            "destinationId": "dst_ha-noi",
            "name": "Test Hotel",
            "room_type": "Updated Deluxe",
            "check_in": "2026-10-01",
            "check_out": "2026-10-02",
            "intro": "Updated stay.",
            "phone": "+84 2",
            "display_city": "Hanoi",
            "display_date": None,
            "hotel_asset": None,
            "room_asset": None,
        }
        updated = self.client.put("/api/v2/accommodations/acc_test", json=payload)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["asset_prefix"], "accommodations/vietnam/north/hanoi/test-hotel")
        interior_location = self.client.post("/api/v2/media-library/resolve-location", json={
            "kind": "accommodation",
            "accommodationId": "acc_test",
            "accommodationAssetCategory": "interiors",
        })
        self.assertEqual(interior_location.status_code, 200)
        self.assertEqual(interior_location.json()["leafPrefix"], "accommodations/vietnam/north/hanoi/test-hotel/interiors")

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
                        "presentation_options": {"template_id": "quote-generator", "travel_designer_id": "td_test"},
                        "trip_facts": {
                            "start_date": "2026-10-01",
                            "end_date": "2026-10-01",
                            "itinerary": [{"day_number": 1, "destination": "Hanoi", "overnight": "Hanoi", "summary": "Arrival", "meals": ["Dinner"], "notes": ["Private arrival"]}],
                        },
                        "customer_facts": {"customer_name": "Test Guest", "nationality": "British", "adults": 2},
                        "service_facts": {"hotels": [{"accommodation_id": "acc_test", "destination": "Hanoi", "name": "Test Hotel", "room_type": "Deluxe", "check_in": "2026-10-01", "check_out": "2026-10-01"}]},
                    },
                )
        self.assertEqual(response.status_code, 200)
        created_id = response.json()["quotationId"]
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

        with patch.object(main, "_inspect_asset_readiness", return_value={"ready": True, "missing": [], "invalid": [], "checkedAt": ""}):
            response = self.client.post("/api/v2/quotations/quo_test/publish", json={"baseRevision": 1})

        self.assertIn(response.status_code, (200, 202))
        self.assertIn(response.json()["status"], ("published", "queued"))
        self.assertTrue(response.json()["fallback_url"].startswith("https://quotes.capellatravel.com/p/"))
        target_id = response.json()["targetId"]
        release_id = response.json()["releaseId"]

        async def _assert_publication():
            async with self.session_factory() as session:
                target_repo = PublicationTargetRepository(session)
                target = await session.get(PublicationTarget, target_id)
                self.assertIsNotNone(target)
                self.assertEqual(target.brand_id, "vietnam_safar")
                self.assertTrue(target.fallback_slug)
                releases = await target_repo.list_releases(target.id)
                self.assertEqual(len(releases), 1)
                self.assertEqual(releases[0].id, release_id)
                self.assertEqual(releases[0].document_revision, 1)

        asyncio.run(_assert_publication())

    def test_public_fallback_resolves_only_active_published_target(self):
        document = _sample_document()
        asyncio.run(self._seed_brochure_document("quo_test", copy.deepcopy(document)))
        with patch.object(main, "_inspect_asset_readiness", return_value={"ready": True, "missing": [], "invalid": [], "checkedAt": ""}):
            published = self.client.post("/api/v2/quotations/quo_test/publish", json={"baseRevision": 1}).json()

        async def _activate_and_get_slug():
            async with self.session_factory() as session:
                repository = PublicationTargetRepository(session)
                target = await session.get(PublicationTarget, published["targetId"])
                release = await repository.get_release(published["releaseId"])
                self.assertIsNotNone(target)
                self.assertIsNotNone(release)
                release.pdf_r2_key = "quotations/quo_test/react/test.pdf"
                await repository.activate_release(target=target, release=release)
                await session.commit()
                return target.fallback_slug

        fallback_slug = asyncio.run(_activate_and_get_slug())
        with patch.dict(os.environ, {"QUOTE_SERVICE_TOKEN": "test-service-token"}):
            resolved = self.client.get(
                f"/api/internal/v2/public-quotations/fallback/{fallback_slug}",
                headers={"X-Quote-Service-Token": "test-service-token"},
            )
            missing = self.client.get(
                "/api/internal/v2/public-quotations/fallback/not-a-publication",
                headers={"X-Quote-Service-Token": "test-service-token"},
            )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["locale"], "en")
        self.assertEqual(resolved.json()["document"]["trip"]["title"], "Vietnam Private Journey")
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
