import uuid
import json
import logging
import os
import asyncio
from functools import partial
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from datetime import date
from github_publish import publish_to_github, publish_file_to_github
from image_selector import select_landing_image

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("quotation")

app = FastAPI(title="Quotation Webhook API")

# CORS — required for ChatGPT Custom GPT Actions to reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/published", StaticFiles(directory="published"), name="published")

# Jinja2 templates
templates = Jinja2Templates(directory="templates")

# ── In-memory quotation store ─────────────────────────────────────────────────
# { quotation_id: { "payload": dict, "html": str, "status": str,
#                   "published_url": str|None, "version": int } }
quotations: dict[str, dict] = {}

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8001")


# ── Debug middleware — logs every incoming request and response ──────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start = time.monotonic()

    # Log request headers for ALL methods
    log.debug(
        "→ REQUEST  %s %s  headers=%s",
        request.method,
        request.url,
        dict(request.headers),
    )

    if request.method in ("POST", "PUT", "PATCH"):
        body_bytes = await request.body()

        # Log raw body
        if body_bytes:
            try:
                body_json = json.loads(body_bytes)
                log.debug(
                    "→ BODY [%s %s]:\n%s",
                    request.method,
                    request.url.path,
                    json.dumps(body_json, indent=2, ensure_ascii=False),
                )
            except Exception:
                log.debug("→ BODY (non-JSON, %d bytes): %s", len(body_bytes), body_bytes[:500])
        else:
            log.warning("→ BODY is EMPTY for %s %s — possible middleware body-read issue", request.method, request.url.path)

        # Rebuild receive so FastAPI/Starlette can read the body again.
        # IMPORTANT: must handle both http.request and http.disconnect messages.
        body_consumed = False

        async def receive():
            nonlocal body_consumed
            if not body_consumed:
                body_consumed = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            # Subsequent calls return disconnect so the connection lifecycle ends cleanly
            return {"type": "http.disconnect"}

        request = Request(request.scope, receive)

    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        log.exception("← EXCEPTION after %.0fms for %s %s: %s", elapsed, request.method, request.url.path, exc)
        raise

    elapsed = (time.monotonic() - start) * 1000
    log.info(
        "← RESPONSE %s %s  status=%s  time=%.0fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


# ── Validation error handler — surfaces exact Pydantic field errors ──────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    log.error(
        "VALIDATION ERROR [%s %s] — %d error(s):\n%s",
        request.method,
        request.url.path,
        len(errors),
        json.dumps(errors, indent=2, default=str),
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": errors,
            "hint": "Check the field path in each error's 'loc' to find the missing or invalid field.",
        },
    )


# ── Generic error handler — catches any unhandled exceptions ─────────────────
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    log.exception("UNHANDLED EXCEPTION [%s %s]", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ── Pydantic models — mapped 1:1 from the OpenAPI spec ──────────────────────
# Only fields listed under `required:` in the spec are non-Optional here.

class Customer(BaseModel):
    # required: [name]
    name: str
    contactName: Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    address:     Optional[str] = None
    taxCode:     Optional[str] = None


class Seller(BaseModel):
    # required: [companyName]
    companyName: str
    contactName: Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    address:     Optional[str] = None
    taxCode:     Optional[str] = None


class Item(BaseModel):
    # required: [name, quantity, unitPrice]
    name:           str
    quantity:       float               # number in spec (allows decimals)
    unitPrice:      float
    sku:            Optional[str]   = None
    description:    Optional[str]   = None
    unit:           Optional[str]   = None
    discountAmount: Optional[float] = None
    taxRate:        Optional[float] = None
    lineSubtotal:   Optional[float] = None
    lineTax:        Optional[float] = None
    lineTotal:      Optional[float] = None


class QuotationPayload(BaseModel):
    # required: [quotationDate, currency, customer, items, grandTotal]
    quotationDate:  date
    currency:       str
    customer:       Customer
    items:          List[Item]
    grandTotal:     float
    # all other top-level fields are optional
    quotationNumber: Optional[str]   = None
    validUntil:      Optional[date]  = None
    seller:          Optional[Seller] = None
    subtotal:        Optional[float] = None
    discountTotal:   Optional[float] = None
    taxTotal:        Optional[float] = None
    paymentTerms:    Optional[str]   = None
    deliveryTerms:   Optional[str]   = None
    notes:           Optional[str]   = None
    internalNotes:   Optional[str]   = None
    source:          Optional[str]   = None


# ── Context builder (pure fn — no I/O) ───────────────────────────────────────

def _build_ctx(quotation_id, payload, hero_image_url, destinations: list[dict]):
    """Build template context. Shared by /quotations (landingpage) and /quotations/{id}/pdf."""
    default_img = "/assets/vietnam-safar-logo.png"
    seller = payload.seller
    seller_name  = seller.companyName if seller else "Vietnam Safar \u2013 Discovery Asia Travel Group"
    seller_email = (seller.email if seller else None) or "sales@vietnamsafar.vn"
    seller_phone = (seller.phone if seller else None) or "+84 911 538 738"
    tour_title = payload.quotationNumber or f"{payload.customer.name} \u2013 {payload.currency} {payload.grandTotal:,.0f}"
    
    # destinations list contains dicts with "name", "slug", "image_url"
    def _d_img(i): return destinations[i].get("image_url", default_img) if i < len(destinations) else default_img
    def _d_name(i): return destinations[i].get("name", "") if i < len(destinations) else ""
    
    img_0 = hero_image_url
    img_1 = _d_img(0)
    img_2 = _d_img(1)
    img_3 = _d_img(2)
    img_4 = _d_img(3)
    
    items_list = payload.items
    def _n(i): return items_list[i].name if i < len(items_list) else ""
    raw_notes = payload.notes or ""
    inc_lines, exc_lines = [], []
    for line in raw_notes.splitlines():
        s = line.strip()
        if s.startswith("+"): inc_lines.append(s[1:].strip())
        elif s.startswith("-"): exc_lines.append(s[1:].strip())
    if not inc_lines:
        inc_lines = ["Private airport pick-up and drop-off","Private air-conditioned transportation throughout",
                     "Accommodation with daily breakfast","Meals as mentioned in the program",
                     "All sightseeing entrance fees as mentioned","English-speaking local guide"]
    if not exc_lines:
        exc_lines = ["International flights","Vietnam visa and visa processing fees",
                     "Travel insurance","Personal expenses, laundry, beverages and tips",
                     "Optional activities not mentioned in the program"]
    experiences = [{"num": f"{i+1:02d}", "title": it.name, "desc": it.description or f"Premium service: {it.name}."}
                   for i, it in enumerate(items_list[:3])]
    while len(experiences) < 3:
        experiences.append({"num": f"{len(experiences)+1:02d}", "title": "Premium Service",
                            "desc": "Carefully curated service included in this quotation."})
    return {
        "quotation_id": quotation_id,
        "img_0": img_0, "img_1": img_1, "img_2": img_2, "img_3": img_3, "img_4": img_4,
        "tour_title": tour_title,
        "kicker": f"Private Luxury Quotation \u2022 {payload.quotationDate}",
        "lede": payload.deliveryTerms or "A polished, privately guided journey \u2014 crafted for discerning travellers who value comfort, cultural depth and seamless pacing.",
        "customer_name": payload.customer.name, "seller_name": seller_name,
        "quotation_number": payload.quotationNumber or quotation_id,
        "quotation_date": str(payload.quotationDate),
        "valid_until": str(payload.validUntil) if payload.validUntil else "On request",
        "contact": seller_phone,
        "strip_duration": f"{len(items_list)}D Tour", "strip_best_for": "B2B Partners",
        "strip_pace": "Relaxed", "strip_service": "Private",
        "overview_h2": f"{payload.customer.name}, curated with elegance and ease.",
        "overview_p": f"This quotation covers {len(items_list)} service(s) totalling {payload.grandTotal:,.2f} {payload.currency}. Crafted for discerning travellers who expect seamless logistics and private service.",
        "experiences": experiences,
        "journey_h2": "Destination imagery woven into the quotation.",
        "journey_p": "Large cinematic destination panels help the quotation feel like a premium travel proposal.",
        "gal1_label": "Highlight" if len(destinations) > 0 else "Destination",
        "gal1_title": _d_name(0), "gal2_label": "Destination", "gal2_title": _d_name(1),
        "gal3_label": "Experience", "gal3_title": _d_name(2), "gal4_label": "Journey", "gal4_title": _d_name(3),
        "itinerary_h2": "Detailed service program",
        "itinerary_p": f"Your personalised quotation \u2014 {len(items_list)} items, {payload.grandTotal:,.2f} {payload.currency} total.",
        "items": [i.model_dump() for i in payload.items], "currency": payload.currency,
        "pricing_h2": f"B2B net price: {payload.grandTotal:,.2f} {payload.currency}",
        "pricing_p": f"Grand total for all services. Currency: {payload.currency}. Final rates subject to reconfirmation.",
        "grand_total": payload.grandTotal, "subtotal": payload.subtotal,
        "tax_total": payload.taxTotal, "payment_terms": payload.paymentTerms or "",
        "inclusions": inc_lines, "exclusions": exc_lines,
        "terms_p": "These notes keep the proposal professional and protect the B2B quotation before services are reconfirmed.",
        "cta_h2": "Confirm dates, then refine the luxury layer.",
        "cta_p": "Share travel dates, preferred hotel tier, rooming list and any dietary or mobility requirements. We will reconfirm availability and return a finalized quotation.",
        "contact_web": "www.vietnamsafar.vn", "contact_phone": seller_phone, "seller_email": seller_email,
        "footer_text": f"{tour_title} \u2014 Luxury quotation prepared for {payload.customer.name}.",
    }


def _load_ctx(quotation_id: str) -> dict | None:
    """Load ctx from memory store or persisted ctx.json (cross-instance resilience)."""
    entry = quotations.get(quotation_id)
    if entry and entry.get("ctx"):
        return entry["ctx"]
    ctx_path = os.path.join("published", quotation_id, "ctx.json")
    if os.path.isfile(ctx_path):
        with open(ctx_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/quotations")
async def create_quotation(request: Request):
    """
    Receives structured quotation data from a ChatGPT Custom GPT Action,
    renders a Jinja2 landing page template, stores it, and returns the preview URL.
    """
    body = await request.json()
    log.debug("[/quotations] Incoming keys: %s", list(body.keys()))

    # Unwrap ChatGPT Action wrapper if present
    data = body.get("params", body)
    log.debug("[/quotations] Data keys after unwrap: %s", list(data.keys()))

    try:
        payload = QuotationPayload.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        log.error("[/quotations] Pydantic validation failed — %d error(s):\n%s",
                  len(errors), json.dumps(errors, indent=2, default=str))
        return JSONResponse(status_code=422, content={"detail": errors,
            "hint": "Field path is in 'loc'. Check which required field is missing."})

    quotation_id = f"quo_{uuid.uuid4().hex[:12]}"

    # ── Extract exact destinations from payload text for the gallery ─────────────
    # Combine item names, descriptions, and notes for context
    text_context = " ".join([f"{i.name} {i.description or ''}" for i in payload.items])
    if payload.notes:
        text_context += " " + payload.notes

    from image_selector import extract_and_map_destinations, get_random_image_for_province
    destinations = await extract_and_map_destinations(text_context, max_items=4)
    
    # Resolve image urls for each destination
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))

    log.debug("[/quotations] Extracted destinations: %s", destinations)

    default_img = "/assets/vietnam-safar-logo.png"
    
    # Hero image: Pick a random image from the resolved destinations, or default
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/quotations] Hero image resolved: %s", hero_image_url)

    ctx = _build_ctx(quotation_id, payload, hero_image_url, destinations)

    # ── Render landing page HTML ───────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    tmpl_lp  = templates.get_template("vietnam_heritage_luxury.html")
    tmpl_pdf = templates.get_template("vietnam_heritage_luxury_pdf.html")

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render,  **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )

    # ── Update in-memory store ────────────────────────────────────────────
    quotations[quotation_id] = {
        "payload":       payload.model_dump(mode="json"),
        "ctx":           ctx,
        "html":          rendered_html,
        "pdf_html":      rendered_pdf,
        "status":        "pending",
        "published_url": None,
        "pdf_url":       None,
        "version":       0,
    }

    # ── Publish v1.html + pdf.html to GitHub (production flow) ──────────────
    # On Vercel, filesystem is READ-ONLY — all persistence must go through GitHub.
    # NEVER fall back to disk writes on production; raise 502 if GitHub fails.
    published_url: str | None = None
    pdf_static_url: str | None = None
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

    if ENVIRONMENT == "production":
        # Hard requirement: GITHUB_TOKEN and GITHUB_REPO must be configured.
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            log.error("[/quotations] GITHUB_TOKEN or GITHUB_REPO not set — cannot persist on Vercel.")
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: GITHUB_TOKEN / GITHUB_REPO env vars are missing.",
            )
        try:
            # Publish landing page and PDF in parallel
            published_url, pdf_static_url = await asyncio.gather(
                publish_to_github(
                    quotation_id=quotation_id,
                    html_content=rendered_html,
                    version=1,
                ),
                publish_file_to_github(
                    file_path=f"published/{quotation_id}/pdf.html",
                    html_content=rendered_pdf,
                    commit_message=f"Publish PDF view for quotation {quotation_id}",
                ),
            )
            quotations[quotation_id]["status"]        = "published"
            quotations[quotation_id]["published_url"] = published_url
            quotations[quotation_id]["pdf_url"]       = pdf_static_url
            quotations[quotation_id]["version"]       = 1
            log.info("[/quotations] ✓ v1 + pdf.html committed to GitHub → %s", published_url)
        except Exception as exc:
            log.exception("[/quotations] GitHub publish FAILED for %s: %s", quotation_id, exc)
            # On Vercel, disk is read-only — we MUST NOT attempt a filesystem fallback.
            raise HTTPException(
                status_code=502,
                detail=f"GitHub publish failed: {exc}. Check GITHUB_TOKEN permissions and GITHUB_REPO value.",
            )

    else:
        # ── Localhost only: persist to disk ────────────────────────────────────
        quo_dir = os.path.join("published", quotation_id)
        os.makedirs(quo_dir, exist_ok=True)
        with open(os.path.join(quo_dir, "v1.html"),  "w", encoding="utf-8") as _f:
            _f.write(rendered_html)
        with open(os.path.join(quo_dir, "pdf.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as _f:
            json.dump(ctx, _f, ensure_ascii=False, default=str)
        quotations[quotation_id]["status"]  = "published"
        quotations[quotation_id]["version"] = 1
        log.info("[/quotations] Localhost: v1.html + pdf.html + ctx.json written to disk.")

    log.info("[/quotations] ✓ id=%s  customer=%s  items=%d  total=%s %s",
             quotation_id, payload.customer.name, len(payload.items),
             payload.grandTotal, payload.currency)

    # quotationUrl should be the stable permalink API endpoint
    quotation_url = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
    return {
        "quotationId":  quotation_id,
        "status":       "published",
        "version":      1,
        "message":      "Landing page published. Open quotationUrl to preview and edit inline.",
        "quotationUrl": quotation_url,
        "pdfUrl":       f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf",
    }


# ── GET /quotations/{id}/pdf — A4-optimised PDF view ─────────────────────
# IMPORTANT: must be registered BEFORE the {quotation_id} catch-all route.

@app.get("/quotations/{quotation_id}/pdf", response_class=HTMLResponse)
async def get_quotation_pdf(quotation_id: str):
    """
    On production (GitHub token set): redirect to the static pdf.html committed to GitHub/Vercel CDN.
    On localhost (no token): dynamically render from ctx.json on disk.
    Auto-triggers the browser print dialog so the user just hits Cmd+P → Save as PDF.
    """
    from fastapi.responses import RedirectResponse

    # 1. In-memory store: check if we already have a static pdf URL (same instance)
    entry = quotations.get(quotation_id)
    if entry and entry.get("pdf_url"):
        return RedirectResponse(url=entry["pdf_url"], status_code=302)

    # 2. Production: static pdf.html is on Vercel CDN — redirect there
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        static_pdf_url = f"{PUBLIC_BASE_URL}/published/{quotation_id}/pdf.html"
        return RedirectResponse(url=static_pdf_url, status_code=302)

    # 3. Localhost fallback: dynamic render from disk ctx.json
    ctx = _load_ctx(quotation_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")
    loop = asyncio.get_event_loop()
    tmpl = templates.get_template("vietnam_heritage_luxury_pdf.html")
    rendered = await loop.run_in_executor(None, partial(tmpl.render, **ctx))
    log.info("[/pdf] Served dynamic PDF view for %s", quotation_id)
    return HTMLResponse(content=rendered)


@app.get("/quotations/{quotation_id}", response_class=HTMLResponse)
async def get_quotation(quotation_id: str):
    """
    Stable permalink for a quotation.
    Serves from memory (instant), then disk (deployed), then GitHub (if Vercel is still building).
    """
    # 1. In-memory fast path (same serverless instance)
    entry = quotations.get(quotation_id)
    if entry and entry.get("html"):
        return HTMLResponse(content=entry["html"])

    # 2. Local disk fallback (if Vercel has finished building this commit)
    for version in range(10, 0, -1):
        path = os.path.join("published", quotation_id, f"v{version}.html")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())

    # 3. GitHub fallback (if Vercel is STILL building and memory was wiped via cold start)
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        import httpx
        repo = os.getenv("GITHUB_REPO")
        token = os.getenv("GITHUB_TOKEN")
        if repo and token:
            # Check v10 down to v1
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.raw"}
                for version in range(10, 0, -1):
                    gh_url = f"https://api.github.com/repos/{repo}/contents/published/{quotation_id}/v{version}.html"
                    resp = await client.get(gh_url, headers=headers)
                    if resp.status_code == 200:
                        log.info("[/quotations] Fetched %s directly from GitHub API.", quotation_id)
                        return HTMLResponse(content=resp.text)

    raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found. It may still be deploying, please refresh in 30 seconds.")



# ── POST /quotations/{id}/publish — commit to GitHub → Vercel ─────────────────

class PublishRequest(BaseModel):
    html: str

@app.post("/quotations/{quotation_id}/publish")
async def publish_quotation(quotation_id: str, body: PublishRequest):
    """
    Commit the edited HTML (sent from browser) to GitHub published/ folder.
    Does NOT require the in-memory store — quotation_id + html come from the request.
    This makes the endpoint resilient across Vercel serverless instances.
    """
    # Fetch the next version from GitHub directly to ensure it works across serverless instances
    from github_publish import get_next_version, publish_to_github
    version = await get_next_version(quotation_id)

    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    
    if ENVIRONMENT == "production":
        try:
            published_url = await publish_to_github(
                quotation_id=quotation_id,
                html_content=body.html,
                version=version,
            )
        except Exception as exc:
            log.exception("[publish] Failed for %s", quotation_id)
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        # Localhost: write to disk
        quo_dir = os.path.join("published", quotation_id)
        os.makedirs(quo_dir, exist_ok=True)
        filename = f"v{version}.html"
        file_path = os.path.join(quo_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body.html)
        published_url = f"{PUBLIC_BASE_URL}/published/{quotation_id}/{filename}"
        log.info("[publish] Localhost: wrote to disk %s", file_path)

    # Update in-memory store if entry exists (same instance flow)
    entry = quotations.get(quotation_id)
    if entry:
        entry["status"]        = "published"
        entry["published_url"] = published_url
        entry["html"]          = body.html
        entry["version"]       = version

    log.info("[publish] ✓ %s v%d → %s", quotation_id, version, published_url)
    return {"published_url": published_url, "version": version, "status": "published"}


# ── Landing page (static demo) ───────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_landing_page():
    # Serve the original static demo file directly
    with open("vietnam-heritage-luxury-landingpage.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("assets/vietnam-safar-logo.png", media_type="image/png")


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Privacy Policy – Vietnam Safar Quotation API</title>
  <style>
    :root {
      --ivory: #f8f3e9;
      --emerald: #17412e;
      --gold: #b7894b;
      --gold-2: #d8bd85;
      --ink: #11130f;
      --muted: #706a5d;
      --line: rgba(183,137,75,.22);
      --card: #fffaf1;
      --serif: Georgia, 'Times New Roman', serif;
      --sans: system-ui, Arial, Helvetica, sans-serif;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      background: var(--ivory);
      color: var(--ink);
      font-family: var(--sans);
      line-height: 1.75;
    }
    header {
      background: var(--emerald);
      color: #fff;
      padding: 48px 0 40px;
      text-align: center;
    }
    header .kicker {
      color: var(--gold-2);
      font-size: 11px;
      letter-spacing: .22em;
      text-transform: uppercase;
      font-weight: 700;
      margin-bottom: 14px;
    }
    header h1 {
      font-family: var(--serif);
      font-size: clamp(28px, 5vw, 52px);
      font-weight: 500;
      letter-spacing: -.04em;
    }
    header p {
      margin-top: 12px;
      color: rgba(255,255,255,.7);
      font-size: 14px;
    }
    .container { width: min(820px, 92%); margin: 0 auto; }
    main { padding: 56px 0 80px; }
    section {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 32px 36px;
      margin-bottom: 20px;
    }
    h2 {
      font-family: var(--serif);
      font-size: 22px;
      font-weight: 500;
      color: var(--emerald);
      margin-bottom: 14px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--line);
    }
    p { color: var(--muted); font-size: 15px; margin-bottom: 12px; }
    p:last-child { margin-bottom: 0; }
    ul { color: var(--muted); font-size: 15px; padding-left: 22px; margin-bottom: 12px; }
    ul li { margin-bottom: 6px; }
    a { color: var(--gold); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .badge {
      display: inline-block;
      background: rgba(183,137,75,.12);
      border: 1px solid var(--line);
      color: var(--gold);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .14em;
      text-transform: uppercase;
      border-radius: 999px;
      padding: 4px 14px;
      margin-bottom: 20px;
    }
    footer {
      text-align: center;
      font-size: 13px;
      color: var(--muted);
      padding: 24px 0 40px;
    }
  </style>
</head>
<body>
  <header>
    <div class="container">
      <div class="kicker">Legal</div>
      <h1>Privacy Policy</h1>
      <p>Vietnam Safar – Discovery Asia Travel Group &nbsp;|&nbsp; Quotation API</p>
    </div>
  </header>

  <main>
    <div class="container">
      <div class="badge">Effective date: May 13, 2026</div>

      <section>
        <h2>1. Overview</h2>
        <p>
          This Privacy Policy describes how <strong>Vietnam Safar – Discovery Asia Travel Group</strong>
          ("we", "our", or "us") handles information submitted through the Vietnam Safar Quotation API,
          which powers the Custom GPT integration for generating travel quotation documents.
        </p>
        <p>
          By using this API or the associated Custom GPT, you agree to the practices described in this policy.
        </p>
      </section>

      <section>
        <h2>2. Information We Collect</h2>
        <p>Through the Quotation API, we may receive the following data submitted by the GPT or user:</p>
        <ul>
          <li>Quotation metadata (quotation number, date, validity period, currency)</li>
          <li>Customer information (company name, contact name, email, phone, address)</li>
          <li>Seller / issuer information (company name, contact details)</li>
          <li>Line items (product or service names, quantities, pricing)</li>
          <li>Payment terms, delivery terms, and notes</li>
          <li>Source identifier (e.g. "custom-gpt", "ChatGPT upload")</li>
        </ul>
      </section>

      <section>
        <h2>3. How We Use This Information</h2>
        <p>Submitted quotation data is used solely for the following purposes:</p>
        <ul>
          <li>Generating and storing travel quotation records for B2B partners</li>
          <li>Enabling the Custom GPT to produce accurate quotation landing pages and documents</li>
          <li>Internal logging and debugging to ensure system reliability</li>
        </ul>
        <p>
          We do <strong>not</strong> use this data for advertising, profiling, or any purpose
          unrelated to the quotation workflow.
        </p>
      </section>

      <section>
        <h2>4. Data Sharing</h2>
        <p>
          We do not sell, rent, or share submitted data with third parties, except as required
          to operate the service (e.g. hosting infrastructure) or comply with applicable law.
        </p>
        <p>
          Data transmitted through the Custom GPT integration is subject to
          <a href="https://openai.com/policies/privacy-policy" target="_blank" rel="noopener">
            OpenAI's Privacy Policy
          </a> for the processing performed on OpenAI's platform.
        </p>
      </section>

      <section>
        <h2>5. Data Retention</h2>
        <p>
          Quotation records are retained for as long as necessary to fulfil the business purpose
          for which they were created, or as required by applicable regulations.
          Internal debug logs are purged on a rolling basis.
        </p>
      </section>

      <section>
        <h2>6. Security</h2>
        <p>
          All data is transmitted over HTTPS. We implement reasonable technical and organisational
          measures to protect submitted information against unauthorised access, loss, or disclosure.
        </p>
      </section>

      <section>
        <h2>7. Your Rights</h2>
        <p>
          You may request access to, correction of, or deletion of any personal data submitted
          through this API by contacting us at the address below.
        </p>
      </section>

      <section>
        <h2>8. Contact</h2>
        <p>
          <strong>Vietnam Safar – Discovery Asia Travel Group</strong><br />
          Email: <a href="mailto:safa@vietnamsafar.vn">safa@vietnamsafar.vn</a><br />
          Phone: <a href="tel:+84911538738">+84 911 538 738</a><br />
          Website: <a href="https://vietnamsafar.vn" target="_blank" rel="noopener">vietnamsafar.vn</a>
        </p>
      </section>
    </div>
  </main>

  <footer>
    <div class="container">
      &copy; 2026 Vietnam Safar – Discovery Asia Travel Group. All rights reserved.
    </div>
  </footer>
</body>
</html>"""
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
