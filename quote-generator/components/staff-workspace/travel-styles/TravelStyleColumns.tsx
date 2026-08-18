"use client";

import { Palette, CheckCircle2 } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography";
import { cn } from "../../../utils/cn";
import type { FlatTravelStyleTag } from "../tourComponentsCatalog";
import type { ColumnDef } from "../../ui/data-view/DataTable";

export function createTravelStyleColumns(): ColumnDef<FlatTravelStyleTag>[] {
  return [
    {
      key: "name",
      header: "Tag Name (EN / VI)",
      render: (tag) => (
        <div className="flex flex-col gap-0.5">
          <h4
            className={cn(
              getTypographyClassName("cardTitle"),
              "text-[var(--color-on-surface)]"
            )}
          >
            {tag.name_en}
          </h4>
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {tag.name_vi}
          </p>
        </div>
      ),
    },
    {
      key: "category",
      header: "Category Group",
      render: (tag) => (
        <span
          className={cn(
            getTypographyClassName("caption"),
            "inline-flex items-center gap-1 rounded bg-[var(--color-accent-wash)] px-2.5 py-1 text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_20%,transparent)]"
          )}
        >
          <Palette size={12} />
          <span>{tag.categoryTitleEn}</span>
        </span>
      ),
    },
    {
      key: "slug",
      header: "Slug ID",
      render: (tag) => (
        <span
          className={cn(
            getTypographyClassName("caption"),
            "font-mono rounded bg-[var(--color-surface-muted)] px-2 py-0.5 text-[var(--color-muted)] border border-[var(--color-border)]"
          )}
        >
          {tag.slug}
        </span>
      ),
    },
    {
      key: "display_order",
      header: "Order",
      render: (tag) => (
        <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
          #{tag.display_order}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: () => (
        <span
          className={cn(
            getTypographyClassName("caption"),
            "flex items-center gap-1 rounded-full px-2.5 py-0.5 shrink-0 inline-self-start bg-[var(--color-accent-wash)] text-[var(--color-accent)] border border-[color-mix(in_srgb,var(--color-accent)_30%,transparent)] shadow-2xs"
          )}
        >
          <CheckCircle2 size={12} />
          <span>Active</span>
        </span>
      ),
    },
  ];
}
