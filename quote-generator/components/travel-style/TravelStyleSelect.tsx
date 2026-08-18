"use client";

import { useState } from "react";
import { Tag, Plus, X, Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography";
import { cn } from "../../utils/cn";
import type { TravelStyleSelectProps } from "./types";
import { useTravelStyles } from "./useTravelStyles";

export function TravelStyleSelect({
  label = "Travel Style",
  value,
  onChange,
  disabled = false,
  size = "md",
  allowCustom = true,
  className,
  helperText,
}: TravelStyleSelectProps) {
  const { categories } = useTravelStyles();
  const [activeCategory, setActiveCategory] = useState<string>("group_composition");
  const [customTag, setCustomTag] = useState("");

  const currentValue = value ?? "";
  const selectedTags = currentValue
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const toggleTag = (tagName: string) => {
    if (disabled) return;
    let next: string[];
    if (selectedTags.includes(tagName)) {
      next = selectedTags.filter((t) => t !== tagName);
    } else {
      next = [...selectedTags, tagName];
    }
    onChange?.(next.length > 0 ? next.join(", ") : null);
  };

  const handleAddCustomTag = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customTag.trim() || disabled) return;
    const tagToAdd = customTag.trim();
    if (!selectedTags.includes(tagToAdd)) {
      const next = [...selectedTags, tagToAdd];
      onChange?.(next.join(", "));
    }
    setCustomTag("");
  };

  const removeTag = (tagName: string) => {
    if (disabled) return;
    const next = selectedTags.filter((t) => t !== tagName);
    onChange?.(next.length > 0 ? next.join(", ") : null);
  };

  const currentCategoryObj = categories.find((c) => c.category_id === activeCategory) || categories[0];

  return (
    <div className={cn("flex flex-col gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-2xs", className)}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border)] pb-2.5">
        <div className="flex items-center gap-2">
          <Tag size={16} className="text-[var(--color-accent)]" aria-hidden="true" />
          <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
            {label}
          </span>
        </div>

        {selectedTags.length > 0 && (
          <span className={cn(getTypographyClassName("caption"), "rounded-full bg-[var(--color-accent-wash)] px-2.5 py-0.5 text-[var(--color-accent)]")}>
            {selectedTags.length} selected
          </span>
        )}
      </div>

      {/* Selected Tags Summary Bar */}
      {selectedTags.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-2">
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)] mr-1 flex items-center gap-1")}>
            <Sparkles size={12} className="text-[var(--color-accent)]" aria-hidden="true" />
            <span>Applied:</span>
          </span>
          {selectedTags.map((tag, idx) => (
            <span
              key={idx}
              className={cn(
                getTypographyClassName("caption"),
                "inline-flex items-center gap-1 rounded-full border border-[var(--color-accent)] bg-[var(--color-accent-wash)] px-2.5 py-0.5 text-[var(--color-accent)]"
              )}
            >
              <span>{tag}</span>
              {!disabled && (
                <button
                  type="button"
                  onClick={() => removeTag(tag)}
                  className="rounded-full p-0.5 hover:bg-[var(--color-accent)]/20 cursor-pointer"
                  aria-label={`Remove ${tag}`}
                >
                  <X size={10} aria-hidden="true" />
                </button>
              )}
            </span>
          ))}
        </div>
      )}

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-[var(--color-border)] pb-2">
        {categories.map((cat) => {
          const isActive = cat.category_id === activeCategory;
          const count = cat.tags.filter((t) => selectedTags.includes(t.name_en)).length;

          return (
            <button
              key={cat.category_id}
              type="button"
              disabled={disabled}
              onClick={() => setActiveCategory(cat.category_id)}
              className={cn(
                getTypographyClassName("caption"),
                "flex items-center gap-1.5 rounded-[var(--radius-button)] px-3 py-1.5 transition-all cursor-pointer",
                isActive
                  ? "bg-[var(--color-contrast)] text-white shadow-2xs"
                  : "bg-[var(--color-surface-muted)] text-[var(--color-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-on-surface)]"
              )}
            >
              <span>{cat.title_en}</span>
              {count > 0 && (
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "flex h-4 w-4 items-center justify-center rounded-full",
                    isActive ? "bg-white text-[var(--color-contrast)]" : "bg-[var(--color-accent)] text-white"
                  )}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tag Chips for Active Category */}
      {currentCategoryObj && (
        <div className="flex flex-wrap gap-2 pt-1">
          {currentCategoryObj.tags.map((tag) => {
            const isSelected = selectedTags.includes(tag.name_en);

            return (
              <button
                key={tag.id}
                type="button"
                disabled={disabled}
                onClick={() => toggleTag(tag.name_en)}
                className={cn(
                  getTypographyClassName("bodySm"),
                  size === "sm" ? "px-2.5 py-1" : "px-3 py-1.5",
                  "rounded-[var(--radius-button)] border text-left transition-all cursor-pointer",
                  isSelected
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-wash)] text-[var(--color-accent)] shadow-2xs"
                    : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-muted)]",
                  disabled ? "opacity-60 cursor-not-allowed" : ""
                )}
              >
                <span>{tag.name_en}</span>
                <span className={cn(getTypographyClassName("caption"), "ml-1.5 text-[var(--color-muted)] opacity-70")}>
                  ({tag.name_vi})
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Custom Tag Input */}
      {allowCustom && !disabled && (
        <div className="flex items-center gap-2 pt-1 border-t border-[var(--color-border)]">
          <input
            type="text"
            placeholder="Add custom travel preference..."
            value={customTag}
            onChange={(e) => setCustomTag(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleAddCustomTag(e);
              }
            }}
            className={cn(
              getTypographyClassName("bodySm"),
              "min-h-9 flex-1 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] placeholder:text-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-focus)]"
            )}
          />
          <button
            type="button"
            disabled={!customTag.trim()}
            onClick={handleAddCustomTag}
            className={cn(
              getTypographyClassName("buttonSecondary"),
              "flex min-h-9 items-center gap-1 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] disabled:opacity-40 cursor-pointer"
            )}
          >
            <Plus size={14} aria-hidden="true" />
            <span>Add</span>
          </button>
        </div>
      )}

      {helperText ? (
        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>{helperText}</span>
      ) : null}
    </div>
  );
}
