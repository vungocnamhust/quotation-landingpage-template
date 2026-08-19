# Notification Subsystem — Master Guidelines & Vibe Coding Rules

> **Dành cho AI Assistants (Antigravity, Codex, Claude Code, Cursor, Windsurf)**: Đây là tài liệu quy chuẩn tối thượng (Single Source of Truth) định hình toàn bộ kiến trúc, hợp đồng dữ liệu và phong cách lập trình cho module `notification/`. Mọi thay đổi code liên quan đến sự kiện, thông báo và worker **BẮT BUỘC** tuân thủ tuyệt đối các quy tắc dưới đây.

---

## 🏛️ 1. Bản Đồ Tư Duy Module (Notification Subsystem Mental Model)

Module `notification/` là một microservice độc lập chịu trách nhiệm:
1. **Event Ingestion (`api/v2/events.py`)**: Tiếp nhận các Domain/Integration Events từ các nghiệp vụ chính (Quotation, Quote Request, Publications) qua Transactional Outbox.
2. **Notification & Preference Engine (`core/orchestrator.py`, `core/policy.py`)**: Đánh giá người nhận (`recipient_email`), kiểm tra cài đặt thông báo và ghi bản ghi `Notification` vào database.
3. **Delivery Worker (`workers/delivery_worker.py`)**: Xử lý gửi thông báo đa kênh (SSE in-app, Email, Webhook) với cơ chế retry, idempotency và error isolation.
4. **Real-time SSE Broadcaster (`infrastructure/broadcaster.py`, `api/v2/stream.py`)**: Duy trì kết nối Server-Sent Events real-time đến trình duyệt của nhân viên và khách hàng.

---

## 📜 2. 5 Hợp Đồng Bất Biến (Core Invariant Contracts)

### 🔒 Contract 1: No Direct Dispatch & Transactional Outbox
- **Quy tắc**: Các domain service ở backend chính (`services/quote_request_service.py`, `services/facts_resolver.py`, v.v.) **TUYỆT ĐỐI KHÔNG** được gửi Email/SMS/Push trực tiếp hoặc import trực tiếp `notification.workers`.
- **Thực thi**: Domain service chỉ ghi bản ghi sự kiện vào bảng `outbox_events` trong cùng một database transaction. `services/outbox_relay.py` sẽ đảm nhiệm việc chuyển tiếp sự kiện sang Notification Service (`POST /api/v2/events/publish`).

### 🔒 Contract 2: Database & Schema Isolation
- **Quy tắc**: Module `notification` sở hữu database riêng (`notification`) và thư mục migration riêng (`notification/alembic/`).
- **Nghiêm cấm**: Tuyệt đối không đọc trực tiếp bảng dữ liệu riêng của service khác (như bảng `quotations`, `quote_requests`). Mọi dữ liệu cần thiết để tạo thông báo phải nằm trọn vẹn trong `event.payload_json`.

### 🔒 Contract 3: Notification State vs Delivery State
- **Bản ghi Notification (Inbox hiển thị)**: Quản lý trạng thái xem của người dùng (`is_read`, `read_at`). Bản ghi này bất biến và không bị ảnh hưởng nếu một kênh gửi bên ngoài (ví dụ SMTP email) thất bại.
- **Bản ghi Delivery Attempt (Nhật ký phát hành)**: Quản lý trạng thái gửi từng kênh (`pending`, `delivered`, `failed`, `retry_count`).

### 🔒 Contract 4: Real-time SSE Broadcaster & Non-blocking Stream
- **Heartbeat**: Luôn duy trì gửi `comment="ping"` mỗi 20 giây khi queue rỗng để giữ kết nối HTTP SSE không bị timeout bởi proxy / load balancer.
- **Disconnect Handling**: Phải bắt `asyncio.CancelledError` và `GeneratorExit` trong stream generator để tự động `unsubscribe` queue khỏi broadcaster, chống rò rỉ bộ nhớ (memory leak).

### 🔒 Contract 5: Multi-Network DNS & Connection String SSOT
- **Docker DNS**: Trong môi trường Docker đa mạng (`quotation_net`, `dmc-network`), các connection string **BẮT BUỘC** dùng hostname định danh rõ ràng `quotation-local-postgres-1:5432`, không dùng `postgres:5432` để tránh xung đột DNS.
- **Dynamic Credentials**: Luôn sử dụng biến môi trường `${POSTGRES_PASSWORD:-quotation_local_password}`.

---

## 📋 3. Bảng Phân Loại Sự Kiện (Event Taxonomy Catalog)

| Event Type (`event_type`) | Aggregate Type | Mô Tả Nghiệp Vụ | Action URL Mặc Định |
| :--- | :--- | :--- | :--- |
| `quote_request.created` | `quote_request` | Khách hàng/Advisor gửi yêu cầu báo giá mới | `/workspace/requests/{id}` |
| `quote_request.edited` | `quote_request` | Cập nhật thông tin yêu cầu báo giá | `/workspace/requests/{id}` |
| `quote_request.converted` | `quote_request` | Yêu cầu được chuyển đổi thành Quotation | `/workspace/quotations/{id}` |
| `quotation.created` | `quotation` | Bản nháp báo giá mới được tạo | `/workspace/quotations/{id}` |
| `quotation.publication.completed` | `quotation` | Brochure được phát hành online thành công | `/workspace/quotations/{id}` |

---

## 🛠️ 4. Chỉ Dẫn Kỹ Năng Kèm Theo (Skills Reference)

Khi làm việc trong module này, hãy kích hoạt các skill tương ứng:
- **`notification-core`**: Thiết kế cấu trúc event mới, policy, inbox semantics, boundary.
- **`notification-fastapi`**: Triển khai router, dependency injection, asyncpg database models.
- **`notification-reliability`**: Tối ưu retry, idempotency key, outbox relay, DLQ.
- **`notification-review`**: Thực hiện checklist kiểm duyệt trước khi merge code.

---

## 🧪 5. Quy Trình Tự Kiểm Thử (Self-Verification Protocol)

1. **Chạy Unit & Integration Tests**:
   ```bash
   PYTHONPATH=. pytest tests/test_notification_api.py
   ```
2. **Kiểm tra Migration**:
   ```bash
   alembic -c notification/alembic.ini upgrade head
   ```
3. **Kiểm tra Live Service Health & SSE Stream**:
   ```bash
   curl -f http://localhost:8116/health
   curl -f -N --max-time 3 http://localhost:8116/api/v2/notifications/stream
   ```
