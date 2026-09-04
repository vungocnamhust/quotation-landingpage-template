"""Black-box Compose proof for the React-only V2 quotation path.

It intentionally uses the HTTP boundary for test setup, then uses Playwright
through Nginx for editor and public routes. This proves host routing, internal
service-token rendering, the PDF worker, and anonymous public access together.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import copy
from io import BytesIO
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import main as api_main
from db.models.publication import PublicationJob, PublicationRelease
from db.models.brand import Brand
from repositories.accommodation_repository import AccommodationRepository
from repositories.destination_repository import DestinationRepository
from repositories.media_library_repository import MediaLibraryRepository
from repositories.travel_designer_repository import TravelDesignerRepository
from scripts.create_test_v2_quotation import create_sample_quote_request
from services.storage.r2_storage import R2Storage


API_BASE = os.environ["E2E_API_BASE_URL"].rstrip("/")
EDITOR_BASE = os.environ["E2E_EDITOR_BASE_URL"].rstrip("/")
PUBLIC_BASES = {
    "capella_travel": os.environ["E2E_CAPELLA_PUBLIC_BASE_URL"].rstrip("/"),
    "selvara": os.environ["E2E_SELVARA_PUBLIC_BASE_URL"].rstrip("/"),
}
ARTIFACT_DIR = Path(os.environ.get("E2E_ARTIFACT_DIR", "/tmp/quotation-e2e"))
EVIDENCE: dict[str, Any] = {"status": "running", "screenshots": [], "draftIds": []}


def save_evidence(*, status: str, error: str | None = None) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE["status"] = status
    if error:
        EVIDENCE["error"] = error
    (ARTIFACT_DIR / "compose-acceptance-report.json").write_text(json.dumps(EVIDENCE, indent=2), encoding="utf-8")


def screenshot(page: Any, name: str) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / name
    page.screenshot(path=str(path), full_page=True)
    EVIDENCE["screenshots"].append(str(path))


def _get_e2e_db_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql+asyncpg://quotation:quotation-e2e@postgres:5432/quotation")


def request_json(path: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: float = 60) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(f"{API_BASE}{path}", data=body, method=method, headers={"Content-Type": "application/json"} if body else {})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except Exception as error:
        if hasattr(error, "code"):
            return error.code, json.loads(error.read().decode("utf-8"))
        raise


def wait_for_api() -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            status, _ = request_json("/health/live")
            if status == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("FastAPI did not become healthy within 90 seconds")


def wait_for_job(job_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 120
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        status, last = request_json(f"/api/v2/publication-jobs/{job_id}")
        if status == 200 and last.get("status") in {"succeeded", "completed", "failed"}:
            if last.get("status") in {"succeeded", "completed"}:
                return last
            raise AssertionError(f"publication job failed: {last.get('lastError')}")
        time.sleep(1)
    raise AssertionError(f"publication job did not finish: {last}")


async def purge_urls_for_release(release_id: str) -> list[str]:
    engine = create_async_engine(_get_e2e_db_url())
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        job = await session.scalar(
            select(PublicationJob)
            .where(PublicationJob.release_id == release_id, PublicationJob.job_type == "purge_cache")
            .order_by(PublicationJob.created_at.desc())
            .limit(1)
        )
        res = list((job.payload_json or {}).get("urls") or []) if job else []
    await engine.dispose()
    return res


async def release_media_url(release_id: str, public_base: str) -> str:
    engine = create_async_engine(_get_e2e_db_url())
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        release = await session.get(PublicationRelease, release_id)
        assert release is not None, release_id
        token = next(iter((release.asset_manifest or {}).keys()), None)
        assert token, f"release {release_id} has no media manifest"
        res = f"{public_base}/media/{release_id}/{token}"
    await engine.dispose()
    return res


def canonicalize_catalog_names(value: Any) -> Any:
    """Keep the external fixture representative while using catalog canonical IDs."""
    if isinstance(value, dict):
        return {key: canonicalize_catalog_names(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonicalize_catalog_names(item) for item in value]
    return "Ha Long Bay" if value == "Halong Bay" else value


def make_disposable_acceptance_payload() -> dict[str, Any]:
    """Return a minimal, complete quotation for one real end-to-end journey.

    Acceptance needs one independently-generated itinerary day, not eight
    duplicate LLM calls.  Keeping a single enabled day makes the run faster and
    still proves the publish gate requires every enabled section and child.
    """
    payload = canonicalize_catalog_names(create_sample_quote_request())
    first_day = copy.deepcopy(payload["trip_facts"]["itinerary"][0])
    first_day["display_date"] = "01 Oct 2026"
    payload["trip_facts"].update(
        {
            "destinations": ["Hanoi"],
            "start_date": "2026-10-01",
            "end_date": "2026-10-01",
            "duration_days": 1,
            "duration_nights": 0,
            "display_route_text": "Hanoi",
            "display_travel_dates": "01 Oct 2026",
            "itinerary": [first_day],
        }
    )
    payload["service_facts"]["hotels"] = [payload["service_facts"]["hotels"][0]]
    return payload


def apply_required_content(
    quotation_id: str,
    *,
    lang: str,
    revision: int,
    itinerary: list[dict[str, Any]],
) -> int:
    """Apply every required candidate before exercising Design controls.

    A new quotation deliberately starts incomplete.  The E2E test must prove
    the actual Facts -> Content -> Design sequence rather than side-step the
    content contract with a presentation write to an invalid document.
    """
    scopes = ["hero", "overview_letter", "route", "itinerary"]
    scopes.extend(f"itinerary:day:{item['day_number']}" for item in itinerary)
    for scope in scopes:
        status, created = request_json(
            f"/api/v2/quotations/{quotation_id}/content-drafts?lang={lang}",
            method="POST",
            payload={"scope": scope, "generationMode": "storytelling", "instruction": "ONE_SHOT_E2E_GUIDANCE"},
        )
        assert status == 200, created
        draft = created.get("draft")
        assert draft, created
        assert "ONE_SHOT_E2E_GUIDANCE" not in json.dumps(draft.get("generation", {})), draft
        if scope in {"hero", "overview_letter"} or scope.startswith("itinerary:day:"):
            assert draft.get("generation", {}).get("llmCalled") is True, created
        EVIDENCE["draftIds"].append(draft["id"])
        status, applied = request_json(
            f"/api/v2/quotations/{quotation_id}/content-drafts/{draft['id']}/apply",
            method="POST",
            payload={"baseRevision": revision},
        )
        assert status == 200, applied
        revision = applied["currentRevision"]
    return revision


def assert_missing_facts_never_call_ai(payload: dict[str, Any]) -> None:
    """A no-AI Content path must surface missing saved facts, not invent copy.

    Creation intentionally enforces complete intake facts.  This test therefore
    creates a valid disposable quotation first, then saves an incomplete Facts
    revision before requesting the day scope.  That exercises the production
    Content boundary without weakening the intake contract just for E2E.
    """
    incomplete = copy.deepcopy(payload)
    incomplete["opportunity_id"] = "E2E-NO-AI-MISSING-FACTS"
    status, created = request_json("/api/v2/quotations", method="POST", payload=incomplete)
    assert status == 200, created
    quotation_id = created["quotationId"]
    status, facts_response = request_json(f"/api/v2/quotations/{quotation_id}/facts")
    assert status == 200, facts_response
    facts = facts_response["facts"]
    facts["trip_facts"]["itinerary"][0]["summary"] = ""
    facts["trip_facts"]["itinerary"][0]["highlights"] = []
    status, updated = request_json(
        f"/api/v2/quotations/{quotation_id}/facts?baseRevision={facts_response['currentRevision']}",
        method="PUT",
        payload=facts,
    )
    assert status == 200, updated
    status, drafts = request_json(
        f"/api/v2/quotations/{quotation_id}/content-drafts?lang=en",
        method="POST",
        payload={"scope": "itinerary:day:1", "generationMode": "detailed"},
    )
    assert status == 200, drafts
    draft = drafts.get("draft")
    assert draft and draft["generation"]["llmCalled"] is False and draft["missingInputs"], drafts


async def _ensure_default_travel_designer() -> None:
    engine = create_async_engine(_get_e2e_db_url())
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        repo = TravelDesignerRepository(session)
        profile = await repo.get_active_by_email("local@localhost")
        if not profile:
            await repo.create_profile(
                profile_id="td_e2e_local",
                email="local@localhost",
                name="E2E Travel Designer",
                phone="+84900000000",
                storage_slug="local",
            )
            await session.commit()
    await engine.dispose()


async def _ensure_e2e_brands_active() -> None:
    """Reset mutable brand test state before a disposable acceptance run.

    The workflow intentionally disables Capella at its final public-route
    assertion. Compose keeps PostgreSQL volumes between invocations, so the
    next otherwise-independent run must restore the seeded brands first.  This
    is test-fixture setup only; every quotation/publication mutation remains
    exercised through the public API.
    """
    engine = create_async_engine(_get_e2e_db_url())
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        for brand_id in ("capella_travel", "selvara"):
            brand = await session.get(Brand, brand_id)
            assert brand is not None, f"Required seeded brand is missing: {brand_id}"
            brand.status = "active"
        await session.commit()
    await engine.dispose()


async def _seed_e2e_intake_catalog(payload: dict[str, Any]) -> None:
    """Create only the catalog records required by this disposable quotation.

    The Create API validates hotel selections against real active accommodation
    profiles.  Seeding them here keeps the HTTP workflow representative while
    avoiding production fixtures or an API-side testing escape hatch.
    """
    engine = create_async_engine(_get_e2e_db_url())
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await api_main._seed_destination_catalog(session)
        destinations = DestinationRepository(session)
        accommodations = AccommodationRepository(session)
        for index, hotel in enumerate(payload["service_facts"]["hotels"]):
            destination = await destinations.resolve(hotel["destination"])
            assert destination is not None, hotel["destination"]
            existing = next(
                (
                    item
                    for item in await accommodations.list_profiles(destination_id=destination.id, search=hotel["name"])
                    if item.name == hotel["name"]
                ),
                None,
            )
            if existing is not None:
                hotel["accommodation_id"] = existing.id
                continue
            saved = await api_main._save_accommodation_profile(
                session,
                api_main.AccommodationProfileRequest(
                    destinationId=destination.id,
                    name=hotel["name"],
                    room_type=hotel["room_type"],
                    intro=hotel.get("intro"),
                    phone=hotel.get("phone"),
                    display_city=hotel.get("display_city"),
                    display_date=hotel.get("display_date"),
                ),
            )
            hotel["accommodation_id"] = saved["id"]
        await session.commit()
    await engine.dispose()


async def _register_e2e_media(keys: list[str]) -> None:
    """Index uploaded disposable R2 objects through the production catalogue."""
    engine = create_async_engine(_get_e2e_db_url())
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        catalogue = MediaLibraryRepository(session)
        for key in keys:
            await catalogue.upsert_object(
                run_id=None,
                bucket="quotation-v2",
                r2_key=key,
                parent_prefix=key.rsplit("/", 1)[0],
                file_name=key.rsplit("/", 1)[-1],
                content_type="image/png",
                size_bytes=69,
                etag=None,
                source_modified_at=None,
            )
        await session.commit()
    await engine.dispose()


def run_sync(coro: Any) -> Any:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coro)).result()


def ensure_default_travel_designer() -> None:
    run_sync(_ensure_default_travel_designer())


def ensure_e2e_brands_active() -> None:
    run_sync(_ensure_e2e_brands_active())


def seed_e2e_intake_catalog(payload: dict[str, Any]) -> None:
    run_sync(_seed_e2e_intake_catalog(payload))


def register_e2e_media(keys: list[str]) -> None:
    run_sync(_register_e2e_media(keys))


def main() -> None:
    wait_for_api()
    ensure_e2e_brands_active()
    ensure_default_travel_designer()
    payload = make_disposable_acceptance_payload()
    payload["brand_id"] = "capella_travel"
    payload["opportunity_id"] = "E2E-REACT-ONLY"
    payload["presentation_options"] = {
        "template_id": "quote-generator",
        "renderer": "quote-generator",
        "theme_id": "brochure",
        "layout_version": 1,
        "travel_designer_id": "td_e2e_local",
    }
    seed_e2e_intake_catalog(payload)
    assert_missing_facts_never_call_ai(payload)
    status, created = request_json("/api/v2/quotations", method="POST", payload=payload)
    assert status == 200, created
    quotation_id = created["quotationId"]
    revision = created["currentRevision"]
    EVIDENCE.update({"quotationId": quotation_id, "initialRevision": revision})
    status, blocked_publish = request_json(
        f"/api/v2/quotations/{quotation_id}/publish?lang=en",
        method="POST",
        payload={"baseRevision": revision, "brandId": "capella_travel"},
    )
    assert status == 422 and blocked_publish, blocked_publish
    revision = apply_required_content(
        quotation_id,
        lang="en",
        revision=revision,
        itinerary=payload["trip_facts"]["itinerary"],
    )
    status, canonical = request_json(f"/api/v2/quotations/{quotation_id}/document?lang=en")
    assert status == 200 and canonical["currentRevision"] == revision, canonical
    assert all(key in canonical["document"].get("content", {}).get("sections", {}) for key in ("inclusions_exclusions", "booking_terms")), canonical
    expected_trip_title = canonical["document"]["trip"]["title"]
    storage = R2Storage()
    old_key, new_key, gallery_key = "vietnam/e2e/old-hero.png", "vietnam/e2e/new-hero.png", "vietnam/e2e/gallery-hero.png"
    # Minimal valid PNG bytes: release validation must HEAD real R2 objects.
    png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cfc0000003010185c3e21b0000000049454e44ae426082")
    storage.upload_bytes(old_key, png, "image/png")
    storage.upload_bytes(new_key, png, "image/png")
    storage.upload_bytes(gallery_key, png, "image/png")
    register_e2e_media([old_key, new_key, gallery_key])
    status, facts_media = request_json(
        f"/api/v2/quotations/{quotation_id}/facts/media?lang=en",
        method="PUT",
        payload={"baseRevision": revision, "slots": [
            {"fieldId": "assets.hero", "value": {"r2Key": old_key, "altText": "E2E Hanoi hero"}},
            {"fieldId": "itinerary.days.0.gallery", "value": [{"r2Key": old_key}, {"r2Key": new_key}, {"r2Key": gallery_key}]},
            {"fieldId": "stays.hotels.0.hotelImage", "value": {"r2Key": old_key}},
            {"fieldId": "stays.hotels.0.roomImage", "value": {"r2Key": gallery_key}},
        ]},
    )
    assert status == 200, facts_media
    revision = facts_media["currentRevision"]
    design_base_revision = revision
    status, design_saved = request_json(
        f"/api/v2/quotations/{quotation_id}/presentation/overrides?lang=en",
        method="PUT",
        payload={
            "baseRevision": revision,
            "copyOverrides": {"a11y.interactiveRouteMap": "E2E interactive route map"},
            "identityOverrides": {},
        },
    )
    assert status == 200, design_saved
    revision = design_saved["currentRevision"]
    status, stale_design = request_json(
        f"/api/v2/quotations/{quotation_id}/presentation/overrides?lang=en",
        method="PUT",
        payload={
            "baseRevision": design_base_revision,
            "copyOverrides": {"a11y.interactiveRouteMap": "stale write must not persist"},
            "identityOverrides": {},
        },
    )
    assert status == 409 and stale_design.get("detail", {}).get("currentRevision") == revision, stale_design
    status, retried_design = request_json(
        f"/api/v2/quotations/{quotation_id}/presentation/overrides?lang=en",
        method="PUT",
        payload={
            "baseRevision": revision,
            "copyOverrides": {"a11y.interactiveRouteMap": "E2E interactive route map, saved after retry"},
            "identityOverrides": {},
        },
    )
    assert status == 200, retried_design
    revision = retried_design["currentRevision"]
    status, design_reload = request_json(f"/api/v2/quotations/{quotation_id}/document?lang=en")
    assert status == 200 and design_reload["document"]["presentation"]["copyOverrides"]["a11y.interactiveRouteMap"] == "E2E interactive route map, saved after retry", design_reload

    # Content opens without automatic generation; selection remains URL-owned.
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        generated_requests: list[str] = []
        page.on("request", lambda request: generated_requests.append(request.url) if request.method == "POST" and "/content-drafts" in request.url else None)
        page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=content&section=hero&lang=en", wait_until="networkidle")
        expect(page).to_have_url(f"{EDITOR_BASE}/workspace/quotations/{quotation_id}/edit?stage=content&section=hero&lang=en")
        expect(page.get_by_text("Quotation Studio")).to_be_visible()
        expect(page.get_by_text("CONTENT STUDIO")).to_be_visible()
        expect(page.get_by_text("Writing instruction", exact=True)).to_be_visible()
        assert not generated_requests, generated_requests
        screenshot(page, "content-studio-desktop.png")
        page.goto(f"{EDITOR_BASE}/quotations/{quotation_id}/workspace?stage=design&lang=en", wait_until="networkidle")
        expect(page).to_have_url(f"{EDITOR_BASE}/workspace/quotations/{quotation_id}/edit?stage=design&lang=en")
        expect(page.get_by_text("Select an element on the brochure.")).to_be_visible()
        editable = page.locator('[data-edit-owner="design"]').first
        editable.click()
        editable.evaluate("element => { element.setAttribute('tabindex', '0'); element.focus(); }")
        page.keyboard.press("Enter")
        expect(page.get_by_text("Select an element on the brochure.")).not_to_be_visible()
        expect(page.get_by_text("Presentation copy")).to_be_visible()
        screenshot(page, "design-canvas-desktop.png")
        browser.close()

    status, published = request_json(
        f"/api/v2/quotations/{quotation_id}/publish?lang=en",
        method="POST",
        payload={"baseRevision": revision, "brandId": "capella_travel"},
    )
    assert status == 202, published
    wait_for_job(published["jobId"])
    EVIDENCE.update({"revision": revision, "releaseId": published["releaseId"], "pdfUrl": f"{published['published_url']}/pdf/download"})
    public_path = urlparse(published["published_url"]).path
    capella_base = PUBLIC_BASES["capella_travel"]

    # Anonymous public host must SSR React and expose its current PDF only.
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        response = page.goto(f"{capella_base}{public_path}", wait_until="networkidle")
        assert response and response.status == 200
        expect(page.get_by_role("heading", name=expected_trip_title, exact=True)).to_be_visible()
        screenshot(page, "public-desktop.png")
        pdf = page.request.get(f"{capella_base}{public_path}/pdf/download")
        assert pdf.status == 200
        assert pdf.headers.get("content-type", "").startswith("application/pdf")
        pdf_bytes = pdf.body()
        assert pdf_bytes.startswith(b"%PDF"), "PDF endpoint did not return a binary PDF"
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        assert len(pdf_reader.pages) >= 1
        assert expected_trip_title in "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
        (ARTIFACT_DIR / "public-brochure.pdf").write_bytes(pdf_bytes)
        media = page.request.get(run_sync(release_media_url(published["releaseId"], capella_base)))
        assert media.status == 200
        assert media.headers.get("cache-control", "").startswith("public, max-age=31536000")
        assert page.request.get(f"{capella_base}/api/v2/brands").status == 404
        assert page.request.get(f"{capella_base}/internal/releases/{published['releaseId']}/pdf").status == 404
        browser.close()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for width, name in ((980, "public-980.png"), (480, "public-mobile.png")):
            page = browser.new_page(viewport={"width": width, "height": 1000})
            response = page.goto(f"{capella_base}{public_path}", wait_until="networkidle")
            assert response and response.status == 200
            screenshot(page, name)
        browser.close()

    # The same canonical document can publish through a second active brand.
    status, selvara = request_json(
        f"/api/v2/quotations/{quotation_id}/publish?lang=en",
        method="POST",
        payload={"baseRevision": revision, "brandId": "selvara"},
    )
    assert status == 202, selvara
    wait_for_job(selvara["jobId"])
    selvara_path = urlparse(selvara["published_url"]).path
    selvara_base = PUBLIC_BASES["selvara"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        response = page.goto(f"{selvara_base}{selvara_path}", wait_until="networkidle")
        assert response and response.status == 200
        expect(page.get_by_role("heading", name=expected_trip_title, exact=True)).to_be_visible()
        assert page.request.get(run_sync(release_media_url(selvara["releaseId"], selvara_base))).status == 200
        browser.close()

    status, facts_media = request_json(
        f"/api/v2/quotations/{quotation_id}/facts/media?lang=en",
        method="PUT",
        payload={"baseRevision": revision, "slots": [{"fieldId": "assets.hero", "value": {"r2Key": new_key, "altText": "Updated E2E Hanoi hero"}}]},
    )
    assert status == 200, facts_media
    revision = facts_media["currentRevision"]
    status, republished = request_json(
        f"/api/v2/quotations/{quotation_id}/publish?lang=en",
        method="POST",
        payload={"baseRevision": revision, "brandId": "capella_travel"},
    )
    assert status == 202, republished
    wait_for_job(republished["jobId"])
    purge_urls = run_sync(purge_urls_for_release(republished["releaseId"]))
    assert any(f"/media/{published['releaseId']}/" in url for url in purge_urls), purge_urls
    assert any(f"/media/{republished['releaseId']}/" in url for url in purge_urls), purge_urls

    # Restore produces a new current release pointer while preserving the target URL.
    status, publications = request_json(f"/api/v2/quotations/{quotation_id}/publications?lang=en")
    assert status == 200, publications
    capella_target = next(item for item in publications["publications"] if item["brandId"] == "capella_travel")
    status, restored = request_json(
        f"/api/v2/quotations/{quotation_id}/publication-targets/{capella_target['targetId']}/releases/1/restore",
        method="POST",
        payload={},
    )
    assert status == 200, restored
    status, unpublished = request_json(
        f"/api/v2/quotations/{quotation_id}/publication-targets/{next(item for item in publications['publications'] if item['brandId'] == 'selvara')['targetId']}/unpublish",
        method="POST",
        payload={},
    )
    assert status == 200, unpublished
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        selvara_response = page.request.get(f"{selvara_base}{selvara_path}")
        capella_response = page.request.get(f"{capella_base}{public_path}")
        assert selvara_response.status == 404, f"Unpublished Selvara route returned {selvara_response.status}"
        assert capella_response.status == 200, f"Restored Capella route returned {capella_response.status}"
        browser.close()

    # Disabling a brand invalidates its public route even when a release exists.
    status, brands = request_json("/api/v2/brands")
    assert status == 200, brands
    capella_brand = next(item for item in brands["brands"] if item["id"] == "capella_travel")
    status, disabled = request_json(
        "/api/v2/brands/capella_travel",
        method="PUT",
        payload={
            "displayName": capella_brand["displayName"],
            "hostname": capella_brand["hostname"],
            "status": "disabled",
            "logoAssetKey": capella_brand.get("logoAssetKey"),
            "sellerProfile": capella_brand.get("sellerProfile") or {},
            "renderProfile": capella_brand["renderProfile"],
        },
    )
    assert status == 200 and disabled["status"] == "disabled", disabled
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        disabled_response = page.request.get(f"{capella_base}{public_path}")
        assert disabled_response.status == 404, f"Disabled brand public route returned {disabled_response.status}"
        browser.close()

    save_evidence(status="passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        save_evidence(status="failed", error=str(exc))
        raise
