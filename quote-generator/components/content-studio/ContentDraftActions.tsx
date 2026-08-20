'use client';

import { cn } from '../../utils/cn.ts';
import { getTypographyClassName } from '../../config/typography.ts';

export function ContentDraftActions({
  hasDraft,
  canApply,
  pending,
  onSave,
  onApply,
  onDiscard,
}: {
  hasDraft: boolean;
  canApply?: boolean;
  pending: boolean;
  onSave: () => void;
  onApply: () => void;
  onDiscard: () => void;
}) {
  const actionClass =
    'min-h-11 rounded-[var(--radius-button)] px-4 py-2 lg:min-h-9 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed';
  const isApplyEnabled = !pending && (canApply ?? hasDraft);

  return (
    <div className="flex flex-wrap items-center gap-2 pt-2">
      <button
        type="button"
        disabled={pending}
        onClick={onSave}
        className={cn(
          getTypographyClassName('buttonSecondary'),
          actionClass,
          'border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-surface-muted)]'
        )}
      >
        {pending ? 'Saving…' : 'Save draft'}
      </button>

      <button
        type="button"
        disabled={!isApplyEnabled}
        onClick={onApply}
        className={cn(
          getTypographyClassName('buttonPrimary'),
          actionClass,
          'bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] shadow-xs'
        )}
      >
        {pending ? 'Applying…' : 'Apply to brochure'}
      </button>

      {hasDraft ? (
        <button
          type="button"
          disabled={pending}
          onClick={onDiscard}
          className={cn(
            getTypographyClassName('buttonSecondary'),
            actionClass,
            'border border-[var(--color-border)] bg-transparent text-[var(--color-muted)] hover:text-[var(--color-on-surface)]'
          )}
        >
          Discard
        </button>
      ) : null}
    </div>
  );
}

