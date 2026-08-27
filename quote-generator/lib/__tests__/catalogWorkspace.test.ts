import assert from "node:assert/strict";
import test from "node:test";
import {
  CATEGORIES,
  PRODUCT_CATEGORY_BY_SLOT,
} from "../../components/staff-workspace/tourComponentsCatalog.ts";
import { createProductDraft } from "../../components/product/productDraft.ts";
import { DEFAULT_CHARGE_UNIT_BY_CATEGORY } from "../../components/product/types.ts";

test("Product Catalog exposes the planned eight tabs in order", () => {
  assert.deepEqual(
    CATEGORIES.map((category) => category.key),
    [
      "hotels",
      "cars",
      "guides",
      "activities",
      "dining",
      "visa",
      "destinations",
      "suppliers",
    ],
  );
});

test("commercial catalog tabs cover each backend category once and have the correct create preset", () => {
  const categories = Object.values(PRODUCT_CATEGORY_BY_SLOT).flat();
  assert.equal(new Set(categories).size, categories.length);
  assert.deepEqual(
    [...categories].sort(),
    Object.keys(DEFAULT_CHARGE_UNIT_BY_CATEGORY).sort(),
  );
  assert.deepEqual(
    Object.fromEntries(
      Object.entries(PRODUCT_CATEGORY_BY_SLOT).map(([key, values]) => [
        key,
        values[0],
      ]),
    ),
    {
      hotels: "accommodation",
      cars: "transportation",
      guides: "guide",
      activities: "experience",
      dining: "meal",
      visa: "visa",
    },
  );
});

test("new product drafts persist category charge defaults instead of display-only fallbacks", () => {
  for (const [category, [unit, timeBasis]] of Object.entries(
    DEFAULT_CHARGE_UNIT_BY_CATEGORY,
  )) {
    const draft = createProductDraft(
      category as keyof typeof DEFAULT_CHARGE_UNIT_BY_CATEGORY,
      "dest_hanoi",
    );
    assert.equal(draft.category, category);
    assert.equal(draft.destination_id, "dest_hanoi");
    assert.equal(draft.unit, unit);
    assert.equal(draft.time_basis, timeBasis);
  }
});
