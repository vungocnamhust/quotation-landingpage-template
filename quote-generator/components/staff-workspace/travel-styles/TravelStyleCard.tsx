"use client";

import { memo } from "react";
import { Palette, CheckCircle2, Hash } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import type { FlatTravelStyleTag } from "../tourComponentsCatalog";

interface Props {
  tag: FlatTravelStyleTag;
}

export const TravelStyleCard = memo(function TravelStyleCard({ tag }: Props) {
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
              {tag.name_en}
            </h3>
            <p
              className={cn(
                getTypographyClassName("bodySm"),
                "mt-0.5 text-[var(--color-muted)]"
              )}
            >
              {tag.name_vi}
            </p>
          </div>
          <span
            className={cn(
              getTypographyClassName("caption"),
              "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0 bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
            )}
          >
            <CheckCircle2 size={12} />
            <span>Active</span>
          </span>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span
            className={cn(
              getTypographyClassName("caption"),
              "inline-flex items-center gap-1 rounded bg-[var(--color-accent-wash)] px-2.5 py-1 text-[var(--color-accent)]"
            )}
          >
            <Palette size={12} />
            <span>{tag.categoryTitleEn}</span>
          </span>

          <span
            className={cn(
              getTypographyClassName("caption"),
              "inline-flex items-center gap-1 font-mono rounded bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-muted)] border border-[var(--color-border)]"
            )}
          >
            <Hash size={11} />
            <span>{tag.slug}</span>
          </span>
        </div>
      </div>

      <div className="mt-5 flex items-center justify-between border-t border-[var(--color-border)] pt-4">
        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          Order: #{tag.display_order}
        </span>
        <span className={cn(getTypographyClassName("caption"), "font-mono text-[var(--color-muted)]")}>
          {tag.id}
        </span>
      </div>
    </article>
  );
});
