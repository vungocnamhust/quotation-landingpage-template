#!/usr/bin/env sh
set -eu

compose_file="docker-compose.production.yml"
docker compose -f "$compose_file" config --quiet
docker compose -f "$compose_file" build nginx
# `nginx -t` resolves upstream hostnames at config-load time.  Use a short
# lived container with explicit loopback aliases so this gate verifies syntax
# without starting, exposing, or mutating production application services.
nginx_image="quotation-production-nginx"
nginx_hosts="${PUBLIC_BRAND_HOSTS:-}"
if [ -z "$nginx_hosts" ] && [ -f .env.production ]; then
  # Read only the non-secret host allowlist from the deployment env file; do
  # not source the file into this verification shell.
  nginx_hosts="$(sed -n 's/^PUBLIC_BRAND_HOSTS=//p' .env.production | tail -n 1)"
fi
nginx_hosts="${nginx_hosts:-journeys.capellatravel.com my.selvarajourneys.com journeys.vietnamsafar.vn}"

render_config() {
  mode="$1"
  if [ "$mode" = "true" ]; then
    docker run --rm \
      --add-host app:127.0.0.1 \
      --add-host quote-generator:127.0.0.1 \
      --add-host dmc-auth-proxy:127.0.0.1 \
      -e DMC_GATEWAY_ENABLED=true \
      -e DMC_AUTH_PROXY_URL=http://dmc-auth-proxy:8120/verify \
      -e PUBLIC_BRAND_HOSTS="$nginx_hosts" \
      "$nginx_image" nginx -T 2>&1
  else
    docker run --rm \
      --add-host app:127.0.0.1 \
      --add-host quote-generator:127.0.0.1 \
      -e DMC_GATEWAY_ENABLED=false \
      -e PUBLIC_BRAND_HOSTS="$nginx_hosts" \
      "$nginx_image" nginx -T 2>&1
  fi
}

direct_rendered="$(render_config false)"
gateway_rendered="$(render_config true)"
printf '%s' "$direct_rendered" | grep -q 'nginx: configuration file .* test is successful'
printf '%s' "$gateway_rendered" | grep -q 'nginx: configuration file .* test is successful'
printf '%s' "$direct_rendered" | grep -q 'auth_request off;'
printf '%s' "$gateway_rendered" | grep -q 'auth_request /_dmc_quote_auth;'
if printf '%s' "$gateway_rendered" | grep -q 'auth_request off;'; then
  echo 'gateway mode must not disable auth_request' >&2
  exit 1
fi
if printf '%s' "$direct_rendered" | grep -q 'proxy_pass http://dmc-auth-proxy'; then
  echo 'direct mode must not retain DMC auth upstream' >&2
  exit 1
fi
for rendered in "$direct_rendered" "$gateway_rendered"; do
  printf '%s' "$rendered" | grep -q 'location / { return 404; }'
  if printf '%s' "$rendered" | grep -A24 'server_name .*journeys' | grep -q 'location /api/'; then
    echo 'public branded hosts must not proxy /api/' >&2
    exit 1
  fi
done
if printf '%s' "$gateway_rendered" | grep -q 'proxy_set_header X-Quote-Service-Token \$http_'; then
  echo 'client service token must never be forwarded' >&2
  exit 1
fi
if printf '%s' "$gateway_rendered" | grep -q 'proxy_set_header X-DMC-Email \$http_'; then
  echo 'client DMC identity headers must never be forwarded' >&2
  exit 1
fi
if printf '%s' "$direct_rendered" | grep -q 'location /api/'; then
  echo 'public branded hosts must not proxy /api/' >&2
  exit 1
fi
docker compose -f "$compose_file" config --format json | python -c '
import json, sys
services = json.load(sys.stdin)["services"]
for name, service in services.items():
    if service.get("ports"):
        raise SystemExit(f"{name} must not publish host ports in production")
'
