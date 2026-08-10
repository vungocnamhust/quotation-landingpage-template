#!/usr/bin/env sh
set -eu

base_compose="docker-compose.e2e.yml"
dmc_compose="docker-compose.e2e-dmc.yml"
cleanup() {
  docker compose -f "$base_compose" -f "$dmc_compose" down --volumes --remove-orphans
}
trap cleanup EXIT

docker compose -f "$base_compose" -f "$dmc_compose" build migrate app quote-generator nginx
docker compose -f "$base_compose" -f "$dmc_compose" up --no-build --wait postgres minio minio-init migrate app quote-generator dmc-auth-proxy nginx
docker compose -f "$base_compose" -f "$dmc_compose" run --no-deps --rm e2e-dmc
