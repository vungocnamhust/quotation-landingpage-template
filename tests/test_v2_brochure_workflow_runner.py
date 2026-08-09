import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.test_v2_brochure_workflow import (
    COVERAGE_MANIFEST,
    SSR_EDITABLE_FIELD_EXPECTATIONS,
    WORKFLOW_SCENARIOS,
    CoverageEntry,
    CurlApi,
    WorkflowFailure,
    assert_ssr_editable_contract,
    assert_content_candidate,
    apply_design_sentinels,
    get_path,
    make_facts,
    select_scenarios,
    parse_args,
    validate_coverage_manifest,
    validate_test_pyramid_contracts,
)
from quote_document import CreateQuoteRequestV1
from services.quotation_intake_policy import quotation_intake_missing_inputs


class WorkflowRunnerTests(unittest.TestCase):
    def test_workflow_fixture_satisfies_the_strict_intake_shape_after_catalog_resolution(self):
        facts = make_facts("vietnam_safar", "en", "workflow-test")
        facts["presentation_options"]["travel_designer_id"] = "td_test"
        for index, hotel in enumerate(facts["service_facts"]["hotels"]):
            hotel["accommodation_id"] = f"acc_{index}"
        payload = CreateQuoteRequestV1.model_validate(facts)
        self.assertEqual(quotation_intake_missing_inputs(payload), [])

    def test_compose_api_base_falls_back_to_shared_e2e_api_contract(self):
        with patch.dict(os.environ, {"E2E_API_BASE_URL": "http://app:8111"}, clear=True), patch.object(sys, "argv", ["runner"]):
            self.assertEqual(parse_args().api_base, "http://app:8111")

    def test_manifest_covers_every_renderable_document_group(self):
        validate_coverage_manifest()
        self.assertGreater(len(COVERAGE_MANIFEST), 10)

    def test_manifest_rejects_missing_or_duplicate_owner_paths(self):
        with self.assertRaisesRegex(WorkflowFailure, "unowned"):
            validate_coverage_manifest((CoverageEntry("trip", "fact", "test"),))
        with self.assertRaisesRegex(WorkflowFailure, "duplicate"):
            validate_coverage_manifest(COVERAGE_MANIFEST + (COVERAGE_MANIFEST[0],))

    def test_test_pyramid_covers_all_tiers_and_public_data_groups(self):
        validate_test_pyramid_contracts()
        self.assertEqual({scenario.tier for scenario in WORKFLOW_SCENARIOS}, {"contract", "api", "ssr", "full"})
        self.assertGreaterEqual(len(SSR_EDITABLE_FIELD_EXPECTATIONS), 15)

    def test_nightly_selection_runs_the_full_scenario_matrix_only(self):
        selected = select_scenarios(("nightly",))
        self.assertEqual(
            {item.id for item in selected},
            {"happy-path", "stale-content", "revision-conflict", "asset-failure", "release-immutability"},
        )
        self.assertTrue(all(item.tier == "full" for item in selected))
        with self.assertRaisesRegex(WorkflowFailure, "full scenarios only"):
            select_scenarios(("field-contract",))

    def test_ssr_contract_rejects_boolean_or_incomplete_editable_markers(self):
        html = "".join(
            f'<span data-editable="{item.path}" data-edit-owner="{item.owner}" data-edit-mode="{item.mode}"></span>'
            for item in SSR_EDITABLE_FIELD_EXPECTATIONS
        )
        assert_ssr_editable_contract(html)
        with self.assertRaisesRegex(WorkflowFailure, "retired"):
            assert_ssr_editable_contract(html + '<span data-editable="true"></span>')
        with self.assertRaisesRegex(WorkflowFailure, "owner or mode"):
            assert_ssr_editable_contract(html.replace(' data-edit-owner="fact"', '', 1))

    def test_get_path_reads_nested_dicts_and_lists(self):
        self.assertEqual(get_path({"days": [{"title": "One"}]}, "days.0.title"), "One")
        with self.assertRaisesRegex(WorkflowFailure, "Missing asserted"):
            get_path({}, "missing.value")

    def test_content_candidate_requires_a_real_generated_status(self):
        draft = {
            "status": "draft", "missingInputs": [],
            "generation": {"llmCalled": True, "generationStatus": "generated"},
            "factsSnapshot": {"facts": {"trip_facts.destinations": ["Hanoi"]}},
            "candidate": {"trip": {"title": "Title", "lede": "Copy"}, "narrative": {"coverKicker": "Kicker"}},
        }
        assert_content_candidate("hero", draft, {"trip_facts": {"destinations": ["Hanoi"], "itinerary": []}})
        draft["generation"]["generationStatus"] = "fallback"
        with self.assertRaisesRegex(WorkflowFailure, "not generated"):
            assert_content_candidate("hero", draft, {"trip_facts": {"destinations": ["Hanoi"], "itinerary": []}})

    def test_design_sentinels_do_not_claim_or_replace_fact_owned_media(self):
        document = {
            "presentation": {},
            "assets": {"hero": {"r2Key": "shared/media/fact-hero.png"}},
            "itinerary": {"days": [{"images": {"carousel": [{"r2Key": "shared/media/fact-day.png"}]}}]},
            "stays": {"hotels": [{"hotelImage": {"r2Key": "shared/media/fact-hotel.png"}}]},
            "designer": {"image": {"r2Key": "shared/media/fact-designer.png"}},
        }
        updated = apply_design_sentinels(document)
        self.assertEqual(updated["assets"]["hero"]["r2Key"], "shared/media/fact-hero.png")
        self.assertEqual(updated["itinerary"]["days"][0]["images"]["carousel"][0]["r2Key"], "shared/media/fact-day.png")
        self.assertEqual(updated["stays"]["hotels"][0]["hotelImage"]["r2Key"], "shared/media/fact-hotel.png")
        self.assertEqual(updated["designer"]["image"]["r2Key"], "shared/media/fact-designer.png")

    @patch("scripts.test_v2_brochure_workflow.subprocess.run")
    def test_curl_uses_fail_with_body_and_parses_json(self, mocked_run):
        mocked_run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"ok": True}), "")
        response = CurlApi("http://api.test", "editor@test", "service").request("GET", "/quote")
        self.assertEqual(response, {"ok": True})
        command = mocked_run.call_args.args[0]
        self.assertIn("--fail-with-body", command)
        self.assertIn("X-DMC-Email: editor@test", command)

    @patch("scripts.test_v2_brochure_workflow.subprocess.run")
    def test_curl_fails_fast_on_http_error(self, mocked_run):
        mocked_run.return_value = subprocess.CompletedProcess([], 22, '{"detail":"bad"}', "")
        with self.assertRaisesRegex(WorkflowFailure, "curl POST /quote failed"):
            CurlApi("http://api.test", "editor@test", None).request("POST", "/quote", body={})

    @patch("scripts.test_v2_brochure_workflow.subprocess.run")
    def test_curl_rejects_invalid_json(self, mocked_run):
        mocked_run.return_value = subprocess.CompletedProcess([], 0, "not json", "")
        with self.assertRaisesRegex(WorkflowFailure, "invalid JSON"):
            CurlApi("http://api.test", "editor@test", None).request("GET", "/quote")

    @patch("scripts.test_v2_brochure_workflow.subprocess.run")
    def test_curl_request_status_asserts_expected_error_without_fail_flag(self, mocked_run):
        mocked_run.return_value = subprocess.CompletedProcess([], 0, '{"detail":{"currentRevision":2}}\n409', "")
        response = CurlApi("http://api.test", "editor@test", None).request_status("PUT", "/quote", body={}, expected_status=409)
        self.assertEqual(response["detail"]["currentRevision"], 2)
        command = mocked_run.call_args.args[0]
        self.assertNotIn("--fail-with-body", command)
        self.assertTrue(any("%{http_code}" in item for item in command))


if __name__ == "__main__":
    unittest.main()
