"use client";
import { MapPin, Users } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { QuoteRequestItem } from "../quotation-workspace/factsTypes.ts";
import { WorkspaceNavigationLink } from "./WorkspaceNavigation.tsx";
export function WorkspaceRequestKanbanCard({ item, pending }: { item: QuoteRequestItem; pending?: boolean }) { return <article className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-[var(--elevation-card)]"><WorkspaceNavigationLink href={`/workspace/requests/${item.id}`} className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>{item.customer_name || "Anonymous Traveller"}</WorkspaceNavigationLink><p className={cn(getTypographyClassName("caption"), "mt-2 flex items-center gap-1 text-[var(--color-muted)]")}><MapPin size={13} />{item.destinations.join(" & ") || "Not specified"}</p><p className={cn(getTypographyClassName("caption"), "mt-1 flex items-center gap-1 text-[var(--color-muted)]")}><Users size={13} />{item.adults || 2} Adults</p>{pending ? <p className={cn(getTypographyClassName("caption"), "mt-3 text-[var(--color-muted)]")}>Saving…</p> : null}</article>; }
