#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT"

TARGETS=(
  "quote-generator/components/display"
  "quote-generator/app"
)

echo "[display] checking section boundaries"

if rg -n "useBrand\\(" "${TARGETS[@]}"; then
  echo "Found forbidden useBrand() usage in display layer"
  exit 1
fi

if rg -n "BRANDS_DATA" quote-generator/components/display quote-generator/app; then
  echo "Found forbidden BRANDS_DATA usage in display layer"
  exit 1
fi

if rg -n "no-print|no-screen" quote-generator/components/display quote-generator/app; then
  echo "Found forbidden no-print/no-screen visibility logic in display layer"
  exit 1
fi

echo "[display] section boundaries look clean"
