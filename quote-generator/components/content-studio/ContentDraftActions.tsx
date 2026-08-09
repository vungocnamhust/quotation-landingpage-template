'use client';

import { cn } from '../../utils/cn';
import { getTypographyClassName } from '../../config/typography';

export function ContentDraftActions({ hasDraft, pending, onSave, onApply, onDiscard }: { hasDraft: boolean; pending: boolean; onSave: () => void; onApply: () => void; onDiscard: () => void }) {
  const actionClass = 'min-h-11 rounded-[var(--radius-button)] px-3 py-2 lg:min-h-9';
  return <div className="flex flex-wrap items-center gap-2"><button type="button" disabled={pending} onClick={onSave} className={cn(getTypographyClassName('buttonSecondary'), actionClass, 'border border-[var(--color-border)] disabled:opacity-50')}>Save draft</button><button type="button" disabled={pending || !hasDraft} onClick={onApply} className={cn(getTypographyClassName('buttonPrimary'), actionClass, 'bg-[var(--color-action-primary-surface)] text-[var(--color-action-primary-text)] disabled:opacity-50')}>Apply to brochure</button>{hasDraft ? <button type="button" disabled={pending} onClick={onDiscard} className={cn(getTypographyClassName('buttonSecondary'), actionClass, 'border border-[var(--color-border)] disabled:opacity-50')}>Discard</button> : null}</div>;
}
