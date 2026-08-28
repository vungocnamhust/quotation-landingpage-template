"use client";

import { DataKanban, type KanbanColumnDef } from "../ui/data-view/DataKanban.tsx";
import { OperationsLineCard, type OperationsLineActionHandlers } from "./OperationsLineCard.tsx";
import { OPERATIONS_URGENCY_GROUPS, OPERATIONS_URGENCY_LABEL, urgencyGroupOf, type OperationsUrgencyGroup } from "./operationsView.ts";
import type { BookingBoardItem } from "./types.ts";

const COLUMNS = OPERATIONS_URGENCY_GROUPS.map((id) => ({
  id,
  label: OPERATIONS_URGENCY_LABEL[id],
  ariaLabel: `${OPERATIONS_URGENCY_LABEL[id]} booking lines`,
  emptyDescription: "No booking lines in this lane.",
})) as readonly KanbanColumnDef<OperationsUrgencyGroup>[];

export function OperationsKanban({ items, onAdvance, onCancelLine, onCancelBooking }: { items: BookingBoardItem[] } & OperationsLineActionHandlers) {
  return (
    <DataKanban
      items={items}
      keyExtractor={(item) => item.line.id}
      kanbanConfig={{
        columns: COLUMNS,
        statusAccessor: urgencyGroupOf,
        renderCard: (item) => <OperationsLineCard item={item} onAdvance={onAdvance} onCancelLine={onCancelLine} onCancelBooking={onCancelBooking} />,
        enableDragAndDrop: false,
      }}
    />
  );
}
