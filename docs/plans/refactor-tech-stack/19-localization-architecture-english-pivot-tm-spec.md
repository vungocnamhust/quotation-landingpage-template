# 19 — Kiến Trúc Localization: English-Pivot Transcreation, Translation Memory & Human Review

> Trạng thái: **Đặc tả kỹ thuật (Phase 1 hoàn tất — Audit & Spec)**
> Phạm vi: Core Backend (FastAPI :8111) + `quote-generator` (Next.js 16 :8115) + Prompt stack `prompts/v1`
> Ngày: 2026-09-04
> Tài liệu liên quan: `18-tourplan-simple-dmc-business-strategy-and-ai-blueprint.md`, `content-studio-draft-lifecycle-persistence-plan.md`

---

## 0. Tóm tắt điều hành & Quyết định kiến trúc

**Quyết định:** Chọn **Kiến trúc C' — English-Pivot Transcreation neo vào Facts** (biến thể của C, kế thừa toàn bộ ưu điểm vận hành của A):

1. Bản tiếng Anh (`lang = baseline_lang = "en"`) là **tài liệu chủ (master)** duy nhất về tính đúng thương mại. Mọi locale khác là **dẫn xuất (derived)**, không bao giờ được sinh trực tiếp từ facts mà không có bản EN tương ứng.
2. Localization Agent nhận **đồng thời** (a) đoạn EN đã được **mask entity** và (b) **facts snapshot** của scope đó (skeleton ngữ nghĩa), rồi **viết lại bằng cú pháp bản ngữ** — không dịch tuần tự từng câu.
3. Mọi đoạn văn được lưu ở mức **segment** trong **Translation Memory (TM)** trên PostgreSQL 16 JSONB (không thêm MongoDB/Redis — stack hiện tại chỉ có Postgres, xem §4.1).
4. Bản dịch đi qua vòng đời `generated → needs_review → approved → published`, có cảnh báo `stale` khi EN master đổi revision.
5. Thêm ngôn ngữ mới (`ja`, `ko`, `ms`) = thêm **1 file `LocaleProfile` YAML + 2 file label JSON + 1 font entry**, không sửa render loop.

**Lý do cốt lõi (từ audit):** V2 hiện tại có 2 đường sinh nội dung đa ngữ **không liên quan nhau**:
- Content Studio V2 (`services/content_draft_service.py`) sinh draft **trực tiếp từ facts theo từng `lang`**, nhưng prompt stack **không có chỉ thị ngôn ngữ đích** — `lang` chỉ xuất hiện như 1 khóa trong JSON facts. Kết quả: bản `vi` và bản `en` của cùng một quotation có thể **khác nội dung** (không phải khác ngôn ngữ) → rủi ro sai lệch thương mại.
- Legacy V1 (`main.py:728 translate_payload_llm`) là dịch danh sách chuỗi phẳng, không ngữ cảnh, không mask entity, không TM, lưu vào `published/{id}/ctx.json` trên đĩa, không có review.

Kiến trúc C' hợp nhất hai đường này thành một pipeline có kiểm soát.

---

## 1. Audit toàn diện các điểm chạm đa ngữ (Multi-Language Touchpoints)

### 1.1 Bản đồ file — Backend (Python / FastAPI)

| Lớp | File | Điểm chạm | Ghi chú audit |
| :-- | :-- | :-- | :-- |
| Static dictionary | `core/i18n.py` | `STATIC_DICTIONARY: dict[str, dict[str,str]]` — **245 khóa EN**, mỗi khóa có `vi` và `ar` (245/245). 13 khóa `ar` giữ nguyên EN (tên địa danh). 22 khóa là **câu dài >80 ký tự** (đoạn văn giới thiệu specialist, điều khoản) — đây là narrative copy đang bị nhét vào dictionary chrome. | Khóa = chuỗi EN nguyên văn → mọi thay đổi dấu câu ở EN làm mất bản dịch. Không có `ja/ko/ms`. |
| Composition root | `main.py:174` | `from core.i18n import STATIC_DICTIONARY` | |
| | `main.py:432-448` | `translate_filter(text, lang)` → Jinja2 filter `translate` (legacy template path) | |
| | `main.py:581-593` | `rtl_mixed_filter` — bọc chuỗi hỗn hợp Latin/Arabic cho RTL trong template Jinja2 | Chỉ legacy. |
| | `main.py:660-726` | `format_duration_display`, `format_currency_display(lang)`, `normalize_room_note(lang)`, `canonicalize_place_names_in_data`, `localize_place_name` — **định dạng số/tiền/ngày theo lang bằng `if lang == "ar"` hardcode** | Cần thay bằng LocaleProfile (§6). |
| | `main.py:728-914` | `translate_payload_llm(payload_dict, target_lang, baseline_lang)` — LLM batch dịch danh sách chuỗi; có `is_translatable()` loại trừ ngày ISO, mã `QT-/VS-`, khóa kỹ thuật; kiểm tra **numeric drift** (chuẩn hóa chữ số Ả Rập-Ấn → giữ nguyên nguồn nếu số lệch). | Tiền thân của Entity Guard (§3.1) nhưng chỉ ở mức "phát hiện & rollback từng chuỗi", không mask. |
| | `main.py:988-1040` | `_translate_item_on_demand` → ghi `translations[lang]` vào `published/{id}/ctx.json` | Không DB, không revision, không review. |
| | `main.py:7089-7130` | `POST /api/v1/{quotations,itineraries}/{id}/translate?lang=`, `GET .../translation-status` | Legacy V1 surface. |
| | `main.py:5248` | `_resolve_v2_locale(quotation_id, requested_lang)` — lấy `quotation.baseline_lang` làm mặc định, **hardcode `{"en","vi","ar"}`** → 422 nếu khác | Điểm cắm LocaleRegistry. |
| | `main.py:3665-3690` | `_load_canonical_quote_document_from_db(quotation_id, target_lang)` — **fallback về baseline doc nếu doc locale đích chưa tồn tại** | Đây là cách một doc `vi` "ra đời": workspace mở `?lang=vi` → nhận doc EN → autosave ghi thành doc `vi` chứa tiếng Anh. |
| | `main.py:3646-3652` | `_hydrate_canonical_quote_document(..., lang)` chỉ set `meta.lang` | Không có `meta.sourceLang/sourceRevision`. |
| | `main.py:9054`, `9226`, `9446` | `_canonical_review_status(lang)`, `publish_canonical_quotation_v2(lang)`, `list_canonical_publications(lang)` — publish **theo từng locale**, advisory lock key `"{quotation_id}:{brand_id}:{lang}"` | Đã sẵn sàng cho multi-locale publish. |
| Router V2 | `routers/v2/quotation_document.py:155-230` | `put_quotation_document(target_lang)` — hardcode `("en","vi","ar")`, `save_current_document(lang=effective_lang)` + `append_document_revision(change_source="autosave")` | |
| | `routers/v2/quotation_document.py:257,311,365` | list/create/apply content drafts với `effective_lang = lang or baseline_lang` | |
| | `routers/v2/quotation_facts.py:64-193` | Facts PUT **chỉ ghi vào `quotation.baseline_lang`** doc | Đúng: facts là ngôn ngữ-độc-lập; nhưng không có cơ chế lan (propagate) sang doc locale khác → doc `vi` giữ facts cũ. **Defect tiềm ẩn**. |
| | `routers/v2/quotation_versions.py:189,260` | redirect URL luôn kèm `lang={baseline_lang}` | |
| Service | `services/content_draft_service.py:104-116` | `_fingerprint(spec, lang, mode, facts_hash, instruction)` → `prompt_version`; `find_cached(quotation_id, lang, scope, mode, facts_hash, prompt_version)` | Cache key **có lang** nhưng prompt **không** có chỉ thị ngôn ngữ → cache đúng nhưng nội dung không xác định ngôn ngữ. |
| | `services/content_draft_service.py:303-331` | `create(lang=...)` → `generator.generate(spec, brand, facts_snapshot, mode, instruction)` — **`lang` không được truyền vào generator** | |
| | `services/section_content_generator.py:15` | `BRAND_POLICY_VERSION = "luxury-premium-en-v1"` — hardcode EN, đưa vào fingerprint | |
| | `services/section_content_generator.py:39-150` | `HeroOutput/OverviewOutput/RouteOutput/DayOutput` — `max_length` Pydantic lấy từ `content_budgets.yaml` (**ký tự EN**) | Bản `ar`/`vi` dài hơn sẽ bị 422 hoặc bị cắt ý. |
| | `services/content_registry.py:170,191,275-293` | `"lang"` là **fact input** của hero/overview/route/itinerary (`FactDependency("lang","content_input","review_or_generate",...)`) | Đổi lang ⇒ hệ thống coi là "facts đổi" ⇒ yêu cầu regenerate — đúng hướng nhưng chưa có nguồn EN. |
| | `services/publication_runtime.py:51`, `publication_worker.py:184` | URL công khai `https://{hostname}/{locale}/q/{slug}` | |
| | `services/quote_request_service.py:778`, `quotation_version_application_service.py:122` | `baseline_lang=effective_lang` khi tạo quotation / successor version | |
| Prompt stack | `prompts/v1/system_base.yaml` | `role: "senior luxury travel copywriter for premium clients from the US, UK, and Australia"` | Ngầm định EN. |
| | `prompts/loader.py:152-280` | `build_system_prompt` / `build_prompt_bundle` — **không có tham số locale**; user prompt = `Scope + Writing instruction + Input Facts JSON` | Điểm cắm §3.2. |
| | `prompts/v1/ground_rules.yaml` | Chú thích đầu file: `~120 words ≈ 600-800 chars`, trần PDF A4 **1,150 ký tự** — đo bằng ký tự Latin | |
| | `prompts/v1/content_budgets.yaml` + `core/rules/content_budgets.py` | `min_chars/max_chars/pdf_ceiling_chars` **một bộ số cho mọi locale**; `tests/test_ssot_integrity.py` khóa đồng bộ với `quote-generator/config/contentBudgets.json` | |
| | `prompts/v1/tools/translation.yaml` | Stub 6 dòng, `tool: "translation"`, **chưa được `PromptLoader` nạp** (không có `get_tool_config`) | |
| | `prompts/v1/brands/*.yaml`, `modes/*.yaml` | Tone/voice — giữ nguyên, **không** nhân bản theo locale (xem §2). | |
| DB | `db/models/quotation.py:27` | `Quotation.baseline_lang String(5) default "en"` | |
| | `db/models/quotation.py:82-110` | `QuotationDocument` — `UniqueConstraint(quotation_id, lang)`; `document_json` chứa `meta.lang` | 1 doc hiện hành / locale. |
| | `db/models/quotation.py:113-132` | `QuotationDocumentRevision` — `Index(quotation_id, lang, revision)`, append-only, `change_source` | Lịch sử **độc lập theo locale**; không có cột nào liên kết revision `vi` ↔ revision `en` nguồn. |
| | `db/models/quotation.py:135-157` | `QuotationContentDraft` — `Index(quotation_id, lang, scope, generation_mode, facts_hash)`; `prompt_version`, `source_document_revision`, `candidate_json`, `generation_metadata` | Có sẵn khung "candidate → apply" theo lang. |
| | `db/models/publication.py:12-38` | `QuotationPublication` `UniqueConstraint(quotation_id, version, lang)` | |
| | `db/models/publication.py:41-66` | `PublicationTarget` `UniqueConstraint(brand_id, locale, public_slug)` + `(quotation_id, brand_id, locale)` | Slug ổn định theo locale. |
| | `alembic/versions/20260729_01`, `20260804_03`, `20260806_09` | Các cột `lang`/`locale` `String(5)` | Đủ chứa BCP-47 ngắn (`ja`, `ko`, `ms`, `zh-TW` = 5). |
| Tests | `tests/test_v2_workspace_locale_contract.py` | Khóa: không hardcode `lang: str = "en"` ở 5 route V2; workspace resolve locale trước hydration; content-studio chỉ redirect | Contract phải giữ xanh. |
| | `tests/test_v2_api_manifest_contract.py` | Mọi route V2 mới (§7.3) phải đăng ký ở đây | |
| Legacy | `quote_generation.py:252-270, 455-475, 645-685` | Sinh brochure V1 với `request.lang`; mode instruction đếm **words** | Đóng băng, không mở rộng. |
| | `templates/*.html`, `published/` | Jinja2 + `translate`/`rtl_mixed` filters | Đóng băng. |

### 1.2 Bản đồ file — Frontend (`quote-generator`)

| File | Điểm chạm | Ghi chú audit |
| :-- | :-- | :-- |
| `display/contracts.ts:9-11` | `LANGUAGE_CODES = ['en','vi','ar'] as const`, `type LanguageCode` | Hằng compile-time → thêm locale = sửa code. Mục tiêu §6: sinh từ `config/locales.json`. |
| `app/[locale]/q/[slug]/page.tsx` | Validate `locale ∈ LANGUAGE_CODES`, `resolvePublicQuotation({hostname, locale, slug})`, `force-dynamic`, `generateMetadata` canonical `https://{hostname}/{locale}/q/{slug}`; truyền `lang: locale` vào `buildDisplayDocumentFromQuoteDocument` | Không có `alternates.languages` (hreflang) cho các locale khác. |
| `app/layout.tsx:44` | `<html lang="en">` **cứng** | `lang`/`dir` phải lấy từ locale route (agent audit §1.2b). |
| `display/labels.ts:3-239` | `I18N_LABELS` — **70 khóa × 3 locale (en/vi/ar), parity 100%**; `PRICING_AMOUNT_LABELS` 6 × 3; `getLanguageLabels(lang)` fallback `en` | Có **narrative dài** (`termDepositBody`, `journeyTogetherTagline`) trong label chrome — cùng lỗi phân lớp như `STATIC_DICTIONARY`. |
| `display/runtimePageBuilder.ts`, `display/pageBuilder.ts` | Nhận `lang`, chọn label set, build `PageViewModel` | |
| `config/typography.ts:945-1010` | `buildArabicBlock()` — `[dir="rtl"]` override `--font-heading/--font-body/--font-accent` sang Amiri / Noto Sans Arabic / Cairo bằng `!important` | Chỉ có 1 khối RTL cứng cho Arabic; không có cơ chế `[lang="ja"]`. |
| `app/fonts.ts` | `next/font/google`: Cormorant, Montserrat, Noto Sans Arabic, Cairo, Amiri | Thêm CJK = thêm font entry (chi phí bundle — xem §6.3). |
| `app/pdf/**` | PDF render theo doc + lang (agent audit) | PDF preflight dùng `pdfCeilings` (ký tự). |
| `config/contentBudgets.json` | Mirror của `content_budgets.yaml` (`npm run sync:budgets`) | Không locale-aware. |
| `app/workspace/quotations/[quotationId]/edit/page.tsx` | `resolveWorkspaceWorkflow` → `workflow.locale`; redirect nếu `requestedLocale !== workflow.locale` | Workspace luôn ép về **baseline locale** → hiện **không có UI** cho locale thứ hai. |
| `proxy.ts`, `next.config.ts` | Rewrite `/api/v1/*` → backend; không có locale middleware | |

#### 1.2b Phát hiện chi tiết frontend (bổ sung sau audit sâu)

| # | Phát hiện | Bằng chứng | Hệ quả |
| :-- | :-- | :-- | :-- |
| F1 | **`dir` chưa bao giờ được set** ở bất kỳ đâu | `config/typography.ts:948,959,965` là 3 chỗ duy nhất nhắc `[dir="rtl"]` — đều là selector; không có writer. `DisplayDocument` (`display/runtimePageBuilder.ts:9-19`) và `display/types.ts` không có trường `dir`; `components/DisplayPage.tsx:16-22` không emit `lang`/`dir` | Brochure `ar` render LTR. Khối font Arabic gần như chết. |
| F2 | **`<html lang>` sai trên route công khai** | `app/layout.tsx:43-50` cứng `lang="en"`; script inline `:14-35` đọc `?lang=` — `/ar/q/{slug}` không có query ⇒ luôn `en`. Chỉ `app/pdf/page.tsx:25-30` set đúng từ `payload.locale`; 3 route PDF còn lại (`app/[locale]/q/[slug]/pdf`, `app/p/[fallbackSlug]/pdf`, `app/internal/releases/[releaseId]/pdf`) không set | PDF `ar` in không đúng font. |
| F3 | `globals.css` có **85** thuộc tính vật lý (`margin-left/right`, `left:`, `right:`) và **0** rule RTL/logical (`:lang()`, `[dir=`, `unicode-bidi` không tồn tại) | grep toàn file 4762 dòng | Có set `dir="rtl"` cũng không mirror layout. |
| F4 | Danh sách locale **trùng lặp 4 lần** | `display/contracts.ts:9`, `proxy.ts:22` (regex `(en\|vi\|ar)`), `next.config.ts:12` (`/:locale(en\|vi\|ar)/q/:slug`), `runtimePageBuilder.ts:539-545` languageOptions cứng, `MinimalQuotationIntakeForm.tsx:168-172` fallback cứng; `factsTypes.ts:183,455,473` union type | Thêm locale = sửa ≥6 chỗ. |
| F5 | **3 tag Intl khác nhau cho Arabic** | `runtimePageBuilder.ts:99` `Intl.DateTimeFormat(lang)` với `'ar'` trần; `:103` `NumberFormat('ar')`; `lib/rules/datesRules.ts:39` `'ar-SA'` | Chữ số Ả Rập-Ấn xuất hiện không nhất quán giữa ngày và tiền. |
| F6 | Formatter **mù locale** trên dữ liệu có locale | `datesRules.ts:94 formatTravelDatesLabel` cứng `en-GB`; `lib/moneyFormat.ts:13` `toLocaleString(undefined)` = locale runtime của server; `workspaceQuotationKanban.ts:18` `en-US` | `trip.travelDates` luôn EN trong doc `vi/ar`. |
| F7 | **Budget mù script** | `config/contentBudgets.json`: 63 `pdfCeilings` + 7 nhóm budget, 0 khóa locale; `lib/rules/contentReconciler.ts:132` đếm `.length` UTF-16; `promptRule`/`targetWords` tiếng Anh được đưa nguyên vào prompt mọi locale | `ar`/`vi` bị chặn sai hoặc tràn PDF. |
| F8 | `workflowReconciler.ts:116-118,252-254` **nhị phân `isVi`** | Arabic rơi vào nhánh English cho blocker messages | Reviewer `ar` thấy lỗi tiếng Anh. |
| F9 | Không có `alternates.languages` (hreflang) | `app/[locale]/q/[slug]/page.tsx:42-47`, `app/p/[fallbackSlug]/page.tsx:23-30` | SEO đa ngữ không được khai. |
| F10 | **Language switcher công khai vô hiệu** trên route canonical | `components/AppTopBar.tsx:74` phát `?lang=`; route `[locale]` bỏ qua query, dùng path segment | Khách không đổi được ngôn ngữ trên `/en/q/…`. |
| F11 | Bảng label rải **4 nơi** + ternary inline | `display/labels.ts`, `display/pageBuilderFixtures.ts:190` (bản sao fixture, được `lint:v2-runtime-imports` cấm import), `app/routeState.ts:133-156` (`getTopbarLabels`), ternary `lang === 'vi' ? … : lang === 'ar' ? …` tại `contentReconciler.ts:189,205,248,252,265,305,353`, `partyReconciler.ts:439-612` | Thêm locale phải chạm 6+ file. |
| F12 | Locale workspace **do server quyết định**, không có UI chọn locale thứ hai | `edit/page.tsx:23-31` redirect về `workflow.locale`; `PublicationTargetManager.tsx` không có locale picker (`locale` read-only, `:14,:64`); `publishQuotation` gửi `lang` của workspace | Hiện **không có đường** tạo/duyệt bản `vi` từ UI ngoài autosave fallback. |
| F13 | Mọi call Content Studio đều mang `?lang=` | `useContentGeneration.ts:108,133,221,296,340,437,467,512,538`; `useQuotationWorkspace.ts:59-65` (trừ `facts`, `options`, `brands`) | Đúng: sẵn sàng cho stage `localize` với `target`. |
| F14 | **Không có test** cho labels/RTL/format theo locale | Không test nào import `getLanguageLabels`, `PRICING_AMOUNT_LABELS`, `LANGUAGE_CODES`; 0 lần `rtl` trong `lib/__tests__`; `moneyFormat.test.ts:7,11` tự tham chiếu (`toLocaleString(undefined)` hai bên) | Regression RTL/locale không bị bắt. |
| F15 | Font | `app/fonts.ts`: Cormorant/Montserrat có subset `vietnamese`; Arabic 3 họ (Noto Sans Arabic, Cairo, Amiri); **0 CJK**; signature font (MyFonts) không có glyph VI/AR/CJK | `ja/ko` cần 2 font mới; signature fallback `cursive`. |
| F16 | PDF pagination **đếm mục**, không đếm ký tự | `lib/rules/pdfRules.ts:9-16` 2 ngày/trang; `:27-50` thang khách sạn cố định | Trần ký tự chỉ là lớp cảnh báo; lớp vật lý là số dòng thực. |
| F17 | `components/display/**` **0 tham chiếu locale** (46 file) | Mọi chuỗi đã được resolve ở `runtimePageBuilder.ts`; không `Intl.*`, không `<bdi>`, không `dir` prop; map label offset tính pixel trái/phải tuyệt đối | Đúng thiết kế 5-layer; RTL phải giải quyết ở view-model + CSS, không ở section. |

#### 1.1b Phát hiện chi tiết backend (bổ sung)

| # | Phát hiện | Bằng chứng | Hệ quả |
| :-- | :-- | :-- | :-- |
| B1 | **Locale không bao giờ tới bước sinh nội dung** | `content_draft_service.py:329,401,411,523` gọi `generator.generate(spec, brand, facts_snapshot, mode, instruction)` — không có `lang`; `PromptBundle` (`prompts/loader.py:14`) không có trường lang; `lang` chỉ dùng cho fingerprint/cache/row | Draft `vi` = draft EN sinh lại với cache key khác (hoặc ngẫu nhiên đổi ngôn ngữ vì `lang` lọt trong facts JSON). |
| B2 | **Hai hành vi khác nhau cho locale không hợp lệ** trong cùng router | `routers/v2/quotation_document.py:118-120,154-156` ép về `None` → baseline (im lặng); các route content-drafts (`:410,428,478,538,581,708,784`) 422 qua `_resolve_v2_locale`; `main.py:9323 resolve_public_quotation_v2` 404 | Cần 1 helper `LocaleRegistry.require()` với 3 chính sách rõ: public 404 / staff 422 / không bao giờ im lặng. |
| B3 | 1 default cứng còn sót | `main.py:9515 download_canonical_publication_pdf(..., lang: str = "en")` — không nằm trong guard list `test_v2_workspace_locale_contract.py:11-20` | Sửa ở Phase 1. |
| B4 | Triple `("en","vi","ar")` literal ở **≥12 chỗ** | `main.py` 5255, 6488, 6688, 7093, 7104, 9323, 9546; `routers/v2/quotation_document.py` 119, 155; `routers/v1/translations.py:26`; `main.py:4793` (dead code sau 410) | `LocaleRegistry` + contract test cấm literal. |
| B5 | Không có CHECK constraint DB trên `lang`/`locale`; cột `String(5)` | Alembic `20260729_01`, `20260804_03`, `20260806_09` | **Tốt** cho mở rộng: thêm `ja` không cần migration. Giữ nguyên, không thêm CHECK. |
| B6 | Đặt tên cột không nhất quán | `publication_targets.locale` vs `lang` ở mọi bảng khác | Không đổi (migration rủi ro); API layer dùng `locale` thống nhất, repository map. |
| B7 | `translate_filter` fallback **bỏ dấu tiếng Việt** khi miss | `main.py:441-445`: nếu `lang != "vi"` và miss dictionary ⇒ NFD strip `Mn` + `Đ→D` | Request `ar` miss ⇒ trả Latin không dấu, không phải Arabic. Legacy only. |
| B8 | `routers/v1/translations.py` tồn tại | `POST /api/v1/translate-block` (`:23`, `TranslateBlockRequest{text, target_lang, source_lang="en"}`), `:76,:89` translate quotation/itinerary | Surface V1 thứ hai cho dịch, song song `main.py:7089`. Đóng băng; thay bằng §7.3. |
| B9 | `tests/test_migration_phase_e.py:292-318` pin **3 doc row `ar/en/vi`** cho 1 quotation với `baseline_lang="ar"` | `GET /document?lang={lang}` trả `lang` tương ứng | Mô hình 1-doc/locale đã là contract; C' giữ nguyên, chỉ thêm `meta.localization`. |
| B10 | Locale branches rải trong service | `services/skeleton_builder.py:26-46` (`_route_stop_default` vi/ar/else), `quote_request_service.py:136` (default meals), `facts_resolver.py:93`, `main.py:1486-1566` (`Ngày {n}`/`اليوم {n}`) | Tier A/glossary; chuyển sang `core/i18n/{locale}.json` + `LocaleProfile.formats` ở Phase 4. |
| B11 | `prompts/v1/tools/translation.yaml` là file **duy nhất** trong prompt stack nhắc ngôn ngữ đích; `PromptLoader` không có `get_tool_config` | grep toàn `prompts/v1` | Thay bằng `prompts/v1/localization/agent.yaml` + `locales/*.yaml`. |
| B12 | Budgets: `target_words`/`target_paragraphs` **không bao giờ được so sánh**; chỉ `*_chars` enforce; registry là singleton module-level (`section_content_generator.py:41`) | `core/rules/content_budgets.py:14-29,145` | Budget locale phải là hàm (`get_max_chars_for_locale`), không phải registry thứ hai. |

### 1.4 Danh sách defect cần sửa độc lập với kiến trúc mới (Phase 1 quick-fix)

1. `app/[locale]/layout.tsx` (mới): `<html lang={locale} dir={direction}>` từ route segment; bỏ script đọc `?lang=` trong `app/layout.tsx`. Áp dụng cho cả 4 route PDF. *(F1, F2)*
2. `main.py:9515`: bỏ `lang: str = "en"`, dùng `_resolve_v2_locale`; thêm `download_canonical_publication_pdf` vào guard list test. *(B3)*
3. Thống nhất Intl tag: 1 hàm `resolveIntlTag(lang)` dùng ở `runtimePageBuilder.ts:99,103`, `datesRules.ts:39,94`, `moneyFormat.ts:13`. *(F5, F6)*
4. `workflowReconciler.ts:118,254`: thay `isVi` bằng lookup theo `lang` với fallback `en`. *(F8)*
5. `AppTopBar.tsx:74`: switcher phát `/{code}/q/{slug}` khi đang ở route `[locale]`. *(F10)*
6. `routers/v2/quotation_document.py:118-120,154-156`: 422 thay vì ép `None`. *(B2)*


### 1.3 Ranh giới 3 lớp nội dung (Content Tier Boundary)

Đây là **hợp đồng phân loại** mà mọi thành phần của pipeline phải tuân theo. Nguồn phân loại là `quote_document.py` (`QuoteDocument*` models) — mỗi trường chuỗi được gán đúng **một** tier.

| Tier | Định nghĩa | Cơ chế localize | Trường trong `QuoteDocument` (path) | Nguồn hiện tại |
| :-- | :-- | :-- | :-- | :-- |
| **A — Static System Chrome** | Nhãn UI, tiêu đề bảng, nút, kicker cố định, nhãn "Highlights:/Notes:" | Static dictionary compile-time; **không** qua LLM, **không** vào TM | `itinerary.days[].labelHighlights`, `labelNotes`, `pricing.ctaLabel`, `pricing.kicker`, `designer.kicker`, nav labels, `perTraveler`, `daySingular/Plural`, section titles mặc định | `core/i18n.py` (backend), `display/labels.ts` (frontend) |
| **B — Protected Entities** | Dữ kiện thương mại/định danh: tên khách sạn, tên khách, số hiệu chuyến bay, mã quotation, số tiền, tiền tệ, ngày, số phòng, điện thoại, email, tọa độ, asset id | **Không dịch**. Được **mask thành slot** trước khi vào LLM, **unmask** sau; định dạng theo `LocaleProfile.formats`; tên địa danh qua **glossary** (không qua LLM) | `trip.quotationNumber`, `trip.travelDates`, `trip.durationText`, `trip.routeText`*, `traveler.customerName`, `traveler.advisorName/Agency`, `stays.hotels[].name`, `.tel`, `.hotelDate`, `.roomType`*, `route.staySegments[].hotelName`, `.hotelDateRange`, `.daysLabel/nightsLabel`, `itinerary.days[].dayDate`, `.segmentCity`*, `.overnight`*, `.meals[]`*, `pricing.options[].*AmountMinor`, `.currency`, `.label`*, `designer.phone/email`, mọi `QuoteAssetRef`, `destinationRef.*` | Đã có: `is_translatable()` blacklist (legacy), `localize_place_name` glossary, numeric drift guard |
| **C — Dynamic Narrative Copy** | Văn bản do LLM/nhân viên viết, có giá trị biểu đạt | **Segment-level transcreation** qua Localization Agent + TM + human review | `trip.title`, `trip.lede`, `narrative.*` (12 trường thư), `route.title/description`, `route.staySegments[].mapSegmentDesc`, `itinerary.title/description`, `itinerary.days[].title`, `.description[]` (mỗi phần tử = 1 đoạn = 1 segment), `.activities[]`, `.notes[]`, `stays.hotels[].introduction`, `.editorialIntroduction`, `stays.roomNotes`, `pricing.title/description`, `pricing.conditions[].text`, `content.sections[*].blocks[]`, `designer.subtitle/experience/quote/title/ctaBody`, `presentation.copyOverrides[*]` | `QuotationContentDraft` (V2), `STATIC_DICTIONARY` (22 câu dài — **sai tier**, cần dời sang C/TM) |

`*` = **Tier B có glossary**: giá trị lấy từ tập hữu hạn (tên thành phố, loại phòng, bữa ăn `B/L/D`, nhãn option) → dịch bằng bảng tra `glossary`, không qua LLM, không vào TM tự do.

**Quy tắc bất biến:**
- Một trường chỉ thuộc **một** tier. Danh sách trên được mã hóa thành `core/localization/tier_map.py` và có test contract `tests/test_localization_tier_contract.py` đảm bảo **mọi** trường chuỗi trong `QuoteDocument` đều được gán tier (fail nếu thêm trường mới mà quên gán).
- Tier B **không bao giờ** xuất hiện dưới dạng văn bản thô trong prompt localization; chỉ xuất hiện dưới dạng slot.
- Tier A **không bao giờ** đi qua LLM; thiếu khóa ⇒ fallback EN + log warning `i18n.missing_label` (không fail request).

---

## 2. Phân tích trade-off: English Pivot vs Direct Native vs Hybrid

Bối cảnh cố định: **EN là ngôn ngữ khách hàng chủ đạo**; travel designer/consultant làm việc bằng EN và VI; bản EN là nguồn đúng thương mại; `ar` và tương lai `ja/ko/ms` phục vụ thị trường ngách.

### 2.1 Ba kiến trúc ứng viên

```
A. English Master Pivot
   Facts ──► [Content Studio EN] ──► EN master doc ──► [Localization Agent] ──► vi / ar / ja …
                                          ▲ review EN                              ▲ review target

B. Direct Native Generation   (≈ hiện trạng V2 nếu thêm chỉ thị ngôn ngữ)
   Facts ──► [Content Studio, lang=en] ──► EN doc
   Facts ──► [Content Studio, lang=vi] ──► VI doc      (độc lập, không liên kết)
   Facts ──► [Content Studio, lang=ar] ──► AR doc

C. Two-Tier Hybrid
   Facts ──► [Content Studio EN] ──► EN master + Semantic Skeleton (intent/bullets per segment)
                                          └──► [Native Synthesizer(locale)] ──► vi / ar / ja …
```

### 2.2 Ma trận so sánh

| Tiêu chí | A — English Pivot | B — Direct Native | C — Hybrid (EN + skeleton) |
| :-- | :-- | :-- | :-- |
| **Thực tế vận hành & review** | Designer review **1** bản EN (ngôn ngữ họ giỏi). Bản đích chỉ cần reviewer song ngữ đọc so sánh. | Designer phải review **N** bản, mỗi bản là sáng tác độc lập → không thể so sánh với EN → reviewer VI/AR phải tự kiểm tra facts. | Như A. Skeleton giúp reviewer thấy "ý nào bị mất". |
| **Tính đúng thương mại** | EN là SSOT; bản đích **bắt buộc** bảo toàn slot entity + số (kiểm tra máy). | **Không có gì ràng buộc** EN và VI nói cùng một điều; LLM có thể thêm/bớt chi tiết khác nhau giữa các locale. Rủi ro cao nhất. | Như A, cộng skeleton làm ràng buộc ngữ nghĩa thứ hai. |
| **Đồng bộ khi advisor sửa Day 2 EN** | Diff segment EN → chỉ segment Day 2 của mọi locale bị `stale` → re-localize 1 segment, TM hit cho phần còn lại. | Phải regenerate **toàn bộ** Day 2 ở mọi locale từ facts; nếu advisor sửa **văn** (không sửa facts) thì **không có tín hiệu nào** lan sang locale khác. | Như A. |
| **Bảo trì prompt/policy** | **1** stack EN (`brands/`, `modes/`, `ground_rules`, `sections/`) + **1** localization prompt + **N** `LocaleProfile` nhỏ (chỉ cú pháp/định dạng/exemplar). | Phải kiểm định ground rules, brand voice, budgets cho **từng** locale; mỗi thay đổi ground rule ⇒ N lần kiểm định. | Như A + thêm bước sinh skeleton (1 prompt chung). |
| **Ngân sách ký tự / trần PDF** | Tính được: `target_max = f(en_len, LocaleProfile.expansion)`. Agent nhận `max_chars` đích trong prompt; validator kiểm tra. | Budget EN áp cho AR/VI → hoặc 422 (Pydantic `max_length`) hoặc cắt ý. Phải duy trì N bộ budget. | Như A. |
| **Chi phí token** | Per locale: input = EN segment (masked) + facts + profile ≈ 1.3× so với B; output tương đương. **Nhưng** TM hit làm chi phí biên ↓ theo thời gian; chỉ segment stale mới tốn. | Mỗi locale trả full facts prompt (system prompt ~1.5-2k token ground rules); không có TM vì không có "nguồn" ổn định để hash. | A + 1 lần sinh skeleton (nhỏ, có thể gộp vào cùng call với EN draft — xem §3.2). |
| **Độ trễ** | Tuần tự: EN phải **approved** trước khi localize (đúng với quy trình duyệt). Localize các locale chạy **song song** với nhau. | Song song ngay từ đầu, nhưng phải đợi N review. | Như A. |
| **Chất lượng bản ngữ (rủi ro calque)** | **Rủi ro chính** của A: LLM bám cấu trúc câu EN → "mùi dịch máy". Cần cơ chế §3. | Tự nhiên nhất về cú pháp (viết trực tiếp) — nhưng đánh đổi bằng tính đúng. | Skeleton (ý chính dạng bullet, không phải câu) cho phép synthesizer **quên cấu trúc câu EN** trong khi vẫn giữ **ý** — giảm calque mà không mất fidelity. |
| **Mở rộng JA/KO/MS** | Thêm profile + exemplar. | Thêm & kiểm định toàn bộ stack. | Thêm profile + exemplar. |

### 2.3 Kết luận & kiến trúc chọn: **C' = A + Facts-anchored skeleton**

Không sinh skeleton bằng một LLM call riêng (tốn thêm 1 pass và 1 model output cần bảo trì). Thay vào đó:

- **Skeleton = facts snapshot của scope** (đã có sẵn: `content_registry.facts_snapshot(payload, scope)`) + **entity slot table** (§3.1). Đây chính là "ý" mà bản EN được sinh ra từ đó; nó khách quan, deterministic, không cần LLM.
- Localization Agent nhận: `masked_source_text` + `facts_snapshot` + `LocaleProfile` + `budget_target` và được yêu cầu **"viết lại cho người đọc {locale} dựa trên facts; dùng bản EN chỉ để biết giọng và mức độ chi tiết, không bám cấu trúc câu"** (§3.2).
- Nhờ đó, **prompt localization là một**; sự khác biệt giữa locale nằm hoàn toàn trong dữ liệu `LocaleProfile`.

Hệ quả cho hiện trạng:
- `QuotationContentDraft` với `lang != baseline_lang` **không còn được sinh từ facts**. Endpoint `create_content_drafts_v2` với `lang ≠ baseline_lang` chuyển sang gọi `LocalizationService` (§7.2) thay vì `SectionContentGenerator`.
- `SectionContentGenerator` giữ nguyên là **EN-only** (đúng với `BRAND_POLICY_VERSION = "luxury-premium-en-v1"`) — không cần locale hóa prompt stack sinh nội dung.

---

## 3. Kỹ thuật chống dịch word-by-word (Anti-Calque Engineering)

Mục tiêu: LLM có **toàn quyền** tổ chức lại ranh giới mệnh đề, trật tự từ (SOV cho JA/KO, VSO/danh-tính cho AR, phân loại từ cho VI) và thành ngữ, nhưng **không có quyền** chạm vào dữ kiện. Bốn cơ chế dưới đây được xếp theo thứ tự thực thi trong pipeline.

### 3.1 Entity Masking / Slot-Preserving Extraction (deterministic, trước LLM)

**Module:** `core/localization/entity_guard.py` (pure, không I/O, test được như `core/rules/*`).

```
EN source (Tier C)                                Masked source + slot table
──────────────────────────────────────────        ─────────────────────────────────────────────────
"Check in to Six Senses Ninh Van Bay on           "Check in to {{E:HOTEL_1}} on {{E:DATE_1}}, where
14 Mar 2027, where a private villa awaits.        a private villa awaits. Your day ends with a
Your day ends with a **Halong Bay** sunset        **{{E:PLACE_1}}** sunset cruise (USD 1,250 per
cruise (USD 1,250 per person)."                   person → {{E:MONEY_1}})."

                                                  slots:
                                                    HOTEL_1 : {kind: hotel, value: "Six Senses Ninh Van Bay", source_path: "stays.hotels[2].name"}
                                                    DATE_1  : {kind: date,  value: "2027-03-14", render: LocaleProfile.formats.date}
                                                    PLACE_1 : {kind: place, value: "Halong Bay", glossary_key: "quang-ninh"}
                                                    MONEY_1 : {kind: money, minor: 125000, currency: "USD", per: "person"}
```

**Nguồn slot (theo thứ tự ưu tiên, deterministic):**
1. **Facts-anchored** — giá trị Tier B lấy từ `facts_snapshot` của scope (tên khách sạn từ `accommodation_facts`, ngày từ `trip_facts`, tiền từ `pricing`) → so khớp exact/normalized trong EN text. Đây là nguồn chính; không cần NER.
2. **Glossary** — tên địa danh từ `core/localization/glossary/places.yaml` (nâng cấp từ `localize_place_name` + 13 khóa địa danh trong `STATIC_DICTIONARY`), mã sân bay/chuyến bay (`^[A-Z]{2}\d{2,4}$`), hạng phòng.
3. **Regex guard** — ISO date, số + đơn vị (`\d+(?:[.,]\d+)?\s?(USD|VND|km|m|°C)`), giờ (`\d{1,2}:\d{2}`), email, phone, mã `QT-/VS-`. Kế thừa `is_translatable()` của legacy.

**Cú pháp slot:** `{{E:<KIND>_<n>}}`. Kind ∈ `HOTEL|PLACE|PERSON|DATE|TIME|MONEY|NUM|CODE|CONTACT|BRAND`. Trong prompt có chỉ thị: "Slot là **danh từ**; bạn được phép thêm tiểu từ/hậu tố ngữ pháp bên ngoài dấu ngoặc (ví dụ JA: `{{E:HOTEL_1}}にて`, VI: `tại {{E:HOTEL_1}}`), không được sửa bên trong."

**Unmask + Validation (`SlotIntegrityValidator`):**

| Kiểm tra | Hành động khi fail |
| :-- | :-- |
| Tập slot output == tập slot input (mỗi slot xuất hiện **đúng 1 lần**) | retry 1 lần với thông báo lỗi cụ thể → nếu vẫn fail: giữ EN source, status `needs_review`, `warning: slot_integrity` |
| Không có chuỗi Tier B thô rò rỉ (ví dụ LLM viết lại tên khách sạn dù đã mask) — kiểm tra bằng tập giá trị gốc + normalized | như trên |
| Số ngoài slot (nếu còn) khớp tập `numeric_tokens` của EN (kế thừa `_extract_numeric_tokens`, chuẩn hóa chữ số Ả Rập-Ấn/Đông Ả Rập, chữ số toàn-độ-rộng CJK) | như trên |
| Không HTML/markdown ngoài `**…**` quanh slot PLACE (ground rule bold highlight) | strip + warning |
| `len(target) ≤ budget_target` (§6.2) | retry với chỉ thị rút gọn; fail → `needs_review`, `warning: over_budget` |

Sau unmask, slot được **render theo `LocaleProfile.formats`** (ngày `14/03/2027` VI, `١٤ مارس ٢٠٢٧` hoặc `14 مارس 2027` tùy `numerals`, tiền `1.250 USD` vs `USD 1,250`). Việc render slot là deterministic ⇒ **không bao giờ** có drift số giữa locale.

### 3.2 Semantic Re-expression Prompting (cấu trúc prompt)

**Vị trí:** `prompts/v1/tools/translation.yaml` được thay bằng `prompts/v1/localization/agent.yaml` (nạp qua `PromptLoader.get_localization_config()` — hàm mới) + `prompts/v1/locales/{locale}.yaml`. Prompt là YAML data; **không** inline string trong Python (đúng quy ước repo).

Cấu trúc system prompt (được `PromptLoader.build_localization_bundle()` lắp ráp):

```yaml
# prompts/v1/localization/agent.yaml
role: "native {locale.name} luxury travel copywriter who re-expresses meaning, never translates sentences"
procedure:            # thứ tự bắt buộc — đây là cơ chế chống calque chính
  - "Read INPUT FACTS first. They are the only truth."
  - "Read the ENGLISH REFERENCE only to learn: which facts are mentioned, in what order of emphasis, and the register."
  - "Discard the English sentence structure entirely. Do not preserve clause order, punctuation rhythm, or English idioms."
  - "Write the passage as a native {locale.name} copywriter would for a {locale.reader_profile}, applying {locale.syntax_directives}."
  - "Every {{E:...}} slot must appear exactly once, unchanged inside the braces. Add grammatical particles outside the braces only."
  - "Stay within {budget.max_chars} characters. Prefer omitting an ornament over exceeding the budget."
output_schema: { intent_notes: "list[str] — 2-5 bullet points, the meaning you extracted (discarded after validation)",
                 target_text: "str" }
constraints_ref: system_base.constraints      # tái dùng: no invented hotels/services/prices
```

Ba điểm kỹ thuật:
- **`intent_notes` là trường schema có chủ đích.** Model phải "trích ý" trước khi "viết" — đây là chain-of-thought nhẹ được ép qua structured output (`pydantic_ai` `output_type=LocalizedSegmentOutput`), không tốn 1 call riêng. Trường này **bị bỏ** sau validation, chỉ log vào `generation_metadata.intentNotes` để reviewer đọc.
- **Facts đứng trước EN reference** trong user prompt: `INPUT FACTS (JSON)` → `ENTITY SLOTS` → `ENGLISH REFERENCE (masked)` → `TARGET BUDGET`. Thứ tự này làm suy yếu attention vào chuỗi EN.
- **Brand/mode tone không nhân bản theo locale:** system prompt chèn nguyên `brands/{brand}.yaml.tone` + `modes/{mode}.yaml.style_rules` (bằng tiếng Anh) như mô tả *về* giọng; `LocaleProfile.register` chỉ bổ sung cách thể hiện giọng đó trong ngôn ngữ đích (ví dụ VI: "xưng hô *Quý khách*, tránh *bạn*"; JA: "敬体 です・ます, tránh 尊敬語 quá mức").

### 3.3 Few-shot Calque-Prevention Exemplars (dữ liệu, theo locale)

Mỗi `LocaleProfile` mang 3–6 cặp exemplar **cấu trúc**, không phải văn mẫu marketing. Định dạng:

```yaml
# prompts/v1/locales/vi.yaml (trích)
calque_exemplars:
  - pattern: "english_passive_with_agent"
    source: "Your afternoon is spent exploring {{E:PLACE_1}} with a private guide."
    rejected: "Buổi chiều của bạn được dành để khám phá {{E:PLACE_1}} với một hướng dẫn viên riêng."   # calque: bị động + sở hữu 'của bạn'
    accepted: "Buổi chiều, hướng dẫn viên riêng đưa Quý khách khám phá {{E:PLACE_1}}."
    why: "VI prefers active voice, topic-first; drop possessive 'your'; honorific 'Quý khách'."
  - pattern: "english_nominal_chain"
    source: "A {{E:HOTEL_1}} sunset cocktail experience awaits."
    rejected: "Một trải nghiệm cocktail hoàng hôn {{E:HOTEL_1}} đang chờ đợi."
    accepted: "Hoàng hôn buông, ly cocktail tại {{E:HOTEL_1}} đã sẵn sàng đón Quý khách."
    why: "Break nominal chain into clause; VI cannot stack noun modifiers."
```

Exemplar được chọn **theo scope**: `hero` dùng 2 exemplar ngắn, `itinerary_day` dùng 4. Bộ exemplar có test snapshot (`tests/test_locale_profiles_contract.py`) đảm bảo mọi exemplar giữ đúng slot và không vượt budget của scope tương ứng — exemplar sai còn tệ hơn không có.

### 3.4 Two-Pass Drafting: có cần pass "Native Polish" không?

**Kết luận: có, nhưng có điều kiện — không áp dụng mặc định.**

| Trường hợp | Pass 2 (polish/reflection) | Lý do |
| :-- | :-- | :-- |
| TM exact hit (`approved`) | **Không** | Đã có người duyệt. |
| Scope `hero`, `overview_letter` (khách đọc đầu tiên, PDF trang 1-2) | **Có** — reflection pass với rubric | Chi phí nhỏ (2 scope × ~300 token), giá trị cảm nhận cao nhất. |
| `itinerary_day.*`, `hotel.introduction` | **Chỉ khi** `CalqueJudge.score < 0.7` | Judge rẻ hơn polish; polish có thể làm mất fidelity nếu áp bừa. |
| Tier A/B | **Không** | Không qua LLM. |

**`CalqueJudge`** (cùng model, `output_type=CalqueVerdict{calque_score: float, fidelity_ok: bool, issues: list[str]}`): chấm target text (đã unmask? **không** — chấm bản còn slot để judge không bị tên riêng làm nhiễu) trên 3 tiêu chí: bám cấu trúc EN, tự nhiên bản ngữ, đúng register. Ngưỡng cấu hình trong `LocaleProfile.quality.calque_threshold`. Điểm được lưu `generation_metadata.calqueScore` → hiển thị trong review UI (§5) để reviewer ưu tiên.

**Polish pass** nhận: target text (slot) + `intent_notes` + `issues` từ judge; **không** nhận lại EN source (tránh kéo về calque). Validator §3.1 chạy lại sau polish.

Kiến trúc này giữ tổng số LLM call cho một quotation 12 ngày ở mức: `1 (batch EN đã có) + ~30 segment localize (song song, batch theo scope) + 2 polish + ≤30 judge` — và **giảm về 0** cho các segment đã có trong TM.

---

## 4. Translation Memory & Segment Store

### 4.1 Lựa chọn kho lưu trữ: PostgreSQL 16 JSONB (không MongoDB/Redis)

Căn cứ:
- `docker-compose.local.yml` chỉ có `postgres:16`; không có Redis/Mongo trong stack, requirements, hay Docker network. Thêm một datastore mới = thêm một Alembic tree/health check/backup và vi phạm nguyên tắc "platform-native trước".
- Yêu cầu truy vấn của TM: (1) exact match theo hash — B-tree; (2) fuzzy match theo văn bản nguồn — `pg_trgm` GIN; (3) lọc theo `(brand_id, scope_family, target_locale, status)` — composite index; (4) versioning append-only. Postgres đáp ứng cả 4 mà không cần cache tầng ngoài: exact-hit lookup < 1 ms trên vài trăm nghìn dòng.
- TM **phải** nằm cùng transaction với `QuotationContentDraft`/`QuotationDocument` khi apply (đảm bảo "approved" trong TM ⇔ đã apply vào doc) — Mongo/Redis không cho phép điều này.
- Redis chỉ cân nhắc ở Phase 4 làm read-through cache nếu đo được p95 lookup > 20 ms — hiện không có bằng chứng.

### 4.2 Phân đoạn (Segmentation)

**Đơn vị segment = 1 giá trị chuỗi Tier C tại 1 `document path`**, với hai ngoại lệ tách nhỏ hơn:
- `itinerary.days[i].description[]` là `List[str]` — **mỗi phần tử (đoạn văn) là 1 segment** (ground rule đã chia Morning/Afternoon thành 2 đoạn).
- `content.sections[*].blocks[]` — mỗi block là 1 segment.

Không tách segment ở mức câu: câu là đơn vị của dịch máy thống kê; transcreation cần cả đoạn để tổ chức lại ý.

**`scope_family`** (dùng cho hash và fuzzy search, tách khỏi path cụ thể để tăng tỷ lệ tái sử dụng giữa các quotation):

| scope_family | Path pattern | Tái sử dụng liên-quotation |
| :-- | :-- | :-- |
| `hero.title`, `hero.lede` | `trip.title`, `trip.lede` | Thấp (đặc thù chuyến) |
| `letter.*` | `narrative.letter*` | Trung bình (greeting/signoff cao) |
| `route.summary` | `route.description` | Thấp |
| `route.segment` | `route.staySegments[].mapSegmentDesc` | **Cao** (mô tả chặng theo cặp thành phố) |
| `day.title`, `day.paragraph`, `day.activity` | `itinerary.days[].title/description[]/activities[]` | **Cao** (tour ngày lặp lại: "Halong Bay cruise day", "Hanoi Old Quarter walk") |
| `hotel.intro`, `hotel.editorial` | `stays.hotels[].introduction/editorialIntroduction` | **Rất cao** (khách sạn cố định) |
| `policy.clause` | `pricing.conditions[].text`, `content.sections.terms.*` | **Rất cao** (điều khoản chuẩn) |
| `designer.*` | `designer.quote/ctaBody/…` | Rất cao (theo designer) |
| `chrome.longform` | 22 câu dài đang nằm sai chỗ trong `STATIC_DICTIONARY` | Rất cao — **di trú vào TM với status `approved`** ở Phase 2 |

### 4.3 Khóa hash & matching

```python
segment_key_hash = sha256(
    "|".join([
        TM_SCHEMA_VERSION,              # "tm1" — đổi khi normalize/mask thay đổi
        source_locale,                  # "en"
        scope_family,                   # "day.paragraph"
        brand_id,                       # tone khác nhau ⇒ bản dịch khác nhau
        generation_mode,                # "storytelling" | "detailed"
        normalize(masked_source_text),  # NFC, collapse whitespace, strip trailing punct, casefold KHÔNG áp dụng (giữ hoa/thường)
    ])
).hexdigest()
```

- **Hash trên văn bản đã mask**: "Check in to {{E:HOTEL_1}} on {{E:DATE_1}}" trùng nhau giữa mọi quotation dù khách sạn/ngày khác ⇒ tỷ lệ exact-hit cao hơn nhiều so với hash văn bản thô. Slot được điền lại theo facts của quotation hiện tại lúc unmask.
- **Không đưa `quotation_id`, `facts_hash`, `revision` vào hash** — chúng là thuộc tính của *usage*, không phải của *segment*.
- **Fuzzy:** `similarity(source_text_norm, :q) > LocaleProfile.tm.fuzzy_threshold` (mặc định 0.85) trong cùng `(scope_family, brand_id, target_locale, status='approved')`, dùng `pg_trgm` GIN index. Fuzzy hit **không** auto-apply: được đưa vào prompt như *reference translation* ("một bản dịch đã duyệt cho đoạn tương tự") và đánh dấu `match_kind = "fuzzy"` trong review UI. Đây là cách TM dạy giọng đã duyệt cho LLM mà không bỏ qua review.
- Embedding/`pgvector` **không** đưa vào phạm vi: trigram trên văn bản masked cùng scope_family đủ cho mục tiêu tái sử dụng tour lặp lại; sẽ đánh giá lại khi TM > 200k segment.

### 4.4 Schema

Hai bảng trong DB `quotation` (cùng Alembic tree `alembic/`), model tại `db/models/translation_memory.py`, repository `repositories/translation_memory_repository.py` (chỉ query, lỗi typed trong `repositories/errors.py`).

```sql
-- Danh tính segment: 1 dòng cho mỗi (segment_key_hash, target_locale). Trạng thái = phiên bản hiện hành.
CREATE TABLE translation_memory_segments (
  id                 TEXT PRIMARY KEY,                   -- "tm_" + 20 hex
  segment_key_hash   CHAR(64) NOT NULL,
  scope_family       VARCHAR(64) NOT NULL,
  brand_id           VARCHAR(64) NOT NULL,
  generation_mode    VARCHAR(32) NOT NULL,
  source_locale      VARCHAR(5)  NOT NULL DEFAULT 'en',
  target_locale      VARCHAR(5)  NOT NULL,
  source_text_masked TEXT NOT NULL,                      -- văn bản EN đã mask (để hiển thị & fuzzy)
  source_text_norm   TEXT NOT NULL,                      -- normalize() của trên (pg_trgm)
  current_version    INTEGER NOT NULL DEFAULT 1,
  status             VARCHAR(24) NOT NULL,               -- generated | needs_review | approved | rejected | stale | published
  usage_count        INTEGER NOT NULL DEFAULT 0,
  last_used_at       TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_tm_segment_identity UNIQUE (segment_key_hash, target_locale)
);
CREATE INDEX ix_tm_segments_lookup ON translation_memory_segments (target_locale, brand_id, scope_family, status);
CREATE INDEX ix_tm_segments_source_trgm ON translation_memory_segments USING gin (source_text_norm gin_trgm_ops);

-- Lịch sử append-only. Mỗi generate / override / approve tạo 1 version mới. Không UPDATE target_text.
CREATE TABLE translation_memory_segment_versions (
  id                 TEXT PRIMARY KEY,
  segment_id         TEXT NOT NULL REFERENCES translation_memory_segments(id) ON DELETE CASCADE,
  version            INTEGER NOT NULL,
  target_text_masked TEXT NOT NULL,                      -- vẫn còn slot; unmask lúc apply
  slot_table         JSONB NOT NULL,                     -- {HOTEL_1: {kind, source_path}, …} — KHÔNG chứa giá trị (giá trị đến từ facts lúc apply)
  origin             VARCHAR(24) NOT NULL,               -- llm | llm_polished | human_override | imported | migrated_dictionary
  status             VARCHAR(24) NOT NULL,               -- như trên, tại thời điểm version
  quality            JSONB NOT NULL DEFAULT '{}',        -- {calqueScore, judgeIssues[], overBudget: bool, slotIntegrity: "ok"}
  provenance         JSONB NOT NULL DEFAULT '{}',        -- {quotationId, sourceDocumentRevision, promptVersion, model, latencyMs, intentNotes[]}
  approved_by        TEXT,                               -- profile id
  approved_at        TIMESTAMPTZ,
  created_by         TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_tm_segment_version UNIQUE (segment_id, version)
);
```

Ánh xạ với document schema người dùng yêu cầu: `{segment_hash, scope, source_locale, source_text, target_locale, target_text, version, approved_by, status, usage_count, created_at, updated_at}` = join của 2 bảng trên; API trả về đúng hình này (`TranslationMemorySegmentView` trong `routers/v2/schemas/localization.py`).

**Liên kết với document:** `QuotationDocument.document_json.meta.localization` (mở rộng `QuoteDocumentMeta`, backward-compatible, default rỗng):

```json
"meta": {
  "lang": "vi",
  "localization": {
    "sourceLang": "en",
    "sourceRevision": 14,
    "profileVersion": "vi@2026-09",
    "segments": {
      "itinerary.days[1].description[0]": { "segmentId": "tm_…", "version": 3, "status": "approved", "sourceSegmentHash": "…", "matchKind": "exact" },
      "trip.lede": { "segmentId": "tm_…", "version": 1, "status": "needs_review", "sourceSegmentHash": "…", "matchKind": "generated" }
    }
  }
}
```

`sourceSegmentHash` là hash của **EN masked text tại thời điểm localize** — dùng để phát hiện stale (§5.4) mà không cần diff toàn doc.

### 4.5 Vòng đời cache & tái sử dụng

```
localize(segment, locale):
  hash = segment_key_hash(...)
  hit = tm.find_exact(hash, locale)
  ├─ hit.status == approved|published  → apply hit.current_version; usage_count += 1; matchKind="exact"; KHÔNG gọi LLM
  ├─ hit.status == needs_review|generated → tái dùng version hiện hành, giữ status (không sinh lại để tránh reviewer phải duyệt 2 bản)
  ├─ hit.status == rejected            → sinh mới (LLM) + đính kèm lý do reject vào prompt như constraint
  └─ miss:
       refs = tm.find_fuzzy(source_text_norm, scope_family, brand, locale, status=approved, limit=2)
       out  = LocalizationAgent(masked, facts, profile, budget, refs)      # §3.2
       validate (§3.1) → judge/polish (§3.4) → tm.create(segment, version=1, status=needs_review)
```

- **0% drift:** exact-hit không đi qua LLM, và slot được render từ facts hiện tại ⇒ giá/ngày/tên luôn đúng của quotation này dù văn được duyệt từ quotation khác.
- **Kiểm soát nổ TM:** `hero.*`, `route.summary` (đặc thù chuyến) vẫn ghi TM nhưng `usage_count` sẽ ≈ 1; job dọn `tm_prune` (Phase 4) xóa version `rejected`/`generated` > 180 ngày không dùng; **không bao giờ** xóa `approved`.
- **Di trú dictionary:** 22 câu dài + các đoạn narrative trong `display/labels.ts` (`termDepositBody`, `journeyTogetherTagline`, …) được import với `origin = migrated_dictionary`, `status = approved`, `approved_by = "migration"` → ngay ngày đầu TM đã có lõi điều khoản/greeting đã duyệt.

---

## 5. Human-in-the-Loop Review Workflow (Content Studio)

### 5.1 Vị trí trong workspace

Workspace hiện ép locale về `workflow.locale` (= `baseline_lang`) và redirect nếu khác (`app/workspace/quotations/[quotationId]/edit/page.tsx:23-31`, được khóa bởi `tests/test_v2_workspace_locale_contract.py`). Giữ nguyên hợp đồng này cho các stage `facts | content | design | review`; thêm **stage mới `localize`** với tham số `target`:

```
/workspace/quotations/{id}/edit?stage=localize&lang=en&target=vi
                                               ▲ vẫn là baseline   ▲ locale đích
```

Lý do: stage `localize` **không sửa doc EN**; nó đọc EN (chỉ đọc) và ghi doc `vi`. Do đó không vi phạm "workspace luôn ở baseline locale". Đây là cách duy nhất để không phải phá contract test hiện có.

Điều kiện vào stage: EN doc `review-status.ready == true` **hoặc** ít nhất các scope được chọn đã `applied` (cho phép localize sớm từng phần, nhưng UI cảnh báo "EN chưa duyệt xong — bản dịch có thể stale").

### 5.2 Side-by-Side Dual Pane

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ Localize → Tiếng Việt      EN rev 14 · VI derived from rev 12  ⚠ 3 stale · 9 to review │
├───────────────────────────────┬──────────────────────────────────────────────────────┤
│ Scope: itinerary.days[1]      │  status ● needs_review   match: generated   calque 0.82 │
│ ─────────────────────────────│──────────────────────────────────────────────────────│
│ [EN · read-only]              │ [VI · editable]                                      │
│ Day title                     │ Tiêu đề ngày                                          │
│  Immersive Hanoi Old Quarter  │  Hà Nội phố cổ – một ngày đậm chất                    │
│ Paragraph 1  (segment)        │ Đoạn 1                                     312/420 ch │
│  Your morning begins at       │  Sáng sớm, {{E:PLACE_1}} …                            │
│  {{E:PLACE_1}} …              │   ▸ slots: PLACE_1 = Temple of Literature (Văn Miếu) │
│ Paragraph 2  (segment)  STALE │ Đoạn 2                          ⚠ EN changed in rev 13│
│  ▲ diff vs rev 12 shown       │  [Re-localize] [Keep & mark reviewed]                 │
├───────────────────────────────┴──────────────────────────────────────────────────────┤
│ intent notes (from model): • buổi sáng Văn Miếu  • trưa tự do  • chiều xích lô 36 phố  │
│ [Approve segment] [Approve scope] [Reject + reason ▾]  [Regenerate with note…]         │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

Hành vi kỹ thuật:
- **Đồng bộ field-level:** hai pane cùng cuộn theo `document path`; click một segment EN highlight segment VI tương ứng (`data-segment-path`). Dữ liệu từ 1 endpoint (§7.3 `GET …/localizations/{target}`) trả cặp `{path, source: {text, hash, revision}, target: {text, status, version, matchKind, quality}}`.
- **Editor bên phải là `EditableText` hiện có** của Content Studio (không tạo editor mới); slot hiển thị dạng chip không sửa được (`contenteditable=false`), người dùng chỉ sửa văn quanh chip. Chip hiển thị giá trị đã render theo locale nhưng lưu lại dạng `{{E:…}}`.
- **Budget meter** dùng `contentBudgets.json` × `LocaleProfile.expansion` (§6.2) — meter đỏ khi vượt ceiling đích, chặn approve.
- **Tier A/B không xuất hiện** trong pane (không có gì để review); tier B hiển thị dưới dạng chip trong ngữ cảnh.
- Trình tự ưu tiên hiển thị: `stale` → `needs_review` (sắp xếp calqueScore tăng dần) → `approved`.

### 5.3 Vòng đời trạng thái

```
                 LLM / TM miss                  reviewer                     publish (lang=vi)
   (none) ──────────────────► generated ──► needs_review ──► approved ──────────────► published
                                   │              │  ▲            │
                                   │   auto-judge │  │ override   │ EN segment hash changed
                                   ▼              ▼  │            ▼
                                needs_review   rejected ──► (regen w/ reason)    stale ──► needs_review (re-localize)
                                                                                    └──► approved (reviewer "keep")
```

| Trạng thái | Ai/cái gì đặt | Ý nghĩa | Điều kiện rời |
| :-- | :-- | :-- | :-- |
| `generated` | LocalizationService, ngay sau validate §3.1 | Bản máy, chưa qua judge | judge chạy xong ⇒ `needs_review` (luôn; judge chỉ sắp ưu tiên, không auto-approve) |
| `needs_review` | hệ thống | Chờ người song ngữ | approve / reject / override |
| `approved` | reviewer (`profile.role ∈ {editor, reviewer}` + `LocaleProfile.reviewers` cho phép) | Được dùng cho quotation này **và** trở thành TM exact-hit cho quotation khác | EN đổi ⇒ `stale`; hoặc publish ⇒ `published` |
| `published` | `publish_canonical_quotation_v2(lang=vi)` | Đã ra release | EN đổi ⇒ `stale` (release cũ vẫn giữ frozen snapshot) |
| `rejected` | reviewer + lý do bắt buộc | Không dùng; lý do được đưa vào prompt regen | regen ⇒ version mới `generated` |
| `stale` | `LocalizationImpactAnalyzer` (§5.4) | EN nguồn đã đổi sau khi dịch | reviewer chọn re-localize hoặc keep |

**Gate publish theo locale:** `_canonical_review_status(quotation_id, lang="vi")` thêm blocker `LOCALIZATION_PENDING` nếu tồn tại segment `needs_review|stale|generated` trong `meta.localization.segments`. Blocker theo đúng envelope `REVIEW_BLOCKED` (422, `recovery: "open-blockers"`), deep-link tới `stage=localize&target=vi&path=…` — tái dùng cơ chế `reviewBlockersDeepLink` hiện có ở frontend.

### 5.4 In-place Override & Stale detection

**Override:** `PATCH /api/v2/quotations/{id}/localizations/{target}/segments` body `{path, targetTextMasked, baseRevision, baseSegmentVersion}`:
1. Validate slot integrity (§3.1) và budget đích → 422 `VALIDATION_FAILED` với `fieldErrors[].path`.
2. Tạo `translation_memory_segment_versions` mới `origin=human_override, status=approved, approved_by=principal` trong **cùng transaction** với `save_current_document(lang=vi, expected_revision=baseRevision)` + `append_document_revision(change_source="localization_override")`.
3. Xung đột revision ⇒ 409 `REVISION_CONFLICT` (`recovery: "reload"`) — đúng contract hiện có.
4. Ghi outbox `quotation.localization.segment_approved` (payload: quotationId, target, path, segmentId, version, approvedBy) qua `services/outbox_service.py`.

**Stale:** Hook vào `QuotationDocumentRepository.append_document_revision` **cho `lang == baseline_lang`**: sau khi ghi revision EN mới, `LocalizationImpactAnalyzer.analyze(quotation_id, old_doc, new_doc)`:
- Chạy `EntityGuard.mask()` + `segment_key_hash` cho mọi path Tier C của cả hai bản → tập `changed_paths` (hash khác) + `removed_paths` + `added_paths`.
- Với mỗi locale đích có doc: cập nhật `meta.localization.segments[path].status = "stale"` (chỉ những path đổi), `meta.localization.sourceRevision` giữ nguyên (chỉ tăng khi re-localize/keep toàn bộ).
- Ghi outbox `quotation.localization.stale` (payload: quotationId, sourceRevision, targets[], changedPaths[]) → notification service hiển thị cho reviewer; **không** email trực tiếp (Outbox contract).
- Đây là cùng mẫu với `QuotationVersionImpact` (facts → content) nhưng ở trục **EN text → target text**; không trộn vào bảng impact hiện có vì đơn vị (segment path) và người xử lý (reviewer song ngữ) khác nhau.

**Facts đổi (không đổi văn EN):** vì slot render từ facts hiện tại lúc build view model, đổi tên khách sạn/ngày/giá **không** làm segment stale — bản dịch vẫn đúng. Chỉ khi facts đổi kéo theo regen EN (impact hiện có) thì EN hash đổi ⇒ stale. Đây là lợi ích trực tiếp của mask-before-hash.

---

## 6. Pluggable Scalability Framework (JA / KO / MS)

### 6.1 `LocaleProfile` schema — `prompts/v1/locales/{locale}.yaml`

Đặt trong `prompts/v1/` để cùng versioning với prompt stack và được `PromptLoader` nạp/validate bằng Pydantic (`core/localization/locale_profile.py: LocaleProfile`). Là **SSOT** cho cả backend lẫn frontend (xuất sang `quote-generator/config/locales.json` bằng `scripts/export_locale_profiles.py`, kiểm tra đồng bộ trong `tests/test_ssot_integrity.py` giống `content_budgets`).

```yaml
# prompts/v1/locales/ja.yaml
code: "ja"                      # BCP-47 ngắn; là giá trị lưu vào cột lang/locale (String(5))
name: "Japanese"
native_name: "日本語"
status: "beta"                  # draft | beta | ga  — chỉ ga/beta mới xuất hiện trong LANGUAGE_CODES runtime
intl_tag: "ja-JP"               # tag duy nhất dùng cho Intl.* (chấm dứt tình trạng 'ar' vs 'ar-SA')

script:
  direction: "ltr"              # ltr | rtl  → <html dir>, [dir] CSS
  family: "cjk"                 # latin | arabic | cjk | hangul
  font_roles:                   # map sang khóa font đã đăng ký trong config/typography.ts FONT_REGISTRY
    heading: "notoSerifJp"
    body: "notoSansJp"
    accent: "notoSerifJp"
    signature: "buongiornoRastellino"   # không có glyph CJK → fallback cursive, chấp nhận
  letter_spacing: "normal"      # Arabic block hiện dùng letter-spacing: normal !important — tổng quát hóa
  line_height_scale: 1.15       # CJK cần leading lớn hơn Latin

expansion:                      # so với EN baseline = 1.00 — GIÁ TRỊ KHỞI ĐIỂM, phải hiệu chỉnh bằng PDF preflight thật (§6.2)
  char_ratio: 0.55              # số ký tự (code point) trung bình / cùng nội dung
  glyph_width_factor: 1.75      # độ rộng render trung bình / glyph Latin (full-width CJK)
  # target_max_chars = floor(en_max_chars × char_ratio × safety) ; line_budget = en_ceiling / (char_ratio × glyph_width_factor)

formats:
  numerals: "latn"              # latn | arab (Arabic-Indic ٠١٢) | arabext — quyết định render slot NUM/MONEY/DATE
  date: { pattern: "yyyy年M月d日", range_separator: "〜" }
  time: { pattern: "H:mm" }
  money: { pattern: "{currency}{amount}", grouping: ",", decimal: ".", currency_display: "code" }   # USD 1,250 → USD1,250 ; VND → ¥ không đổi tiền
  duration: { days_nights: "{days}日{nights}泊" }
  list_joiner: "、"

register:                       # bổ sung cho brand tone (không thay thế)
  reader_profile: "affluent Japanese leisure traveller, 40-65, travelling as couple or family"
  honorific: "お客様"
  politeness: "です・ます体; avoid 尊敬語 stacking; no ！"
  taboo: ["直訳調", "カタカナ英語の多用"]

syntax_directives:              # đưa thẳng vào prompt §3.2
  - "Japanese is SOV: place the verb at the end; do not mirror English SVO clause order."
  - "Prefer topic-comment structure (は) over English subject-led sentences."
  - "Drop explicit subjects/pronouns ('you', 'your') — implied by context."
  - "Attractions in bold slots keep original name + reading if well known (e.g. {{E:PLACE_1}}（ハロン湾）)."

calque_exemplars: [...]         # ≥3, định dạng §3.3

glossary_refs: ["places", "meals", "room_types", "hotel_categories"]   # core/localization/glossary/*.yaml, mỗi file có khóa ja

quality:
  calque_threshold: 0.7
  polish_scopes: ["hero.*", "letter.*"]
  fuzzy_threshold: 0.85

reviewers:                      # profile ids hoặc role được phép approve locale này; rỗng = bất kỳ editor
  roles: ["reviewer_ja"]

chrome_labels: "core/i18n/ja.json"          # Tier A backend
frontend_labels: "quote-generator/locales/ja.json"   # Tier A frontend (70 khóa display + 6 pricing + 4 topbar)
```

Validation ở load-time (fail-fast, `tests/test_locale_profiles_contract.py`):
- `code` đúng regex `^[a-z]{2,3}(-[A-Z]{2})?$` và ≤ 5 ký tự (khớp `String(5)`).
- Mọi `font_roles.*` phải tồn tại trong `FONT_REGISTRY` của `config/typography.ts` (đọc qua `config/locales.json` export ngược — hoặc đơn giản: script export fail nếu key lạ).
- `chrome_labels`/`frontend_labels` phải có đủ khóa (so với `en`); thiếu ⇒ test fail, không phải runtime fallback im lặng.
- Mọi exemplar giữ slot và trong budget scope.

### 6.2 Budget theo locale — không nhân bản `content_budgets.yaml`

`content_budgets.yaml` **giữ nguyên là EN SSOT**. Budget đích được **tính**, không được khai báo:

```python
# core/rules/content_budgets.py (mở rộng, backward-compatible)
def get_max_chars_for_locale(self, scope, field, profile: LocaleProfile) -> int:
    en = self.get_max_chars(scope, field)
    return math.floor(en * profile.expansion.char_ratio * SAFETY)          # SAFETY = 0.95
def get_pdf_ceiling_for_locale(self, scope, field, profile) -> int:
    en = self.get_pdf_ceiling(scope, field)
    return math.floor(en * profile.expansion.char_ratio)                    # trần vật lý: giữ số DÒNG ~ bằng EN
```

- Frontend: `lib/rules/contentReconciler.ts: validatePdfTextBudget(text, fieldId, lang)` nhân với `locales.json[lang].expansion.char_ratio` thay vì dùng `.length` thô. Đếm bằng `Intl.Segmenter(intl_tag, {granularity:'grapheme'})` thay vì UTF-16 length (VI có dấu tổ hợp, AR có tashkeel).
- **Hiệu chuẩn:** `scripts/calibrate_locale_expansion.py` render 20 segment mẫu/locale bằng route PDF hiện có (`/[locale]/q/[slug]/pdf`), đo số dòng thực qua Playwright `getClientRects()`, xuất `char_ratio`/`glyph_width_factor` đo được vào profile. Giá trị trong YAML luôn kèm `calibrated_at` và `sample_size`.
- Giá trị khởi điểm đề xuất (phải hiệu chuẩn, không phải sự thật): `vi` char_ratio 1.20, glyph 1.00; `ar` 1.15, glyph 1.05 (chữ Ả Rập hẹp hơn nhưng cần leading); `ja` 0.55, glyph 1.75; `ko` 0.70, glyph 1.60; `ms` 1.15, glyph 1.00.

### 6.3 Các điểm cắm (plug points) cần chuyển từ hardcode sang data — làm **một lần** ở Phase 4

| Hiện tại (hardcode) | Sau Phase 4 (data-driven) |
| :-- | :-- |
| `main.py:5255 _resolve_v2_locale` `{"en","vi","ar"}` + 11 chỗ literal khác | `LocaleRegistry.enabled_codes()` (đọc profiles `status ∈ {beta, ga}`); 1 helper `core/localization/registry.py`; contract test cấm literal `("en", "vi", "ar")` trong `main.py`/`routers/` |
| `display/contracts.ts LANGUAGE_CODES`, `proxy.ts:22` regex, `next.config.ts:12` header source, `runtimePageBuilder.ts:539-545` languageOptions, `MinimalQuotationIntakeForm.tsx:168` | Sinh từ `config/locales.json` (`LANGUAGE_CODES = Object.keys(locales)`), regex build từ cùng mảng; `lint:locale-literals` chặn literal mới |
| `app/layout.tsx:44 <html lang="en">` + script đọc `?lang=` | `app/[locale]/layout.tsx` set `lang={locale}` `dir={profile.script.direction}` từ route segment (server-side, không script) |
| `config/typography.ts buildArabicBlock()` | `buildLocaleBlocks(locales)` sinh `[lang="xx"]`/`[dir="rtl"]` block từ `font_roles`, `letter_spacing`, `line_height_scale` của **mọi** profile |
| `app/fonts.ts` 6 font | Thêm font entry theo `font_roles` — đây là **1 dòng code** không tránh được (Next font phải khai báo tĩnh); tải **có điều kiện** theo locale route để không tăng bundle cho EN |
| `runtimePageBuilder.ts:99-108`, `datesRules.ts:39,94`, `moneyFormat.ts:13` | Một module `lib/locale/format.ts` đọc `locales.json[lang].intl_tag/formats` |
| `main.py:660-726 format_*`, `skeleton_builder.py:26-46` | `core/localization/formatters.py` đọc `LocaleProfile.formats` |
| `core/i18n.py STATIC_DICTIONARY` (khóa = câu EN) | `core/i18n/{locale}.json` với **khóa symbolic** (`section.journey_glance.title`), loader `core/i18n/__init__.py: t(key, locale)`; migration script sinh `en.json/vi.json/ar.json` từ dict hiện tại + đổi các call site Jinja `{{ "Timeline" \| translate(lang) }}` → `{{ t("section.timeline") }}` (legacy templates) |
| `display/labels.ts` (70 khóa × 3) + `routeState.ts:134` (4 × 3) + ternary trong `contentReconciler.ts:189-353`, `workflowReconciler.ts:118,254` | `quote-generator/locales/{locale}.json` (1 file/locale, ~80 khóa), `getLanguageLabels(lang)` đọc JSON; ternary `lang === 'vi' ? … : …` bị `lint:locale-literals` cấm |
| `globals.css` 85 thuộc tính vật lý left/right | Chuyển sang logical (`margin-inline-start`, `inset-inline-end`, `text-align: start`) — cần cho `ar` **ngay bây giờ**, không chỉ cho ngôn ngữ mới |

### 6.4 Quy trình thêm Japanese (`ja`) — sau Phase 4

| Bước | Việc | Chạm core render loop? |
| :-- | :-- | :-- |
| 1 | Tạo `prompts/v1/locales/ja.yaml` (schema §6.1) với 3+ exemplar, `status: draft` | Không |
| 2 | Tạo `core/i18n/ja.json` và `quote-generator/locales/ja.json` (copy `en.json`, dịch ~330 + ~80 khóa; có thể seed bằng LocalizationAgent với `scope_family = chrome.label` rồi review) | Không |
| 3 | Thêm khóa glossary `ja` vào `core/localization/glossary/{places,meals,room_types}.yaml` | Không |
| 4 | Thêm 2 entry `Noto_Serif_JP`, `Noto_Sans_JP` vào `app/fonts.ts` + `FONT_REGISTRY` (`config/typography.ts`) — 2 khai báo tĩnh | Chỉ registry, không render loop |
| 5 | `python scripts/export_locale_profiles.py && cd quote-generator && npm run sync:locales` → cập nhật `config/locales.json`, `LANGUAGE_CODES`, proxy regex, header source | Sinh mã, không sửa tay |
| 6 | `python scripts/calibrate_locale_expansion.py --locale ja` → ghi `expansion` đo được | Không |
| 7 | Chạy contract: `PYTHONPATH=. pytest tests/test_locale_profiles_contract.py tests/test_ssot_integrity.py tests/test_v2_api_manifest_contract.py`; `npm run lint && npm test` | — |
| 8 | Đổi `status: beta` → locale xuất hiện trong intake `options.languages` và trong stage `localize`; migrate: **không cần Alembic** (`String(5)` chứa `ja`; không có CHECK constraint theo triple — và **không thêm** CHECK để tránh migration mỗi lần thêm locale) | Không |
| 9 | Seed TM: chạy localize cho 3–5 quotation mẫu, reviewer JA duyệt → `policy.clause`, `hotel.intro`, `designer.*` được approved và tái dùng | Không |
| 10 | `status: ga` | Không |

Tổng: **3 file mới + 2 dòng font + 3 file glossary**, không sửa `main.py`, `routers/`, `display/runtimePageBuilder.ts`, `components/display/**`.

`ko`: như trên với `font_roles` Noto Sans/Serif KR, `honorific: "고객님"`, SOV directives, `list_joiner: ", "`. `ms`: Latin script, `char_ratio ≈ 1.15`, không cần font mới, `register` phân biệt `Anda` (formal) — chỉ 2 file + glossary.

---

## 7. Đặc tả hệ thống hợp nhất & Kế hoạch hành động

### 7.1 Data contract: `QuotationDocumentRevision` ↔ `QuotationContentDraft` ↔ TM

```
quotations (baseline_lang = "en")
  │
  ├─ quotation_documents (quotation_id, lang="en")  ◄── MASTER. Facts PUT, Content Studio EN, autosave ghi vào đây.
  │     └─ quotation_document_revisions (lang="en", revision n)  ◄── append-only; revision EN là "sourceRevision" của mọi locale
  │
  ├─ quotation_documents (quotation_id, lang="vi")  ◄── DERIVED. Chỉ LocalizationService & override ghi vào.
  │     ├─ document_json.meta.localization { sourceLang, sourceRevision, segments{path → tmRef,status,sourceSegmentHash} }
  │     └─ quotation_document_revisions (lang="vi", revision m, change_source ∈ {localize, localization_override, localization_keep})
  │
  ├─ quotation_content_drafts (lang="vi", scope, candidate_json)  ◄── GIỮ NGUYÊN làm "candidate" cho stage localize:
  │       generation_mode = "localize"; prompt_version = fingerprint(profileVersion, tmSchema, sourceSegmentHashes…)
  │       generation_metadata.localization = { sourceRevision, segments[{path, segmentId, version, matchKind, calqueScore}] }
  │       status: draft → applied (apply = ghi doc vi + TM status approved trong 1 transaction) | discarded
  │
  └─ translation_memory_segments ⟷ translation_memory_segment_versions   ◄── liên-quotation, không FK tới quotation
```

Bất biến:
1. `documents(lang≠baseline).document_json` **không bao giờ** chứa Tier B khác với doc EN cùng `sourceRevision`; `LocalizationService.apply()` copy nguyên khối Tier B từ EN doc rồi chỉ ghi đè Tier C. Facts PUT (chỉ ghi EN) vì thế không cần lan sang doc locale khác — **sửa defect** "doc `vi` giữ facts cũ" (§1.1).
2. `sourceRevision` của doc `vi` ≤ `documents(en).revision`; bằng nhau ⇔ không có segment stale.
3. Publish `lang=vi` chỉ được phép khi `sourceRevision == en.revision` **hoặc** mọi segment stale đã được reviewer "keep". Release `vi` ghi thêm `source_base_revision` (cột đã có trong `PublicationRelease`) = EN revision.
4. `QuotationDocumentRevision` không đổi schema. Chỉ thêm giá trị `change_source` mới.

### 7.2 Kiến trúc service

```
routers/v2/localization.py  (mới; _get_helpers() import main — theo pattern repo)
   │  parse/auth/envelope only
   ▼
services/localization_service.py  ── LocalizationService
   ├─ plan(quotation_id, target, scopes, base_revision)         → SegmentPlan[]   (paths Tier C, EN hash, TM lookup kết quả)
   ├─ localize(plan) → LocalizationCandidate (draft `generation_mode="localize"`)
   │     ├─ core/localization/entity_guard.py      EntityGuard.mask()/unmask()/validate()    (pure)
   │     ├─ core/localization/segmenter.py         segment(document) → [Segment{path, scope_family, text}] (pure, dùng tier_map)
   │     ├─ core/localization/locale_profile.py    LocaleProfile, LocaleRegistry              (pure, YAML→Pydantic)
   │     ├─ core/rules/content_budgets.py          get_max_chars_for_locale()                 (pure)
   │     ├─ services/translation_memory_manager.py TranslationMemoryManager.find_exact/find_fuzzy/record/approve
   │     │       └─ repositories/translation_memory_repository.py (query only)
   │     └─ services/localization_agent.py         LocalizationAgent (pydantic_ai Agent, output_type=LocalizedSegmentOutput)
   │             ├─ prompts/loader.py build_localization_bundle(profile, scope_family, masked, facts, budget, refs)
   │             ├─ CalqueJudge (Agent, output_type=CalqueVerdict)
   │             └─ llm_client.get_model()   ← duy nhất nơi tạo provider (giữ nguyên)
   ├─ apply(candidate, base_revision)  → save doc(lang=target) + TM approve + revision + outbox   (1 transaction)
   ├─ override(path, text, …)          → §5.4
   └─ analyze_impact(quotation_id, old_en, new_en) → stale marks + outbox    (gọi từ append_document_revision khi lang==baseline)

services/outbox_service.py  ← events: quotation.localization.{generated,needs_review,segment_approved,stale,applied}
notification/                ← không đổi; thêm 5 event_type vào taxonomy `notification/AGENTS.md` §3
```

Ranh giới:
- `core/localization/*` **không I/O, không session** (giống `core/rules/*`), test thuần.
- `SectionContentGenerator` **không** bị sửa; `create_content_drafts_v2` với `lang ≠ baseline_lang` được router chuyển sang `LocalizationService.localize` (1 nhánh if trong router, không trong service).
- Display layer (`components/display/**`) **không** biết TM; chỉ nhận `viewModel` với văn đã unmask + `lang` + `dir`.

### 7.3 API surface mới (đăng ký trong `tests/test_v2_api_manifest_contract.py`)

| Method | Path | Body / Query | Envelope |
| :-- | :-- | :-- | :-- |
| `POST` | `/api/v2/quotations/{id}/localizations/{target}/plan` | `{scopes?: string[], baseRevision}` | 200 `SegmentPlan[]`; 409 `REVISION_CONFLICT` |
| `POST` | `/api/v2/quotations/{id}/localizations/{target}/generate` | `{scopes?, baseRevision, instruction?}` | 200 draft (`generation_mode="localize"`); 422 `VALIDATION_FAILED` (slot/budget) |
| `GET` | `/api/v2/quotations/{id}/localizations/{target}` | — | 200 side-by-side payload §5.2 |
| `PATCH` | `/api/v2/quotations/{id}/localizations/{target}/segments` | `{path, targetTextMasked, baseRevision, baseSegmentVersion}` | 200; 409; 422 |
| `POST` | `/api/v2/quotations/{id}/localizations/{target}/segments/approve` | `{paths[], baseRevision}` | 200 |
| `POST` | `/api/v2/quotations/{id}/localizations/{target}/segments/reject` | `{path, reason, baseRevision}` | 200 |
| `POST` | `/api/v2/quotations/{id}/localizations/{target}/apply` | `{draftId, baseRevision}` | 200; 409 |
| `GET` | `/api/v2/translation-memory/segments` | `?q=&targetLocale=&scopeFamily=&brandId=&status=&cursor=` | 200 (paginated `TranslationMemorySegmentView`) |
| `GET` | `/api/v2/locales` | — | 200 `[{code, name, nativeName, direction, status}]` (thay cho `options.languages` hardcode) |

`review-status?lang={target}` mở rộng thêm `localization: {sourceRevision, pending, stale}`; không đổi shape hiện có.

### 7.4 Lộ trình

| Phase | Phạm vi & Deliverables | Gate |
| :-- | :-- | :-- |
| **1 — Audit & Spec** (tài liệu này) | Chốt tier map, kiến trúc C', schema TM, LocaleProfile. Deliverable code: `core/localization/tier_map.py` + `tests/test_localization_tier_contract.py` (mọi trường chuỗi `QuoteDocument` có tier) | Test tier contract xanh; 2 bug-fix nhanh tách riêng: (a) `<html lang/dir>` từ route segment (`app/[locale]/layout.tsx`), (b) `main.py:9515` bỏ `lang="en"` mặc định + thêm vào guard list |
| **2 — TM Store & English-Pivot Relay** | Alembic `translation_memory_*` (+ `CREATE EXTENSION pg_trgm`); `EntityGuard`, `Segmenter`, `LocaleProfile` (en/vi/ar); `prompts/v1/localization/agent.yaml`, `locales/{vi,ar}.yaml`; `LocalizationAgent` + judge; `LocalizationService.plan/localize/apply`; router + manifest; di trú 22 câu dài + `termDepositBody`… vào TM `approved`; `create_content_drafts_v2(lang≠baseline)` reroute | Tests: `test_entity_guard.py` (slot integrity, numerals arab/latn/fullwidth), `test_segmenter.py`, `test_translation_memory_repository.py` (exact/fuzzy), `test_localization_service.py` (TM hit ⇒ `llmCalled=False`), manifest + envelope contracts. E2E: 1 quotation `vi` publish với 0 LLM call ở lần thứ hai |
| **3 — Content Studio Side-by-Side** | Stage `localize`; dual pane; slot chips; budget meter theo locale; approve/reject/override; `LocalizationImpactAnalyzer` + stale + outbox events + notification taxonomy; publish gate `LOCALIZATION_PENDING` | `npm run lint` (typography/display-system/colors) xanh; `lib/__tests__/localizationReconciler.test.ts` (pure: stale merge, budget meter); Playwright: dual pane 1024/1440, RTL `ar` pane với `dir` đúng; `test_v2_workspace_locale_contract.py` không đổi |
| **4 — Pluggable Locale Profiles** | Mọi điểm cắm §6.3: `LocaleRegistry`, `config/locales.json` + `sync:locales`, `buildLocaleBlocks`, `core/i18n/{locale}.json` khóa symbolic, `quote-generator/locales/*.json`, `lib/locale/format.ts`, logical CSS, `lint:locale-literals`, `calibrate_locale_expansion.py`; thêm `ja` theo §6.4 làm bằng chứng | Thêm `ja` **không** có diff trong `main.py`, `routers/`, `display/runtimePageBuilder.ts`, `components/display/**` (kiểm tra bằng `git diff --stat` trong PR) |

### 7.5 Rủi ro & quyết định mở

| Rủi ro | Giảm thiểu |
| :-- | :-- |
| LLM sửa nội dung trong slot / bỏ slot | Validator §3.1 + retry 1 lần + fallback `needs_review`; đo tỷ lệ `slot_integrity_fail` theo model, đưa vào `generation_metadata` |
| Bản duyệt TM từ quotation A dùng cho B có ngữ cảnh khác (cùng EN masked nhưng ý khác) | Hash gồm `scope_family + brand + mode`; TM hit hiển thị `matchKind=exact` với nguồn quotation trong review UI; reviewer có thể "detach" (override tạo version mới không ảnh hưởng A) |
| Expansion ratio sai ⇒ tràn PDF | Trần vật lý là preflight PDF hiện có (đếm dòng thực), budget locale chỉ là lớp cảnh báo sớm; hiệu chuẩn bằng đo |
| `pg_trgm` cần extension trên Postgres production | Alembic `CREATE EXTENSION IF NOT EXISTS pg_trgm`; kiểm tra quyền superuser/`azure_pg_admin` trước Phase 2 |
| Phase 4 đổi khóa `STATIC_DICTIONARY` sang symbolic ảnh hưởng legacy Jinja templates (10 template, hàng trăm call `\| translate`) | Giữ `translate_filter` như adapter đọc `en.json` đảo ngược (EN text → key) trong 1 release; xóa sau khi legacy path retire |
| Reviewer song ngữ cho `ar/ja/ko` không có nội bộ | `LocaleProfile.reviewers.roles` cho phép gán đối tác ngoài với quyền chỉ ở stage `localize` (không sửa EN/facts) |

**Quyết định mở (cần chủ sở hữu sản phẩm):**
1. Có cho phép publish locale khi còn segment `needs_review` (soft gate + banner "machine-translated") cho thị trường thử nghiệm không? Đề xuất: **không** cho `ga`, **có** cho `beta` với watermark trong `footerText`.
2. Model cho LocalizationAgent: cùng `llm_client.get_model()` hay provider chuyên dịch? Đề xuất: giữ 1 provider ở Phase 2, đo `calqueScore` phân phối trước khi tách.
