"use client";

import { Trash2 } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { ServiceLineProfile } from "./types.ts";
import { formatMinorAmount as formatMinor } from "../../lib/moneyFormat.ts";

export interface ServiceLineRowProps {
  line: ServiceLineProfile;
  sheetCurrency?: string;
  disabled?: boolean;
  onDelete: (lineId: string) => void;
}

export function ServiceLineRow({ line, sheetCurrency = "USD", disabled, onDelete }: ServiceLineRowProps) {
  const isCatalogLine = Boolean(line.product_id);
  const hasFx = line.cost_currency !== sheetCurrency;

  return (
    <tr className="border-b border-[var(--color-border)] last:border-b-0">
      <td className="px-3 py-2">
        <div className="flex flex-col">
          <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{line.title}</span>
          <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
            {[line.category, line.subcategory].filter(Boolean).join(" · ")}
            {isCatalogLine ? " · catalog" : " · manual"}
            {hasFx ? ` · fx from ${formatMinor(line.unit_cost_minor, line.cost_currency)}` : ""}
          </span>
        </div>
      </td>
      <td className={cn(getTypographyClassName("caption"), "px-3 py-2 text-[var(--color-muted)]")}>
        {line.qty_unit} {line.unit} × {line.qty_time} {line.time_basis}
      </td>
      <td className={cn(getTypographyClassName("bodySm"), "px-3 py-2 text-right text-[var(--color-on-surface)]")}>
        {formatMinor(line.cost_minor, sheetCurrency)}
      </td>
      <td className={cn(getTypographyClassName("bodySm"), "px-3 py-2 text-right text-[var(--color-accent)]")}>
        {formatMinor(line.sell_minor, sheetCurrency)}
      </td>
      <td className="px-3 py-2 text-right">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onDelete(line.id)}
          className="rounded-full p-1.5 text-[var(--color-muted)] transition-colors hover:bg-[var(--color-surface-muted)] hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
          aria-label={`Delete line ${line.title}`}
        >
          <Trash2 size={14} aria-hidden="true" />
        </button>
      </td>
    </tr>
  );
}

export default ServiceLineRow;
