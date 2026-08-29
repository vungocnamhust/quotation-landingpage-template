"use client";

import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { groupRowsByDay } from "../../lib/rules/costingReconciler.ts";
import { toCostingRows } from "../../lib/rules/costingAdapter.ts";
import type { CostingWorkbenchResponse } from "./types.ts";
import { ServiceLineRow } from "./ServiceLineRow.tsx";

export interface ServiceLinesTableProps {
  workbench: CostingWorkbenchResponse;
  disabled?: boolean;
  onDeleteLine: (lineId: string) => void;
}

export function ServiceLinesTable({ workbench, disabled, onDeleteLine }: ServiceLinesTableProps) {
  const rows = toCostingRows(workbench);
  const groups = groupRowsByDay(rows);
  const linesById = new Map(workbench.items.map((line) => [line.id, line]));

  if (groups.length === 0) {
    return (
      <div className="rounded-[var(--radius-card)] border border-dashed border-[var(--color-border)] px-4 py-8 text-center">
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>
          No service lines yet — pick a product or add a manual line below.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {groups.map((group) => (
        <div key={group.dayNumber ?? "trip-level"} className="overflow-hidden rounded-[var(--radius-card)] border border-[var(--color-border)]">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2">
            <span className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>
              {group.dayNumber === null ? "Whole trip" : `Day ${group.dayNumber}`}
            </span>
          </div>
          <table className="w-full border-collapse">
            <tbody>
              {group.rows.map((row) => {
                const line = linesById.get(row.id);
                if (!line) return null;
                return (
                  <ServiceLineRow
                    key={row.id}
                    line={line}
                    sheetCurrency={workbench.sheet.currency}
                    disabled={disabled}
                    onDelete={onDeleteLine}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

export default ServiceLinesTable;
