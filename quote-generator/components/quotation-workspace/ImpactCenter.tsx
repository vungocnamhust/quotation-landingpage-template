"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, Sparkles } from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { QuotationImpact } from "./useQuotationWorkspace.ts";

type Props = {
  impacts: QuotationImpact[];
  loading?: boolean;
  error?: string | null;
  pending?: boolean;
  onAccept: (selectedImpactIds: number[]) => Promise<void>;
  onReviewFacts: () => void;
  onOpenDesign: () => Promise<void>;
  onRetry: () => void;
};

function valueText(value: Record<string, unknown> | null | undefined): string {
  if (!value || !("value" in value)) return "—";
  const raw = value.value;
  if (typeof raw === "string" || typeof raw === "number") return String(raw) || "—";
  if (Array.isArray(raw)) return raw.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join(", ") || "—";
  return JSON.stringify(raw);
}

export default function ImpactCenter({ impacts, loading = false, error = null, pending = false, onAccept, onReviewFacts, onOpenDesign, onRetry }: Props) {
  const initialSelected = useMemo(() => new Set(impacts.filter((item) => item.generationSelected).map((item) => item.id)), [impacts]);
  const [selected, setSelected] = useState<Set<number>>(initialSelected);
  const accepted = impacts.length > 0 && impacts.every((item) => item.status === "resolved");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const groups = useMemo(() => {
    const ordered = [...impacts].sort((left, right) => left.stage.localeCompare(right.stage) || left.scope.localeCompare(right.scope) || left.id - right.id);
    return { content: ordered.filter((item) => item.stage === "content"), design: ordered.filter((item) => item.stage === "design") };
  }, [impacts]);

  const toggle = (impactId: number) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(impactId)) next.delete(impactId);
      else next.add(impactId);
      return next;
    });
  };

  const accept = async () => {
    setIsSubmitting(true);
    try {
      await onAccept([...selected]);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-[70vh] w-full max-w-5xl items-center p-4 sm:p-8">
      <section role="dialog" aria-modal="true" aria-labelledby="impact-center-title" className="w-full rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-8">
        <header className="border-b border-[var(--color-border)] pb-5">
          <p className={cn(getTypographyClassName("label"), "text-[var(--color-accent)]")}>NEW QUOTATION VERSION</p>
          <h1 id="impact-center-title" className={cn(getTypographyClassName("sectionTitle"), "mt-2 text-[var(--color-on-surface)]")}>Impact Center</h1>
          <p className={cn(getTypographyClassName("bodyMd"), "mt-2 text-[var(--color-muted)]")}>Review exactly what changed. Facts-derived fields rebuild now; only selected narrative targets will generate when you open Design.</p>
        </header>

        {loading ? <p className={cn(getTypographyClassName("bodyMd"), "mt-6 text-[var(--color-muted)]")}>Loading the concrete change plan…</p> : null}
        {error ? <div className="mt-6 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] p-4"><p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>{error}</p><button type="button" onClick={onRetry} className={cn(getTypographyClassName("buttonSecondary"), "mt-3 min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-4 text-[var(--color-on-surface)]")}>Retry</button></div> : null}
        {!loading && !error ? <div className="mt-6 grid gap-6 lg:grid-cols-2">
          {(["content", "design"] as const).map((stage) => (
            <section key={stage} aria-labelledby={`${stage}-impact-title`}>
              <h2 id={`${stage}-impact-title`} className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>{stage === "content" ? "Content targets" : "Design targets"}</h2>
              <div className="mt-3 flex flex-col gap-3">
                {groups[stage].map((impact) => (
                  <article key={impact.id} className="rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
                    <div className="flex items-start gap-3">
                      {impact.generationEligible ? <input id={`impact-${impact.id}`} type="checkbox" checked={selected.has(impact.id)} disabled={accepted || pending} onChange={() => toggle(impact.id)} className="mt-1 size-4 accent-[var(--color-accent)]" /> : <CheckCircle2 size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-[var(--color-accent)]" />}
                      <div className="min-w-0 flex-1">
                        {impact.generationEligible ? <label htmlFor={`impact-${impact.id}`} className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>{impact.scope.replaceAll("-", " ")}</label> : <p className={cn(getTypographyClassName("label"), "text-[var(--color-on-surface)]")}>{impact.scope.replaceAll("-", " ")}</p>}
                        <p className={cn(getTypographyClassName("caption"), "mt-1 text-[var(--color-muted)]")}>{impact.explanation}</p>
                        {impact.targets?.map((target) => <p key={target.id} className={cn(getTypographyClassName("caption"), "mt-2 text-[var(--color-muted)]")}>{target.treatment.replaceAll("_", " ")}: {target.targetPath}</p>)}
                        <dl className="mt-3 grid gap-2">
                          <div><dt className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Before</dt><dd className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{valueText(impact.oldValue)}</dd></div>
                          <div><dt className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>After</dt><dd className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{valueText(impact.newValue)}</dd></div>
                        </dl>
                        {impact.generationEligible ? <p className={cn(getTypographyClassName("caption"), "mt-3 flex items-center gap-1 text-[var(--color-accent)]")}><Sparkles size={14} aria-hidden="true" /> Select to create a reviewed draft only for this target.</p> : null}
                      </div>
                    </div>
                  </article>
                ))}
                {!groups[stage].length ? <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>No {stage} targets changed.</p> : null}
              </div>
            </section>
          ))}
        </div> : null}

        <footer className="mt-8 flex flex-wrap justify-end gap-3 border-t border-[var(--color-border)] pt-5">
          {!accepted ? <button type="button" onClick={() => void accept()} disabled={loading || Boolean(error) || pending || isSubmitting || impacts.length === 0} className={cn(getTypographyClassName("buttonPrimary"), "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 text-[var(--color-on-accent)] disabled:opacity-60")}>{isSubmitting ? "Accepting…" : "Accept change plan"}</button> : <><button type="button" onClick={onReviewFacts} disabled={pending || isSubmitting} className={cn(getTypographyClassName("buttonSecondary"), "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-5 text-[var(--color-on-surface)]")}>Review Facts</button><button type="button" onClick={() => void onOpenDesign()} disabled={pending || isSubmitting} className={cn(getTypographyClassName("buttonPrimary"), "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 text-[var(--color-on-accent)] disabled:opacity-60")}>Generate selected & open Design</button></>}
        </footer>
      </section>
    </main>
  );
}
