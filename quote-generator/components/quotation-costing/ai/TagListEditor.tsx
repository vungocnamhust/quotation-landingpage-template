"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";

export interface TagListEditorProps {
  label: string;
  values: string[];
  placeholder?: string;
  onChange: (values: string[]) => void;
}

/** Small chip-input editor shared by the dietary and guide-languages fields in `TripProfileReviewDialog`. */
export function TagListEditor({ label, values, placeholder, onChange }: TagListEditorProps) {
  const [draft, setDraft] = useState("");

  const addTag = () => {
    const trimmed = draft.trim();
    if (!trimmed || values.includes(trimmed)) {
      setDraft("");
      return;
    }
    onChange([...values, trimmed]);
    setDraft("");
  };

  return (
    <div className="flex flex-col gap-1.5">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>{label}</span>
      <div className="flex flex-wrap items-center gap-1.5">
        {values.map((tag) => (
          <span
            key={tag}
            className={cn(
              getTypographyClassName("caption"),
              "inline-flex items-center gap-1 rounded-full border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-on-surface)]",
            )}
          >
            {tag}
            <button
              type="button"
              onClick={() => onChange(values.filter((value) => value !== tag))}
              className="text-[var(--color-muted)] hover:text-rose-600 cursor-pointer"
              aria-label={`Remove ${tag}`}
            >
              <X size={10} aria-hidden="true" />
            </button>
          </span>
        ))}
        <input
          type="text"
          value={draft}
          placeholder={placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addTag();
            }
          }}
          onBlur={addTag}
          className={cn(
            getTypographyClassName("bodySm"),
            "h-7 min-w-[8rem] flex-1 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2 text-[var(--color-on-surface)]",
          )}
        />
      </div>
    </div>
  );
}

export default TagListEditor;
