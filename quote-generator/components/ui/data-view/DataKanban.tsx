"use client";

import React, { useMemo, useState } from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";

export type KanbanColumnDef<S extends string> = { id: S; label: string; ariaLabel: string; emptyTitle?: string; emptyDescription?: string };
export type KanbanColumnLoadState = { isLoading?: boolean; error?: string | null; hasMore?: boolean; onLoadMore?: () => void };
export type KanbanConfig<T, S extends string> = { columns: readonly KanbanColumnDef<S>[]; statusAccessor: (item: T) => S; renderCard: (item: T) => React.ReactNode; canDrop?: (item: T, target: S) => boolean; onItemMove?: (item: T, from: S, target: S) => Promise<void> | void; enableDragAndDrop?: boolean; getColumnLoadState?: (status: S) => KanbanColumnLoadState; isItemPending?: (item: T) => boolean };
export type DataKanbanProps<T, S extends string> = { items: T[]; keyExtractor: (item: T, index: number) => string; kanbanConfig: KanbanConfig<T, S> };

function Lane<S extends string>({ column, children }: { column: KanbanColumnDef<S>; children: React.ReactNode }) {
  const { setNodeRef } = useDroppable({ id: column.id });
  return <section ref={setNodeRef} aria-label={column.ariaLabel} className="w-80 shrink-0 snap-start rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3"><h2 className={cn(getTypographyClassName("label"), "mb-3 text-[var(--color-on-surface)]")}>{column.label}</h2>{children}</section>;
}

function Card({ id, disabled, draggable, children }: { id: string; disabled: boolean; draggable: boolean; children: React.ReactNode }) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({ id, disabled: disabled || !draggable });
  return <div ref={setNodeRef} {...(draggable ? { ...attributes, ...listeners } : {})} style={transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined} className={cn(draggable && "touch-none", disabled && "opacity-60")}>{children}</div>;
}

export function DataKanban<T, S extends string>({ items, keyExtractor, kanbanConfig }: DataKanbanProps<T, S>) {
  const draggable = kanbanConfig.enableDragAndDrop ?? Boolean(kanbanConfig.canDrop && kanbanConfig.onItemMove);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }), useSensor(KeyboardSensor));
  const [active, setActive] = useState<string | null>(null);
  const grouped = useMemo(() => { const map = new Map<S, T[]>(); kanbanConfig.columns.forEach((column) => map.set(column.id, [])); items.forEach((item) => map.get(kanbanConfig.statusAccessor(item))?.push(item)); return map; }, [items, kanbanConfig]);
  const byId = useMemo(() => new Map(items.map((item, index) => [keyExtractor(item, index), item])), [items, keyExtractor]);
  const onDragEnd = (event: DragEndEvent) => { setActive(null); if (!draggable || !kanbanConfig.canDrop || !kanbanConfig.onItemMove) return; const item = event.active.id ? byId.get(String(event.active.id)) : undefined; const target = event.over?.id as S | undefined; if (!item || !target) return; const from = kanbanConfig.statusAccessor(item); if (from !== target && kanbanConfig.canDrop(item, target)) void kanbanConfig.onItemMove(item, from, target); };
  return <DndContext sensors={draggable ? sensors : undefined} onDragStart={draggable ? (event) => setActive(String(event.active.id)) : undefined} onDragCancel={draggable ? () => setActive(null) : undefined} onDragEnd={onDragEnd}><div className="flex gap-4 overflow-x-auto snap-x snap-mandatory pb-2">{kanbanConfig.columns.map((column) => { const state = kanbanConfig.getColumnLoadState?.(column.id) ?? {}; const lane = grouped.get(column.id) ?? []; return <Lane key={column.id} column={column}><div className="flex flex-col gap-3">{state.isLoading ? ["skeleton-1", "skeleton-2", "skeleton-3"].map((id) => <div key={id} className="h-32 animate-pulse rounded-[var(--radius-card)] bg-[var(--color-surface)]" />) : lane.map((item, index) => { const id = keyExtractor(item, index); return <Card key={id} id={id} draggable={draggable} disabled={active === id || Boolean(kanbanConfig.isItemPending?.(item))}>{kanbanConfig.renderCard(item)}</Card>; })}{!state.isLoading && !lane.length ? <p className={cn(getTypographyClassName("bodySm"), "rounded-[var(--radius-card)] border border-dashed border-[var(--color-border)] p-4 text-[var(--color-muted)]")}>{column.emptyDescription ?? "No items in this stage."}</p> : null}{state.error ? <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>{state.error}</p> : null}{state.hasMore && state.onLoadMore ? <button type="button" onClick={state.onLoadMore} className={cn(getTypographyClassName("buttonSecondary"), "rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-2 text-[var(--color-on-surface)]")}>Load more</button> : null}</div></Lane>; })}</div></DndContext>;
}
