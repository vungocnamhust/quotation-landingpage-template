# RUN BOOK

Tai lieu nay mo ta cach chay he thong `Create quotation V2` theo 2 moi truong:

- local
- production

Muc tieu la de team co 1 tai lieu thao tac nhanh, dung de:

- dung env file dung cho tung moi truong
- chay migration dung thu tu
- start app dung compose file
- verify health sau khi start

## 1. Files can dung

### Local

- `docker-compose.local.yml`
- `.env.local`
- `.env.local.example`

### Production

- `docker-compose.production.yml`
- `.env.production`
- `.env.production.example`

## 2. Dieu kien tien quyet

Can co san:

- Docker
- Docker Compose plugin
- file env dung voi moi truong

Can luu y:

- khong commit `.env.local`
- khong commit `.env.production`
- production phai dung secret that

## 3. Bien moi truong quan trong

### Database

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `DATABASE_URL_SYNC`

### App

- `ENVIRONMENT`
- `APP_BASE_URL`
- `PUBLIC_BASE_URL`
- `DMC_CORE_URL`

### R2

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`
- `R2_REGION`
- `R2_ENDPOINT`
- `R2_PUBLIC_BASE_URL`

### Media

- `MEDIA_SYNC_DIR`
- `MEDIA_CACHE_DIR`

## 4. Chay local

### Buoc 1. Tao file env

```bash
cp .env.local.example .env.local
```

Can update toi thieu:

- `OPENAI_API_KEY`
- `GITHUB_TOKEN`
- `DEEPSEEK_API_KEY`
- cac bien R2 neu muon test media upload that

### Buoc 2. Build va start

```bash
docker compose -f docker-compose.local.yml up --build
```

Compose local se start:

- `postgres`
- `migrate`
- `app`

Local mapping:

- app: `http://localhost:8111`
- postgres host port: `5433`

### Published quotation preview on localhost

Run the Next.js application locally with its internal API pointed at the local
FastAPI service, then start the loopback-only preview proxy. It forwards only
public quotation, media, and Next static routes while supplying the selected
brand hostname to Next.js; it does not alter DNS or production traffic.

```bash
cd quote-generator
QUOTATION_INTERNAL_API_URL=http://localhost:8111 QUOTE_SERVICE_TOKEN=local-ci-service-token npm run dev
```

In a second terminal from the repository root, choose an active local brand:

```bash
PUBLICATION_PREVIEW_HOSTNAME=journeys.capellatravel.com \
  docker compose -f docker-compose.local-public-preview.yml up --build
```

Open the target at `http://localhost:8180/<locale>/q/<slug>`. The local API
database and R2 credentials must contain the target/release being previewed;
the proxy deliberately never falls back to production.

Stop it with:

```bash
docker compose -f docker-compose.local-public-preview.yml down
```

### Buoc 3. Verify local

Kiem tra app:

```bash
curl http://localhost:8111/health/live
curl http://localhost:8111/health/ready
```

Ky vong:

- `/health/live` tra `200`
- `/health/ready` tra `200`

### Buoc 4. Stop local

```bash
docker compose -f docker-compose.local.yml down
```

Neu muon xoa ca volumes:

```bash
docker compose -f docker-compose.local.yml down -v
```

## 5. Chay production

### Buoc 1. Tao file env

```bash
cp .env.production.example .env.production
```

Can update day du:

- `APP_BASE_URL`
- `PUBLIC_BASE_URL`
- `DMC_CORE_URL`
- `POSTGRES_PASSWORD`
- `OPENAI_API_KEY`
- `GITHUB_TOKEN`
- `DEEPSEEK_API_KEY`
- toan bo R2 credentials

### Buoc 2. Chon image tags va build image

Dat tag bat bien (vi du Git SHA) neu deploy tu registry; mac dinh local chi
phu hop cho may phat trien.

```bash
export QUOTE_APP_IMAGE=registry.example/quotation-app:<git-sha>
export QUOTE_MIGRATE_IMAGE=registry.example/quotation-migrate:<git-sha>
export QUOTE_GENERATOR_IMAGE=registry.example/quotation-generator:<git-sha>
export QUOTE_NGINX_IMAGE=registry.example/quotation-nginx:<git-sha>
```

```bash
docker compose -f docker-compose.production.yml build
```

Python dependencies duoc cai tu `requirements.lock`, nen cold build khong tu
dong chon version moi. Khi can nang cap dependency, resolve lai tren Python
3.11 bang `pip-tools`, review ca graph transitive trong lock file, sau do
chay `python scripts/verify_python_lock.py`, build va E2E truoc khi deploy.

### Buoc 3. Start database

```bash
docker compose -f docker-compose.production.yml up -d postgres
```

### Buoc 4. Chay migration

```bash
docker compose -f docker-compose.production.yml run --rm migrate
```

Chi chay app sau khi migration thanh cong.

### Buoc 5. Start app, renderer va worker

```bash
docker compose -f docker-compose.production.yml up -d app quote-generator publication-worker nginx
```

Production se start:

- `postgres`
- `migrate`
- `app`
- `quote-generator`
- `publication-worker`
- `nginx`

### Buoc 6. Verify production

```bash
curl http://127.0.0.1/health/live
curl http://127.0.0.1/health/ready
```

Neu VPS da gan domain va nginx route dung, co the verify them qua domain:

```bash
curl https://your-domain/health/live
curl https://your-domain/health/ready
```

## 6. Thu tu deploy khuyen nghi

Thu tu an toan:

1. pull code moi
2. review `.env.production`
3. build image moi
4. start hoac giu `postgres`
5. chay `migrate`
6. start `app` va `nginx`
7. verify health
8. test nhanh create quotation, autosave, upload media, publish

## 7. Lenh van hanh thuong dung

### Xem service dang chay

```bash
docker compose -f docker-compose.local.yml ps
docker compose -f docker-compose.production.yml ps
```

### Xem logs

```bash
docker compose -f docker-compose.local.yml logs -f app
docker compose -f docker-compose.production.yml logs -f app
docker compose -f docker-compose.production.yml logs -f nginx
docker compose -f docker-compose.production.yml logs -f postgres
```

### Restart app

```bash
docker compose -f docker-compose.local.yml restart app
docker compose -f docker-compose.production.yml restart app
```

### Re-run migration

```bash
docker compose -f docker-compose.local.yml run --rm migrate
docker compose -f docker-compose.production.yml run --rm migrate
```

## 8. Data migration sau khi deploy

Neu can migrate du lieu cu:

### Migrate quotation

```bash
docker compose -f docker-compose.production.yml run --rm app python3 scripts/migrate_quotation_v2_to_postgres.py
```

Neu can upload publication HTML len R2 trong luc migrate:

```bash
docker compose -f docker-compose.production.yml run --rm app python3 scripts/migrate_quotation_v2_to_postgres.py --upload-publications
```

### Migrate media

```bash
docker compose -f docker-compose.production.yml run --rm app python3 scripts/migrate_media_to_r2.py
```

Sau migration, verify:

- quotation mo duoc trong editor
- media inventory hien du
- publish tao duoc publication moi

## 9. Checklist verify nhanh

Sau khi stack da len, can check:

- `GET /health/live`
- `GET /health/ready`
- tao duoc 1 quotation v2 moi
- editor save duoc
- upload duoc 1 image
- list media inventory tra du lieu
- publish duoc 1 quotation

## 10. Troubleshooting

### `/health/ready` fail

Kiem tra:

- `postgres` da healthy chua
- `DATABASE_URL` co dung khong
- file env dung moi truong chua
- migration da chay xong chua

### App khong ket noi duoc Postgres

Kiem tra:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `DATABASE_URL_SYNC`
- compose file dang dung co dung moi truong khong

### Upload media fail

Kiem tra:

- R2 credentials
- `R2_ENDPOINT`
- `R2_BUCKET`
- `R2_PUBLIC_BASE_URL`

### Migration fail

Kiem tra:

- schema da up-to-date chua
- env DB co dung khong
- du lieu legacy co thieu file bat buoc khong

## 11. Ghi chu van hanh

- local dung `docker-compose.local.yml`
- production dung `docker-compose.production.yml`
- khong dung nham `.env.local` tren VPS
- khong dung nham `.env.production` tren may dev neu dang debug local
- production phai verify health sau moi lan deploy
