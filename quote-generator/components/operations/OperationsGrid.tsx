"use client";

import { DataGrid } from "../ui/data-view/DataGrid.tsx";
import { OperationsLineCard, type OperationsLineActionHandlers } from "./OperationsLineCard.tsx";
import type { BookingBoardItem } from "./types.ts";

export function OperationsGrid({ items, onAdvance, onCancelLine, onCancelBooking }: { items: BookingBoardItem[] } & OperationsLineActionHandlers) {
  return <DataGrid items={items} keyExtractor={(item) => item.line.id} renderItem={(item) => <OperationsLineCard item={item} onAdvance={onAdvance} onCancelLine={onCancelLine} onCancelBooking={onCancelBooking} />} />;
}
