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

### First production start — commands only

```bash
cd /opt/quotation-landingpage-template
cp -n .env.production.example .env.production
${EDITOR:-vi} .env.production

docker network inspect dmc-network
docker compose -f docker-compose.production.yml config --quiet
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d postgres
docker compose -f docker-compose.production.yml run --rm migrate

export DESIGNER_ID=td_initial_designer
export DESIGNER_EMAIL=staff@capellatravel.com
export DESIGNER_NAME='Initial Travel Designer'
export DESIGNER_PHONE=''
export DESIGNER_STORAGE_SLUG=initial-travel-designer

docker compose -f docker-compose.production.yml exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U quotation -d quotation \
  -v designer_id="$DESIGNER_ID" \
  -v designer_email="$DESIGNER_EMAIL" \
  -v designer_name="$DESIGNER_NAME" \
  -v designer_phone="$DESIGNER_PHONE" \
  -v designer_storage_slug="$DESIGNER_STORAGE_SLUG" <<'SQL'
INSERT INTO travel_designer_profiles
  (id, email, name, phone, storage_slug, is_active)
VALUES
  (:'designer_id', lower(:'designer_email'), :'designer_name', :'designer_phone', :'designer_storage_slug', true)
ON CONFLICT (email) DO UPDATE
SET name = EXCLUDED.name,
    phone = EXCLUDED.phone,
    storage_slug = EXCLUDED.storage_slug,
    is_active = true;

INSERT INTO travel_designer_brand_defaults (brand_id, designer_profile_id)
SELECT brand_id, :'designer_id'
FROM unnest(ARRAY['capella_travel', 'selvara', 'vietnam_safar']) AS brand_id
WHERE EXISTS (SELECT 1 FROM brands WHERE brands.id = brand_id)
ON CONFLICT (brand_id) DO UPDATE
SET designer_profile_id = EXCLUDED.designer_profile_id;prefillEn
SQL

docker compose -f docker-compose.production.yml up -d app quote-generator publication-worker nginx

cd /opt/dmc-agentic-ai
python scripts/generate-nginx-config.py --output docker/dmc-gateway/nginx.prod.conf
docker exec dmc-gateway nginx -t
docker exec dmc-gateway nginx -s reload

curl --fail --show-error -H 'Host: quote.capellatravel.com' http://127.0.0.1:8008/health/live
curl --fail --show-error -H 'Host: quote.capellatravel.com' http://127.0.0.1:8008/health/ready
test "$(curl --silent --output /dev/null --write-out '%{http_code}' -H 'Host: quotes.capellatravel.com' http://127.0.0.1:8008/not-allowed)" = 404
```

### Public ingress qua DMC Cloudflare Tunnel

Production khong expose port cua quotation Compose ra Internet. DMC's existing
Cloudflare Tunnel forwards both hosts to `http://localhost:8008`, where
`dmc-gateway` forwards them to the `quotation-ingress` Docker alias:

- `quote.capellatravel.com`: Cloudflare Access application required; this is
  the staff workspace host.
- `quotes.capellatravel.com`: no Cloudflare Access application; this is the
  customer-facing fallback host and may serve only `/p/<fallback-slug>` and
  `/media/*`.

After changing `dmc-agentic-ai/configs/route-registry.yml`, regenerate and
reload the DMC gateway config, then add both hostname routes in the existing
Cloudflare Tunnel dashboard/config. Do not add a second tunnel or open VPS
ports 80/443 for the quotation stack.

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

`Warm quote generator build cache` tren GitHub Actions chi cap nhat Buildx
registry cache tai
`ghcr.io/<owner>/quotation-landingpage-template-quote-generator:buildcache`.
No khong publish runtime image de deploy. Cache bao gom multi-stage dependency
layers (`mode=max`), nen VPS van build image tu source vua `git pull` nhung
reuse layer `npm ci` neu `quote-generator/package-lock.json` khong doi.

```bash
git pull --ff-only

# Token nay can read/write package GHCR de import/export BuildKit cache.
printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin

# Image nay duoc build tu source hien tai va load vao Docker daemon cua VPS.
export QUOTE_GENERATOR_IMAGE=quotation-generator:local
export QUOTE_GENERATOR_BUILD_CACHE=ghcr.io/<owner>/quotation-landingpage-template-quote-generator:buildcache
scripts/build_quote_generator_deploy.sh
docker compose -f docker-compose.production.yml up -d --no-deps --force-recreate quote-generator
```

Khong chay `docker compose build quote-generator` sau script tren: script da
build source va da load dung image tag vao VPS. Khi can build cac service khac
tai may deploy, chi ro chung de tranh build lai Next.js:

```bash
docker compose -f docker-compose.production.yml build migrate app nginx
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

`migrate` chi nang schema Alembic va xac nhan database dang o `head`. No khong
duoc doc, archive, hay chuyen doi canonical quotation state; do do co the chay
lai an toan trong moi deployment/recreate.

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

### V2 cutover co phe duyet

Khong coi restart/deploy la cutover. Truoc khi cutover mot database hien co,
operator phai export backup, phan loai toan bo quotation legacy, va chi archive
thu cong sau khi co phe duyet. Khong xoa row hay doi co moi truong de bypass
preflight.

Voi database V2 moi, chay fresh-start gate tường minh (co nay khong nam trong
`.env.production` thuong):

```bash
docker compose -f docker-compose.production.yml --profile cutover run --rm \
  -e V2_PRODUCTION_FRESH_START=true v2-cutover-preflight
```

Voi rich-content conversion da duoc phe duyet, luon xem report truoc; chi chay
apply sau khi report sach va phe duyet da duoc ghi nhan:

```bash
docker compose -f docker-compose.production.yml --profile cutover run --rm v2-rich-content-report
docker compose -f docker-compose.production.yml --profile cutover run --rm v2-rich-content-apply
```

Ca ba job tren la one-shot profile `cutover`; khong service runtime nao phu
thuoc vao chung.

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

### Quotation ingress down sau khi recreate fail

Khong chay them `docker compose up --force-recreate` cho full stack. Start lai
truc tiep cac runtime container dang `Exited`/`Created`, khong kich hoat job
`migrate`:

```bash
cd ~/quotation-landingpage-template
docker ps -a --filter name=quotation-production
docker start quotation-production-app-1
docker start quotation-production-quote-generator-1
docker start quotation-production-nginx-1
```

Bo qua loi `already started`. Xac nhan Nginx co alias tren DMC network, reload
gateway, sau do probe ca staff va sale host:

```bash
docker network inspect dmc-network \
  --format '{{range $id, $c := .Containers}}{{println $c.Name $c.IPv4Address}}{{end}}' \
  | grep quotation-production-nginx
docker exec dmc-gateway getent hosts quotation-ingress
docker exec dmc-gateway nginx -t && docker exec dmc-gateway nginx -s reload
curl -i -H 'Host: quote.capellatravel.com' http://127.0.0.1:8008/
curl -i -H 'Host: sale.capellatravel.com' http://127.0.0.1:8008/
```

`getent` phai tra mot IP `172.19.x.x`. VPS gateway/browser probes la gate van
hanh sau deploy, khong duoc thay the bang unit test local.

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
