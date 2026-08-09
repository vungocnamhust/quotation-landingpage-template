# 08. Quotation Content Studio API Contract

## 1. Source of truth and state flow

```text
dmc-core facts -> quotation skeleton -> Content Studio candidate -> Apply -> canonical editor document -> publish
```

- Postgres is canonical for facts snapshots, editor documents, content drafts and publications.
- A content draft is never renderable. Only an applied canonical document is used by web, PDF and publish.
- Facts come from dmc-core or from a manual Quote Generator draft and are not changed by deterministic or LLM generation. Manual facts remain editable only until an explicit DMC attach.

## 2. Input catalog

`POST /api/v2/quotations` accepts `CreateQuoteRequestV1` and returns a draft skeleton. All nested fields are optional for compatibility, but missing factual input can make a Content Studio scope ineligible.

| Group / field | Type | Owner / source | Missing rule |
| --- | --- | --- | --- |
| `source.kind` | `manual` / `dmc_handoff` | Quote Generator / dmc-core | controls facts ownership; defaults to `manual` |
| `opportunity_id` | string or null | dmc-core | null for independent quotations; never falls back to quotation ID |
| `brand_id`, `lang` | string | dmc-core | brand default / `en`; `lang` is `en`, `vi`, or `ar` |
| `trip_facts.title`, `subtitle` | string | dmc-core / content override | title is required for hero generation unless destinations exist |
| `trip_facts.start_date`, `end_date`, `duration_days`, `duration_nights` | string / integer | dmc-core | display values are deterministic; never inferred by LLM |
| `trip_facts.destinations` | string[] | dmc-core | used for route and hero context |
| `trip_facts.itinerary[]` | fact array | dmc-core | see day catalog below |
| `customer_facts` | customer name, adults, children, nationality, market, profile | dmc-core | guest labels are deterministic |
| `service_facts.hotels[]` | destination, name, room, dates, intro, assets | dmc-core | hotel copy may be generated only from supplied hotel facts |
| `service_facts.inclusions`, `exclusions` | string[] | dmc-core | no LLM additions |
| `pricing_facts` | currency, totals, options, conditions | dmc-core | calculations/display are deterministic; no LLM prices |
| `booking_facts`, `finalization_facts`, `seller_facts` | facts or supplied copy | dmc-core / caller | supplied values win over generated content |
| `assetOverrides` | object | caller | selected media; never generated as fact |
| `contentOverrides` | object | caller | brochure copy or assets; wins over deterministic/default/LLM values |
| `generationOptions` | object | caller | request preferences only; cannot relax factual guards |

### Exact `CreateQuoteRequestV1` field inventory

| Object | Fields |
| --- | --- |
| Root | `source`, `opportunity_id`, `brand_id`, `lang`, `trip_facts`, `pricing_facts`, `customer_facts`, `service_facts`, `booking_facts`, `finalization_facts`, `seller_facts`, `retrieval_refs`, `contentOverrides`, `assetOverrides`, `generationOptions` |
| `trip_facts` | `title`, `subtitle`, `destinations`, `start_date`, `end_date`, `duration_days`, `duration_nights`, `itinerary`, `special_requirements`, `display_route_text`, `display_travel_dates`, `hero_meta_1`, `hero_meta_2`, `footer_text`, `overview_title`, `journey_overview_title`, `letter_highlight`, `letter_greeting`, `letter_intro`, `letter_body`, `letter_outro`, `letter_sign_off`, `letter_sender`, `route_title`, `route_description`, `itinerary_title`, `itinerary_description`, `cover_kicker` |
| `trip_facts.itinerary[]` | `day_number`, `destination`, `summary`, `overnight`, `meals`, `display_title`, `highlights`, `notes`, `sense_of_pace`, `display_date`, `label_highlights`, `label_notes` |
| `pricing_facts` | `currency`, `total_budget`, `price_basis`, `option_label`, `kicker`, `display_title`, `display_subtitle`, `cta_label`, `conditions`, `options` |
| `pricing_facts.options[]` | `category`, `name`, `per_person_text`, `total_text`, `is_total`, `is_confirmed_main_option`, `is_alternative_option` |
| `customer_facts` | `customer_name`, `adults`, `children`, `nationality`, `guest_profile`, `market`, `party_label`, `greeting_name` |
| `service_facts` | `hotels`, `inclusions`, `exclusions`, `room_notes` |
| `service_facts.hotels[]` | `destination`, `name`, `room_type`, `check_in`, `check_out`, `intro`, `phone`, `display_city`, `display_date`, `hotel_asset`, `room_asset` |
| `booking_facts` | `title`, `description`, `items` |
| `booking_facts.items[]` | `key`, `label`, `body` |
| `finalization_facts` | `required_title`, `after_confirmation_title`, `required_items`, `after_confirmation_items` |
| `seller_facts` | `seller_name`, `seller_subtitle`, `seller_email`, `seller_phone`, `contact_web`, `designer_name`, `designer_signature`, `designer_kicker`, `designer_quote`, `designer_experience`, `designer_title`, `cta_body`, `designer_email`, `designer_phone` |

### Itinerary-day fact catalog

Each `trip_facts.itinerary[]` item has `day_number`, `destination`, `display_date`, `overnight`, `meals`, `summary`, `highlights`, `notes`, and `sense_of_pace`.

To generate `itinerary:day:{day_number}`, the day must have `day_number`, `destination`, and at least one of `summary` or `highlights`. Missing data returns `missingInputs`; the API does not call the model or create invented activities, timing, transport, hotel, service, price, inclusion, date or claim.

### Presence and precedence

- Omitted key or `null`: eligible for deterministic/default/LLM fill where the field is not a required fact.
- `""` or `[]`: explicit caller choice; do not refill.
- Precedence is `facts` (immutable) -> `contentOverrides` -> deterministic resolver -> brand default -> generated candidate.

## 3. API

### Create quotation

`POST /api/v2/quotations`

Creates the request snapshot, quotation row, canonical skeleton document and revision `1`. It does not call the narrative model, render HTML/PDF or publish.

The response also contains `resolvedFacts`: server-owned display values for duration, route, travel-date label, guest label, price-per-adult and legal-default status. Clients may display these values but must not persist or override them as facts. `GET /api/v2/quotations/{id}/facts` and a successful manual `PUT` return the same object.

`resolvedFacts.destinationRefs` additionally reports destination catalog matches. `presentationOptions` contains Quote Generator-owned template and Travel Designer choices, while image selection uses canonical `r2Key` references as specified in [09-media-library-and-option-catalog.md](./09-media-library-and-option-catalog.md).

`source.kind=manual` permits a direct quotation with no opportunity. `source.kind=dmc_handoff` requires an opportunity ID. `POST /api/v2/quotation-handoffs/resolve` exchanges a one-time DMC token server-to-server and returns this same request shape; Quote Generator never stores the opaque token.

`GET/PUT /api/v2/quotations/{id}/facts` reloads or updates a manual snapshot using `baseRevision`. DMC-owned facts return `409` on PUT. `POST /api/v2/quotations/{id}/attach-opportunity` first returns a facts diff; repeating with `confirm=true` records the DMC snapshot, regenerates the factual skeleton, and permanently changes ownership to `dmc_handoff`.

```json
{
  "quotationId": "quo_abc123",
  "status": "draft",
  "baselineLang": "en",
  "currentRevision": 1,
  "currentVersion": 0,
  "document": {},
  "documentVersion": 1
}
```

### Content drafts

`POST /api/v2/quotations/{id}/content-drafts?lang=en`

```json
{
  "scopes": ["hero", "overview", "itinerary:day:1"],
  "generationMode": "storytelling"
}
```

Supported scopes are `hero`, `overview`, `booking_terms`, `finalization`, and `itinerary:day:{number}`. It returns persisted review candidates. The wire contract remains scope-based, while the implementation groups eligible hero/overview/booking/finalization scopes into one model request and itinerary scopes into batches of at most four days; every result remains an independently reviewable draft. If every requested scope lacks required facts, it returns `422` with `detail.drafts[].missingInputs`.

`GET /api/v2/quotations/{id}/content-drafts?lang=en` reloads candidates and marks a draft `stale` when its source document revision differs from the current document.

`PATCH /api/v2/quotations/{id}/content-drafts/{draftId}` accepts `{ "candidate": {} }` for manual review edits.

`POST /api/v2/quotations/{id}/content-drafts/{draftId}/apply` accepts `{ "baseRevision": 3 }`. It merges only the scope-owned fields, appends an `apply_content_draft` revision and marks the draft `applied`.

`POST /api/v2/quotations/{id}/content-drafts/{draftId}/discard` marks an unapplied candidate `discarded`.

### Errors and states

| Code | Meaning |
| --- | --- |
| `404` | quotation, document or candidate is absent |
| `409` | editor revision conflict, stale draft, or invalid state transition |
| `422` | invalid scope, no scopes, unresolved required facts, or invalid document |
| `500` | unexpected persistence/generation failure |

Draft statuses: `draft`, `applied`, `discarded`, `stale`.

## 4. Deterministic and LLM generation

Deterministic code owns date/duration/route labels, guest labels, pricing arithmetic, IDs/order/layout, brand tokens and legal defaults. LLM candidates may supply only hero lede, overview letter, booking/finalization copy and itinerary narrative.

Every content prompt has a stable shared prefix: language, brand policy, structured-output contract, scope, factual boundary and validation rule. It receives only traveller/trip summary plus the requested section/day facts; it never receives the full editor document.

| Mode | Purpose | Copy budget |
| --- | --- | --- |
| `storytelling` | Luxury, sensory and calm narrative that remains grounded in facts | hero 20-35 words; overview 80-120; day 70-100 |
| `detailed` | Concise, sequential and operationally clear wording | hero 15-25 words; overview 60-90; day 50-80 |

Cache identity is `factsHash + scope + lang + generationMode + promptVersion`. Cached `draft` candidates are reused only at the same source revision. The persisted metadata records prompt version, provider status, warnings, latency and cache hit.

## 5. Editor and publish contract

Content Studio is a Quote Generator workspace, not a brochure display section. It shows used facts, missing inputs, mode choice, candidate, manual edits, regenerate, Apply and Discard. The landing-page editor only edits the applied canonical document. Existing autosave uses `baseRevision`; publish reads the canonical Postgres document and never reads an unapplied content draft.
# Publication safety addendum

Facts updates atomically append a skeleton revision and mark existing `draft` and `applied` content candidates `stale`. Missing-input candidates are persisted without a model call. Global content scopes share one request; itinerary generation is bounded to four eligible days per request. Only applied copy can reach canonical render, PDF or publication.
