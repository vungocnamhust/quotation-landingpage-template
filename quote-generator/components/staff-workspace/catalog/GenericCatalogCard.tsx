"use client";

import { memo } from "react";
import { CheckCircle2, Tag } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import type { GenericComponentItem } from "../tourComponentsCatalog.ts";

interface Props {
  item: GenericComponentItem;
}

export const GenericCatalogCard = memo(function GenericCatalogCard({ item }: Props) {
  return (
    <article className="flex flex-col justify-between rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] transition-all hover:border-[var(--color-border-strong)]">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3
              className={cn(
                getTypographyClassName("cardTitle"),
                "truncate text-[var(--color-on-surface)]"
              )}
            >
              {item.name}
            </h3>
            <p
              className={cn(
                getTypographyClassName("caption"),
                "mt-0.5 text-[var(--color-muted)]"
              )}
            >
              {item.subtitle}
            </p>
          </div>
          <span
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0 bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
            )}
          >
            <CheckCircle2 size={12} />
            <span>{item.status}</span>
          </span>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-1.5">
          {item.tags.map((tag) => (
            <span
              key={tag}
              className={cn(
                getTypographyClassName("caption"),
                "inline-flex items-center gap-1 rounded bg-[var(--color-accent-wash)] px-2 py-0.5 text-[var(--color-accent)]"
              )}
            >
              <Tag size={11} />
              <span>{tag}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="mt-5 flex items-center justify-between border-t border-[var(--color-border)] pt-4">
        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          Updated: {item.updatedAt}
        </span>
        <button
          type="button"
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1.5 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)] cursor-pointer"
          )}
        >
          Manage
        </button>
      </div>
    </article>
  );
});
