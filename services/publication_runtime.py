"""Infrastructure runtime used by publication routes and the worker.

Keeping these functions outside ``main`` prevents workers from importing the
ASGI composition root just to render or purge a release.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request
from typing import Any

log = logging.getLogger(__name__)


def render_react_pdf_bytes(*, hostname: str, release_id: str) -> bytes:
    """Render the immutable private React release route to an A4 PDF."""
    del hostname  # Release resolution is intentionally ID-based.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright/Chromium is not installed.") from exc
    origin = os.getenv("QUOTE_GENERATOR_INTERNAL_URL", "http://quote-generator:8115").rstrip("/")
    with sync_playwright() as browser_runtime:
        browser = browser_runtime.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(f"{origin}/internal/releases/{release_id}/pdf", wait_until="networkidle", timeout=60_000)
            page.wait_for_selector('[data-render-ready="true"]', state="attached", timeout=15_000)
            return page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
        finally:
            browser.close()


def release_cache_urls(*, hostname: str, target: Any, release: Any) -> list[str]:
    base = f"https://{hostname}/{target.locale}/q/{target.public_slug}"
    urls = [base, f"{base}/pdf/download"]
    urls.extend(f"https://{hostname}/media/{release.id}/{token}" for token in (release.asset_manifest or {}))
    return urls


def fallback_release_cache_urls(*, fallback_hostname: str, target: Any, release: Any) -> list[str]:
    slug = getattr(target, "fallback_slug", None) or target.public_slug
    base = f"https://{fallback_hostname}/p/{slug}"
    urls = [base, f"{base}/pdf/download"]
    urls.extend(f"https://{fallback_hostname}/media/{release.id}/{token}" for token in (release.asset_manifest or {}))
    return urls


def release_transition_cache_urls(
    *, hostnames: list[str], target: Any, releases: list[Any | None], fallback_hostname: str,
) -> list[str]:
    return sorted({
        url
        for hostname in hostnames
        for release in releases
        if release is not None
        for url in [
            *release_cache_urls(hostname=hostname, target=target, release=release),
            *fallback_release_cache_urls(fallback_hostname=fallback_hostname, target=target, release=release),
        ]
    })


async def purge_public_urls(urls: str | list[str]) -> None:
    files = [urls] if isinstance(urls, str) else sorted(set(urls))
    if not files:
        return
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID", "")
    token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    if not zone_id or not token:
        raise RuntimeError("Cloudflare cache purge credentials are not configured.")
    request = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache",
        data=json.dumps({"files": files}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        response = await asyncio.to_thread(urllib.request.urlopen, request, timeout=10)
        if not json.loads(response.read().decode("utf-8")).get("success"):
            raise RuntimeError("Cloudflare cache purge rejected the request.")
    except Exception as exc:
        log.exception("Cloudflare cache purge failed for %s", files)
        raise RuntimeError("Cloudflare cache purge failed") from exc
