"""
GitHub publish service — commits an HTML file to the repo's published/ folder.
Vercel auto-redeploys on each new commit.
"""
import base64
import logging
import os
import httpx

log = logging.getLogger("quotation.github")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "")   # e.g. "vungocnamhust/quotation-landingpage-template"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

GITHUB_API = "https://api.github.com"


async def publish_to_github(quotation_id: str, html_content: str, version: int) -> str:
    """
    Commit published/{quotation_id}_v{version}.html to the GitHub repo.
    Returns the public Vercel URL of the published page.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise ValueError("GITHUB_TOKEN and GITHUB_REPO must be set in environment.")

    filename = f"{quotation_id}_v{version}.html"
    file_path = f"published/{filename}"
    api_url   = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{file_path}"
    headers   = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "quotation-landingpage/1.0",
    }

    encoded = base64.b64encode(html_content.encode("utf-8")).decode("ascii")

    # Check if file already exists (needed to supply sha for updates)
    existing_sha: str | None = None
    async with httpx.AsyncClient(timeout=20) as client:
        check = await client.get(api_url, headers=headers)
        if check.status_code == 200:
            existing_sha = check.json().get("sha")
            log.info("[github] File exists (sha=%s), will update.", existing_sha)

        body: dict = {
            "message": f"Publish quotation {quotation_id} v{version}",
            "content": encoded,
        }
        if existing_sha:
            body["sha"] = existing_sha

        resp = await client.put(api_url, headers=headers, json=body)

    if resp.status_code not in (200, 201):
        log.error("[github] Commit failed %s: %s", resp.status_code, resp.text[:400])
        raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text[:200]}")

    public_url = f"{PUBLIC_BASE_URL}/published/{filename}"
    log.info("[github] ✓ Committed %s → %s", file_path, public_url)
    return public_url
