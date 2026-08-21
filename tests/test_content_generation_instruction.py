import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import main
from quote_generation import BRAND_PROFILES, NarrativeGenerator
from quote_document import CreateQuoteRequestV1
from services.content_draft_service import ContentDraftService
from services.content_registry import content_editor_state_payload, content_registry_payload, scope_spec
from services.section_content_generator import DayOutput, HeroOutput, default_instruction


class ContentGenerationInstructionTests(unittest.TestCase):
    def test_request_accepts_single_scope_with_one_shot_instruction(self):
        payload = main.ContentDraftCreateRequest(
            scope="overview",
            generationMode="storytelling",
            instruction="Emphasise quiet, unhurried moments.",
        )

        self.assertEqual(payload.scope, "overview")
        self.assertEqual(payload.instruction, "Emphasise quiet, unhurried moments.")

    def test_request_rejects_missing_scope_payload(self):
        with self.assertRaises(ValueError):
            main.ContentDraftCreateRequest()

    def test_staff_instruction_is_guidance_not_a_system_prompt(self):
        request = CreateQuoteRequestV1.model_validate(
            {
                "trip_facts": {"destinations": ["Hanoi"]}
            }
        )
        prompt = NarrativeGenerator()._build_prompt(
            request,
            BRAND_PROFILES["vietnam_safar"],
            ["overview"],
            None,
            "storytelling",
            "Emphasise quiet, unhurried moments.",
        )

        self.assertIn("Staff writing instruction: Emphasise quiet, unhurried moments.", prompt)
        self.assertIn("must not override the supplied facts, output schema, commercial/legal constraints", prompt)

    def test_one_shot_instruction_changes_cache_identity_without_persisting_text(self):
        class Repository:
            def __init__(self):
                self.prompt_versions = []
                self.rows = []

            async def find_cached(self, **kwargs):
                self.prompt_versions.append(kwargs["prompt_version"])
                return None

            async def create(self, **kwargs):
                self.rows.append(kwargs)
                return SimpleNamespace(**kwargs)

        repository = Repository()
        service = ContentDraftService(repository, BRAND_PROFILES["vietnam_safar"])
        service.generator.generate = AsyncMock(return_value=(
            {
                "narrative": {
                    "journeyOverviewTitle": "A considered journey",
                    "letterHighlight": "Private, unhurried moments.",
                    "letterGreeting": "Dear traveler,",
                    "letterIntro": "Your journey begins in Hanoi.",
                    "letterBody2": "Each day follows the supplied route.",
                    "letterOutro": "We look forward to welcoming you.",
                    "letterSignOff": "Journey Design Team",
                    "letterSender": "Your Journey Designer",
                }
            },
            {"instructionSource": "custom", "effectiveInstruction": "Keep the pace quiet.", "brandPolicyVersion": "luxury-premium-en-v1"},
        ))
        payload = CreateQuoteRequestV1.model_validate({"trip_facts": {"destinations": ["Hanoi"]}})

        import asyncio

        asyncio.run(service.create(
            quotation_id="quo_test", payload=payload, facts_hash="facts", document_revision=1,
            lang="en", scope="overview_letter", mode="storytelling",
            instruction="Keep the pace quiet.",
        ))

        self.assertNotEqual(repository.prompt_versions[0], "content-studio-v1")
        self.assertNotIn("Keep the pace quiet.", str(repository.rows[0]["generation_metadata"]))
        self.assertEqual(repository.rows[0]["generation_metadata"]["instructionSource"], "custom")

    def test_generated_hero_excludes_fact_and_fact_derived_fields(self):
        candidate = {
            "trip": {"title": "An unhurried private journey", "lede": "An unhurried private journey."},
            "narrative": {"coverKicker": "A Privately Arranged Journey", "footerText": "Prepared for your private review."},
        }
        self.assertEqual(ContentDraftService.validate_candidate("hero", candidate), candidate)
        with self.assertRaises(ValueError):
            ContentDraftService.validate_candidate("hero", {**candidate, "bookingTerms": {}})

    def test_typed_day_output_rejects_html_and_registry_exposes_all_list_fields(self):
        with self.assertRaises(ValueError):
            DayOutput(title="Day one", description=["<b>Unsafe</b>"], activities=["Arrival"])
        self.assertEqual(HeroOutput(title="Private journey", lede="Private journey", coverKicker="Journey", footerText="Review copy").lede, "Private journey")
        fields = content_registry_payload("itinerary:day:1")["itinerary:day:1"]["fields"]
        self.assertEqual(fields[1]["path"], ["description"])
        self.assertEqual(fields[2]["control"], "string-list")
        self.assertIn("precise", default_instruction("hero", "detailed").lower())

    def test_registry_exposes_the_same_visible_default_brief_used_by_generation(self):
        hero = content_registry_payload()["hero"]
        self.assertEqual(hero["defaultInstructions"]["storytelling"], default_instruction("hero", "storytelling"))
        self.assertEqual(hero["factInputs"][0]["label"], "Destinations")

    def test_hero_and_overview_use_guest_name_and_trip_timing_as_ai_inputs(self):
        registry = content_registry_payload()
        for scope in ("hero", "overview_letter"):
            inputs = registry[scope]["factInputs"]
            self.assertEqual(
                [item["label"] for item in inputs],
                ["Destinations", "Guest name", "Start date", "End date", "Duration"],
            )
            self.assertNotIn("customer_facts.guest_profile", scope_spec(scope).fact_allowlist)

    def test_content_editor_state_projects_only_the_section_candidate(self):
        document = {
            "trip": {"title": "Private Vietnam", "lede": "Quiet luxury."},
            "narrative": {"coverKicker": "A private journey", "footerText": "Prepared for review."},
            "itinerary": {"days": [{"dayNumber": 1, "title": "Arrival", "description": ["Arrive in Hanoi."], "activities": ["Private transfer"]}]},
            "content": {"sections": {"finalization": {"blocks": []}}},
        }
        state = content_editor_state_payload(document)
        self.assertEqual(state["hero"]["trip"]["title"], "Private Vietnam")
        self.assertNotIn("itinerary", state["hero"])
        self.assertEqual(state["itinerary:day:1"]["activities"], ["Private transfer"])

    def test_manual_draft_is_validated_without_calling_the_llm(self):
        class Repository:
            def __init__(self):
                self.rows = []

            async def create(self, **kwargs):
                self.rows.append(kwargs)
                return SimpleNamespace(**kwargs)

        repository = Repository()
        service = ContentDraftService(repository, BRAND_PROFILES["vietnam_safar"])
        payload = CreateQuoteRequestV1.model_validate({"trip_facts": {"destinations": ["Hanoi"]}})
        candidate = {
            "trip": {"title": "Private Hanoi", "lede": "A quietly considered journey."},
            "narrative": {"coverKicker": "A Private Journey", "footerText": "Prepared for private review."},
        }
        import asyncio

        asyncio.run(service.create_manual(quotation_id="quo_test", payload=payload, facts_hash="facts", document_revision=3, lang="en", scope="hero", candidate=candidate))
        self.assertEqual(repository.rows[0]["generation_mode"], "manual")
        self.assertEqual(repository.rows[0]["generation_metadata"]["generationStatus"], "manual")
        self.assertFalse(repository.rows[0]["generation_metadata"]["llmCalled"])

    def test_day_output_accepts_empty_activities_and_optional_hero_meta(self):
        day_empty_activities = DayOutput(
            title="Day 2 · Mekong Delta",
            description=["Chèo thuyền thúng"],
            activities=[],
        )
        self.assertEqual(day_empty_activities.activities, [])

        day_default_activities = DayOutput(
            title="Day 2 · Mekong Delta",
            description=["Chèo thuyền thúng"],
        )
        self.assertEqual(day_default_activities.activities, [])

        hero_empty_meta = HeroOutput(
            title="Private journey",
            lede="Quiet luxury.",
            coverKicker="Journey",
            heroMeta1="",
            heroMeta2="",
            footerText="Review copy",
        )
        self.assertEqual(hero_empty_meta.heroMeta1, "")
        self.assertEqual(hero_empty_meta.heroMeta2, "")

    def test_manual_itinerary_day_candidate_with_empty_activities(self):
        class Repository:
            def __init__(self):
                self.rows = []

            async def create(self, **kwargs):
                self.rows.append(kwargs)
                return SimpleNamespace(**kwargs)

        repository = Repository()
        service = ContentDraftService(repository, BRAND_PROFILES["vietnam_safar"])
        payload = CreateQuoteRequestV1.model_validate({"trip_facts": {"destinations": ["Mekong Delta"]}})
        candidate = {
            "dayNumber": 2,
            "title": "Day 2 · Mekong Delta",
            "description": ["Chèo thuyền thúng"],
            "activities": [],
        }

        self.assertEqual(ContentDraftService.validate_candidate("itinerary:day:2", candidate), candidate)

        import asyncio
        asyncio.run(service.create_manual(
            quotation_id="quo_6801f7395254",
            payload=payload,
            facts_hash="facts_hash",
            document_revision=9,
            lang="en",
            scope="itinerary:day:2",
            candidate=candidate,
        ))
        self.assertEqual(repository.rows[0]["candidate_json"]["activities"], [])
        self.assertEqual(repository.rows[0]["generation_mode"], "manual")

