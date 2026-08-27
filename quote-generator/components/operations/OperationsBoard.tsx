"use client";

import { useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";
import { useOperationsBoard } from "./useOperationsBoard.ts";
import { BookingCard } from "./BookingCard.tsx";
import { TransitionDialog, type TransitionRequest } from "./TransitionDialog.tsx";
import { CreateBookingDialog } from "./CreateBookingDialog.tsx";
import { CancelBookingDialog, type CancelBookingRequest } from "./CancelBookingDialog.tsx";
import { URGENCY_GROUP_LABEL, URGENCY_GROUPS, type BookingBoardItem, type BookingLineProfile, type UrgencyGroup } from "./types.ts";

type BookingGroup = { bookingId: string; context: BookingBoardItem; lines: BookingLineProfile[] };

function urgencyGroupOf(item: BookingBoardItem): UrgencyGroup {
  if (item.line.status === "delivered" || item.line.status === "cancelled") return "done";
  if (item.line.urgency === "overdue") return "overdue";
  if (item.line.urgency === "due_soon") return "due_soon";
  return "upcoming";
}

function matchesSearch(item: BookingBoardItem, query: string): boolean {
  if (!query) return true;
  const haystack = `${item.booking_code} ${item.party_label_snapshot ?? ""} ${item.line.title_snapshot} ${item.line.supplier_name_snapshot ?? ""}`.toLowerCase();
  return haystack.includes(query.toLowerCase());
}

export function OperationsBoard() {
  const { items, isLoading, actionError, createNewBooking, transitionLine, cancelWholeBooking } = useOperationsBoard();
  const { toast } = useToast();

  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [pendingTransition, setPendingTransition] = useState<{ request: TransitionRequest; bookingId: string; bookingRevision: number } | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [pendingCancel, setPendingCancel] = useState<CancelBookingRequest | null>(null);
  const [isCancellingBooking, setIsCancellingBooking] = useState(false);

  const filtered = useMemo(() => items.filter((item) => matchesSearch(item, search)), [items, search]);

  const groupsByUrgency = useMemo(() => {
    const byUrgency = new Map<UrgencyGroup, Map<string, BookingGroup>>();
    for (const group of URGENCY_GROUPS) byUrgency.set(group, new Map());
    for (const item of filtered) {
      const bucket = byUrgency.get(urgencyGroupOf(item));
      if (!bucket) continue;
      const existing = bucket.get(item.booking_id);
      if (existing) {
        existing.lines.push(item.line);
      } else {
        bucket.set(item.booking_id, { bookingId: item.booking_id, context: item, lines: [item.line] });
      }
    }
    return byUrgency;
  }, [filtered]);

  const openAdvance = (bookingContext: BookingBoardItem, line: BookingLineProfile, to: "requested" | "confirmed" | "delivered") => {
    setPendingTransition({ request: { line, to }, bookingId: bookingContext.booking_id, bookingRevision: bookingContext.booking_revision });
  };

  const openCancelLine = (bookingContext: BookingBoardItem, line: BookingLineProfile) => {
    setPendingTransition({ request: { line, to: "cancelled" }, bookingId: bookingContext.booking_id, bookingRevision: bookingContext.booking_revision });
  };

  const handleTransitionSubmit = async (input: { supplier_ref?: string; cancel_reason?: string }) => {
    if (!pendingTransition) return;
    setIsTransitioning(true);
    try {
      const { request, bookingId, bookingRevision } = pendingTransition;
      const result = await transitionLine(bookingId, request.line.id, bookingRevision, { to: request.to, ...input });
      if (!result) return;
      const updatedLine = result.lines.find((line) => line.id === request.line.id);
      if (request.to !== "confirmed") {
        setPendingTransition(null);
        toast(request.to === "cancelled" ? "Booking line cancelled." : "Booking line updated.", "success");
      }
      return updatedLine?.voucher_ref ? { voucherRef: updatedLine.voucher_ref } : undefined;
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

  const hasAnyItems = items.length > 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search booking code, party or service…"
          className={cn(
            getTypographyClassName("bodySm"),
            "w-full max-w-sm rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]",
          )}
        />
        <button
          type="button"
          onClick={() => setIsCreateOpen(true)}
          className={cn(
            getTypographyClassName("buttonPrimary"),
            "flex items-center gap-2 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-accent-wash)] px-4 py-2.5 text-[var(--color-accent)] shadow-xs transition-all hover:bg-[var(--color-surface-hover)]",
          )}
        >
          <Plus size={16} aria-hidden="true" />
          Start a booking
        </button>
      </div>

      {actionError ? (
        <div className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-card)] border border-rose-200 bg-rose-50 p-3 text-rose-700")}>
          {actionError}
        </div>
      ) : null}

      {isLoading ? (
        <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>Loading operations board…</p>
      ) : !hasAnyItems ? (
        <div className="rounded-[var(--radius-card)] border border-dashed border-[var(--color-border)] p-10 text-center">
          <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>
            No bookings yet. Start one once a quotation&apos;s deposit lands.
          </p>
        </div>
      ) : (
        URGENCY_GROUPS.map((group) => {
          const bookingsInGroup = groupsByUrgency.get(group);
          if (!bookingsInGroup || bookingsInGroup.size === 0) return null;
          return (
            <section key={group} className="flex flex-col gap-3">
              <h2 className={cn(getTypographyClassName("sectionTitle"), "text-[var(--color-on-surface)]")}>
                {URGENCY_GROUP_LABEL[group]}
              </h2>
              <div className="flex flex-col gap-3">
                {Array.from(bookingsInGroup.values()).map(({ bookingId, context, lines }) => (
                  <BookingCard
                    key={bookingId}
                    bookingId={bookingId}
                    bookingCode={context.booking_code}
                    quotationId={context.quotation_id}
                    partyLabel={context.party_label_snapshot}
                    travelStartDate={context.travel_start_date}
                    travelEndDate={context.travel_end_date}
                    lines={lines}
                    hasCashFlowWarning={filtered.some((item) => item.booking_id === bookingId && item.cash_flow_warning)}
                    onAdvance={(line, to) => openAdvance(context, line, to)}
                    onCancelLine={(line) => openCancelLine(context, line)}
                    onCancelBooking={() =>
                      setPendingCancel({ bookingId, bookingCode: context.booking_code, bookingRevision: context.booking_revision })
                    }
                  />
                ))}
              </div>
            </section>
          );
        })
      )}

      <TransitionDialog
        request={pendingTransition?.request ?? null}
        isSubmitting={isTransitioning}
        errorMessage={actionError}
        onClose={() => setPendingTransition(null)}
        onSubmit={handleTransitionSubmit}
      />

      <CreateBookingDialog
        isOpen={isCreateOpen}
        isSubmitting={isCreating}
        errorMessage={actionError}
        onClose={() => setIsCreateOpen(false)}
        onSubmit={handleCreateBooking}
      />

      <CancelBookingDialog
        request={pendingCancel}
        isSubmitting={isCancellingBooking}
        errorMessage={actionError}
        onClose={() => setPendingCancel(null)}
        onSubmit={handleCancelBooking}
      />
    </div>
  );
}
