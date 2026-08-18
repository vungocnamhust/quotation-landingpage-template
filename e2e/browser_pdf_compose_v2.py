"""Browser/PDF evidence tier for a release prepared by the real curl runner.

This deliberately does not create a quotation or invoke an LLM.  It consumes
the compact ``full`` tier report, then proves workspace interaction, anonymous
SSR and a real PDF endpoint against the same already-running Compose services.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader


# Resolve inside ``main`` so ``--help`` remains usable outside Compose.
API_BASE = ""
EDITOR_BASE = ""


def request_json(path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(f"{API_BASE}{path}", data=body, method=method, headers={"Content-Type": "application/json"} if body else {})
    try:
        with urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except Exception as error:
        if hasattr(error, "code"):
            return error.code, json.loads(error.read().decode("utf-8"))
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, help="Completed report from scripts/test_v2_brochure_workflow.py --tier full")
    parser.add_argument("--report-file", required=True)
    return parser.parse_args()


def save_report(path: str, report: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def screenshot(page: Any, artifact_dir: Path, report: dict[str, Any], name: str) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    target = artifact_dir / name
    page.screenshot(path=str(target), full_page=True)
    report.setdefault("screenshots", []).append(str(target))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def document_at_path(document: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = document
    for segment in path:
        require(isinstance(value, dict) and segment in value, f"Missing document path: {'.'.join(path)}")
        value = value[segment]
    return value


def wait_for_publication(job_id: str) -> None:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        status, job = request_json(f"/api/v2/publication-jobs/{job_id}")
        require(status == 200, f"Cannot read publication job: {job}")
        if job.get("status") == "succeeded":
            return
        if job.get("status") == "failed":
            raise AssertionError(f"Publication job failed: {job}")
        time.sleep(1)
    raise AssertionError(f"Publication job timed out: {job_id}")


def publish_current_revision(quotation_id: str, revision: int) -> dict[str, Any]:
    status, queued = request_json(
        f"/api/v2/quotations/{quotation_id}/publish?lang=en",
        method="POST",
        payload={"baseRevision": revision},
    )
    require(status == 200 or status == 202, f"Publish was not queued: {queued}")
    require(isinstance(queued.get("jobId"), str) and isinstance(queued.get("releaseId"), str), f"Publish response incomplete: {queued}")
    wait_for_publication(queued["jobId"])
    return queued


def assert_canvas_handoff(
    page: Any,
    *,
    quotation_id: str,
    source: str,
    stage: str,
    section: str,
    focus_control: str | None = None,
    keyboard: bool = False,
) -> None:
    """Exercise selection through the canvas; it must only navigate, never write."""
    page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=design&lang=en", wait_until="networkidle")
    marker = page.locator(f'[data-editable="{source}"]').first
    expect(marker).to_be_visible()
    if keyboard:
        marker.evaluate("element => { element.setAttribute('tabindex', '0'); element.focus(); }")
        page.keyboard.press("Enter")
    else:
        marker.click()
    expect(page.get_by_text(f"Canonical source: {source}", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name=f"Open {'Facts' if stage == 'facts' else 'Content Studio'}")).to_be_visible().click()
    query = rf"stage={stage}&(?:factsSection|section)={re.escape(section)}"
    expect(page).to_have_url(re.compile(query))
    if focus_control:
        expect(page.locator(f"#{focus_control}")).to_be_focused()


def save_design_value_from_canvas(
    page: Any,
    *,
    quotation_id: str,
    source: str,
    value: str,
    selector: str,
    attribute: str,
) -> None:
    """Save through the UI, then prove the public display model sees the exact override."""
    page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=design&lang=en", wait_until="networkidle")
    marker = page.locator(f'[data-editable="{source}"]').first
    expect(marker).to_be_visible()
    marker.click()
    input_control = page.get_by_label("Presentation copy", exact=True)
    expect(input_control).to_be_visible()
    input_control.fill(value)
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_text("Design override saved.", exact=True)).to_be_visible()
    expect(page.locator(selector).first).to_have_attribute(attribute, value)


def save_designer_fact_from_canvas(
    page: Any,
    *,
    quotation_id: str,
    source: str,
    value: str,
) -> None:
    """Prove Fact-owned Designer text uses the Canvas inspector, not a handoff."""
    page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=design&lang=en", wait_until="networkidle")
    marker = page.locator(f'[data-editable="{source}"]').first
    expect(marker).to_be_visible()
    marker.click()
    input_control = page.get_by_label("Designer copy (saved to Facts)", exact=True)
    expect(input_control).to_be_visible()
    input_control.fill(value)
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_text("Designer copy saved to Facts.", exact=True)).to_be_visible()
    expect(page.locator(f'[data-editable="{source}"]').first).to_contain_text(value)


def assert_system_canvas_target_is_read_only(page: Any, *, quotation_id: str, source: str) -> None:
    page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=design&lang=en", wait_until="networkidle")
    marker = page.locator(f'[data-editable="{source}"]').first
    expect(marker).to_be_visible()
    marker.click()
    expect(page.get_by_text("This is locale-owned system copy. It has no quotation-level editor.", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name=re.compile("Open (Facts|Content Studio)"))).to_have_count(0)


def main() -> int:
    global API_BASE, EDITOR_BASE
    args = parse_args()
    API_BASE = os.environ.get("E2E_API_BASE_URL", "").rstrip("/")
    EDITOR_BASE = os.environ.get("E2E_EDITOR_BASE_URL", "").rstrip("/")
    if not API_BASE or not EDITOR_BASE:
        raise RuntimeError("E2E_API_BASE_URL and E2E_EDITOR_BASE_URL are required inside the Compose e2e service.")
    source = json.loads(Path(args.report).read_text(encoding="utf-8"))
    if source.get("status") != "passed" or source.get("tier") != "full":
        raise RuntimeError(f"Browser/PDF needs a passed full report, got: {source}")
    quotation_id, release_id, published_url = (source.get(key) for key in ("quotationId", "releaseId", "publishedUrl"))
    if not all(isinstance(item, str) and item for item in (quotation_id, release_id, published_url)):
        raise RuntimeError(f"Full report lacks release identifiers: {source}")

    artifact_dir = Path(args.report_file).resolve().parent
    report: dict[str, Any] = {
        "status": "running",
        "tier": "browser-pdf",
        "quotationId": quotation_id,
        "releaseId": release_id,
        "sourceReport": str(Path(args.report)),
        "screenshots": [],
        "canvasAssertions": [],
    }
    try:
        status, current = request_json(f"/api/v2/quotations/{quotation_id}/document?lang=en")
        assert status == 200, current
        revision = current["currentRevision"]
        document = current["document"]
        # Content provenance must survive canvas handoff: write an explicitly
        # distinguishable sender/sign-off through the manual Content-draft
        # contract, never through the profile/Facts document path.
        editor_state = current.get("contentEditorState", {})
        overview_candidate = editor_state.get("overview_letter")
        require(isinstance(overview_candidate, dict), "Overview Content editor state is missing.")
        manual_candidate = json.loads(json.dumps(overview_candidate))
        narrative = manual_candidate.setdefault("narrative", {})
        require(isinstance(narrative, dict), "Overview candidate has no narrative object.")
        narrative.update({"letterSignOff": "E2E Content Sign-off", "letterSender": "E2E Content Sender"})
        status, manual = request_json(
            f"/api/v2/quotations/{quotation_id}/content-drafts/manual?lang=en",
            method="POST",
            payload={"scope": "overview_letter", "candidate": manual_candidate, "baseRevision": revision},
        )
        require(status == 200, f"Manual Content draft rejected: {manual}")
        draft = manual.get("draft", {})
        require(isinstance(draft.get("id"), str), f"Manual draft identifier missing: {manual}")
        status, applied = request_json(
            f"/api/v2/quotations/{quotation_id}/content-drafts/{draft['id']}/apply",
            method="POST",
            payload={"baseRevision": revision},
        )
        require(status == 200, f"Manual Content draft Apply failed: {applied}")
        revision, document = applied["currentRevision"], applied["document"]
        require(document_at_path(document, ("narrative", "letterSignOff")) == "E2E Content Sign-off", "Content sign-off was not canonicalized.")
        require(document_at_path(document, ("narrative", "letterSender")) == "E2E Content Sender", "Content sender was not canonicalized.")
        day_id = document["itinerary"]["days"][0]["id"]
        day_number = document["itinerary"]["days"][0]["dayNumber"]
        hotel_id = document["stays"]["hotels"][0]["id"]
        pricing_id = document["pricing"]["options"][0]["id"]
        booking_blocks = document["content"]["sections"]["booking_terms"]["blocks"]
        booking_block_index = next(index for index, block in enumerate(booking_blocks) if block.get("type") in {"termList", "paymentSchedule"} and block.get("items"))

        # The deliberate stale retry proves the same revision policy observed
        # by the Design Canvas UI, without overwriting its saved values.
        status, saved = request_json(
            f"/api/v2/quotations/{quotation_id}/presentation/overrides?lang=en",
            method="PUT",
            payload={"baseRevision": revision, "copyOverrides": {"a11y.interactiveRouteMap": "Browser PDF acceptance map"}, "identityOverrides": {}},
        )
        assert status == 200, saved
        revision = saved["currentRevision"]
        status, conflict = request_json(
            f"/api/v2/quotations/{quotation_id}/presentation/overrides?lang=en",
            method="PUT",
            payload={"baseRevision": revision - 1, "copyOverrides": {"a11y.interactiveRouteMap": "must not persist"}, "identityOverrides": {}},
        )
        assert status == 409 and conflict.get("detail", {}).get("currentRevision") == revision, conflict

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            generated_requests: list[str] = []
            page.on("request", lambda request: generated_requests.append(request.url) if request.method == "POST" and "/content-drafts" in request.url else None)
            page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=content&section=hero&lang=en", wait_until="networkidle")
            expect(page).to_have_url(f"{EDITOR_BASE}/workspace/quotations/{quotation_id}/edit?stage=content&section=hero&lang=en")
            expect(page.get_by_text("CONTENT STUDIO")).to_be_visible()
            assert not generated_requests, generated_requests
            screenshot(page, artifact_dir, report, "content-studio-desktop.png")

            page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=design&lang=en", wait_until="networkidle")
            expect(page.get_by_text("Select an element on the brochure.")).to_be_visible()
            editable = page.locator('[data-edit-owner="design"]').first
            editable.click()
            editable.evaluate("element => { element.setAttribute('tabindex', '0'); element.focus(); }")
            page.keyboard.press("Enter")
            expect(page.get_by_text("Presentation copy")).to_be_visible()

            # Every owner class is exercised from the real canvas. Repeated
            # records navigate by canonical stable ID and focus the native
            # Facts control; neither click makes a quotation write.
            assert_canvas_handoff(page, quotation_id=quotation_id, source="/narrative/letterSignOff", stage="content", section="overview_letter", keyboard=True)
            report["canvasAssertions"].append("content-letter-signoff-keyboard")
            assert_canvas_handoff(page, quotation_id=quotation_id, source="/narrative/letterSender", stage="content", section="overview_letter")
            report["canvasAssertions"].append("content-letter-sender")
            assert_canvas_handoff(page, quotation_id=quotation_id, source="/content/sections/inclusions_exclusions/blocks/0/leftItems/0", stage="content", section="inclusions_exclusions")
            report["canvasAssertions"].append("content-finalization-group")
            assert_canvas_handoff(page, quotation_id=quotation_id, source="/itinerary/days/0/title", stage="content", section=f"itinerary:day:{day_number}")
            assert_canvas_handoff(page, quotation_id=quotation_id, source="/itinerary/days/0/labelHighlights", stage="facts", section="programme", focus_control="day-0-number")
            report["canvasAssertions"].append("facts-itinerary-repeater")
            assert_canvas_handoff(page, quotation_id=quotation_id, source="/stays/hotels/0/name", stage="facts", section="services", focus_control="hotel-0-name")
            report["canvasAssertions"].append("facts-hotel-repeater")
            assert_canvas_handoff(page, quotation_id=quotation_id, source="/pricing/options/0/label", stage="facts", section="commercial", focus_control="pricing-0-label")
            report["canvasAssertions"].append("facts-pricing-repeater")
            assert_canvas_handoff(page, quotation_id=quotation_id, source=f"/content/sections/booking_terms/blocks/{booking_block_index}/items/0/label", stage="facts", section="seller", focus_control="booking-term-0-label")
            report["canvasAssertions"].append("facts-booking-block-item")
            assert_canvas_handoff(page, quotation_id=quotation_id, source="/designer/name", stage="facts", section="trip")
            assert_canvas_handoff(page, quotation_id=quotation_id, source="/route/staySegments/0/displayName", stage="facts", section="programme")
            assert_system_canvas_target_is_read_only(page, quotation_id=quotation_id, source="/labels/classic")
            report["canvasAssertions"].extend(["fact-derived-designer", "fact-derived-route", "system-read-only"])
            save_designer_fact_from_canvas(page, quotation_id=quotation_id, source="/designer/kicker", value="E2E DESIGNER KICKER")
            save_designer_fact_from_canvas(page, quotation_id=quotation_id, source="/designer/title", value="E2E DESIGNER TITLE")
            save_designer_fact_from_canvas(page, quotation_id=quotation_id, source="/designer/subtitle", value="E2E DESIGNER SUBTITLE")
            save_designer_fact_from_canvas(page, quotation_id=quotation_id, source="/designer/quote", value="E2E Designer quote")
            save_designer_fact_from_canvas(page, quotation_id=quotation_id, source="/designer/signature", value="E2E DESIGNER SIGNATURE")
            save_designer_fact_from_canvas(page, quotation_id=quotation_id, source="/designer/experience", value="E2E designer experience")
            save_designer_fact_from_canvas(page, quotation_id=quotation_id, source="/designer/ctaBody", value="E2E CTA body")
            report["canvasAssertions"].append("designer-fact-inspector-writes")

            page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=facts&factsSection=programme&focus=day:{day_id}&lang=en", wait_until="networkidle")
            expect(page.locator("#day-0-number")).to_be_focused()
            page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=facts&factsSection=services&focus=hotel:{hotel_id}&lang=en", wait_until="networkidle")
            expect(page.locator("#hotel-0-name")).to_be_focused()
            page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=facts&factsSection=commercial&focus=pricingOption:{pricing_id}&lang=en", wait_until="networkidle")
            expect(page.locator("#pricing-0-label")).to_be_focused()
            mobile = browser.new_page(viewport={"width": 480, "height": 1000})
            mobile.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=design&lang=en", wait_until="networkidle")
            mobile.locator('[data-editable="/narrative/letterSignOff"]').first.click()
            expect(mobile.get_by_role("button", name="Open Content Studio")).to_be_visible()
            mobile.close()
            save_design_value_from_canvas(
                page,
                quotation_id=quotation_id,
                source="/presentation/identityOverrides/logoAlt",
                value="E2E Canvas Logo Alt",
                selector="img.display-nav__logo-image",
                attribute="alt",
            )
            save_design_value_from_canvas(
                page,
                quotation_id=quotation_id,
                source="/presentation/copyOverrides/a11y.brochureSections",
                value="E2E Canvas Navigation",
                selector="nav.display-nav__links",
                attribute="aria-label",
            )
            report["canvasAssertions"].extend(["design-logo-alt-save", "design-nav-aria-save"])
            screenshot(page, artifact_dir, report, "design-canvas-desktop.png")
            browser.close()

        status, after_canvas = request_json(f"/api/v2/quotations/{quotation_id}/document?lang=en")
        require(status == 200, f"Cannot reload canvas mutations: {after_canvas}")
        revision = after_canvas["currentRevision"]
        document = after_canvas["document"]
        require(document_at_path(document, ("presentation", "identityOverrides", "logoAlt")) == "E2E Canvas Logo Alt", "Logo-alt UI save did not persist.")
        require(document_at_path(document, ("presentation", "copyOverrides", "a11y.brochureSections")) == "E2E Canvas Navigation", "Navigation label UI save did not persist.")
        republished = publish_current_revision(quotation_id, revision)
        release_id, published_url = republished["releaseId"], republished["published_url"]
        report.update({"releaseId": release_id, "publishedUrl": published_url, "revisionBeforeCanvas": source["revision"], "revisionAfter": revision})

        published = urlparse(published_url)
        assert published.hostname and published.path, published_url
        # Nginx aliases every supported brand hostname inside the Compose
        # network, so use the actual release hostname instead of assuming one
        # brand in this evidence runner.
        public_base, public_path = f"http://{published.hostname}", published.path
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            response = page.goto(f"{public_base}{public_path}", wait_until="networkidle")
            assert response and response.status == 200
            # Public route must be browse-only: no workspace selection overlay.
            assert page.locator("[data-workspace-selection-overlay]").count() == 0
            expect(page.locator("nav.display-nav__links").first).to_have_attribute("aria-label", "E2E Canvas Navigation")
            expect(page.locator("img.display-nav__logo-image").first).to_have_attribute("alt", "E2E Canvas Logo Alt")
            expect(page.get_by_text("E2E Content Sign-off", exact=True)).to_be_visible()
            expect(page.get_by_text("E2E Content Sender", exact=True)).to_be_visible()
            expect(page.locator('[data-editable="/assets/hero/altText"]').first).to_have_attribute("alt", "WF_E2E hero image")
            report["publicAssertions"] = ["no-workspace-overlay", "design-nav-aria", "design-logo-alt", "content-letter-provenance", "hero-media-alt"]
            screenshot(page, artifact_dir, report, "public-desktop.png")
            pdf = page.request.get(f"{public_base}{public_path}/pdf/download")
            assert pdf.status == 200 and pdf.headers.get("content-type", "").startswith("application/pdf")
            pdf_bytes = pdf.body()
            assert pdf_bytes.startswith(b"%PDF")
            reader = PdfReader(BytesIO(pdf_bytes))
            pdf_text = "\n".join(item.extract_text() or "" for item in reader.pages)
            assert len(reader.pages) >= 1 and pdf_text.strip()
            require("E2E Content Sign-off" in pdf_text and "E2E Content Sender" in pdf_text, "PDF did not consume canonical Content letter values.")
            pdf_path = artifact_dir / "public-brochure.pdf"
            pdf_path.write_bytes(pdf_bytes)
            report["pdfPath"] = str(pdf_path)
            for width, name in ((980, "public-980.png"), (480, "public-mobile.png")):
                responsive = browser.new_page(viewport={"width": width, "height": 1000})
                responsive_response = responsive.goto(f"{public_base}{public_path}", wait_until="networkidle")
                assert responsive_response and responsive_response.status == 200
                screenshot(responsive, artifact_dir, report, name)
                responsive.close()
            browser.close()

        report.update({"status": "passed", "revision": revision, "pdfUrl": f"{published_url}/pdf/download"})
        save_report(args.report_file, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        report.update({"status": "failed", "error": str(exc)})
        save_report(args.report_file, report)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
