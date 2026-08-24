#!/usr/bin/env sh
set -eu

# Run real-service acceptance in the smallest useful tier.  The stack is
# intentionally kept alive between invocations: PostgreSQL, MinIO, FastAPI,
# the worker and Next are never replaced by mocks, but normal API changes do
# not rebuild a browser/PDF image or recreate the whole Compose project.
#
# Usage:
#   scripts/run_compose_e2e.sh smoke
#   scripts/run_compose_e2e.sh workflow
#   scripts/run_compose_e2e.sh actionable-content
#   scripts/run_compose_e2e.sh actionable-browser artifacts/e2e/actionable-content-plan-report.json
#   scripts/run_compose_e2e.sh full
#   scripts/run_compose_e2e.sh browser-pdf artifacts/e2e/full-report.json
#   scripts/run_compose_e2e.sh down
# Add --build app (or quote-generator/nginx/migrate) only after changing that
# service's image inputs.

compose_file="${COMPOSE_FILE:-docker-compose.e2e.yml}"
tier="${1:-smoke}"
shift || true
artifact_dir="${E2E_ARTIFACT_DIR:-artifacts/e2e}"

usage() {
  echo "usage: $0 {smoke|workflow|actionable-content|actionable-browser|full|browser-pdf|down} [report-file] [--build service ...]" >&2
  exit 64
}

build_services=""
report_file=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --build)
      shift
      [ "$#" -gt 0 ] || usage
      build_services="$build_services $1"
      ;;
    *)
      [ -z "$report_file" ] || usage
      report_file="$1"
      ;;
  esac
  shift || true
done

case "$tier" in
  smoke|workflow|actionable-content|actionable-browser|full|browser-pdf|down) ;;
  *) usage ;;
esac

if [ "$tier" = "down" ]; then
  docker compose -f "$compose_file" down --volumes --remove-orphans
  exit 0
fi

mkdir -p "$artifact_dir"

if [ -n "$build_services" ]; then
  # A source/dependency change is explicit and scoped.  Do not turn this into
  # `docker compose build` for every fast API run.
  docker compose -f "$compose_file" build $build_services
  docker compose -f "$compose_file" up -d --no-deps --force-recreate $build_services
fi

# Start the long-lived disposable dependencies once.  `migrate` is a
# fail-closed job and completes before API services start; it is intentionally
# not hidden inside a full-stack recreate.
docker compose -f "$compose_file" up -d --no-build --wait postgres minio minio-init migrate
docker compose -f "$compose_file" up -d --no-build --wait app publication-worker nginx

case "$tier" in
  smoke)
    docker compose -f "$compose_file" run --rm --no-deps e2e \
      python scripts/test_v2_brochure_workflow.py --tier smoke \
      --report-file /artifacts/smoke-report.json
    ;;
  workflow)
    docker compose -f "$compose_file" run --rm --no-deps e2e \
      python scripts/test_v2_brochure_workflow.py --tier workflow \
      --report-file /artifacts/workflow-report.json
    ;;
  actionable-content)
    docker compose -f "$compose_file" run --rm --no-deps e2e \
      python scripts/test_actionable_content_plan_e2e.py \
      --report-file /artifacts/actionable-content-plan-report.json
    ;;
  actionable-browser)
    [ -n "$report_file" ] || report_file="$artifact_dir/actionable-content-plan-report.json"
    [ -f "$report_file" ] || {
      echo "actionable-browser requires a completed actionable-content report: $report_file" >&2
      exit 66
    }
    report_name=$(basename "$report_file")
    cp "$report_file" "$artifact_dir/$report_name"
    docker compose -f "$compose_file" run --rm --no-deps e2e \
      python -m e2e.actionable_content_plan_browser --report "/artifacts/$report_name" \
      --report-file /artifacts/actionable-browser-report.json
    ;;
  full)
    docker compose -f "$compose_file" run --rm --no-deps e2e \
      python scripts/test_v2_brochure_workflow.py --tier full \
      --report-file /artifacts/full-report.json
    ;;
  browser-pdf)
    [ -n "$report_file" ] || report_file="$artifact_dir/full-report.json"
    [ -f "$report_file" ] || {
      echo "browser-pdf requires a completed full report: $report_file" >&2
      exit 66
    }
    report_name=$(basename "$report_file")
    cp "$report_file" "$artifact_dir/$report_name"
    docker compose -f "$compose_file" run --rm --no-deps e2e \
      python -m e2e.browser_pdf_compose_v2 --report "/artifacts/$report_name" \
      --report-file /artifacts/browser-pdf-report.json
    ;;
esac
