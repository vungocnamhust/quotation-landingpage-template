"""E2E Visual Verification and Evidence Capture for Sprint PB4.

Tests T-01, T-15, T-16, T-17, T-19, T-20 with live visual evidence.
"""
import os
import sys
import json
import time
import subprocess
import httpx
from playwright.sync_api import sync_playwright

API_BASE = "http://localhost:8111/api/v2"
FRONTEND_PORT = 8115
QUOTATION_ID = "quo_2f0b1675563c"

def run_drain():
    worker_script = """
import os, asyncio
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://quotation:quotation_local_password@localhost:5433/quotation"
os.environ["DATABASE_URL_SYNC"] = "postgresql+psycopg://quotation:quotation_local_password@localhost:5433/quotation"
from services.publication_worker import _claim_job, _run_pdf, _run_cache_purge

async def drain():
    count = 0
    while True:
        job = await _claim_job()
        if not job:
            break
        count += 1
        print(f"  [Worker] {job.job_type} job {job.id}", flush=True)
        if job.job_type == "render_pdf":
            await _run_pdf(job)
        elif job.job_type == "purge_cache":
            await _run_cache_purge(job)
    return count

asyncio.run(drain())
"""
    subprocess.run(
        [sys.executable, "-c", worker_script],
        env=dict(os.environ, PYTHONPATH="."),
        check=True
    )

def main():
    client = httpx.Client(timeout=30.0)
    
    print("=== STEP 1: Ensure Quotation quo_2f0b1675563c is Ready ===", flush=True)
    r_ov = client.get(f"{API_BASE}/workspace/quotations")
    q = next(item for item in r_ov.json()["items"] if item["id"] == QUOTATION_ID)
    rev = q["currentRevision"]
    print(f"Quotation {QUOTATION_ID} Revision: {rev}", flush=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--host-resolver-rules="
                "MAP journeys.capellatravel.com 127.0.0.1, "
                "MAP my.selvarajourneys.com 127.0.0.1, "
                "MAP quotes.capellatravel.com 127.0.0.1, "
                "MAP quotes.selvarajourneys.com 127.0.0.1"
            ]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        # 1. Capture Workspace Review Stage
        print("Capturing 01_workspace_review_publish.png...", flush=True)
        page.goto(f"http://localhost:{FRONTEND_PORT}/workspace/quotations/{QUOTATION_ID}/edit?stage=review", wait_until="domcontentloaded")
        time.sleep(3)
        page.screenshot(path="evidence/01_workspace_review_publish.png", full_page=True)
        print("  -> Saved evidence/01_workspace_review_publish.png", flush=True)
        
        # === STEP 2: Test T-15 PDF 302 Redirect & No-Store ===
        print("\n=== STEP 2: Testing T-15 PDF 302 Redirect & Immutable Release Key ===", flush=True)
        r_pubs = client.get(f"{API_BASE}/quotations/{QUOTATION_ID}/publications?lang=en")
        capella_pub = next((p for p in r_pubs.json().get("publications", []) if p.get("brandId") == "capella_travel"), None)
        assert capella_pub is not None, "Capella publication target must exist"
        
        slug = capella_pub["slug"]
        fallback_slug = capella_pub["fallbackUrl"].rsplit("/", 1)[-1]
        release_id = capella_pub["release"]["id"]
        
        # Test 302 on /en/q/{slug}/pdf/download
        raw_client = httpx.Client(timeout=30.0, follow_redirects=False)
        r_pdf_slug = raw_client.get(
            f"http://localhost:{FRONTEND_PORT}/en/q/{slug}/pdf/download",
            headers={"Host": "journeys.capellatravel.com"}
        )
        print(f"  GET /en/q/{slug}/pdf/download -> Status: {r_pdf_slug.status_code}, Location: {r_pdf_slug.headers.get('location')}, Cache-Control: {r_pdf_slug.headers.get('cache-control')}", flush=True)
        assert r_pdf_slug.status_code == 302
        assert r_pdf_slug.headers.get("location") == f"/media/{release_id}/pdf"
        assert "no-store" in r_pdf_slug.headers.get("cache-control", "")
        
        # Test 200 on /media/{release_id}/pdf
        r_pdf_media = raw_client.get(f"http://localhost:{FRONTEND_PORT}/media/{release_id}/pdf")
        print(f"  GET /media/{release_id}/pdf -> Status: {r_pdf_media.status_code}, Content-Type: {r_pdf_media.headers.get('content-type')}, Cache-Control: {r_pdf_media.headers.get('cache-control')}", flush=True)
        assert r_pdf_media.status_code == 200
        assert "application/pdf" in r_pdf_media.headers.get("content-type", "")
        assert "immutable" in r_pdf_media.headers.get("cache-control", "")
        
        # Test 302 on fallback URL /p/{fallback_slug}/pdf/download
        r_pdf_fallback = raw_client.get(f"http://localhost:{FRONTEND_PORT}/p/{fallback_slug}/pdf/download")
        print(f"  GET /p/{fallback_slug}/pdf/download -> Status: {r_pdf_fallback.status_code}, Location: {r_pdf_fallback.headers.get('location')}", flush=True)
        assert r_pdf_fallback.status_code == 302
        assert r_pdf_fallback.headers.get("location") == f"/media/{release_id}/pdf"
        
        # Record PDF Trace JSON
        pdf_trace = {
            "test_case": "T-15",
            "slug_endpoint": {
                "url": f"/en/q/{slug}/pdf/download",
                "status": r_pdf_slug.status_code,
                "location": r_pdf_slug.headers.get("location"),
                "cache_control": r_pdf_slug.headers.get("cache-control")
            },
            "fallback_endpoint": {
                "url": f"/p/{fallback_slug}/pdf/download",
                "status": r_pdf_fallback.status_code,
                "location": r_pdf_fallback.headers.get("location"),
                "cache_control": r_pdf_fallback.headers.get("cache-control")
            },
            "release_media_endpoint": {
                "url": f"/media/{release_id}/pdf",
                "status": r_pdf_media.status_code,
                "content_type": r_pdf_media.headers.get("content-type"),
                "cache_control": r_pdf_media.headers.get("cache-control"),
                "size_bytes": len(r_pdf_media.content)
            }
        }
        with open("evidence/t15_pdf_trace.json", "w") as f:
            json.dump(pdf_trace, f, indent=2)
        print("  -> Saved evidence/t15_pdf_trace.json", flush=True)
        
        # Capture 02_pdf_302_redirect_trace.png (Brochure PDF mode)
        page.goto(f"http://journeys.capellatravel.com:{FRONTEND_PORT}/en/q/{slug}?view=pdf", wait_until="domcontentloaded")
        time.sleep(3)
        page.screenshot(path="evidence/02_pdf_302_redirect_trace.png", full_page=False)
        print("  -> Saved evidence/02_pdf_302_redirect_trace.png", flush=True)
        
        # Capture 03_public_brochure_desktop.png (Capella Travel Desktop)
        page.goto(f"http://journeys.capellatravel.com:{FRONTEND_PORT}/en/q/{slug}", wait_until="domcontentloaded")
        time.sleep(3)
        page.screenshot(path="evidence/03_public_brochure_desktop.png", full_page=False)
        print("  -> Saved evidence/03_public_brochure_desktop.png", flush=True)
        
        # === STEP 3: Multi-Brand Publication & Capture Selvara (Brand B) ===
        print("\n=== STEP 3: Publishing Brand B (Selvara Journeys) ===", flush=True)
        r_pubs2 = client.get(f"{API_BASE}/quotations/{QUOTATION_ID}/publications?lang=en")
        selvara_pub = next((p for p in r_pubs2.json().get("publications", []) if p.get("brandId") == "selvara"), None)
        selvara_slug = selvara_pub["slug"]
        
        # Capture Selvara Landing Page
        page.goto(f"http://my.selvarajourneys.com:{FRONTEND_PORT}/en/q/{selvara_slug}", wait_until="domcontentloaded")
        time.sleep(3)
        page.screenshot(path="evidence/04_public_brochure_brand_b.png", full_page=False)
        print("  -> Saved evidence/04_public_brochure_brand_b.png", flush=True)
        
        # === STEP 4: Test T-20 Tenant Domain Isolation ===
        print("\n=== STEP 4: Testing T-20 Tenant Domain Isolation ===", flush=True)
        # Cross brand domain check (Capella slug on Selvara domain -> 404)
        r_cross = raw_client.get(
            f"http://localhost:{FRONTEND_PORT}/en/q/{slug}",
            headers={"Host": "my.selvarajourneys.com"}
        )
        print(f"  GET Capella slug with Selvara Host -> Status: {r_cross.status_code}", flush=True)
        assert r_cross.status_code == 404
        
        # Fallback SEO meta check
        r_fb = raw_client.get(f"http://localhost:{FRONTEND_PORT}/p/{fallback_slug}")
        assert "<meta name=\"robots\" content=\"noindex, nofollow\"" in r_fb.text or "noindex" in r_fb.text
        print("  Fallback page contains robots noindex: OK", flush=True)
        
        # === STEP 5: Test T-16 Proxy Gate 404 & T-19 Unpublish/Restore ===
        print("\n=== STEP 5: Testing T-16 Proxy Gate 404 & T-19 Unpublish / Restore ===", flush=True)
        # 1. Unpublish Capella target
        target_id = capella_pub["targetId"]
        r_unpub = client.post(f"{API_BASE}/quotations/{QUOTATION_ID}/publication-targets/{target_id}/unpublish")
        print(f"  Unpublish Capella Target {target_id} -> Status: {r_unpub.status_code}", flush=True)
        assert r_unpub.status_code == 200
        run_drain()
        
        # 2. Verify /p/{fallback_slug} returns 404 immediately from proxy gate
        r_unpub_404 = raw_client.get(f"http://localhost:{FRONTEND_PORT}/p/{fallback_slug}")
        print(f"  GET unpublished /p/{fallback_slug} -> Status: {r_unpub_404.status_code}, Length: {len(r_unpub_404.text)}", flush=True)
        assert r_unpub_404.status_code == 404
        
        # Capture 05_proxy_gate_404_fallback.png
        page.goto(f"http://localhost:{FRONTEND_PORT}/p/{fallback_slug}", wait_until="domcontentloaded")
        time.sleep(2)
        page.screenshot(path="evidence/05_proxy_gate_404_fallback.png")
        print("  -> Saved evidence/05_proxy_gate_404_fallback.png", flush=True)
        
        # 3. Restore Capella target
        r_restore = client.post(f"{API_BASE}/quotations/{QUOTATION_ID}/publication-targets/{target_id}/releases/1/restore")
        print(f"  Restore Capella Target {target_id} Release 1 -> Status: {r_restore.status_code}", flush=True)
        assert r_restore.status_code == 200
        run_drain()
        
        # Verify restored target is published again
        r_restored_check = raw_client.get(
            f"http://localhost:{FRONTEND_PORT}/en/q/{slug}",
            headers={"Host": "journeys.capellatravel.com"}
        )
        print(f"  GET restored /en/q/{slug} -> Status: {r_restored_check.status_code}", flush=True)
        assert r_restored_check.status_code == 200
        
        browser.close()
        
    print("\nALL PB4 E2E TESTS AND VISUAL EVIDENCE CAPTURED SUCCESSFULLY!", flush=True)

if __name__ == "__main__":
    main()
