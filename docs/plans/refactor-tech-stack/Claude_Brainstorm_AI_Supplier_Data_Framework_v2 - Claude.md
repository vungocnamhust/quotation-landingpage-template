# AI Supplier & Operations Data Framework — v2.0

> **Purpose:** A machine-readable framework covering the full commercial lifecycle:
> raw supplier data → structured rates → costing → quotation → **booking operations → payment tracking**.

> **Changelog v1.0 → v2.0**
> - Added the missing operational layer: Quotations, Bookings, Booking Services, Payables, Receivables (§20–§25)
> - Structured `payment_terms` and `cancellation_policy` (were free text — blocked automated payment tracking) (§12)
> - Split Supplier from Property/Product so the same hotel can be sourced from multiple suppliers (§6)
> - Rewrote the rate model as **Price Lines** to fix the `net_rate` vs `adult_rate` ambiguity (§10)
> - Added occupancy-based accommodation pricing (SGL/DBL/TWN/TRPL, single supplement) (§10.4)
> - Moved child/infant age definitions up to rate level (§11)
> - Added `rate_basis` (NET vs GROSS_COMMISSIONABLE), FOC policy, structured supplements (§10, §13)
> - Added rate versioning + conflict resolution rules (§16)
> - Split `source_type` into `document_type` + `channel` (§8)
> - Split `human_review_status` into `review_status` + `lifecycle_status` (§17)
> - Demoted `confidence_score` to a secondary signal; rule-based validation is now the gate (§18)

---

# 1. Core Objective

The goal is not to make staff manually complete a complex supplier database.

The goal is a consistent framework where raw supplier information can be uploaded and AI can automatically:

1. identify the supplier,
2. identify the service,
3. classify the service,
4. extract the rate,
5. extract validity and commercial conditions,
6. normalize the service into internal terminology,
7. add useful matching tags,
8. flag uncertain or missing data,
9. save the result into a structured supplier database,
10. **carry the confirmed rate into booking operations as an immutable snapshot,**
11. **generate the payment schedule for both supplier and client automatically.**

Target workflow:

```text
RAW SUPPLIER DATA
(PDF / Excel / Email / WhatsApp / Contract / Screenshot / Manual Note)
        ↓
AI EXTRACTION
        ↓
NORMALIZATION
        ↓
STRUCTURED SUPPLIER DATABASE
        ↓
MATCH WITH QUOTATION INTAKE
        ↓
COSTING
        ↓
QUOTATION
        ↓
BOOKING (rate snapshot taken here)
        ↓
OPERATIONS (confirmation / voucher / amendment)
        ↓
PAYABLES + RECEIVABLES
        ↓
RECONCILIATION & MARGIN ACTUALS
```

---

# 2. Design Principle

The system separates four types of information.

## 2.1 Source Fact
Information written directly by the supplier. Immutable.

## 2.2 Normalized Fact
AI converts supplier language into internal standard terminology.

## 2.3 AI Inference
AI-generated interpretation used for future matching. Never overwrites source facts.

## 2.4 Transaction Snapshot *(new in v2.0)*
Once a service is sold, the commercial terms are **copied** into the booking and frozen.
A booking must never read live from the rate table — rates get updated, expire, or are superseded,
but the price agreed with the client and the supplier is fixed at the moment of confirmation.

```text
Rate table   = what we can sell today
Booking line = what we actually sold, at the terms in force that day
```

This single rule prevents the most common failure mode in tour-operator systems:
historical bookings silently changing price when a new rate sheet is imported.

---

# 3. Data Layer Map

```text
LAYER 1 — SOURCE          Suppliers · Properties · Raw Sources
LAYER 2 — CATALOGUE       Services · Rates (Price Lines) · Policies · Tags
LAYER 3 — COMMERCIAL      Quotations · Quotation Lines
LAYER 4 — OPERATIONS      Bookings · Booking Services · Amendments · Vouchers
LAYER 5 — FINANCE         Payables · Receivables · Payments · FX Records
```

Layers 1–2 answer *"what can we sell and at what cost."*
Layers 3–5 answer *"what did we sell, to whom, and who owes what."*

---

# 4. Primary Service Categories

## Accommodation
- Hotel
- Resort
- Boutique Hotel
- Villa
- Overnight Cruise
- Overnight Train
- Lodge
- Homestay
- Other Overnight Accommodation

## Transportation
- 4-seat Car
- 7-seat Car
- 9-seat Limousine Van
- 16-seat Van
- 29-seat Bus
- 35-seat Bus
- 45-seat Bus
- Train
- Ferry / Boat
- Speedboat
- Other Transportation


## Ticket
- Park
- National Park
- Attraction
- Museum
- Heritage Site
- Cable Car
- Boat Ticket
- Entrance Ticket
- Show
- Performance
- Other Admission

## Flights
- Domestic Flight
- Regional Flight
- International Flight
- Charter Flight
- Seaplane
- Helicopter

## Guide
- Local Guide
- Full-trip Guide
- Tour Escort
- Specialist Guide
- Language-specific Guide

## Guide Expense
- Guide Accommodation
- Guide Meals
- Guide Transportation
- Guide Flight
- Guide Train
- Guide Entrance Fee
- Guide Allowance
- Other Guide Expense

## Experience
- Workshop
- Jeep Tour
- Vespa Tour
- Cycling
- Cooking Class
- Food Tour
- Art / Craft Experience
- Wellness
- Cultural Experience
- Private Access
- Expert Meeting
- Photography
- Boat Experience
- Adventure Activity
- Other Experience

## Meal
- Breakfast
- Lunch
- Dinner
- Set Menu
- Fine Dining
- Street Food
- Halal Meal
- Vegetarian Meal
- Special Event Dinner
- Drinks Package
- Other F&B

## Visa
- Standard Visa
- E-visa
- Urgent Visa
- Visa on Arrival Support
- Visa Processing Service
- Special-Nationality Visa

## Others
- Airport Fast Track
- Meet & Assist
- VIP Airport Service
- SIM
- eSIM
- Souvenir
- Welcome Gift
- Porterage
- Lounge
- Photographer
- Security
- Concierge
- Other Ancillary Service

---

# 5. Database Structure

## 5.1 MVP Phase 1 — Supplier Knowledge (build first)

```text
1. Suppliers
2. Properties            ← new
3. Raw Sources
4. Services
5. Rates (Price Lines)   ← restructured
6. Policies              ← new (payment / cancellation / child)
7. AI Extraction Review
```

## 5.2 MVP Phase 2 — Operations & Finance (design now, build next)

```text
8.  Quotations
9.  Bookings
10. Booking Services     ← holds the frozen snapshot
11. Payables
12. Receivables
13. Payments
```

Do not create separate databases per service category.
Category-specific fields live in a JSON/attribute block on the Service record.

---

# 6. Suppliers and Properties

**Why they are separate.** A DMC or wholesaler may sell 50 hotels; the same hotel may be
bought through two sources at two different prices. If a service is only attached to a supplier,
the same hotel cannot be price-compared across sources.

```text
Property (the thing the guest experiences)
   ↕ many-to-many
Supplier (the entity we contract and pay)
   ↓
Service (a sellable product = property + supplier + specific product)
```

## 6.1 Suppliers

```yaml
supplier_id:
supplier_name:
legal_name:
supplier_type:            # see enum below
country:
city:
supplier_categories:
contact_person:
email:
phone:
whatsapp:
website:
preferred_status:
quality_tier:
default_currency:
default_payment_terms_id: # → Policies
credit_terms_days:        # 0 = prepay
tax_code:
bank_details_ref:         # pointer to secure store, never inline
internal_notes:
active:
last_updated:
```

### supplier_type
```text
DIRECT_SUPPLIER      # hotel, restaurant, transport company we contract directly
DMC                  # local destination management company
WHOLESALER
BEDBANK
OTA
FREELANCER           # guide, photographer
GOVERNMENT_BODY      # park authority, visa office
OTHER
```

### preferred_status
```text
PREFERRED
RECOMMENDED
STANDARD
BACKUP
DO_NOT_USE
```

### quality_tier
```text
ULTRA_LUXURY
LUXURY
PREMIUM
STANDARD
VALUE
```

## 6.2 Properties / Products

```yaml
property_id:
property_name:
property_type:            # HOTEL / RESTAURANT / ATTRACTION / VESSEL / VENUE
country:
destination:
address:
geo_lat:
geo_lng:
star_rating:
internal_luxury_tier:
brand_group:
description:
usp_notes:
active:
```

Services reference **both** `supplier_id` and `property_id` (property may be null for
services with no fixed venue, e.g. a freelance guide).

---

# 7. Standard Locations

Free-text destinations break matching. Maintain a controlled location list.

```yaml
location_id:
location_name:
location_type:     # COUNTRY / REGION / CITY / DISTRICT / AIRPORT / PORT / STATION / POI
parent_location_id:
country:
aliases:           # ["HAN", "Noi Bai", "Hanoi Airport"] — AI matches against these
geo_lat:
geo_lng:
```

All `destination`, `origin`, `end_location` fields store `location_id`,
with the supplier's original wording preserved in the source-fact block.

---

# 8. Raw Sources

Every source document is preserved.

```yaml
source_id:
supplier_id:
source_name:
document_type:       # what it is
channel:             # how it arrived
file_format:         # derived automatically from the file
source_file:
source_date:
effective_from:
effective_to:
supersedes_source_id:   # for amendments / new rate sheets
received_by:
received_date:
ai_processed:
review_status:
notes:
```

> **v1.0 fix:** `source_type` previously mixed three concepts
> (document nature, arrival channel, file format). Now split.

### document_type
```text
RATE_SHEET
CONTRACT
AMENDMENT
QUOTATION
PROMOTION
ALLOTMENT_NOTICE
MANUAL_NOTE
OTHER
```

### channel
```text
EMAIL
WHATSAPP
ZALO
PORTAL_DOWNLOAD
IN_PERSON
INTERNAL_UPLOAD
```

### file_format
```text
PDF · EXCEL · WORD · IMAGE · TEXT · CSV
```
---

# 9. Master Service Record

A Service is a sellable product. It carries **no price** — prices live in Price Lines.

```yaml
service_id:
supplier_id:
property_id:              # nullable
category:
subcategory:
supplier_product_name:    # SOURCE FACT — never edited
standardized_service_name:# NORMALIZED FACT
country:
destination_id:
origin_id:
end_location_id:
description:
private_shared:
duration:
duration_unit:
default_min_pax:
default_max_pax:
luxury_level:
category_attributes: {}   # category-specific block, see §13
ai_tags: []
source_id:
active:
```

---

# 10. Master Rate Record — the Price Line model

> **v1.0 fix.** The old record held `net_rate` *and* `adult_rate` *and* `child_rate`
> simultaneously, leaving it ambiguous which one applies. v2.0 splits this into:
> **Rate Header** (validity, currency, commercial terms) → **Price Lines** (one number each).

## 10.1 Rate Header

```yaml
rate_id:
service_id:
supplier_id:
source_id:
source_reference:          # page / sheet / cell for traceability
currency:
rate_basis:                # NET | GROSS_COMMISSIONABLE
commission_pct:            # required if GROSS_COMMISSIONABLE
contract_year:
valid_from:
valid_to:
season_name:
blackout_dates: []
booking_window_from:       # rate only bookable if booked within this window
booking_window_to:
min_pax:
max_pax:
min_stay_nights:
tax_included:
tax_pct:                   # if not included
service_charge_included:
service_charge_pct:
inclusions: []
exclusions: []
payment_terms_id:          # → §12.1 structured
cancellation_policy_id:    # → §12.2 structured
child_policy_id:           # → §12.3 structured
foc_policy: {}             # → §10.5
supplements: []            # → §10.6
allotment: {}              # → §10.7
version:
supersedes_rate_id:
lifecycle_status:          # → §17
review_status:             # → §17
confidence_score:
validation_flags: []
human_verified:
verified_by:
verified_date:
```

## 10.2 Price Line

```yaml
price_line_id:
rate_id:
pricing_unit:              # → §11
price_for:                 # ADULT | CHILD | INFANT | SENIOR | ROOM | VEHICLE | GROUP | GUIDE | UNIT
occupancy_basis:           # SGL | DBL | TWN | TRPL | QUAD | NA        (accommodation)
tier_min_pax:              # for TIERED pricing
tier_max_pax:
amount:
notes:
```

**Rule:** exactly one `amount` per Price Line. A rate with adult + child + infant prices
produces three Price Lines under one Rate Header, not one row with three columns.

## 10.3 Example — a simple ticket

```yaml
rate_header:
  currency: VND
  rate_basis: NET
  valid_from: 2026-01-01
  valid_to: 2026-12-31
price_lines:
  - price_for: ADULT
    pricing_unit: PER_TICKET
    amount: 250000
  - price_for: CHILD
    pricing_unit: PER_TICKET
    amount: 125000
  - price_for: INFANT
    pricing_unit: PER_TICKET
    amount: 0
```

## 10.4 Example — accommodation with occupancy

> **v1.0 fix.** Hotel rates are Room Type × Meal Plan × Season × **Occupancy**.
> A single `net_rate` per room breaks on the first contract where single ≠ double.

```yaml
rate_header:
  service_id: SVC-HOTEL-PREMIER-ROOM
  currency: VND
  rate_basis: NET
  season_name: LOW
  valid_from: 2026-10-01
  valid_to: 2027-03-31
  min_stay_nights: 1
  blackout_dates:
    - from: 2026-12-24
      to: 2027-01-02
      reason: FESTIVE_PERIOD
price_lines:
  - price_for: ROOM
    occupancy_basis: SGL
    pricing_unit: PER_ROOM_PER_NIGHT
    amount: 7000000
  - price_for: ROOM
    occupancy_basis: DBL
    pricing_unit: PER_ROOM_PER_NIGHT
    amount: 8000000
  - price_for: ROOM
    occupancy_basis: TRPL
    pricing_unit: PER_ROOM_PER_NIGHT
    amount: 10000000
  - price_for: UNIT
    pricing_unit: PER_NIGHT
    amount: 2000000
    notes: Extra bed
```

## 10.5 FOC Policy *(new — required for group costing)*

```yaml
foc_policy:
  enabled: true
  foc_type: FULL_FREE          # FULL_FREE | HALF_PRICE | ROOM_ONLY
  every_n_paying_pax: 15
  max_foc: 2
  applies_to: [ADULT]
  notes:
```

Without this, group costing silently overcharges. Common in coach tours, cruises, restaurants.

## 10.6 Supplements *(structured)*

> **v1.0 fix.** "Tet surcharge +30%" as free text cannot be applied automatically —
> AI has no way to know which travel dates it hits.

```yaml
supplements:
  - supplement_id:
    type: PEAK_SEASON          # see enum
    label: Tet surcharge
    value: 30
    unit: PERCENT              # PERCENT | AMOUNT
    applies_to: BASE_RATE      # BASE_RATE | PER_PERSON | PER_NIGHT | PER_VEHICLE
    date_from: 2027-02-14
    date_to: 2027-02-20
    weekdays: []               # e.g. [SAT, SUN] for weekend supplement
    mandatory: true
    currency:
```

### supplement types
```text
PEAK_SEASON · FESTIVE · WEEKEND · PUBLIC_HOLIDAY · SINGLE_SUPPLEMENT
COMPULSORY_GALA_DINNER · EARLY_CHECK_IN · LATE_CHECK_OUT · OVERTIME
NIGHT_SURCHARGE · WAITING_TIME · EXTRA_KM · EXTRA_HOUR · FUEL · OTHER
```

## 10.7 Allotment (optional, phase 2)

```yaml
allotment:
  type: FREESALE            # FREESALE | ALLOTMENT | ON_REQUEST
  units_held:
  release_days_before:
```

---

# 11. Pricing Unit Taxonomy

```text
PER_PERSON
PER_ADULT
PER_CHILD
PER_INFANT
PER_ROOM
PER_NIGHT
PER_ROOM_PER_NIGHT
PER_CABIN
PER_VEHICLE
PER_VEHICLE_PER_DAY
PER_TRANSFER
PER_GUIDE
PER_GUIDE_PER_DAY
PER_GROUP
PER_SERVICE
PER_MEAL
PER_TICKET
PER_SEGMENT
PER_HOUR
PER_DAY
FIXED
TIERED
```

---

# 12. Structured Policies

> **v1.0 fix — the single most important change for operations.**
> `payment_terms` and `cancellation_policy` were free text. Free text cannot generate
> a payment schedule, cannot calculate cancellation cost, cannot raise a due-date alert.
> Both are now structured objects, stored once per supplier/contract and referenced by rates.

## 12.1 Payment Terms

```yaml
payment_terms_id:
supplier_id:
label: "50% deposit / balance 30 days before arrival"
schedule:
  - stage: DEPOSIT
    pct: 50
    trigger: ON_CONFIRMATION       # see triggers
    offset_days: 0
  - stage: BALANCE
    pct: 50
    trigger: BEFORE_SERVICE_DATE
    offset_days: 30
credit_days: 0                     # >0 = pay after service
currency:
payment_method: BANK_TRANSFER      # BANK_TRANSFER | CARD | CASH | OTA_COLLECT
non_refundable_deposit: true
source_quote: "50% deposit upon confirmation, balance 30 days prior to arrival"
```

### triggers
```text
ON_CONFIRMATION
ON_INVOICE
BEFORE_SERVICE_DATE
AFTER_SERVICE_DATE
ON_BOOKING_DATE
FIXED_DATE
```

**Consequence:** the moment a Booking Service is confirmed, the system generates
Payable rows automatically from this schedule. This is what makes payment tracking possible.

## 12.2 Cancellation Policy

```yaml
cancellation_policy_id:
supplier_id:
label: "Standard 30/14/7"
tiers:
  - days_before_service: 30      # 30+ days before
    penalty_pct: 0
  - days_before_service: 14
    penalty_pct: 50
  - days_before_service: 7
    penalty_pct: 100
no_show_penalty_pct: 100
amendment_fee:
amendment_fee_unit: AMOUNT       # AMOUNT | PERCENT
free_amendment_days_before:
peak_period_override:            # festive periods often have stricter rules
  - date_from: 2026-12-24
    date_to: 2027-01-02
    tiers:
      - days_before_service: 45
        penalty_pct: 100
source_quote:
```

Tiers are read as: penalty applies when cancelling **within** that many days of the service date,
evaluated from the strictest matching tier.

## 12.3 Child Policy

> **v1.0 fix.** `age_rule` existed only under Ticket. But every supplier defines
> "child" differently (5–11, 4–9, under 120cm...). Family costing is wrong without this
> at rate level.

```yaml
child_policy_id:
infant_age_from: 0
infant_age_to: 1               # inclusive upper bound, in years
child_age_from: 2
child_age_to: 11
child_pricing_rule: PERCENT_OF_ADULT   # PERCENT_OF_ADULT | FIXED | FREE | ADULT_RATE
child_pct_of_adult: 50
child_sharing_rule: FREE_SHARING_EXISTING_BEDDING
child_with_extra_bed_rule: EXTRA_BED_RATE_APPLIES
max_children_per_room:
height_rule:                   # e.g. "under 120cm free" — parks, cable cars
age_reference_date: TRAVEL_DATE  # TRAVEL_DATE | BOOKING_DATE
source_quote:
```

---

# 13. Category-Specific Fields

Stored in `category_attributes` on the Service record (or on the Rate where price-bearing).

## Accommodation
```yaml
room_type:
room_category_level:
meal_plan:                 # RO | BB | HB | FB | AI
bedding:
max_occupancy:
max_adults:
max_children:
extra_bed_allowed:
connecting_rooms:
view:
size_sqm:
minimum_stay:
check_in_time:
check_out_time:
early_check_in_policy:
late_check_out_policy:
```

Rate structure: `Property → Room Type → Meal Plan → Season → Occupancy → Price Line`

## Transportation
```yaml
transport_type:
vehicle_class:
vehicle_model:
seat_capacity:
recommended_pax:            # always < seat_capacity when luggage is carried
luggage_capacity:
route_id:
included_hours:
included_km:
extra_hour_rate:
extra_km_rate:
driver_included:
fuel_included:
toll_included:
parking_included:
driver_meal_included:
driver_accommodation_included:
overnight_charge:
night_surcharge_after:      # e.g. 22:00
waiting_time_free_minutes:
```

## Ticket
```yaml
attraction_name:
ticket_type:
age_rule:                   # supplier's original wording; structured in child_policy
height_rule:
timed_entry:
operating_hours:
closure_days:
guide_ticket_required:
guide_ticket_free:
advance_booking_required:
lead_time_days:
```

## Flight
```yaml
airline:
flight_type:
origin_airport:
destination_airport:
cabin_class:
fare_class:
baggage:
hand_baggage:
refundable:
changeable:
change_fee:
cancellation_fee:
tax_included:
name_change_allowed:
ticketing_deadline:
```

## Guide
```yaml
language:
guide_level:
expertise:
service_duration:
half_day_hours:
full_day_hours:
overtime_rate:
evening_supplement:
overnight_rate:
meal_allowance:
accommodation_required:
transport_required:
license_number:
```

## Guide Expense
```yaml
guide_service_id:
expense_type:
amount:
currency:
pricing_unit:
applicable_route:
mandatory:
reimbursement_basis:      # ACTUAL | ALLOWANCE
notes:
```

## Experience
```yaml
experience_name:
experience_type:
duration:
private_shared:
min_guests:
max_guests:
start_time:
operating_days:
seasonal_availability:
guide_included:
transfer_included:
meal_included:
entrance_included:
equipment_included:
weather_dependent:
wet_weather_alternative:
physical_level:
lead_time_days:
```

## Meal
```yaml
restaurant_name:
cuisine:
meal_type:
menu_type:
drinks_included:
vegetarian_available:
vegan_available:
halal_available:
gluten_free_available:
private_room:
group_capacity:
dining_level:
reservation_required:
dress_code:
```

## Visa
```yaml
visa_type:
nationality:
destination_country:
processing_time:
validity_days:
entry_type:
government_fee:
service_fee:
urgent_surcharge:
documents_required:
restrictions:
```

## Others
```yaml
service_subtype:
airport:
duration:
capacity:
operating_hours:
advance_booking_required:
inclusions:
exclusions:
```

---

# 14. AI Tags

## Traveller Tags
```text
FIT
COUPLE
HONEYMOON
FAMILY
MULTIGENERATIONAL
SENIOR
SOLO
SMALL_GROUP
GROUP
MICE
CORPORATE
VIP
VVIP
GCC
HALAL_SENSITIVE
```

## Travel Style Tags
```text
SLOW_TRAVEL
CULTURE
HERITAGE
GASTRONOMY
WELLNESS
NATURE
ADVENTURE
LUXURY
QUIET_LUXURY
FAMILY
HONEYMOON
PHOTOGRAPHY
RAIL
BEACH
URBAN
LOCAL_IMMERSION
```

## Suitability Tags
```text
FAMILY_SUITABLE
CHILD_FRIENDLY
HONEYMOON_SUITABLE
SENIOR_SUITABLE
HALAL_SUITABLE
ACCESSIBLE
VIP_SUITABLE
PRIVATE_ACCESS
CROWD_AVOIDANCE
DESIGN_FORWARD
HERITAGE
LOCAL_IMMERSION
WEATHER_DEPENDENT
```
---

# 15. AI Extraction Output Schema

```yaml
source:
  source_id:
  source_reference:
  document_type:
  channel:

supplier:
  supplier_name_raw:
  supplier_id:
  match_method: EXACT | FUZZY | NEW | UNRESOLVED

property:
  property_name_raw:
  property_id:

service:
  category:
  subcategory:
  supplier_product_name:      # SOURCE FACT
  standardized_service_name:  # NORMALIZED FACT

location:
  country:
  destination_raw:
  destination_id:
  origin_raw:
  origin_id:
  end_location_raw:
  end_location_id:

rate_header:
  currency:
  rate_basis:
  commission_pct:
  valid_from:
  valid_to:
  season_name:
  blackout_dates: []
  min_pax:
  max_pax:
  tax_included:
  service_charge_included:

price_lines:
  - price_for:
    occupancy_basis:
    pricing_unit:
    tier_min_pax:
    tier_max_pax:
    amount:

policies:
  payment_terms: {}           # structured per §12.1
  cancellation_policy: {}     # structured per §12.2
  child_policy: {}            # structured per §12.3

conditions:
  supplements: []
  inclusions: []
  exclusions: []
  foc_policy: {}

category_specific: {}

ai:
  ai_tags: []
  ai_selection_notes:
  confidence_score:
  missing_fields: []
  validation_flags: []
  duplicate_candidates: []
  unparsed_text: []           # anything AI saw but could not classify — never discard
```

**`unparsed_text` is mandatory.** Anything the model cannot map must be surfaced for a human,
not silently dropped. Dropped conditions are how a system loses money.

---

# 16. Rate Versioning and Conflict Resolution

> **v1.0 gap.** The old framework flagged "duplicate rate" but gave no resolution rule.
> Rate sheets arrive continuously; without a rule the database fills with contradictions.

## 16.1 Versioning

When a new rate arrives for a service whose validity overlaps an existing active rate:

```text
1. Compare on the key: service_id + price_for + occupancy_basis + season + date range
2. If identical values           → discard, log as CONFIRMED_UNCHANGED
3. If values differ:
     a. mark old rate lifecycle_status = SUPERSEDED
     b. set old.superseded_by = new.rate_id
     c. new rate inherits version = old.version + 1
     d. record a rate_change_log entry (old value, new value, source, date)
4. Never delete a superseded rate — existing bookings reference its snapshot
```

## 16.2 Conflict resolution when two rates are simultaneously valid

Applied in order:

```text
1. Contract beats rate sheet beats email beats verbal note   (document_type priority)
2. Later source_date wins
3. Narrower date range wins over broader (specific promo beats general season)
4. If still tied → do NOT auto-select. Flag RATE_CONFLICT and route to human review.
```

Rule 4 matters: silent auto-selection between contradicting rates is a costing error
that surfaces only at invoice time.

## 16.3 Rate change log

```yaml
change_id:
rate_id:
field:
old_value:
new_value:
source_id:
changed_by:            # AI | user_id
changed_at:
pct_change:            # for anomaly detection
```

---

# 17. Status Model

> **v1.0 fix.** `human_review_status` mixed workflow state with lifecycle state.
> A rate can be VERIFIED *and* EXPIRED at the same time — one field cannot express that.

## 17.1 review_status (workflow)
```text
AI_EXTRACTED
NEEDS_REVIEW
IN_REVIEW
VERIFIED
REJECTED
```

## 17.2 lifecycle_status (commercial validity)
```text
DRAFT
ACTIVE
SUPERSEDED
EXPIRED
SUSPENDED
```

## 17.3 Usability rule

```text
Usable in production quotation  =  review_status VERIFIED
                                 AND lifecycle_status ACTIVE
                                 AND travel_date within valid_from..valid_to
                                 AND no blocking validation_flags
```

---

# 18. Validation Rules — the real gate

> **v1.0 change of emphasis.** A self-reported `confidence_score` from a language model
> is not a statistically meaningful number: 0.97 does not mean 97% correct.
> Treat it as a **secondary signal only**. The gate that forces human review must be
> **rule-based** and deterministic.

## 18.1 Blocking flags — record cannot go ACTIVE

```text
MISSING_SUPPLIER
MISSING_CATEGORY
MISSING_SERVICE_NAME
MISSING_AMOUNT
MISSING_CURRENCY
MISSING_PRICING_UNIT
MISSING_VALIDITY
CONTRADICTORY_DATES            # valid_to < valid_from
RATE_CONFLICT                  # §16.2 rule 4
UNPARSED_COMMERCIAL_TEXT       # unclassified text that looks like a condition
PRICE_ANOMALY                  # >±30% vs previous version of same service
IMPLAUSIBLE_AMOUNT             # order-of-magnitude check per currency
```

## 18.2 Warning flags — usable but marked

```text
MISSING_CANCELLATION_POLICY
MISSING_PAYMENT_TERMS
MISSING_CHILD_POLICY
TAX_TREATMENT_UNCLEAR
SUPPLEMENT_DATES_UNCLEAR
DUPLICATE_CANDIDATE
NEAR_EXPIRY                    # valid_to within 45 days
```

## 18.3 Category-specific checks

### Accommodation
- Occupancy basis missing on a room price line
- Meal plan unclear
- Extra bed rate missing while extra_bed_allowed = true
- Minimum stay conflict
- Blackout overlaps requested travel date

### Transportation
- Vehicle capacity missing
- recommended_pax ≥ seat_capacity (luggage not accounted for)
- Route unclear or origin = destination
- Overtime / extra-km rule missing
- Overnight charge unclear

### Guide
- Language missing
- Half-day vs full-day boundary undefined
- Overtime rule missing
- Guide expenses not captured

### Experience
- min_pax or max_pax missing
- Operating days unclear
- Weather dependency unclear
- Lead time missing for a service requiring advance booking

### Commercial
- Rate expired at time of use
- rate_basis GROSS_COMMISSIONABLE without commission_pct
- Supplement without date range
- FOC policy mentioned in text but not structured

## 18.4 Confidence score (secondary)

```text
0.95–1.00 = High confidence
0.80–0.94 = Review recommended
0.60–0.79 = Human verification required
Below 0.60 = Do not publish automatically
```

Used for **queue prioritisation**, not for authorisation. A record with confidence 0.99
and a blocking flag still cannot go ACTIVE.

---

# 19. Matching and Costing

## 19.1 Service requirement (from quotation intake)

```yaml
requirement_id:
destination_id: HANOI
category: Transportation
subcategory: Airport Transfer
service_date: 2026-11-15
pax_adults: 4
pax_children: 1
child_ages: [7]
luggage_count: 5
luxury_level: PREMIUM
privacy: PRIVATE
special_requirements: []
```

## 19.2 Search keys

```text
Destination
+ Category / Subcategory
+ Validity (service_date within valid_from..valid_to, not blacklisted)
+ Capacity (pax and luggage vs recommended_pax)
+ Quality fit
+ Tags
+ Supplier preference
+ Status (VERIFIED + ACTIVE)
```

## 19.3 Matching principle

AI must not automatically select the cheapest supplier.

```text
1. Validity
2. Correct service
3. Capacity
4. Quality fit
5. Traveller fit
6. Supplier reliability
7. Preferred supplier status
8. Commercial value
```

Target: `BEST FIT + RELIABLE OPERATION + APPROPRIATE QUALITY + ACCEPTABLE COST`

## 19.4 Costing calculation order

Deterministic, and must be reproducible from stored data:

```text
1. Base price line × quantity (by pax type / room-night / vehicle)
2. Apply child policy to child pax
3. Apply occupancy basis for accommodation
4. Apply FOC deduction
5. Add mandatory supplements matching travel dates
6. Add optional supplements selected by consultant
7. Add tax and service charge if not included
8. Add guide expenses
9. Convert to quotation currency using the FX record (§20.2)
10. Apply markup / margin rule
11. Round per rounding policy
```

Each step must be stored as a costing line so the quotation is auditable line by line.

---

# 20. Quotations *(new layer)*

## 20.1 Quotation

```yaml
quotation_id:
quotation_code:            # client-facing reference
client_id:
agent_id:                  # B2B partner if applicable
sales_owner:
version:
parent_quotation_id:       # for revisions
status:                    # DRAFT | SENT | REVISED | ACCEPTED | LOST | EXPIRED
travel_date_from:
travel_date_to:
pax_adults:
pax_children:
child_ages: []
quotation_currency:
fx_record_id:              # locks the exchange rate used
markup_rule_id:
total_net_cost:
total_sell_price:
gross_margin:
margin_pct:
valid_until:
sent_date:
decision_date:
lost_reason:
notes:
```

## 20.2 FX Record

Multi-currency costing is meaningless without a locked rate.

```yaml
fx_record_id:
base_currency:
rates:
  USD: 25400
  EUR: 27600
  THB: 720
rate_date:
rate_source:               # BANK | MANUAL | API
buffer_pct:                # safety margin applied to protect margin
locked_by:
```

## 20.3 Quotation Line

```yaml
quotation_line_id:
quotation_id:
day_number:
service_date:
service_id:
rate_id:
price_line_id:
quantity:
unit_net_cost:
supplements_applied: []
total_net_cost:
markup_pct:
sell_price:
currency:
is_optional:
is_included_in_package:
alternative_of_line_id:    # for "option A / option B" presentation
notes:
```

---

# 21. Bookings *(new layer)*

## 21.1 Booking

```yaml
booking_id:
booking_code:
quotation_id:              # source quotation
client_id:
agent_id:
operations_owner:
status:                    # → §21.3
travel_date_from:
travel_date_to:
pax_adults:
pax_children:
lead_passenger_name:
passenger_list_ref:
total_sell_price:
total_net_cost_snapshot:
currency:
fx_record_id:
confirmed_date:
cancelled_date:
cancellation_reason:
notes:
```

## 21.2 Booking Service — where the snapshot lives

> **This is the core of the operational layer.** A Booking Service **copies** the commercial
> terms in force at confirmation. It stores `rate_id` for traceability only — never for pricing.

```yaml
booking_service_id:
booking_id:
day_number:
service_date:
service_time:

# traceability (reference only, never read for price)
service_id:
rate_id:
price_line_id:

# ---- FROZEN SNAPSHOT ----
supplier_id_snapshot:
supplier_name_snapshot:
service_name_snapshot:
pricing_unit_snapshot:
quantity:
unit_net_cost_snapshot:
supplements_snapshot: []
total_net_cost_snapshot:
currency_snapshot:
payment_terms_snapshot: {}       # structured copy of §12.1
cancellation_policy_snapshot: {} # structured copy of §12.2
inclusions_snapshot: []
exclusions_snapshot: []
# -------------------------

sell_price:
status:                          # → §21.4
supplier_confirmation_number:
supplier_confirmed_date:
requested_date:
release_deadline:                # auto-alert if not confirmed by this date
voucher_id:
voucher_issued_date:
special_requests:
operational_notes:
```

## 21.3 Booking status
```text
DRAFT
PROVISIONAL          # held, not yet confirmed with suppliers
CONFIRMED
IN_PROGRESS          # travel started
COMPLETED
CANCELLED
```

## 21.4 Booking Service status
```text
TO_REQUEST
REQUESTED
WAITLISTED
CONFIRMED
VOUCHER_ISSUED
AMENDED
DELIVERED
CANCELLED
NO_SHOW
```

## 21.5 Amendments

Amendments must never overwrite the original line — they create a new version.

```yaml
amendment_id:
booking_service_id:
amendment_type:            # DATE_CHANGE | PAX_CHANGE | SERVICE_CHANGE | CANCELLATION | UPGRADE
old_snapshot: {}
new_snapshot: {}
cost_difference:
penalty_applied:           # calculated from cancellation_policy_snapshot
charged_to:                # CLIENT | COMPANY | SUPPLIER_WAIVED
requested_by:
approved_by:
amendment_date:
reason:
```

`charged_to: COMPANY` is the field that reveals where margin leaks. Report on it monthly.

## 21.6 Vouchers

```yaml
voucher_id:
booking_service_id:
voucher_number:
issued_to_supplier:
issued_date:
service_details_text:
inclusions_text:
issued_by:
sent_channel:
acknowledged:
```

---

# 22. Payables — money owed to suppliers *(new layer)*

Payable rows are **generated automatically** from `payment_terms_snapshot`
the moment a Booking Service reaches CONFIRMED.

```yaml
payable_id:
booking_id:
booking_service_id:
supplier_id:
stage:                     # DEPOSIT | BALANCE | FULL | PENALTY | ADJUSTMENT
amount_due:
currency:
due_date:                  # computed from trigger + offset_days
status:                    # SCHEDULED | DUE | PAID | PARTIALLY_PAID | OVERDUE | CANCELLED | DISPUTED
amount_paid:
balance:
supplier_invoice_number:
supplier_invoice_date:
supplier_invoice_amount:
variance_vs_snapshot:      # invoice vs what we agreed — the reconciliation field
variance_reason:
approved_by:
notes:
```

## 22.1 Due-date generation example

Given `payment_terms_snapshot` = 50% on confirmation, 50% 30 days before service,
confirmed 2026-08-01 for a service on 2026-11-15:

```text
Payable 1 — DEPOSIT  50%  due 2026-08-01   (trigger ON_CONFIRMATION, offset 0)
Payable 2 — BALANCE  50%  due 2026-10-16   (trigger BEFORE_SERVICE_DATE, offset 30)
```

This generation is only possible because §12.1 is structured. With free text it is manual.

## 22.2 Operational alerts

```text
T-7 days   → payment due soon
T-0        → payment due today
T+1        → OVERDUE, escalate
Release deadline reached without confirmation → risk of losing the service
Supplier invoice ≠ snapshot                   → variance review
```

---

# 23. Receivables — money owed by clients *(new layer)*

```yaml
receivable_id:
booking_id:
client_id:
agent_id:
stage:                     # DEPOSIT | BALANCE | FULL | AMENDMENT_CHARGE | REFUND
invoice_number:
invoice_date:
amount_due:
currency:
due_date:
status:                    # SCHEDULED | INVOICED | PAID | PARTIALLY_PAID | OVERDUE | REFUNDED
amount_received:
balance:
payment_method:
received_date:
bank_reference:
notes:
```

## 23.1 Client payment terms

Held on the client/agent record, structurally identical to §12.1:

```yaml
client_payment_terms:
  schedule:
    - stage: DEPOSIT
      pct: 30
      trigger: ON_CONFIRMATION
    - stage: BALANCE
      pct: 70
      trigger: BEFORE_SERVICE_DATE
      offset_days: 45
  credit_days: 0
```

## 23.2 Cash-flow guardrail

The rule most often violated in practice:

```text
For every booking, check:  client balance due date  ≤  supplier balance due date
```

If the supplier must be paid before the client pays, the company is financing the trip.
Flag it at booking confirmation, not at payment time.

---

# 24. Payments Ledger

One table records actual money movement, on both sides.

```yaml
payment_id:
direction:                 # OUTGOING (to supplier) | INCOMING (from client)
payable_id:                # one of these two is set
receivable_id:
amount:
currency:
fx_rate_applied:
amount_in_base_currency:
payment_date:
payment_method:
bank_reference:
bank_fee:
recorded_by:
attachment_ref:            # receipt / transfer slip
reconciled:
```

---

# 25. Margin Actuals

Closing the loop: quoted margin vs realised margin.

```yaml
booking_id:
quoted_net_cost:
quoted_sell_price:
quoted_margin:
actual_supplier_cost:      # sum of paid payables + penalties
actual_client_revenue:     # sum of received receivables
actual_margin:
variance_amount:
variance_pct:
variance_drivers: []       # AMENDMENT_ABSORBED | FX_MOVEMENT | SUPPLIER_INVOICE_HIGHER |
                           # UNBILLED_EXTRA | PENALTY_ABSORBED | ROUNDING
```

`variance_drivers` is the most valuable analytics field in the system.
After one season it tells you exactly where the business loses money,
and it feeds back into supplier `preferred_status`.

---

# 26. Full Entity Relationship Overview

```text
Supplier ──┬─< Service >── Property
           │      │
           │      └─< Rate Header ──< Price Line
           │              │
           │              ├── Payment Terms
           │              ├── Cancellation Policy
           │              └── Child Policy
           │
           └─< Raw Source

Quotation ──< Quotation Line ──> Rate Header (live reference)
     │
     └──> Booking ──< Booking Service  [FROZEN SNAPSHOT]
                          │
                          ├──< Amendment
                          ├──< Voucher
                          └──< Payable ──< Payment

Booking ──< Receivable ──< Payment
Booking ──> Margin Actuals
```

**The one-way valve:** Quotation Lines read live from Rates.
Booking Services never do — they hold a snapshot. Everything downstream
(payables, penalties, margin actuals) reads only the snapshot.

---

# 27. Build Sequence

## Phase 1 — Supplier Knowledge (weeks 1–8)
```text
Suppliers · Properties · Locations · Raw Sources
Services · Rate Headers · Price Lines
Payment / Cancellation / Child Policies (structured from day one)
AI extraction + rule-based validation + review queue
```
Exit criterion: 200+ verified services across the top 3 categories,
with zero rates carrying blocking flags.

## Phase 2 — Costing & Quotation (weeks 9–14)
```text
Service Requirements · Matching · Costing Engine · FX Records
Quotations · Quotation Lines · Markup rules
```
Exit criterion: a consultant can produce a full quotation without opening a rate sheet.

## Phase 3 — Operations (weeks 15–22)
```text
Bookings · Booking Services (snapshot) · Amendments · Vouchers
Confirmation tracking · Release-deadline alerts
```

## Phase 4 — Finance (weeks 23–28)
```text
Payables · Receivables · Payments · Reconciliation · Margin Actuals
```

**Do not skip ahead.** But **do** implement §12 structured policies in Phase 1 even though
they are only consumed in Phase 4 — retrofitting structure onto thousands of free-text
payment terms is far more expensive than capturing it correctly the first time.

## Phase 1 required production fields

```yaml
supplier_name:
property_name:
category:
subcategory:
supplier_product_name:
standardized_service_name:
destination_id:
origin_id:
end_location_id:
currency:
rate_basis:
pricing_unit:
price_for:
occupancy_basis:
amount:
min_pax:
max_pax:
valid_from:
valid_to:
supplements:
inclusions:
exclusions:
payment_terms:            # structured
cancellation_policy:      # structured
child_policy:             # structured
source_id:
review_status:
lifecycle_status:
validation_flags:
human_verified:
```

---

# 28. Roles

## What staff do
1. Upload supplier files
2. Assign supplier / property when AI cannot resolve them
3. Review flagged extractions (not every record — only flagged ones)
4. Approve commercially significant rates
5. Correct errors
6. Confirm bookings with suppliers and record confirmation numbers
7. Approve payments and record supplier invoices
8. Update supplier status based on performance

Staff should never be required to manually populate dozens of AI-generated fields.

## What AI does
- Read raw supplier data and split files into individual services
- Normalize naming and classify category
- Extract price lines and identify pricing basis
- Structure payment, cancellation and child policies
- Identify validity, seasons, blackouts and supplements with dates
- Create matching tags
- Detect duplicates and rate conflicts
- Run rule-based validation and flag blocking issues
- Surface unparsed text rather than discarding it
- Generate payment schedules from confirmed bookings
- Raise operational alerts (release deadlines, due dates, expiring rates)
- Prepare records for human review, prioritised by risk and value

## What AI must never do
- Overwrite a source fact
- Publish a record carrying a blocking validation flag
- Auto-select between two conflicting rates
- Change a booking snapshot
- Silently drop text it could not classify

---

# 29. Golden Rules

> **1. Store raw supplier facts first. Let AI create structure and intelligence around those facts.**

```text
RAW DATA → VERIFIED FACT → NORMALIZED FACT → AI INFERENCE → MATCHING → COSTING
```

> **2. What we can sell is a rate. What we sold is a snapshot. Never confuse them.**

```text
Rate table changes over time.  Booking snapshot never changes.
```

> **3. If a commercial condition cannot be expressed as structured data, it cannot be automated.**

```text
Free text = manual work forever.
```

Never reverse these orders.

---

# 30. Framework Definition

This is not a manually maintained rate sheet. It is an:

> **AI-readable Supplier Knowledge Layer with an operational transaction layer built on top.**

Long-term value comes from combining:

```text
Raw Supplier Data
+ Standard Taxonomy
+ Verified Rates with Structured Policies
+ Product Knowledge
+ AI Normalization
+ Client Requirements
+ Transaction History and Margin Actuals
```

into one consistent data framework — where the last element feeds back into the first,
and supplier quality assessment stops being an opinion and becomes a measurement.

---

# Appendix A — Worked Example: raw data to payment schedule

## A.1 Raw supplier data

```text
Mercedes Sprinter Hanoi Airport - Hotel
1,200,000 VND
Maximum 8 guests
Valid until 30 September 2027
Tet surcharge +30% (14-20 Feb 2027)
Driver, fuel and toll included
50% deposit on confirmation, balance 15 days before service
Cancel within 48h: 100% charge
```

## A.2 AI extraction output

```yaml
service:
  category: Transportation
  subcategory: Airport Transfer
  supplier_product_name: Mercedes Sprinter Hanoi Airport - Hotel
  standardized_service_name: Hanoi Airport → Hanoi City | Private Premium Van
location:
  origin_id: LOC_HAN_AIRPORT
  destination_id: LOC_HANOI
rate_header:
  currency: VND
  rate_basis: NET
  valid_from: 2026-01-01
  valid_to: 2027-09-30
  max_pax: 8
price_lines:
  - price_for: UNIT
    pricing_unit: PER_TRANSFER
    amount: 1200000
category_specific:
  transport_type: Van
  vehicle_class: Premium
  recommended_pax: 6          # AI infers: 8 seats minus luggage allowance
  seat_capacity: 8
  driver_included: true
  fuel_included: true
  toll_included: true
supplements:
  - type: FESTIVE
    label: Tet surcharge
    value: 30
    unit: PERCENT
    applies_to: BASE_RATE
    date_from: 2027-02-14
    date_to: 2027-02-20
    mandatory: true
policies:
  payment_terms:
    schedule:
      - stage: DEPOSIT
        pct: 50
        trigger: ON_CONFIRMATION
        offset_days: 0
      - stage: BALANCE
        pct: 50
        trigger: BEFORE_SERVICE_DATE
        offset_days: 15
  cancellation_policy:
    tiers:
      - days_before_service: 2
        penalty_pct: 100
      - days_before_service: 999
        penalty_pct: 0
ai:
  ai_tags: [PRIVATE, PREMIUM, FIT, FAMILY_SUITABLE]
  confidence_score: 0.94
  validation_flags: [MISSING_CHILD_POLICY]
  unparsed_text: []
```

Note: `recommended_pax: 6` is an **AI inference**, not a source fact — it is stored in the
inference layer and shown to the reviewer as an assumption, never as supplier data.

## A.3 Booking snapshot (confirmed 2026-08-24 for travel 2026-11-15)

```yaml
booking_service_id: BS-00417
service_date: 2026-11-15
rate_id: RT-0093                    # reference only
supplier_name_snapshot: ABC Transport Co.
service_name_snapshot: Hanoi Airport → Hanoi City | Private Premium Van
pricing_unit_snapshot: PER_TRANSFER
quantity: 1
unit_net_cost_snapshot: 1200000
supplements_snapshot: []            # travel date outside Tet window
total_net_cost_snapshot: 1200000
currency_snapshot: VND
payment_terms_snapshot:
  schedule:
    - stage: DEPOSIT
      pct: 50
      trigger: ON_CONFIRMATION
    - stage: BALANCE
      pct: 50
      trigger: BEFORE_SERVICE_DATE
      offset_days: 15
cancellation_policy_snapshot:
  tiers:
    - days_before_service: 2
      penalty_pct: 100
sell_price: 1560000
status: CONFIRMED
supplier_confirmation_number: ABC-2026-8841
```

If the supplier raises this rate to 1,400,000 VND in September 2026, the rate table updates
and the old rate becomes SUPERSEDED — but booking BS-00417 still costs 1,200,000 VND,
because it reads only its own snapshot.

## A.4 Auto-generated payables

```yaml
- payable_id: PAY-01120
  booking_service_id: BS-00417
  stage: DEPOSIT
  amount_due: 600000
  due_date: 2026-08-24        # ON_CONFIRMATION
  status: DUE

- payable_id: PAY-01121
  booking_service_id: BS-00417
  stage: BALANCE
  amount_due: 600000
  due_date: 2026-10-31        # 2026-11-15 minus 15 days
  status: SCHEDULED
```

No human entered these dates. They exist because §12.1 was captured as structure, not prose.

## A.5 If the client cancels on 2026-11-14

```text
Days before service = 1  →  matches tier (within 2 days)  →  penalty 100%
Penalty payable = 1,200,000 VND
Amendment record: type CANCELLATION, penalty_applied 1200000, charged_to CLIENT
Receivable raised: stage AMENDMENT_CHARGE
Margin actuals: variance_driver = PENALTY_ABSORBED if charged_to = COMPANY
```

The entire calculation is deterministic from stored data — no one has to reread the contract.
