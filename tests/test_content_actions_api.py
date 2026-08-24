"""HTTP-contract tests for the Actionable Content Plan router."""
from __future__ import annotations

from routers.v2.content_actions import router
from routers.v2.schemas.content_actions import BypassContentActionsRequest, ExecuteContentActionsRequest


def test_content_action_router_exposes_only_typed_action_operations() -> None:
    operations = {
        (route.path, method)
        for route in router.routes
        for method in route.methods or set()
        if method in {"GET", "POST"}
    }
    assert operations == {
        ("/api/v2/quotations/{quotation_id}/content-actions", "GET"),
        ("/api/v2/quotations/{quotation_id}/content-actions/accept", "POST"),
        ("/api/v2/quotations/{quotation_id}/content-actions/generate-drafts", "POST"),
        ("/api/v2/quotations/{quotation_id}/content-actions/generate-and-apply", "POST"),
    }


def test_content_action_execution_contracts_keep_revision_boundary() -> None:
    auto = ExecuteContentActionsRequest(planId="cap_1", actionIds=["act_1"])
    bypass = BypassContentActionsRequest(planId="cap_1", actionIds=["act_1"], expectedRevision=7)

    assert auto.writingStyle == "storytelling"
    assert bypass.expectedRevision == 7
