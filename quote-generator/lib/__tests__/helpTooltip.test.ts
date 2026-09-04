import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  ALL_COSTING_CONCEPT_KEYS,
  COSTING_GLOSSARY,
  getCostingGlossary,
  resolveTooltipContent,
  type CostingConceptKey,
} from "../glossary/costingGlossary.ts";
import { computeTooltipPosition } from "../../components/ui/tooltip/useTooltip.ts";

describe("Costing Glossary System", () => {
  const REQUIRED_16_KEYS: CostingConceptKey[] = [
    "CURRENCY",
    "MARKUP_BPS",
    "ROUND_UP_TO",
    "COST",
    "SELL",
    "MARGIN",
    "AI_DRAFTER",
    "SOURCE_MODE",
    "DAY_NUMBER",
    "QTY_UNIT",
    "QTY_TIME",
    "SERVICE_DATE",
    "PRODUCT_SELECT",
    "SELL_OVERRIDE",
    "SERVICE_NOTE",
    "CREATE_QUOTATION_CTA",
  ];

  it("contains all 16 required costing concept keys plus ADD_LINE", () => {
    for (const key of REQUIRED_16_KEYS) {
      assert.ok(
        ALL_COSTING_CONCEPT_KEYS.includes(key),
        `Expected ALL_COSTING_CONCEPT_KEYS to include ${key}`
      );
      assert.ok(
        key in COSTING_GLOSSARY,
        `Expected COSTING_GLOSSARY to contain key ${key}`
      );
    }
    assert.ok(ALL_COSTING_CONCEPT_KEYS.includes("ADD_LINE"));
  });

  it("ensures all glossary entries have non-empty titles, descriptions, and examples", () => {
    for (const key of ALL_COSTING_CONCEPT_KEYS) {
      const entry = COSTING_GLOSSARY[key];
      assert.ok(entry, `Entry for ${key} should exist`);
      assert.strictEqual(entry.key, key);
      assert.ok(entry.title.length > 0, `Title for ${key} must not be empty`);
      assert.ok(entry.description.length > 10, `Description for ${key} must be descriptive`);
      assert.ok(
        typeof entry.example === "string" && entry.example.length > 0,
        `Example for ${key} must be non-empty`
      );
    }
  });

  it("getCostingGlossary retrieves entry for valid key", () => {
    const entry = getCostingGlossary("MARKUP_BPS");
    assert.strictEqual(entry.key, "MARKUP_BPS");
    assert.match(entry.title, /Markup/i);
    assert.match(entry.description, /Basis Points/i);
  });

  it("getCostingGlossary provides safe fallback for unknown keys", () => {
    const fallback = getCostingGlossary("UNKNOWN_CONCEPT");
    assert.strictEqual(fallback.key, "UNKNOWN_CONCEPT" as CostingConceptKey);
    assert.strictEqual(fallback.title, "UNKNOWN_CONCEPT");
    assert.match(fallback.description, /Khái niệm dự toán/);
  });
});

describe("resolveTooltipContent contract", () => {
  it("resolves content purely from conceptKey when no custom props are provided", () => {
    const resolved = resolveTooltipContent({ conceptKey: "CURRENCY" });
    assert.match(resolved.title, /Tiền tệ cơ sở/);
    assert.match(resolved.content, /Đồng tiền thanh toán/);
    assert.ok(resolved.example);
  });

  it("allows custom title to override glossary title while preserving description and example", () => {
    const resolved = resolveTooltipContent({
      conceptKey: "MARGIN",
      title: "Biên lợi nhuận gộp",
    });
    assert.strictEqual(resolved.title, "Biên lợi nhuận gộp");
    assert.match(resolved.content, /Lợi nhuận gộp và tỷ suất/);
    assert.ok(resolved.example);
  });

  it("allows custom content to override glossary description", () => {
    const resolved = resolveTooltipContent({
      conceptKey: "ROUND_UP_TO",
      content: "Quy tắc làm tròn tuỳ chỉnh cho đại lý",
    });
    assert.match(resolved.title, /Làm tròn giá bán/);
    assert.strictEqual(resolved.content, "Quy tắc làm tròn tuỳ chỉnh cho đại lý");
  });

  it("supports text prop as an alias for content", () => {
    const resolved = resolveTooltipContent({
      conceptKey: "COST",
      text: "Nội dung giải thích qua prop text",
    });
    assert.strictEqual(resolved.content, "Nội dung giải thích qua prop text");
  });

  it("supports completely custom tooltips without conceptKey", () => {
    const resolved = resolveTooltipContent({
      title: "Khái niệm riêng",
      content: "Mô tả giải thích chi tiết cho trường dữ liệu",
      example: "Ví dụ abc",
    });
    assert.strictEqual(resolved.title, "Khái niệm riêng");
    assert.strictEqual(resolved.content, "Mô tả giải thích chi tiết cho trường dữ liệu");
    assert.strictEqual(resolved.example, "Ví dụ abc");
  });
});

describe("computeTooltipPosition algorithm", () => {
  const defaultTrigger = {
    top: 200,
    bottom: 220,
    left: 400,
    right: 420,
    width: 20,
    height: 20,
  };
  const defaultTooltip = { width: 200, height: 80 };

  it("computes standard top placement centered on trigger", () => {
    const pos = computeTooltipPosition({
      triggerRect: defaultTrigger,
      tooltipRect: defaultTooltip,
      placement: "top",
      offset: 10,
      viewportWidth: 1024,
      viewportHeight: 768,
    });
    // Expected top: 200 - 80 - 10 = 110
    // Expected left: 400 + (20 - 200) / 2 = 310
    assert.strictEqual(pos.top, 110);
    assert.strictEqual(pos.left, 310);
    assert.strictEqual(pos.actualPlacement, "top");
  });

  it("computes standard bottom placement centered on trigger", () => {
    const pos = computeTooltipPosition({
      triggerRect: defaultTrigger,
      tooltipRect: defaultTooltip,
      placement: "bottom",
      offset: 10,
      viewportWidth: 1024,
      viewportHeight: 768,
    });
    // Expected top: 220 + 10 = 230
    assert.strictEqual(pos.top, 230);
    assert.strictEqual(pos.left, 310);
    assert.strictEqual(pos.actualPlacement, "bottom");
  });

  it("flips top to bottom when trigger is too close to top edge", () => {
    const triggerNearTop = {
      top: 10,
      bottom: 30,
      left: 400,
      right: 420,
      width: 20,
      height: 20,
    };
    const pos = computeTooltipPosition({
      triggerRect: triggerNearTop,
      tooltipRect: defaultTooltip,
      placement: "top",
      offset: 8,
      viewportWidth: 1024,
      viewportHeight: 768,
    });
    // With trigger top at 10, placing on top would be 10 - 80 - 8 = -78 (< 8 padding)
    // Flips to bottom: top = 30 + 8 = 38
    assert.strictEqual(pos.actualPlacement, "bottom");
    assert.strictEqual(pos.top, 38);
  });

  it("flips bottom to top when trigger is too close to bottom edge", () => {
    const triggerNearBottom = {
      top: 730,
      bottom: 750,
      left: 400,
      right: 420,
      width: 20,
      height: 20,
    };
    const pos = computeTooltipPosition({
      triggerRect: triggerNearBottom,
      tooltipRect: defaultTooltip,
      placement: "bottom",
      offset: 8,
      viewportWidth: 1024,
      viewportHeight: 768,
    });
    // With trigger bottom at 750, placing on bottom would be 750 + 8 = 758 (exceeds 768 - 8)
    // Flips to top: top = 730 - 80 - 8 = 642
    assert.strictEqual(pos.actualPlacement, "top");
    assert.strictEqual(pos.top, 642);
  });

  it("clamps coordinates within viewport boundaries", () => {
    const triggerAtLeftEdge = {
      top: 200,
      bottom: 220,
      left: 2,
      right: 22,
      width: 20,
      height: 20,
    };
    const pos = computeTooltipPosition({
      triggerRect: triggerAtLeftEdge,
      tooltipRect: defaultTooltip,
      placement: "top",
      offset: 8,
      viewportWidth: 1024,
      viewportHeight: 768,
      padding: 10,
    });
    // Unclamped left would be 2 + (20 - 200)/2 = -88
    // Clamped left must be at least padding (10)
    assert.strictEqual(pos.left, 10);
  });
});
