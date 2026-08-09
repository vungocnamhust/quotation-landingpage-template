# 06. Docker Compose And Ops

## 1. Muc tieu

Deploy toan bo he thong len 1 VPS bang Docker Compose, bao gom:

- app
- postgres
- migration
- nginx

## 2. File can tao

```text
docker-compose.yml
docker/
  app/
    Dockerfile
  nginx/
    default.conf
  scripts/
    wait-for-postgres.sh
```

Co the tiep tuc dung `Dockerfile` goc, nhung khuyen nghi tach `docker/app/Dockerfile` cho de quan ly.

## 3. Compose layout

Services:

- `postgres`
- `migrate`
- `app`
- `nginx`

Volumes:

- `postgres_data`
- `media_sync_data`

Networks:

- `quotation_net`

## 4. Compose sample

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: quotation
      POSTGRES_USER: quotation
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U quotation -d quotation"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  migrate:
    build:
      context: .
      dockerfile: docker/app/Dockerfile
    env_file:
      - .env.production
    depends_on:
      postgres:
        condition: service_healthy
    command: ["alembic", "upgrade", "head"]
    restart: "no"

  app:
    build:
      context: .
      dockerfile: docker/app/Dockerfile
    env_file:
      - .env.production
    depends_on:
      postgres:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully
    volumes:
      - media_sync_data:/data/media-sync
    command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8111"]
    restart: unless-stopped

  nginx:
    image: nginx:1.27-alpine
    depends_on:
      - app
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped

volumes:
  postgres_data:
  media_sync_data:
```

## 5. Dockerfile app

Can bao gom:

- system packages cho Pillow neu can
- pip install requirements
- copy app code
- default workdir

Example:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data/media-sync/inbox /data/media-sync/cache

EXPOSE 8111
```

## 6. Nginx reverse proxy

Yeu cau:

- proxy pass toi `app:8111`
- bat `client_max_body_size 20M`
- set timeout hop ly cho upload va publish

Snippet:

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location / {
        proxy_pass http://app:8111;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 7. Production env file

Tao `.env.production` tren VPS, khong commit.

Can co:

```env
ENVIRONMENT=production
APP_BASE_URL=https://quotes.example.com
PUBLIC_BASE_URL=https://quotes.example.com

POSTGRES_PASSWORD=change_me
DATABASE_URL=postgresql+asyncpg://quotation:${POSTGRES_PASSWORD}@postgres:5432/quotation
DATABASE_URL_SYNC=postgresql+psycopg://quotation:${POSTGRES_PASSWORD}@postgres:5432/quotation

R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=quotation-v2
R2_REGION=auto
R2_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
R2_PUBLIC_BASE_URL=https://cdn.example.com

MEDIA_SYNC_DIR=/data/media-sync/inbox
MEDIA_CACHE_DIR=/data/media-sync/cache
```

## 8. Healthchecks

Can them route:

- `GET /health/live`
- `GET /health/ready`

### `/health/live`

- chi tra 200 neu process dang song

### `/health/ready`

- check Postgres query `SELECT 1`
- check R2 config co san

Khong can bat buoc ping R2 moi request readiness, tranh lam healthcheck cham.

## 9. Backup va restore

### Postgres

Can co cron ngoai container hoac host script:

- `pg_dump` hang ngay
- luu file backup ngoai volume neu co the

### R2

- R2 la canonical object store
- can co inventory list va metadata trong Postgres
- backup metadata Postgres la uu tien so 1

## 10. Logging

Khuyen nghi:

- app log ra stdout
- nginx log ra stdout/stderr
- docker logs du de phase 1

Neu can:

- mount `/var/log/quotation` tren host

## 11. Security can toi thieu

- SSH key only
- ufw mo `80/443`, dong port `5432` public
- Postgres khong expose ra internet
- chi app container noi bo noi voi postgres
- rotate R2 credentials neu lo

> **Deployment status.** Compose manifests and Dockerfile exist in this repo,
> but a real VPS/gateway/browser smoke is not established by local lint or
> build. Treat the following as the required deployment gate, not completed
> evidence.

## 12. Runbook deploy

Tren VPS:

1. clone repo
2. tao `.env.production`
3. `docker compose build`
4. `docker compose up -d postgres`
5. `docker compose run --rm migrate`
6. `docker compose up -d app nginx`
7. goi `/health/ready`

## 13. Runbook update

1. pull code moi
2. build image moi
3. chay migration
4. restart `app`
5. verify healthcheck

## 14. Root-cause prevention

Khong duoc deploy app truoc migration neu code moi phu thuoc schema moi.

Compose phai co:

- dependency healthcheck cho postgres
- migration step ro rang
