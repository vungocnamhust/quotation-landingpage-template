# Notification Subsystem (Travel.AI Event & Notification Engine)

Module `notification/` là dịch vụ thông báo đa kênh thời gian thực (Real-time Multi-Channel Notification Microservice) và bộ thu nạp sự kiện (Event Ingestion Engine) cho nền tảng Travel Quotation.

---

## 🏛️ 1. Kiến Trúc Phân Lớp (Layered Architecture)

```mermaid
flowchart LR
    subgraph Producers ["Event Producers (Core Backend)"]
        QR[Quote Request Service] -->|Record Event| OB[(Outbox Table)]
        Q[Quotation Service] -->|Record Event| OB
        P[Publication Service] -->|Record Event| OB
        OB -->|Poll & Forward| OR[Outbox Relay]
    end

    subgraph NotificationService ["Notification Microservice (Port 8116)"]
        OR -->|POST /api/v2/events/publish| EP[Event Ingestion API]
        EP --> ORCH[Notification Orchestrator]
        ORCH --> POL[Policy & Preferences]
        ORCH --> NDB[(Notification PostgreSQL DB)]
        ORCH --> BROAD[SSE Broadcaster]
    end

    subgraph Consumers ["Delivery & Clients"]
        BROAD -->|SSE Stream /stream| UI[Next.js Staff Workspace (8115)]
        DW[Delivery Worker] -->|Fetch Pending| NDB
        DW -->|Send| SMTP[Email Provider]
        DW -->|Send| HOOK[Webhook Receivers]
    end
```

### Cấu trúc Thư mục Module:
```text
notification/
├── api/                         # FastAPI Routers & Dependencies
│   ├── v2/
│   │   ├── events.py            # POST /api/v2/events/publish (Event Ingestion)
│   │   ├── notifications.py     # GET/PATCH notifications, mark-all-read
│   │   └── stream.py            # GET /api/v2/notifications/stream (SSE Stream)
│   └── dependencies.py          # Database sessions & Principal auth
├── core/                        # Business Policy & Orchestration
│   ├── orchestrator.py          # Xử lý Domain Event -> Notification Record
│   ├── policy.py                # Chính sách thông báo, quyền ưu tiên & lọc
│   └── preferences.py           # Quản lý opt-in/opt-out của người dùng
├── infrastructure/              # Database & External Adapters
│   ├── db/
│   │   ├── base.py              # Async SQLAlchemy Engine & Session Factory
│   │   └── models.py            # EventLog, Notification, DeliveryAttempt models
│   └── broadcaster.py           # In-Memory SSE Broadcaster & Client Queues
├── workers/                     # Background Delivery Workers
│   └── delivery_worker.py       # Asynchronous multi-channel dispatcher
├── alembic/                     # Database Migrations riêng cho Notification DB
├── alembic.ini                  # Alembic Config
├── main.py                      # FastAPI Application Entrypoint (Port 8116)
└── AGENTS.md                    # 🌟 Quy chuẩn tối thượng cho AI Agents
```

---

## ⚙️ 2. Biến Môi Trường (Environment Variables)

| Tên Biến | Mặc Định Local | Mô Tả |
| :--- | :--- | :--- |
| `NOTIFICATION_PORT` | `8116` | Cổng lắng nghe của FastAPI Notification Service |
| `NOTIFICATION_DATABASE_URL` | `postgresql+asyncpg://quotation:${POSTGRES_PASSWORD}@quotation-local-postgres-1:5432/notification` | Chuỗi kết nối Asyncpg |
| `NOTIFICATION_DATABASE_URL_SYNC` | `postgresql+psycopg://quotation:${POSTGRES_PASSWORD}@quotation-local-postgres-1:5432/notification` | Chuỗi kết nối Psycopg (cho Alembic) |
| `NEXT_PUBLIC_NOTIFICATION_API_URL`| `http://localhost:8116` | URL gọi từ Frontend Next.js Workspace |

---

## 🚀 3. Hướng Dẫn Vận Hành & Khởi Động

### Chạy Local Development (Python):
```bash
# 1. Chạy migration
alembic -c notification/alembic.ini upgrade head

# 2. Khởi động Notification API Service (Port 8116)
uvicorn notification.main:app --host 0.0.0.0 --port 8116 --reload

# 3. Khởi động Background Delivery Worker
python -m notification.workers.delivery_worker
```

### Chạy qua Docker Compose:
```bash
docker compose -f docker-compose.local.yml up -d notification-service notification-worker
```

---

## 🧪 4. Kiểm Thử & Xác Minh (Testing)

```bash
# Chạy toàn bộ test suites của module Notification
PYTHONPATH=. pytest tests/test_notification_api.py

# Kiểm tra Endpoint Health
curl -s http://localhost:8116/health

# Kiểm tra Realtime SSE Stream
curl -s -N --max-time 3 http://localhost:8116/api/v2/notifications/stream
```
