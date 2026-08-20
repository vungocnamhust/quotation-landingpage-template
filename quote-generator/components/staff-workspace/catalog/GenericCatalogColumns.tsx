"use client";

import { Tag } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import type { GenericComponentItem } from "../tourComponentsCatalog.ts";
import type { ColumnDef } from "../../ui/data-view/DataTable.tsx";

export function createGenericCatalogColumns(): ColumnDef<GenericComponentItem>[] {
  return [
    {
      key: "name",
      header: "Item Name & Subtitle",
      render: (item) => (
        <div className="flex flex-col gap-1">
          <h4
            className={cn(
              getTypographyClassName("cardTitle"),
              "text-[var(--color-on-surface)]"
            )}
          >
            {item.name}
          </h4>
          <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {item.subtitle}
          </p>
        </div>
      ),
    },
    {
      key: "category",
      header: "Category",
      render: (item) => (
        <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>
          {item.category}
        </span>
      ),
    },
    {
      key: "tags",
      header: "Tags",
      render: (item) => (
        <div className="flex flex-wrap items-center gap-1.5">
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
      ),
    },
    {
      key: "updatedAt",
      header: "Updated",
      render: (item) => (
        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          {item.updatedAt}
        </span>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      headerClassName: "text-right",
      cellClassName: "text-right",
      render: () => (
        <button
          type="button"
          className={cn(
            getTypographyClassName("buttonSecondary"),
            "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-1 text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)] cursor-pointer"
          )}
        >
          Manage
        </button>
      ),
    },
  ];
}
