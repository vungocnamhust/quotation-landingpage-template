import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

describe('TravelStyleSelect normalization & deduplication logic', () => {
  function parseSelectedTags(value: string | null | undefined): string[] {
    const raw = (value ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    return Array.from(new Set(raw));
  }

  function addCustomTags(selectedTags: string[], customTagInput: string): string[] {
    const newTags = customTagInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (newTags.length === 0) return selectedTags;
    return Array.from(new Set([...selectedTags, ...newTags]));
  }

  function toggleTag(selectedTags: string[], tagName: string): string[] {
    if (selectedTags.includes(tagName)) {
      return selectedTags.filter((t) => t !== tagName);
    }
    return [...selectedTags, tagName];
  }

  it('deduplicates duplicate tag inputs such as "6, 6"', () => {
    const tags = parseSelectedTags("6, 6");
    assert.deepEqual(tags, ["6"]);
  });

  it('deduplicates mixed duplicate tags with whitespace', () => {
    const tags = parseSelectedTags("Family, 6, 6, Cultural & Heritage, Family,   ");
    assert.deepEqual(tags, ["Family", "6", "Cultural & Heritage"]);
  });

  it('handles null, undefined, and empty string safely', () => {
    assert.deepEqual(parseSelectedTags(null), []);
    assert.deepEqual(parseSelectedTags(undefined), []);
    assert.deepEqual(parseSelectedTags(""), []);
    assert.deepEqual(parseSelectedTags("  , ,  "), []);
  });

  it('adds comma-separated custom tags without duplicates', () => {
    const initial = ["Family", "6"];
    const updated = addCustomTags(initial, "6, Luxury, Adventure & Trekking");
    assert.deepEqual(updated, ["Family", "6", "Luxury", "Adventure & Trekking"]);
  });

  it('toggles tags on and off cleanly without duplicates', () => {
    let tags = parseSelectedTags("6, Family");
    // Toggle off "6"
    tags = toggleTag(tags, "6");
    assert.deepEqual(tags, ["Family"]);
    // Toggle on "6"
    tags = toggleTag(tags, "6");
    assert.deepEqual(tags, ["Family", "6"]);
  });
});
