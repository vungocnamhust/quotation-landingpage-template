'use client';

import { useState, useTransition } from 'react';
import { getTypographyClassName } from '../../config/typography';
import { cn } from '../../utils/cn';
import type { InspectorDescriptor } from './BoundaryCanvas';
import type { ResolvedHandoff } from './editableHandoff';

export default function ContextualInspector({ selected, resolvedHandoff, renderedValue, onSave, onHandoff, canEditFactInspector = false }: {
  selected: InspectorDescriptor | null;
  resolvedHandoff?: ResolvedHandoff;
  renderedValue: string;
  onSave: (descriptor: InspectorDescriptor, value: string) => Promise<void>;
  onHandoff: (target: ResolvedHandoff) => void;
  canEditFactInspector?: boolean;
}) {
  const [notice, setNotice] = useState<string | null>(null); const [pending, startTransition] = useTransition();
  const owner = selected?.owner;
  const control = selected?.inspectorControl;
  const directFactInspector = owner === 'fact' && selected?.editorSurface === 'design-inspector';
  const defaultMessage = !selected ? 'Select an element on the brochure.' : selected.owner === 'design' ? 'Edit this presentation field in the inspector.' : directFactInspector ? 'Edit this Designer copy here; it will be saved to canonical Facts.' : selected.owner === 'system' ? 'This is locale-owned system copy. It has no quotation-level editor.' : selected.owner === 'fact-derived' ? 'This is a derived value. Open its source Facts; do not create a second brochure field.' : `This field is owned by ${selected.owner === 'fact' ? 'Facts' : 'Content Studio'}.`;
  return <aside className="grid content-start gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
    <p aria-live="polite" className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>{notice ?? defaultMessage}</p>
    {!selected ? null : <><h2 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>{selected.fieldId.replaceAll('.', ' · ')}</h2>
      {control !== 'none' && (owner === 'design' || directFactInspector) ? <DesignControl key={`${selected.fieldId}:${renderedValue}`} initialValue={renderedValue} control={control === 'textarea' ? 'textarea' : 'text'} pending={pending} disabled={directFactInspector && !canEditFactInspector} allowEmpty={directFactInspector} label={directFactInspector ? 'Designer copy (saved to Facts)' : 'Presentation copy'} onSave={(value) => startTransition(async () => { try { await onSave(selected, value); setNotice(directFactInspector ? 'Designer copy saved to Facts.' : 'Design override saved.'); } catch (error) { setNotice(error instanceof Error ? error.message : 'Designer copy could not be saved.'); } })} /> : <><p className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>{owner === 'system' ? 'System copy has no quotation-level editor.' : `Canonical source: ${resolvedHandoff?.source ?? selected.source}.`}</p>{resolvedHandoff ? <button type="button" onClick={() => onHandoff(resolvedHandoff)} className={cn(getTypographyClassName('buttonSecondary'), 'w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2')}>Open {resolvedHandoff.stage === 'facts' ? 'Facts' : 'Content Studio'}</button> : null}</>}
    </>}
  </aside>;
}

function DesignControl({ initialValue, control, pending, disabled, allowEmpty, label, onSave }: { initialValue: string; control: 'text' | 'textarea'; pending: boolean; disabled: boolean; allowEmpty: boolean; label: string; onSave: (value: string) => void }) {
  const [value, setValue] = useState(initialValue);
  return <><label className="grid gap-2"><span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>{label}</span>
    {control === 'textarea' ? <textarea value={value} disabled={disabled} onChange={(event) => setValue(event.target.value)} className={cn(getTypographyClassName('bodySm'), 'min-h-28 rounded-[var(--radius-card)] border border-[var(--color-border)] p-3')} /> : <input value={value} disabled={disabled} onChange={(event) => setValue(event.target.value)} className={cn(getTypographyClassName('bodySm'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3')} />}
  </label><button type="button" disabled={disabled || pending || (!allowEmpty && !value.trim())} onClick={() => onSave(value.trim())} className={cn(getTypographyClassName('buttonPrimary'), 'w-fit rounded-[var(--radius-button)] bg-[var(--color-action-primary-surface)] px-4 py-2 text-[var(--color-action-primary-text)] disabled:opacity-50')}>Save</button></>;
}
