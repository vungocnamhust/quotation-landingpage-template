"""
GitHub publish service — commits an HTML file to the repo's published/ folder.
Vercel auto-redeploys on each new commit.
"""
from dotenv import load_dotenv
import base64
import logging
import os
import httpx

log = logging.getLogger("quotation.github")

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "")   # e.g. "vungocnamhust/quotation-landingpage-template"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

GITHUB_API = "https://api.github.com"


def _get_next_version_local(quotation_id: str) -> int:
    import glob
    existing = glob.glob(os.path.join("published", quotation_id, "v*.html"))
    versions = [1]
    for f in existing:
        name = os.path.basename(f)
        if name.endswith(".html"):
            name_no_ext = name[:-5]
            base_name = name_no_ext.split("_")[0]
            if base_name.startswith("v") and base_name[1:].isdigit():
                versions.append(int(base_name[1:]) + 1)
    return max(versions)


async def get_next_version(quotation_id: str) -> int:
    """
    Fetch the contents of the published/{quotation_id} directory from GitHub API
    and return the next version number. This ensures cross-instance accuracy on Vercel.
    """
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT != "production" or not GITHUB_TOKEN or not GITHUB_REPO:
        return _get_next_version_local(quotation_id)

    api_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/published/{quotation_id}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "quotation-landingpage/1.0",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(api_url, headers=headers)
        
        if resp.status_code == 200:
            files = resp.json()
            if isinstance(files, list):
                versions = [1]
                for f in files:
                    name = f.get("name", "")
                    if name.endswith(".html"):
                        name_no_ext = name[:-5]
                        base_name = name_no_ext.split("_")[0]
                        if base_name.startswith("v") and base_name[1:].isdigit():
                            versions.append(int(base_name[1:]) + 1)
                return max(versions)
                
    return _get_next_version_local(quotation_id)



async def _put_github_file(
    api_url: str,
    headers: dict,
    encoded_content: str,
    commit_message: str,
    *,
    max_retries: int = 2,
) -> dict:
    """
    PUT a file to GitHub, handling 409 SHA-mismatch conflicts with automatic retry.
    On 409, re-fetches the current SHA and retries up to max_retries times.
    """
    async with httpx.AsyncClient(timeout=20) as client:
        for attempt in range(1, max_retries + 1):
            # Always fetch the latest SHA before each attempt
            existing_sha: str | None = None
            check = await client.get(api_url, headers=headers)
            if check.status_code == 200:
                existing_sha = check.json().get("sha")
                log.debug("[github] Attempt %d: file exists sha=%s", attempt, existing_sha)

            body: dict = {"message": commit_message, "content": encoded_content}
            if existing_sha:
                body["sha"] = existing_sha

            resp = await client.put(api_url, headers=headers, json=body)

            if resp.status_code in (200, 201):
                return resp.json()

            if resp.status_code == 409 and attempt < max_retries:
                log.warning(
                    "[github] 409 SHA conflict on attempt %d — re-fetching SHA and retrying.",
                    attempt,
                )
                continue  # retry with fresh SHA

            # Unrecoverable error
            log.error("[github] Commit failed %s: %s", resp.status_code, resp.text[:400])
            raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text[:200]}")

    raise RuntimeError("GitHub PUT failed after all retries.")  # should never reach


async def publish_to_github(quotation_id: str, html_content: str, version: int, lang: str = None, baseline_lang: str = "en") -> str:
    """
    Commit published/{quotation_id}/v{version}.html (or language specific suffix) to the GitHub repo.
    Returns the public Vercel URL of the published page.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise ValueError("GITHUB_TOKEN and GITHUB_REPO must be set in environment.")

    lang_suffix = f"_{lang}" if lang and lang != baseline_lang else ""
    filename  = f"v{version}{lang_suffix}.html"
    file_path = f"published/{quotation_id}/{filename}"
    api_url   = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{file_path}"
    headers   = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "quotation-landingpage/1.0",
    }
    encoded = base64.b64encode(html_content.encode("utf-8")).decode("ascii")

    await _put_github_file(
        api_url, headers, encoded,
        commit_message=f"Publish quotation {quotation_id} {filename}",
    )

    public_url = f"{PUBLIC_BASE_URL}/published/{quotation_id}/{filename}"
    log.info("[github] ✓ Committed %s → %s", file_path, public_url)
    return public_url



async def publish_file_to_github(
    file_path: str,
    html_content: str | bytes,
    commit_message: str,
) -> str:
    """
    Generic helper: commit any file to GitHub at the given file_path.
    Returns its public Vercel CDN URL.
    Used for publishing pdf.html alongside v{n}.html.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise ValueError("GITHUB_TOKEN and GITHUB_REPO must be set in environment.")

    api_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "quotation-landingpage/1.0",
    }
    raw_bytes = html_content if isinstance(html_content, bytes) else html_content.encode("utf-8")
    encoded = base64.b64encode(raw_bytes).decode("ascii")

    await _put_github_file(api_url, headers, encoded, commit_message=commit_message)

    public_url = f"{PUBLIC_BASE_URL}/{file_path}"
    log.info("[github] ✓ Committed %s → %s", file_path, public_url)
    return public_url
