"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo, useState, useTransition } from "react";
import { Plus } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";
import { DataViewToggle, type ViewModeOption } from "../ui/data-view/DataViewToggle.tsx";
import { CancelBookingDialog, type CancelBookingRequest } from "./CancelBookingDialog.tsx";
import { CreateBookingDialog } from "./CreateBookingDialog.tsx";
import { OperationsGrid } from "./OperationsGrid.tsx";
import { OperationsKanban } from "./OperationsKanban.tsx";
import { OperationsTable } from "./OperationsTable.tsx";
import { TransitionDialog, type TransitionRequest } from "./TransitionDialog.tsx";
import { matchesOperationsSearch, normalizeOperationsView } from "./operationsView.ts";
import type { BookingBoardItem } from "./types.ts";
import { useOperationsBoard } from "./useOperationsBoard.ts";

export function OperationsBoard() {
  const { items, isLoading, actionError, createNewBooking, transitionLine, cancelWholeBooking } = useOperationsBoard();
  const { toast } = useToast();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [pendingTransition, setPendingTransition] = useState<{ request: TransitionRequest; bookingId: string; bookingRevision: number } | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [pendingCancel, setPendingCancel] = useState<CancelBookingRequest | null>(null);
  const [isCancellingBooking, setIsCancellingBooking] = useState(false);

  const viewMode = normalizeOperationsView(searchParams.get("view"));
  const filtered = useMemo(() => items.filter((item) => matchesOperationsSearch(item, search)), [items, search]);

  const setViewMode = useCallback((nextView: ViewModeOption) => {
    startTransition(() => {
      const params = new URLSearchParams(searchParams.toString());
      if (nextView === "kanban") params.delete("view"); else params.set("view", nextView);
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    });
  }, [pathname, router, searchParams, startTransition]);

  const openAdvance = useCallback((item: BookingBoardItem, to: "requested" | "confirmed" | "delivered") => {
    setPendingTransition({ request: { line: item.line, to }, bookingId: item.booking_id, bookingRevision: item.booking_revision });
  }, []);

  const openCancelLine = useCallback((item: BookingBoardItem) => {
    setPendingTransition({ request: { line: item.line, to: "cancelled" }, bookingId: item.booking_id, bookingRevision: item.booking_revision });
  }, []);

  const openCancelBooking = useCallback((item: BookingBoardItem) => {
    setPendingCancel({ bookingId: item.booking_id, bookingCode: item.booking_code, bookingRevision: item.booking_revision });
  }, []);

  const handleTransitionSubmit = async (input: { supplier_ref?: string; cancel_reason?: string }) => {
    if (!pendingTransition) return;
    setIsTransitioning(true);
    try {
      const { request, bookingId, bookingRevision } = pendingTransition;
      const result = await transitionLine(bookingId, request.line.id, bookingRevision, { to: request.to, ...input });
      if (!result) return;
      const updatedLine = result.lines.find((line) => line.id === request.line.id);
      if (request.to === "confirmed" && updatedLine?.voucher_ref) return { voucherRef: updatedLine.voucher_ref };
      setPendingTransition(null);
      toast(request.to === "cancelled" ? "Booking line cancelled." : "Booking line updated.", "success");
      return undefined;
    } finally {
      setIsTransitioning(false);
    }
  };

  const handleCreateBooking = async (input: { quotation_id: string; deposit_received_at: string; customer_balance_due_date?: string }) => {
    setIsCreating(true);
    try {
      const result = await createNewBooking(input);
      if (result) {
        setIsCreateOpen(false);
        toast(`Booking ${result.booking.booking_code} created.`, "success");
      }
    } finally {
      setIsCreating(false);
    }
  };

  const handleCancelBooking = async (reason: string) => {
    if (!pendingCancel) return;
    setIsCancellingBooking(true);
    try {
      const result = await cancelWholeBooking(pendingCancel.bookingId, pendingCancel.bookingRevision, reason);
      if (result) {
        setPendingCancel(null);
        toast(`Booking ${pendingCancel.bookingCode} cancelled.`, "success");
      }
    } finally {
      setIsCancellingBooking(false);
    }
  };

  const renderBoard = () => {
    if (viewMode === "grid") return <OperationsGrid items={filtered} onAdvance={openAdvance} onCancelLine={openCancelLine} onCancelBooking={openCancelBooking} />;
    if (viewMode === "table") return <OperationsTable items={filtered} onAdvance={openAdvance} onCancelLine={openCancelLine} onCancelBooking={openCancelBooking} />;
    return <OperationsKanban items={filtered} onAdvance={openAdvance} onCancelLine={openCancelLine} onCancelBooking={openCancelBooking} />;
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search booking code, party, supplier, service, or voucher…" className={cn(getTypographyClassName("bodySm"), "w-full max-w-xl rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]")} />
        <div className="flex flex-wrap items-center gap-3">
          <DataViewToggle viewMode={viewMode} onViewModeChange={setViewMode} kanbanAvailable />
          <button type="button" onClick={() => setIsCreateOpen(true)} className={cn(getTypographyClassName("buttonPrimary"), "flex items-center gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] px-4 py-2.5 text-[var(--color-accent)] shadow-xs transition-all hover:bg-[var(--color-surface-hover)]")}>
            <Plus size={16} aria-hidden="true" />
            Start a booking
          </button>
        </div>
      </div>

      {actionError ? <div className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-card)] border border-rose-200 bg-rose-50 p-3 text-rose-700")}>{actionError}</div> : null}

      {isLoading ? <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>Loading operations board…</p> : items.length === 0 ? (
        <div className="rounded-[var(--radius-card)] border border-dashed border-[var(--color-border)] p-10 text-center">
          <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>No bookings yet. Start one once a quotation&apos;s deposit lands.</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-[var(--radius-card)] border border-dashed border-[var(--color-border)] p-10 text-center">
          <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>No booking lines match your search.</p>
        </div>
      ) : renderBoard()}

      <TransitionDialog request={pendingTransition?.request ?? null} isSubmitting={isTransitioning} errorMessage={actionError} onClose={() => setPendingTransition(null)} onSubmit={handleTransitionSubmit} />
      <CreateBookingDialog isOpen={isCreateOpen} isSubmitting={isCreating} errorMessage={actionError} onClose={() => setIsCreateOpen(false)} onSubmit={handleCreateBooking} />
      <CancelBookingDialog request={pendingCancel} isSubmitting={isCancellingBooking} errorMessage={actionError} onClose={() => setPendingCancel(null)} onSubmit={handleCancelBooking} />
    </div>
  );
}
