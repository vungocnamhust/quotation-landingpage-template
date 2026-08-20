"use client";

import React from "react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";

export interface ColumnDef<T> {
  key: string;
  header: React.ReactNode;
  headerClassName?: string;
  cellClassName?: string;
  render: (item: T, index: number) => React.ReactNode;
}

export interface DataTableProps<T> {
  items: T[];
  columns: ColumnDef<T>[];
  keyExtractor: (item: T, index: number) => string;
  tableClassName?: string;
  containerClassName?: string;
}

export function DataTable<T>({
  items,
  columns,
  keyExtractor,
  tableClassName,
  containerClassName,
}: DataTableProps<T>) {
  return (
    <div
      className={cn(
        "overflow-x-auto rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--elevation-card)]",
        containerClassName
      )}
    >
      <table
        className={cn(
          "w-full text-left border-collapse min-w-[700px]",
          tableClassName
        )}
      >
        <thead>
          <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-muted)]">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  getTypographyClassName("label"),
                  "px-4 py-3",
                  col.headerClassName
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-border)]">
          {items.map((item, index) => {
            const rowKey = keyExtractor(item, index);
            return (
              <tr
                key={rowKey}
                className="group transition-colors hover:bg-[var(--color-surface-hover)]"
              >
                {columns.map((col) => (
                  <td
                    key={`${rowKey}-${col.key}`}
                    className={cn("px-4 py-3.5 align-middle", col.cellClassName)}
                  >
                    {col.render(item, index)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
