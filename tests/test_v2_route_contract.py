"""Public V2 URL/method contract retained during router extraction."""
from __future__ import annotations

import main


def test_v2_route_contract_preserves_core_public_operations() -> None:
    routes = {
        (route.path, method)
        for route in main.app.routes
        for method in getattr(route, "methods", set())
        if route.path.startswith("/api/v2/")
    }
    expected = {
        ("/api/v2/quotations", "POST"),
        ("/api/v2/quotations/{quotation_id}/facts", "GET"),
        ("/api/v2/quotations/{quotation_id}/document", "GET"),
        ("/api/v2/quotations/{quotation_id}/document", "PUT"),
        ("/api/v2/quotations/{quotation_id}/publish", "POST"),
        ("/api/v2/media-library/uploads", "POST"),
        ("/api/v2/brands", "GET"),
        ("/api/v2/publication-jobs/{job_id}", "GET"),
    }
    assert expected <= routes
