# Audit Implementation — Track 4: Ingestion Platform & AI Service Drafter Defect Log

> Adversarial audit 2026-09-03. Anchor specs: `15.8-text-to-catalog-ingestion.md`, `15.8b-corpus-and-seeding-runbook.md`, `15.7-ai-service-drafter.md`, master `15-modular-tour-ops-brainstorm.md`. Mọi finding dưới đây đã được trace tận gốc trong source và (với parser/corpus) tái hiện bằng probe chạy thật — không suy đoán.

## 1. Subsystem Scope & Verified Call-Graph Perimeter

**Anchor entrypoints scanned end-to-end:**

- AI Platform Layer: `services/ai_platform/{runtime,deps,guardrails,runs}.py`, `services/ai_platform/toolsets/catalog.py`, `db/models/ai_run.py`, `llm_client.py` (provider construction duy nhất), installed `pydantic_ai` 2.16.0 (semantics thực thi tool).
- Ingestion: `services/ingestion/{extraction_service,resolution_service,commit_service}.py`, `core/rules/{ingest_sanitizer,ingest_parser}.py`, `schemas/catalog_ingest.py`, `db/models/ingestion.py`, `repositories/ingestion_repository.py`, `routers/v2/ingestion.py`, migration `20260907_45_ingestion_platform.py`.
- Drafter: `services/ai_drafter/{trip_analyst,service_drafter,draft_run_service}.py`, `schemas/{trip_profile,service_draft}.py`, `routers/v2/ai_drafter.py`, migration `20260908_46_costing_service_line_ai_meta.py`.
- Traced outward: `repositories/{supplier,product,rate,destination,costing}_repository.py`, `services/{supplier,product,rate,costing,outbox}_service.py`, `core/rules/rate_selection.py`, `services/facts…` (không bị đụng), `api/dependencies.py`, `main.py` exception handlers (`_v2_error_payload`, `http_exception_handler` — HTTPException từ router ingestion VẪN đi qua envelope), seeding `scripts/seed_catalog_via_ingestion.py`, corpus `tests/fixtures/ingestion_corpus/` + `tests/test_ingestion_corpus.py`.

**Automated test baseline (default `PYTHONPATH=. pytest` trên 10 suite Track 4):**

- `test_ai_drafter_api`, `test_ai_platform_guardrails`, `test_ai_platform_toolset`, `test_ingest_commit`, `test_ingest_parser`, `test_ingest_resolution`, `test_ingest_sanitizer`, `test_ingestion_api`, `test_ingestion_architecture_boundary`: **104 passed**.
- `test_ingestion_corpus`: **8/8 FAILED** — harness chết vì API drift (xem H10), và các test này (real-LLM) chạy cả trong default invocation vì mark `integration` không được đăng ký/deselect (xem M12).
- Frozen contracts: `test_v2_api_manifest_contract` + `test_v2_error_envelope` + `test_ssot_integrity`: **9 passed** — manifest đã pin đủ 7 route ingestion + 3 route ai-drafter.

**Kết luận kiến trúc giữ vững (verified, không cần re-chase):** zero-money schema của drafter (introspection test + không tool nào trả amount); rate resolution 100% server-side (`_resolve_price_serverside` chỉ đọc DB + pure `rate_selection`, bỏ qua mọi hint của LLM); allowlist fail-closed và check TRƯỚC existence-check; raw prose chỉ tới 2 agent 0-tool (Extractor, TripAnalyst); `services/ai_platform/` không bị 15.7 sửa (chỉ `toolsets/catalog.py` được nối thêm — extension point hợp lệ); prompts 100% YAML `prompts/v1/`; migration 45/46 thuận nghịch, constraint khớp model; tenant_id luôn từ deps, không bao giờ là tham số LLM.

---

## 2. Defect Log (BẮT BUỘC trước khi nghiệm thu)

### §4.1 — CRITICAL

#### C1 🔴 CRITICAL — Currency misdetection: alias `"d"` nuốt `"usd"` → tiền USD commit thành VND
- **Vị trí**: `core/rules/ingest_parser.py::_detect_currency` (~dòng 24–66, đặc biệt vòng lặp substring 63–66 và alias `"d"` dòng 28).
- **Cơ chế lỗi**: sau khi exact-match thất bại, hàm quét substring theo insertion order của `_CURRENCY_ALIASES`, trong đó `"d"` (alias VND) đứng TRƯỚC `"usd"`. Bất kỳ `amount_text` chứa chữ `d` mà không có `currency_text` exact → trả về `VND`. **Đã tái hiện thật**: `parse_amount_text("500 USD net")` → `minor_units=500, currency='VND', ambiguous=False`; `parse_amount_text("150 usd/pax")` → 150 VND; `_detect_currency("120 dollars", None)` → VND. Giá trị này chảy thẳng vào `parsed` tree → `commit_service._price_lines_for` → `RatePriceLineCreateSchema(amount_minor=...)` → bảng rates thật. Một tariff $500 thành 500 đồng.
- **Kịch bản kích hoạt**: Extractor emit `amount_text="500 USD net"`, `currency_text=None` (hoặc `"US Dollar"`, `"usd/pax"` — mọi thứ không exact-match) — cực kỳ phổ biến với tariff tiếng Anh.
- **Fix**: trong `_detect_currency` (pure rule, không đổi schema): (1) bỏ alias 1 ký tự `"d"` khỏi vòng substring (chỉ cho phép exact-match với `"d"`/`"đ"`), (2) quét substring theo alias DÀI trước (sort by `len` desc), (3) dùng word-boundary regex thay vì `in`.
- **Test bắt buộc**: parametrize `("500 USD net", USD)`, `("150 usd/pax", USD)`, `("1.200.000 đ", VND)`, `("35 eur", EUR)`, `("120 dollars", ambiguous hoặc USD)`; thêm property test: mọi text chứa `usd` không bao giờ ra VND.

#### C2 🔴 CRITICAL — `parse_amount_text` chộp SỐ ĐẦU TIÊN trong text → "2 pax: 500.000 VND" thành 2 VND
- **Vị trí**: `core/rules/ingest_parser.py::parse_amount_text` (~dòng 126–135, `_NUMERIC_RE.search`).
- **Cơ chế lỗi**: `_NUMERIC_RE.search` lấy nhóm số đầu tiên bất kể vị trí so với currency token. **Đã tái hiện**: `parse_amount_text("2 pax: 500.000 VND")` → `minor_units=2, currency='VND', ambiguous=False`. Không ambiguous → không có clarification → operator chỉ thấy sai nếu tự soi parsed tree → commit ghi rate 2 VND vào catalog. Đây chính là dạng trap `trap_ambiguous_price_01.txt` của corpus 15.8b, nhưng corpus gate đang chết (H10) nên không ai chặn.
- **Kịch bản kích hoạt**: LLM emit `amount_text` kèm ngữ cảnh đứng trước con số tiền ("2 pax: …", "1 x 500.000", "từ 01/05: 350.000") — parser lấy 2 / 1 / 1 làm amount.
- **Fix** (pure rule): khi text có ≥2 numeric group, chọn group liền kề currency token (trước/sau alias) hoặc group lớn nhất-có-separator; nếu vẫn nhiều ứng viên → `ambiguous=True, reason="multiple numeric groups"`. Tuyệt đối không đổi schema.
- **Test bắt buộc**: `("2 pax: 500.000 VND") → 500_000 VND` hoặc ambiguous (không bao giờ 2); `("1 x 500.000 đ") → 500_000` hoặc ambiguous; case một số duy nhất giữ nguyên hành vi cũ.

#### C3 🔴 CRITICAL — pydantic_ai 2.16 chạy tool SONG SONG trên MỘT AsyncSession chia sẻ → crash / session poisoning
- **Vị trí**: `services/ai_platform/deps.py:24–45` (một `session` cho mọi tool), `services/ai_platform/toolsets/catalog.py` (mọi tool query `ctx.deps.session`), `services/ai_platform/runtime.py::build_agent:62–70` (không set sequential), `services/ai_drafter/draft_run_service.py:193`, `services/ingestion/resolution_service.py:96`.
- **Cơ chế lỗi**: pydantic_ai 2.16 mặc định thực thi nhiều tool call trong cùng một model turn bằng `asyncio.create_task` song song (`pydantic_ai/_tool_execution.py:649–670`); không tool nào được đăng ký `sequential=True`. SQLAlchemy `AsyncSession` cấm concurrent ops → hai `repository.list()` đồng thời → `InvalidRequestError`/greenlet error. Tệ hơn: session này là CHÍNH session request sẽ dùng để ghi `service_lines`/`ai_runs` sau đó — exception giữa chừng có thể làm transaction bất khả dụng cho phần còn lại của run.
- **Kịch bản kích hoạt**: drafter prompt khuyến khích tìm accommodation + transport + activities cho một ngày; DeepSeek/GPT thường emit 2–4 tool call trong một message → ngày đó fail (`days_failed`) hoặc 500. Resolver (toolset B, 24 calls) cùng rủi ro.
- **Fix**: trong `build_agent` ép chế độ thực thi tool tuần tự (per-tool `sequential=True` khi đăng ký, hoặc run-scoped sequential mode); hoặc gắn `asyncio.Lock` vào `CatalogReadOnlyDeps` bao quanh mọi truy cập session. Không đổi schema.
- **Test bắt buộc**: fake model trả MỘT response chứa 2 tool call (`search_accommodations` + `search_transport`) chạy trên `AsyncSession` SQLite thật; assert cả hai hoàn thành không `InvalidRequestError` và budget đếm đúng 2.

### §4.2 — HIGH

#### H1 🟠 HIGH — Row lock costing sheet + transaction DB mở xuyên suốt chuỗi LLM call (nhiều phút)
- **Vị trí**: `services/ai_drafter/draft_run_service.py::run_draft` (~207–312), commit duy nhất tại `routers/v2/ai_drafter.py:117`; nguồn lock `repositories/costing_repository.py:141–151` (`_bump_revision_guarded` giữ row lock tới commit).
- **Cơ chế lỗi**: `run_draft` lặp từng ngày tuần tự trong MỘT session/transaction. Sau `create_line` đầu tiên của ngày 1, guarded UPDATE lên `costing_sheets` giữ Postgres row lock; lock này bị giữ trong khi các ngày sau `await agent.run(...)` (timeout 120s/attempt × retries=2 × số ngày). Draft 5 ngày có thể giữ lock hàng chục phút; connection pool cũng bị chiếm idle-in-transaction.
- **Kịch bản kích hoạt**: Sale A bấm Draft; Sale B sửa bất kỳ line nào trên cùng sheet → UPDATE của B TREO (không phải 409) đến khi run của A commit. Vài draft đồng thời → cạn pool.
- **Fix**: tách transaction theo ngày (commit sau mỗi ngày, mang `current_revision` đi tiếp — run đã resumable nhờ per-line idempotency key), hoặc chạy TOÀN BỘ LLM call xong mới resolve+persist một lượt để không lock nào bắc qua network call; bọc `agent.run` bằng `asyncio.wait_for`.
- **Test bắt buộc**: mock `draft_day` sleep; từ session thứ hai `create_line` cùng sheet — assert không bị block theo thời lượng run / không có UPDATE sheet-row nào flush trước khi mọi LLM call kết thúc.

#### H2 🟠 HIGH — `RunBudget(max_calls=len(days)+2)` đếm TOOL call thay vì agent call → ngày sau bị bỏ đói, "succeeded" giả
- **Vị trí**: `services/ai_drafter/draft_run_service.py:192`; tiêu thụ tại `services/ai_platform/toolsets/catalog.py:143,179,216,286`; notice cạn budget `catalog.py:23–31,285`.
- **Cơ chế lỗi**: spec 15.7 "trần RunBudget = số ngày + 2 calls" ngụ ý agent(LLM)-call; implementation tái dùng `RunBudget.max_calls` mà guardrails định nghĩa và mọi tool tiêu thụ như TOOL-call ceiling. Prompt lại yêu cầu mỗi ngày 3–4 tool call → draft 5 ngày có 7 call: ngày 1–2 tiêu hết, ngày 3–5 chỉ nhận `_budget_exhausted_notice` → agent không thấy `product_id` nào → mọi đề xuất rớt allowlist → ngày trống, `manual_review_count` tăng, run vẫn `status="succeeded"`. Suy giảm HOÀN TOÀN im lặng.
- **Kịch bản kích hoạt**: bất kỳ draft ≥2–3 ngày với model thật.
- **Fix**: `RunBudget` riêng mỗi ngày (vd 8 tool call/ngày, gộp stats về run-level), giữ trần run-level chỉ để thống kê. Không đổi schema.
- **Test bắt buộc**: fake agent 4 tool call/ngày × 3 ngày → assert không ngày nào nhận exhausted-notice, mọi ngày có candidates.

#### H3 🟠 HIGH — Va chạm idempotency-key CHÉO AGENT (analyst ↔ drafter) → 500 thay vì lỗi có chủ đích
- **Vị trí**: `services/ai_drafter/draft_run_service.py::find_existing_run` (~53–62, KHÔNG lọc `agent_name` — đã verify bằng grep: `agent_name` chỉ xuất hiện tại dòng 94 khi ghi); unique constraint agent-agnostic `db/models/ai_run.py:22–26`; guard một chiều tại `routers/v2/ai_drafter.py:65`.
- **Cơ chế lỗi**: (a) Draft với key đã dùng cho Analyze cùng sheet → `find_existing_run` trả run `trip_analyst` → `DraftResponseSchema.model_validate` trên output analyst → thiếu `status`/`days_done` → pydantic ValidationError → 500. (b) Chiều ngược: Analyze với key đã thuộc draft run → lọt qua check `agent_name == "trip_analyst"` ở router → chạy LLM → `record_run` vỡ `uq_ai_runs_anchor_idempotency_key` → IntegrityError → 500.
- **Kịch bản kích hoạt**: client dùng "một key cho một phiên draft" (pattern ngây thơ hợp lý) gọi lần lượt hai endpoint.
- **Fix**: thêm filter `AiRun.agent_name == AGENT_NAME` vào `find_existing_run` (tham số keyword, không đổi schema/constraint); cross-agent hit → 422 "idempotency key already used by another operation"; race trên constraint trong `record_run` → re-read và replay thay vì 500.
- **Test bắt buộc**: cùng sheet + cùng key: analyze rồi draft, và ngược lại → deterministic 422/409 envelope, không bao giờ 500/IntegrityError.

#### H4 🟠 HIGH — Commit action `update` cho supplier XÓA TRẮNG `contact_json` của supplier đang tồn tại
- **Vị trí**: `services/ingestion/commit_service.py::_resolve_or_create_supplier` (~96–99): `SupplierUpdateSchema(contact_json=SupplierContactSchema())`.
- **Cơ chế lỗi**: `contact_json` được SET tường minh thành contact RỖNG → `model_dump(exclude_unset=True)` giữ lại field → `SupplierService.update_supplier` (dòng 89–106) overwrite `contact_json` thật của supplier bằng object rỗng. Đồng thời KHÔNG một dữ liệu ingest nào (`contact_text`, `destination_text`, `type_hint`) được ghi — "update" duy nhất phá hủy contact hiện có. Mọi batch mà operator chọn `update_existing` ở câu hỏi dedupe đều kích hoạt.
- **Kịch bản kích hoạt**: paste tariff của supplier đã có trong catalog → resolver hỏi dedupe → operator trả lời `update_existing` → commit → contact supplier bay sạch.
- **Fix**: bỏ hẳn `contact_json` khỏi payload update (chỉ `SupplierUpdateSchema()` no-op, hoặc map `payload.supplier.contact_text` vào notes nếu muốn thêm dữ liệu). Không đổi schema.
- **Test bắt buộc**: supplier có contact_json đầy đủ; commit batch action=update → assert contact_json GIỮ NGUYÊN.

#### H5 🟠 HIGH — Ngày "hợp lệ lịch giả" (31/02) vượt qua validator rồi nổ `date.fromisoformat` → 500 ở cả create lẫn commit
- **Vị trí**: `core/rules/ingest_parser.py::_is_valid_calendar` (~206–211: chỉ check `1 ≤ day ≤ 31`, không check theo tháng); nổ tại `services/ingestion/resolution_service.py:318–319` và `services/ingestion/commit_service.py:218–219`.
- **Cơ chế lỗi**: **đã tái hiện**: `parse_validity_text("31/02/2025 - 15/03/2025")` → `date_range, date_from='2025-02-31', ambiguous=False`. `_verify_rate_entry`/`_commit_rate_group` gọi `date.fromisoformat` → `ValueError: day is out of range for month` — KHÔNG được catch (chỉ ExtractionError/ResolutionError/CommitError được map) → 500. Ở create route lỗi xảy ra SAU khi đã trả tiền LLM cho Extractor + Resolver và rollback cả batch.
- **Kịch bản kích hoạt**: tariff gõ nhầm "31/04", "30/02", "31/6" — lỗi người thật gõ rất thường gặp.
- **Fix** (pure rule): `_is_valid_calendar` dùng `calendar.monthrange`/`datetime.date` thử-nghiệm (với năm nếu có; không năm thì cho phép 29/02) → invalid ⇒ `ambiguous=True` thành clarification, không crash.
- **Test bắt buộc**: `parse_validity_text("31/02/2025 - 15/03/2025")` → ambiguous; API-level: create batch chứa validity đó → 201 + clarification, không 500.

#### H6 🟠 HIGH — Edit/Reject KHÔNG chặn trạng thái terminal → sửa batch đã committed, mở đường COMMIT LẶP ghi trùng rate
- **Vị trí**: `routers/v2/ingestion.py::edit_ingestion_batch` (~190–221) và `reject_ingestion_batch` (~252–276) — không có guard `_TERMINAL_STATUSES` (đối chiếu: `answer_clarifications` có, `resolution_service.py:504`); kết hợp `commit_service.py:272` cho phép commit từ `needs_clarification`.
- **Cơ chế lỗi**: batch `committed` vẫn nhận PUT /edits: payload_json bị ghi đè, và nếu reparse sinh `unresolved` thì `status` lật về `needs_clarification` — trạng thái COMMITTABLE. POST /commit lần hai replay toàn bộ resolution entries cũ: supplier/product có dedupe đỡ được một phần (nhưng đỡ bằng CONFLICT-500, xem M4), còn rate action `create` chạy `create_draft`+`activate` LẦN NỮA → rate trùng/chồng validity trong catalog thật. Reject-sau-commit cũng dán nhãn `rejected` lên batch đã ghi catalog mà không undo gì — trạng thái nói dối.
- **Kịch bản kích hoạt**: operator lỡ tay edit một batch committed (UI không chặn thì API càng không) → answer/ack → commit lại.
- **Fix**: thêm guard terminal-status (`committed|rejected|archived`) vào cả hai route (409/422), và siết `commit_batch` chỉ nhận `ready`/`draft` đúng spec §1.7 dòng 121 ("commit chỉ từ `ready` (hoặc `draft` không blocking)").
- **Test bắt buộc**: batch committed → PUT /edits → 409; POST /reject → 409; batch `needs_clarification` có blocking → commit → 422 (đã có) và batch committed → commit → trả idempotent, KHÔNG ghi catalog lần hai (spy trên RateService).

#### H7 🟠 HIGH — "Read-only theo cấu tạo" là giả: `CatalogReadOnlyDeps` lộ nguyên repository ghi + session ghi sống
- **Vị trí**: `services/ai_platform/deps.py:24–45`; claim tại docstring `deps.py:6–9`; structural test một-tầng `tests/test_ai_platform_toolset.py::test_deps_has_no_write_method`.
- **Cơ chế lỗi**: các property trả FULL repository (`supplier_repository.create/update/delete`, `rate_repository.replace_lines`, …) và `deps.session` là chính request `AsyncSession` (`.commit()`, `.execute()` tùy ý). Test cấu trúc chỉ soi `dir(deps)` một tầng nên xanh trong khi `deps.product_repository.delete(...)` cách đúng một attribute-hop. Spec P2 đòi "read-only theo cấu tạo, không theo quy ước" — hiện là quy ước. Một tool tương lai (hoặc bug trong tool) có toàn quyền ghi trên transaction request.
- **Kịch bản kích hoạt**: tool toolset-A/B mới thêm sau này gọi nhầm method ghi — không gì chặn, commit chung với request.
- **Fix**: bọc repository bằng facade chỉ expose đúng các query method tool dùng; đổi `session` thành private/loại khỏi deps; mở rộng structural test đi sâu một tầng attribute.
- **Test bắt buộc**: assert đệ quy 1 tầng: mọi public attr của deps và của object nó trả ra không có `create/update/delete/commit/add/flush/execute`.

#### H8 🟠 HIGH — Run thất bại → KHÔNG có bản ghi `ai_runs`, mất luôn line đã tạo; catch per-day quá hẹp
- **Vị trí**: drafter: `services/ai_drafter/draft_run_service.py:217` (try chỉ bọc `draft_day`; `get_by_id:228`, `_resolve_price_serverside:233` — `KeyError/ValueError` từ `supplements_json` dị dạng tại 138–146 — và lỗi non-Costing từ `create_line` đều thoát), run record chỉ ghi ở 323 SAU vòng lặp; ingestion: `extraction_service.py:54–56` (ExtractionError → 502, không record_run failed), `resolution_service.py:106–107` (tương tự).
- **Cơ chế lỗi**: exception giữa chừng → 500/502, session rollback → line các ngày đã xong BAY (spec P4: "giữ phần đã xong") và `ai_runs` KHÔNG có dòng nào (spec P3: mọi run được log — sai đúng với những run cần soi nhất; token đã đốt nhưng `tokens_in=0` hoặc không log). Retry cùng key chạy lại từ đầu, trả tiền LLM lần nữa.
- **Kịch bản kích hoạt**: CAS conflict ngày 3/5 do sale sửa sheet tab khác; hoặc một rate có `supplements_json` thiếu `applies_from` → 500, không dấu vết.
- **Fix**: mở rộng try per-day bọc cả resolve+persist (ngày lỗi → `days_failed`, đi tiếp); top-level except ghi run `failed/partial` bằng SESSION NGẮN RIÊNG (sống sót rollback domain) rồi re-raise; parse supplements/blackout qua helper khoan dung (flag thay vì raise). Extraction/Resolution lỗi cũng record_run `failed` trước khi map 502.
- **Test bắt buộc**: (a) `create_line` raise conflict ngày 2/3 → tồn tại `ai_runs` row `failed/partial` sau 409; (b) `supplements_json` thiếu key → run hoàn tất, line bị flag, không 500; (c) ExtractionError → có run `failed`.

#### H9 🟠 HIGH — Không có trần token/input ở drafter: `raw_text` analyze KHÔNG giới hạn độ dài (spec P4 "trần call/token cứng" chưa enforce)
- **Vị trí**: `schemas/v2/ai_drafter.py::AnalyzeRequestSchema.raw_text` (~34, chỉ `min_length=1`); `services/ai_platform/guardrails.py:29–66` (`RunBudget` tự nhận "not a token budget"); `services/ai_drafter/trip_analyst.py:29`. Đối chiếu: ingestion CÓ cap `MAX_RAW_TEXT_CHARS=50_000` (`ingest_sanitizer.py:14`).
- **Cơ chế lỗi**: paste 1 MB vào analyze → gửi nguyên cho provider (đốt token), có thể 400 provider-side → rơi vào fallback im lặng của `trip_analyst.py:69` → nhìn như "AI trả profile fallback" thay vì "input quá cỡ". Usage chỉ được record khi run thành công.
- **Kịch bản kích hoạt**: dán nhầm cả PDF dump vào ô mô tả chuyến đi.
- **Fix**: `max_length` cho `raw_text` (vd 20 000) + validate độ dài `Idempotency-Key` ≤ 64 tại router; tùy chọn `max_tokens_in` heuristic trong `RunBudget` check trước `agent.run`.
- **Test bắt buộc**: `raw_text` vượt cap → 422 envelope `VALIDATION_FAILED`; key 200 ký tự → 422, không DataError.

#### H10 🟠 HIGH — Corpus gate 15.8 §4 ĐANG CHẾT: harness truyền tuple `(payload, usage)` vào `verify_source_quotes`
- **Vị trí**: `tests/test_ingestion_corpus.py::_extract_and_parse` (~dòng 32–34) vs `services/ingestion/extraction_service.py::_run_extractor` (~49–56, trả `tuple[CatalogIngestPayload, usage]`).
- **Cơ chế lỗi**: `_run_extractor` đổi chữ ký trả `(payload, usage)` phục vụ token accounting; corpus test không được cập nhật, truyền nguyên tuple → `AttributeError: 'tuple' object has no attribute 'products'` tại `extraction_service.py:77` — **8/8 corpus case fail** trước khi kịp kiểm tra bất kỳ expectation nào của `manifest.json`. Toàn bộ lưới an toàn corpus (trong đó có chính trap bắt C2) vô hiệu.
- **Kịch bản kích hoạt**: chạy `PYTHONPATH=. pytest -m integration tests/test_ingestion_corpus.py` (hoặc default run — xem M12).
- **Fix**: sửa test unpack `extracted, _usage = await _run_extractor(sanitized)`. (Fix nằm ở test vì service signature là chủ đích có accounting.)
- **Test bắt buộc**: chính suite corpus xanh trở lại với provider cấu hình; thêm một unit test không-LLM gọi `verify_source_quotes(payload, text)` với payload thật để pin chữ ký.

### §4.3 — MEDIUM

#### M1 🟡 MEDIUM — 409 của ingestion trả `currentRevision` = revision CŨ client gửi lên, không phải revision hiện tại
- **Vị trí**: `routers/v2/ingestion.py::_conflict_detail` (~49–53): `"currentRevision": expected_revision`.
- **Cơ chế lỗi**: hợp đồng `REVISION_CONFLICT` (recovery `reload`) tồn tại để client biết revision thật mà reload; ở đây field bị nhét chính giá trị stale của client → client "reload" xong vẫn nghĩ mình đúng revision, retry, lại 409 — vòng lặp. `IngestionRepository.get_revision` có sẵn (~90–94) nhưng không được dùng.
- **Kịch bản kích hoạt**: hai operator cùng answer một batch; người thua nhận 409 với revision sai.
- **Fix**: trong các handler 409, gọi `get_revision(batch_id)` và trả giá trị thật.
- **Test bắt buộc**: update batch ở revision 3, gửi write với `base_batch_revision=2` → 409 có `currentRevision == 3`.

#### M2 🟡 MEDIUM — LLM tự lái việc CHỌN price line thật qua `occupancy_basis`/`price_for`/`pax_count` không được validate
- **Vị trí**: `schemas/service_draft.py:24–27` (plain `str`, chỉ mô tả bằng docstring — đối chiếu `flags:30` dùng `Literal` đúng chuẩn); tiêu thụ tại `draft_run_service.py:233–241` → `pick_price_line`.
- **Cơ chế lỗi**: amount luôn từ DB (không hallucinate được tiền) nhưng LLM chọn LINE nào áp giá: emit `price_for="child"` cho người lớn, `pax_count=2` cho đoàn 10 (chọn tier nhỏ, `qty` lệch đoàn), hoặc chuỗi ngoài vocab chỉ degrade thành `rate_missing`. Line ra giá "hợp lý" mà không cờ nào.
- **Kịch bản kích hoạt**: model đoán sai party → tier giá sai được persist như bình thường.
- **Fix**: validator ràng `occupancy_basis`/`price_for` theo `OCCUPANCY_BASIS`/`PRICE_FOR` (đã import sẵn tại `service_draft.py:15`); `pax_count` derive/clamp từ `TripProfile.party` trong `run_draft`, lệch thì flag `needs_manual`.
- **Test bắt buộc**: draft emit `pax_count=1` cho party 6 với tiered rates → line bị flag hoặc reprice theo party.

#### M3 🟡 MEDIUM — Hallucinated ID bị DROP im lặng — không flag per-day, không dùng `OutputValidator` (spec P4 "bỏ + flag" mới làm nửa)
- **Vị trí**: `services/ai_drafter/draft_run_service.py:226–231` (`continue` + đếm gộp); `OutputValidator` (`guardrails.py:88–103`) chỉ ingestion dùng.
- **Cơ chế lỗi**: allowlist check đúng và fail-closed (verified), nhưng ID bịa bị loại không để lại dấu vết trong `day_outcomes`/`skipped_reasons`/run record — không phân biệt được với `rate_missing`. Sale thấy "Day 3: 2 lines" không biết model đề xuất 4 và 2 là bịa.
- **Fix**: chạy `OutputValidator.filter_valid` trên `draft_result.services`, ghi từng ID bị loại + lý do vào `DraftDayOutcomeSchema`/`stats_json`.
- **Test bắt buộc**: agent emit 1 ID hợp lệ + 1 ID bịa → day outcome nêu đích danh ID bịa, không chỉ đếm.

#### M4 🟡 MEDIUM — Commit: `SupplierConflictError` không được bọc → 500; entry supplier thiếu → mặc định `create` bỏ qua verify
- **Vị trí**: `services/ingestion/commit_service.py::_resolve_or_create_supplier` (~91: `action = entry["action"] if entry else "create"`; ~100–110: `create_supplier` KHÔNG có try/except — đối chiếu product ~148–163 có bọc `ProductValidationError/ProductConflictError`).
- **Cơ chế lỗi**: (a) supplier trùng tên được tạo giữa lúc resolve và commit → `SupplierConflictError` xuyên qua router (chỉ catch `CommitError`/revision-conflict) → 500. (b) khi resolution_json không có entry supplier (round đầu bị skip, hoặc dữ liệu cũ), commit mặc định `create` — bypass toàn bộ verify/dedupe của resolver, chỉ còn trông vào conflict-500 của service.
- **Fix**: bọc create/update supplier trong try → `CommitError` (422 như product); entry thiếu → `CommitError("supplier chưa được resolve")` thay vì mặc định create.
- **Test bắt buộc**: tạo supplier trùng tên trước rồi commit action=create → 422 CommitError, không 500; batch không có supplier entry nhưng payload có supplier → 422.

#### M5 🟡 MEDIUM — `product_ids_by_title` khóa theo `title_text` → hai product trùng title đè nhau, rate gắn nhầm product
- **Vị trí**: `services/ingestion/commit_service.py:294–300` và `resolution_service.py:371–381` (cùng pattern); tiêu thụ tại `_commit_rate_group:213`.
- **Cơ chế lỗi**: map title→id; hai candidate cùng `title_text` (vd "Deluxe Room" xuất hiện 2 lần cho 2 wing/2 board basis) → entry sau đè entry trước → mọi rate_group của title đó gắn vào MỘT product, product kia mồ côi rate.
- **Fix**: khóa theo candidate index (`/products/{i}`) — `entity_ref` của rate entry đã trỏ theo index rate_group, chỉ cần map product theo index thay vì title (rate_group có `product_title_text`, thêm disambiguation: nếu title trùng → CommitError yêu cầu operator sửa title).
- **Test bắt buộc**: payload 2 product cùng title + 2 rate_group → hoặc CommitError rõ ràng, hoặc mỗi rate về đúng product theo index.

#### M6 🟡 MEDIUM — `verify_source_quotes` bypass bằng quote toàn whitespace
- **Vị trí**: `services/ingestion/extraction_service.py::_quote_verified` (~44–46).
- **Cơ chế lỗi**: `source_quote=" "` qua được `min_length=1` của schema; `bool(" ")` là True và `" ".strip()` → `""`, mà `"" in sanitized_text` LUÔN True → candidate bịa hoàn toàn vẫn "verified", vào thẳng payload staging.
- **Fix** (pure): `stripped = (source_quote or "").strip(); return bool(stripped) and stripped in sanitized_text`.
- **Test bắt buộc**: candidate với `source_quote=" "` / `"\n"` → bị drop thành `unresolved`.

#### M7 🟡 MEDIUM — Line idempotency key có thể vượt `service_lines.idempotency_key` String(64) → DataError 500 giữa run (Postgres)
- **Vị trí**: `services/ai_drafter/draft_run_service.py:286` (`f"{key}:d{n}:{product_id}:{i}"`); cột `String(64)` trong `db/models/costing.py`; header nhận không validate tại `routers/v2/ai_drafter.py:59,101`; tương tự Idempotency-Key ingestion vs `String(128)` (`db/models/ingestion.py:43`).
- **Cơ chế lỗi**: UUID 36 ký tự + `:d10:` + `prd_`+16hex + `:10` ≈ 64+; key client dài hơn 40 ký tự tràn ngay. Postgres raise `StringDataRightTruncation` (không phải IntegrityError → không thành `CostingLineDuplicateError`) → 500 giữa run; SQLite trong test không enforce nên suite xanh.
- **Fix**: derive per-line key bằng hash cố định độ dài (`sha1(...)[:40]`); validate header ≤64 (drafter) / ≤128 (ingestion) tại router.
- **Test bắt buộc**: assert `len(line_key) <= 64` với worst case (key 64 ký tự, day 12, line 12); API test key quá dài → 422.

#### M8 🟡 MEDIUM — Mobility filter sai vocab + fallback nguy hiểm; transport origin filter nửa hỏng
- **Vị trí**: `services/ai_platform/toolsets/catalog.py:224–226` (mobility: so `physical_level` với vocab mobility `"limited"/"wheelchair"`, default `"full"` không bao giờ match, và `or candidates` trả list KHÔNG lọc khi rỗng); `catalog.py:185` (origin: `(p.origin_destination_id or arrival_id) == origin_id or p.origin_destination_id == origin_id` — product origin=NULL chỉ match khi from==to; disjunct hai thừa).
- **Cơ chế lỗi**: đoàn wheelchair nhận activities cường độ cao "như đã lọc sẵn" (spec §1.4 "mobility lọc physical_level"); transport không khai `origin_destination_id` vô hình trên mọi route thật.
- **Fix**: định nghĩa thang `physical_level` khớp seeded data, map mobility→mức tối đa, BỎ fallback `or candidates` cho mobility (hard constraint như `seat_capacity:186–188`); origin filter viết tường minh semantic (`in (None, origin_id)` nếu wildcard, hoặc equality chặt).
- **Test bắt buộc**: catalog chỉ có `physical_level="strenuous"` + `mobility="wheelchair"` → rỗng; product origin=None trên route A→B → assert hành vi đã chọn.

#### M9 🟡 MEDIUM — Replay idempotent của draft mất `day_outcomes`; `runId` request là input chết
- **Vị trí**: `draft_run_service.py:330` (persist output LOẠI `day_outcomes`) vs `:182–184` (replay đọc `day_outcomes` → luôn `[]`); `schemas/v2/ai_drafter.py:47` (`run_id` analyze không bao giờ được đọc — chuỗi analyze→review→draft không kiểm chứng được server-side).
- **Fix**: persist `day_outcomes` (hoặc bản compact) vào `output_json`; ghi `payload.run_id` vào `input_ref_json`.
- **Test bắt buộc**: draft 2 lần cùng key → hai response `day_outcomes` giống hệt, cùng `run_id`, không line trùng.

#### M10 🟡 MEDIUM — `llm_client.get_model()` chạy tiếp với `api_key=None` + dùng `print`
- **Vị trí**: `llm_client.py:35–51`.
- **Cơ chế lỗi**: thiếu key → in `[Error]` rồi vẫn dựng provider → lỗi auth nổ SÂU trong agent run, bị fallback của analyst (`trip_analyst.py:69`) hoặc per-day catch của drafter nuốt → misconfiguration đội lốt "AI degrade". Vi phạm rule "validate secrets at startup" + "no print, use logging".
- **Fix**: raise `RuntimeError` rõ ràng khi không có key nào; chuyển `print` → `logging`.
- **Test bắt buộc**: unset cả hai env key → `get_model()` raise message hành động được.

#### M11 🟡 MEDIUM — Heuristic separator + locale ngày âm thầm chọn nghĩa: "12.500" USD → $12,500; "05/06/2025" luôn là DMY
- **Vị trí**: `core/rules/ingest_parser.py::_split_numeric_groups` (~81–98: một dấu chấm + đúng 3 số cuối ⇒ thousands) và `_parse_date_component` (~179–183: chỉ thử DMY, không cờ ambiguity cho token hợp lệ cả hai chiều).
- **Cơ chế lỗi**: **đã tái hiện** `parse_amount_text("12.500","USD")` → 1_250_000 minor ($12,500) trong khi tariff Anh-Mỹ nghĩa là $12.50 — sai ×1000 không cờ. "05/06/2025" đọc 5-June; tariff US nghĩa May-6 — sai im lặng (MDY thuần như "12/25/2025" thì may mắn invalid). Đây là quyết định ngầm về locale chưa được spec chốt.
- **Fix** (pure): với USD/EUR một-chấm-3-số-cuối và giá trị < 100 → `ambiguous=True` hỏi operator; ngày mà cả DMY lẫn MDY đều hợp lệ và cho kết quả khác nhau → chỉ chấp nhận khi khớp `doc_meta.detected_language`/nguồn VN, còn lại ambiguous.
- **Test bắt buộc**: `("12.500","USD")` → ambiguous; `("12.500","VND")` → 12_500; `"05/06/2025"` một mình → ambiguous hoặc pin DMY có documented rationale + test khóa.

#### M12 🟡 MEDIUM — Suite real-LLM chạy trong default `pytest` (mark `integration` không đăng ký, không deselect)
- **Vị trí**: `tests/test_ingestion_corpus.py:54` (`PytestUnknownMarkWarning`), repo không có `pytest.ini`/`pyproject` addopts `-m "not integration"` (CLAUDE.md xác nhận không có pytest.ini).
- **Cơ chế lỗi**: docstring tự nhận "does not run in the default pytest invocation" — SAI: baseline default run đã thực thi cả 8 case, gọi network/LLM thật (56s, tốn phí, CI không hermetic).
- **Fix**: đăng ký marker + default deselect qua `conftest.py` (`collection_modifyitems` thêm skip khi thiếu `-m integration`), giữ nguyên không thêm pytest.ini nếu đó là chủ đích repo.
- **Test bắt buộc**: `pytest tests/test_ingestion_corpus.py` không có `-m integration` → 8 skipped, 0 network call.

#### M13 🟡 MEDIUM — Idempotency tạo batch có race → double LLM spend + IntegrityError 500; `idempotency_key` của commit là tham số chết
- **Vị trí**: `services/ingestion/extraction_service.py::create_batch` (~224–228 check-then-insert, không khóa); unique constraint hứng race tại flush (`ingestion_repository.py:68`); `commit_service.py::commit_batch` (~263) nhận `idempotency_key` nhưng KHÔNG dùng ở bất kỳ đâu — idempotency của commit chỉ dựa status + CAS.
- **Cơ chế lỗi**: hai request cùng key đồng thời đều miss `get_by_idempotency_key` → cả hai gọi Extractor (trả tiền ×2) → insert thứ hai vỡ unique → 500 thay vì trả batch sẵn có. Tham số chết ở commit là API nói dối (client tưởng key bảo vệ).
- **Fix**: catch IntegrityError trên flush → re-read theo key và trả replay; commit: hoặc dùng key ghi vào `commit_result_json` để đối chiếu, hoặc bỏ tham số khỏi chữ ký.
- **Test bắt buộc**: hai create song song cùng key (hai session) → một 201 một 200/201 replay, đúng MỘT batch, đúng MỘT lần gọi extractor (mock đếm).

#### M14 🟡 MEDIUM — Supersede chọn `overlapping[0]` tùy ý; các rate chồng lấn còn lại vẫn active
- **Vị trí**: `services/ingestion/commit_service.py::_commit_rate_group` (~238–242).
- **Cơ chế lỗi**: nhiều active rate chồng validity → chỉ rate đầu (thứ tự query không cam kết) bị supersede; các rate còn lại tiếp tục chồng cửa sổ với rate mới → trạng thái "hai giá cùng lúc" mà 15.2 cấm.
- **Fix**: supersede TẤT CẢ overlapping, hoặc CommitError khi `len(overlapping) > 1` yêu cầu operator xử lý.
- **Test bắt buộc**: product có 2 active rate chồng cửa sổ mới → hành vi đã chọn (cả hai superseded / 422), không bao giờ để lại rate chồng.

### §4.4 — LOW (ghi nhận, fix cùng đợt khi tiện)

- **L1** `repositories/ingestion_repository.py::list` (~57–60): `total = len(items)` sau `limit` — không phải tổng thật, pagination UI sai. Fix: `count()` riêng.
- **L2** `parse_amount_text` dùng float trung gian (`round(value * divisor)`) — trong biên độ 2^53 hiện an toàn, chuyển `Decimal` để khoá rủi ro tương lai.
- **L3** `ingest_sanitizer`: bảng zero-width thiếu Cf khác (U+200E/200F LRM/RLM, U+2066–2069, variation selectors, U+E0000 tags — kênh smuggling còn mở); truncate 50k im lặng — nên append một `UnresolvedItem` "văn bản bị cắt" khi chạm trần; text chứa `</INGESTION_RAW_TEXT>` phá delimiter (vô hại nhờ 0-tool nhưng nên strip/escape tag trùng).
- **L4** `catalog.py:305` `resolve_applicable_rates` hardcode `price_for="adult"` (tín hiệu bookability sai cho line child-only); `:307` trả `tariff_id` không record vào allowlist (phá invariant "mọi id trả ra đều được record" dù vô hại hiện tại); `price_band` rank trong nội bộ MỘT rate → single-line luôn "low".
- **L5** `catalog.py:188,252`: `int(category_attributes["seat_capacity"])` / `date.fromisoformat(blackout)` trên JSON staff nhập tay có thể raise trong tool → chết cả ngày draft; coerce khoan dung.
- **L6** `trip_analyst.py:69` bare `except Exception` nuốt cả programming error thành fallback "partial" — catch hẹp theo lớp lỗi provider/validation + log.
- **L7** Một `AllowlistRecorder` dùng chung mọi ngày draft → ngày 5 emit product ngày 1 vẫn qua allowlist (server re-resolve giới hạn thiệt hại thành line sai destination có rate thật); nếu cần provenance per-day thì snapshot/diff allowlist theo ngày.
- **L8** `draft_run_service.py:75–107` nhân bản `runs.record_run` nhưng bỏ check `_VALID_STATUSES`; `stats_json.retries` luôn 0 (retry nằm trong pydantic_ai, không mirror). Cùng nguồn: `draft_run_service.py:30` import private `_rate_candidates_for_product` từ toolset (layering smell).
- **L9** `llm_client._get_http_client` race cold-start có thể leak một `AsyncClient`; guard bằng lock module.
- **L10** Create-batch replay không kiểm tra actor: staff B gửi trùng key của staff A đọc được batch của A (cùng tenant, rủi ro thấp — ghi nhận).
- **L11** `commit_service._resolve_or_create_product` action `update` chỉ ghi đè `title` bằng text ingest (rename churn) và không mang dữ liệu mới nào khác — cân nhắc no-op như fix H4.

---

## 3. §4.7 Danh sách test nợ theo spec (Bổ sung cùng đợt fix)

1. **Allowlist enforcement (per-finding)**: fabricated `product_id` bị loại VÀ được nêu đích danh trong day outcome (M3); id hợp lệ-trong-DB-nhưng-tool-chưa-thấy bị loại (đang có test "fabricated", thiếu case DB-valid).
2. **Partial commit rollback**: commit_batch fail ở rate thứ K/N (mock RateService raise ở K) → KHÔNG supplier/product/rate nào tồn tại sau rollback (assert đếm bảng); và commit lặp trên batch committed → zero ghi mới (H6).
3. **Zero-money schema grep**: mở rộng introspection test hiện có thành grep cấm `amount|price|cost|currency|rate_value` trên `schemas/service_draft.py` + `schemas/trip_profile.py` + mọi tool return type trong `toolsets/catalog.py` (khóa vĩnh viễn Drafter Pricing Hallucination).
4. **Read-only session assertion**: structural test đệ quy 1 tầng trên `CatalogReadOnlyDeps` (H7) + runtime spy: chạy đủ 7 tool trên session thật rồi assert `session.new/dirty/deleted` rỗng và không có `commit/flush` được gọi.
5. **Concurrent tool-call safety**: fake model 2 tool call/turn trên AsyncSession thật (C3).
6. **Parser corruption pins**: toàn bộ case tái hiện ở C1/C2/H5/M11 thành parametrized tests trong `test_ingest_parser.py`.
7. **Failure-path run logging**: mọi đường lỗi (extraction 502, resolution 502, drafter mid-run) đều để lại `ai_runs` row (H8).
8. **Corpus harness signature pin** + default-run deselect cho mark `integration` (H10, M12).
9. **409 revision truthfulness**: `currentRevision` là revision thật từ DB (M1).
10. **Postgres-enforced length**: line idempotency key ≤64, header keys ≤64/128 (M7) — chạy trên Postgres container hoặc assert độ dài tĩnh worst-case.

## 4. §4.8 Exit Gate của Track 4

1. **C1, C2, C3 + H1→H10 fix xong**, toàn bộ "Test bắt buộc" tương ứng và 10 mục test nợ §4.7 xanh.
2. **M1→M14 fix** (M11 được phép chốt bằng quyết định locale có document + test khóa thay vì đổi hành vi); L1→L11 ghi nhận, fix cùng đợt khi chạm file.
3. **Toàn bộ test suite Track 4 (112 test hiện có + test mới) xanh**; frozen contracts (`test_v2_api_manifest_contract`, `test_v2_error_envelope`, `test_domain_rules`, `test_business_gates`, `test_ssot_integrity`) xanh; **KHÔNG sửa 2 migration** `20260907_45`/`20260908_46` (mọi fix nằm ở service/schema-validator/pure-rules/test); corpus suite chạy được lại với provider và 8/8 case pass (bao gồm 2 trap case — chính là lưới bắt C1/C2 tái phát).
