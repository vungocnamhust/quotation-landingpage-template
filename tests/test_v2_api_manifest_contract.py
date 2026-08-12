"""Frozen HTTP surface for V2 modular-router refactors.

Keep this list intentionally explicit.  Adding/removing/rebinding an endpoint
must be a separate API change, never an incidental result of moving code.
"""
from __future__ import annotations

import main


EXPECTED_V2_OPERATIONS = {
    ("/api/internal/v2/brands/editor-bootstrap", "GET"),
    ("/api/internal/v2/public-media/{release_id}/{token}", "GET"),
    ("/api/internal/v2/public-pdfs/{release_id}", "GET"),
    ("/api/internal/v2/public-quotations/fallback/{fallback_slug}", "GET"),
    ("/api/internal/v2/public-quotations/releases/{release_id}", "GET"),
    ("/api/internal/v2/public-quotations/resolve", "GET"),
    ("/api/internal/v2/quotations/{quotation_id}/workflow", "GET"),
    ("/api/v2/accommodations", "GET"), ("/api/v2/accommodations", "POST"),
    ("/api/v2/accommodations/{profile_id}", "GET"), ("/api/v2/accommodations/{profile_id}", "PUT"),
    ("/api/v2/accommodations/{profile_id}/status", "PATCH"),
    ("/api/v2/brands", "GET"), ("/api/v2/brands/{brand_id}", "PUT"),
    ("/api/v2/brands/{brand_id}/travel-designer-default", "PUT"),
    ("/api/v2/destinations", "GET"), ("/api/v2/destinations", "POST"),
    ("/api/v2/destinations/{destination_id}", "GET"), ("/api/v2/destinations/{destination_id}", "PUT"),
    ("/api/v2/destinations/{destination_id}/status", "PATCH"),
    ("/api/v2/legacy-create-quotations", "POST"),
    ("/api/v2/legacy-quotations/{quotation_id}/publish", "POST"),
    ("/api/v2/media", "GET"), ("/api/v2/media/upload", "POST"),
    ("/api/v2/media/{asset_id}/select", "POST"), ("/api/v2/media/sync", "POST"),
    ("/api/v2/media-library/children", "GET"), ("/api/v2/media-library/resolve-location", "POST"),
    ("/api/v2/media-library/search", "GET"), ("/api/v2/media-library/sync", "POST"),
    ("/api/v2/media-library/sync/{run_id}", "GET"), ("/api/v2/media-library/uploads", "POST"),
    ("/api/v2/publication-jobs/{job_id}", "GET"), ("/api/v2/quotation-options", "GET"),
    ("/api/v2/quotations", "POST"),
    ("/api/v2/quotations/{quotation_id}/content-drafts", "GET"),
    ("/api/v2/quotations/{quotation_id}/content-drafts", "POST"),
    ("/api/v2/quotations/{quotation_id}/content-drafts/manual", "POST"),
    ("/api/v2/quotations/{quotation_id}/content-drafts/{draft_id}", "PATCH"),
    ("/api/v2/quotations/{quotation_id}/content-drafts/{draft_id}/apply", "POST"),
    ("/api/v2/quotations/{quotation_id}/content-drafts/{draft_id}/discard", "POST"),
    ("/api/v2/quotations/{quotation_id}/document", "GET"), ("/api/v2/quotations/{quotation_id}/document", "PUT"),
    ("/api/v2/quotations/{quotation_id}/facts", "GET"), ("/api/v2/quotations/{quotation_id}/facts", "PUT"),
    ("/api/v2/quotations/{quotation_id}/facts/designer", "PUT"),
    ("/api/v2/quotations/{quotation_id}/facts/media", "PUT"),
    ("/api/v2/quotations/{quotation_id}/facts/media-defaults", "POST"),
    ("/api/v2/quotations/{quotation_id}/presentation", "PUT"),
    ("/api/v2/quotations/{quotation_id}/presentation/copy-overrides", "PUT"),
    ("/api/v2/quotations/{quotation_id}/presentation/overrides", "PUT"),
    ("/api/v2/quotations/{quotation_id}/publication-targets/{target_id}/releases/{release_number}/restore", "POST"),
    ("/api/v2/quotations/{quotation_id}/publication-targets/{target_id}/unpublish", "POST"),
    ("/api/v2/quotations/{quotation_id}/publications", "GET"),
    ("/api/v2/quotations/{quotation_id}/publish", "POST"),
    ("/api/v2/quotations/{quotation_id}/review-status", "GET"),
    ("/api/v2/quotations/{quotation_id}/workflow", "GET"),
    ("/api/v2/travel-designers", "GET"), ("/api/v2/travel-designers", "POST"),
    ("/api/v2/travel-designers/{profile_id}", "PUT"), ("/api/v2/travel-designers/{profile_id}/status", "PATCH"),
    ("/api/v2/travel-styles", "GET"), ("/api/v2/workspace/me", "GET"),
    ("/api/v2/workspace/quotations", "GET"), ("/api/v2/workspace/quotations/{quotation_id}/overview", "GET"),
}


def test_v2_route_manifest_is_exact() -> None:
    actual = {
        (route.path, method)
        for route in main.app.routes
        for method in getattr(route, "methods", set())
        if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        and (route.path.startswith("/api/v2/") or route.path.startswith("/api/internal/v2/"))
    }
    assert actual == EXPECTED_V2_OPERATIONS


def test_v2_openapi_operations_keep_operation_ids() -> None:
    specification = main.app.openapi()
    for path, method in EXPECTED_V2_OPERATIONS:
        if path in {
            "/api/v2/legacy-create-quotations",
            "/api/v2/legacy-quotations/{quotation_id}/publish",
        }:
            continue
        operation = specification["paths"][path][method.lower()]
        assert operation["operationId"]
