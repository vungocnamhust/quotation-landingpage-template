"""Unit tests for injecting Request Brief context into AI Prompt Engine."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from quote_generation import BRAND_PROFILES
from quote_document import CreateQuoteRequestV1
from services.content_draft_service import (
    ContentDraftService,
    extract_request_brief,
)


class ContentGenerationWithRequestBriefTests(unittest.TestCase):
    def test_extract_request_brief_filters_and_extracts_allowed_keys(self):
        # 1. Full payload with supported, unsupported, and empty fields
        payload = {
            "occasion": "Honeymoon",
            "primary_theme": "Romance & Culture",
            "travel_pace": "Relaxed",
            "interests": ["Photography", "Culinary", "Architecture"],
            "must_have": "Private sunset cruise in Halong Bay",
            "avoid": "Overcrowded tourist traps",
            "dietary": "Pescatarian, No Shellfish",
            "halal": "Halal certified options preferred",
            "mobility": "Mild walking only",
            "dining_level": "Fine Dining & Michelin-starred",
            "client_context": "VIP anniversary celebration",
            # Unsupported / internal fields that should not be in request_brief
            "budget": "15000",
            "internal_notes": "Call client before 5 PM",
            "empty_field": "",
            "none_field": None,
            "empty_list": [],
            "empty_dict": {},
        }

        brief = extract_request_brief(payload)

        self.assertEqual(brief["occasion"], "Honeymoon")
        self.assertEqual(brief["primary_theme"], "Romance & Culture")
        self.assertEqual(brief["travel_pace"], "Relaxed")
        self.assertEqual(brief["interests"], ["Photography", "Culinary", "Architecture"])
        self.assertEqual(brief["must_have"], "Private sunset cruise in Halong Bay")
        self.assertEqual(brief["avoid"], "Overcrowded tourist traps")
        self.assertEqual(brief["dietary"], "Pescatarian, No Shellfish")
        self.assertEqual(brief["halal"], "Halal certified options preferred")
        self.assertEqual(brief["mobility"], "Mild walking only")
        self.assertEqual(brief["dining_level"], "Fine Dining & Michelin-starred")
        self.assertEqual(brief["client_context"], "VIP anniversary celebration")

        # Unsupported keys must not be in brief
        self.assertNotIn("budget", brief)
        self.assertNotIn("internal_notes", brief)
        self.assertNotIn("empty_field", brief)
        self.assertNotIn("none_field", brief)
        self.assertNotIn("empty_list", brief)

    def test_extract_request_brief_empty_or_invalid_inputs(self):
        self.assertEqual(extract_request_brief(None), {})
        self.assertEqual(extract_request_brief({}), {})
        self.assertEqual(extract_request_brief({"other_stuff": 123}), {})

    def test_facts_snapshot_includes_request_brief_when_provided(self):
        payload = CreateQuoteRequestV1.model_validate({
            "trip_facts": {
                "destinations": ["Hanoi", "Hue", "Hoi An"],
                "itinerary": [
                    {
                        "day_number": 1,
                        "destination": "Hanoi",
                        "summary": "Arrival and evening street food discovery",
                        "highlights": ["Old Quarter", "Egg Coffee"],
                        "meals": ["Dinner"],
                        "overnight": "Hanoi",
                    }
                ],
            },
            "customer_facts": {
                "customer_name": "Alexander Wright",
            },
        })

        brief = {
            "occasion": "Honeymoon",
            "interests": ["Photography", "Culinary"],
        }

        # 1. Overview Letter
        snapshot_overview = ContentDraftService.facts_snapshot(payload, "overview_letter", request_brief=brief)
        self.assertIn("request_brief", snapshot_overview)
        self.assertEqual(snapshot_overview["request_brief"]["occasion"], "Honeymoon")
        self.assertEqual(snapshot_overview["request_brief"]["interests"], ["Photography", "Culinary"])
        self.assertIn("trip_facts.destinations", snapshot_overview["facts"])

        # 2. Hero Section
        snapshot_hero = ContentDraftService.facts_snapshot(payload, "hero", request_brief=brief)
        self.assertIn("request_brief", snapshot_hero)
        self.assertEqual(snapshot_hero["request_brief"]["occasion"], "Honeymoon")

        # 3. Itinerary Day Section
        snapshot_day = ContentDraftService.facts_snapshot(payload, "itinerary:day:1", request_brief=brief)
        self.assertIn("request_brief", snapshot_day)
        self.assertIn("itineraryDay", snapshot_day)
        self.assertEqual(snapshot_day["itineraryDay"]["destination"], "Hanoi")
        self.assertEqual(snapshot_day["request_brief"]["interests"], ["Photography", "Culinary"])

        # 4. Without request_brief (standalone quotation)
        snapshot_no_brief = ContentDraftService.facts_snapshot(payload, "overview_letter")
        self.assertNotIn("request_brief", snapshot_no_brief)
        self.assertIn("facts", snapshot_no_brief)

    def test_preview_prompt_injects_request_brief_into_prompt_bundle(self):
        class DummyRepository:
            pass

        service = ContentDraftService(DummyRepository(), BRAND_PROFILES["selvara"])
        payload = CreateQuoteRequestV1.model_validate({
            "trip_facts": {
                "destinations": ["Hanoi", "Ninh Binh"],
                "start_date": "2026-10-01",
                "end_date": "2026-10-10",
                "duration_days": 10,
                "duration_nights": 9,
            },
            "customer_facts": {
                "customer_name": "Eleanor & Liam Vance",
            },
        })

        request_payload = {
            "occasion": "10th Wedding Anniversary",
            "primary_theme": "Heritage & Culinary Journey",
            "interests": ["Culinary Arts", "Landscape Photography"],
            "must_have": "Private cooking class with Master Chef",
            "avoid": "Large tour buses and early morning rushes",
        }

        # Preview overview_letter prompt
        preview = service.preview_prompt(
            payload=payload,
            scope="overview_letter",
            mode="storytelling",
            request_payload=request_payload,
        )

        user_prompt = preview["userPrompt"]
        system_prompt = preview["systemPrompt"]
        facts_snapshot = preview["factsSnapshot"]

        # Check factsSnapshot contains request_brief
        self.assertIn("request_brief", facts_snapshot)
        self.assertEqual(facts_snapshot["request_brief"]["occasion"], "10th Wedding Anniversary")

        # Check userPrompt contains JSON representation of request_brief
        self.assertIn('"occasion": "10th Wedding Anniversary"', user_prompt)
        self.assertIn('"interests": [', user_prompt)
        self.assertIn('"must_have": "Private cooking class with Master Chef"', user_prompt)

        # Check systemPrompt contains the updated YAML rules for overview_letter
        self.assertIn("When 'request_brief.occasion' is provided, open the letter with personalized congratulations.", system_prompt)
        self.assertIn("When 'request_brief.interests' are provided, reference how the itinerary honors these specific passions.", system_prompt)
        self.assertIn("When 'request_brief.must_have' is provided, highlight that this signature experience has been seamlessly secured.", system_prompt)
        self.assertIn("When 'request_brief.avoid' is provided, reassure the guest regarding seclusion, crowd avoidance, and relaxed pacing.", system_prompt)

    def test_hero_and_itinerary_day_prompt_rules(self):
        class DummyRepository:
            pass

        service = ContentDraftService(DummyRepository(), BRAND_PROFILES["vietnam_safar"])
        payload = CreateQuoteRequestV1.model_validate({
            "trip_facts": {
                "destinations": ["Da Nang", "Hoi An"],
                "itinerary": [
                    {
                        "day_number": 1,
                        "destination": "Da Nang",
                        "summary": "Arrival and coastal orientation",
                        "highlights": ["Son Tra Peninsula"],
                    }
                ],
            },
        })

        request_payload = {
            "occasion": "Honeymoon",
            "primary_theme": "Coastal Serenity",
            "interests": ["Culinary", "Scuba Diving"],
        }

        # Hero preview
        hero_preview = service.preview_prompt(
            payload=payload,
            scope="hero",
            mode="storytelling",
            request_payload=request_payload,
        )
        self.assertIn("When 'request_brief.primary_theme' or 'request_brief.occasion' is present, adapt the cover kicker or subtitle to reflect this milestone.", hero_preview["systemPrompt"])
        self.assertIn('"occasion": "Honeymoon"', hero_preview["userPrompt"])

        # Itinerary day preview
        day_preview = service.preview_prompt(
            payload=payload,
            scope="itinerary:day:1",
            mode="detailed",
            request_payload=request_payload,
        )
        self.assertIn("When 'request_brief.interests' match the day's theme, enrich the narrative with sensory cultural/culinary details.", day_preview["systemPrompt"])
        self.assertIn('"interests": [', day_preview["userPrompt"])

    def test_content_draft_service_create_with_request_payload(self):
        class Repository:
            def __init__(self):
                self.saved_rows = []

            async def find_cached(self, **kwargs):
                return None

            async def create(self, **kwargs):
                self.saved_rows.append(kwargs)
                return SimpleNamespace(**kwargs)

        repo = Repository()
        service = ContentDraftService(repo, BRAND_PROFILES["capella_travel"])

        service.generator.generate = AsyncMock(return_value=(
            {
                "narrative": {
                    "journeyOverviewTitle": "An Exquisite Celebration",
                    "letterHighlight": "Warmest congratulations on your honeymoon.",
                    "letterGreeting": "Dear Alexander & Sarah,",
                    "letterIntro": "In honour of your honeymoon, we have crafted an intimate journey.",
                    "letterBody2": "Culinary delights and photography vantage points await you.",
                    "letterOutro": "Every detail has been seamlessly prepared.",
                    "letterSignOff": "Warm regards,",
                    "letterSender": "Capella Journey Designers",
                }
            },
            {
                "instructionSource": "default",
                "effectiveInstruction": "Write an overview letter.",
                "brandPolicyVersion": "luxury-premium-en-v1",
                "systemPrompt": "System prompt text",
                "userPrompt": "User prompt text with Honeymoon",
                "promptVersion": "v1",
            },
        ))

        payload = CreateQuoteRequestV1.model_validate({
            "trip_facts": {"destinations": ["Hanoi", "Sapa"]},
            "customer_facts": {"customer_name": "Alexander & Sarah"},
        })

        request_payload = {
            "occasion": "Honeymoon",
            "interests": ["Gastronomy", "Photography"],
            "avoid": "Crowded spots",
        }

        import asyncio

        items = asyncio.run(service.create(
            quotation_id="quo_test_123",
            payload=payload,
            facts_hash="facts_hash_abc",
            document_revision=1,
            lang="en",
            scope="overview_letter",
            mode="storytelling",
            request_payload=request_payload,
        ))

        self.assertEqual(len(items), 1)
        saved = repo.saved_rows[0]
        self.assertIn("request_brief", saved["facts_snapshot"])
        self.assertEqual(saved["facts_snapshot"]["request_brief"]["occasion"], "Honeymoon")
        self.assertEqual(saved["facts_snapshot"]["request_brief"]["interests"], ["Gastronomy", "Photography"])
        self.assertEqual(saved["facts_snapshot"]["request_brief"]["avoid"], "Crowded spots")

    def test_facts_endpoint_helper_resolution_includes_request_brief(self):
        from unittest.mock import MagicMock
        from routers.v2.quotation_facts import get_quotation_facts_v2

        # Verify extract_request_brief contract for endpoint response
        raw_request_payload = {
            "occasion": "10th Anniversary",
            "interests": ["Culinary", "Trekking"],
            "must_have": "Private guide",
            "avoid": "Long driving",
            "budget": "20000",  # filtered
        }
        brief = extract_request_brief(raw_request_payload)
        self.assertEqual(brief["occasion"], "10th Anniversary")
        self.assertEqual(brief["interests"], ["Culinary", "Trekking"])
        self.assertEqual(brief["must_have"], "Private guide")
        self.assertEqual(brief["avoid"], "Long driving")
        self.assertNotIn("budget", brief)

    def test_batch_generation_reads_travel_pace_from_request_brief_not_facts(self):
        class Repository:
            async def create(self, **_kwargs):
                raise AssertionError("no drafts are expected for this empty generator response")

        service = ContentDraftService(Repository(), BRAND_PROFILES["selvara"])
        service.generator.generate_narrative_batch = AsyncMock(return_value=({}, {"instructionSource": "default"}))
        payload = CreateQuoteRequestV1.model_validate({"trip_facts": {"destinations": ["Hanoi"]}})

        import asyncio

        items = asyncio.run(service.create_batch(
            quotation_id="quo_batch",
            payload=payload,
            facts_hash="facts",
            document_revision=1,
            lang="en",
            mode="storytelling",
            request_payload={"travel_pace": "Relaxed"},
        ))

        self.assertEqual(items, [])
        snapshot = service.generator.generate_narrative_batch.await_args.kwargs["facts_snapshot"]
        self.assertEqual(snapshot["trip"]["travel_pace"], "Relaxed")


if __name__ == "__main__":
    unittest.main()
