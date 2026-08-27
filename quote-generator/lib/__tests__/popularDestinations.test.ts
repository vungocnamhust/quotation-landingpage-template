import test from "node:test";
import assert from "node:assert/strict";
import { POPULAR_DESTINATIONS } from "../../components/destination/popularDestinations.ts";
import { SEED_DESTINATION_SLUGS } from "./fixtures/seedDestinationSlugs.ts";

test("every POPULAR_DESTINATIONS id resolves to a slug the backend seed actually ships", () => {
  const seeded = new Set(SEED_DESTINATION_SLUGS);
  for (const destination of POPULAR_DESTINATIONS) {
    assert.equal(destination.id, `dst_${destination.slug}`, `${destination.id} must follow the dst_<slug> convention`);
    assert.ok(seeded.has(destination.slug), `${destination.slug} is missing from destination_catalog_seed.py — dropdown would render an empty result`);
  }
});

test("POPULAR_DESTINATIONS has no duplicate ids", () => {
  const ids = POPULAR_DESTINATIONS.map((destination) => destination.id);
  assert.equal(new Set(ids).size, ids.length);
});
