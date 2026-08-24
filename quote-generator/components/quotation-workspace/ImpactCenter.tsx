'use client';

import { useMemo, useState } from 'react';
import { CheckCircle2, Sparkles } from 'lucide-react';
import { getTypographyClassName } from '../../config/typography.ts';
import { cn } from '../../utils/cn.ts';
import type { ContentAction, ContentActionPlan } from './useContentActionPlan.ts';

type Props = {
  plan?: ContentActionPlan;
  loading?: boolean;
  error?: string | null;
  pendingMode?: 'accept' | 'auto' | 'bypass' | null;
  onAccept: () => Promise<void>;
  onGenerateDrafts: (actions: ContentAction[]) => Promise<void>;
  onGenerateAndApply: (actions: ContentAction[]) => Promise<void>;
  onRetry: () => void;
  onReviewFacts: () => void;
  onOpenContent: (action?: ContentAction) => void;
};

const POLICY_LABEL: Record<ContentAction['automationPolicy'], string> = {
  manual: 'Review manually', auto: 'Generate review draft', bypass: 'Generate and apply',
};

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (Array.isArray(value)) return value.map(displayValue).join(', ');
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    return typeof record.label === 'string' ? record.label : typeof record.value === 'string' ? record.value : 'Updated Facts';
  }
  return 'Updated Facts';
}

function actionChange(action: ContentAction): { before: string; after: string; fields: string[] } {
  const metadata = action.metadata ?? {};
  const rawFields = metadata.affectedFields;
  return {
    before: displayValue(metadata.old ?? metadata.before),
    after: displayValue(metadata.new ?? metadata.after),
    fields: Array.isArray(rawFields) ? rawFields.map(displayValue).filter(Boolean) : [],
  };
}

function actionLabel(action: ContentAction): string {
  return action.entityKey.startsWith('day:') ? `Day ${action.entityKey.slice(4)}` : action.entityKey.replaceAll('_', ' ');
}

export default function ImpactCenter({ plan, loading = false, error = null, pendingMode = null, onAccept, onGenerateDrafts, onGenerateAndApply, onRetry, onReviewFacts, onOpenContent }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmBypass, setConfirmBypass] = useState(false);
  const accepted = plan?.status === 'accepted';
  const actions = useMemo(() => plan?.actions ?? [], [plan?.actions]);
  const eligible = useMemo(() => actions.filter((action) => action.state === 'pending' && action.automationPolicy !== 'manual'), [actions]);
  const selectedActions = useMemo(() => eligible.filter((action) => selected.has(action.id)), [eligible, selected]);
  const autoActions = selectedActions.filter((action) => action.automationPolicy === 'auto');
  const bypassActions = selectedActions.filter((action) => action.automationPolicy === 'bypass');
  const toggle = (id: string) => setSelected((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  return <main className="mx-auto flex min-h-[70vh] w-full max-w-5xl items-center p-4 sm:p-8">
    <section role="dialog" aria-modal="true" aria-labelledby="impact-center-title" className="w-full rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-5 shadow-[var(--elevation-card)] sm:p-8">
      <header className="border-b border-[var(--color-border)] pb-5"><p className={cn(getTypographyClassName('label'), 'text-[var(--color-accent)]')}>NEW QUOTATION VERSION</p><h1 id="impact-center-title" className={cn(getTypographyClassName('sectionTitle'), 'mt-2 text-[var(--color-on-surface)]')}>Content change plan</h1><p className={cn(getTypographyClassName('bodyMd'), 'mt-2 text-[var(--color-muted)]')}>Facts are rebuilt in the successor. Choose only editorial actions to run.</p></header>
      {loading ? <p className={cn(getTypographyClassName('bodyMd'), 'mt-6 text-[var(--color-muted)]')}>Loading change plan…</p> : null}
      {error ? <div role="alert" className="mt-6 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] p-4"><p className={cn(getTypographyClassName('bodyMd'), 'text-[var(--color-on-surface)]')}>{error}</p><button type="button" onClick={onRetry} className={cn(getTypographyClassName('buttonSecondary'), 'mt-3 min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-4')}>Retry</button></div> : null}
      {!loading && !error && actions.length === 0 ? <p className={cn(getTypographyClassName('bodyMd'), 'mt-6 text-[var(--color-muted)]')}>No editorial Content action is required. You can review the new Facts or open Content Studio.</p> : null}
      {!loading && !error && actions.length > 0 ? <div className="mt-6 grid gap-3">{actions.map((action) => {
        const change = actionChange(action);
        const actionable = action.state === 'pending' && action.automationPolicy !== 'manual';
        return <article key={action.id} className="rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4"><div className="flex gap-3">{actionable ? <input id={`content-action-${action.id}`} type="checkbox" aria-label={`Select ${actionLabel(action)}`} checked={selected.has(action.id)} disabled={!accepted || pendingMode !== null} onChange={() => toggle(action.id)} className="mt-1 size-4 accent-[var(--color-accent)]" /> : <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-[var(--color-accent)]" aria-hidden="true" />}<div className="min-w-0 flex-1"><p className={cn(getTypographyClassName('label'), 'text-[var(--color-on-surface)]')}>{actionLabel(action)} · {POLICY_LABEL[action.automationPolicy]}</p><p className={cn(getTypographyClassName('bodySm'), 'mt-2 text-[var(--color-on-surface)]')}>Facts: {change.before} → {change.after}</p><p className={cn(getTypographyClassName('caption'), 'mt-2 text-[var(--color-muted)]')}>Affected Content: {change.fields.join(', ') || action.scope}</p><p className={cn(getTypographyClassName('caption'), 'mt-2 text-[var(--color-muted)]')}>Inherited context: {action.inheritedReferenceStatus.replaceAll('_', ' ')}</p>{accepted ? <button type="button" onClick={() => onOpenContent(action)} className={cn(getTypographyClassName('buttonSecondary'), 'mt-3 min-h-9 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-3')}>Open Content scope</button> : null}</div></div></article>;
      })}</div> : null}
      <footer className="mt-8 flex flex-wrap justify-end gap-3 border-t border-[var(--color-border)] pt-5">{!accepted ? <button type="button" disabled={loading || Boolean(error) || pendingMode !== null} onClick={() => void onAccept()} className={cn(getTypographyClassName('buttonPrimary'), 'min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 text-[var(--color-on-accent)] disabled:opacity-60')}>{pendingMode === 'accept' ? 'Accepting…' : 'Accept change plan'}</button> : <><button type="button" onClick={onReviewFacts} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-5')}>Review Facts</button><button type="button" onClick={() => onOpenContent(selectedActions[0])} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-5')}>Open Content</button><button type="button" disabled={autoActions.length === 0 || pendingMode !== null} onClick={() => void onGenerateDrafts(autoActions)} className={cn(getTypographyClassName('buttonPrimary'), 'min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 text-[var(--color-on-accent)] disabled:opacity-60')}><Sparkles size={15} aria-hidden="true" className="mr-2 inline" />{pendingMode === 'auto' ? 'Generating…' : `Generate review drafts (${autoActions.length})`}</button><button type="button" disabled={bypassActions.length === 0 || pendingMode !== null} onClick={() => setConfirmBypass(true)} className={cn(getTypographyClassName('buttonPrimary'), 'min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-5 text-[var(--color-on-accent)] disabled:opacity-60')}>{pendingMode === 'bypass' ? 'Applying…' : `Generate & apply (${bypassActions.length})`}</button></>}</footer>
    </section>
    {confirmBypass ? <section role="alertdialog" aria-modal="true" aria-labelledby="bypass-title" className="fixed inset-0 z-50 grid place-items-center bg-[color-mix(in_srgb,var(--color-on-surface)_45%,transparent)] p-4"><div className="w-full max-w-lg rounded-[var(--radius-card)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]"><h2 id="bypass-title" className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>Apply selected generated content?</h2><p className={cn(getTypographyClassName('bodySm'), 'mt-2 text-[var(--color-muted)]')}>Only these scopes will change the quotation: {bypassActions.map((action) => action.scope).join(', ')}.</p><div className="mt-5 flex justify-end gap-3"><button type="button" onClick={() => setConfirmBypass(false)} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-10 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-4')}>Cancel</button><button type="button" onClick={() => { setConfirmBypass(false); void onGenerateAndApply(bypassActions); }} className={cn(getTypographyClassName('buttonPrimary'), 'min-h-10 rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 text-[var(--color-on-accent)]')}>Generate & apply</button></div></div></section> : null}
  </main>;
}
