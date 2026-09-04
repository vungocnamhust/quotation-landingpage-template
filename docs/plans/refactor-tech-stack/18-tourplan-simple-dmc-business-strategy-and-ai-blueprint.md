# 18. TourPlan Simple for DMC Startup — Chiến lược kinh doanh DMC hiện đại & Bản thiết kế điểm chạm AI

> **Loại tài liệu**: Nghiên cứu chiến lược kinh doanh & mô hình vận hành (business blueprint),
> **không phải** spec kỹ thuật. Viết từ góc nhìn Managing Director / CPO của một DMC inbound cao cấp
> (Private, Tailor-made 3–5 sao, thị trường Âu–Mỹ–Úc). Mục đích: Founder chọn phương hướng; mỗi
> tính năng được chọn sau đó mới có spec riêng theo khuôn 15.x.
>
> **Quan hệ với các plan trước**: Plan 15 và 15.1–15.9 là "bệ phóng kỹ thuật" đã có: Supplier
> Registry, Product Catalog, Rates đa tiền tệ theo mùa, Costing bóc tách từng dòng dịch vụ, Booking
> đóng băng snapshot giá + điều khoản, AP đối soát theo `voucher_ref`, Ingestion Co-Pilot (bảng giá
> văn bản → catalog), AI Service Drafter, Interactive brochure (16.x), AI Platform Layer (agent
> factory + guardrails + nhật ký `ai_runs` + kho tool chỉ-đọc). Tài liệu này **không mở lại** bất kỳ
> quyết định kiến trúc nào ở đó. Nó trả lời câu hỏi ngược lại: *"Với bệ phóng ấy, DMC nên kinh doanh
> và vận hành thế nào, và tính năng nào đáng xây tiếp — theo thứ tự nào?"*
>
> **Cách đọc**: Mỗi mảng nghiệp vụ đi theo trình tự (a) bản chất & nỗi đau thực địa → (b) phương án
> chiến lược (Option A thực dụng / Option B số hóa sâu / đôi khi Option C) → (c) tính năng hệ thống
> cụ thể, neo vào module đã có. Phần 5 (AI) đứng riêng, có ma trận chi phí/giá trị và lộ trình 30 ngày.
>
> **Quy ước**: "Agent" = đại lý gửi khách B2B (Travel Designer, Boutique Outbound Tour Operator).
> "NCC" = nhà cung cấp dịch vụ (khách sạn, xe, tàu, nhà hàng, hướng dẫn viên). "File" = một hồ sơ
> tour (từ yêu cầu đến khi đóng sổ). Tiền tệ ví dụ dùng USD/EUR (bán) và VND (mua).

**Một câu**: DMC cao cấp không bán phòng khách sạn hay xe; nó bán **sự an tâm có bảo chứng** cho
đại lý quốc tế và **trải nghiệm không thể google** cho khách — hệ thống vì vậy phải khép kín vòng
*Yêu cầu → Báo giá chính xác → Vận hành không lỗi → Xử lý sự cố tại chỗ → Phản hồi → Dữ liệu độc
quyền*, và AI chỉ được cắm vào những điểm nghẽn thủ công có đầu vào cấu trúc và có người gác cổng.

---

## 0. Tóm tắt điều hành (Executive Summary)

1. **Đại lý quốc tế chọn DMC theo 4 tiêu chí, không phải theo giá**: tốc độ phản hồi có chất lượng
   (dưới 2 giờ làm việc), báo giá không phát sinh phụ thu ngầm, linh hoạt khi khách đổi ý mà không
   làm loạn hồ sơ, và bảo chứng an toàn khi có sự cố. Mất một agent tốt = mất 10–40 file/năm, tức
   hàng trăm nghìn USD doanh thu tái diễn. Giữ chân agent là bài toán vận hành, không phải marketing.
2. **Chu trình DMC phải khép kín ở dữ liệu, không chỉ ở quy trình**: mỗi chuyến đi phải trả lại cho
   hệ thống (i) giá thực tế so với giá báo, (ii) chất lượng thực tế của NCC, (iii) tri thức thực địa
   mới. Nền tảng hiện có đã trả trước "vé vào cửa" cho (i) bằng snapshot booking + AP theo voucher;
   (ii) và (iii) là hai mảng còn trống và là **kho tài sản độc quyền** (data moat) của DMC.
3. **B2B Partner Deep-Query Portal** là tính năng giữ chân agent có đòn bẩy cao nhất: agent không
   cần chatbot bách khoa, họ cần câu trả lời nghiệp vụ đã kiểm chứng ("xe 16 chỗ có vào được phố cổ
   Hội An buổi chiều không?") trong vài phút thay vì vài ngày. Điều kiện tiên quyết là **ma trận
   phơi nhiễm dữ liệu 4 lớp** (Public / Partner / Internal / Restricted) — giá NET, chiết khấu, danh
   bạ điều hành không bao giờ rời lớp Restricted.
4. **6 phòng ban, 6 nút thắt**: Sale mất thời gian dựng lại từ đầu mỗi báo giá và không kiểm soát
   được phiên bản; Ops chôn 30–40% thời gian vào việc "đuổi" xác nhận NCC và không có nhật ký chuyến
   đi để đối soát; Dữ liệu NCC được nhập bằng tay từ PDF nên vừa chậm vừa sai; Marketing không có kho
   tri thức bản địa có cấu trúc; CS không có cảnh báo sớm mức độ hài lòng; CEO không nhìn được biên lợi
   nhuận thực và khoảng trống dòng tiền theo ngày.
5. **Phân kỳ**: Phase 1 (0–3 tháng) khép vòng vận hành với dữ liệu thật (catalog giàu qua ingestion,
   costing → booking → AP chạy đủ một chu kỳ); Phase 2 (3–9 tháng) giữ chân & bảo vệ (Partner Portal
   v1, Trip Diary + Incident, Supplier Trust Score, Cash-flow calendar); Phase 3 (9–18 tháng) xây moat
   (Destination Knowledge Base + Media Vault gắn vào tour, Agent Profitability Matrix, AI retrieval).
6. **AI**: Cắm vào 5 điểm có ROI cao và đầu vào cấu trúc — bóc tách bảng giá/hóa đơn NCC, dựng dàn
   dịch vụ từ yêu cầu văn xuôi, trợ lý tra cứu cho agent trên kho tri thức có phân lớp, kiểm tra tính
   khả thi lịch trình (pacing/logistics), phân loại sự cố & phản hồi. **Cấm tuyệt đối** AI quyết giá,
   quyết availability, viết điều khoản hủy, trả lời phàn nàn của khách VIP, quyết bồi thường, gửi
   thẳng cho NCC/khách không qua người. Chiến lược Lean: dùng nguyên AI Platform Layer đã có (typed
   output, tool chỉ-đọc, ngân sách per-run, nhật ký), RAG trên PostgreSQL, định tuyến model rẻ →
   frontier theo độ rủi ro. **3 việc làm ngay trong 30 ngày**: (1) Rate Ingestion Co-Pilot đọc được
   PDF/Excel và đóng data gate 15.8b; (2) đưa AI Service Drafter qua exit gate với corpus thật để rút
   thời gian ra báo giá đầu tiên xuống dưới 1 giờ; (3) Partner Deep-Query Assistant bản nội bộ (staff
   dùng trước) trên Destination Knowledge Base tối thiểu có phân lớp phơi nhiễm và trích dẫn nguồn.

---

## 1. TỔNG QUAN CHIẾN LƯỢC: MÔ HÌNH VẬN HÀNH KHÉP KÍN CỦA MODERN PRIVATE DMC

### 1.1 DMC cao cấp thực sự bán cái gì

Ở phân khúc private 3–5 sao cho khách Âu–Mỹ–Úc, giá phòng và giá xe gần như minh bạch: agent có
thể tự tra OTA, khách có thể tự đọc TripAdvisor. Cái agent **không thể** tự làm, và sẵn sàng trả
biên lợi nhuận 18–30% cho DMC, là ba thứ:

| Giá trị | Agent mua gì | Bằng chứng trong vận hành | Hệ quả cho hệ thống |
| :-- | :-- | :-- | :-- |
| **An tâm có bảo chứng** | "Nếu có chuyện gì lúc 2 giờ sáng ở Sapa, có người xử lý và tôi biết trước khi khách gọi tôi" | Đường dây 24/7, quy trình escalation, bồi thường tại chỗ trước khi khách về nước | Cần Incident log, Trip Diary, cảnh báo sớm — không phải "tính năng CS", mà là **sản phẩm cốt lõi** |
| **Cá nhân hóa may đo** | Lịch trình đúng nhịp cho gia đình 3 thế hệ, người ăn chay nghiêm ngặt, khách 70 tuổi đi trekking nhẹ | Pacing hợp lý, chọn NCC đúng hồ sơ khách, amendment nhanh | Cần TripProfile có cấu trúc, catalog có thuộc tính phù hợp (suitability), quản lý phiên bản |
| **Tri thức bản địa độc quyền** | "Chỗ chụp ruộng bậc thang không có người lúc 6h sáng", "nghệ nhân X chỉ nhận khách qua chúng tôi" | Insider tips trong proposal, upsell trải nghiệm không có trên Google | Cần Destination Knowledge Base + Media Vault gắn vào từng dịch vụ — **data moat** |

Hệ quả chiến lược: **mọi tính năng phải được đo bằng một trong ba giá trị trên**. Tính năng không
tăng an tâm, không tăng cá nhân hóa, không tích lũy tri thức độc quyền → xếp sau.

### 1.2 Chu trình khép kín 8 chặng của một file tour

Chu trình thực tế của một DMC cao cấp không kết thúc khi khách về nước; nó kết thúc khi **dữ liệu
của chuyến đi đã quay về nuôi chuyến sau**. Bảng dưới là chu trình chuẩn, kèm nỗi đau thực địa và
điểm neo trên nền tảng hiện có.

| # | Chặng | Bản chất nghiệp vụ | Nỗi đau thực địa điển hình | Tiêu chuẩn dịch vụ (SLA nội bộ) | Neo trên nền tảng hiện có |
| :-: | :-- | :-- | :-- | :-- | :-- |
| 1 | **Tiếp nhận yêu cầu** (Inquiry) | Agent gửi brief: số khách, ngày, ngân sách/hạng sao, sở thích, hạn chế (ăn uống, sức khỏe, trẻ em) | Brief thiếu thông tin chủ chốt (ngày bay, phân bổ phòng), phải hỏi lại 2–3 vòng; yêu cầu nằm trong hộp thư cá nhân của sale | Xác nhận đã nhận trong 30 phút; câu hỏi làm rõ gộp **một lần** trong 2 giờ | Quote request intake + TripProfile (15.7 TripAnalyst) |
| 2 | **Tư vấn may đo** (Design) | Chọn tuyến, nhịp, NCC theo hồ sơ khách; đề xuất 1 phương án chính + 1–2 biến thể (hạng sao / nhịp) | Dựng lại từ đầu mỗi lần; tri thức nằm trong đầu senior sale; pacing sai (ngày 7 giờ xe) chỉ lộ khi khách phàn nàn | Proposal đầu tiên trong **24 giờ** (mục tiêu 4 giờ với Drafter) | Costing sheet + service lines (15.4), Drafter (15.7), catalog `quality_tier` |
| 3 | **Chốt giá** (Price lock) | Giá bán = tổng net + markup; kiểm tra phụ thu mùa vụ, gala bắt buộc, single supplement, child policy; hiệu lực báo giá | Quên phụ thu Tết/Noel → lỗ hoặc phải "xin" agent; rate hết hạn giữa chừng; nhiều phiên bản giá không biết bản nào agent đã đồng ý | Báo giá kèm hiệu lực (14 ngày); mọi phụ thu hiện rõ dòng riêng | Rates theo mùa + supplements có ngày hiệu lực (15.3), Apply pricing log bất biến + drift badge (15.5) |
| 4 | **Đặt cọc & Book dịch vụ** (Confirm & Dispatch) | Nhận cọc → gửi yêu cầu từng NCC → đuổi xác nhận → nhận mã xác nhận → phát voucher | 30–40% thời gian operator là đuổi xác nhận; hạn release/hạn cọc NCC nằm trong PDF, không ai nhớ; amendment làm lệch kế toán | Mọi dịch vụ có trạng thái + hạn phải quyết; không dịch vụ nào "cháy hạn" mà không có cảnh báo trước 7 ngày | Booking lines snapshot + deadline engine + Ops board (15.6), Dispatch/voucher (15.12 blueprint) |
| 5 | **Điều hành thực địa** (Operate) | Guide/driver thực thi; ops theo dõi từng ngày; xử lý thay đổi nhỏ (đổi nhà hàng, đổi giờ) | Không có nhật ký ngày; chi phí phát sinh (đổi xe, thêm bữa) không được ghi ngay → mất khi đối soát | Mỗi ngày tour có 1 dòng nhật ký trước 21h; phát sinh ghi trong ngày | Trip Diary (**mới**, §3.2), event `booking.line.delivered` |
| 6 | **Xử lý sự cố tại chỗ** (Service Recovery) | Phân loại mức độ, leo thang đúng người, bù đắp trước khi khách rời điểm đến | Guide tự xử rồi không báo; ops biết khi agent đã nhận email phàn nàn từ khách | Ghi nhận ≤15 phút; kế hoạch xử lý ≤1 giờ; agent được báo **trước** khách báo | Incident Escalation (**mới**, §3.5) |
| 7 | **Thu thập phản hồi** (Feedback) | Khách (NPS, từng dịch vụ), guide (báo cáo cuối tour), ops (phát sinh), kế toán (lệch hóa đơn) | Khảo sát chung chung, không gắn vào NCC cụ thể; điểm tốt/xấu không quay về catalog | Phản hồi gắn **từng dịch vụ đã đi**; NCC có điểm tín nhiệm cập nhật trong 7 ngày sau tour | Supplier Trust Score (**mới**, §3.3), AP variance (15.9) |
| 8 | **Tái nuôi dưỡng dữ liệu** (Re-nourish) | Giá thực → catalog; chất lượng → điểm NCC; tri thức mới → knowledge base; ảnh mới → media vault | Không có chỗ chứa; tri thức mất khi nhân viên nghỉ | Sau mỗi tour có ≥1 bản cập nhật knowledge/media/score | Destination Knowledge Base + Media Vault (**mới**, §3.4) |

Nhận xét chiến lược:

- Chặng 1–4 đã có nền tảng (Plan 15.x). Nút thắt còn lại là **dữ liệu** (catalog chưa giàu) chứ
  không phải phần mềm.
- Chặng 5–8 là **vùng trắng** của hệ thống và cũng là nơi tạo khác biệt với đối thủ dùng Tourplan /
  Lemax thuần túy (các hệ đó rất mạnh ở chặng 3–4, yếu ở 5–8).
- Vòng lặp khép kín đòi hỏi một nguyên tắc dữ liệu: **mọi phản hồi phải gắn được vào dịch vụ đã đi**
  (booking line), không phải gắn vào "chuyến đi" chung chung. Nền tảng đã có nguyên tử này
  (`service_line` → `booking_line` → `voucher_ref`), nên toàn bộ phần 5–8 chỉ cần *đọc* nó.

### 1.3 Đại lý quốc tế cần gì nhất ở một local DMC

Từ kinh nghiệm đàm phán với luxury travel designers (Virtuoso-type, boutique operators Anh/Đức/Úc),
bốn kỳ vọng dưới đây quyết định họ có gửi file thứ hai hay không. Bảng kèm "đơn vị đo" để hệ thống
đo được — cái gì không đo được thì không cải thiện được.

| Kỳ vọng | Ý nghĩa thực tế với agent | Đơn vị đo nội bộ | Nền tảng hỗ trợ gì hiện nay | Còn thiếu |
| :-- | :-- | :-- | :-- | :-- |
| **Tốc độ phản hồi có chất lượng (<2h)** | Agent thường hỏi 2–3 DMC cùng lúc; DMC trả lời **đầu tiên và đủ** sẽ "đóng khung" chuyến đi; các DMC sau chỉ được so giá | Thời gian đến phản hồi đầu (first response), thời gian đến proposal đầu, số vòng hỏi lại | Intake + Drafter rút thời gian dựng dàn dịch vụ | SLA timer nhìn thấy được, hàng đợi câu hỏi agent, template trả lời |
| **Báo giá chính xác, không phụ thu ngầm** | Một lần "xin thêm phụ thu gala dinner" là mất uy tín 2 năm | Số lần sửa giá sau khi agent đã đồng ý; % file có phát sinh ngoài báo giá | Supplements có ngày hiệu lực, cancellation tiers snapshot, drift badge khi rate đổi | Checklist phụ thu bắt buộc theo ngày (Tết, 24/12, 31/12, cuối tuần lễ hội), cảnh báo rate hết hạn trước ngày khởi hành |
| **Linh hoạt khi khách đổi ý** | Đổi ngày, đổi khách sạn, thêm 1 khách, bỏ 1 ngày — cần trả lời "được không, giá bao nhiêu, phạt bao nhiêu" trong vài giờ | Thời gian xử lý amendment; % amendment có lỗi kế toán | Amendment = hủy dòng + thêm dòng, phạt tính từ tiers đóng băng (15.6) | Màn hình "Amendment quote" cho agent tự xem tác động giá/phạt trước khi quyết |
| **Bảo chứng an toàn tuyệt đối** | Agent bán "chúng tôi có đối tác tại chỗ 24/7" cho khách; DMC phải chứng minh được điều đó | Thời gian ghi nhận sự cố, thời gian agent được thông báo, % sự cố xử lý xong trước khi khách rời điểm | Notification subsystem (SSE/email) | Incident ladder, Trip Diary, báo cáo sự cố chuẩn gửi agent |

**Kinh tế học giữ chân agent (Agent Retention Economics)** — số liệu điển hình cho boutique outbound
operator gửi khách Việt Nam/Đông Dương:

| Chỉ số | Khoảng điển hình | Ý nghĩa |
| :-- | :-- | :-- |
| Số file/agent/năm | 10–40 | Một agent tốt = một "kênh bán" ổn định |
| Giá trị trung bình/file | 6.000–20.000 USD (gia đình 4–6 khách, 10–14 ngày) | |
| Biên lợi nhuận gộp | 18–30% | Upsell trải nghiệm chiếm 15–25% biên |
| Chi phí giành 1 agent mới | 1–2 chuyến fam trip + 6–12 tháng nuôi quan hệ + 3–5 file "chào" biên thấp | Đắt gấp 5–10 lần chi phí giữ agent cũ |
| Nguyên nhân mất agent | (1) sự cố xử lý kém, (2) phụ thu ngầm, (3) trả lời chậm, (4) đối thủ có sản phẩm độc quyền | 3/4 nguyên nhân là **vận hành**, không phải giá |

Kết luận: đầu tư vào tốc độ + chính xác + recovery + độc quyền có ROI cao hơn mọi chương trình
khuyến mãi B2B.

### 1.4 Các bẫy nghiệp vụ kinh điển của tour cao cấp (hệ thống phải "biết" trước sale)

Đây là danh sách những thứ senior sale/ops nhớ trong đầu; startup DMC mất tiền vì nhân viên mới
không biết. Hệ thống phải biến chúng thành dữ liệu có cấu trúc hoặc checklist bắt buộc.

| Bẫy | Bản chất | Hậu quả nếu bỏ sót | Nền tảng xử lý thế nào |
| :-- | :-- | :-- | :-- |
| **Cancellation tiers** | Hủy trước 30 ngày miễn phí, 15–29 ngày phạt 50%, <14 ngày 100%, no-show 100%; mỗi NCC một kiểu; mùa cao khác mùa thấp | Khách hủy, DMC chịu phạt NCC mà không thu được khách | Policy JSONB có cấu trúc trên supplier/rate, snapshot khi booking, phạt tính tự động (15.1/15.3/15.6) |
| **Room release / option date** | Khách sạn giữ phòng đến ngày X, sau đó tự thả nếu chưa cọc | Mất phòng ở resort đẹp nhất mùa cao; phải downgrade và bồi thường | `penalty_free_until`, `request_by_date` tính máy trên Ops board (15.6) |
| **Deposit deadline NCC trước khi khách trả** | NCC đòi cọc 30–50% khi confirm; agent có credit terms trả sau khởi hành 30 ngày | DMC ứng vốn hàng chục nghìn USD/mùa; "chết vốn" | T9 cash-flow guardrail (15.6) — cần nâng thành **Cash-flow calendar** (§3.6) |
| **Phụ thu mùa vụ & gala bắt buộc** | Tết, 24/12, 31/12 compulsory gala dinner 80–250 USD/người; peak surcharge; weekend surcharge; lễ hội (Hội An rằm) | Báo thiếu → lỗ hoặc xin thêm | Supplements có ngày hiệu lực (15.3 T7); cần **checklist ngày đặc biệt** tự bắn cảnh báo theo ngày dịch vụ |
| **Single supplement / half-twin** | Khách lẻ phòng đơn; 3 người 1 phòng (extra bed) giá khác | Sai phân bổ phòng → sai giá 10–20% | Rate price lines theo occupancy (15.3 E5), RoomAllocation (15.7) |
| **Child / infant policy** | Tuổi tính trẻ em khác nhau theo NCC (2–5, 6–11, 12+); trẻ dùng giường chung/ giường phụ | Lệch giá, tranh cãi tại quầy | `child_policy_json` (14.0 B.3) |
| **Guide allowance & tipping norms** | Guide/driver overnight cần phòng + bữa ăn (một số KS cấp phòng staff, số khác không); tipping 5–10 USD/ngày/khách cho guide, 3–5 cho driver (Việt Nam) — phải nói với agent trước | Chi phí "vô hình" 3–5% file; khách khó chịu vì không được báo trước | Product category `guide`/`driver` với line "allowance"; nội dung tipping trong proposal (content budgets) |
| **Giới hạn phương tiện theo địa hình/giờ** | Xe 16 chỗ không vào phố cổ Hội An/Hà Nội theo khung giờ cấm; đèo Hà Giang giới hạn xe 29 chỗ; mùa mưa đường Mai Châu–Pù Luông | Khách kéo vali 800m dưới mưa; đổi xe phát sinh | Destination Knowledge Base (§3.4) + Feasibility checker (§5) |
| **Thời tiết & lệnh cấm** | Cảng vụ Hạ Long cấm tàu khi bão; Sapa sương mù mất view; Mekong lũ | Hủy dịch vụ không phải lỗi DMC nhưng khách trách DMC | Incident playbook + phương án B có sẵn giá (§3.2/§3.5) |
| **Ăn kiêng / tôn giáo / y tế** | Vegetarian nghiêm ngặt, halal, kosher, dị ứng hạt, celiac; thuốc cần lạnh | Sự cố nghiêm trọng nhất về danh tiếng | Thuộc tính NCC (nhà hàng/KS có năng lực), flag trên TripProfile, briefing pack cho guide |
| **Hiệu lực rate & tái đàm phán** | Contract rate 1/10–30/9; NCC gửi bảng mới giữa mùa; giá "provisional" | Báo giá bằng rate cũ, NCC đòi giá mới lúc confirm | Rate supersede + drift badge + `rate.superseded` event (15.3/15.5) |
| **Overbooking khách sạn** | KS "walk" khách sang KS khác, thường tệ hơn | Khách VIP nổi giận | Quy tắc "walk chỉ sang tương đương hoặc cao hơn, KS chịu chi phí" phải nằm trong hợp đồng → ghi vào supplier policy + Incident playbook |

### 1.5 Định vị chiến lược cho "TourPlan Simple for DMC Startup" — 3 lựa chọn

Founder cần chọn một trọng tâm để mọi quyết định tính năng nhất quán. Ba định vị dưới đây không
loại trừ nhau về lâu dài, nhưng **trong 12 tháng đầu chỉ chọn một**.

| | Option A — **Ops Excellence DMC** | Option B — **Knowledge-Moat DMC** | Option C — **Agent-Platform DMC** |
| :-- | :-- | :-- | :-- |
| Lời hứa với agent | "Không bao giờ sai, không bao giờ chậm, có chuyện gì chúng tôi lo" | "Chúng tôi biết những thứ không ai biết" | "Agent tự tra cứu, tự dựng, tự xem tác động amendment 24/7" |
| Tính năng mũi nhọn | Ops board + Trip Diary + Incident + AP/margin | Destination Knowledge Base + Media Vault + insider tips trong proposal | Partner Portal self-service + Deep-Query + Amendment quote |
| Điều kiện dữ liệu | Catalog + booking chạy đủ 1 chu kỳ | ≥200 knowledge cards đã kiểm chứng, ≥500 ảnh có bản quyền | Catalog rất giàu + policy chuẩn hóa 100% NCC + exposure matrix |
| Rủi ro chính | Trở thành "Tourplan bản nhỏ", khó khác biệt về marketing | Tri thức khó thu thập, cần văn hóa ghi chép | Agent dùng để **so giá** với DMC khác; lộ dữ liệu nếu phân lớp sai |
| Thời gian thấy kết quả | 3–6 tháng | 6–12 tháng | 9–18 tháng |
| Phù hợp khi | Team ops mỏng, đang mất tiền vì lỗi vận hành | Có senior guide/sale nhiều năm sẵn sàng "đổ" tri thức | Đã có ≥15 agent hoạt động đều, muốn scale mà không tăng sale |

**Khuyến nghị**: **A trước, B chạy song song ở chế độ "thu thập", C ở Phase 3**. Lý do: (1) Plan
15.x đã trả trước 70% của A — chi phí hoàn thành thấp nhất; (2) B chỉ có giá trị khi tích lũy, nên
phải bắt đầu thu thập ngay dù chưa "bán" được; (3) C phụ thuộc vào cả A (policy chuẩn) lẫn B (tri
thức để trả lời) — làm C trước là xây cổng mà không có kho.

---

## 2. B2B PARTNER DEEP-QUERY PORTAL: NGHIỆP VỤ TRA CỨU CHUYÊN SÂU & KIẾN TRÚC KHO DỮ LIỆU ĐỘC QUYỀN

### 2.1 Travel Designer quốc tế thực sự hỏi gì

Thống kê từ hộp thư của một DMC inbound điển hình: **60–70% email từ agent không phải yêu cầu báo
giá**, mà là câu hỏi nghiệp vụ để agent tự tin bán cho khách của họ. Mỗi câu hỏi mất trung bình
20–90 phút của sale (tra hỏi ops, gọi guide, đọc lại PDF NCC) và trả lời sau 1–3 ngày vì lệch múi
giờ. Đây là nút thắt lớn nhất của tốc độ phản hồi và cũng là kho tri thức đang bị **bốc hơi** — câu
trả lời nằm trong email, không quay về hệ thống.

Phân loại 7 nhóm câu hỏi thực tế (ví dụ là câu hỏi thật hoặc rất gần thật):

| Nhóm | Ví dụ câu hỏi | Ai trong DMC biết câu trả lời | Nguồn dữ liệu cần để trả lời tự tin |
| :-- | :-- | :-- | :-- |
| **1. Khả thi logistics** | "Xe 16 chỗ có vào được phố cổ Hội An lúc 16h không?" · "Từ Hà Nội đi Hà Giang một ngày có quá dài với trẻ 6 tuổi?" · "Mùa mưa tháng 9 đường Pù Luông có đi được xe 7 chỗ?" | Ops + driver kỳ cựu | Quy tắc giao thông theo điểm đến, thời gian di chuyển thực tế theo mùa, giới hạn phương tiện theo cung đường |
| **2. Phù hợp hồ sơ khách** | "Cung trekking này có hợp người 65 tuổi khớp gối yếu?" · "Resort này có phù hợp gia đình có bé 2 tuổi (hồ bơi trẻ em, cũi)?" · "Tàu Hạ Long này có thang máy?" | Sale senior + site inspection | Thuộc tính suitability của từng dịch vụ (độ khó, độ cao, accessibility, family facilities) đã kiểm chứng |
| **3. Ăn uống / tôn giáo / y tế** | "Khách ăn chay nghiêm ngặt (không hành tỏi) tại resort X được phục vụ thế nào?" · "Có nhà hàng halal ở Ninh Bình?" · "Khách cần tiêm insulin, khách sạn có tủ lạnh mini?" | Ops + guide | Năng lực dietary của nhà hàng/KS, kinh nghiệm thực tế từ tour trước |
| **4. Mùa vụ & thời tiết** | "Tháng 10 Sapa có ruộng vàng?" · "Tháng 3 Phú Quốc có sứa?" · "Hạ Long tháng 8 rủi ro bão bao nhiêu?" | Sale + ops | Lịch mùa vụ theo điểm đến, tỷ lệ hủy tàu theo tháng (từ nhật ký sự cố) |
| **5. Chi tiết chỗ ở** | "Phòng Deluxe Sea View có thực sự nhìn thấy biển hay bị cây che?" · "Villa 2 phòng ngủ có cửa thông?" · "Late checkout 16h có thương lượng được không?" | Site inspection + ops | Ghi chú site inspection, ảnh thật do nhân viên chụp, lịch sử thương lượng |
| **6. Điều khoản & chính sách** | "Nếu khách hủy trước 20 ngày thì phạt bao nhiêu?" · "Trẻ 11 tuổi tính giá thế nào?" · "Có bắt buộc gala dinner 31/12?" | Sale (đọc PDF NCC) | Policy có cấu trúc trên supplier/rate (đã có) — **phải lọc: chỉ hiện điều khoản đã "chuyển" sang agent, không hiện điều khoản NCC gốc** |
| **7. Trải nghiệm độc bản** | "Có thể gặp nghệ nhân làm nón làng Chuông tại nhà không?" · "Có chỗ nào ngắm bình minh vịnh Lan Hạ mà không có tàu khác?" | Senior sale, guide giỏi, MD | Destination Knowledge Base (insider tips) — **tài sản độc quyền**, chỉ mở một phần |

Ba nhận xét quyết định thiết kế:

1. **Nhóm 1–5 là câu hỏi có đáp án đúng/sai** — trả lời sai gây thiệt hại thật (khách kéo vali
   dưới mưa, người già kiệt sức). Câu trả lời phải có **nguồn và ngày kiểm chứng**; không có
   nguồn → hệ thống phải nói "chưa kiểm chứng, đang hỏi chuyên gia" chứ không đoán.
2. **Nhóm 6 là vùng nhạy cảm nhất về dữ liệu**: điều khoản NCC gốc (cọc 30%, phạt theo giá NET)
   khác điều khoản DMC chuyển cho agent (cọc 50%, phạt theo giá bán). Portal phải trả lời bằng
   **điều khoản của DMC**, không bao giờ để lộ điều khoản NCC.
3. **Nhóm 7 là moat**: chỉ mở dạng "teaser" (có/không, mô tả 1 câu), chi tiết chỉ xuất hiện trong
   proposal đã bán. Mở toàn bộ = tặng đối thủ.

### 2.2 Vì sao "chatbot bách khoa" thất bại với agent chuyên nghiệp

| Lý do | Hệ quả | Thiết kế đúng |
| :-- | :-- | :-- |
| Agent đã biết Wikipedia; họ hỏi vì **cần người đã đi thực địa** | Chatbot trả lời chung chung → agent mất niềm tin sau 2 câu, quay về email | Mỗi câu trả lời phải hiện: *ai/khi nào kiểm chứng*, *áp dụng cho dịch vụ nào trong catalog*, *điều kiện* |
| Sai một lần về khả thi = mất agent | Không thể chấp nhận "đúng 90%" | Ba tầng trả lời (§2.3): Fact đã kiểm chứng → Suy luận có điều kiện → Chuyển người |
| Agent cần **hành động tiếp theo**, không cần văn | "Có, và chúng tôi có thể thêm dịch vụ X vào ngày 5 với giá Y" | Câu trả lời gắn với hành động: thêm vào proposal, yêu cầu báo giá, đặt câu hỏi cho chuyên gia |
| Lộ dữ liệu nhạy cảm chỉ một lần là thảm họa | Giá NET, tên contact NCC rơi vào tay agent → agent làm việc trực tiếp với NCC hoặc ép giá | Ma trận phơi nhiễm 4 lớp thi hành **ở tầng dữ liệu**, không ở tầng "prompt xin AI đừng nói" |

### 2.3 Cơ chế nghiệp vụ: ba tầng câu trả lời

Mọi câu hỏi đi qua đúng một trong ba tầng; tầng nào cũng phải để lại **dấu vết quay về kho tri thức**.

```text
Câu hỏi của agent
      │
      ▼
[Tầng 1 — FACT ĐÃ KIỂM CHỨNG]   Có knowledge card / thuộc tính catalog khớp, còn hiệu lực,
      │ có                       exposure ∈ Partner → trả lời ngay, kèm nguồn + ngày kiểm chứng
      │ không
      ▼
[Tầng 2 — SUY LUẬN CÓ ĐIỀU KIỆN] Có dữ liệu liên quan (thời gian di chuyển, độ khó, mùa vụ)
      │ có                       → trả lời dạng "Thường thì X, với điều kiện Y; chúng tôi sẽ xác
      │                            nhận trong ≤4h" + tự tạo ticket cho chuyên gia
      │ không
      ▼
[Tầng 3 — CHUYỂN NGƯỜI]          Ticket "Ask our destination expert" với SLA hiển thị (4h / 24h),
                                 người trả lời → câu trả lời được **đề xuất lưu thành knowledge
                                 card** (một cú bấm) → lần sau thành Tầng 1
```

Nguyên tắc vận hành:

- **Tầng 1 không cần AI**: đây là tra cứu có cấu trúc. AI chỉ giúp *hiểu câu hỏi* và *diễn đạt* câu
  trả lời từ card — nội dung sự thật đến từ card, không từ mô hình.
- **Tầng 2 bắt buộc có "điều kiện" và "sẽ xác nhận"** — không bao giờ là câu khẳng định trần.
- **Tầng 3 là nơi tri thức sinh ra**. KPI quan trọng nhất của portal không phải "AI trả lời được bao
  nhiêu %" mà là **tỷ lệ ticket Tầng 3 được chuyển thành card** (mục tiêu ≥60%). Sau 6 tháng, tỷ lệ
  Tầng 1 tự tăng.

### 2.4 Ranh giới dữ liệu: Ma trận phơi nhiễm 4 lớp (Data Exposure Matrix)

Đây là điều kiện tiên quyết để mở bất kỳ dữ liệu nào cho agent. Nguyên tắc: **mỗi trường dữ liệu có
một lớp phơi nhiễm; lớp được thi hành ở tầng truy vấn dữ liệu** (agent chỉ đọc qua "khung nhìn
partner" không chứa trường Restricted), không phải bằng lời dặn AI.

| Lớp | Ai thấy | Ví dụ trường | Quy tắc |
| :-- | :-- | :-- | :-- |
| **L0 Public** | Bất kỳ ai (brochure công khai) | Tên điểm đến, mô tả marketing, ảnh đã duyệt công khai, giá bán "from" nếu DMC muốn | Đã có trong publication pipeline |
| **L1 Partner** | Agent đã đăng nhập, theo tier | Tên KS/dịch vụ, hạng sao, thuộc tính suitability, **điều khoản DMC→agent** (hủy, cọc, child policy của DMC), mùa vụ, thời gian di chuyển, giá bán theo tier của agent, insider tip dạng teaser, ảnh L1 | Tier `Preferred/VIP` thấy thêm: giá bán tốt hơn, tip chi tiết hơn, ưu tiên SLA |
| **L2 Internal** | Nhân viên DMC | Ghi chú site inspection thô, điểm tín nhiệm NCC, lịch sử sự cố, tên guide/driver, tip chi tiết, phương án B | Portal **không bao giờ** đọc lớp này; nhân viên dùng qua workspace |
| **L3 Restricted** | Ban giám đốc + kế toán | Giá NET NCC, markup, chiết khấu/commission, hoa hồng agent, danh bạ ops NCC, điều khoản NCC gốc, hóa đơn, biên lợi nhuận | Không xuất hiện trong bất kỳ khung nhìn nào ngoài finance/costing; **không nằm trong bất kỳ tài liệu nào đưa vào AI phục vụ agent** |

Ánh xạ vào nền tảng hiện có (để thấy tính khả thi, không phải spec):

- `rates.cost_*` / `rate_price_lines` cost → **L3**; sell tính từ costing → **L1 theo tier**.
- `suppliers.contact_*`, `payment_terms_json`, `cancellation_policy_json` gốc → **L3**. Cần thêm một
  bộ **"điều khoản DMC chuyển cho agent"** (Partner Terms) ở cấp DMC hoặc cấp sản phẩm → **L1**.
- `suppliers.quality_tier`, `preferred_status`, Supplier Trust Score (mới) → **L2**.
- `partner_profiles.tier` (Preferred/Standard/VIP) đã có — dùng làm khóa phân quyền L1.
- Knowledge card (mới) có trường `exposure ∈ {L0, L1, L2, L3}` bắt buộc khi tạo; mặc định **L2**
  (an toàn), phải chủ động hạ xuống L1.

Ba kiểm soát bổ sung (nghiệp vụ, không phải kỹ thuật):

1. **Nhật ký truy vấn của agent** — ai hỏi gì, khi nào, được trả lời từ card nào. Vừa để audit rò rỉ,
   vừa là tín hiệu thương mại (agent hỏi nhiều về Hà Giang → chuẩn bị sản phẩm).
2. **Quy tắc "không liệt kê toàn bộ"** — portal trả lời câu hỏi, không cho xuất danh sách toàn bộ
   NCC/giá theo điểm đến (chống agent "cào" catalog để đi trực tiếp).
3. **Watermark tri thức** — insider tip L1 luôn kèm "theo kinh nghiệm điều hành của [DMC]" và không
   nêu tên/liên hệ nghệ nhân, chủ thuyền, chủ homestay; chi tiết liên hệ luôn L2/L3.

### 2.5 Phương án triển khai — Founder chọn

| | Option A — **Curated FAQ + Expert Desk** (thực dụng) | Option B — **Structured Knowledge Base + Deep-Query có AI** (số hóa sâu) | Option C — **Full Agent Portal self-service** |
| :-- | :-- | :-- | :-- |
| Mô tả | Cổng đăng nhập cho agent; FAQ theo điểm đến do sale biên soạn; form "Ask expert" có SLA timer; câu trả lời hay được ghim thành FAQ | Như A + knowledge card có cấu trúc (loại, điểm đến, dịch vụ, mùa, exposure, nguồn, ngày kiểm chứng) + trợ lý tra cứu AI đọc card L1 và trả lời có trích dẫn, tự mở ticket khi không đủ dữ liệu | Như B + agent tự dựng lịch trình từ catalog L1, xem giá theo tier, gửi yêu cầu amendment và thấy tác động giá/phạt tức thì |
| Chi phí xây | Thấp (2–4 tuần, chủ yếu nội dung) | Trung bình (6–10 tuần, cần schema card + AI retrieval + exposure filter) | Cao (4–6 tháng, cần catalog + partner terms chuẩn 100%) |
| Chi phí vận hành | Sale duy trì FAQ thủ công; dễ lỗi thời | Card có ngày hết hạn, quy trình kiểm chứng; AI giảm 50–70% thời gian trả lời | Cần support cho agent, rủi ro agent dùng để so giá |
| Giá trị | Giảm 30% email lặp; SLA nhìn thấy được | Giảm 60–70% thời gian trả lời; tri thức tích lũy thành tài sản; nền cho Phase 3 | Agent "sống" trong hệ của DMC; chi phí sale/file giảm mạnh |
| Rủi ro | FAQ cũ → trả lời sai | AI diễn đạt sai card (giảm bằng trích dẫn nguyên văn + ba tầng) | Lộ dữ liệu nếu exposure sai; agent bỏ qua sale |
| Khi nào chọn | Ngay Phase 1 nếu chưa có card | Phase 2 khi có ≥100 card kiểm chứng | Phase 3 |

**Khuyến nghị**: **A ngay (Phase 1) với schema card của B ẩn bên dưới** — tức FAQ ngay từ đầu được
nhập dưới dạng card có `exposure` + `verified_by/at`, để khi bật AI ở Phase 2 không phải nhập lại.

### 2.6 Đề xuất tính năng cụ thể cho Partner Portal

| Tính năng | Giải quyết bài toán | Phase | Ghi chú nghiệp vụ |
| :-- | :-- | :-- | :-- |
| **Query Inbox với SLA timer** | Agent thấy câu hỏi của mình đang ở đâu, còn bao lâu; DMC thấy hàng đợi theo tier agent | 1 | SLA theo tier: VIP 2h / Preferred 4h / Standard 24h (giờ làm việc VN, hiển thị theo múi giờ agent) |
| **Feasibility Checker (tra cứu khả thi)** | Nhóm câu hỏi 1–2: chọn điểm đi/đến + loại xe + tháng + hồ sơ khách → hệ thống trả "khả thi / có điều kiện / không" từ card + quy tắc | 2 | Chỉ trả lời khi có card kiểm chứng ≤12 tháng; ngược lại tạo ticket |
| **Partner Terms Card** | Nhóm 6: điều khoản DMC→agent theo sản phẩm/điểm đến, tự sinh từ policy của DMC (không phải NCC) | 1–2 | Cần Founder chốt chính sách chuẩn của DMC (cọc, hủy, child) — hiện chỉ có policy NCC |
| **Knowledge Cards có trích dẫn** | Nhóm 3–5, 7 (teaser) | 2 | Mỗi card: câu trả lời ≤120 từ, ảnh (nếu có), nguồn, ngày kiểm chứng, hết hạn |
| **Proposal Sharing & Comment** | Agent xem interactive brochure, comment trực tiếp trên ngày/dịch vụ thay vì email | 1 | Đã có brochure; thêm luồng comment gắn vào ngày → thành amendment request |
| **Amendment Request + Impact Preview** | Agent gửi "đổi KS ngày 4", hệ thống hiện tác động giá & phạt (tính từ snapshot) trước khi sale xác nhận | 2–3 | Đọc từ booking lines; sale vẫn là người quyết |
| **Query → Knowledge Loop** | Nút "Lưu thành card" trên mỗi câu trả lời của chuyên gia | 1 | KPI ≥60% ticket thành card |
| **Agent Activity Signal** | Dashboard nội bộ: agent nào hỏi gì nhiều, chưa gửi file từ khi nào | 2 | Đầu vào cho Agent Profitability Matrix (§3.6) |

### 2.7 Chỉ số đo thành công của Portal

| Chỉ số | Mục tiêu 6 tháng | Vì sao quan trọng |
| :-- | :-- | :-- |
| Thời gian trả lời trung vị (giờ làm việc) | ≤2h (VIP/Preferred), ≤8h (Standard) | Kỳ vọng #1 của agent |
| Tỷ lệ trả lời ở Tầng 1 (fact) | 30% → 60% | Đo tốc độ tích lũy tri thức |
| Tỷ lệ ticket Tầng 3 chuyển thành card | ≥60% | Moat có lớn lên không |
| Tỷ lệ câu hỏi dẫn tới yêu cầu báo giá trong 14 ngày | ≥25% | Portal có bán được không |
| Số sự cố rò rỉ dữ liệu L2/L3 | 0 | Điều kiện sống còn |
| Email hỏi đáp ngoài portal (per agent/tháng) | Giảm ≥50% | Agent có thật sự dùng không |

---

## 3. PHÂN TÍCH CHUYÊN SÂU 6 PHÒNG BAN: NGHIỆP VỤ THỰC TẾ & ĐỊNH HƯỚNG TÍNH NĂNG

Mỗi mục đi theo (a) Bản chất & thách thức → (b) Phương án chiến lược → (c) Tính năng cụ thể →
(d) Chỉ số đo. Tính năng đánh dấu **[có]** đã tồn tại trên nền tảng, **[mở rộng]** là bổ sung vào
module có sẵn, **[mới]** là module mới cần spec riêng.

### 3.1 Sale / Travel Designer — Tối ưu Win Rate, nghệ thuật upsell, quản trị amendment

#### (a) Bản chất nghiệp vụ & thách thức thực tế

**Phễu bán hàng B2B của DMC** và số liệu điển hình:

| Bước | Tỷ lệ điển hình | Điểm rơi |
| :-- | :-- | :-- |
| Yêu cầu nhận → proposal gửi | 90–95% (5–10% bị từ chối vì không hợp/không kịp) | Yêu cầu bị "chìm" trong hộp thư cá nhân |
| Proposal → agent phản hồi | 60–75% | Proposal quá dài hoặc đến chậm hơn đối thủ |
| Phản hồi → chốt (sau 2–4 vòng sửa) | 35–55% | Sửa đổi chậm, giá đội lên khi thêm phụ thu "quên" |
| **Win rate tổng** | **25–40%** | Mục tiêu lên 45%+ nhờ tốc độ và độ chính xác |

Ba thách thức thực địa:

1. **Thời gian ra proposal đầu tiên** là biến số dự báo win rate mạnh nhất. Với sale mới, dựng một
   file 12 ngày mất 4–8 giờ (chọn dịch vụ, tra giá, tính, viết mô tả). Với senior, 2–3 giờ nhưng senior
   là cổ chai. Agent Âu–Mỹ gửi yêu cầu lúc cuối ngày của họ = sáng Việt Nam; DMC trả lời trong ngày
   làm việc VN = agent nhận khi mở máy sáng hôm sau — "24h" thực ra là cửa sổ duy nhất.
2. **Upsell trải nghiệm cao cấp** là nơi biên lợi nhuận tốt nhất (60–80% biên trên dịch vụ độc quyền
   so với 15–20% trên phòng khách sạn) nhưng phụ thuộc hoàn toàn vào việc sale *nhớ* đề xuất đúng thứ
   đúng lúc: bữa tối riêng trên bãi biển cho kỷ niệm ngày cưới, lớp nấu ăn với nghệ nhân, thủy phi cơ
   Hạ Long, ngắm bình minh bằng thuyền riêng. Không có "kho upsell theo bối cảnh" thì upsell phụ thuộc
   vào cá nhân.
3. **Amendment** — trung bình 3–5 phiên bản trước khi chốt và 1–2 sau khi chốt (đổi ngày bay, thêm
   1 khách, nâng hạng KS, bỏ 1 đêm). Lỗi kinh điển: (i) không biết bản nào agent đã đồng ý; (ii) giá
   ở bản mới quên phụ thu đã có ở bản cũ; (iii) sau khi đặt cọc, đổi KS làm hỏng chứng từ kế toán vì
   sửa đè vào dòng đã book. Nền tảng đã xử lý (iii) bằng nguyên tắc "hủy dòng + thêm dòng"; (i) và
   (ii) cần quản lý phiên bản ở tầng proposal.

#### (b) Định hướng chiến lược — Options

| | Option A — **Fast-Response Desk** (thực dụng) | Option B — **Scenario Engine + Interactive Proposal** (số hóa sâu) |
| :-- | :-- | :-- |
| Cốt lõi | Thư viện lịch trình mẫu (15–25 khung tour theo archetype: gia đình, honeymoon, văn hóa, biển) + costing thủ công từ catalog + template proposal | Costing một lần, sinh 3 kịch bản hạng sao tự động; AI dựng dàn dịch vụ từ brief; proposal tương tác có comment; phiên bản có so sánh |
| Chi phí | Thấp — chủ yếu nội dung mẫu; nền tảng đã có costing + brochure | Trung bình — cần "swap theo tier" trong catalog, Drafter qua exit gate, comment trên brochure |
| Kết quả kỳ vọng | Proposal đầu tiên: 8h → 3h; win rate +3–5 điểm | Proposal đầu tiên: → <1h; win rate +8–12 điểm; upsell +10–15% biên |
| Rủi ro | Mẫu làm proposal "giống nhau", mất chất may đo | Phụ thuộc catalog giàu; kịch bản tự động sai nếu `quality_tier` gán sai |
| Khi chọn | Catalog <100 sản phẩm có giá | Catalog ≥200 sản phẩm có giá active, ≥3 tier mỗi điểm đến chính |

**Khuyến nghị**: A trong 60 ngày đầu (thư viện mẫu là *dữ liệu* cho B), chuyển B khi catalog đủ.

#### (c) Đề xuất tính năng hệ thống

| Tính năng | Trạng thái | Bài toán giải quyết | Mô tả nghiệp vụ |
| :-- | :-- | :-- | :-- |
| **Costing sheet bóc tách dòng** | [có] 15.4 | Giá đúng từng dịch vụ, markup tách bạch | Giữ nguyên; bổ sung "checklist ngày đặc biệt" (Tết, 24/12, 31/12, lễ hội) tự bật cảnh báo khi ngày dịch vụ rơi vào |
| **Itinerary Template Library** | [mới] | Rút thời gian dựng dàn | 15–25 khung tour theo archetype × vùng; mỗi khung là costing sheet mẫu có dịch vụ + ghi chú pacing; "clone rồi may đo" |
| **Multi-Scenario Pricing (3★/4★/5★)** | [mở rộng] 15.2/15.4 | Agent hỏi "cho tôi 2 phương án" | Từ một sheet, hệ thống tạo biến thể bằng cách thay dịch vụ lưu trú cùng điểm đến theo `quality_tier`; các dòng không phải lưu trú giữ nguyên; sale chỉ duyệt/đổi từng chỗ. Kết quả: 2–3 bảng giá song song trên một proposal |
| **AI Service Drafter** | [có, chưa qua exit gate] 15.7 | Dựng dàn dịch vụ từ brief văn xuôi | Đưa qua exit gate với corpus thật (§5.8) |
| **Interactive Proposal + Comment theo ngày** | [có brochure] 16.x + [mở rộng] | Agent phản hồi đúng chỗ, giảm vòng email | Comment gắn vào ngày/dịch vụ; mỗi comment có thể thành amendment request |
| **Proposal Version Ledger** | [mở rộng] costing_applications + quotation revision | "Bản nào agent đã đồng ý?" | Mỗi lần gửi agent = 1 phiên bản đánh số, khóa giá + hiệu lực; màn so sánh 2 phiên bản (dịch vụ thêm/bớt, chênh giá); bản "agent accepted" được đánh dấu và là bản duy nhất được chuyển sang booking |
| **Quote Validity & Rate Expiry Guard** | [mở rộng] 15.3/15.5 drift | Rate hết hạn / bị thay giữa chừng | Cảnh báo khi: rate dùng trong sheet sẽ hết hạn trước ngày dịch vụ; rate bị supersede sau khi gửi proposal (đã có drift badge) → sale phải "tái xác nhận giá" trước khi chuyển booking |
| **Upsell Prompt Library** | [mới, nội dung] | Upsell phụ thuộc cá nhân | Thư viện gợi ý upsell theo bối cảnh (điểm đến × dịp × archetype): "honeymoon + Hội An → bữa tối riêng bên sông + chụp ảnh áo dài"; hiện gợi ý trong costing khi thêm ngày ở điểm đến đó; gắn với sản phẩm trong catalog có giá |
| **Amendment Quote (sau cọc)** | [có] 15.6 + [mở rộng] | "Đổi được không, phạt bao nhiêu?" | Sale chọn dòng cần đổi → hệ thống tính phạt từ tiers đóng băng + giá dịch vụ mới → sinh "Amendment Quote" gửi agent → khi agent đồng ý mới thực thi hủy/thêm dòng |
| **Response SLA Board** | [mới] | Yêu cầu chìm | Hàng đợi yêu cầu/câu hỏi theo tier agent với đồng hồ SLA; escalate cho trưởng nhóm khi quá 50% SLA chưa ai nhận |

#### (d) Chỉ số đo

| Chỉ số | Hiện trạng ước tính | Mục tiêu 6 tháng |
| :-- | :-- | :-- |
| Thời gian đến proposal đầu tiên (trung vị) | 8–24h | ≤4h (Option A) / ≤1h (Option B) |
| Win rate | 25–35% | 40–45% |
| Số phiên bản trước chốt | 3–5 | ≤3 |
| Tỷ lệ file có sửa giá sau khi agent đồng ý | 10–15% | <3% |
| Tỷ trọng biên từ upsell trải nghiệm | 10–15% | 20–25% |

### 3.2 Operator / Điều hành & Vận hành thực địa

#### (a) Bản chất nghiệp vụ & thách thức thực tế

Điều hành là nơi DMC **mất tiền thật** và **mất agent thật**. Ba khối việc:

1. **Booking Dispatch & Confirmation Chasing**. Sau khi nhận cọc, operator gửi yêu cầu tới 10–25
   NCC cho một file 12 ngày (KS, xe, guide, tàu, vé, nhà hàng). Mỗi NCC trả lời theo kênh riêng
   (email, Zalo, WhatsApp, điện thoại), thời gian khác nhau (KS 24–72h, xe 2–24h, tàu Hạ Long
   1–3 ngày mùa cao). Operator phải: theo dõi cái nào chưa trả lời, cái nào "provisional" chờ cọc,
   cái nào có hạn release. Thực tế: **30–40% thời gian là đuổi xác nhận**, và lỗi thường gặp là
   "tưởng đã confirm" (NCC trả lời "noted" chứ không phải "confirmed").
2. **Quản trị rủi ro chuyến đi**. Ma trận rủi ro thực địa cao cấp:

   | Rủi ro | Tần suất | Tác động | Phương án B chuẩn |
   | :-- | :-- | :-- | :-- |
   | Chuyến bay nội địa hoãn/hủy | Cao (mùa mưa, sương mù Hà Nội/Sapa) | Lỡ tàu Hạ Long, lỡ đêm KS | Kịch bản "delay > 2h": xe chờ có phí, đổi ngày tàu, KS thay thế cùng hạng |
   | Cảng cấm tàu (bão) | Trung bình, theo mùa | Mất đêm tàu, khách thất vọng | Đổi sang du thuyền ngày/KS vịnh + bù đắp; điều khoản hoàn tiền tàu phải nằm trong policy |
   | KS overbooked/walk | Thấp nhưng nặng | Khách VIP nổi giận | Quy tắc hợp đồng: walk chỉ lên hạng cao hơn, KS chịu chi phí + 1 bữa tối |
   | Guide không hợp gu khách | Trung bình | Toàn bộ trải nghiệm xấu đi dù dịch vụ tốt | Đổi guide trong 24h; hồ sơ guide (ngôn ngữ, phong cách, độ tuổi hợp) |
   | Xe hỏng/đường cấm/mưa lũ | Trung bình theo vùng | Trễ lịch, thêm chi phí | Danh sách xe dự phòng theo vùng; knowledge về đường |
   | Y tế (ngộ độc, tai nạn) | Thấp | Nghiêm trọng nhất | Escalation tức thì, bệnh viện quốc tế theo vùng, bảo hiểm |
   | Sự cố dịch vụ nhỏ (phòng ồn, bữa ăn dở) | Cao | Tích tụ thành phàn nàn lớn | Guide ghi nhận & xử lý trong ngày |

3. **Amendment không làm rối kế toán**. Sau cọc, mọi thay đổi phải để lại chứng từ đúng: dịch vụ
   cũ bị hủy (kèm phạt nếu có), dịch vụ mới có voucher mới; hóa đơn NCC sau này khớp theo voucher.
   Nền tảng đã có nguyên tắc này; vấn đề còn lại là **quy trình người**: operator phải làm đúng
   trình tự thay vì "sửa tay cho nhanh".

Thách thức tổ chức: DMC startup thường **không có nhật ký chuyến đi**. Ngày 5 khách đổi nhà hàng,
ngày 7 thêm xe đi bệnh viện, ngày 9 bỏ vé — tất cả nằm trong đầu guide và tin nhắn Zalo. Đến khi
đối soát hóa đơn NCC (2–4 tuần sau), không ai nhớ. Đây là **nguồn rò rỉ biên lợi nhuận số 1** sau
lỗi báo giá.

#### (b) Định hướng chiến lược — Options

| | Option A — **Deadline-Driven Board + Dispatch thủ công có mẫu** | Option B — **Auto-Dispatch + Confirmation Parsing + Trip Diary số** | Option C — **Supplier Portal** |
| :-- | :-- | :-- | :-- |
| Cốt lõi | Ops board sắp theo hạn (đã có); mẫu email/Zalo yêu cầu NCC sinh từ snapshot; operator copy-gửi và cập nhật trạng thái tay; nhật ký chuyến đi là form đơn giản guide điền hàng ngày | Hệ thống gửi yêu cầu/voucher tự động qua email, ghi nhật ký gửi; phản hồi NCC được đọc bán tự động (AI phân loại confirmed/provisional/declined, người duyệt); Trip Diary có cấu trúc gắn từng dòng dịch vụ; phát sinh ghi thành dòng chờ đối soát | NCC đăng nhập xác nhận trực tiếp, cập nhật availability |
| Chi phí | Thấp | Trung bình | Cao, và NCC Việt Nam **hiếm khi dùng** portal của DMC nhỏ |
| Kết quả | Không cháy hạn; giảm 30% thời gian đuổi | Giảm 60% thời gian đuổi; nhật ký đầy đủ → đối soát AP chính xác | Chỉ hiệu quả với 5–10 NCC lớn |
| Rủi ro | Vẫn phụ thuộc kỷ luật operator | Gửi tự động sai → NCC nhận thông tin sai; phải có gate "xem trước rồi gửi" | NCC không dùng |
| Khi chọn | Ngay | Sau 1 mùa dùng A (đã có mẫu chuẩn) | Không khuyến nghị trước 24 tháng |

**Khuyến nghị**: A → B. Không làm C.

#### (c) Đề xuất tính năng hệ thống

| Tính năng | Trạng thái | Bài toán | Mô tả nghiệp vụ |
| :-- | :-- | :-- | :-- |
| **Ops Board deadline-driven** | [có] 15.6 | "Hạn nào sắp cháy?" | Giữ; bổ sung khung nhìn **Kanban theo trạng thái** (To request / Requested / Provisional / Confirmed / Delivered / Cancelled) song song khung nhìn theo hạn; bộ lọc "theo NCC" để gọi một cuộc điện thoại chốt nhiều dịch vụ |
| **Dispatch Templates & Dispatch Log** | [mở rộng] 15.12 blueprint | Gửi yêu cầu/voucher nhất quán | Mẫu yêu cầu NCC (song ngữ) sinh từ snapshot: dịch vụ, ngày, số khách, rooming, yêu cầu đặc biệt, hạn trả lời; mẫu voucher cho khách/guide; mọi lần gửi có log (ai, khi nào, kênh) |
| **Confirmation Chasing Queue** | [mới] | Đuổi xác nhận | Hàng đợi tự động: dịch vụ "requested" quá X giờ (theo loại NCC) → nhắc operator; "provisional" sắp đến hạn cọc → nhắc; ghi lại số lần nhắc (đầu vào Supplier Trust Score) |
| **Trip Diary (Nhật ký chuyến đi)** | [mới] | Đối soát & recovery | Mỗi booking có nhật ký theo ngày: dịch vụ thực tế đã diễn ra (mặc định từ booking lines), sai lệch (đổi/bỏ/thêm), chi phí phát sinh (số tiền, NCC, lý do, ai duyệt), điểm hài lòng trong ngày, ghi chú guide. Dòng phát sinh tự thành "dòng chờ đối soát" cho AP (line_type `adjustment`) |
| **Incident Log & Playbook** | [mới] (chi tiết §3.5) | Xử lý rủi ro | Ghi nhận sự cố với mức độ, chủ sở hữu, SLA; playbook theo loại (bão cấm tàu, bay hoãn, walk KS) có sẵn phương án B kèm giá tham khảo |
| **Guide/Driver Assignment & Briefing Pack** | [mới] | Guide không hợp gu, thiếu thông tin | Hồ sơ guide (ngôn ngữ, phong cách, kinh nghiệm, điểm feedback); gán theo file; Briefing Pack tự sinh từ snapshot: lịch trình, rooming, dietary/medical flags, sở thích, số liên hệ NCC, voucher — gửi guide 48h trước |
| **Day-of-Travel Checklist** | [mới] | Lỗi ngày khởi hành | Checklist tự động 72h/24h trước: vé máy bay, xe đón, tên bảng đón, KS đêm đầu confirmed, SIM/WhatsApp khách, tiền tip guide chuẩn bị |
| **Amendment Workflow (post-deposit)** | [có] 15.6 | Kế toán không loạn | Bắt buộc đi qua "Amendment Quote" (§3.1) → hủy dòng cũ (phạt ghi nhận) → thêm dòng mới → voucher mới → thông báo NCC/guide; cấm sửa đè |
| **Cancellation Penalty Simulator** | [mở rộng] 15.6 | Trả lời agent nhanh khi hủy | Chọn ngày hủy giả định → tổng phạt NCC (từ tiers đóng băng) + phạt DMC→agent (từ Partner Terms) → chênh lệch DMC chịu |

#### (d) Chỉ số đo

| Chỉ số | Mục tiêu |
| :-- | :-- |
| Dịch vụ cháy hạn release/cọc mà không có cảnh báo trước 7 ngày | 0 |
| Thời gian operator dành cho đuổi xác nhận | Giảm 50% |
| % booking có Trip Diary đủ mọi ngày | ≥90% |
| Phát sinh không được ghi trong ngày phát sinh | <10% |
| Sự cố ghi nhận ≤15 phút từ khi guide biết | ≥80% |

### 3.3 Dữ liệu NCC, Khảo sát thực địa, Feedback & Crawler — Chu trình khép kín dữ liệu

#### (a) Bản chất nghiệp vụ & thách thức thực tế

DMC cao cấp làm việc với **150–400 NCC** (50–120 KS/resort, 20–40 nhà xe, 10–20 tàu, 30–60 nhà
hàng, 30–80 guide, còn lại vé/trải nghiệm). Ba dòng dữ liệu về NCC:

1. **Giá & điều khoản (Rates)** — mỗi năm 1–2 bảng giá chính (contract rate tháng 10–9 hoặc theo
   năm dương lịch) + cập nhật giữa mùa + promo. Định dạng: PDF (60%), Excel (25%), email/Zalo thuần
   văn bản (15%). Nhập tay một bảng giá KS 5 sao (8 loại phòng × 4 mùa × 3 occupancy + phụ thu + policy)
   mất 45–90 phút và **sai 5–10%** (nhầm mùa, nhầm SGL/DBL, quên gala). Đây là nút thắt lớn nhất
   khiến catalog nghèo — và catalog nghèo làm mọi tính năng phía trên (Drafter, scenario) vô dụng.
   Nền tảng đã có Ingestion Co-Pilot cho **văn bản**; PDF/Excel còn phải copy-paste tay.
2. **Chất lượng thực tế (Quality)** — hai nguồn: *site inspection* (nhân viên đi khảo sát, 1–2
   lần/năm mỗi KS chính) và *feedback sau tour* (khách qua agent, guide, operator). Thực tế startup:
   site inspection không có mẫu chuẩn (ảnh trong điện thoại cá nhân, ghi chú rời rạc), feedback khách
   là email tự do từ agent, không gắn vào NCC cụ thể. Kết quả: quyết định "dùng KS này hay không" dựa
   vào trí nhớ của 1–2 người.
3. **Biến động thị trường (Market signals)** — NCC đổi chủ, đóng cửa sửa chữa, mở phòng mới; giá
   OTA công khai thấp hơn contract rate (parity vi phạm → agent so giá); lệnh cấm/quy định mới
   (cảng, đường). Hiện không ai theo dõi có hệ thống.

Thách thức cốt lõi: **vòng lặp không khép kín** — giá thực tế từ hóa đơn (15.9 variance) không
quay về xếp hạng NCC; feedback không quay về catalog; site inspection không quay về thuộc tính
suitability để trả lời agent (§2).

#### (b) Định hướng chiến lược — Options

| | Option A — **Manual-structured** | Option B — **Ingestion Co-Pilot mở rộng + Trust Score tự động** | Option C — **Crawler & aggregation ngoài** |
| :-- | :-- | :-- | :-- |
| Rates | Copy-paste text vào Co-Pilot (đã có); PDF/Excel chuyển text tay | Co-Pilot đọc PDF/Excel trực tiếp (text layer + bảng), OCR cho ảnh chụp bảng giá; lịch hết hạn rate tự nhắc NCC gửi bảng mới | Theo dõi giá OTA công khai để phát hiện vi phạm parity |
| Quality | Site Inspection Form chuẩn (giấy/điện thoại → nhập 1 lần); feedback khách nhập tay theo dịch vụ | Form có cấu trúc trên điện thoại gắn thẳng vào sản phẩm; feedback khách/guide theo booking line; Trust Score tính tự động có trọng số | Kéo điểm TripAdvisor/Google làm tín hiệu phụ |
| Chi phí | Thấp | Trung bình (Co-Pilot đã có 70%) | Trung bình–cao, pháp lý/kỹ thuật cào dữ liệu không ổn định |
| Giá trị | Catalog tăng chậm (5–10 NCC/tuần) | Catalog tăng nhanh (30–50 NCC/tuần); quyết định NCC dựa dữ liệu | Tín hiệu bổ sung, không phải nền |
| Khuyến nghị | Phase 1 | Phase 1–2 (ưu tiên số 1 của toàn tài liệu) | Phase 3, chỉ parity check |

#### (c) Đề xuất tính năng hệ thống

| Tính năng | Trạng thái | Bài toán | Mô tả nghiệp vụ |
| :-- | :-- | :-- | :-- |
| **Rate Ingestion Co-Pilot** | [có] 15.8 | Nhập bảng giá | Giữ nguyên nguyên tắc: AI bóc tách + đặt câu hỏi, người duyệt, ghi qua cửa chính |
| **Rate Ingestion — PDF/Excel/Ảnh** | [mở rộng] 15.8 | 85% bảng giá không phải text | Nhận file PDF (lớp text + bảng), Excel (sheet → text có cấu trúc), ảnh (OCR) → đưa vào cùng pipeline Extractor; mỗi giá trị vẫn kèm trích dẫn nguồn (trang/ô) để người duyệt đối chiếu |
| **Rate Expiry Watchlist & Renewal Calendar** | [mở rộng] 15.3 | Rate hết hạn âm thầm | Danh sách rate hết hạn trong 60/30/14 ngày; tự sinh email nhắc NCC gửi bảng mới (người bấm gửi); lịch tái đàm phán theo NCC |
| **Site Inspection Report (SIR)** | [mới] | Khảo sát không chuẩn | Form theo loại NCC: KS (loại phòng thực tế, view, ồn, khoảng cách, tiện ích trẻ em, accessibility, dietary, wifi, late checkout), nhà hàng (dietary capability, phòng riêng, sức chứa), tàu (cabin, thang máy, an toàn), xe (đời xe, ghế, hành lý). Mỗi mục có ảnh gắn thẳng Media Vault + trường suitability cập nhật thuộc tính sản phẩm (đầu vào Feasibility Checker §2) |
| **Post-Trip Feedback per Service** | [mới] | Feedback không gắn NCC | Khảo sát khách (qua agent hoặc trực tiếp) theo từng dịch vụ đã đi (từ booking lines): điểm 1–5 + nhận xét; Guide End-of-Tour Report: điểm từng NCC + sự cố + gợi ý; Operator note |
| **Supplier Trust Score** | [mới] | "Dùng NCC này không?" | Điểm 0–100 tính có trọng số từ: feedback khách (35%), báo cáo guide (20%), sự cố ops (15%), tốc độ xác nhận (10%), lệch hóa đơn AP (10%), hủy/đổi từ phía NCC (10%). Có suy giảm theo thời gian (feedback 18 tháng trước bớt trọng số). Hiển thị trong picker khi sale chọn dịch vụ; **chỉ L2** |
| **Supplier Review Cadence** | [mới, quy trình] | Quyết định thay NCC | Mỗi quý: NCC dưới ngưỡng → review; NCC top → thương lượng điều khoản tốt hơn (allotment, late checkout mặc định) |
| **Parity Watch** | [mới, Phase 3] | Agent so giá OTA | Theo dõi giá công khai của 20–30 KS chính; nếu giá OTA < giá bán DMC → cảnh báo sale/thương lượng NCC |

**Trọng số Trust Score** là quyết định nghiệp vụ, không phải kỹ thuật — Founder nên chốt sau 1 mùa
dữ liệu. Nguyên tắc: điểm là **đề xuất**, quyết định dùng/không dùng NCC vẫn là người; AI không
được tự thay đổi điểm (§5.4).

#### (d) Chỉ số đo

| Chỉ số | Mục tiêu 6 tháng |
| :-- | :-- |
| Số NCC có rate active trong catalog | ≥150 |
| Thời gian nhập 1 bảng giá KS (trung vị) | 60 phút → ≤10 phút duyệt |
| Tỷ lệ lỗi giá phát hiện sau khi commit | <1% |
| % KS chính (top 50) có SIR ≤12 tháng | ≥80% |
| % booking có feedback per service | ≥60% |
| % NCC có Trust Score (≥3 điểm dữ liệu) | ≥50% top 100 |

### 3.4 Marketing & Kho tài sản dữ liệu độc quyền (Data Moat)

#### (a) Bản chất nghiệp vụ & thách thức thực tế

Marketing của DMC B2B không phải quảng cáo; nó là **chứng minh năng lực bản địa** với agent. Cái
agent trả tiền (và cái đối thủ + AI đại trà không có) là tri thức thực địa dạng ngầm (tacit):

| Loại tri thức | Ví dụ thật | Ai giữ hiện nay | Rủi ro |
| :-- | :-- | :-- | :-- |
| Góc chụp / thời điểm | Mù Cang Chải: ruộng vàng nhất tuần 3–4 tháng 9, điểm nhìn đồi Mâm Xôi lúc 6h sáng không có xe khách; Hội An: chợ đèn lồng đẹp nhất 17h–18h trước khi đoàn lớn tới | Guide giỏi, sale senior | Guide nghỉ = mất |
| Cung đường bí mật | Đèo Hải Vân bằng jeep cổ dừng ở trạm gác cũ; đường vòng Pù Luông tránh xe tải | Driver, ops | Không ai ghi |
| Tiếp cận nghệ nhân / cộng đồng | Nghệ nhân làm nón ở làng Chuông chỉ nhận qua giới thiệu; gia đình người Dao ở Tả Phìn mở bữa tối riêng | MD, sale senior | **Tài sản có giá trị nhất**, không được lộ |
| Mẹo vận hành không văn bản | KS X cho late checkout 15h nếu hỏi trước 1 ngày; nhà hàng Y đóng thứ hai; bến tàu Z lên tàu thuận tiện hơn cho người già | Ops | Nhân viên mới lặp lỗi |
| Mùa vụ chi tiết | Sứa Phú Quốc tháng 3–4 (bãi nào ít); sương mù Sapa tháng 12–1; nước cạn Mekong tháng 4 | Sale | Trả lời agent sai |

Thách thức: (1) tri thức không có chỗ chứa có cấu trúc; (2) không có văn hóa ghi chép vì không ai
thấy lợi ích tức thì; (3) ảnh/video của nhân viên nằm rải rác, không rõ bản quyền, không gắn vào dịch
vụ nên proposal vẫn dùng ảnh stock giống đối thủ.

**Vì sao đây là moat**: AI đại trà (ChatGPT, Google) tổng hợp từ nội dung công khai; tri thức trên
không công khai. DMC nào số hóa được nó sẽ (i) trả lời agent nhanh và đúng hơn (§2), (ii) proposal có
"insider tip" mà đối thủ không có, (iii) huấn luyện nhân viên mới trong tuần thay vì năm, (iv) có tài
sản chuyển nhượng được khi gọi vốn/bán công ty.

#### (b) Định hướng chiến lược — Options

| | Option A — **Wiki ghi chú gắn sản phẩm/điểm đến** | Option B — **Destination Knowledge Base (DKB) có cấu trúc + Media Vault** | Option C — **DKB + AI retrieval + sinh nội dung** |
| :-- | :-- | :-- | :-- |
| Cốt lõi | Trường "ghi chú nội bộ" tự do trên sản phẩm & điểm đến; thư mục ảnh theo điểm đến | Knowledge card có loại, điểm đến, sản phẩm, mùa, exposure, nguồn, người/ngày kiểm chứng, hết hạn; Media Vault có tag, bản quyền, exclusivity, gắn dịch vụ | Như B + trợ lý tra cứu (§2, §5) + tự đề xuất tip vào proposal theo ngày |
| Chi phí | Rất thấp | Trung bình (schema + form nhập nhanh trên điện thoại + quy trình) | Trung bình–cao |
| Giá trị | Có còn hơn không; khó tra cứu, không phân lớp được để mở cho agent | Tra cứu được, phân lớp được, đo được; nền của Portal | Tự động hóa hiển thị; giá trị bán hàng cao nhất |
| Rủi ro | Ghi chú tự do lẫn L2/L3 → không bao giờ mở được cho agent | Cần kỷ luật kiểm chứng; card sai → trả lời agent sai | AI diễn giải sai card |
| Khuyến nghị | Không (mất cơ hội phân lớp) | **Phase 1–2, bắt đầu thu thập ngay** | Phase 3 |

#### (c) Đề xuất tính năng hệ thống

| Tính năng | Trạng thái | Bài toán | Mô tả nghiệp vụ |
| :-- | :-- | :-- | :-- |
| **Destination Knowledge Base (DKB)** | [mới] | Chỗ chứa tri thức | Card có: loại (logistics / suitability / seasonality / photo-spot / access / ops-tip / policy-note), điểm đến (cây phân cấp đã có 15.2b), sản phẩm liên quan (tùy chọn), thời điểm áp dụng (tháng/giờ), nội dung ≤120 từ, ảnh, **exposure L0–L3** (mặc định L2), nguồn (site inspection / tour / guide / NCC), người kiểm chứng, ngày kiểm chứng, ngày hết hạn (mặc định 12 tháng), số lần được dùng để trả lời |
| **Quick-Capture trên điện thoại** | [mới] | Không ai ghi | Guide/ops ghi 1 card trong 60 giây (chọn loại, gõ/ghi âm 1 câu, chụp ảnh) ngay tại hiện trường; card vào hàng đợi "chưa kiểm chứng"; sale/ops senior duyệt hàng tuần. Gắn thưởng nhỏ theo card được duyệt |
| **Curated Media Vault** | [mở rộng] media library (03/09/11) | Ảnh độc quyền gắn dịch vụ | Mỗi ảnh/video: điểm đến, sản phẩm, mùa, giờ chụp, người chụp, **bản quyền** (nhân viên/NCC/khách đồng ý/stock), **exclusivity** (độc quyền/không), exposure; xuất hiện trong picker khi dựng brochure theo ngày/dịch vụ; ưu tiên ảnh độc quyền |
| **Insider Tip Injection** | [mở rộng] brochure sections | Proposal khác biệt | Khi proposal có ngày tại điểm đến X, hệ thống gợi ý 1–2 card L1 phù hợp (mùa, archetype) để sale chèn thành "Tip từ đội điều hành"; không tự chèn |
| **Knowledge Freshness Dashboard** | [mới] | Card lỗi thời | Card sắp hết hạn theo điểm đến; card được dùng nhiều nhưng lâu chưa kiểm chứng → ưu tiên khảo sát |
| **Query → Card loop** | [mới] (§2.6) | Tri thức sinh từ câu hỏi thật | Mọi câu trả lời cho agent có nút "lưu thành card" |
| **Product Story Sheet** | [mở rộng] content studio | Marketing B2B | Mỗi sản phẩm độc quyền có 1 trang "câu chuyện" (L1) + bộ ảnh độc quyền + điều kiện, dùng cho newsletter agent và proposal |

Nguyên tắc dữ liệu: **card không có nguồn và người kiểm chứng thì không tồn tại ở L1**. AI (nếu dùng,
§5) chỉ được đề xuất card từ nhật ký/feedback, không được tự tạo card đã kiểm chứng.

#### (d) Chỉ số đo

| Chỉ số | Mục tiêu 12 tháng |
| :-- | :-- |
| Số card kiểm chứng | ≥300 (top 15 điểm đến) |
| % proposal có ≥1 insider tip L1 | ≥70% |
| % ảnh trong proposal là độc quyền | ≥50% |
| Số card do guide/ops đóng góp/tháng | ≥30 |
| Thời gian onboarding sale mới đến proposal độc lập | 8 tuần → 3 tuần |

### 3.5 Customer Service & In-Trip Concierge

#### (a) Bản chất nghiệp vụ & thách thức thực tế

Khách private cao cấp kỳ vọng ba thứ trong chuyến đi: **được nhớ đến** (chào đón đúng tên, biết
ngày kỷ niệm), **được giải quyết ngay** (không phải chờ về nước để khiếu nại), và **không phải tự
điều phối** (guide – driver – KS – ops là một khối). Ba khối nghiệp vụ:

1. **Chăm sóc chủ động** — tin nhắn chào trước khi bay, check-in ngày đầu, hỏi thăm mỗi ngày (qua
   guide hoặc trực tiếp), quà nhỏ đúng lúc (kỷ niệm, sinh nhật). Chi phí thấp, tác động lớn với NPS.
2. **Service Recovery tại chỗ** — quy tắc vàng của ngành: *phàn nàn được giải quyết trước khi khách
   rời điểm đến sẽ biến thành lời khen; phàn nàn về đến agent qua email của khách sẽ thành mất agent*.
   Nghệ thuật: thừa nhận ngay (≤15 phút), sửa (≤ vài giờ), bù đắp có ý nghĩa (nâng hạng, bữa tối
   riêng, trải nghiệm thêm — không phải giảm giá), và **báo agent trước khi khách báo**.
3. **Phối hợp Ops – Guide – Driver** — mỗi tour thường có nhóm chat riêng; thông tin chìm trong
   chat, không có "trạng thái hôm nay" rõ ràng; guide ngại báo sự cố nhỏ vì sợ bị trách → tích tụ.

Thách thức đặc thù: khách Âu–Mỹ thường **không phàn nàn với guide** (lịch sự) nhưng viết email dài
cho agent sau chuyến; DMC không có tín hiệu sớm. Cần cơ chế đo "nhiệt độ" hàng ngày không phiền khách.

#### (b) Định hướng chiến lược — Options

| | Option A — **Human Concierge có kịch bản** | Option B — **Trip Companion + Daily Pulse + Escalation số** | Option C — **Concierge thời gian thực có AI triage** |
| :-- | :-- | :-- | :-- |
| Cốt lõi | Quy trình chăm sóc chuẩn (checklist trước/trong/sau); WhatsApp trực tiếp với 1 ops phụ trách; guide gọi điện báo cáo tối | Trang chuyến đi trên điện thoại cho khách (lịch trình sống, liên hệ, voucher, nút "cần hỗ trợ"); guide nhập Daily Pulse (điểm 1–5 + 1 dòng) mỗi tối; Incident ladder có SLA; agent nhận báo cáo sự cố chuẩn | Như B + AI phân loại tin nhắn khách/guide theo mức khẩn, đề xuất playbook; kênh WhatsApp Business tích hợp |
| Chi phí | Thấp | Trung bình (trang chuyến đi tái dùng brochure pipeline) | Trung bình–cao (tích hợp kênh chat) |
| Giá trị | Đủ cho <10 tour đồng thời | Nhìn được toàn bộ tour đang chạy trên 1 màn; cảnh báo sớm | Scale khi >30 tour đồng thời |
| Rủi ro | Phụ thuộc 1–2 người, không có tín hiệu sớm | Guide không nhập Pulse → cần gắn vào quy trình thanh toán công tác phí | AI phân loại sai mức khẩn (phải luôn có "khách/guide tự chọn khẩn cấp" vượt AI) |
| Khuyến nghị | Phase 1 | Phase 2 | Phase 3 (chỉ triage, không trả lời khách) |

#### (c) Đề xuất tính năng hệ thống

| Tính năng | Trạng thái | Bài toán | Mô tả nghiệp vụ |
| :-- | :-- | :-- | :-- |
| **Trip Companion Page (mobile web)** | [mở rộng] brochure publication | Khách không phải tự điều phối | Sinh từ booking snapshot (không phải proposal): lịch trình hôm nay/ngày mai, tên & ảnh guide/driver, giờ đón, địa chỉ KS, voucher, số khẩn cấp 24/7, nút "cần hỗ trợ" (tạo ticket + gọi); song ngữ; không cần đăng nhập (link riêng có hạn) |
| **Daily Pulse** | [mới] | Không có tín hiệu sớm | Guide nhập mỗi tối ≤60 giây: điểm hài lòng ước lượng (1–5), tâm trạng (chọn), 1 dòng ghi chú, dịch vụ nào có vấn đề; Pulse ≤3 hai ngày liên tiếp hoặc ≤2 một lần → cảnh báo ops trưởng |
| **Satisfaction Early-Warning** | [mới] | Phàn nàn bùng nổ sau tour | Tổng hợp Pulse + sự cố + phát sinh + (tùy chọn) tin nhắn khách → "nhiệt kế" từng tour đang chạy trên màn ops; đỏ = ops trưởng gọi khách trong ngày |
| **Incident Escalation Ladder** | [mới] | Sự cố không lên đúng người | Mức 1 (guide xử lý, ghi nhận ≤15 phút) → Mức 2 (ops, ≤1h có kế hoạch) → Mức 3 (trưởng ops/MD, ≤4h, quyền bồi thường đến ngưỡng X USD) → Mức 4 (MD, y tế/an toàn/pháp lý, tức thì). Mỗi sự cố: loại, mức, chủ, thời hạn, chi phí, kết quả, khách đã hài lòng chưa |
| **Recovery Playbook** | [mới, nội dung] | Xử lý không nhất quán | Theo loại sự cố: hành động chuẩn, ngưỡng bồi thường theo hạng tour, mẫu tin nhắn cho khách và **mẫu báo cáo cho agent** (sự việc – đã làm – bù đắp – phòng ngừa) |
| **Agent Incident Report** | [mới] | Agent biết sau khách | Khi sự cố mức ≥2 được ghi nhận, sale được nhắc gửi báo cáo chuẩn cho agent trong 4 giờ; log gửi |
| **Post-Trip Care Sequence** | [mới, quy trình] | Kết thúc lạnh | Ngày cuối: quà/ thư tay; +2 ngày: cảm ơn + khảo sát per service; +7 ngày: album ảnh độc quyền (từ guide) — đồng thời là kênh thu thập media có đồng ý |

#### (d) Chỉ số đo

| Chỉ số | Mục tiêu |
| :-- | :-- |
| % tour có Daily Pulse ≥90% ngày | ≥85% |
| Sự cố mức ≥2 có báo cáo agent trong 4h | ≥90% |
| Phàn nàn đến agent mà DMC chưa biết trước | 0 |
| NPS khách (qua agent) | ≥70 |
| Tỷ lệ tour có sự cố được xử lý trước khi khách rời điểm đến | ≥90% |

### 3.6 CEO & Ban Giám đốc — Dòng tiền, biên lợi nhuận thực, hiệu quả từng đại lý

#### (a) Bản chất nghiệp vụ & thách thức thực tế

DMC là nghề **ứng vốn**: NCC đòi cọc khi confirm (30–50% với KS/tàu mùa cao), thanh toán đủ trước
dịch vụ 7–30 ngày; trong khi agent lớn có credit terms: cọc 20–30%, số dư trả 30–45 ngày **trước**
khởi hành (tốt) hoặc **sau** khởi hành (xấu, nhưng phổ biến với agent lớn ở Anh/Úc). Mùa cao (11–3)
một DMC 200 file/năm có thể ứng 100–300 nghìn USD tại một thời điểm. Ba câu hỏi CEO cần trả lời
**mỗi tuần**:

1. **Dòng tiền 90 ngày tới**: ngày nào phải trả NCC bao nhiêu, ngày nào khách/agent phải trả bao
   nhiêu, khoảng trống ở đâu, file nào gây khoảng trống lớn nhất (T9 guardrail đã bắt từng file; CEO
   cần tổng hợp theo lịch).
2. **Biên lợi nhuận thực**: Quoted (lúc báo giá) → Operating (sau booking, đã tính phạt hủy) →
   Realized (sau hóa đơn NCC & thu khách). Chênh Quoted vs Realized điển hình 2–5 điểm % — do phát
   sinh không ghi, phụ thu quên, lệch tỷ giá (mua VND bán USD/EUR: biến động 3–5%/năm ăn thẳng vào
   biên nếu không hedge/quy đổi đúng lúc), phạt hủy NCC không thu được khách.
3. **Agent nào đáng phục vụ**: doanh thu cao nhưng amendment 8 lần/file, trả tiền chậm 60 ngày,
   hỏi 40 email/file → có thể **lỗ** sau khi tính chi phí sale. Ngược lại agent nhỏ, ít phiền, trả
   sớm → nên nâng tier. Hiện `partner_profiles.tier` được gán tay, không dựa dữ liệu.

Rủi ro chiến lược khác CEO cần thấy: tập trung doanh thu (1 agent >30%), tập trung NCC (1 tàu Hạ
Long chiếm 40% đêm tàu), mùa vụ (70% doanh thu trong 5 tháng), FX.

#### (b) Định hướng chiến lược — Options

| | Option A — **Báo cáo tuần từ export** | Option B — **Read-model Dashboards** | Option C — **Cảnh báo dự báo** |
| :-- | :-- | :-- | :-- |
| Cốt lõi | Kế toán xuất CSV (AP/AR/booking) → bảng tính tuần cho CEO | Dashboard sống: Cash-flow calendar, Margin waterfall, Agent matrix, Variance report — tính từ log bất biến (15.5/15.6/15.9/15.11) | Như B + dự báo dòng tiền theo pipeline (xác suất chốt × giá trị), cảnh báo trước khoảng trống |
| Chi phí | Thấp | Trung bình (15.11 blueprint đã có phần margin) | Trung bình |
| Giá trị | Đủ cho <100 file/năm | Quyết định theo ngày; phát hiện rò rỉ biên | Tránh khủng hoảng tiền mặt mùa cao |
| Rủi ro | Trễ 1 tuần; lỗi bảng tính | Số liệu chỉ đúng nếu Trip Diary/AP được nhập kỷ luật | Dự báo sai gây tự tin giả |
| Khuyến nghị | Phase 1 | Phase 2 | Phase 3 |

#### (c) Đề xuất tính năng hệ thống

| Tính năng | Trạng thái | Bài toán | Mô tả nghiệp vụ |
| :-- | :-- | :-- | :-- |
| **Cash-flow Calendar (90 ngày)** | [mở rộng] 15.6 T9 + 15.9/15.10 | Khoảng trống dòng tiền | Lịch theo ngày: dòng ra (hạn cọc/số dư NCC từ booking lines), dòng vào (hạn thu agent từ AR), số dư lũy kế; tô đỏ ngày âm; drill-down tới file; bộ lọc "nếu agent X trả chậm 15 ngày" |
| **Margin Waterfall per File & per Tháng** | [có blueprint] 15.11 | Biên thực | Quoted → Operating → Realized, phân rã nguyên nhân: phát sinh, phạt hủy, lệch hóa đơn, FX, phụ thu quên; top 10 file rò rỉ |
| **Post-Tour Variance Report** | [có] 15.9 variance + [mở rộng] Trip Diary | "Tại sao file này lỗ?" | Sau khi tour delivered + hóa đơn khớp: bảng từng dịch vụ giá báo / giá booking / giá hóa đơn / phát sinh; gắn lý do từ Trip Diary; ai duyệt phát sinh |
| **Agent Profitability Matrix** | [mới] | Agent nào đáng nuôi | Trục X: biên lợi nhuận gộp/năm; trục Y: "chi phí phục vụ" (số amendment/file, số câu hỏi/file, ngày trả tiền trung bình DSO, tỷ lệ hủy, sự cố). 4 góc: Nuôi (cao–thấp), Đàm phán lại (cao–cao), Tự động hóa (thấp–thấp), Cân nhắc dừng (thấp–cao). Đề xuất tier tự động; người quyết |
| **Pipeline Health** | [mới] | Dự báo doanh thu | Theo giai đoạn: yêu cầu → proposal → chờ agent → chốt; giá trị × xác suất theo lịch sử agent; tuổi yêu cầu; SLA vi phạm |
| **Concentration & FX Exposure** | [mới] | Rủi ro chiến lược | % doanh thu top 3 agent, top 3 NCC; số dư phải trả VND vs phải thu USD/EUR theo tháng; cảnh báo ngưỡng |
| **Supplier Spend & Terms Leverage** | [mở rộng] 15.9 | Đàm phán NCC | Chi tiêu theo NCC 12 tháng, số đêm/ghế → cơ sở đòi điều khoản tốt hơn (giảm cọc, late checkout mặc định, allotment) |
| **Weekly CEO Brief** | [mới, tự động] | Không có thời gian mở dashboard | Email thứ hai: 5 số (tiền mặt 30 ngày, biên tháng, file chốt/tuần, sự cố mức ≥2, rate hết hạn) + 3 việc cần quyết |

#### (d) Chỉ số đo

| Chỉ số | Mục tiêu |
| :-- | :-- |
| Chênh Quoted vs Realized margin | ≤1,5 điểm % |
| Số ngày dòng tiền âm không dự báo trước 30 ngày | 0 |
| DSO trung bình agent | ≤30 ngày |
| % agent có tier dựa dữ liệu (không gán tay) | 100% sau 12 tháng |
| Thời gian đóng sổ file sau delivered | ≤30 ngày |

---

## 4. MA TRẬN PHÂN KỲ TÍNH NĂNG & KHUNG QUYẾT ĐỊNH CHO FOUNDER

### 4.1 Nguyên tắc phân kỳ

1. **Manual-first, data-first, AI-last** — bài học Plan 14: xây AI trước khi flow thủ công chạy
   là lý do thất bại. Mọi tính năng AI ở Phase ≥2 chỉ bật khi flow thủ công tương ứng đã chạy đủ
   một mùa và có dữ liệu để đo.
2. **Mỗi phase phải "đóng" một vòng lặp nghiệp vụ**, không phải giao một danh sách tính năng.
3. **Không sửa module đã đóng** (15.1–15.6, 15.9): tính năng mới là consumer đọc log/snapshot.
4. **Mỗi tính năng có chủ nghiệp vụ** (Sale lead / Ops lead / Finance / MD) chịu trách nhiệm KPI,
   không phải "team dev".
5. **Đo trước khi xây**: mỗi phase bắt đầu bằng 2 tuần đo baseline (thời gian ra proposal, thời
   gian đuổi xác nhận, chênh biên) để biết có cải thiện thật không.

### 4.2 Phase 1 (tháng 0–3) — "Khép vòng vận hành với dữ liệu thật"

Mục tiêu: một file đi trọn Yêu cầu → Costing → Booking → Ops → AP với dữ liệu thật; catalog đủ giàu
để Drafter có ích.

| Ưu tiên | Tính năng | Phòng ban | Trạng thái | Điều kiện xong |
| :-: | :-- | :-- | :-- | :-- |
| P0 | Rate Ingestion — PDF/Excel/Ảnh + đóng data gate 15.8b (corpus 30, seed ≥25→150 NCC) | Data | [mở rộng] | ≥150 NCC có rate active; lỗi giá sau commit <1% |
| P0 | AI Service Drafter qua exit gate với corpus request thật | Sale | [có] | 20 request thật → dàn dịch vụ đúng ≥80% dòng, 0 giá bịa |
| P0 | Costing → Booking → AP chạy đủ 1 chu kỳ (15.9 §12 defect log xanh) | Ops/Finance | [có] | 1 hóa đơn gộp nhiều booking khớp end-to-end |
| P1 | Itinerary Template Library (15 khung) | Sale | [mới, nội dung] | Proposal từ mẫu ≤3h |
| P1 | Checklist ngày đặc biệt & phụ thu bắt buộc | Sale | [mở rộng] | 0 file quên gala/peak trong mùa |
| P1 | Dispatch Templates + Dispatch Log (15.12 kéo lên) | Ops | [mở rộng] | Mọi yêu cầu NCC đi từ hệ thống |
| P1 | Trip Diary v1 (form đơn giản, phát sinh → dòng chờ đối soát) | Ops | [mới] | ≥80% booking có nhật ký |
| P1 | Partner Portal Option A: Query Inbox + SLA + FAQ dạng card (schema DKB ẩn) | Sale/Portal | [mới] | ≥5 agent dùng; 50 card đầu |
| P2 | DKB Quick-Capture (guide/ops) + Media Vault tag bản quyền | Marketing | [mới] | ≥100 card chờ duyệt, ≥300 ảnh tag |
| P2 | Weekly CEO Brief từ export | CEO | [mới, nhẹ] | Email tự động mỗi thứ hai |

### 4.3 Phase 2 (tháng 3–9) — "Giữ chân & bảo vệ"

Mục tiêu: agent thấy khác biệt (tốc độ, chính xác, recovery); CEO thấy biên thực và dòng tiền.

| Ưu tiên | Tính năng | Phòng ban | Điều kiện bắt đầu |
| :-: | :-- | :-- | :-- |
| P0 | Partner Portal Option B: Knowledge Cards có trích dẫn + Deep-Query Assistant (nội bộ → agent) + Partner Terms Card | Portal | ≥100 card kiểm chứng; Partner Terms của DMC đã chốt |
| P0 | Multi-Scenario Pricing (3★/4★/5★) | Sale | ≥3 tier/điểm đến chính trong catalog |
| P0 | Proposal Version Ledger + Amendment Quote | Sale/Ops | Booking flow chạy ổn |
| P0 | Incident Escalation Ladder + Recovery Playbook + Agent Incident Report | CS | Trip Diary v1 chạy |
| P1 | Confirmation Chasing Queue | Ops | Dispatch log có dữ liệu |
| P1 | Post-Trip Feedback per Service + Guide End-of-Tour Report + Supplier Trust Score v1 | Data | ≥30 tour delivered có feedback |
| P1 | Site Inspection Report chuẩn (mobile) | Data | Lịch khảo sát mùa thấp |
| P1 | Cash-flow Calendar 90 ngày (cần AR 15.10) | CEO | 15.10 AR triển khai |
| P1 | Margin Waterfall (15.11) + Post-Tour Variance Report | CEO | 15.9 đóng + 15.10 |
| P2 | Trip Companion Page + Daily Pulse | CS | Booking snapshot đủ trường liên hệ |
| P2 | Guide/Driver Assignment + Briefing Pack | Ops | Hồ sơ guide nhập |
| P2 | Rate Expiry Watchlist & Renewal Calendar | Data | Catalog ≥150 NCC |

### 4.4 Phase 3 (tháng 9–18) — "Moat & scale"

| Ưu tiên | Tính năng | Điều kiện bắt đầu |
| :-: | :-- | :-- |
| P0 | Insider Tip Injection + Product Story Sheet (DKB → proposal) | ≥300 card L1 |
| P0 | Agent Profitability Matrix + tier dựa dữ liệu | 12 tháng dữ liệu AR/amendment/query |
| P0 | Feasibility Checker cho agent (Portal) | Card logistics ≥50 điểm đến/cung đường |
| P1 | Amendment Request + Impact Preview cho agent (Portal Option C một phần) | Partner Terms 100% |
| P1 | Satisfaction Early-Warning (Pulse + sự cố + phát sinh) | Daily Pulse ≥85% tour |
| P1 | Pipeline Health + Concentration/FX Exposure | Dữ liệu 12 tháng |
| P2 | Parity Watch (OTA) | Top 30 KS xác định |
| P2 | AI triage sự cố/tin nhắn (§5) | Kênh chat tích hợp |
| P2 | Allotment (M8) | Có hợp đồng allotment thật |

### 4.5 Khung quyết định cho Founder — 8 quyết định cần chốt

| # | Quyết định | Option A | Option B | Tiêu chí chọn | Khuyến nghị |
| :-: | :-- | :-- | :-- | :-- | :-- |
| D1 | Định vị 12 tháng (§1.5) | Ops Excellence | Knowledge-Moat | Team ops đang mất tiền vì lỗi? → A | **A + thu thập B** |
| D2 | Partner Portal mở cho agent khi nào | Sau ≥100 card (an toàn) | Ngay với FAQ thủ công | Có ≥5 agent hoạt động để thử? | **B với schema A ẩn dưới** |
| D3 | Partner Terms chuẩn của DMC (cọc, hủy, child, hiệu lực báo giá) | Một bộ chung toàn DMC | Theo tier agent | Phức tạp vận hành vs sức mạnh đàm phán | **A trước, B khi có matrix** |
| D4 | Trip Diary bắt buộc hay khuyến khích | Bắt buộc, gắn thanh toán công tác phí guide | Khuyến khích | Guide là nhân viên hay cộng tác viên? | **A** (không có nhật ký = không có biên thực) |
| D5 | Trust Score: trọng số và ngưỡng review | Trọng số mặc định §3.3 | Chờ 1 mùa dữ liệu rồi chốt | Có ≥30 tour feedback? | **B**, dùng A tạm |
| D6 | Ai duyệt bồi thường và ngưỡng theo mức | Ops trưởng đến 200 USD, MD trên | Guide có ngưỡng nhỏ 50 USD | Tin cậy guide? | **Cả hai** (guide 50, ops 200, MD trên) |
| D7 | Multi-scenario: thay chỉ lưu trú hay cả trải nghiệm | Chỉ lưu trú | Lưu trú + xe + trải nghiệm theo tier | Catalog có tier cho xe/trải nghiệm? | **A** rồi mở rộng |
| D8 | AI ưu tiên (§5.8) | 3 việc 30 ngày như đề xuất | Đổi (2) bằng invoice extraction | AP đã có ≥50 hóa đơn/tháng? | **A** |

### 4.6 Rủi ro chiến lược & guardrails

| Rủi ro | Dấu hiệu sớm | Guardrail |
| :-- | :-- | :-- |
| Xây tính năng mà không có dữ liệu (lặp Plan 14) | Catalog <100 NCC sau tháng 2 | Phase 2 không bắt đầu nếu P0 Phase 1 chưa xanh |
| Portal lộ dữ liệu | Card L1 chứa tên NCC/liên hệ/giá NET | Duyệt card 2 người cho L1; nhật ký truy vấn; kiểm tra định kỳ |
| Guide/ops không nhập Diary/Pulse/Card | <50% sau tháng đầu | Gắn vào quy trình công tác phí; thưởng card duyệt; form ≤60 giây |
| Agent dùng Portal để so giá rồi đi DMC khác | Hỏi nhiều, không gửi file | Không liệt kê toàn bộ; giá chỉ theo yêu cầu; theo dõi Activity Signal |
| Biên thực không đo được | Chênh Quoted–Realized >5 điểm | Trip Diary bắt buộc; AP khớp voucher; đóng sổ ≤30 ngày |
| Phụ thuộc AI trước khi tin cậy | Sale gửi proposal AI không đọc | Human gate bắt buộc; đo lỗi AI mỗi tháng; kill criteria §5.9 |

---

## 5. [DEDICATED FINALE] BẢN THIẾT KẾ ĐIỂM CHẠM AI CHO DMC — TỐI ƯU, HIỆU QUẢ, TIẾT KIỆM, TĂNG TỐC

### 5.1 Năm nguyên tắc bất biến khi cắm AI vào DMC

Nền tảng đã "trả giá trước" cho các nguyên tắc này ở 15.7/15.8 (AI Platform Layer). Tài liệu này
nâng chúng thành **chính sách công ty**, áp dụng cho mọi điểm chạm AI tương lai:

| # | Nguyên tắc | Ý nghĩa nghiệp vụ | Cách thi hành (đã có / cần có) |
| :-: | :-- | :-- | :-- |
| A1 | **AI không bao giờ chạm tiền** | AI không sinh giá, không chọn giữa hai rate mâu thuẫn, không tính phạt, không đề xuất markup, không quyết bồi thường | Schema output không có trường tiền (15.7 chốt #1); giá luôn do máy tính từ rate đã duyệt; số tiền trong văn bản NCC được giữ **nguyên văn** cho người/parser xử lý (15.8) |
| A2 | **Luôn có người gác cổng trước khi có tác động ra ngoài** | Mọi thứ AI tạo là *đề xuất* (draft/candidate/suggestion); gửi cho agent/NCC/khách, ghi vào catalog, đổi trạng thái booking — đều do người bấm | Staging bắt buộc (15.8), TripProfile review (15.7), Diff Viewer; mở rộng: "xem trước rồi gửi" cho mọi email AI soạn |
| A3 | **Đầu ra có cấu trúc, có nguồn, có nhật ký** | Không chấp nhận văn xuôi tự do làm đầu ra nghiệp vụ; mỗi giá trị kèm trích dẫn nguồn; mỗi lần chạy có nhật ký chi phí và kết quả | Typed output + `source_quote` + `ai_runs` (đã có); mở rộng cho retrieval: mỗi câu trả lời kèm card id |
| A4 | **Văn bản không tin cậy bị cô lập** | Email khách/NCC, tin nhắn, PDF có thể chứa nội dung "ra lệnh" cho AI; tầng đọc văn bản thô không có công cụ nào để làm gì ngoài trích xuất | Phân tầng 2 agent (0-tool đọc thô → có tool chỉ đọc payload) đã có ở 15.7/15.8; áp dụng y hệt cho email NCC, tin nhắn khách, feedback |
| A5 | **Rẻ trước, mạnh sau, có trần** | Model nhỏ/rẻ làm phần lớn; leo lên frontier khi kiểm chứng thất bại hoặc rủi ro cao; mọi run có ngân sách cứng | RunBudget (đã có); mở rộng: định tuyến 2 tầng (§5.7) |

### 5.2 Bản đồ điểm chạm AI (AI Insertion Map) theo chu trình

Ký hiệu ROI: 🟢 cao (hoàn vốn <3 tháng) · 🟡 trung bình · 🔴 thấp/âm. Rủi ro: mức thiệt hại nếu AI
sai mà không ai phát hiện. "Đầu vào" nói AI nhận gì — cấu trúc (S) hay văn bản thô (U).

| Chặng | Điểm chạm | Việc thủ công hiện nay (ước tính) | AI làm gì | Đầu vào | ROI | Rủi ro nếu sai | Gác cổng | Trạng thái |
| :-- | :-- | :-- | :-- | :-: | :-: | :-- | :-- | :-- |
| Data | **Bóc tách bảng giá NCC** (PDF/Excel/email/ảnh) | 45–90 phút/bảng, sai 5–10% | Trích xuất giá (nguyên văn), mùa, occupancy, policy, phụ thu; đặt câu hỏi khi mơ hồ | U→S | 🟢 | Trung bình (bắt bởi Diff Viewer + parser) | Người duyệt từng dòng | [có 15.8, mở rộng PDF/Excel] |
| Data | **Bóc tách hóa đơn NCC** | 10–20 phút/hóa đơn gộp; nhầm voucher | Đọc hóa đơn → dòng {mô tả, số tiền nguyên văn, voucher nếu có} → gợi ý khớp voucher | U→S | 🟢 (khi AP ≥50 HĐ/tháng) | Thấp (AP có constraint chống double-billing) | Kế toán duyệt match | [15.9b tương lai] |
| Sale | **TripAnalyst: brief văn xuôi → TripProfile** | 20–40 phút đọc/hỏi lại | Rút số khách, ngày, phân bổ phòng, archetype, flags (dietary/medical/mobility), câu hỏi còn thiếu | U→S | 🟢 | Thấp (sale review 1 lần) | Sale review | [có 15.7] |
| Sale | **ServiceDrafter: dàn dịch vụ theo ngày** | 2–6 giờ/file | Chọn dịch vụ từ catalog theo profile (chỉ ID + lý do); giá do máy resolve | S | 🟢 | Trung bình (dịch vụ không hợp) | Sale sửa trên grid | [có 15.7, chờ exit gate] |
| Sale | **Pacing & Feasibility Check** | Chỉ senior "cảm" được | Kiểm tra ngày quá dài (giờ xe), chuyển tiếp không khả thi (bay 18h nhưng tàu về 12h ở 170 km), phương tiện không vào được điểm, mùa không phù hợp — dựa quy tắc + card logistics; giải thích bằng lời | S | 🟢 | Trung bình | Sale xem cảnh báo | [mới — rule-first, AI giải thích] |
| Sale | **Soạn nội dung proposal** (mô tả ngày, KS, tip) | 1–2 giờ/file | Sinh bản nháp theo budget & brand voice từ facts + card L1 | S | 🟢 | Thấp (nội dung, không phải giá) | Sale sửa | [có: section content generator + content budgets] |
| Sale | **Dịch song ngữ proposal/voucher** | 30–60 phút | Dịch giữ thuật ngữ, giữ số/ngày nguyên văn | S | 🟢 | Thấp | Sale đọc | [mở rộng content pipeline] |
| Sale | **Gợi ý upsell theo bối cảnh** | Phụ thuộc cá nhân | Từ archetype + điểm đến + dịp → 3 gợi ý từ catalog (ID) | S | 🟡 | Thấp | Sale chọn | [mới, có thể rule-only] |
| Portal | **Deep-Query Assistant cho agent** | 20–90 phút/câu, 1–3 ngày trả lời | Hiểu câu hỏi → tìm card L1/thuộc tính catalog L1 → trả lời có trích dẫn hoặc mở ticket | U→S(retrieval) | 🟢 | **Cao nếu bịa**; thấp nếu chỉ diễn đạt card | Ba tầng §2.3; L3 người | [mới — ưu tiên 30 ngày] |
| Portal | **Phân loại & định tuyến câu hỏi/yêu cầu** | Sale đọc tay | Gắn nhãn loại (báo giá/khả thi/điều khoản/khiếu nại), độ khẩn, người phụ trách | U | 🟢 (rẻ) | Thấp | Người có thể sửa nhãn | [mới] |
| Ops | **Đọc phản hồi NCC** (email/Zalo) → trạng thái | 5–10 phút/phản hồi, nhầm "noted" với "confirmed" | Phân loại confirmed/provisional/declined/needs-info + rút mã xác nhận, hạn cọc (nguyên văn) | U→S | 🟢 | Trung bình (tưởng confirmed) | Operator bấm xác nhận | [mới] |
| Ops | **Soạn yêu cầu NCC / voucher / briefing** | 10–20 phút/lần | Điền mẫu từ snapshot (thực ra là template, AI chỉ cho phần ghi chú đặc biệt song ngữ) | S | 🟡 | Thấp | Xem trước rồi gửi | [template-first, AI phụ] |
| Ops/CS | **Triage sự cố & tin nhắn** | Ops đọc chat liên tục | Phân mức khẩn (y tế/an toàn → mức 4 ngay), loại, gợi ý playbook | U | 🟢 | Cao nếu hạ mức sai → luôn cho phép người nâng mức, và từ khóa an toàn/y tế ép mức 4 không qua AI | Ops quyết | [Phase 3] |
| Feedback | **Rút chủ đề & cảm xúc từ feedback/Daily Pulse/guide report** | Không ai đọc hết | Tóm tắt theo NCC, gắn nhãn (phòng ồn, đồ ăn, guide), đề xuất điểm điều chỉnh | U→S | 🟢 | Thấp (đề xuất) | Người duyệt điểm | [Phase 2] |
| Feedback | **Đề xuất card DKB từ nhật ký/feedback** | Không xảy ra | Từ Trip Diary/feedback rút "tip" ứng viên với nguồn | U→S | 🟡 | Thấp (card chờ duyệt) | 2 người duyệt L1 | [Phase 2–3] |
| Data | **Cấu trúc hóa ghi chú site inspection** (giọng nói/ảnh → form) | 1–2 giờ/KS | Chuyển ghi âm/ghi chú thành trường SIR + gợi ý thuộc tính suitability | U→S | 🟡 | Thấp | Người duyệt | [Phase 2] |
| CEO | **Weekly Brief narrative** | 2–3 giờ/tuần | Diễn đạt số liệu dashboard thành 5 dòng + 3 việc cần quyết; **không** tính số | S | 🟡 | Thấp (số từ read-model) | CEO đọc | [Phase 2] |
| CEO | **Giải thích variance** ("tại sao file này lỗ") | Kế toán tra tay | Ghép variance AP + Trip Diary + amendment thành lời giải thích có dẫn chứng | S | 🟡 | Thấp | Kế toán xác nhận | [Phase 3] |

### 5.3 Nơi NÊN dùng AI — 10 quick wins xếp theo ROI

| # | Quick win | Vì sao AI hợp | Giá trị/năm (DMC 200 file, 250 NCC) | Chi phí (dev + API) |
| :-: | :-- | :-- | :-- | :-- |
| 1 | Rate ingestion PDF/Excel | Văn bản bán cấu trúc, lặp, có người duyệt, sai sót bị chặn bằng parser | 250 bảng × 60 phút = **250 giờ** + giảm lỗi giá 5–10% → tránh 1–2% biên | Dev 3–4 tuần (pipeline có sẵn); API ~0,05–0,3 USD/bảng |
| 2 | TripAnalyst + ServiceDrafter | Chọn từ tập đóng (catalog), giá do máy | 200 file × 3 giờ = **600 giờ** sale; proposal <1h → win rate +5–10 điểm | Dev đã xong; cần data gate; API ~0,1–0,5 USD/file |
| 3 | Deep-Query Assistant (3 tầng) | Retrieval trên card kiểm chứng, không sinh sự thật | 2.000 câu hỏi/năm × 40 phút = **1.300 giờ**; SLA <2h | Dev 4–6 tuần; API ~0,01–0,05 USD/câu |
| 4 | Đọc phản hồi NCC → trạng thái | Phân loại + trích mã, người bấm | 3.000 phản hồi × 7 phút = **350 giờ** ops; giảm "tưởng confirmed" | Dev 2 tuần; API ~0,005 USD/email |
| 5 | Pacing/Feasibility check | Quy tắc là chính, AI giải thích | Tránh 5–10 sự cố lịch trình/năm (mỗi cái 200–1.000 USD bù đắp + uy tín) | Dev 2–3 tuần (rule) + 1 tuần AI |
| 6 | Feedback theme extraction → Trust Score | Văn bản tự do → nhãn đề xuất | Quyết định NCC dựa dữ liệu; tránh 1–2 KS tệ/mùa | Dev 2 tuần; API rẻ |
| 7 | Phân loại/định tuyến inbox | Rẻ, nhanh, sai ít hậu quả | SLA nhìn thấy; 100 giờ | Dev 1 tuần |
| 8 | Proposal content + dịch | Đã có; chỉ nối card L1 | 200 × 1,5 giờ = 300 giờ | Đã có |
| 9 | Invoice extraction (15.9b) | Như #1, khi AP đủ khối lượng | 600 hóa đơn × 15 phút = 150 giờ; giảm nhầm voucher | Dev 2–3 tuần (tái dùng #1) |
| 10 | Site inspection voice → form | Nhân viên ghi nhiều hơn khi dễ | +50% SIR hoàn thành | Dev 2 tuần |

Tổng tiềm năng: **~3.000 giờ/năm** (≈1,5 nhân sự) + 1–3 điểm biên + win rate. Chi phí API cho toàn bộ
ở quy mô này ước **dưới 3.000 USD/năm** với định tuyến hợp lý — nhỏ so với giá trị; chi phí thật là
**thời gian dev và kỷ luật duyệt**.

### 5.4 Nơi TUYỆT ĐỐI KHÔNG dùng AI — Anti-patterns & bẫy lãng phí

| # | Anti-pattern | Vì sao cấm | Thay bằng |
| :-: | :-- | :-- | :-- |
| X1 | **AI sinh/gợi ý giá bán, markup, chọn rate khi mâu thuẫn** | Ảo giác giá = lỗ tiền thật hoặc mất agent; không audit được | Máy tính từ rate đã duyệt (đã có); sale quyết conflict |
| X2 | **AI xác nhận availability / "còn phòng"** | Không có nguồn thật; NCC không có API | Trạng thái booking do operator cập nhật từ phản hồi NCC; AI chỉ phân loại phản hồi |
| X3 | **AI viết điều khoản hủy/cọc hoặc diễn giải điều khoản cho agent** | Sai một số = tranh chấp pháp lý | Partner Terms có cấu trúc, render bằng template; AI chỉ trỏ tới card điều khoản |
| X4 | **AI trả lời trực tiếp phàn nàn của khách VIP / agent về sự cố** | Đây là "human touch" đắt giá nhất của tour 5 sao; câu xin lỗi máy móc phá hủy quan hệ | Người viết; AI chỉ tóm tắt sự việc và gợi ý playbook nội bộ |
| X5 | **AI quyết mức bồi thường hoặc hạ mức khẩn sự cố** | Rủi ro an toàn/tiền; trách nhiệm pháp lý | Ladder có ngưỡng người; AI chỉ đề xuất nâng, không hạ; từ khóa y tế/an toàn ép mức 4 |
| X6 | **AI tự gửi email/tin nhắn cho NCC, agent, khách** | Một email sai số khách gửi 20 NCC = hỗn loạn; không thể thu hồi | "Xem trước rồi gửi" bắt buộc; log dispatch |
| X7 | **AI tự ghi vào catalog / tự tạo card đã kiểm chứng / tự đổi Trust Score** | Dữ liệu nền sai lan ra mọi báo giá | Staging + người duyệt (đã có); card L1 cần 2 người |
| X8 | **Chatbot "hỏi gì cũng trả lời" cho agent** | Bịa khả thi, lộ dữ liệu, mất niềm tin sau 2 câu | Ba tầng §2.3; exposure thi hành ở dữ liệu |
| X9 | **Agent tự động nhiều bước (auto-book, auto-negotiate)** | Không có API NCC, không thể hoàn tác, chi phí token nổ, không ai chịu trách nhiệm | Từng bước có người; ngân sách cứng per run |
| X10 | **Dùng frontier model cho mọi việc "cho chắc"** | Chi phí ×20–50 mà không tăng độ tin cậy ở việc phân loại đơn giản | Định tuyến §5.7 |
| X11 | **Fine-tune model riêng / xây vector DB riêng / đội ML** | Startup không có dữ liệu đủ lớn; chi phí bảo trì; PostgreSQL + typed output đủ | Prompt YAML + RAG trên Postgres + corpus golden tests |
| X12 | **AI sinh ảnh "điểm đến" cho proposal** | Agent/khách phát hiện ảnh giả = mất toàn bộ uy tín "tri thức bản địa" | Media Vault độc quyền, ảnh thật có bản quyền |
| X13 | **Đo AI bằng "cảm giác"** | Không biết khi nào dừng | KPI + kill criteria §5.9 cho mỗi tính năng |

### 5.5 Ma trận Chi phí vs Giá trị (ROI Matrix)

Thang điểm 1–5. Chi phí = dev + vận hành + API (5 = rẻ nhất). Giá trị = giờ tiết kiệm + biên + giữ
agent (5 = cao nhất). Rủi ro = thiệt hại nếu sai không phát hiện (5 = an toàn nhất). Điểm ưu tiên =
Chi phí + Giá trị + Rủi ro.

| Điểm chạm | Chi phí | Giá trị | Rủi ro (an toàn) | Tổng | Xếp hạng | Phase |
| :-- | :-: | :-: | :-: | :-: | :-: | :-- |
| Rate ingestion PDF/Excel | 4 | 5 | 4 | **13** | 1 | 30 ngày |
| TripAnalyst + Drafter (exit gate) | 5 (đã xong) | 5 | 4 | **14** | 1 | 30 ngày |
| Deep-Query Assistant 3 tầng | 3 | 5 | 3 (có ba tầng) | **11** | 2 | 30 ngày (nội bộ) |
| Đọc phản hồi NCC | 4 | 4 | 3 | 11 | 2 | 60 ngày |
| Phân loại inbox | 5 | 3 | 5 | 13 | 1 (nhưng giá trị nhỏ) | 60 ngày |
| Pacing/Feasibility | 3 | 4 | 3 | 10 | 3 | 90 ngày |
| Feedback → theme → Trust Score | 4 | 4 | 4 | 12 | 2 | Phase 2 |
| Invoice extraction | 4 | 3 (tùy khối lượng) | 4 | 11 | 3 | Phase 2 |
| Proposal content + dịch | 5 | 3 | 5 | 13 | có sẵn | — |
| Site inspection voice→form | 4 | 3 | 4 | 11 | 3 | Phase 2 |
| Triage sự cố | 3 | 4 | 2 | 9 | 4 | Phase 3 |
| CEO brief narrative / variance explain | 4 | 2 | 4 | 10 | 4 | Phase 2–3 |
| Auto-send / auto-book / AI pricing | — | — | 1 | **cấm** | — | — |

### 5.6 Chiến lược Lean AI cho Startup — phát triển nhanh không cần đội ML

**Tài sản đã có (không xây lại)**:

| Thành phần | Có sẵn | Dùng cho mọi điểm chạm mới thế nào |
| :-- | :-- | :-- |
| Agent factory (PydanticAI) + prompt YAML | 15.7/15.8 | Mỗi điểm chạm = 1 prompt YAML + 1 schema output; không viết runtime mới |
| Typed structured output | 15.7/15.8 | Mọi đầu ra là schema; trường tiền/ngày giữ nguyên văn cho parser |
| Kho tool chỉ-đọc (catalog) | 15.7/15.8 | Thêm tool đọc card DKB (L1 filter), đọc booking snapshot, đọc policy DMC — **không thêm tool ghi** |
| Guardrails: allowlist, validator, ngân sách | 15.7/15.8 | Áp tự động cho agent mới |
| Nhật ký `ai_runs` | 15.7/15.8 | Đo chi phí, tỷ lệ retry, tỷ lệ bị người sửa — đầu vào kill criteria |
| Corpus làm golden test | 15.8b | Mỗi điểm chạm mới có corpus 20–30 ca thật trước khi bật |
| Content budgets + brand voice | prompts/v1 | Nội dung proposal, tip, dịch |
| Outbox/notification | có | AI hoàn thành → sự kiện → người được nhắc duyệt |

**Bốn kỹ thuật đủ dùng cho 95% nhu cầu**:

1. **Structured Output (typed)** — thay cho "xin AI trả JSON". Mọi trích xuất, phân loại, tóm tắt.
2. **Function Calling chỉ-đọc** — AI tra catalog/card/snapshot qua tool có allowlist; không có tool
   ghi; tool trả ≤N dòng; ngân sách call cứng.
3. **RAG trên PostgreSQL** — card DKB, SIR, feedback, policy DMC được lập chỉ mục (vector + JSONB
   metadata: điểm đến, mùa, exposure, hết hạn). Truy vấn **lọc exposure & hiệu lực ở tầng dữ liệu
   trước**, rồi mới đưa top-k vào AI để diễn đạt. Không cần vector DB riêng ở quy mô <100k card.
4. **Corpus-as-tests + human correction loop** — mỗi lần người sửa đầu ra AI được ghi lại (đã có cột
   `ai_meta`); hàng tháng rút 10 ca sai nặng nhất thành golden test mới; prompt được sửa dựa trên ca
   thật, không dựa trên cảm giác.

**Điều KHÔNG làm**: fine-tune, huấn luyện model riêng, framework agent tự chế, plugin system, multi-agent
tự trị, vector DB riêng, "AI platform team". Một backend dev có kỷ luật + một người nghiệp vụ duyệt
corpus là đủ.

**Chi phí vận hành AI ước tính** (quy mô 200 file/năm, 250 NCC, 2.000 câu hỏi agent/năm):

| Hạng mục | Lượt/năm | Token/lượt (ước) | Model | Chi phí/năm (ước) |
| :-- | :-: | :-: | :-- | :-: |
| Rate ingestion | 300 | 15–40k | nhỏ → frontier khi mơ hồ | 30–150 USD |
| TripAnalyst + Drafter | 250 | 30–80k | frontier cho Analyst, nhỏ cho Drafter per-day | 150–500 USD |
| Deep-Query | 2.000 | 5–10k | nhỏ (retrieval + diễn đạt), frontier khi Tầng 2 | 50–300 USD |
| Phản hồi NCC + inbox | 5.000 | 2–4k | nhỏ | 20–60 USD |
| Feedback/Pulse/SIR | 1.500 | 3–8k | nhỏ | 20–80 USD |
| Content + dịch | 500 | 10–30k | nhỏ/trung | 50–200 USD |
| **Tổng** | | | | **≈300–1.300 USD/năm** |

(Đơn giá token thay đổi nhanh; con số để thấy **bậc độ lớn**: chi phí API không phải rào cản, chi
phí thật là dev và duyệt.)

### 5.7 Chiến lược định tuyến mô hình (Model Routing)

Nguyên tắc: **model nhỏ/nhanh/rẻ mặc định; leo tầng theo rủi ro và theo kết quả kiểm chứng**, không
theo "cảm giác quan trọng". Nền tảng hiện dùng một cổng model OpenAI-compatible (DeepSeek, fallback
OpenAI) — mở rộng thành 2 tầng bằng cấu hình, không đổi kiến trúc.

| Việc | Tầng mặc định (nhỏ/rẻ: Flash / Haiku / DeepSeek-chat / GPT-mini) | Leo lên frontier (Sonnet / Opus / GPT-4-class) khi | Lý do |
| :-- | :-- | :-- | :-- |
| Phân loại inbox, phản hồi NCC, mức khẩn, cảm xúc feedback | ✅ luôn | Không bao giờ (nếu sai, người sửa nhãn rẻ hơn) | Tập nhãn đóng, rủi ro thấp |
| Trích xuất bảng giá NCC | ✅ lần 1 | Parser/validator fail ≥2 trường, hoặc tài liệu >4 mùa × >5 loại phòng, hoặc nhiều NCC trong 1 file | Bảng phức tạp cần suy luận cấu trúc |
| Trích xuất hóa đơn | ✅ | Không khớp voucher nào >30% dòng | |
| TripAnalyst (brief → profile) | ❌ | ✅ **luôn frontier** | Một lần/file, chi phí nhỏ, sai profile = sai cả file |
| ServiceDrafter per-day | ✅ (tool calls nhiều, cần rẻ) | Ngày có ≥3 flag đặc biệt (mobility, dietary, trẻ nhỏ) hoặc validator loại >50% ID | Phần lớn ngày là chọn từ tập nhỏ |
| Pacing/Feasibility giải thích | ✅ | Không (quy tắc quyết, AI chỉ diễn đạt) | |
| Deep-Query Tầng 1 (có card) | ✅ | Không | Diễn đạt card, không suy luận |
| Deep-Query Tầng 2 (suy luận có điều kiện) | ❌ | ✅ frontier | Cần suy luận thận trọng + nêu điều kiện; sai = mất agent |
| Nội dung proposal (theo budget) | ✅ trung | Bản cho agent VIP hoặc sản phẩm độc quyền | Chất lượng văn |
| Dịch | ✅ | Không | |
| Tóm tắt feedback → theme | ✅ | Không | |
| CEO brief narrative | ✅ | Không | Số từ read-model |
| Triage sự cố (Phase 3) | ✅ phân loại | **Từ khóa y tế/an toàn bỏ qua AI, ép mức 4** | An toàn không giao AI |

Cơ chế leo tầng phải là **tự động dựa trên kiểm chứng máy** (validator fail, allowlist reject, số
câu hỏi làm rõ >N) — không dựa trên "confidence" AI tự khai (bài học T5 ở 14.0). Mọi run ghi tầng đã
dùng vào `ai_runs` để đo tỷ lệ leo tầng (mục tiêu <20%).

### 5.8 Lộ trình AI — 3 việc làm ngay trong 30 ngày, rồi 60–90 ngày, rồi 6–12 tháng

#### 30 ngày — ba tính năng tạo đột phá tức thì

| # | Tính năng | Vì sao đây | Tuần 1 | Tuần 2 | Tuần 3 | Tuần 4 | Tiêu chí nghiệm thu |
| :-: | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | **Rate Ingestion Co-Pilot v1.1: PDF/Excel + đóng data gate 15.8b** | Catalog nghèo là nút thắt của mọi thứ phía trên; pipeline có sẵn 70% | Gom 30 bảng giá thật (10 PDF, 10 Excel, 10 email); chuyển PDF/Excel → text có cấu trúc (giữ vị trí trang/ô làm nguồn) | Chạy corpus qua Extractor; đo tỷ lệ trường cần hỏi; sửa prompt theo ca sai | Định tuyến 2 tầng (nhỏ → frontier khi fail); Diff Viewer hiện nguồn trang/ô | Seeding 25→150 NCC qua pipeline; operator duyệt; chạy lại corpus → skip_duplicate | ≥150 NCC rate active; lỗi sau commit <1%; ≤10 phút duyệt/bảng |
| 2 | **AI Service Drafter qua exit gate với corpus request thật** | Code xong, chỉ thiếu dữ liệu; giảm thời gian proposal đầu tiên là đòn bẩy win rate lớn nhất | Gom 20–30 brief thật (ẩn danh) đủ archetype; định nghĩa "đúng" cùng sale senior | Chạy TripAnalyst; sale chấm profile; sửa prompt | Chạy Drafter trên catalog mới; sale chấm từng dòng (đúng/đổi/bỏ); đo `rate_missing` | Bật cho 2 sale dùng thật trên file mới; đo thời gian ra proposal | ≥80% dòng được giữ; 0 giá bịa (máy kiểm); proposal đầu tiên ≤1h ở ≥50% file |
| 3 | **Partner Deep-Query Assistant — bản nội bộ (staff-facing) trên DKB tối thiểu** | Xây "kho" trước "cổng": staff dùng trước để tạo card và bắt lỗi; agent thấy sau khi ≥100 card | Chốt schema card (loại, điểm đến, exposure, nguồn, kiểm chứng, hết hạn); nhập 50 card đầu từ 50 câu hỏi agent gần nhất | Lập chỉ mục card (Postgres vector + metadata); tool đọc card có lọc exposure/hiệu lực | Prompt 3 tầng: có card → trả lời + trích dẫn; không → "chưa kiểm chứng" + mở ticket; cấm suy đoán ở bản nội bộ | Sale dùng trả lời agent qua email (copy có sửa); mỗi câu trả lời mới → nút lưu card | 50→150 card; ≥60% câu hỏi thật được trả lời Tầng 1 từ card; 0 câu trả lời không có trích dẫn |

Ba việc này **không phụ thuộc nhau** về kỹ thuật, có thể chạy song song với 1–2 dev + 1 sale senior +
1 operator; và cùng đóng một kết quả kinh doanh: *báo giá nhanh hơn, đúng hơn, trả lời agent nhanh hơn*.

#### 60–90 ngày

- Đọc phản hồi NCC → trạng thái (gắn vào Confirmation Chasing Queue).
- Phân loại/định tuyến inbox + SLA.
- Pacing/Feasibility check (quy tắc trước, AI giải thích sau).
- Mở Deep-Query cho 3–5 agent thân thiết (Preferred/VIP) khi ≥100 card L1 kiểm chứng 2 người.

#### 6–12 tháng

- Feedback/Pulse/Guide report → theme → Trust Score đề xuất.
- Invoice extraction (15.9b) khi AP ≥50 hóa đơn/tháng.
- Site inspection voice → form; đề xuất card từ Trip Diary.
- CEO brief narrative; giải thích variance.
- Triage sự cố (Phase 3), chỉ sau khi Incident Ladder chạy tay ổn ≥1 mùa.

### 5.9 KPI & kill criteria cho từng tính năng AI

Mỗi tính năng AI bật lên phải có **điều kiện tắt** định trước. Nếu sau 60 ngày không đạt, tắt và
quay về thủ công — không "sửa mãi".

| Tính năng | KPI chính | Ngưỡng giữ | Kill criteria (tắt sau 60 ngày nếu) |
| :-- | :-- | :-- | :-- |
| Rate ingestion | % trường người phải sửa; thời gian duyệt/bảng | ≤15% trường sửa; ≤10 phút | >30% trường sửa hoặc phát hiện ≥2 lỗi giá sau commit/tháng |
| Drafter | % dòng giữ nguyên; thời gian ra proposal | ≥70%; giảm ≥50% | <50% dòng giữ hoặc sale tắt tính năng >50% file |
| Deep-Query | % Tầng 1; % câu trả lời sai (agent/sale báo) | ≥40% Tầng 1; sai <2% | Sai ≥5% hoặc 1 sự cố lộ L2/L3 |
| Đọc phản hồi NCC | Độ chính xác nhãn confirmed | ≥95% | <90% (rủi ro "tưởng confirmed") |
| Feasibility | % cảnh báo đúng (sale đồng ý) | ≥70% | <50% (cảnh báo giả làm sale bỏ qua) |
| Feedback theme | % nhãn người giữ | ≥80% | <60% |
| Triage sự cố | 0 ca hạ mức sai với y tế/an toàn | 0 | ≥1 ca |
| Chi phí | USD/file cho toàn bộ AI | ≤2 USD | >5 USD kéo dài 2 tháng |

---

## Phụ lục A — Thuật ngữ nghiệp vụ dùng trong tài liệu

| Thuật ngữ | Nghĩa trong vận hành DMC |
| :-- | :-- |
| **Contract rate / NET rate** | Giá NCC bán cho DMC, không kèm hoa hồng; bí mật kinh doanh (L3) |
| **Sell rate** | Giá DMC bán cho agent (theo tier) hoặc khách |
| **Release date / option date** | Ngày KS/tàu tự thả chỗ giữ nếu chưa cọc/xác nhận |
| **Cancellation tiers** | Bậc phạt hủy theo số ngày trước dịch vụ |
| **Allotment** | Số phòng/chỗ NCC cam kết giữ cho DMC theo hợp đồng, có release days |
| **Free-sell** | Không có allotment; hỏi từng lần |
| **FOC (Free of charge)** | Chính sách miễn phí (vd 1 free/15 khách trả tiền) — chủ yếu đoàn |
| **Single supplement** | Phụ thu phòng đơn |
| **Half-twin** | Giá per person khi 2 người chung phòng |
| **Compulsory gala dinner** | Bữa tối bắt buộc mua đêm 24/12, 31/12, Tết tại nhiều resort |
| **Peak / seasonal surcharge** | Phụ thu mùa cao/lễ |
| **Guide allowance** | Công tác phí guide/driver: phòng, bữa ăn, vé vào cửa |
| **Tipping norms** | Chuẩn tip theo thị trường; phải báo agent trước |
| **Voucher** | Chứng từ dịch vụ đã xác nhận; khóa nối cho đối soát công nợ NCC |
| **Amendment** | Thay đổi sau khi đã chốt/cọc |
| **Site inspection** | Khảo sát thực địa NCC |
| **Service recovery** | Xử lý phàn nàn/sự cố tại chỗ để khôi phục trải nghiệm |
| **DSO** | Số ngày trung bình thu được tiền từ agent |
| **Parity** | Giá công khai OTA không thấp hơn giá DMC được hưởng/bán |

## Phụ lục B — Ánh xạ tính năng đề xuất → nền tảng hiện có

| Tính năng đề xuất | Đọc từ | Ghi vào | Module mới? |
| :-- | :-- | :-- | :-- |
| Multi-Scenario Pricing | products.quality_tier, rates, costing sheet | costing sheet biến thể | Mở rộng costing |
| Proposal Version Ledger / Amendment Quote | costing_applications, quotation revision, booking lines | bảng phiên bản proposal | Mới, consumer |
| Query Inbox + SLA + Knowledge Cards (DKB) | partner_profiles.tier, destinations | bảng cards, tickets, query log | Mới |
| Trip Diary / Incident Log | booking lines snapshot | bảng diary, incidents; dòng phát sinh → AP adjustment | Mới, consumer |
| Dispatch Templates & Log | booking lines snapshot | dispatch_log (15.12) | Blueprint có sẵn |
| Supplier Trust Score | feedback, guide report, incidents, AP variance, dispatch log | điểm (read-model) + lịch sử | Mới, read-model |
| Site Inspection Report | products, accommodation content | SIR + cập nhật thuộc tính suitability + media | Mới |
| Curated Media Vault | media library (R2) | tag bản quyền/exclusivity/exposure | Mở rộng |
| Trip Companion Page / Daily Pulse | booking snapshot, publication pipeline | pulse log | Mở rộng + mới |
| Cash-flow Calendar | booking lines deadlines, AR (15.10) | read-model | Consumer |
| Margin Waterfall / Variance Report | costing_applications, booking lines, AP/AR | read-model (15.11) | Blueprint có sẵn |
| Agent Profitability Matrix | AR, amendments, query log, incidents | read-model + đề xuất tier | Mới, read-model |
| AI: ingestion PDF/Excel, Deep-Query, phản hồi NCC, feasibility | AI Platform Layer (runtime, guardrails, ai_runs, toolsets chỉ-đọc) | staging / đề xuất, người duyệt | Prompt YAML + tool đọc mới |

## Phụ lục C — Câu hỏi mở Founder cần trả lời trước khi viết spec 15.x tiếp theo

1. Partner Terms chuẩn của DMC (cọc %, bậc hủy, child policy, hiệu lực báo giá) — một bộ hay theo tier?
2. Guide là nhân viên hay cộng tác viên — quyết định cách bắt buộc Trip Diary/Pulse/Card.
3. Ngưỡng bồi thường theo mức (guide/ops/MD) bằng USD cụ thể.
4. Tier agent hiện tại (Preferred/Standard/VIP) gán theo tiêu chí gì — cần để thiết kế SLA và exposure.
5. Ba điểm đến/cung đường ưu tiên xây DKB trước (đề xuất: Hà Nội–Hạ Long–Ninh Bình, Huế–Đà Nẵng–Hội An, Sài Gòn–Mekong).
6. Ai là "người duyệt thứ hai" cho card L1 và corpus AI — phải là người có thẩm quyền nghiệp vụ.
7. Có chấp nhận đường tắt tường minh cho 15.9 (AP) như đã làm với 15.8 để có dữ liệu variance sớm?
8. Ngân sách AI/tháng trần (đề xuất 150 USD) và người theo dõi `ai_runs` hàng tuần.

---

*Tài liệu này là blueprint nghiệp vụ. Mỗi tính năng được Founder chọn sẽ có spec riêng theo khuôn
15.x (scope chốt, bảng, API, test, exit gate, vùng cấm) — không implement trực tiếp từ tài liệu này.*
