'use client';

import { cn } from '../../utils/cn';
import { getTypographyClassName } from '../../config/typography';
import type { ContentCandidate, ContentEditorField } from '../quotation-workspace/useQuotationWorkspace';

export function cloneCandidate(value: ContentCandidate): ContentCandidate {
  return JSON.parse(JSON.stringify(value)) as ContentCandidate;
}

function readValue(candidate: ContentCandidate, path: Array<string | number>): unknown {
  let value: unknown = candidate;
  for (const part of path) value = value && typeof value === 'object' ? (value as Record<string | number, unknown>)[part] : undefined;
  return value;
}

function writeValue(candidate: ContentCandidate, path: Array<string | number>, value: unknown): ContentCandidate {
  const next = cloneCandidate(candidate);
  let cursor: Record<string | number, unknown> | unknown[] = next;
  path.forEach((part, index) => {
    if (index === path.length - 1) cursor[part as never] = value;
    else cursor = cursor[part as never] as Record<string | number, unknown> | unknown[];
  });
  return next;
}

function FieldEditor({ field, candidate, onChange }: { field: ContentEditorField; candidate: ContentCandidate; onChange: (value: ContentCandidate) => void }) {
  const common = cn(getTypographyClassName('bodySm'), 'w-full rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)]');
  if (field.control === 'string-list') {
    const items = Array.isArray(readValue(candidate, field.path)) ? (readValue(candidate, field.path) as unknown[]).map(String) : [];
    return <fieldset className="grid gap-2"><legend className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>{field.label}</legend>{items.map((item, index) => <div key={`${field.id}-${index}`} className="flex gap-2"><textarea value={item} maxLength={field.maxLength} rows={2} onChange={(event) => onChange(writeValue(candidate, field.path, items.map((current, currentIndex) => currentIndex === index ? event.target.value : current)))} className={cn(common, 'min-w-0 flex-1')} /><button type="button" onClick={() => onChange(writeValue(candidate, field.path, items.filter((_, currentIndex) => currentIndex !== index)))} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3')}>Remove</button></div>)}<button type="button" onClick={() => onChange(writeValue(candidate, field.path, [...items, '']))} className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-2')}>Add item</button></fieldset>;
  }
  const value = typeof readValue(candidate, field.path) === 'string' ? String(readValue(candidate, field.path)) : '';
  return <label className="grid gap-1.5"><span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>{field.label}</span>{field.control === 'textarea' ? <textarea value={value} maxLength={field.maxLength} rows={5} onChange={(event) => onChange(writeValue(candidate, field.path, event.target.value))} className={common} /> : <input value={value} maxLength={field.maxLength} onChange={(event) => onChange(writeValue(candidate, field.path, event.target.value))} className={common} />}</label>;
}

function FinalizationFields({ candidate, onChange }: { candidate: ContentCandidate; onChange: (value: ContentCandidate) => void }) {
  const groups = readValue(candidate, ['content', 'sections', 'finalization', 'blocks', 0, 'groups']);
  if (!Array.isArray(groups)) return <p className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>Complete the approved finalization Facts to create this checklist.</p>;
  return <div className="grid gap-4">{groups.map((group, groupIndex) => {
    const record = group as Record<string, unknown>;
    const items = Array.isArray(record.items) ? record.items : [];
    return <div key={groupIndex} className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] p-3"><label className="grid gap-1.5"><span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>Checklist group</span><input value={String(record.title ?? '')} onChange={(event) => onChange(writeValue(candidate, ['content', 'sections', 'finalization', 'blocks', 0, 'groups', groupIndex, 'title'], event.target.value))} className={cn(getTypographyClassName('bodySm'), 'rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-2')} /></label>{items.map((item, itemIndex) => <label key={itemIndex} className="grid gap-1.5"><span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>Item {itemIndex + 1}</span><input value={String(item ?? '')} onChange={(event) => onChange(writeValue(candidate, ['content', 'sections', 'finalization', 'blocks', 0, 'groups', groupIndex, 'items', itemIndex], event.target.value))} className={cn(getTypographyClassName('bodySm'), 'rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-2')} /></label>)}</div>;
  })}</div>;
}

export function SectionContentFields({ scope, fields, candidate, onChange }: { scope: string; fields: ContentEditorField[]; candidate: ContentCandidate; onChange: (value: ContentCandidate) => void }) {
  return <section className="grid gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4"><div><h3 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>Brochure content</h3><p className={cn(getTypographyClassName('bodySm'), 'mt-1 text-[var(--color-muted)]')}>Write directly, or generate into these fields. Nothing is published until Apply.</p></div>{scope === 'finalization' ? <FinalizationFields candidate={candidate} onChange={onChange} /> : fields.map((field) => <FieldEditor key={field.id} field={field} candidate={candidate} onChange={onChange} />)}</section>;
}
