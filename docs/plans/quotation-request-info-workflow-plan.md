# FE & Backend Design & Implementation Plan: Request-First Quotation Workflow

**Generated**: 2026-08-14
**Estimated Complexity**: Medium-High
**Design Orchestration Risk Rating**: Moderate Risk

---

## 1. Executive Summary & Refined Requirements

- **Terminology Standard**: Single source of truth model and entity name is **`QuoteRequest`** / **`quote_requests`**.
- **Persona Scope (2 Personas Only)**:
  1. **Persona 1: Traveller (Khách tự đi)**
  2. **Persona 2: Travel Advisor (Đại lý du lịch)**
- **Kid Ages Array (`kid_ages`)**: Explicitly modeled array field `kid_ages: list[int]` (e.g. `[6, 11]`). When `children > 0`, UI renders individual age picker inputs for each child.
- **Optional Basic Daily Itinerary**: The day-by-day itinerary block in `New Request` is now **Optional** (rendered inside an expandable accordion). Travel Designers can create a request with or without daily itinerary breakdown.
- **Auto-Redirect on Quotation Generation**: Clicking `+ Generate Quotation` in `Detail Request` creates a prefilled `Quotation` record and automatically redirects the browser to `/workspace/quotations/[new_id]`.
- **Free-Text Date Auto-Parsing (`advisor_dates`)**: Backend automatically parses free-text inputs like `"09–20 Nov 2026"` into ISO `start_date="2026-11-09"` and `end_date="2026-11-20"` while keeping the raw string for display.

---

## 2. Field Matrix & UI/UX Workflow for 2 Personas

### 2.1 Persona 1: `traveller` (Khách Tự Đi)

| Category | Field Name | HTML / UI Control | Type & Constraints | Mapping to `QuoteRequest` |
| :--- | :--- | :--- | :--- | :--- |
| **Journey Specs** | `destination` | `<select>` | String (Required) | `destinations: ["Vietnam", ...]` |
| | `travel_timing` | `<select>` | `Exact dates`, `Approximate month`, `Flexible` | `payload_json.travel_timing` |
| | `arrival_date` | `<input type="date">` | ISO Date String (`YYYY-MM-DD`) | `start_date` |
| | `departure_date` | `<input type="date">` | ISO Date String (`YYYY-MM-DD`) | `end_date` |
| | `adults` | Counter / `<input type="number">` | Integer (Min 1, Default 2) | `adults` |
| | `children` | Counter / `<input type="number">` | Integer (Min 0, Default 0) | `children` |
| | **`kid_ages`** | **Dynamic Array Inputs** | **`list[int]` (e.g. `[6, 11]`)** | **`kid_ages: [6, 11]`** |
| | `children_details` | `<input type="text">` | Auto-derived / Free-text | `children_details` |
| **Theme & Vision**| `primary_theme` | Radio Pill Chips | `Living Heritage`, `Icons Reimagined`, `Natural Worlds`, `Unhurried Journeys`, `Beyond the Familiar`, `A Thoughtful Mix` | `travel_style` |
| | `traveller_message`| `<textarea>` | Text (Special requests, celebration, dietary, accessibility) | `special_requirements` |
| **Identity Info** | `first_name` | `<input type="text">` | String (Required) | `customer_name` (First) |
| | `last_name` | `<input type="text">` | String (Required) | `customer_name` (Last) |
| | `email` | `<input type="email">` | String (Required) | `email` |
| | `phone` | `<input type="tel">` | String (Phone / WhatsApp) | `phone` |
| | `country` | `<input type="text">` | String (Country of residence) | `market` / `country` |
| | `preferred_contact`| `<select>` | `Email`, `Phone`, `WhatsApp` | `preferred_contact` |

---

### 2.2 Persona 2: `advisor` (Travel Advisor / Agent)

| Category | Field Name | HTML / UI Control | Type & Constraints | Mapping to `QuoteRequest` |
| :--- | :--- | :--- | :--- | :--- |
| **Advisor Practice**| `advisor_first_name` | `<input type="text">` | String (Required) | `customer_name` (Advisor First) |
| | `advisor_last_name` | `<input type="text">` | String (Required) | `customer_name` (Advisor Last) |
| | `advisor_company` | `<input type="text">` | String (Required - Agency/Company) | `company_name` |
| | `advisor_email` | `<input type="email">` | String (Required) | `email` |
| | `advisor_phone` | `<input type="tel">` | String (Phone / WhatsApp) | `phone` |
| | `advisor_market` | `<select>` | Vietnam, Singapore, HK, UK, US, Australia, Europe, Other | `market` |
| **Client Journey** | `advisor_destination` | `<select>` | String (Required) | `destinations: ["Vietnam", ...]` |
| | `advisor_dates` | `<input type="text">` | Free-text (e.g. `"09–20 Nov 2026"`) | `raw_dates_text` & Auto-parsed `start_date`/`end_date` |
| | `advisor_travellers` | Counter / `<input type="number">` | Integer (Min 1, Default 2) | `adults` |
| | `children` | Counter / `<input type="number">` | Integer (Min 0, Default 0) | `children` |
| | **`kid_ages`** | **Dynamic Array Inputs** | **`list[int]` (e.g. `[8, 12]`)** | **`kid_ages: [8, 12]`** |
| | `advisor_journey_type`| `<select>` | Cultural, Family, Honeymoon, Wellness, Other | `travel_style` |
| | `advisor_message` | `<textarea>` | Text (Client journey vision & requests) | `special_requirements` |

---

### 2.3 Optional Section: `Basic Daily Itinerary (Optional)`

Rendered inside a collapsible accordion card in `New Request`:
- Header: `+ Add Basic Daily Itinerary (Optional)`
- Days Table / Cards: Day #, Date, Destination Ref, Short Summary, Overnight Location.
- Can be submitted empty without blocking Request creation.

---

## 3. Backend Architecture & Database Design (FastAPI & SQLAlchemy)

### 3.1 Database Model (`db/models/quote_request.py`)

Table Name: `quote_requests`

```python
class QuoteRequest(Base):
    __tablename__ = "quote_requests"
    __table_args__ = (
        Index("ix_quote_requests_status_created_at", "status", "created_at"),
        Index("ix_quote_requests_role_created_at", "role", "created_at"),
        Index("ix_quote_requests_customer_email", "email"),
        Index("ix_quote_requests_linked_quotation_id", "linked_quotation_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True) # e.g. "REQ-20260814-001"
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True) # "traveller", "advisor"
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new", server_default="new", index=True) # "new", "under_review", "quotation_created", "archived"
    
    # Contact & Persona Info
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_contact: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Journey Preferences
    destinations: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False, default=list) # e.g. ["Vietnam", "Cambodia"]
    start_date: Mapped[str | None] = mapped_column(String(32), nullable=True) # ISO "2026-11-09"
    end_date: Mapped[str | None] = mapped_column(String(32), nullable=True)   # ISO "2026-11-20"
    raw_dates_text: Mapped[str | None] = mapped_column(String(255), nullable=True) # e.g. "09–20 Nov 2026"
    adults: Mapped[int | None] = mapped_column(Integer, nullable=True, default=2)
    children: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    kid_ages: Mapped[list[int]] = mapped_column(JSON_VARIANT, nullable=False, default=list) # e.g. [6, 11]
    children_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    travel_style: Mapped[str | None] = mapped_column(String(64), nullable=True) # e.g. "Living Heritage"
    special_requirements: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Structured Payload
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False) # Full json payload

    # Relationships & Foreign Keys
    created_by_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("travel_designer_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    linked_quotation_id: Mapped[str | None] = mapped_column(
        ForeignKey("quotations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
```

---

### 3.2 Pydantic Schemas (`schemas/v2/quote_request.py`)

```python
class QuoteRequestCreateSchema(BaseModel):
    role: Literal["traveller", "advisor"]
    customer_name: str
    email: str
    phone: str | None = None
    company_name: str | None = None
    market: str | None = None
    preferred_contact: str | None = None
    destinations: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    raw_dates_text: str | None = None
    adults: int = Field(default=2, ge=1)
    children: int = Field(default=0, ge=0)
    kid_ages: list[int] = Field(default_factory=list) # Array of ages e.g. [6, 11]
    children_details: str | None = None
    travel_style: str | None = None
    special_requirements: str | None = None
    itinerary_days: list[dict[str, Any]] = Field(default_factory=list) # Optional basic itinerary
    website: str | None = None # Honeypot anti-bot field (must be empty)

class QuoteRequestResponseSchema(BaseModel):
    id: str
    role: str
    status: str
    customer_name: str | None
    email: str | None
    phone: str | None
    company_name: str | None
    market: str | None
    preferred_contact: str | None
    destinations: list[str]
    start_date: str | None
    end_date: str | None
    raw_dates_text: str | None
    adults: int | None
    children: int | None
    kid_ages: list[int] # Array of ages
    children_details: str | None
    travel_style: str | None
    special_requirements: str | None
    payload_json: dict[str, Any]
    linked_quotation_id: str | None
    created_at: datetime
    updated_at: datetime
```

---

### 3.3 FastAPI Router (`routers/v2/quote_requests.py`)

Using `Annotated` dependencies, return types, single HTTP operation per endpoint:

- `POST /api/v2/workspace/requests` (`create_quote_request`) -> Creates request. Returns `QuoteRequestResponseSchema`.
- `GET /api/v2/workspace/requests` (`list_quote_requests`) -> Lists requests with filters (`q`, `role`, `status`, `limit`, `offset`). Returns `QuoteRequestListResponseSchema`.
- `GET /api/v2/workspace/requests/{request_id}` (`get_quote_request`) -> Gets request details. Returns `QuoteRequestResponseSchema`.
- `PATCH /api/v2/workspace/requests/{request_id}` (`update_quote_request`) -> Updates status. Returns `QuoteRequestResponseSchema`.
- `POST /api/v2/workspace/requests/{request_id}/generate-quotation` (`generate_quotation_from_request`) -> Generates `Quotation` and returns `{ redirect_url: "/workspace/quotations/[new_id]" }`.

---

## 4. Frontend Implementation Updates (`quote-generator`)

1. **`KidAgesInput.tsx` Component**:
   - Renders dynamic age selector inputs when `children > 0`.
   - Maintains `kid_ages` state as an array of numbers `[6, 11]`.
2. **`LeadRoleSelector.tsx`**:
   - Shows 2 Persona cards: `I'm planning a journey` (`traveller`) and `I'm a Travel Advisor` (`advisor`).
3. **`NewRequestPage` (`/workspace/requests/new`)**:
   - Section 1: Persona & Contact Info (Required).
   - Section 2: Journey Preferences & Theme (Required).
   - Section 3: Basic Daily Itinerary (Optional Accordion).
4. **`DetailRequestView.tsx`**:
   - Displays `kid_ages` array nicely as age badges (e.g. `Children: 2 (Ages 6, 11)`).
   - **`+ Generate Quotation`** button triggers backend API and executes `router.push(data.redirect_url)`.

---

## 5. Verification Plan

### Automated Tests
- `cd quote-generator && npm run lint && npm run lint:typography && npm run build`
- `python -m pytest tests`

### Manual Verification
- Test `children` counter & `kid_ages` dynamic input fields. Verify `kid_ages` saves as integer array `[6, 11]`.
- Test request creation with empty optional itinerary section.
- Test `+ Generate Quotation` auto-redirect to `/workspace/quotations/[new_id]`.
