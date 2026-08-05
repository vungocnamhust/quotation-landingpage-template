#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$ROOT/quote-generator"

echo "[display] running typography lint"
npm run lint:typography

status=0

if ! rg -n "next/font/(google|local)" app/fonts.ts >/dev/null; then
  echo "[display] typography audit failed: app/fonts.ts must own next/font loading"
  status=1
fi

fail_if_found() {
  local label="$1"
  local pattern="$2"
  shift 2

  if rg -n --glob '*.{css,tsx,ts}' -g '!app/fonts.ts' "$pattern" "$@"; then
    echo "[display] typography audit failed: ${label}"
    status=1
  fi
}

fail_if_found \
  "font loading or aliases outside the typography owner" \
  '@font-face|--font-(cormorant|montserrat|jost|allura)|font-family:[[:space:]]*(Allura|Jost|Montserrat|Cormorant[[:space:]]Garamond)' \
  app components

fail_if_found \
  "raw CSS typography metrics in app/components" \
  '(^|[[:space:]])font(-size|-weight|-style|:)|(^|[[:space:]])line-height:|(^|[[:space:]])letter-spacing:|(^|[[:space:]])text-transform:' \
  app components

fail_if_found \
  "hardcoded typographic measure in JSX" \
  'max-w-\[[^]]+ch\]' \
  app components

if rg -n '<(Kicker|DisplayTitle|BodyCopy|MetaText|PriceText|LabelText|QuoteText|ActionButton)[^>]*variant="[A-Za-z]' components/display/molecules.tsx; then
  echo "[display] typography audit failed: molecule-level variant literal"
  status=1
fi

if rg -n "typo-body-sm" components/display/atoms.tsx; then
  echo "[display] typography audit failed: TextLink or atom has a fixed typography class"
  status=1
fi

exit "$status"
