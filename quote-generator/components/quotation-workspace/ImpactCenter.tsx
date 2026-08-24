"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { ImpactTarget, QuotationImpact } from "./useQuotationWorkspace.ts";

type Props = { impacts: QuotationImpact[]; loading?: boolean; error?: string | null; pending?: boolean; onAccept: (ids: number[]) => Promise<void>; onRetry: () => void; onReviewFacts: () => void; onOpenContent: (target: ImpactTarget) => void };

const TREATMENT_LABEL: Record<ImpactTarget["treatment"], string> = { derived_rebuilt: "Rebuilt from Facts", preserved_review: "Preserved — review", generation_candidate: "Optional generation", retired: "Retired", preserved_unchanged: "Preserved unchanged" };

function valueText(value: Record<string, unknown> | null | undefined): string {
  const raw = value?.value;
  if (raw == null) return "—";
  if (typeof raw === "string" || typeof raw === "number") return String(raw);
  return value?.label ? String(value.label) : "Changed";
}

export default function ImpactCenter({ impacts, loading = false, error = null, pending = false, onAccept, onRetry, onReviewFacts, onOpenContent }: Props) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const accepted = impacts.length > 0 && impacts.every((item) => item.status === "resolved");
  const targets = useMemo(() => impacts.flatMap((impact) => impact.targets.map((target) => ({ impact, target }))).sort((a, b) => a.target.treatment.localeCompare(b.target.treatment) || a.target.scope.localeCompare(b.target.scope)), [impacts]);
  const accept = async () => { setSubmitting(true); try { await onAccept([...selected]); } finally { setSubmitting(false); } };
  return <main className="mx-auto flex min-h-[70vh] w-full max-w-5xl items-center p-4 sm:p-8"><section role="dialog" aria-modal="true" aria-labelledby="impact-center-title" className="w-full rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-8">
    <header className="border-b border-[var(--color-border)] pb-5"><p className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>NEW QUOTATION VERSION</p><h1 id="impact-center-title" className={cn(getTypographyClassName("sectionTitle"), "mt-2 text-[var(--color-on-surface)]")}>Impact Center</h1><p className={cn(getTypographyClassName("bodyMd"), "mt-2 text-[var(--color-muted)]")}>Review Content changes from the new immutable Facts. Nothing is generated or applied here.</p></header>
    {loading ? <p className={cn(getTypographyClassName("bodyMd"), "mt-6 text-[var(--color-muted)]")}>Loading change plan…</p> : null}
    {error ? <div className="mt-6 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] p-4"><p className={getTypographyClassName("bodyMd")}>{error}</p><button type="button" onClick={onRetry} className={cn(getTypographyClassName("buttonSecondary"), "mt-3 min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-4")}>Retry</button></div> : null}
    {!loading && !error ? <div className="mt-6 flex flex-col gap-3">{targets.map(({ impact, target }) => <article key={target.id} className="rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4"><div className="flex gap-3">{target.generationEligible ? <input id={`impact-target-${target.id}`} aria-label={`Select ${impact.entityKey} for later Content generation`} type="checkbox" checked={selected.has(target.id)} disabled={accepted || pending} onChange={() => setSelected((current) => { const next = new Set(current); if (next.has(target.id)) next.delete(target.id); else next.add(target.id); return next; })} className="mt-1 size-4 accent-[var(--color-accent)]" /> : <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-[var(--color-accent)]" aria-hidden="true" />}<div className="min-w-0 flex-1"><p className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>{impact.entityKey.replace("day:", "Day ")} · {TREATMENT_LABEL[target.treatment]}</p><p className={cn(getTypographyClassName("caption"), "mt-1 text-[var(--color-muted)]")}>{impact.explanation}</p><p className={cn(getTypographyClassName("bodySm"), "mt-2 text-[var(--color-on-surface)]")}>Before: {valueText(impact.oldValue)} → After: {valueText(impact.newValue)}</p><p className={cn(getTypographyClassName("caption"), "mt-2 text-[var(--color-muted)]")}>Fields: {target.affectedFields.map((field) => field.label ?? field.path).join(", ") || "Facts-derived labels"}</p>{accepted ? <button type="button" onClick={() => onOpenContent(target)} className={cn(getTypographyClassName("buttonSecondary"), "mt-3 min-h-9 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-3")}>Open Content scope</button> : null}{target.generationEligible ? <p className={cn(getTypographyClassName("caption"), "mt-3 flex items-center gap-1 text-[var(--color-accent)]")}><Sparkles size={14} aria-hidden="true" /> Selection is recorded only; generation remains user-controlled in Content Studio.</p> : null}</div></div></article>)}</div> : null}
    <footer className="mt-8 flex flex-wrap justify-end gap-3 border-t border-[var(--color-border)] pt-5">{!accepted ? <button type="button" disabled={loading || Boolean(error) || pending || submitting || targets.length === 0} onClick={() => void accept()} className={cn(getTypographyClassName("buttonPrimary"), "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 text-[var(--color-on-accent)] disabled:opacity-60")}>{submitting ? "Accepting…" : "Accept change plan"}</button> : <button type="button" onClick={onReviewFacts} className={cn(getTypographyClassName("buttonPrimary"), "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 text-[var(--color-on-accent)]")}>Review Facts</button>}</footer>
  </section></main>;
}
