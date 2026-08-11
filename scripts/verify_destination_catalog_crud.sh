#!/usr/bin/env bash
set -euo pipefail

# Run against the Compose/API environment after `alembic upgrade head`.
# Set DESTINATION_AUTH_HEADER to an authenticated quote-admin identity in
# gateway environments, for example: `X-DMC-Email: admin@example.test`.
api_base="${DESTINATION_API_BASE:-http://localhost:8111}"
auth_header="${DESTINATION_AUTH_HEADER:-X-DMC-Email: quote-admin@example.test}"
slug="map-anchor-check-$(date +%s)"

request() {
  curl --fail-with-body --silent --show-error -H "$auth_header" -H 'Content-Type: application/json' "$@"
}

created="$(request -X POST "$api_base/api/v2/destinations" --data "{\"canonicalName\":\"Map Anchor Check\",\"slug\":\"$slug\",\"aliases\":[\"Map Anchor Check Alias\"],\"countrySlug\":\"vietnam\",\"latitude\":21.0285,\"longitude\":105.8542}")"
destination_id="$(printf '%s' "$created" | jq -er '.id')"
test "$(printf '%s' "$created" | jq -r '.latitude')" = "21.0285"

read_back="$(request "$api_base/api/v2/destinations/$destination_id")"
test "$(printf '%s' "$read_back" | jq -r '.slug')" = "$slug"

updated="$(request -X PUT "$api_base/api/v2/destinations/$destination_id" --data "{\"canonicalName\":\"Map Anchor Check Updated\",\"slug\":\"$slug\",\"aliases\":[\"Map Anchor Check Alias\"],\"countrySlug\":\"vietnam\",\"latitude\":21.1,\"longitude\":105.9}")"
test "$(printf '%s' "$updated" | jq -r '.latitude')" = "21.1"

status="$(request -X PATCH "$api_base/api/v2/destinations/$destination_id/status" --data '{"isActive":false}')"
test "$(printf '%s' "$status" | jq -r '.isActive')" = "false"

if request -X POST "$api_base/api/v2/destinations" --data "{\"canonicalName\":\"Invalid Anchor\",\"slug\":\"$slug-invalid\",\"latitude\":91,\"longitude\":105}"; then
  echo "Expected invalid coordinate payload to fail" >&2
  exit 1
fi

echo "Destination catalog CRUD contract passed for $destination_id"
