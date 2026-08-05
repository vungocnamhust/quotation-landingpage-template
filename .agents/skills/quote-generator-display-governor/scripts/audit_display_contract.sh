#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT/quote-generator"

echo "[display] running display-system lint"
npm run lint:display-system

echo "[display] checking section boundaries"
bash "$ROOT/.agents/skills/quote-generator-display-governor/scripts/check_section_boundaries.sh"

echo "[display] checking typography contract"
bash "$ROOT/.agents/skills/quote-generator-display-governor/scripts/audit_typography_usage.sh"

echo "[display] running color contract lint"
npm run lint:colors
