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
from pydantic import BaseModel, ValidationError, Field
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
# Removed: app.mount("/published", StaticFiles(directory="published"), name="published")
# We now use a dynamic route below to handle /published to allow GitHub API fallback on Vercel

# Jinja2 templates
templates = Jinja2Templates(directory="templates")

# ── In-memory quotation store ─────────────────────────────────────────────────
# { quotation_id: { "payload": dict, "html": str, "status": str,
#                   "published_url": str|None, "version": int } }
quotations: dict[str, dict] = {}
itineraries: dict[str, dict] = {}

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


# ── Pydantic models — mapped 1:1 from the OpenAPI schema (v2.1.0) ───────────
# Only fields listed under `required:` in the spec are non-Optional here.

class Duration(BaseModel):
    # required: [days, nights]
    days:   int
    nights: int
    label:  Optional[str] = None


class TravelDates(BaseModel):
    # required: [startDate, endDate]
    startDate:   date
    endDate:     date
    displayText: Optional[str] = None


class GuestComposition(BaseModel):
    # required: [totalGuests]
    totalGuests:  int
    adults:       Optional[int]       = None
    children:     Optional[int]       = None
    infants:      Optional[int]       = None
    childrenAges: Optional[List[int]] = None
    displayText:  Optional[str]       = None


class Customer(BaseModel):
    # required: [name]
    name:        str
    contactName: Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    address:     Optional[str] = None
    nationality: Optional[str] = None
    market:      Optional[str] = None


class Seller(BaseModel):
    # required: [companyName]
    companyName: str
    contactName: Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    address:     Optional[str] = None
    taxCode:     Optional[str] = None
    website:     Optional[str] = None


class TextSection(BaseModel):
    # required: [paragraphs]
    paragraphs: List[str]
    heading:    Optional[str] = None


class ItineraryDay(BaseModel):
    # required: [dayNumber, title, description]
    dayNumber:          int
    title:              str
    description:        List[str]
    date:               Optional[str]        = None  # kept as str to avoid Pydantic v2 field-name shadowing
    overnight:          Optional[str]        = None
    meals:              Optional[List[str]]  = None
    destinations:       Optional[List[str]]  = None
    activities:         Optional[List[str]]  = None
    optionalActivities: Optional[List[str]]  = None
    notes:              Optional[List[str]]  = None


class MoneyAmount(BaseModel):
    # required: [amount, currency]
    amount:      float
    currency:    str
    displayText: Optional[str]  = None
    isFromPrice: Optional[bool] = None


class PriceOption(BaseModel):
    # required: [hotelCategory, pricePerPerson, totalPrice]
    hotelCategory:        str
    pricePerPerson:       MoneyAmount
    totalPrice:           MoneyAmount
    optionName:           Optional[str]       = None
    isConfirmedMainOption: Optional[bool]     = None
    isAlternativeOption:  Optional[bool]      = None
    notes:                Optional[List[str]] = None


class TourPricing(BaseModel):
    # required: [currency, priceOptions]
    currency:     str
    priceOptions: List[PriceOption]
    pricingTitle: Optional[str]   = None
    basis:        Optional[str]   = None
    totalGuests:  Optional[int]   = None
    subtotal:     Optional[float] = None
    discountTotal: Optional[float] = None
    taxTotal:     Optional[float] = None
    grandTotal:   Optional[float] = None


from quotation_schemas import TourQuotationPayload


# ── Detailed Itinerary Booking Models ───────────────────────────────────────

class BookedHotel(BaseModel):
    name: str
    star: Optional[int] = None
    addressArea: Optional[str] = None
    roomType: Optional[str] = None
    checkInDate: str
    checkOutDate: str
    nights: int
    destination: str
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    imageUrl: Optional[str] = None
    pricePerNightUsd: Optional[float] = None
    pricePerNightVnd: Optional[float] = None


class BookedActivity(BaseModel):
    activityName: str
    operator: Optional[str] = None
    date: str
    area: str
    durationHours: Optional[float] = None
    privateGroup: Optional[bool] = True
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    imageUrl: Optional[str] = None
    pricePerAdultUsd: Optional[float] = None
    pricePerChildUsd: Optional[float] = None
    totalEstimateUsd: Optional[float] = None


class BookedTransfer(BaseModel):
    transferType: str  # airport_pickup, airport_dropoff, intercity, day_trip_return
    fromLocation: str
    toLocation: str
    date: str
    vehicleRequirement: str  # e.g., 7-seat, 16-seat
    seats: Optional[int] = None
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    priceUsd: Optional[float] = None
    priceVnd: Optional[float] = None


class BookedGuide(BaseModel):
    guideName: Optional[str] = None
    language: str
    destination: str
    dates: List[str]
    days: int
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    pricePerDayUsd: Optional[float] = None
    totalEstimateUsd: Optional[float] = None


class BookedFlight(BaseModel):
    flightNumber: str
    airline: str
    date: str
    fromCity: str
    toCity: str
    departureTime: Optional[str] = None
    arrivalTime: Optional[str] = None
    status: Optional[str] = "Confirmed"
    notes: Optional[str] = None
    priceUsd: Optional[float] = None


class DetailItineraryPayload(BaseModel):
    quotationNumber: str
    quotationTitle: str
    tourTitle: str
    duration: Duration
    preparedFor: str
    nationality: Optional[str] = None
    travelDates: TravelDates
    guests: GuestComposition
    route: List[str]
    travelStyle: Optional[List[str]] = None
    
    # Service and itinerary lists
    notes: Optional[List[str]] = None
    seller: Optional[Seller] = None
    programOverview: Optional[TextSection] = None
    hotels: List[BookedHotel] = Field(default_factory=list)
    activities: List[BookedActivity] = Field(default_factory=list)
    transfers: List[BookedTransfer] = Field(default_factory=list)
    flights: List[BookedFlight] = Field(default_factory=list)
    guides: List[BookedGuide] = Field(default_factory=list)
    itinerary: List[ItineraryDay] = Field(default_factory=list)
    inclusions: Optional[List[str]] = None
    exclusions: Optional[List[str]] = None
    priceConditions: Optional[TextSection] = None
    pricing: Optional[TourPricing] = None
# ── Context builder (pure fn — no I/O) ───────────────────────────────────────


def truncate_text(text: Optional[str], max_chars: int) -> str:
    if not text:
        return ""
    text_str = str(text).strip()
    if len(text_str) <= max_chars:
        return text_str
    # Try to split on last space to avoid cutting words
    truncated = text_str[:max_chars].rsplit(" ", 1)[0]
    if not truncated:
        truncated = text_str[:max_chars - 3]
    return truncated.strip() + "..."

# ── Context builder (pure fn — no I/O) ───────────────────────────────────────

def _build_ctx(quotation_id, payload: "TourQuotationPayload", hero_image_url, destinations: list[dict]):
    """Build template context. Shared by /quotations (landingpage) and /quotations/{id}/pdf."""
    default_img = "/assets/vietnam-safar-logo.png"
    
    # Defaults for seller/contact
    seller_name  = "Vietnam Safar \u2013 Discovery Asia Travel Group"
    seller_email = "sales@vietnamsafar.vn"
    seller_phone = "+84 911 538 738"

    # Resolve key display strings from new Spec 36 schema
    tour_title    = truncate_text(payload.landingpageContent.heroSection.subtitle, 100)
    prepared_for  = truncate_text(payload.journeyGlance.guestProfile, 60)
    
    # Calculate duration
    days_count = len(payload.itinerary)
    nights_count = max(0, days_count - 1)
    duration_lbl  = f"{days_count}D{nights_count}N"
    
    # Travel dates - fallback to hotel plan if checkInDate is available, otherwise placeholder
    travel_dates = "Flexible Dates"
    if payload.hotelPlan.hotels:
        start_date = payload.hotelPlan.hotels[0].checkInDate
        end_date = payload.hotelPlan.hotels[-1].checkOutDate
        if start_date and end_date:
            travel_dates = f"{start_date} \u2013 {end_date}"
            
    guests_txt    = truncate_text(payload.journeyGlance.guestProfile, 100)
    
    # Extract route from itinerary destinations in sequence
    route_list = []
    for d in payload.itinerary:
        if d.destination and d.destination not in route_list:
            route_list.append(d.destination)
    route_txt = " \u2013 ".join(route_list)
    
    nationality   = truncate_text(payload.journeyGlance.market, 60)
    travel_style  = truncate_text(payload.journeyGlance.partnerNote, 100)

    # Construct pricing context from agent custom pricing dict or default
    price_options = []
    total_price = ""
    price_per_pax = ""
    grand_total_num = 0.0
    currency = "USD"

    # Check if pricing is custom pricing context dict (from pricing engine)
    if isinstance(payload.pricing, dict) or hasattr(payload.pricing, "totalPriceUsd"):
        p_dict = payload.pricing if isinstance(payload.pricing, dict) else payload.pricing.model_dump()
        currency = p_dict.get("currency", "USD")
        grand_total_num = p_dict.get("totalPriceUsd", 0.0)
        
        # Estimate per-person
        guests_count = 1
        import re
        m = re.search(r'(\d+)\s+adult', guests_txt, re.IGNORECASE)
        if m:
            guests_count = int(m.group(1))
        price_per_person = grand_total_num / max(1, guests_count)
        
        price_per_pax = f"{currency} {price_per_person:,.0f} / person"
        total_price = f"{currency} {grand_total_num:,.0f}"
        
        price_options = [{
            "hotelCategory": truncate_text(payload.journeyGlance.hotelStandard, 80),
            "optionName": "Main confirmed option",
            "pricePerPerson": {
                "amount": price_per_person,
                "currency": currency,
                "displayText": price_per_pax,
                "isFromPrice": False
            },
            "totalPrice": {
                "amount": grand_total_num,
                "currency": currency,
                "displayText": total_price,
                "isFromPrice": False
            },
            "isConfirmedMainOption": True,
            "isAlternativeOption": False,
            "notes": ["Calculated based on actual supplier costs"]
        }]
    else:
        # Standard Pricing model
        currency = payload.pricing.currency
        for opt in payload.pricing.priceOptions:
            price_per_person_amt = opt.amount or 0.0
            total_price_amt = price_per_person_amt * 2  # default placeholder
            
            p_pax_txt = f"{currency} {price_per_person_amt:,.0f} / person"
            tot_txt = f"{currency} {total_price_amt:,.0f}"
            
            price_options.append({
                "hotelCategory": truncate_text(opt.label, 80),
                "optionName": truncate_text(opt.notes, 150),
                "pricePerPerson": {
                    "amount": price_per_person_amt,
                    "currency": currency,
                    "displayText": p_pax_txt,
                    "isFromPrice": False
                },
                "totalPrice": {
                    "amount": total_price_amt,
                    "currency": currency,
                    "displayText": tot_txt,
                    "isFromPrice": False
                },
                "isConfirmedMainOption": True,
                "isAlternativeOption": False,
                "notes": [truncate_text(opt.notes, 150)] if opt.notes else []
            })
        grand_total_num = payload.pricing.grandTotal or 0.0
        total_price = f"{currency} {grand_total_num:,.0f}"

    # Extract inclusions from itinerary day mainInclusions dynamically
    inc_lines = []
    for d in payload.itinerary:
        if d.mainInclusions and d.mainInclusions not in inc_lines:
            inc_lines.append(d.mainInclusions)
    if not inc_lines:
        inc_lines = [
            "Private airport pick-up and drop-off",
            "Private air-conditioned transportation throughout",
            "Accommodation with daily breakfast",
            "Meals as mentioned in the program",
            "All sightseeing entrance fees as mentioned",
            "English-speaking local guide",
        ]
        
    exc_lines = [
        "International flights",
        "Vietnam visa and visa processing fees",
        "Travel insurance",
        "Personal expenses, laundry, beverages and tips",
        "Optional activities not mentioned in the program",
    ]

    inc_lines = [truncate_text(x, 120) for x in inc_lines]
    exc_lines = [truncate_text(x, 120) for x in exc_lines]

    # Overview paragraphs
    overview_paras = [truncate_text(payload.quotationNarrative, 500)]
    overview_heading = "PROGRAM OVERVIEW"
    lede = truncate_text(payload.quotationNarrative, 500)

    # Gallery helpers
    def _d_img(i): return destinations[i].get("image_url", default_img) if i < len(destinations) else default_img
    def _d_name(i): return truncate_text(destinations[i].get("name", ""), 40) if i < len(destinations) else ""

    img_0 = hero_image_url
    img_1 = _d_img(0)
    img_2 = _d_img(1)
    img_3 = _d_img(2)
    img_4 = _d_img(3)

    # Highlight experiences — first 3 itinerary days
    experiences = [
        {"num": f"{i+1:02d}", "title": truncate_text(f"Day {day.dayNumber}: {day.destination}", 80),
         "desc": truncate_text(day.summary, 160)}
        for i, day in enumerate(payload.itinerary[:3])
    ]
    while len(experiences) < 3:
        experiences.append({"num": f"{len(experiences)+1:02d}", "title": "Premium Experience",
                            "desc": "A carefully curated moment in this journey."})

    # Price conditions note
    price_cond_paras = [
        "Rates are B2B net indicative and subject to reconfirmation at the time of booking.",
        "Final price may vary depending on hotel availability, resort category, cruise selection, domestic flight fare, rooming arrangement, child policy, and final travel services confirmed."
    ]
    price_cond_paras = [truncate_text(x, 250) for x in price_cond_paras]

    # --- GAP ALIGNMENT LOGIC ---
    show_muslim_care = False
    
    # Check meal preference in journeyGlance
    if payload.journeyGlance and payload.journeyGlance.mealPreference:
        if "halal" in payload.journeyGlance.mealPreference.lower() or "no pork" in payload.journeyGlance.mealPreference.lower():
            show_muslim_care = True
            
    # Check nationality / market (case-insensitive substring checks)
    muslim_keywords = ["saudi", "arabia", "uae", "emirates", "qatar", "kuwait", "oman", "bahrain", "gcc", "middle east", "malaysia", "indonesia", "egypt", "jordan", "turkey", "halal", "muslim"]
    
    nat_str = (nationality or "").lower()
    if any(k in nat_str for k in muslim_keywords):
        show_muslim_care = True

    # Journey at a Glance defaults/fallbacks
    glance = payload.journeyGlance
    glance_market = truncate_text(glance.market, 60)
    glance_profile = truncate_text(glance.guestProfile, 100)
    glance_standard = truncate_text(glance.hotelStandard, 80)
    glance_meals = truncate_text(glance.mealPreference, 100)
    glance_price_type = truncate_text(glance.priceType, 60)
    glance_tour_code = truncate_text(glance.tourCode, 40)
    glance_flights = truncate_text(glance.domesticFlights, 100)
    glance_basis = truncate_text(glance.priceBasis, 80)
    glance_partner_note = truncate_text(glance.partnerNote, 100)
    glance_validity = truncate_text(glance.validity, 60)

    # Why works defaults/fallbacks
    why = payload.whyWorks
    why_private = truncate_text(why.privateFlexible, 250)
    why_comfort = truncate_text(why.comfort, 250)
    why_muslim = truncate_text(why.muslimFriendly, 250)
    why_balanced = truncate_text(why.balancedHighlights, 250)

    # Selected Hotel Plan defaults/fallbacks
    hotel_plan_items = []
    hotel_room_notes = ""
    if payload.hotelPlan:
        for item in payload.hotelPlan.hotels:
            h_dict = item.model_dump(mode="json")
            h_dict["name"] = truncate_text(h_dict.get("name"), 80)
            h_dict["roomType"] = truncate_text(h_dict.get("roomType"), 80)
            h_dict["destination"] = truncate_text(h_dict.get("destination"), 60)
            h_dict["notes"] = truncate_text(h_dict.get("notes"), 150)
            hotel_plan_items.append(h_dict)
        hotel_room_notes = truncate_text(payload.hotelPlan.roomNotes or "", 200)

    # Optional Enhancements defaults/fallbacks
    opt_enhancements = []
    if payload.optionalEnhancements:
        for item in payload.optionalEnhancements:
            opt_dict = item.model_dump(mode="json")
            opt_dict["name"] = truncate_text(opt_dict.get("name"), 80)
            opt_dict["description"] = truncate_text(opt_dict.get("description"), 200)
            opt_enhancements.append(opt_dict)

    # Booking Terms defaults/fallbacks
    b_terms = payload.bookingTerms
    term_deposit = truncate_text(b_terms.deposit, 300)
    term_balance = truncate_text(b_terms.balance, 300)
    term_cancellation = truncate_text(b_terms.cancellation, 300)
    term_confirmation = truncate_text(b_terms.confirmation, 300)

    # Finalization defaults/fallbacks
    final = payload.finalization
    final_req = [truncate_text(final.finalDetailsRequired, 300)]
    final_after = [truncate_text(final.afterConfirmation, 300)]

    # Build itinerary days matching template expectations
    mapped_itinerary = []
    for d in payload.itinerary:
        mapped_itinerary.append({
            "dayNumber": d.dayNumber,
            "date": "",  # date is not explicitly in itinerary day in the new schema, but can be empty
            "title": truncate_text(f"Explore {d.destination}", 80),
            "description": [truncate_text(d.summary, 350)],
            "overnight": truncate_text(d.destination, 40),
            "meals": [truncate_text(d.dining, 80)] if d.dining else [],
            "activities": [truncate_text(d.mainInclusions, 120)] if d.mainInclusions else [],
            "notes": [truncate_text(f"Sense of Pace: {d.senseOfPace}", 80)] if d.senseOfPace else [],
            "destinations": [truncate_text(d.destination, 40)]
        })

    return {
        # IDs & images
        "quotation_id":   quotation_id,
        "img_0": img_0, "img_1": img_1, "img_2": img_2, "img_3": img_3, "img_4": img_4,
        "destinations":   destinations,
        # Hero / header
        "quotation_title": truncate_text(payload.landingpageContent.heroSection.headline, 100),
        "tour_title":      tour_title,
        "kicker":          f"Private Luxury Quotation \u2012 {duration_lbl} \u2012 {travel_dates}",
        "lede":            lede,
        # Guest & trip meta
        "customer_name":   prepared_for,
        "nationality":     nationality,
        "travel_style":    travel_style,
        "guests_txt":      guests_txt,
        "route_txt":       route_txt,
        "duration_label":  duration_lbl,
        "travel_dates":    travel_dates,
        "hotel_options":   [],
        "confirmed_option": "",
        # Seller / contact
        "seller_name":    seller_name,
        "seller_email":   seller_email,
        "contact":        seller_phone,
        "contact_web":    "www.vietnamsafar.vn",
        "contact_phone":  seller_phone,
        # Quotation ref
        "quotation_number": payload.quotationNumber or quotation_id,
        "quotation_date":   travel_dates.split(" \u2013 ")[0] if "\u2013" in travel_dates else travel_dates,
        "valid_until":      glance_validity,
        # Strip badges
        "strip_duration":  duration_lbl,
        "strip_best_for":  nationality or "B2B Partners",
        "strip_pace":      "Relaxed",
        "strip_service":   "Private",
        # Overview section
        "overview_heading": overview_heading,
        "overview_h2":      f"Prepared for: {prepared_for} \u2014 {tour_title}",
        "overview_p":       payload.quotationNarrative,
        "overview_paras":   overview_paras,
        # Experiences (first 3 days)
        "experiences":      experiences,
        # Gallery section
        "journey_h2":   "Destination imagery woven into the quotation.",
        "journey_p":    "Cinematic destination panels crafted for a premium travel proposal.",
        "gal1_label":   "Highlight" if len(destinations) > 0 else "Destination",
        "gal1_title":   _d_name(0), "gal2_label": "Destination", "gal2_title": _d_name(1),
        "gal3_label":   "Experience", "gal3_title": _d_name(2), "gal4_label": "Journey", "gal4_title": _d_name(3),
        # Itinerary section
        "itinerary_h2": "Day-by-Day Journey Program",
        "itinerary_p":  f"Your private {duration_lbl} journey \u2014 {len(payload.itinerary)} days, carefully crafted.",
        "itinerary":    mapped_itinerary,
        # Pricing section
        "currency":       currency,
        "pricing_title":  "PRICE QUOTATION \u2013 B2B NET INDICATIVE",
        "pricing_basis":  glance_basis,
        "price_options":  price_options,
        "price_per_pax":  price_per_pax,
        "total_price":    total_price,
        "grand_total":    grand_total_num,
        "subtotal":       grand_total_num,
        "tax_total":      0.0,
        "pricing_h2":     f"B2B Net Price: {total_price}",
        "pricing_p":      f"Grand total for {guests_txt}. Currency: {currency}. Final rates subject to reconfirmation.",
        # Inclusions / exclusions
        "inclusions":     inc_lines,
        "exclusions":     exc_lines,
        # Price conditions
        "price_cond_paras": price_cond_paras,
        "payment_terms":    "Refer to Booking & Payment terms below.",
        "terms_p":          price_cond_paras[0],
        # CTA
        "cta_h2": "Confirm dates, then refine the luxury layer.",
        "cta_p":  "Share travel dates, preferred hotel tier, rooming list and any dietary or mobility requirements. We will reconfirm availability and return a finalized quotation.",
        # Footer
        "footer_text": f"{tour_title} \u2014 Luxury quotation prepared for {prepared_for}.",
        # Raw quotation (for reference / debugging)
        "raw_quotation":  "",
        # GAP ALIGNMENT context
        "show_muslim_care": show_muslim_care,
        "glance_market": glance_market,
        "glance_profile": glance_profile,
        "glance_standard": glance_standard,
        "glance_meals": glance_meals,
        "glance_price_type": glance_price_type,
        "glance_tour_code": glance_tour_code,
        "glance_flights": glance_flights,
        "glance_basis": glance_basis,
        "glance_partner_note": glance_partner_note,
        "glance_validity": glance_validity,
        "why_private": why_private,
        "why_comfort": why_comfort,
        "why_muslim": why_muslim,
        "why_balanced": why_balanced,
        "hotels": hotel_plan_items,
        "room_notes": hotel_room_notes,
        "optional_enhancements": opt_enhancements,
        "term_deposit": term_deposit,
        "term_balance": term_balance,
        "term_cancellation": term_cancellation,
        "term_confirmation": term_confirmation,
        "final_req": final_req,
        "final_after": final_after,
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


def _load_itinerary_ctx(itinerary_id: str) -> dict | None:
    """Load itinerary ctx from memory store or persisted ctx.json (cross-instance resilience)."""
    entry = itineraries.get(itinerary_id)
    if entry and entry.get("ctx"):
        return entry["ctx"]
    ctx_path = os.path.join("published", itinerary_id, "ctx.json")
    if os.path.isfile(ctx_path):
        with open(ctx_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _build_itinerary_ctx(itinerary_id: str, payload: DetailItineraryPayload, hero_image_url: str, destinations: list[dict]):
    """Build rendering context for the detailed itinerary landing page."""
    default_img = "/assets/vietnam-safar-logo.png"
    seller = payload.seller
    seller_name  = (seller.companyName if seller else None) or "Vietnam Safar – Discovery Asia Travel Group"
    seller_email = (seller.email if seller else None) or "sales@vietnamsafar.vn"
    seller_phone = (seller.phone if seller else None) or "+84 911 538 738"

    tour_title    = truncate_text(payload.tourTitle, 100)
    prepared_for  = truncate_text(payload.preparedFor, 60)
    duration_lbl  = payload.duration.label or f"{payload.duration.days}D{payload.duration.nights}"
    travel_dates  = payload.travelDates.displayText or f"{payload.travelDates.startDate} – {payload.travelDates.endDate}"
    guests_txt    = truncate_text(payload.guests.displayText or f"{payload.guests.totalGuests} guests", 100)
    route_txt     = " – ".join(payload.route)
    nationality   = truncate_text(payload.nationality or "", 60)
    travel_style  = truncate_text(" | ".join(payload.travelStyle) if payload.travelStyle else "Private", 100)

    # Narrative overview
    overview_paras = [truncate_text(p, 500) for p in payload.programOverview.paragraphs] if payload.programOverview and payload.programOverview.paragraphs else []
    overview_heading = truncate_text(payload.programOverview.heading or "PROGRAM OVERVIEW", 60) if payload.programOverview else "PROGRAM OVERVIEW"
    lede = truncate_text(overview_paras[0] if overview_paras else "A detailed booking itinerary crafted for your journey.", 500)

    # Gallery helpers
    def _d_img(i): return destinations[i].get("image_url", default_img) if i < len(destinations) else default_img
    def _d_name(i): return truncate_text(destinations[i].get("name", ""), 40) if i < len(destinations) else ""

    img_0 = hero_image_url
    img_1 = _d_img(0)
    img_2 = _d_img(1)
    img_3 = _d_img(2)
    img_4 = _d_img(3)

    # Highlight experiences — first 3 itinerary days
    experiences = [
        {"num": f"{i+1:02d}", "title": truncate_text(day.title, 80),
         "desc": truncate_text(day.description[0] if day.description else f"Day {day.dayNumber} of the journey.", 160)}
        for i, day in enumerate(payload.itinerary[:3])
    ]
    while len(experiences) < 3:
        experiences.append({"num": f"{len(experiences)+1:02d}", "title": "Premium Experience",
                            "desc": "A carefully curated moment in this journey."})

    inc_lines = payload.inclusions or [
        "Private airport pick-up and drop-off",
        "Private air-conditioned transportation throughout",
        "Accommodation with daily breakfast",
        "Meals as mentioned in the program",
        "All sightseeing entrance fees as mentioned",
        "English-speaking local guide",
    ]
    exc_lines = payload.exclusions or [
        "International flights",
        "Vietnam visa and visa processing fees",
        "Travel insurance",
        "Personal expenses, laundry, beverages and tips",
        "Optional activities not mentioned in the program",
    ]

    inc_lines = [truncate_text(x, 120) for x in inc_lines]
    exc_lines = [truncate_text(x, 120) for x in exc_lines]

    # Pricing fields from payload
    main_option   = next((o for o in payload.pricing.priceOptions if o.isConfirmedMainOption), None) if payload.pricing else None
    currency      = payload.pricing.currency if payload.pricing else "USD"
    if main_option:
        price_per_pax = main_option.pricePerPerson.displayText or f"{currency} {main_option.pricePerPerson.amount:,.0f} / person"
        total_price   = main_option.totalPrice.displayText or f"{currency} {main_option.totalPrice.amount:,.0f}"
        grand_total_num = main_option.totalPrice.amount
    else:
        price_per_pax = ""
        total_price   = ""
        grand_total_num = 0.0

    # Map daily services
    days_list = []
    for day in payload.itinerary:
        day_date = day.date
        
        # Match hotels: check-in date <= day_date < check-out date
        day_hotels = []
        for idx, h in enumerate(payload.hotels):
            if h.checkInDate and h.checkOutDate and h.checkInDate <= day_date < h.checkOutDate:  # type: ignore
                h_dict = h.model_dump(mode="json")
                h_dict["_index"] = idx
                h_dict["name"] = truncate_text(h_dict.get("name"), 80)
                h_dict["roomType"] = truncate_text(h_dict.get("roomType"), 80)
                h_dict["destination"] = truncate_text(h_dict.get("destination"), 60)
                h_dict["notes"] = truncate_text(h_dict.get("notes"), 150)
                day_hotels.append(h_dict)
        
        # Match activities
        day_activities = []
        for idx, act in enumerate(payload.activities):
            if act.date == day_date:
                act_dict = act.model_dump(mode="json")
                act_dict["_index"] = idx
                act_dict["activityName"] = truncate_text(act_dict.get("activityName"), 80)
                act_dict["operator"] = truncate_text(act_dict.get("operator"), 80)
                act_dict["notes"] = truncate_text(act_dict.get("notes"), 150)
                day_activities.append(act_dict)

        # Match transfers
        day_transfers = []
        for idx, tx in enumerate(payload.transfers):
            if tx.date == day_date:
                tx_dict = tx.model_dump(mode="json")
                tx_dict["_index"] = idx
                tx_dict["vehicleRequirement"] = truncate_text(tx_dict.get("vehicleRequirement"), 80)
                tx_dict["fromLocation"] = truncate_text(tx_dict.get("fromLocation"), 60)
                tx_dict["toLocation"] = truncate_text(tx_dict.get("toLocation"), 60)
                tx_dict["notes"] = truncate_text(tx_dict.get("notes"), 150)
                day_transfers.append(tx_dict)

        # Match flights
        day_flights = []
        for idx, fl in enumerate(payload.flights):
            if fl.date == day_date:
                fl_dict = fl.model_dump(mode="json")
                fl_dict["_index"] = idx
                fl_dict["flightNumber"] = truncate_text(fl_dict.get("flightNumber"), 30)
                fl_dict["airline"] = truncate_text(fl_dict.get("airline"), 50)
                fl_dict["fromCity"] = truncate_text(fl_dict.get("fromCity"), 40)
                fl_dict["toCity"] = truncate_text(fl_dict.get("toCity"), 40)
                fl_dict["notes"] = truncate_text(fl_dict.get("notes"), 150)
                day_flights.append(fl_dict)

        # Match guides
        day_guides = []
        for idx, gd in enumerate(payload.guides):
            if gd.dates and day_date in gd.dates:
                gd_dict = gd.model_dump(mode="json")
                gd_dict["_index"] = idx
                gd_dict["guideName"] = truncate_text(gd_dict.get("guideName"), 60)
                gd_dict["destination"] = truncate_text(gd_dict.get("destination"), 60)
                gd_dict["notes"] = truncate_text(gd_dict.get("notes"), 150)
                day_guides.append(gd_dict)

        days_list.append({
            "dayNumber": day.dayNumber,
            "date": day_date,
            "title": truncate_text(day.title, 80),
            "description": [truncate_text(d, 350) for d in day.description],
            "overnight": truncate_text(day.overnight, 40),
            "meals": [truncate_text(m, 80) for m in (day.meals or [])],
            "destinations": [truncate_text(dest, 40) for dest in (day.destinations or [])],
            "activities": [truncate_text(act, 120) for act in (day.activities or [])],
            "optionalActivities": [truncate_text(opt, 120) for opt in (day.optionalActivities or [])],
            "notes": [truncate_text(nt, 150) for nt in (day.notes or [])],
            "booked_hotels": day_hotels,
            "booked_activities": day_activities,
            "booked_transfers": day_transfers,
            "booked_flights": day_flights,
            "booked_guides": day_guides,
        })

    return {
        "itinerary_id":     itinerary_id,
        "img_0": img_0, "img_1": img_1, "img_2": img_2, "img_3": img_3, "img_4": img_4,
        "destinations":     destinations,
        # Hero / header
        "quotation_title":  truncate_text(payload.quotationTitle, 100),
        "tour_title":       tour_title,
        "kicker":           f"Confirmed Booking Itinerary • {duration_lbl} • {travel_dates}",
        "lede":             lede,
        # Guest & trip meta
        "customer_name":    prepared_for,
        "nationality":      nationality,
        "travel_style":     travel_style,
        "guests_txt":       guests_txt,
        "guests_adults":    payload.guests.adults,
        "guests_children":   payload.guests.children,
        "route_txt":        route_txt,
        "duration_label":   duration_lbl,
        "travel_dates":     travel_dates,
        # Seller / contact
        "seller_name":      seller_name,
        "seller_email":     seller_email,
        "contact":          seller_phone,
        "contact_web":      "www.vietnamsafar.vn",
        "contact_phone":    seller_phone,
        "quotation_number": payload.quotationNumber or itinerary_id,
        "valid_until":      "N/A",
        # Overview
        "overview_heading": overview_heading,
        "overview_h2":      f"{prepared_for} — {tour_title}",
        "overview_p":       " ".join(overview_paras),
        "overview_paras":   overview_paras,
        # Experiences
        "experiences":      experiences,
        # Daily Itinerary with matched services
        "itinerary":        days_list,
        # Consolidated list of booked services (useful for summary tabs/cards!)
        "hotels":           [
            {
                **h.model_dump(mode="json"),
                "name": truncate_text(h.name, 80),
                "roomType": truncate_text(h.roomType, 80),
                "destination": truncate_text(h.destination, 60),
                "notes": truncate_text(h.notes, 150)
            } for h in payload.hotels
        ],
        "activities":       [
            {
                **act.model_dump(mode="json"),
                "activityName": truncate_text(act.activityName, 80),
                "operator": truncate_text(act.operator, 80),
                "notes": truncate_text(act.notes, 150)
            } for act in payload.activities
        ],
        "transfers":        [
            {
                **tx.model_dump(mode="json"),
                "vehicleRequirement": truncate_text(tx.vehicleRequirement, 80),
                "fromLocation": truncate_text(tx.fromLocation, 60),
                "toLocation": truncate_text(tx.toLocation, 60),
                "notes": truncate_text(tx.notes, 150)
            } for tx in payload.transfers
        ],
        "flights":          [
            {
                **fl.model_dump(mode="json"),
                "flightNumber": truncate_text(fl.flightNumber, 30),
                "airline": truncate_text(fl.airline, 50),
                "fromCity": truncate_text(fl.fromCity, 40),
                "toCity": truncate_text(fl.toCity, 40),
                "notes": truncate_text(fl.notes, 150)
            } for fl in payload.flights
        ],
        "guides":           [
            {
                **gd.model_dump(mode="json"),
                "guideName": truncate_text(gd.guideName, 60),
                "destination": truncate_text(gd.destination, 60),
                "notes": truncate_text(gd.notes, 150)
            } for gd in payload.guides
        ],
        # Inclusions / exclusions
        "inclusions":       inc_lines,
        "exclusions":       exc_lines,
        "notes":            [truncate_text(x, 200) for x in (payload.notes or [])],
        # Pricing section
        "currency":       currency,
        "pricing_title":  truncate_text(payload.pricing.pricingTitle or "PRICE QUOTATION – B2B NET INDICATIVE" if payload.pricing else "", 100),
        "pricing_basis":  truncate_text(payload.pricing.basis or "B2B net indicative" if payload.pricing else "", 80),
        "price_options":  [
            {
                **o.model_dump(mode="json"),
                "hotelCategory": truncate_text(o.hotelCategory, 80),
                "optionName": truncate_text(o.optionName, 80),
                "notes": [truncate_text(n, 150) for n in o.notes] if o.notes else []
            } for o in payload.pricing.priceOptions
        ] if payload.pricing else [],
        "price_per_pax":  price_per_pax,
        "total_price":    total_price,
        "grand_total":    grand_total_num,
        "subtotal":       payload.pricing.subtotal if payload.pricing else 0.0,
        "tax_total":      payload.pricing.taxTotal if payload.pricing else 0.0,
        "pricing_h2":     f"B2B Net Price: {total_price}" if total_price else "",
        "pricing_p":      f"Grand total for {guests_txt}. Currency: {currency}." if total_price else "",
        # Footer
        "footer_text":      f"{tour_title} — Detailed booking itinerary prepared for {prepared_for}.",
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.post("/quotations/b2c")
async def create_quotation_b2c(request: Request):
    """
    Receives structured B2C quotation data,
    renders a B2C Jinja2 landing page template, stores it, and returns the preview URL.
    """
    body = await request.json()
    log.debug("[/quotations/b2c] Incoming keys: %s", list(body.keys()))

    # Unwrap ChatGPT Action wrapper if present
    data = body.get("params", body)
    log.debug("[/quotations/b2c] Data keys after unwrap: %s", list(data.keys()))

    try:
        payload = TourQuotationPayload.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        log.error("[/quotations/b2c] Pydantic validation failed — %d error(s):\n%s",
                  len(errors), json.dumps(errors, indent=2, default=str))
        return JSONResponse(status_code=422, content={"detail": errors,
            "hint": "Field path is in 'loc'. Check which required field is missing."})

    quotation_id = f"quo_{uuid.uuid4().hex[:12]}"

    # ── Extract destinations from route + itinerary for the gallery ──────────
    route_list = []
    for d in payload.itinerary:
        if d.destination and d.destination not in route_list:
            route_list.append(d.destination)
    route_text = " ".join(route_list)
    itinerary_text = " ".join(
        (day.destination or "") + " " + (day.summary or "")
        for day in payload.itinerary
    )
    text_context = route_text + " " + itinerary_text

    from image_selector import extract_and_map_destinations, get_random_image_for_province
    destinations = await extract_and_map_destinations(text_context, max_items=None)
    
    # Resolve image urls for each destination
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))

    log.debug("[/quotations/b2c] Extracted destinations: %s", destinations)

    default_img = "/assets/vietnam-safar-logo.png"
    
    # Hero image: Pick a random image from the resolved destinations, or default
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/quotations/b2c] Hero image resolved: %s", hero_image_url)

    ctx = _build_ctx(quotation_id, payload, hero_image_url, destinations)

    # ── Render landing page HTML ───────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    tmpl_lp  = templates.get_template("vietnam_heritage_luxury_b2c.html")
    tmpl_pdf = templates.get_template("vietnam_heritage_luxury_b2c_pdf.html")

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
    published_url: str | None = None
    pdf_static_url: str | None = None
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

    if ENVIRONMENT == "production":
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            log.error("[/quotations/b2c] GITHUB_TOKEN or GITHUB_REPO not set — cannot persist on Vercel.")
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
            log.info("[/quotations/b2c] ✓ v1 + pdf.html committed to GitHub → %s", published_url)
        except Exception as exc:
            log.exception("[/quotations/b2c] GitHub publish FAILED for %s: %s", quotation_id, exc)
            raise HTTPException(
                status_code=502,
                detail=f"GitHub publish failed: {exc}. Check GITHUB_TOKEN permissions.",
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
        log.info("[/quotations/b2c] Localhost: v1.html + pdf.html + ctx.json written to disk.")

    log.info("[/quotations/b2c] ✓ id=%s  preparedFor=%s  days=%d",
             quotation_id, payload.journeyGlance.guestProfile, len(payload.itinerary))

    quotation_url = f"{PUBLIC_BASE_URL}/quotations/{quotation_id}"
    return {
        "quotationId":  quotation_id,
        "status":       "published",
        "version":      1,
        "message":      "B2C Landing page published. Open quotationUrl to preview and edit inline.",
        "quotationUrl": quotation_url,
        "pdfUrl":       f"{PUBLIC_BASE_URL}/quotations/{quotation_id}/pdf",
    }


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
        payload = TourQuotationPayload.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        log.error("[/quotations] Pydantic validation failed — %d error(s):\n%s",
                  len(errors), json.dumps(errors, indent=2, default=str))
        return JSONResponse(status_code=422, content={"detail": errors,
            "hint": "Field path is in 'loc'. Check which required field is missing."})

    quotation_id = f"quo_{uuid.uuid4().hex[:12]}"

    # ── Extract destinations from route + itinerary for the gallery ──────────
    route_list = []
    for d in payload.itinerary:
        if d.destination and d.destination not in route_list:
            route_list.append(d.destination)
    route_text = " ".join(route_list)
    itinerary_text = " ".join(
        (day.destination or "") + " " + (day.summary or "")
        for day in payload.itinerary
    )
    text_context = route_text + " " + itinerary_text

    from image_selector import extract_and_map_destinations, get_random_image_for_province
    destinations = await extract_and_map_destinations(text_context, max_items=None)
    
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

    log.info("[/quotations] ✓ id=%s  preparedFor=%s  days=%d  route=%s",
             quotation_id, payload.journeyGlance.guestProfile,
             len(payload.itinerary), " > ".join(route_list))

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


# ── GET /published/{file_path:path} — Dynamic static files ────────────────────

@app.get("/published/{file_path:path}")
async def get_published_file(file_path: str):
    """
    Serve files from the local 'published' directory if they exist.
    On Vercel (where no rebuild happens and local file might be missing),
    fetch the file directly from GitHub API and serve it.
    """
    import mimetypes
    from fastapi.responses import Response, FileResponse

    local_path = os.path.join("published", file_path)
    if os.path.isfile(local_path):
        return FileResponse(local_path)
        
    # File not found locally - if we are on Vercel, try fetching from GitHub
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        import httpx
        repo = os.getenv("GITHUB_REPO")
        token = os.getenv("GITHUB_TOKEN")
        if repo and token:
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {
                    "Authorization": f"token {token}", 
                    "Accept": "application/vnd.github.v3.raw"
                }
                gh_url = f"https://api.github.com/repos/{repo}/contents/published/{file_path}"
                resp = await client.get(gh_url, headers=headers)
                if resp.status_code == 200:
                    log.info("[/published] Fetched %s from GitHub API", file_path)
                    mt, _ = mimetypes.guess_type(file_path)
                    if not mt:
                        mt = "application/octet-stream"
                    return Response(content=resp.content, media_type=mt)
                    
    raise HTTPException(status_code=404, detail=f"File {file_path} not found.")


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

class ApproveRequest(BaseModel):
    html: str
    token: str

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



# ── Detailed Itinerary Endpoints ─────────────────────────────────────────────

@app.post("/itineraries")
async def create_itinerary(request: Request):
    """
    Receives structured itinerary data, renders a Jinja2 template with booked services,
    stores it locally or on GitHub, and returns the preview/PDF URLs.
    """
    body = await request.json()
    log.debug("[/itineraries] Incoming keys: %s", list(body.keys()))

    # Unwrap ChatGPT Action wrapper if present
    data = body.get("params", body)
    log.debug("[/itineraries] Data keys after unwrap: %s", list(data.keys()))

    try:
        payload = DetailItineraryPayload.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors()
        log.error("[/itineraries] Pydantic validation failed — %d error(s):\n%s",
                  len(errors), json.dumps(errors, indent=2, default=str))
        return JSONResponse(status_code=422, content={"detail": errors,
            "hint": "Field path is in 'loc'. Check which required field is missing."})

    itinerary_id = f"iti_{uuid.uuid4().hex[:12]}"

    # Extract destinations from route + itinerary for the gallery
    route_text = " ".join(payload.route)
    itinerary_text = " ".join(
        " ".join(day.destinations or []) + " " + day.title
        for day in payload.itinerary
    )
    text_context = route_text + " " + itinerary_text
    if payload.notes:
        text_context += " " + " ".join(payload.notes)

    from image_selector import extract_and_map_destinations, get_random_image_for_province
    destinations = await extract_and_map_destinations(text_context, max_items=None)
    
    # Resolve image urls for each destination
    for d in destinations:
        d["image_url"] = get_random_image_for_province(d.get("slug"))

    log.debug("[/itineraries] Extracted destinations: %s", destinations)

    default_img = "/assets/vietnam-safar-logo.png"
    
    # Hero image: Pick a random image from the resolved destinations, or default
    valid_images = [d["image_url"] for d in destinations if d.get("image_url") != default_img]
    if valid_images:
        import random
        hero_image_url = random.choice(valid_images)
    else:
        hero_image_url = default_img

    log.debug("[/itineraries] Hero image resolved: %s", hero_image_url)

    # Let's check hotels and activities image URLs. If they don't have them, we can try resolving one!
    for h in payload.hotels:
        if not h.imageUrl:
            from image_selector import get_province_slug_for_location
            slug = await get_province_slug_for_location(h.destination or h.addressArea)  # type: ignore
            h.imageUrl = get_random_image_for_province(slug)

    for act in payload.activities:
        if not act.imageUrl:
            from image_selector import get_province_slug_for_location
            slug = await get_province_slug_for_location(act.area or act.activityName)
            act.imageUrl = get_random_image_for_province(slug)

    ctx = _build_itinerary_ctx(itinerary_id, payload, hero_image_url, destinations)

    # Render landing page HTML and PDF
    loop = asyncio.get_event_loop()
    tmpl_lp  = templates.get_template("detail_itinerary_landingpage_template.html")
    tmpl_pdf = templates.get_template("detail_itinerary_landingpage_template_pdf.html")

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render,  **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )

    # Update in-memory store
    itineraries[itinerary_id] = {
        "payload":       payload.model_dump(mode="json"),
        "ctx":           ctx,
        "html":          rendered_html,
        "pdf_html":      rendered_pdf,
        "status":        "pending",
        "published_url": None,
        "pdf_url":       None,
        "version":       0,
    }

    published_url: str | None = None
    pdf_static_url: str | None = None
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

    if ENVIRONMENT == "production":
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            log.error("[/itineraries] GITHUB_TOKEN or GITHUB_REPO not set — cannot persist on Vercel.")
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: GITHUB_TOKEN / GITHUB_REPO env vars are missing.",
            )
        try:
            # Commit to GitHub
            published_url, pdf_static_url = await asyncio.gather(
                publish_to_github(
                    quotation_id=itinerary_id,  # will publish to published/{itinerary_id}
                    html_content=rendered_html,
                    version=1,
                ),
                publish_file_to_github(
                    file_path=f"published/{itinerary_id}/pdf.html",
                    html_content=rendered_pdf,
                    commit_message=f"Publish PDF view for itinerary {itinerary_id}",
                ),
            )
            itineraries[itinerary_id]["status"]        = "published"
            itineraries[itinerary_id]["published_url"] = published_url
            itineraries[itinerary_id]["pdf_url"]       = pdf_static_url
            itineraries[itinerary_id]["version"]       = 1
            log.info("[/itineraries] ✓ v1 + pdf.html committed to GitHub → %s", published_url)
        except Exception as exc:
            log.exception("[/itineraries] GitHub publish FAILED for %s: %s", itinerary_id, exc)
            raise HTTPException(
                status_code=502,
                detail=f"GitHub publish failed: {exc}.",
            )
    else:
        # Localhost: write to disk
        iti_dir = os.path.join("published", itinerary_id)
        os.makedirs(iti_dir, exist_ok=True)
        with open(os.path.join(iti_dir, "v1.html"),  "w", encoding="utf-8") as _f:
            _f.write(rendered_html)
        with open(os.path.join(iti_dir, "pdf.html"), "w", encoding="utf-8") as _f:
            _f.write(rendered_pdf)
        with open(os.path.join(iti_dir, "ctx.json"), "w", encoding="utf-8") as _f:
            json.dump(ctx, _f, ensure_ascii=False, default=str)
        itineraries[itinerary_id]["status"]  = "published"
        itineraries[itinerary_id]["version"] = 1
        log.info("[/itineraries] Localhost: v1.html + pdf.html + ctx.json written to disk.")

    log.info("[/itineraries] ✓ id=%s  preparedFor=%s  days=%d",
             itinerary_id, payload.preparedFor, payload.duration.days)

    itinerary_url = f"{PUBLIC_BASE_URL}/itineraries/{itinerary_id}"
    return {
        "itineraryId":  itinerary_id,
        "status":       "published",
        "version":      1,
        "message":      "Itinerary page published. Open itineraryUrl to preview and edit inline.",
        "itineraryUrl": itinerary_url,
        "pdfUrl":       f"{PUBLIC_BASE_URL}/itineraries/{itinerary_id}/pdf",
    }


@app.get("/itineraries/{itinerary_id}", response_class=HTMLResponse)
async def get_itinerary(itinerary_id: str):
    """
    Stable permalink for an itinerary. Serves from memory, disk, then GitHub.
    """
    # 1. In-memory fast path
    entry = itineraries.get(itinerary_id)
    if entry and entry.get("html"):
        return HTMLResponse(content=entry["html"])

    # 2. Local disk fallback
    for version in range(10, 0, -1):
        path = os.path.join("published", itinerary_id, f"v{version}.html")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())

    # 3. GitHub fallback
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        import httpx
        repo = os.getenv("GITHUB_REPO")
        token = os.getenv("GITHUB_TOKEN")
        if repo and token:
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.raw"}
                for version in range(10, 0, -1):
                    gh_url = f"https://api.github.com/repos/{repo}/contents/published/{itinerary_id}/v{version}.html"
                    resp = await client.get(gh_url, headers=headers)
                    if resp.status_code == 200:
                        log.info("[/itineraries] Fetched %s directly from GitHub API.", itinerary_id)
                        return HTMLResponse(content=resp.text)

    raise HTTPException(status_code=404, detail=f"Itinerary '{itinerary_id}' not found. It may still be deploying.")


@app.get("/itineraries/{itinerary_id}/pdf", response_class=HTMLResponse)
async def get_itinerary_pdf(itinerary_id: str):
    """ Serves A4 PDF view for itinerary. """
    from fastapi.responses import RedirectResponse

    entry = itineraries.get(itinerary_id)
    if entry and entry.get("pdf_url"):
        return RedirectResponse(url=entry["pdf_url"], status_code=302)

    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        static_pdf_url = f"{PUBLIC_BASE_URL}/published/{itinerary_id}/pdf.html"
        return RedirectResponse(url=static_pdf_url, status_code=302)

    ctx = _load_itinerary_ctx(itinerary_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Itinerary '{itinerary_id}' not found.")
    loop = asyncio.get_event_loop()
    tmpl = templates.get_template("detail_itinerary_landingpage_template_pdf.html")
    rendered = await loop.run_in_executor(None, partial(tmpl.render, **ctx))
    log.info("[/itineraries/pdf] Served dynamic PDF view for %s", itinerary_id)
    return HTMLResponse(content=rendered)


@app.post("/itineraries/{itinerary_id}/publish")
async def publish_itinerary(itinerary_id: str, body: PublishRequest):
    """ Saves inline edits back to the system. """
    from github_publish import get_next_version, publish_to_github
    version = await get_next_version(itinerary_id)

    # Update ctx.json and pdf.html using values from the edited HTML
    from html.parser import HTMLParser
    
    class ServiceCardParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cards = []
            
        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if 'class' in attrs_dict and 'service-card' in attrs_dict['class']:  # type: ignore
                self.cards.append(attrs_dict)

    parser = ServiceCardParser()
    parser.feed(body.html)
    
    ctx = _load_itinerary_ctx(itinerary_id)
    rendered_pdf = None
    if ctx:
        for card in parser.cards:
            card_type = card.get("data-type")
            idx_str = card.get("data-index")
            if idx_str is None:
                continue
            idx = int(idx_str)
            
            if card_type == "hotel":
                if idx < len(ctx.get("hotels", [])):
                    h = ctx["hotels"][idx]
                    h["pricePerNightUsd"] = float(card.get("data-price-per-night", 0))
                    h["nights"] = int(card.get("data-nights", 0))
                    h["rooms"] = int(card.get("data-rooms", 1))
            elif card_type == "activity":
                if idx < len(ctx.get("activities", [])):
                    act = ctx["activities"][idx]
                    act["pricePerAdultUsd"] = float(card.get("data-price-adult", 0))
                    act["pricePerChildUsd"] = float(card.get("data-price-child", 0))
                    adults = int(card.get("data-adults", ctx.get("guests_adults") or 0))
                    children = int(card.get("data-children", ctx.get("guests_children") or 0))
                    act["totalEstimateUsd"] = (act["pricePerAdultUsd"] * adults) + (act["pricePerChildUsd"] * children)
            elif card_type == "transfer":
                if idx < len(ctx.get("transfers", [])):
                    tx = ctx["transfers"][idx]
                    base = float(card.get("data-base-cost", 0))
                    tolls = float(card.get("data-tolls", 0))
                    overnight = float(card.get("data-overnight", 0))
                    surcharges = float(card.get("data-surcharges", 0))
                    vat = float(card.get("data-vat", 0))
                    tx["priceUsd"] = base + tolls + overnight + surcharges + vat
            elif card_type == "flight":
                if idx < len(ctx.get("flights", [])):
                    fl = ctx["flights"][idx]
                    fl["priceUsd"] = float(card.get("data-price-ticket", 0))
            elif card_type == "guide":
                if idx < len(ctx.get("guides", [])):
                    gd = ctx["guides"][idx]
                    gd["pricePerDayUsd"] = float(card.get("data-price-day", 0))
                    gd["days"] = int(card.get("data-days", 0))
                    gd["totalEstimateUsd"] = gd["pricePerDayUsd"] * gd["days"]

        # Recalculate Grand Total in ctx
        grand_total = 0.0
        for h in ctx.get("hotels", []):
            grand_total += (h.get("pricePerNightUsd") or 0.0) * (h.get("nights") or 0) * (h.get("rooms") or 1)
        for act in ctx.get("activities", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (act.get("pricePerAdultUsd") or 0.0) * adults + (act.get("pricePerChildUsd") or 0.0) * children
        for tx in ctx.get("transfers", []):
            grand_total += tx.get("priceUsd") or 0.0
        for fl in ctx.get("flights", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (fl.get("priceUsd") or 0.0) * (adults + children)
        for gd in ctx.get("guides", []):
            grand_total += (gd.get("pricePerDayUsd") or 0.0) * (gd.get("days") or 0)

        ctx["grand_total"] = grand_total
        
        if ctx.get("price_options"):
            for opt in ctx["price_options"]:
                if opt.get("isConfirmedMainOption"):
                    opt["totalPrice"]["amount"] = grand_total
                    opt["totalPrice"]["displayText"] = f"${grand_total:,.0f} total"
                    guests_adults = ctx.get("guests_adults") or 1
                    per_person = grand_total / guests_adults
                    opt["pricePerPerson"]["amount"] = per_person
                    opt["pricePerPerson"]["displayText"] = f"${per_person:,.0f} per adult"
            
            main_option = next((o for o in ctx["price_options"] if o.get("isConfirmedMainOption")), None)
            if main_option:
                ctx["total_price"] = main_option["totalPrice"]["displayText"]
                ctx["price_per_pax"] = main_option["pricePerPerson"]["displayText"]
                ctx["pricing_h2"] = f"B2B Net Price: {ctx['total_price']}"
                ctx["pricing_p"] = f"Grand total for {ctx['guests_txt']}. Currency: {ctx['currency']}."

        loop = asyncio.get_event_loop()
        tmpl_pdf = templates.get_template("detail_itinerary_landingpage_template_pdf.html")
        rendered_pdf = await loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx))
        
        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            from github_publish import publish_file_to_github
            try:
                await asyncio.gather(
                    publish_file_to_github(
                        file_path=f"published/{itinerary_id}/pdf.html",
                        html_content=rendered_pdf,
                        commit_message=f"Update PDF view for itinerary {itinerary_id} (version {version})",
                    ),
                    publish_file_to_github(
                        file_path=f"published/{itinerary_id}/ctx.json",
                        html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                        commit_message=f"Update context for itinerary {itinerary_id} (version {version})",
                    )
                )
            except Exception as e:
                log.warning("Failed to publish updated PDF/ctx to GitHub: %s", e)
        else:
            iti_dir = os.path.join("published", itinerary_id)
            os.makedirs(iti_dir, exist_ok=True)
            with open(os.path.join(iti_dir, "ctx.json"), "w", encoding="utf-8") as _f:
                json.dump(ctx, _f, ensure_ascii=False, default=str)
            with open(os.path.join(iti_dir, "pdf.html"), "w", encoding="utf-8") as _f:
                _f.write(rendered_pdf)

    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        try:
            published_url = await publish_to_github(
                quotation_id=itinerary_id,
                html_content=body.html,
                version=version,
            )
        except Exception as exc:
            log.exception("[publish_itinerary] Failed for %s", itinerary_id)
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        # Localhost: write to disk
        iti_dir = os.path.join("published", itinerary_id)
        os.makedirs(iti_dir, exist_ok=True)
        filename = f"v{version}.html"
        file_path = os.path.join(iti_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body.html)
        published_url = f"{PUBLIC_BASE_URL}/published/{itinerary_id}/{filename}"
        log.info("[publish_itinerary] Localhost: wrote to disk %s", file_path)

    entry = itineraries.get(itinerary_id)
    if entry:
        entry["status"]        = "published"
        entry["published_url"] = published_url
        entry["html"]          = body.html
        if ctx:
            entry["ctx"]       = ctx
            entry["pdf_html"]  = rendered_pdf
        entry["version"]       = version

    log.info("[publish_itinerary] ✓ %s v%d → %s", itinerary_id, version, published_url)
    return {"published_url": published_url, "version": version, "status": "published"}


@app.post("/itineraries/{itinerary_id}/approve")
async def approve_itinerary(itinerary_id: str, body: ApproveRequest):
    """
    Saves inline edits back to the system, recalculates ctx/PDF,
    and calls the DMC Core webhook with the JWT token.
    """
    from github_publish import get_next_version, publish_to_github
    version = await get_next_version(itinerary_id)

    # 1. Update ctx.json and pdf.html using values from the edited HTML
    from html.parser import HTMLParser
    
    class ServiceCardParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cards = []
            
        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if 'class' in attrs_dict and 'service-card' in attrs_dict['class']:  # type: ignore
                self.cards.append(attrs_dict)

    parser = ServiceCardParser()
    parser.feed(body.html)
    
    ctx = _load_itinerary_ctx(itinerary_id)
    rendered_pdf = None
    if ctx:
        for card in parser.cards:
            card_type = card.get("data-type")
            idx_str = card.get("data-index")
            if idx_str is None:
                continue
            idx = int(idx_str)
            
            if card_type == "hotel":
                if idx < len(ctx.get("hotels", [])):
                    h = ctx["hotels"][idx]
                    h["pricePerNightUsd"] = float(card.get("data-price-per-night", 0))
                    h["nights"] = int(card.get("data-nights", 0))
                    h["rooms"] = int(card.get("data-rooms", 1))
            elif card_type == "activity":
                if idx < len(ctx.get("activities", [])):
                    act = ctx["activities"][idx]
                    act["pricePerAdultUsd"] = float(card.get("data-price-adult", 0))
                    act["pricePerChildUsd"] = float(card.get("data-price-child", 0))
                    adults = int(card.get("data-adults", ctx.get("guests_adults") or 0))
                    children = int(card.get("data-children", ctx.get("guests_children") or 0))
                    act["totalEstimateUsd"] = (act["pricePerAdultUsd"] * adults) + (act["pricePerChildUsd"] * children)
            elif card_type == "transfer":
                if idx < len(ctx.get("transfers", [])):
                    tx = ctx["transfers"][idx]
                    base = float(card.get("data-base-cost", 0))
                    tolls = float(card.get("data-tolls", 0))
                    overnight = float(card.get("data-overnight", 0))
                    surcharges = float(card.get("data-surcharges", 0))
                    vat = float(card.get("data-vat", 0))
                    tx["priceUsd"] = base + tolls + overnight + surcharges + vat
            elif card_type == "flight":
                if idx < len(ctx.get("flights", [])):
                    fl = ctx["flights"][idx]
                    fl["priceUsd"] = float(card.get("data-price-ticket", 0))
            elif card_type == "guide":
                if idx < len(ctx.get("guides", [])):
                    gd = ctx["guides"][idx]
                    gd["pricePerDayUsd"] = float(card.get("data-price-day", 0))
                    gd["days"] = int(card.get("data-days", 0))
                    gd["totalEstimateUsd"] = gd["pricePerDayUsd"] * gd["days"]

        # Recalculate Grand Total in ctx
        grand_total = 0.0
        for h in ctx.get("hotels", []):
            grand_total += (h.get("pricePerNightUsd") or 0.0) * (h.get("nights") or 0) * (h.get("rooms") or 1)
        for act in ctx.get("activities", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (act.get("pricePerAdultUsd") or 0.0) * adults + (act.get("pricePerChildUsd") or 0.0) * children
        for tx in ctx.get("transfers", []):
            grand_total += tx.get("priceUsd") or 0.0
        for fl in ctx.get("flights", []):
            adults = ctx.get("guests_adults") or 0
            children = ctx.get("guests_children") or 0
            grand_total += (fl.get("priceUsd") or 0.0) * (adults + children)
        for gd in ctx.get("guides", []):
            grand_total += (gd.get("pricePerDayUsd") or 0.0) * (gd.get("days") or 0)

        ctx["grand_total"] = grand_total
        
        if ctx.get("price_options"):
            for opt in ctx["price_options"]:
                if opt.get("isConfirmedMainOption"):
                    opt["totalPrice"]["amount"] = grand_total
                    opt["totalPrice"]["displayText"] = f"${grand_total:,.0f} total"
                    guests_adults = ctx.get("guests_adults") or 1
                    per_person = grand_total / guests_adults
                    opt["pricePerPerson"]["amount"] = per_person
                    opt["pricePerPerson"]["displayText"] = f"${per_person:,.0f} per adult"
            
            main_option = next((o for o in ctx["price_options"] if o.get("isConfirmedMainOption")), None)
            if main_option:
                ctx["total_price"] = main_option["totalPrice"]["displayText"]
                ctx["price_per_pax"] = main_option["pricePerPerson"]["displayText"]
                ctx["pricing_h2"] = f"B2B Net Price: {ctx['total_price']}"
                ctx["pricing_p"] = f"Grand total for {ctx['guests_txt']}. Currency: {ctx['currency']}."

        loop = asyncio.get_event_loop()
        tmpl_pdf = templates.get_template("detail_itinerary_landingpage_template_pdf.html")
        rendered_pdf = await loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx))
        
        ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
        if ENVIRONMENT == "production":
            from github_publish import publish_file_to_github
            try:
                await asyncio.gather(
                    publish_file_to_github(
                        file_path=f"published/{itinerary_id}/pdf.html",
                        html_content=rendered_pdf,
                        commit_message=f"Update PDF view for approved itinerary {itinerary_id} (version {version})",
                    ),
                    publish_file_to_github(
                        file_path=f"published/{itinerary_id}/ctx.json",
                        html_content=json.dumps(ctx, ensure_ascii=False, default=str),
                        commit_message=f"Update context for approved itinerary {itinerary_id} (version {version})",
                    )
                )
            except Exception as e:
                log.warning("Failed to publish approved PDF/ctx to GitHub: %s", e)
        else:
            iti_dir = os.path.join("published", itinerary_id)
            os.makedirs(iti_dir, exist_ok=True)
            with open(os.path.join(iti_dir, "ctx.json"), "w", encoding="utf-8") as _f:
                json.dump(ctx, _f, ensure_ascii=False, default=str)
            with open(os.path.join(iti_dir, "pdf.html"), "w", encoding="utf-8") as _f:
                _f.write(rendered_pdf)

    # 2. Save the edited HTML
    ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
    if ENVIRONMENT == "production":
        try:
            published_url = await publish_to_github(
                quotation_id=itinerary_id,
                html_content=body.html,
                version=version,
            )
        except Exception as exc:
            log.exception("[approve_itinerary] Failed to publish HTML for %s", itinerary_id)
            raise HTTPException(status_code=502, detail=str(exc))
    else:
        # Localhost: write to disk
        iti_dir = os.path.join("published", itinerary_id)
        os.makedirs(iti_dir, exist_ok=True)
        filename = f"v{version}.html"
        file_path = os.path.join(iti_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body.html)
        published_url = f"{PUBLIC_BASE_URL}/published/{itinerary_id}/{filename}"
        log.info("[approve_itinerary] Localhost: wrote to disk %s", file_path)

    # Update in-memory
    entry = itineraries.get(itinerary_id)
    if entry:
        entry["status"]        = "approved"
        entry["published_url"] = published_url
        entry["html"]          = body.html
        if ctx:
            entry["ctx"]       = ctx
            entry["pdf_html"]  = rendered_pdf
        entry["version"]       = version

    # 3. Webhook callback to DMC Core
    dmc_core_url = (os.environ.get("DMC_CORE_URL") or "http://localhost:8000").rstrip("/")
    webhook_url = f"{dmc_core_url}/webhooks/landing-page/approve"
    log.info("[approve_itinerary] Triggering callback to DMC Core: %s", webhook_url)
    
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {body.token}"}
            payload = {
                "itinerary_id": itinerary_id,
                "status": "approved",
                "grand_total": grand_total if ctx else 0.0
            }
            resp = await client.post(webhook_url, json=payload, headers=headers)
            log.info("[approve_itinerary] DMC Core response status: %d, body: %s", resp.status_code, resp.text)
            if resp.status_code not in (200, 201):
                log.error("[approve_itinerary] DMC Core webhook returned error status %d", resp.status_code)
                raise HTTPException(status_code=502, detail=f"DMC Core webhook callback failed: status {resp.status_code}")
    except Exception as exc:
        log.exception("[approve_itinerary] DMC Core callback failed: %s", exc)
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=502, detail=f"DMC Core callback failed: {exc}")

    log.info("[approve_itinerary] ✓ %s approved v%d → %s", itinerary_id, version, published_url)
    return {"published_url": published_url, "version": version, "status": "approved"}


# ── Landing page (static demo) ───────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_landing_page():
    # Serve the original static demo file directly
    with open("vietnam-heritage-luxury-landingpage.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("assets/vietnam-safar-logo.png", media_type="image/png")


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    from fastapi.responses import Response
    content = """// Service Worker for Vietnam Safar PWA
const CACHE_NAME = 'vietnam-safar-v2';
const ASSETS = [
  '/',
  '/favicon.ico',
  '/assets/vietnam-safar-logo.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if (!event.request.url.startsWith('http')) return;

  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(event.request) || caches.match('/');
      })
    );
    return;
  }
  
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).then(networkResponse => {
        if (networkResponse && networkResponse.status === 200 && (event.request.url.includes('/assets/') || event.request.url.includes('unpkg.com') || event.request.url.includes('basemaps.cartocdn.com'))) {
          const cacheCopy = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, cacheCopy);
          });
        }
        return networkResponse;
      }).catch(() => {});
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const urlToOpen = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
      for (let i = 0; i < windowClients.length; i++) {
        const client = windowClients[i];
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});
"""
    return Response(content=content, media_type="application/javascript")


@app.get("/manifest.json", include_in_schema=False)
async def web_manifest(id: str = None, type: str = None):
    name = "Vietnam Safar - Luxury Travel"
    start_url = "/"
    if id and type:
        start_url = f"/{type}/{id}"
        if type == "quotations":
            entry = quotations.get(id)
            if entry and entry.get("ctx"):
                q_title = entry["ctx"].get("quotation_title") or entry["ctx"].get("tour_title")
                if q_title:
                    name = f"Itinerary: {q_title}"
        elif type == "itineraries":
            entry = itineraries.get(id)
            if entry and entry.get("ctx"):
                i_title = entry["ctx"].get("tour_title") or entry["ctx"].get("quotation_title")
                if i_title:
                    name = f"Itinerary: {i_title}"
                    
    manifest_data = {
        "name": name,
        "short_name": "Vietnam Safar",
        "description": "Your luxury travel itinerary and quotation custom-tailored by Vietnam Safar.",
        "start_url": start_url,
        "display": "standalone",
        "background_color": "#f8f3e9",
        "theme_color": "#17412e",
        "orientation": "any",
        "icons": [
            {
                "src": "/assets/vietnam-safar-logo.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/assets/vietnam-safar-logo.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return manifest_data


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
