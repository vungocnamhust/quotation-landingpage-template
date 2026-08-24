"""Browser evidence for an accepted Actionable Content Plan.

This runner consumes the real API/action report.  It deliberately only proves
the staff routing and interaction contract: accepting or opening a scope must
not turn navigation into an AI, draft, or document mutation request.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, help="Passed actionable-content API report")
    parser.add_argument("--report-file", required=True)
    return parser.parse_args()


def write_report(path: str, report: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    args = parse_args()
    editor_base = os.environ.get("E2E_EDITOR_BASE_URL", "").rstrip("/")
    require(bool(editor_base), "E2E_EDITOR_BASE_URL is required inside the Compose e2e service.")
    source = json.loads(Path(args.report).read_text(encoding="utf-8"))
    require(source.get("status") == "passed", f"Browser proof needs a passed Actionable Content report: {source}")
    quotation_id = source.get("successorId")
    require(isinstance(quotation_id, str) and quotation_id, f"Actionable Content report lacks successorId: {source}")
    artifact_dir = Path(args.report_file).resolve().parent
    report: dict[str, Any] = {
        "status": "running",
        "tier": "actionable-browser",
        "quotationId": quotation_id,
        "sourceReport": str(Path(args.report)),
        "screenshots": [],
        "mutationRequests": [],
    }
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            mutation_requests: list[str] = []

            def capture(request: Any) -> None:
                if request.method != "POST":
                    return
                if "/content-actions" in request.url or "/content-drafts" in request.url:
                    mutation_requests.append(f"{request.method} {request.url}")

            page.on("request", capture)
            impact_url = f"{editor_base}/quotations/{quotation_id}/workspace?stage=impact&lang=en"
            page.goto(impact_url, wait_until="networkidle")
            expect(page.get_by_role("heading", name="Content change plan")).to_be_visible()
            artifact_dir.mkdir(parents=True, exist_ok=True)
            impact_shot = artifact_dir / "actionable-impact-center.png"
            page.screenshot(path=str(impact_shot), full_page=True)
            report["screenshots"].append(str(impact_shot))

            before_facts = len(mutation_requests)
            page.get_by_role("button", name="Review Facts").click()
            expect(page).to_have_url(re.compile(r"stage=facts"))
            require(
                mutation_requests[before_facts:] == [],
                f"Review Facts issued a Content mutation: {mutation_requests[before_facts:]}",
            )

            page.goto(impact_url, wait_until="networkidle")
            before_content = len(mutation_requests)
            scope_button = page.get_by_role("button", name="Open Content scope").first
            expect(scope_button).to_be_visible()
            scope_button.click()
            expect(page).to_have_url(re.compile(r"stage=content&.*section="))
            require(
                mutation_requests[before_content:] == [],
                f"Open Content issued a Content mutation: {mutation_requests[before_content:]}",
            )
            content_shot = artifact_dir / "actionable-content-deep-link.png"
            page.screenshot(path=str(content_shot), full_page=True)
            report["screenshots"].append(str(content_shot))
            browser.close()

        report.update({
            "status": "passed",
            "assertions": [
                "impact-center-visible",
                "review-facts-deep-link-without-content-mutation",
                "open-content-deep-link-without-content-mutation",
            ],
            "mutationRequests": mutation_requests,
        })
        write_report(args.report_file, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as error:
        report.update({"status": "failed", "error": str(error)})
        write_report(args.report_file, report)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
