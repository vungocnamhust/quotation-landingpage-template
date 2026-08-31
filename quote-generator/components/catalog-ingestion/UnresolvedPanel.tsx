"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { IngestionUnresolvedItem } from "./types.ts";

interface Props {
  items: IngestionUnresolvedItem[];
  acknowledged: boolean;
  onAcknowledgedChange: (value: boolean) => void;
}

export function UnresolvedPanel({ items, acknowledged, onAcknowledgedChange }: Props) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (items.length === 0) return null;

  return (
    <section className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-rose-500/50 bg-rose-500/5 p-5 shadow-xs">
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex items-center gap-2 text-left"
      >
        {isExpanded ? <ChevronDown size={18} aria-hidden="true" /> : <ChevronRight size={18} aria-hidden="true" />}
        <h2 className={cn(getTypographyClassName("cardTitle"), "text-rose-600 dark:text-rose-400")}>
          {items.length} item(s) could not be resolved automatically
        </h2>
      </button>

      {isExpanded ? (
        <ul className="flex flex-col gap-3">
          {items.map((item, index) => (
            <li key={index} className="rounded-[var(--radius-input)] border border-rose-500/30 bg-[var(--color-surface)] p-3">
              <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{item.description}</p>
              {item.reason ? (
                <p className={cn(getTypographyClassName("caption"), "mt-1 text-[var(--color-muted)]")}>{item.reason}</p>
              ) : null}
              {item.source_quote ? (
                <blockquote
                  className={cn(
                    getTypographyClassName("quote"),
                    "mt-1 border-l-2 border-rose-500/40 pl-3 text-[var(--color-muted)]",
                  )}
                >
                  “{item.source_quote}”
                </blockquote>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
          Expand to review before committing.
        </p>
      )}

      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={acknowledged}
          disabled={!isExpanded}
          onChange={(event) => onAcknowledgedChange(event.target.checked)}
          className="h-4 w-4 accent-rose-600"
        />
        <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
          I reviewed the unresolved items above and want to commit the rest of this batch anyway.
        </span>
      </label>
    </section>
  );
}
