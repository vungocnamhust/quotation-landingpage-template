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
from github_publish import publish_to_github
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


# ── Endpoint ─────────────────────────────────────────────────────────────────

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

    # ── Extract locations from payload → select images concurrently ─────────────
    # Locations are derived from item names + notes + delivery terms.
    # select_landing_image is already async (calls OpenAI), so we gather all at once.
    location_sources: list[str] = []

    # Hero image: use notes/page title as the primary location hint
    hero_location = payload.notes or payload.deliveryTerms or payload.customer.name
    location_sources.append(hero_location)

    # Per-item images: use each item's name as location hint
    for item in payload.items:
        location_sources.append(item.name)

    log.debug("[/quotations] Selecting images for %d locations: %s", len(location_sources), location_sources)

    # Run all LLM image lookups in parallel — no blocking
    image_urls: list[str] = await asyncio.gather(
        *[select_landing_image(loc) for loc in location_sources],
        return_exceptions=False,
    )

    hero_image_url   = image_urls[0]                        # First = hero
    item_image_urls  = image_urls[1:]                       # Rest = per-item

    log.debug("[/quotations] Images resolved: hero=%s  items=%s", hero_image_url, item_image_urls)

    # ── Build template context ────────────────────────────────────────────────
    seller = payload.seller

    # Attach resolved image URL to each item dict
    items_with_images = []
    for i, item in enumerate(payload.items):
        item_dict = item.model_dump()
        item_dict["image_url"] = item_image_urls[i] if i < len(item_image_urls) else hero_image_url
        items_with_images.append(item_dict)

    ctx = {
        "quotation_id":     quotation_id,
        "page_title":       payload.notes or f"{payload.customer.name} – Quotation",
        "kicker":           f"Private Quotation • {payload.quotationDate}",
        "lede":             payload.notes or "A curated quotation prepared exclusively for you.",
        "hero_image_url":   hero_image_url,
        "customer_name":    payload.customer.name,
        "seller_name":      seller.companyName if seller else "Vietnam Safar – Discovery Asia Travel Group",
        "seller_email":     (seller.email if seller else None) or "sales@vietnamsafar.vn",
        "seller_phone":     (seller.phone if seller else None) or "+84 911 538 738",
        "seller_address":   (seller.address if seller else None) or "",
        "quotation_number": payload.quotationNumber or quotation_id,
        "quotation_date":   str(payload.quotationDate),
        "valid_until":      str(payload.validUntil) if payload.validUntil else "On request",
        "contact":          (seller.email if seller else None) or "www.vietnamsafar.vn",
        "currency":         payload.currency,
        "grand_total":      payload.grandTotal,
        "subtotal":         payload.subtotal,
        "tax_total":        payload.taxTotal,
        "item_count":       len(payload.items),
        "payment_terms":    payload.paymentTerms or "On confirmation",
        "delivery_terms":   payload.deliveryTerms or "As agreed",
        "notes":            payload.notes or "",
        "items":            items_with_images,
        "overview_heading": f"{payload.customer.name}, a premium proposal crafted with care.",
        "overview_desc":    f"This quotation covers {len(payload.items)} item(s) totalling {payload.grandTotal:,.2f} {payload.currency}.",
        "pricing_heading":  f"Total: {payload.grandTotal:,.2f} {payload.currency}",
        "pricing_desc":     f"Grand total for all items. Currency: {payload.currency}.",
    }

    # ── Register slot in store immediately (status=pending) ─────────────────
    # This lets GET /quotations/{id} respond with a loading page while
    # rendering runs in the thread pool — keeps the event loop unblocked.
    quotations[quotation_id] = {
        "payload":       payload.model_dump(mode="json"),
        "html":          None,
        "status":        "pending",
        "published_url": None,
        "version":       0,
    }

    # ── Offload sync Jinja2 render to thread pool (non-blocking) ─────────────
    # tmpl.render() is CPU-bound/sync — running it directly in an async handler
    # would block the event loop and delay responses to ALL concurrent requests.
    loop = asyncio.get_event_loop()
    tmpl = templates.get_template("vietnam_heritage_luxury.html")
    rendered_html = await loop.run_in_executor(None, partial(tmpl.render, **ctx))

    # Update store with rendered HTML
    quotations[quotation_id]["html"]   = rendered_html
    quotations[quotation_id]["status"] = "draft"

    # ── Persist draft to filesystem ───────────────────────────────────────────
    # Vercel serverless instances don't share memory between requests.
    # Writing to published/{id}.draft.html ensures GET /quotations/{id} can
    # serve the page even if called from a different serverless instance.
    draft_path = os.path.join("published", f"{quotation_id}.draft.html")
    os.makedirs("published", exist_ok=True)
    loop2 = asyncio.get_event_loop()
    await loop2.run_in_executor(
        None,
        lambda: open(draft_path, "w", encoding="utf-8").write(rendered_html)
    )
    log.info("[/quotations] Draft written → %s", draft_path)

    log.info("[/quotations] ✓ id=%s  customer=%s  items=%d  total=%s %s",
             quotation_id, payload.customer.name, len(payload.items),
             payload.grandTotal, payload.currency)

    quotation_url = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
    return {
        "quotationId":  quotation_id,
        "status":       "draft",
        "message":      "Landing page created. Open quotationUrl to preview and edit.",
        "quotationUrl": quotation_url,
    }


# ── GET /quotations/{id} — serve editable preview ────────────────────────────

@app.get("/quotations/{quotation_id}", response_class=HTMLResponse)
async def get_quotation(quotation_id: str):
    # 1. Try in-memory store first (same instance, fastest)
    entry = quotations.get(quotation_id)

    if entry and entry["status"] == "pending":
        # Render still in progress — serve auto-refresh loading page
        loading_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta http-equiv="refresh" content="1;url=/quotations/{quotation_id}"/>
<title>Preparing your quotation…</title>
<style>
  body{{margin:0;background:#f8f3e9;display:grid;place-items:center;min-height:100vh;font-family:Arial,sans-serif}}
  .card{{background:#fffaf1;border:1px solid rgba(183,137,75,.28);border-radius:28px;padding:48px 56px;text-align:center;box-shadow:0 24px 60px rgba(17,19,15,.1)}}
  h1{{font-family:Georgia,serif;color:#17412e;font-size:32px;margin:0 0 12px}}
  p{{color:#706a5d;font-size:15px;margin:0 0 24px}}
  .spinner{{width:40px;height:40px;border:3px solid rgba(183,137,75,.2);border-top-color:#b7894b;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto}}
  @keyframes spin{{to{{transform:rotate(360deg)}}}}
</style></head>
<body><div class="card">
  <div class="spinner"></div>
  <h1 style="margin-top:24px">Preparing your quotation…</h1>
  <p>Your landing page is being rendered. This page will refresh automatically.</p>
  <code style="color:#b7894b;font-size:13px">{quotation_id}</code>
</div></body></html>"""
        return HTMLResponse(content=loading_html, status_code=202)

    if entry and entry["html"]:
        return HTMLResponse(content=entry["html"])

    # 2. Fallback: read draft file from filesystem (cross-instance resilience)
    draft_path = os.path.join("published", f"{quotation_id}.draft.html")
    if os.path.isfile(draft_path):
        with open(draft_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())

    raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' not found.")



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
    # Derive version by counting existing published files for this quotation
    import glob
    existing = glob.glob(os.path.join("published", f"{quotation_id}_v*.html"))
    version  = len(existing) + 1

    try:
        published_url = await publish_to_github(
            quotation_id=quotation_id,
            html_content=body.html,
            version=version,
        )
    except Exception as exc:
        log.exception("[publish] Failed for %s", quotation_id)
        raise HTTPException(status_code=502, detail=str(exc))

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
