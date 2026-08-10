#!/usr/bin/env sh
set -eu

compose_file="docker-compose.e2e.yml"
cleanup() {
  docker compose -f "$compose_file" down --volumes --remove-orphans
}
trap cleanup EXIT

docker compose -f "$compose_file" build
docker compose -f "$compose_file" up --no-build --wait postgres minio minio-init migrate app quote-generator publication-worker nginx
docker compose -f "$compose_file" run --no-deps --rm e2e python -m e2e.test_step10_unpublish_restore_v2
