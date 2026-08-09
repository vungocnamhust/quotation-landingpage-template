'use client';

import { cn } from '../../utils/cn';
import { getTypographyClassName } from '../../config/typography';
import type { ContentFactInput } from '../quotation-workspace/useQuotationWorkspace';

type Mode = 'storytelling' | 'detailed';

function readFact(value: Record<string, unknown> | undefined, path: Array<string | number>): unknown {
  let current: unknown = value;
  for (const part of path) current = current && typeof current === 'object' ? (current as Record<string | number, unknown>)[part] : undefined;
  return current;
}

function factKeyLabel(key: string): string {
  return key.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/[_-]+/g, ' ').replace(/^./, (char) => char.toUpperCase());
}

function FactValue({ value, nested = false }: { value: unknown; nested?: boolean }) {
  if (value === undefined || value === null || value === '') return <span className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>Not provided</span>;
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return <span className={cn(getTypographyClassName('bodySm'), 'break-words text-[var(--color-on-surface)]')}>{String(value)}</span>;
  if (Array.isArray(value)) {
    if (!value.length) return <span className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>Not provided</span>;
    if (value.every((item) => typeof item === 'string' || typeof item === 'number')) return <ul className="grid min-w-0 gap-1.5">{value.map((item, index) => <li key={`${String(item)}-${index}`} className={cn(getTypographyClassName('bodySm'), 'break-words text-[var(--color-on-surface)]')}>{String(item)}</li>)}</ul>;
    return <div className="grid min-w-0 gap-2">{value.map((item, index) => <div key={index} className="min-w-0 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-2"><FactValue value={item} nested /></div>)}</div>;
  }
  if (typeof value === 'object') return <dl className={cn('grid min-w-0 gap-1.5', nested && 'gap-2')}>{Object.entries(value as Record<string, unknown>).map(([key, item]) => <div key={key} className="grid min-w-0 gap-0.5"><dt className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)]')}>{factKeyLabel(key)}</dt><dd className="min-w-0"><FactValue value={item} nested /></dd></div>)}</dl>;
  return <span className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>Not provided</span>;
}

export function ContentGenerationPanel({ mode, onModeChange, instruction, defaultInstruction, onInstructionChange, onRestoreDefault, factInputs, facts, onGenerate, pending, disabled }: { mode: Mode; onModeChange: (mode: Mode) => void; instruction: string; defaultInstruction: string; onInstructionChange: (value: string) => void; onRestoreDefault: () => void; factInputs: ContentFactInput[]; facts?: Record<string, unknown>; onGenerate: () => void; pending: boolean; disabled: boolean }) {
  const usingDefault = instruction === defaultInstruction;
  return <aside className="grid h-fit min-w-0 max-w-full gap-4 overflow-hidden rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 xl:sticky xl:top-4"><div className="min-w-0"><h3 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>AI assistant</h3><p className={cn(getTypographyClassName('bodySm'), 'mt-1 break-words text-[var(--color-muted)]')}>Generate a validated draft into the editable fields. It never publishes automatically.</p></div><div className="flex flex-wrap gap-2" role="group" aria-label="Writing mode">{(['storytelling', 'detailed'] as const).map((value) => <button key={value} type="button" onClick={() => onModeChange(value)} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border px-3 py-2 capitalize lg:min-h-9', mode === value ? 'border-[var(--color-accent)] bg-[var(--color-accent-wash)]' : 'border-[var(--color-border)]')}>{value}</button>)}</div><label className="grid min-w-0 gap-1.5"><span className={cn(getTypographyClassName('label'), 'break-words text-[var(--color-muted)]')}>Generation brief {usingDefault ? '· default' : '· custom'}</span><textarea value={instruction} onChange={(event) => onInstructionChange(event.target.value)} maxLength={2000} rows={6} className={cn(getTypographyClassName('bodySm'), 'min-w-0 w-full rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]')} /></label><p className={cn(getTypographyClassName('bodySm'), 'break-words text-[var(--color-muted)]')}>This brief changes style only. Facts, brand policy, ownership and response schema remain fixed.</p><button type="button" onClick={onRestoreDefault} disabled={usingDefault} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-2 disabled:opacity-50 lg:min-h-9')}>Restore default</button><FactsUsed factInputs={factInputs} facts={facts} /><button type="button" disabled={pending || disabled} onClick={onGenerate} className={cn(getTypographyClassName('buttonPrimary'), 'min-h-11 w-fit rounded-[var(--radius-button)] bg-[var(--color-action-primary-surface)] px-3 py-2 text-[var(--color-action-primary-text)] disabled:opacity-50 lg:min-h-9')}>{pending ? 'Generating draft…' : 'Generate draft'}</button></aside>;
}

export function FactsUsed({ factInputs, facts }: { factInputs: ContentFactInput[]; facts?: Record<string, unknown> }) {
  return <div className="grid min-w-0 max-w-full gap-2"><p className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>FACTS USED</p>{factInputs.map((input) => {
    const value = readFact(facts, input.path);
    const nights = input.id === 'duration' ? readFact(facts, ['trip_facts', 'duration_nights']) : undefined;
    const formattedDuration = typeof value === 'number' && typeof nights === 'number' ? `${value} days / ${nights} nights` : value;
    return <div key={input.id} className="min-w-0 overflow-hidden rounded-[var(--radius-button)] border border-[var(--color-border)] p-3"><p className={cn(getTypographyClassName('label'), 'break-words text-[var(--color-muted)]')}>{input.label}{input.required ? ' · required' : ''}</p><div className="mt-1 min-w-0"><FactValue value={formattedDuration} /></div></div>;
  })}</div>;
}
