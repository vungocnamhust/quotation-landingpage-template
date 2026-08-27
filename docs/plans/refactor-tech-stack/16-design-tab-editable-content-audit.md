# Plan 16 — Design Tab Editable Content: Audit, Data Contract & Implementation Roadmap

> **Trạng thái:** Finalized plan (chưa thi công). **Phạm vi:** Hardening ranh giới Facts ↔ Content ↔ Design ↔ Publish để Design Canvas (Step 3) edit được hầu hết content mà không bao giờ corrupt Structural Facts.
> **Liên quan:** chuỗi plan 14.x (AI Service Drafter), 15.x (Modular Tour Ops). Plan này độc lập, có thể chạy trước/song song.

---

## A. Tóm Tắt Kiểm Toán (Audit Summary)

### A.1. Nền móng đã đúng — giữ nguyên

| Cơ chế | Bằng chứng | Vai trò |
| :-- | :-- | :-- |
| SSOT hiển thị = `document_json` canonical | `buildDisplayDocumentFromQuoteDocument()` (`quote-generator/display/runtimePageBuilder.ts:153`) là boundary duy nhất cho cả Design canvas lẫn brochure công khai | Content Studio chỉ ảnh hưởng brochure khi `apply` draft (merge server-side, bump revision) |
| Contract sở hữu field | `editable_brochure_contract.py` + `editable-brochure-contract.json` (v3, 152 fields: 47 `fact`, 46 `design`, 30 `content`, 18 `system`, 11 `fact-derived`); check non-overlap source lúc import (`editable_brochure_contract.py:107`) | Dispatcher `save()` trong `DesignCanvas.tsx:351` rẽ nhánh theo `owner` |
| Facts một cửa ghi | `FactsForm → useFactsFormState → prefillEngine/adapters → reconcilers`; ngoại lệ duy nhất: allowlist 12 field `designer_facts` từ Design inspector | Không component nào khác gọi `saveFacts` |
| `PUT /facts` server-rebuild | `SkeletonBuilder` rebuild từ facts đã resolve + `_preserve_content_owned_values` (main.py:4825+) carry-forward content theo `sourceFactId`; diff ngày theo `id` (`core/rules/content_action_reconciler.py:17`) | Facts save không phá narrative; reorder không invalidate content |
| Optimistic concurrency | `baseRevision` → 409 `DocumentRevisionConflictError` trên mọi endpoint ghi; publish double-check + advisory lock | Chống concurrent clobber |
| Frozen release | Release trỏ `document_revision` bất biến (append-only history); public render fetch đúng revision lịch sử | Đã đạt yêu cầu frozen snapshot |

### A.2. Blockers & Gaps

| # | Mức | Vấn đề | Bằng chứng |
| :-- | :-- | :-- | :-- |
| B1 | 🔴 | `PUT /document` nhận **nguyên khối** document từ client, backend chỉ validate shape — không re-derive `trip`/`pricing`/`party` từ Facts. Contract owner chỉ là metadata tư vấn client, **không phải write-time ACL**. Client lỗi/gọi API trực tiếp có thể sửa lậu ngày/giá/party và publish nguyên trạng. | `main.py:7279-7367`; caller `DesignCanvas.tsx:244-266` (`saveCanonicalDocument`) |
| B2 | 🔴 | `PublishReadinessGate` (`core/rules/readiness_rules.py:9`) và `QuotationTransitionGate` (`core/rules/quotation_rules.py:17`) chỉ chạy trong test, **không wired** vào `POST /publish`. Không gate nào cross-check `document_json` vs Facts đã duyệt. | `_canonical_review_status` (`main.py:8895`) chỉ check completeness/shape |
| B3 | 🟠 | Addressing theo **index**: content source `/itinerary/days/*/title` bám vị trí mảng; edit Design giữa 2 lần facts-save có thể gán nhầm ngày sau reorder/xóa. | `editable-brochure-contract.json` fields; `matchEditableSource` (`editableHandoff.ts:43`) |
| B4 | 🟠 | Copy sống lậu trong Facts: `itinerary[].summary/highlights/notes`, `hotel.intro`, `booking_facts` (body 4000 chars), `finalization_facts`, `designer_facts`. Field `title` per-day chỉ tồn tại frontend, bị `serializeFactsForApi` drop âm thầm (`factsTypes.ts:313`) → data-loss. | `quote_document.py:440-644` vs docstring dòng 456 |
| B5 | 🟠 | Fallback im lặng `fact → presentation.copyOverrides` khi `canEditDesignerFacts === false` (`DesignCanvas.tsx:354-364`) → shadow value lệch Facts, không chỉ báo UI, không reconcile. | |
| B6 | 🟡 | Precedence nhân đôi: `runtimePageBuilder` hardcode `designCopy/contentCopy/factCopy` thay vì gọi `presentationReconciler.resolveEffectivePresentationValue`; `mediaOverrides` nằm ngoài `presentationAdapter.CanonicalPresentationState`. | |
| B7 | 🟡 | Dual-write hazards Content Studio ↔ Design: Design content-edit không `mark_stale` draft cùng scope (draft zombie applyable đè edit tay); `localCandidate` chưa save bị Generate thay im lặng (`useContentGeneration.ts:128`). | |
| B8 | 🟠 | **UX dead-end khi facts immutable**: khi `businessVersion.immutable === true`, Facts tab read-only trừ khi `isEditingQuotation` (`QuotationWorkspaceClient.tsx:395-396`); handoff "Sửa ở Facts tab" thuần túy chuyển stage sẽ đưa user vào form khóa không lối ra. | Nút "Edit Quotation" tại `QuotationWorkspaceClient.tsx:599-601`; submit → `createBusinessVersion` (`:264-279`) → `POST /versions` → redirect version mới + Impact Center |

---

## B. Brainstorm & Decision Log

### B.1. Ma trận sở hữu field chốt (Field Ownership — Final)

**🔒 LOCKED — Structural Facts (Design/Content chỉ xem; sửa qua Facts tab hoặc Edit Quotation flow):**

| Nhóm | Fields | Handoff đích |
| :-- | :-- | :-- |
| Thời gian | `start_date`, `end_date`, `duration_days/nights`, `day_number`, `display_date`, cấu trúc mảng ngày (thêm/xóa/reorder) | `facts.programme` |
| Lộ trình & lưu trú | `destinations`, `itinerary[].destination`, `overnight`, `hotels[].accommodation_id/destination/room_type/check_in/check_out` | `facts.programme` / `facts.services.hotel` |
| Đoàn khách & phòng | `adults`, `children`, `kid_ages`, `room_configurations`, `nationality`, `market` | `facts.customer` |
| Giá | `pricing_facts.options[]` (mọi amount minor-unit), `pricing_scheme`, markup, net rates, `conditions[]` | `facts.pricing` |
| AI input | `itinerary[].summary`, `highlights[]`, `notes[]` — **giữ trong Facts** làm `content_input` (nguyên liệu prompt, đổi → `review_or_generate` impact) | `facts.programme.day` |
| Meta | `brand_id`, `template_id`, `renderer`, `layout_version`, `meta.*` | (backend đóng băng) |

**✏️ EDITABLE trên Design Canvas:**

| Nhóm | Fields (theo contract source) | Store đích |
| :-- | :-- | :-- |
| Narrative | `/trip/{title,lede}`, `/narrative/*` (14 field letter/hero/footer), `/itinerary/{title,description}`, `/itinerary/days/{dayId}/{title,description/0,activities}`, `/route/{title,description}`, `/route/staySegments/{segId}/mapSegmentDesc`, `/pricing/{kicker,title,description}` (câu chữ khung — không con số), `/stays/hotels/{hotelId}/editorialIntroduction`, finalization titles+items | **Content** (qua `PATCH /content-values`) |
| Design copy | nav labels, CTA labels, `identity.{brandName,logoAlt}` | `presentation.copyOverrides` / `identityOverrides` (giữ nguyên) |
| Media | hero background, day gallery, hotel/room images, dividers, avatar | `presentation.mediaOverrides` (giữ nguyên, đưa vào adapter — B6) |
| Designer copy | 12 field `designer_facts` allowlist | Giai đoạn 1 giữ đường Facts-allowlist hiện có; **P2 di cư sang Content scope `designer`** |

### B.2. Nghị quyết vùng xám (Gray-Area Resolutions)

| Field | Quyết định | Lý do & đường di cư |
| :-- | :-- | :-- |
| `day.title` (frontend-only, bị drop) | **Xóa khỏi `ItineraryDayFact`** frontend. Title brochure đã thuộc Content (`/itinerary/days/*/title`, owner `content`). Facts form không hiển thị ô title; nếu cần preview, hiển thị read-only giá trị content với nút "Edit in Design". | Chấm dứt data-loss âm thầm tại `serializeFactsForApi` (`factsTypes.ts:313`). Không cần migration DB (chưa từng persist). |
| `summary` vs `description` | **Giữ phân đôi**: `summary` = AI input, sống trong Facts, sửa ở Facts tab; `description` = brochure output, sống trong Content, sửa ở Design/Content. Inspector Design cho field description hiển thị chú thích "Regenerate from Facts summary" (link Content Studio). | Đúng với `FactDependency` `review_or_generate` đã khai báo (`content_registry.py:334-339`). |
| `booking_facts` bodies | **P2 migration**: thêm Content scope `booking_terms` (candidate `{items: [{key, label, body}]}` key theo `items[].key`); Facts giữ **chỉ** `items[].key` (structural toggle). SkeletonBuilder seed document section từ Facts default copy; content candidate override. Legacy: `_preserve_content_owned_values` mở rộng cho booking targets; drafts cũ không ảnh hưởng (scope mới). | `body` 4000 chars là editorial policy text, không phải fact. Contract hiện đã coi finalization items là `content` — booking làm tương tự cho nhất quán. |
| `finalization_facts` | Contract v3 **đã** đặt finalization titles/items là owner `content` (source `/content/sections/finalization/...`). Quyết định: hợp thức hóa — P2 chuyển `finalization_facts` trong Facts schema thành optional seed (giữ backward-compat, SkeletonBuilder chỉ dùng khi document chưa có content), khai báo scope `finalization` trong `CONTENT_SECTION_REGISTRY` với owner `content` thay vì `fact-derived`. | Xóa nốt mâu thuẫn "một field 2 chủ". |
| `designer_facts` (12 field copy) | **P2**: thêm Content scope `designer`; xóa allowlist `DESIGNER_FACT_FIELD_BY_DESCRIPTOR` + xóa fallback B5. `travel_designer_id` (structural) ở lại Facts/`presentation_options`. | Xóa ngoại lệ duy nhất cho phép Design ghi Facts → union mutation không còn nhánh `fact` (xem C.2). |
| `hotel.intro` | Giữ Facts (P3/backlog — ít rủi ro vì brochure render `editorialIntroduction` từ Content). | Không chặn mục tiêu chính. |

### B.3. UX Handoff Architecture — "Locked Fact" trên Design Canvas

**Nguyên tắc:** click vào field `owner ∈ {fact, fact-derived}` KHÔNG BAO GIỜ ghi gì (xóa fallback B5). Inspector hiển thị **Locked Panel** với 3 biến thể theo trạng thái quotation:

```
click field khóa → ContextualInspector (Locked Panel)
  ├─ hiển thị: giá trị hiện tại + badge "Structural Fact · Version N" + provenance
  │
  ├─ Case 1: editable (manual + !immutableFacts)
  │    CTA "Edit in Facts" → guardedNavigateStage('facts') + factsDeepLink
  │    (deepLink từ resolveEditableHandoff — hạ tầng ĐÃ CÓ: FactsForm prop
  │     `deepLink`, handoff.editorRoute như `facts.programme.day` + focus{kind,index,id})
  │
  ├─ Case 2: manual + immutableFacts && !isEditingQuotation   ← B8, trọng tâm
  │    Modal "Start Edit Quotation?":
  │      "Facts của version N đã đóng băng. Sửa fact này sẽ tạo business
  │       version N+1; version hiện tại và mọi bản publish giữ nguyên."
  │      [Start Edit Quotation]  → setIsEditingQuotation(true)
  │                              → navigate stage=facts + deep link tới field
  │                              → user sửa, submit = createBusinessVersion
  │                              → redirect version mới (Impact Center review)
  │      [Cancel]
  │    KHÔNG auto-create version khi mở modal — chỉ bật edit mode; version
  │    chỉ sinh ra khi user chủ động submit form Facts (giữ nguyên semantics
  │    hiện có của nút "Edit Quotation" ở header).
  │
  └─ Case 3: source.kind !== 'manual' (DMC handoff)
       Panel giải thích "Facts do DMC Core sở hữu" + opportunityId; không CTA edit.
```

**Deep-link continuity qua version redirect:** `createBusinessVersion` redirect sang URL version mới → mất focus. Giải pháp: truyền `?stage=facts&focus=<encoded-handoff>` khi navigate vào edit-mode (trước khi tạo version); sau redirect, version mới mở Impact Center theo flow hiện có — không cần restore focus sau redirect (user đã sửa xong field trước khi submit). Chỉ cần focus **trước** submit, tức tại bước navigate của Case 2.

**Trade-off đã cân nhắc:**
- ❌ *Cho sửa fact inline trên Design rồi auto-tạo version ngầm*: bị loại — vi phạm nguyên tắc mọi facts mutation phải qua reconciler stack + Impact Center review; tạo version là hành vi nghiệp vụ nặng, không được ngầm định.
- ❌ *Fallback copyOverride như hiện tại*: bị loại — dual SSOT (B5).
- ✅ *Modal + edit-mode + deep link*: rẻ (tái dùng `isEditingQuotation`, `guardedNavigateStage`, `factsDeepLink` đều đã tồn tại), minh bạch, giữ audit trail.

### B.4. Chiến lược xử lý `PUT /document` (B1)

Hai phương án đã cân nhắc:
- **(a) Xóa/thu hồi endpoint** — sạch nhất nhưng phá manifest contract + apply-draft nội bộ dùng chung đường save; rủi ro regression cao.
- **(b) Giữ endpoint, đổi semantics thành "content-merge only" + structural guard** ✅ **CHỌN**: server load document từ DB, diff payload vs DB; mọi khác biệt ngoài tập pointer content-owned/presentation-owned → 422 `STRUCTURAL_FIELDS_LOCKED` (liệt kê paths); khác biệt hợp lệ được merge server-side lên bản DB (không persist nguyên khối payload). DesignCanvas đồng thời chuyển sang `PATCH /content-values` nên `PUT /document` chỉ còn là defense-in-depth + backward-compat.

---

## C. Data & API Contracts

### C.1. Backend — `PATCH /api/v2/quotations/{id}/content-values`

**Vị trí:** `routers/v2/quotation_document.py` (KHÔNG thêm vào `main.py`; helpers qua `_get_helpers()` pattern). Service mới `services/content_value_service.py`. Cập nhật `tests/test_v2_api_manifest_contract.py` (thêm operation, chỉnh semantics note của `PUT /document`).

```python
# routers/v2/quotation_document.py (schema block)
class ContentValueMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=2, max_length=300)   # JSON pointer, id-keyed
    value: str | list[str]

class ContentValuesPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseRevision: int = Field(ge=0)
    mutations: Annotated[list[ContentValueMutation], Field(min_length=1, max_length=40)]

class ContentValuesPatchResponse(BaseModel):
    revision: int
    updatedSources: list[str]
    staleDraftScopes: list[str]
```

```python
# services/content_value_service.py — luồng xử lý
class ContentValueService:
    """Server-enforced, path-scoped content writes from the Design canvas."""

    def apply(self, *, quotation_id: str, lang: str,
              base_revision: int, mutations: list[ContentValueMutation]) -> ContentValuesResult:
        # 1. ACL: từng mutation.source resolve qua
        #    editable_brochure_contract.content_write_allowlist()
        #    (helper mới — union các field owner == 'content', đã expand
        #    id-keyed template). Pointer không khớp → 422 VALIDATION_FAILED,
        #    fieldErrors[].path = source, code = "CONTENT_ACL_DENIED".
        # 2. Load document hiện tại từ DB (không tin bất kỳ document nào từ client).
        # 3. Resolve id-keyed segment → index thực tại (match theo
        #    sourceFactId / hotelSourceFactId / segment id trong document DB).
        #    Id không tồn tại → 422 "TARGET_ENTITY_MISSING" (vd ngày đã bị xóa).
        # 4. Validate value: kind/text budget (tái dùng
        #    core/rules/content_budgets.py qua budget-type của field).
        # 5. Apply mutations immutably lên bản DB; CAS
        #    save_current_document(expected_revision=base_revision)
        #    → DocumentRevisionConflictError → 409 REVISION_CONFLICT.
        # 6. drafts.mark_stale(scopes=touched_content_scopes)  ← đóng lỗ B7
        #    (map source → scope qua services/content_registry.py).
        # 7. append_document_revision(change_source="design_content_values").
```

**Helper mới trong `editable_brochure_contract.py`:**

```python
def content_write_allowlist() -> tuple[str, ...]:
    """Source templates the Design canvas may PATCH (owner == 'content')."""
    return tuple(f["source"] for f in EDITABLE_BROCHURE_FIELDS if f["owner"] == "content")

def resolve_id_keyed_source(source: str, document: dict) -> tuple[str, str] | None:
    """'/itinerary/days/{dayId}/title' -> ('/itinerary/days/3/title', scope)."""
```

**Structural guard cho `PUT /document`** (B4-a, defense-in-depth):

```python
# services/content_value_service.py
MUTABLE_POINTER_PREFIXES = content_write_allowlist() + PRESENTATION_POINTER_PREFIXES

def assert_no_structural_diff(current: dict, submitted: dict) -> None:
    """Raise DocumentStructuralDiffError(paths) if submitted differs from
    current outside content/presentation-owned pointers."""
```
→ wired vào `PUT /document` trước khi merge; lỗi → 422 envelope `{code: "STRUCTURAL_FIELDS_LOCKED", fieldErrors: [{path}...], recovery: "reload"}`.

### C.2. Addressing theo `sourceFactId` — Contract v4

`editable-brochure-contract.json` bump `version: 4`:

- Source per-item đổi index-wildcard → id-keyed: `/itinerary/days/{dayId}/title`, `/itinerary/days/{dayId}/description/0`, `/itinerary/days/{dayId}/activities`, `/stays/hotels/{hotelId}/editorialIntroduction`, `/route/staySegments/{segmentId}/mapSegmentDesc`, media slots tương tự.
- `editable_brochure_contract.py`: `_source_segments`/`_source_templates_intersect` học segment `{param}` (tương đương `*` khi so trùng lặp); thêm `resolve_id_keyed_source`.
- Frontend: `runtimePageBuilder.ts` khi build `EditableText` phát `data-editable` bằng id-keyed pointer (nó có sẵn `day.id`/`hotelSourceFactId` trong document); `editableHandoff.ts::matchEditableSource` match `{param}` segment và trả `params: Record<string,string>`; `DesignCanvas` không còn `setDocumentPath` cho content (chỉ gửi source + value).
- **Transition:** server chấp nhận cả 2 dạng trong 1 sprint (id-keyed ưu tiên; numeric segment resolve như index kèm log cảnh báo), gỡ numeric ở cuối Sprint 16.2.

### C.3. Frontend mutation union (thay `save()` dispatcher)

```typescript
// quote-generator/lib/rules/designMutation.ts  (Layer 1 — pure)
export type ContentPointer = string; // id-keyed JSON pointer, validated by contract

export interface ContentMutation  { kind: "content"; source: ContentPointer; value: string | string[] }
export interface DesignMutation   { kind: "presentation"; target: "copyOverrides" | "identityOverrides";
                                    fieldId: string; value: string }
export interface MediaMutation    { kind: "media"; slotId: string;
                                    value: { r2Key: string; source: "manual" } | { r2Key: string }[] }
export type DesignCanvasMutation = ContentMutation | DesignMutation | MediaMutation;
// KHÔNG có nhánh "fact": field owner=fact chỉ render Locked Panel + handoff (B.3).

export interface ContentPatchRequest { baseRevision: number; mutations: ContentMutation[] }
```

```typescript
// Locked Panel descriptor (ContextualInspector)
export interface LockedFactDescriptor {
  fieldId: string;
  owner: "fact" | "fact-derived";
  currentValue: string;
  factsVersion: number;              // businessVersion.number
  lockState: "editable" | "immutable-manual" | "dmc-owned";
  handoff: { stage: "facts"; editorRoute: string;
             focus?: { kind: string; id?: string; index?: number } };
}
```

### C.4. `FactsConsistencyGate` — Publish consistency

```python
# core/rules/facts_consistency_rules.py  (pure — no I/O, no session)
STRUCTURAL_PROJECTION_PATHS: tuple[str, ...] = (
    "/trip/startDate", "/trip/endDate", "/trip/durationDays", "/trip/durationNights",
    "/itinerary/days/*/id", "/itinerary/days/*/dayNumber",
    "/itinerary/days/*/destinationId", "/itinerary/days/*/overnightId",
    "/party/adults", "/party/children", "/party/kidAges",
    "/pricing/options/*/amounts", "/pricing/options/*/currency",
    "/stays/hotels/*/hotelSourceFactId", "/stays/hotels/*/accommodationId",
    "/stays/hotels/*/checkIn", "/stays/hotels/*/checkOut",
)

def structural_projection(document: dict[str, Any]) -> dict[str, Any]:
    """Extract the structural subtree per STRUCTURAL_PROJECTION_PATHS."""

class FactsConsistencyGate:
    """Compare the persisted document's structural subtree against a fresh
    SkeletonBuilder rebuild from the persisted, resolved Facts."""
    def evaluate(self, *, document_json: dict[str, Any],
                 rebuilt_json: dict[str, Any]) -> GateResult:
        # diff structural_projection(document_json) vs structural_projection(rebuilt_json)
        # mỗi path lệch → GateIssue(code="FACTS_DOCUMENT_DIVERGENCE", path=..., 
        #                           expected=..., actual=...)
```

**Wiring** (`main.py::_canonical_review_status`): thêm block sau `impact_blockers`:
1. Rebuild `SkeletonBuilder().build(...)` từ facts đã persist (tái dùng đúng đường `PUT /facts` đang dùng — server-side, không nhận input client).
2. `FactsConsistencyGate().evaluate(...)`; đồng thời wire `PublishReadinessGate` (trên `document_json`) và `QuotationTransitionGate` (trên resolved facts).
3. Issues → nhập vào `review["blockers"]`; publish tiếp tục trả 422 `REVIEW_BLOCKED` (`recovery: "open-blockers"`) theo envelope hiện có — **không thêm error code mới** vào frozen envelope contract.

So khớp dùng **canonical normalization** (sort keys, chuẩn hóa None/"" ) để tránh false positive; các field content-owned và presentation không nằm trong projection nên không bao giờ block vì copy.

---

## D. Phased Implementation Plan (Sprint Roadmap)

> Quy ước chung mọi sprint: Router → Service → Repository; test contract (`test_*_contract.py`) chỉ được sửa khi thay đổi public shape có chủ đích; frontend pass đủ `npm run lint` (chain) + `npm run build`; backend pass `PYTHONPATH=. pytest` các suite liệt kê.

### Sprint 16.1 — P0 Backend: Content-Values Endpoint & Structural Guard

| # | Task | Files | Test |
| :-- | :-- | :-- | :-- |
| 1.1 | `content_write_allowlist()` + `resolve_id_keyed_source()` + hỗ trợ `{param}` segment trong intersect check | `editable_brochure_contract.py` | `tests/test_editable_brochure_contract.py` (mới): allowlist đúng 30+ source, param-segment overlap detection |
| 1.2 | `ContentValueService` (ACL → load DB doc → resolve id → budget validate → immutable apply → CAS → `mark_stale` → `append_document_revision(change_source="design_content_values")`) | `services/content_value_service.py` (mới) | `tests/test_content_value_service.py`: happy path; ACL denied (pointer fact) → 422; id missing → 422; stale revision → `DocumentRevisionConflictError`; drafts cùng scope thành `stale` |
| 1.3 | Router `PATCH /content-values` (Pydantic models C.1, auth `require_owned_quotation`, error envelope chuẩn) | `routers/v2/quotation_document.py` | `tests/test_content_values_api.py` (mới): 200/422/409/403; **cập nhật `tests/test_v2_api_manifest_contract.py`** thêm operation |
| 1.4 | Structural guard cho `PUT /document`: `assert_no_structural_diff` → 422 `STRUCTURAL_FIELDS_LOCKED`; merge server-side thay vì persist payload nguyên khối | `services/content_value_service.py`, `main.py:7279-7367` | `tests/test_document_structural_guard.py` (mới): payload sửa `trip.itinerary` length / pricing amount / party → 422 liệt kê paths; payload chỉ sửa content/presentation → pass; apply-draft nội bộ không regression (`tests/` content-draft suites xanh) |
| 1.5 | Regression sweep | — | `PYTHONPATH=. pytest tests/test_v2_api_manifest_contract.py tests/test_v2_error_envelope.py tests/test_domain_rules.py tests/test_business_gates.py tests/test_ssot_integrity.py` |

### Sprint 16.2 — P0 Frontend: Mutation Flow, sourceFactId, Locked-Fact UX

| # | Task | Files | Test |
| :-- | :-- | :-- | :-- |
| 2.1 | Contract v4: id-keyed sources (C.2); server transition chấp nhận numeric tạm thời | `editable-brochure-contract.json`, `editable_brochure_contract.py` | test 1.1 mở rộng; snapshot fields count |
| 2.2 | `runtimePageBuilder` phát `data-editable` id-keyed; `matchEditableSource` hỗ trợ `{param}` + trả `params` | `quote-generator/display/runtimePageBuilder.ts`, `components/quotation-workspace/editableHandoff.ts` | `lib/__tests__/editableHandoff.test.ts`: match id-keyed, reorder không đổi target |
| 2.3 | `lib/rules/designMutation.ts` (union C.3, pure Layer-1) + `DesignCanvas.save()` content branch → `PATCH /content-values` (bỏ `saveCanonicalDocument` whole-doc, bỏ `setDocumentPath` cho content); 409 → refresh + retry một lần (giữ pattern hiện có) | `lib/rules/designMutation.ts` (mới), `components/quotation-workspace/DesignCanvas.tsx` | `lib/__tests__/designMutation.test.ts`; smoke: sửa day description qua canvas → chỉ 1 request PATCH, payload chỉ chứa mutation |
| 2.4 | **Xóa fallback fact→copyOverride** (B5); Locked Panel trong `ContextualInspector` với 3 case B.3 (`LockedFactDescriptor`) | `DesignCanvas.tsx:354-364`, `ContextualInspector.tsx` | test UI state: field fact + immutable → không có nút Save, có CTA đúng case |
| 2.5 | Edit Quotation modal flow: modal Case 2 → `setIsEditingQuotation(true)` + `guardedNavigateStage('facts')` + `factsDeepLink` (encode qua `?focus=`); Case 1 dùng deep link trực tiếp; Case 3 panel DMC | `QuotationWorkspaceClient.tsx`, `ContextualInspector.tsx`, `FactsForm.tsx` (nhận focus các nhóm pricing/customer nếu chưa có anchor) | e2e Playwright: click locked price trên Design → modal → edit mode → field được focus; submit → `POST /versions` |
| 2.6 | Quality gates | — | `cd quote-generator && npm run lint && npm test && npm run build` |

### Sprint 16.3 — P1 Publish Consistency Gate

| # | Task | Files | Test |
| :-- | :-- | :-- | :-- |
| 3.1 | `FactsConsistencyGate` + `structural_projection` (C.4, pure) | `core/rules/facts_consistency_rules.py` (mới) | `tests/test_facts_consistency_gate.py` (mới): identical → pass; lệch duration/pricing/party/day-id → GateIssue đúng path; content/presentation lệch → KHÔNG issue |
| 3.2 | Wire vào `_canonical_review_status`: SkeletonBuilder rebuild + FactsConsistencyGate + `PublishReadinessGate` + `QuotationTransitionGate` → `review.blockers` | `main.py:8895-8937` | `tests/test_business_gates.py` mở rộng: publish với document đã bị làm lệch (bơm trực tiếp qua repository trong test) → 422 `REVIEW_BLOCKED`; quotation hợp lệ → publish 202 như cũ |
| 3.3 | Review stage UI hiển thị blocker `FACTS_DOCUMENT_DIVERGENCE` với path + nút "Rebuild from Facts" (gọi lại `PUT /facts` no-op để server rebuild+preserve) | `components/quotation-workspace/` review components | e2e: lệch → blocker hiện; rebuild → blocker biến mất |
| 3.4 | Perf check: rebuild SkeletonBuilder trong review status (đã chạy mỗi lần mở Review) — đo thêm ~1 build/request; nếu >100ms, cache theo `(facts_row_id, revision)` | — | benchmark ghi vào PR |

### Sprint 16.4 — P2 Cleanup & Migrations

| # | Task | Files | Test |
| :-- | :-- | :-- | :-- |
| 4.1 | `runtimePageBuilder` dùng `presentationReconciler.resolveEffectivePresentationValue` (xóa precedence hardcode); thêm `mediaOverrides` vào `CanonicalPresentationState` + `syncToDocument` | `display/runtimePageBuilder.ts`, `lib/rules/presentationReconciler.ts`, `presentationAdapter.ts` | `lib/__tests__/presentationReconciler.test.ts` + `runtimePageBuilderContentOwnership.test.ts` giữ xanh (precedence không đổi hành vi) |
| 4.2 | Xóa `title` khỏi `ItineraryDayFact` + mọi UI Facts form liên quan | `factsTypes.ts:32-49`, `FactsForm` day editor | `npm test`; grep không còn tham chiếu |
| 4.3 | Content scope `designer`: registry entry + candidate contract, migrate 12 field khỏi Facts-allowlist; xóa `DESIGNER_FACT_FIELD_BY_DESCRIPTOR` & `onSaveDesignerFacts` | `services/content_registry.py`, `services/content_draft_service.py`, `DesignCanvas.tsx`, `QuotationWorkspaceClient.tsx:824-836`, contract v4 fields đổi owner | pytest content-draft suites + contract test; e2e sửa designer quote qua Design → content-values |
| 4.4 | Content scope `booking_terms` (B.2): registry + SkeletonBuilder seed + `_preserve_content_owned_values` mở rộng; Facts giữ `items[].key` | `services/content_registry.py`, `services/skeleton_builder.py`, `main.py` preserve helper, `quote_document.py` (body → optional/deprecated) | pytest: facts save không mất booking copy; contract suites |
| 4.5 | Content Studio: confirm dialog khi Generate sẽ thay `localCandidate` chưa save (B7) | `components/content-studio/useContentGeneration.ts`, UI | unit test hook |
| 4.6 | Gỡ hỗ trợ numeric-index source transition (2.1) | `editable_brochure_contract.py`, service | contract tests |

### Definition of Done toàn plan

- [ ] Không tồn tại đường ghi nào từ client có thể thay đổi structural subtree của `document_json` mà không đi qua `PUT /facts` (SkeletonBuilder) — chứng minh bằng `test_document_structural_guard.py` + `test_content_values_api.py`.
- [ ] Mọi content edit trên Design đi qua `PATCH /content-values` với ACL server-side; `mark_stale` draft cùng scope.
- [ ] Publish bị chặn `REVIEW_BLOCKED` khi document lệch Facts (FactsConsistencyGate) — kể cả dữ liệu lệch được bơm thẳng vào DB.
- [ ] Click field khóa trên Design khi facts immutable → modal Edit Quotation → edit mode + deep link; không còn fallback copyOverride im lặng.
- [ ] Addressing per-day/per-hotel hoàn toàn theo `sourceFactId`; reorder/xóa ngày không bao giờ gán nhầm edit.
- [ ] Contract suites (`test_v2_api_manifest_contract.py`, `test_v2_error_envelope.py`, `test_ssot_integrity.py`) xanh với các edit có chủ đích được ghi chú trong PR.
- [ ] Brochure đã publish và mọi đường render hiện hữu không đổi hành vi (release trỏ revision lịch sử — không backfill).

---

## E. Phụ lục — Rủi ro & Câu hỏi mở

| Rủi ro | Giảm thiểu |
| :-- | :-- |
| Structural guard 1.4 false-positive do serialization drift (None vs "", key order) giữa payload client và DB | Canonical normalization trước diff; rollout theo 2 bước: 1 tuần chỉ log-warning (metric đếm diff paths), sau đó mới enforce 422 |
| FactsConsistencyGate chặn nhầm quotation legacy có document cũ lệch schema | Gate chỉ áp cho quotation `source_kind == "manual"` chưa publish version hiện tại; legacy lệch → hiển thị blocker kèm nút "Rebuild from Facts" thay vì bắt sửa tay |
| Contract v4 đổi source làm lệch client cache cũ | `version` field trong payload contract; client so version, force refresh khi lệch |
| Sprint 16.4.3/4.4 đổi owner field trong contract → đổi hành vi Design tab | Chạy sau khi 16.1–16.3 ổn định; mỗi migration một PR riêng có e2e |

**Câu hỏi mở (không chặn P0):** (1) Có cần UI ẩn/hiện section phụ + theme variant trên Design không (hiện chưa có control nào)? Nếu có → mở plan 17, ghi vào `presentation.sectionVisibility`. (2) `hotel.intro` trong Facts có nên di cư đợt sau cùng scope với `hotel_plan` không?
