from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class V2WorkspaceLocaleContractTests(unittest.TestCase):
    def test_v2_api_has_no_hardcoded_en_query_defaults(self):
        api = (ROOT / "main.py").read_text()
        for route in (
            "list_content_drafts_v2",
            "create_content_drafts_v2",
            "get_canonical_review_status",
            "publish_canonical_quotation_v2",
            "list_canonical_publications",
        ):
            source = api.split(f"async def {route}", 1)[1].split("\n\n", 1)[0]
            self.assertNotIn('lang: str = "en"', source)
        self.assertIn("async def _resolve_v2_locale", api)

    def test_legacy_v2_creation_is_retired_at_react_boundary(self):
        api = (ROOT / "main.py").read_text()
        route = api.split('@app.post("/api/v2/legacy-create-quotations"', 1)[1].split("async def", 1)[1]
        self.assertIn("status_code=410", route[:500])
        self.assertIn("POST /api/v2/quotations", route[:700])

    def test_workspace_gets_canonical_locale_before_hydration(self):
        page = (ROOT / "quote-generator/app/workspace/quotations/[quotationId]/edit/page.tsx").read_text()
        self.assertIn("resolveWorkspaceWorkflow(quotationId)", page)
        self.assertIn("requestedLocale !== workflow.locale", page)
        self.assertIn("URLSearchParams({ stage, lang: workflow.locale })", page)
        self.assertIn("return <QuotationWorkspaceClient", page)
        self.assertNotIn("useSWR", page)

    def test_legacy_workspace_redirect_preserves_query_for_canonicalization(self):
        page = (ROOT / "quote-generator/app/quotations/[quotationId]/workspace/page.tsx").read_text()
        self.assertIn("target.set('stage', query.stage)", page)
        self.assertIn("target.set('lang', query.lang)", page)

    def test_standalone_content_studio_is_only_a_workspace_redirect(self):
        page = (ROOT / "quote-generator/app/content-studio/page.tsx").read_text()
        self.assertIn("const query = new URLSearchParams({ stage: 'content' });", page)
        self.assertIn("if (typeof params.section === 'string') query.set('section', params.section);", page)
        self.assertIn("redirect(`/workspace/quotations/${encodeURIComponent(quotationId)}/edit?${query}`)", page)
        for forbidden in ("BRANDS_DATA", "BRAND_PREFERENCE_KEY", "routeState", "buildPageViewModel"):
            self.assertNotIn(forbidden, page)

    def test_internal_workflow_endpoint_is_service_only(self):
        api = (ROOT / "main.py").read_text()
        route = "/api/internal/v2/quotations/{quotation_id}/workflow"
        self.assertIn(route, api)
        route_source = api.split(route, 1)[1].split('@app.', 1)[0]
        self.assertIn("Depends(require_editor_or_service)", route_source)
        self.assertIn("if not principal.is_service", route_source)

    def test_canonical_review_status_filters_pending_drafts_to_active_draft_status(self):
        api = (ROOT / "main.py").read_text()
        review_source = api.split("async def _canonical_review_status", 1)[1].split("\n\n", 1)[0]
        self.assertIn('pending_drafts = sorted({item.scope for item in content if item.status == "draft"})', review_source)


if __name__ == "__main__":
    unittest.main()
