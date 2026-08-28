"use client";

import { Copy } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { DataTable, type ColumnDef } from "../ui/data-view/DataTable.tsx";
import { OperationsLineActions, OperationsStatusBadge, OperationsUrgencyBadge, type OperationsLineActionHandlers } from "./OperationsLineCard.tsx";
import { formatOperationDate } from "./operationsView.ts";
import type { BookingBoardItem } from "./types.ts";

export function OperationsTable({ items, onAdvance, onCancelLine, onCancelBooking }: { items: BookingBoardItem[] } & OperationsLineActionHandlers) {
  const columns: ColumnDef<BookingBoardItem>[] = [
    {
      key: "booking",
      header: "Booking code",
      render: (item) => (
        <a href={`/workspace/quotations/${encodeURIComponent(item.quotation_id)}`} className={cn(getTypographyClassName("bodySm"), "text-[var(--color-accent)] hover:underline")}>
          {item.booking_code}
        </a>
      ),
    },
    {
      key: "party",
      header: "Party / client",
      render: (item) => <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{item.party_label_snapshot ?? "Party TBD"}</span>,
    },
    {
      key: "service",
      header: "Service / title",
      cellClassName: "min-w-48",
      render: (item) => <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{item.line.title_snapshot}</span>,
    },
    {
      key: "supplier",
      header: "Supplier",
      render: (item) => <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>{item.line.supplier_name_snapshot ?? "—"}</span>,
    },
    {
      key: "status",
      header: "Status",
      render: (item) => <OperationsStatusBadge status={item.line.status} />,
    },
    {
      key: "urgency",
      header: "Urgency",
      render: (item) => <OperationsUrgencyBadge urgency={item.line.urgency} />,
    },
    {
      key: "dates",
      header: "Dates",
      cellClassName: "min-w-48",
      render: (item) => (
        <div className={cn(getTypographyClassName("caption"), "flex flex-col gap-1 text-[var(--color-muted)]")}>
          <span>Service: {formatOperationDate(item.line.service_date)}</span>
          <span>Request by: {formatOperationDate(item.line.request_by_date)}</span>
        </div>
      ),
    },
    {
      key: "voucher",
      header: "Voucher ref",
      render: (item) => item.line.voucher_ref ? (
        <button type="button" onClick={() => navigator.clipboard?.writeText(item.line.voucher_ref ?? "")} className={cn(getTypographyClassName("caption"), "inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline")}>
          <Copy size={12} aria-hidden="true" />
          {item.line.voucher_ref}
        </button>
      ) : <span className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>—</span>,
    },
    {
      key: "actions",
      header: "Actions",
      cellClassName: "min-w-72",
      render: (item) => <OperationsLineActions item={item} onAdvance={onAdvance} onCancelLine={onCancelLine} onCancelBooking={onCancelBooking} />,
    },
  ];

  return <DataTable items={items} columns={columns} keyExtractor={(item) => item.line.id} />;
}
