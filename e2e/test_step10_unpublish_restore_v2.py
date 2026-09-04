"""Focused E2E proof for Step 10:
Restore release, Unpublish target, Disable brand, and verify public 404 responses.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import copy
import json
import os
import time
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models.publication import PublicationJob, PublicationRelease
from repositories.travel_designer_repository import TravelDesignerRepository
from scripts.create_test_v2_quotation import create_sample_quote_request
from services.storage.r2_storage import R2Storage


API_BASE = os.environ["E2E_API_BASE_URL"].rstrip("/")
EDITOR_BASE = os.environ["E2E_EDITOR_BASE_URL"].rstrip("/")
PUBLIC_BASES = {
    "capella_travel": os.environ["E2E_CAPELLA_PUBLIC_BASE_URL"].rstrip("/"),
    "selvara": os.environ["E2E_SELVARA_PUBLIC_BASE_URL"].rstrip("/"),
}


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


def canonicalize_catalog_names(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: canonicalize_catalog_names(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonicalize_catalog_names(item) for item in value]
    return "Ha Long Bay" if value == "Halong Bay" else value


def apply_required_content(
    quotation_id: str,
    *,
    lang: str,
    revision: int,
    itinerary: list[dict[str, Any]],
) -> int:
    scopes = ["hero", "overview_letter", "route", "itinerary"]
    scopes.extend(f"itinerary:day:{item['day_number']}" for item in itinerary)
    for scope in scopes:
        status, created = request_json(
            f"/api/v2/quotations/{quotation_id}/content-drafts?lang={lang}",
            method="POST",
            payload={"scopes": [scope], "generationMode": "storytelling"},
        )
        assert status == 200, created
        drafts = created.get("drafts") or []
        assert len(drafts) == 1, created
        status, applied = request_json(
            f"/api/v2/quotations/{quotation_id}/content-drafts/{drafts[0]['id']}/apply",
            method="POST",
            payload={"baseRevision": revision},
        )
        assert status == 200, applied
        revision = applied["currentRevision"]
    return revision


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


def ensure_default_travel_designer() -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(lambda: asyncio.run(_ensure_default_travel_designer())).result()


def main() -> None:
    print("[E2E STEP 10] Starting Step 10 isolation test...")
    wait_for_api()
    ensure_default_travel_designer()

    # 1. Fast-forward creation & publication for Capella & Selvara
    payload = canonicalize_catalog_names(create_sample_quote_request())
    payload["brand_id"] = "capella_travel"
    payload["opportunity_id"] = "E2E-STEP10-ISOLATION"
    status, created = request_json("/api/v2/quotations", method="POST", payload=payload)
    assert status == 200, created
    quotation_id = created["quotationId"]
    revision = created["currentRevision"]
    revision = apply_required_content(
        quotation_id,
        lang="en",
        revision=revision,
        itinerary=payload["trip_facts"]["itinerary"],
    )

    storage = R2Storage()
    old_key, new_key = "vietnam/e2e/step10-old-hero.png", "vietnam/e2e/step10-new-hero.png"
    png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cfc0000003010185c3e21b0000000049454e44ae426082")
    storage.upload_bytes(old_key, png, "image/png")
    storage.upload_bytes(new_key, png, "image/png")

    # Presentation v1
    status, presentation = request_json(
        f"/api/v2/quotations/{quotation_id}/presentation?lang=en",
        method="PUT",
        payload={"baseRevision": revision, "themeId": "brochure", "layoutVersion": 1, "heroR2Key": old_key},
    )
    assert status == 200, presentation
    revision = presentation["currentRevision"]

    # Publish Capella Release 1
    status, capella_v1 = request_json(
        f"/api/v2/quotations/{quotation_id}/publish?lang=en",
        method="POST",
        payload={"baseRevision": revision, "brandId": "capella_travel"},
    )
    assert status == 202, capella_v1
    wait_for_job(capella_v1["jobId"])
    public_path = urlparse(capella_v1["published_url"]).path
    capella_base = PUBLIC_BASES["capella_travel"]

    # Publish Selvara
    status, selvara = request_json(
        f"/api/v2/quotations/{quotation_id}/publish?lang=en",
        method="POST",
        payload={"baseRevision": revision, "brandId": "selvara"},
    )
    assert status == 202, selvara
    wait_for_job(selvara["jobId"])
    selvara_path = urlparse(selvara["published_url"]).path
    selvara_base = PUBLIC_BASES["selvara"]

    # Update Presentation & Publish Capella Release 2
    status, presentation = request_json(
        f"/api/v2/quotations/{quotation_id}/presentation?lang=en",
        method="PUT",
        payload={"baseRevision": revision, "themeId": "brochure", "layoutVersion": 1, "heroR2Key": new_key},
    )
    assert status == 200, presentation
    revision = presentation["currentRevision"]
    status, capella_v2 = request_json(
        f"/api/v2/quotations/{quotation_id}/publish?lang=en",
        method="POST",
        payload={"baseRevision": revision, "brandId": "capella_travel"},
    )
    assert status == 202, capella_v2
    wait_for_job(capella_v2["jobId"])

    print("[E2E STEP 10] Pre-requisite state ready. Testing Step 10 assertions...")

    # EXECUTE STEP 10 ASSERTIONS
    # A) Restore Capella Release 1
    status, publications = request_json(f"/api/v2/quotations/{quotation_id}/publications?lang=en")
    assert status == 200, publications
    capella_target = next(item for item in publications["publications"] if item["brandId"] == "capella_travel")
    status, restored = request_json(
        f"/api/v2/quotations/{quotation_id}/publication-targets/{capella_target['targetId']}/releases/1/restore",
        method="POST",
        payload={},
    )
    assert status == 200 and restored["release"] == 1, restored
    print("[E2E STEP 10] ✓ Capella release 1 restored successfully")

    # B) Unpublish Selvara target
    selvara_target = next(item for item in publications["publications"] if item["brandId"] == "selvara")
    status, unpublished = request_json(
        f"/api/v2/quotations/{quotation_id}/publication-targets/{selvara_target['targetId']}/unpublish",
        method="POST",
        payload={},
    )
    assert status == 200 and unpublished["status"] == "unpublished", unpublished
    print("[E2E STEP 10] ✓ Selvara target unpublished successfully")

    # Verify Selvara public route -> 404, Capella public route -> 200
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        assert page.request.get(f"{selvara_base}{selvara_path}").status == 404
        assert page.request.get(f"{capella_base}{public_path}").status == 200
        browser.close()
    print("[E2E STEP 10] ✓ Selvara route returns 404 and Capella route returns 200")

    # C) Disable Capella brand and verify public route -> 404
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
    print("[E2E STEP 10] ✓ Capella brand status updated to disabled")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        assert page.request.get(f"{capella_base}{public_path}").status == 404
        browser.close()
    print("[E2E STEP 10] ✓ Capella route returns 404 when brand is disabled")

    # Cleanup: restore Capella brand status back to active
    request_json(
        "/api/v2/brands/capella_travel",
        method="PUT",
        payload={
            "displayName": capella_brand["displayName"],
            "hostname": capella_brand["hostname"],
            "status": "active",
            "logoAssetKey": capella_brand.get("logoAssetKey"),
            "sellerProfile": capella_brand.get("sellerProfile") or {},
            "renderProfile": capella_brand["renderProfile"],
        },
    )
    print("[E2E STEP 10] 🎉 Step 10 test suite COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
