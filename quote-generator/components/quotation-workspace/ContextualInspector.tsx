'use client';

import { useState, useTransition } from 'react';
import { AlertCircle, Camera } from 'lucide-react';
import { getTypographyClassName } from '../../config/typography.ts';
import { cn } from '../../utils/cn.ts';
import type { InspectorDescriptor } from './BoundaryCanvas.tsx';
import type { ResolvedHandoff } from './editableHandoff.ts';
import type { QuotationFacts } from './factsTypes.ts';
import type { FactInspectorPatch } from './DesignCanvas.tsx';
import { inferGreetingName, inferPartyLabel } from '../../lib/prefillRules.ts';
import { contentReconciler } from '../../lib/rules/contentReconciler.ts';
import { RichTextEditor } from '../ui/RichTextEditor.tsx';

export default function ContextualInspector({
  selected,
  resolvedHandoff,
  renderedValue,
  onSave,
  onHandoff,
  canEditFactInspector = false,
  facts,
  onSaveFactFields,
  onOpenMediaDrawer,
  mediaValue,
}: {
  selected: InspectorDescriptor | null;
  resolvedHandoff?: ResolvedHandoff;
  renderedValue: string;
  onSave: (descriptor: InspectorDescriptor, value: string) => Promise<void>;
  onHandoff: (target: ResolvedHandoff) => void;
  canEditFactInspector?: boolean;
  facts?: QuotationFacts;
  onSaveFactFields?: (patch: FactInspectorPatch) => Promise<void>;
  onOpenMediaDrawer?: (descriptor: InspectorDescriptor) => void;
  mediaValue?: unknown;
}) {
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const owner = selected?.owner;
  const control = selected?.inspectorControl;
  const directFactInspector = owner === 'fact' && selected?.editorSurface === 'design-inspector';
  const isContentField = owner === 'content';
  const isMediaField = selected?.kind === 'image' || selected?.kind === 'gallery' || Boolean(selected?.fieldId?.includes('Image') || selected?.fieldId?.includes('gallery') || selected?.source?.includes('gallery') || selected?.source?.includes('Image'));

  const defaultMessage = !selected
    ? 'Select an element on the brochure.'
    : selected.owner === 'design'
    ? 'Edit this presentation field in the inspector.'
    : directFactInspector
    ? 'Edit this field copy here; it will be saved to Facts.'
    : isContentField
    ? 'Edit this content field here; it will be saved to Canonical Document.'
    : selected.owner === 'system'
    ? 'This is locale-owned system copy. It has no quotation-level editor.'
    : selected.owner === 'fact-derived'
    ? 'This is a derived value. Open its source Facts; do not create a second brochure field.'
    : `This field is owned by ${selected.owner === 'fact' ? 'Facts' : 'Content Studio'}.`;

  const customerName = facts?.customer_facts?.customer_name ?? null;
  const adults = facts?.customer_facts?.adults ?? null;
  const children = facts?.customer_facts?.children ?? null;

  const isGreetingField = selected?.fieldId === 'customer.greetingName';
  const isPartyField = selected?.fieldId === 'customer.partyLabel';

  const budgetType = selected ? contentReconciler.deriveBudgetType(resolvedHandoff?.section ?? selected.section, selected.fieldId) : undefined;

  return (
    <aside className="grid content-start gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <p aria-live="polite" className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>
        {notice ?? defaultMessage}
      </p>

      {selected ? (
        <>
          <h2 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>
            {selected.fieldId.replaceAll('.', ' · ')}
          </h2>

          {isMediaField && onOpenMediaDrawer ? (
            <MediaControl
              selected={selected}
              mediaValue={mediaValue}
              renderedValue={renderedValue}
              onOpenMediaDrawer={onOpenMediaDrawer}
            />
          ) : (control !== 'none' && (owner === 'design' || directFactInspector)) || isContentField ? (
            <div className="grid gap-2">
              <DesignControl
                key={`${selected.fieldId}:${renderedValue}`}
                initialValue={renderedValue}
                control={control === 'textarea' || selected.fieldId === 'bookingTerms.body' ? 'textarea' : 'text'}
                pending={pending}
                disabled={directFactInspector && !canEditFactInspector}
                allowEmpty={directFactInspector || isContentField}
                budgetType={isContentField ? budgetType : undefined}
                label={
                  isContentField
                    ? 'Content copy (saved to Canonical Document)'
                    : directFactInspector
                    ? (selected?.fieldId.startsWith('designer.') ? 'Designer copy (saved to Facts)' : 'Copy / Setting (saved to Facts)')
                    : 'Presentation copy'
                }
                onSave={(value) =>
                  startTransition(async () => {
                    try {
                      await onSave(selected, value);
                      setNotice(isContentField ? 'Content saved.' : 'Copy saved.');
                    } catch (error) {
                      setNotice(error instanceof Error ? error.message : 'Copy could not be saved.');
                    }
                  })
                }
              />

              {isGreetingField && onSaveFactFields ? (
                <button
                  type="button"
                  disabled={pending || (directFactInspector && !canEditFactInspector)}
                  onClick={() =>
                    startTransition(async () => {
                      const auto = inferGreetingName(customerName);
                      await onSaveFactFields({ customer_greeting_name: auto });
                      setNotice('Auto-generated greeting name saved.');
                    })
                  }
                  className={cn(getTypographyClassName('caption'), 'w-fit text-[var(--color-accent)] hover:underline mt-1 cursor-pointer')}
                >
                  Auto-generate greeting name
                </button>
              ) : null}

              {isPartyField && onSaveFactFields ? (
                <button
                  type="button"
                  disabled={pending || (directFactInspector && !canEditFactInspector)}
                  onClick={() =>
                    startTransition(async () => {
                      const auto = inferPartyLabel(customerName, adults, children);
                      await onSaveFactFields({ customer_party_label: auto });
                      setNotice('Auto-generated party label saved.');
                    })
                  }
                  className={cn(getTypographyClassName('caption'), 'w-fit text-[var(--color-accent)] hover:underline mt-1 cursor-pointer')}
                >
                  Auto-generate party label
                </button>
              ) : null}

              {resolvedHandoff ? (
                <button
                  type="button"
                  onClick={() => onHandoff(resolvedHandoff)}
                  className={cn(getTypographyClassName('caption'), 'w-fit text-[var(--color-muted)] hover:text-[var(--color-accent)] hover:underline mt-2 flex items-center gap-1 cursor-pointer')}
                >
                  <span>Open {resolvedHandoff.stage === 'facts' ? 'Facts' : 'Content Studio'}</span>
                </button>
              ) : null}
            </div>
          ) : (
            <>
              <p className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>
                {owner === 'system'
                  ? 'System copy has no quotation-level editor.'
                  : `Canonical source: ${resolvedHandoff?.source ?? selected.source}.`}
              </p>
              {resolvedHandoff ? (
                <button
                  type="button"
                  onClick={() => onHandoff(resolvedHandoff)}
                  className={cn(getTypographyClassName('buttonSecondary'), 'w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2 cursor-pointer')}
                >
                  Open {resolvedHandoff.stage === 'facts' ? 'Facts' : 'Content Studio'}
                </button>
              ) : null}
            </>
          )}
        </>
      ) : null}
    </aside>
  );
}

function MediaControl({
  selected,
  mediaValue,
  renderedValue,
  onOpenMediaDrawer,
}: {
  selected: InspectorDescriptor;
  mediaValue?: unknown;
  renderedValue: string;
  onOpenMediaDrawer: (descriptor: InspectorDescriptor) => void;
}) {
  const isGallery = selected.kind === 'gallery' || selected.fieldId.includes('gallery');

  let rawUrl = '';
  let source = 'auto';
  if (mediaValue && typeof mediaValue === 'object') {
    if (Array.isArray(mediaValue) && mediaValue.length > 0) {
      rawUrl = mediaValue[0]?.url || mediaValue[0]?.r2Key || '';
      source = mediaValue[0]?.source || 'auto';
    } else {
      const val = mediaValue as Record<string, unknown>;
      rawUrl = (val.url as string) || (val.r2Key as string) || '';
      source = (val.source as string) || 'auto';
    }
  } else if (renderedValue && (renderedValue.startsWith('http') || renderedValue.startsWith('/') || renderedValue.startsWith('data:'))) {
    rawUrl = renderedValue;
  }

  const isAuto = source === 'auto';
  const label = isAuto ? 'R2 default' : 'Manual selection';

  return (
    <div className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-3">
      <div className="flex items-center justify-between">
        <span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>
          {isGallery ? 'Brochure gallery' : 'Brochure image'}
        </span>
        <span
          className={cn(
            getTypographyClassName('caption'),
            'rounded-full px-2 py-0.5 border',
            isAuto
              ? 'border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300'
              : 'border-[var(--color-accent)]/30 bg-[var(--color-accent)]/10 text-[var(--color-accent)]'
          )}
        >
          {label}
        </span>
      </div>

      {rawUrl ? (
        <div className="relative aspect-video w-full overflow-hidden rounded-[var(--radius-button)] border border-[var(--color-border)] bg-black/5">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={rawUrl}
            alt={selected.fieldId}
            className="h-full w-full object-cover"
          />
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => onOpenMediaDrawer(selected)}
        className={cn(
          getTypographyClassName('buttonPrimary'),
          'flex items-center justify-center gap-2 min-h-10 w-full rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 py-2 transition-all cursor-pointer'
        )}
      >
        <Camera size={16} aria-hidden="true" />
        <span>{isGallery ? 'Manage Gallery' : 'Change Image'}</span>
      </button>
    </div>
  );
}

function DesignControl({
  initialValue,
  control,
  pending,
  disabled,
  allowEmpty,
  label,
  budgetType,
  onSave,
}: {
  initialValue: string;
  control: 'text' | 'textarea';
  pending: boolean;
  disabled: boolean;
  allowEmpty: boolean;
  label: string;
  budgetType?: string;
  onSave: (value: string) => void;
}) {
  const [value, setValue] = useState(initialValue);
  const budgetResult = budgetType ? contentReconciler.validatePdfTextBudget(budgetType, value) : null;

  return (
    <>
      <div className="grid gap-2">
        <label className="grid gap-2">
          <span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>{label}</span>
          {control === 'textarea' || value.includes('\n') || value.length > 80 ? (
            <RichTextEditor value={value} minHeight="6rem" onChange={(val) => setValue(val)} />
          ) : (
            <RichTextEditor value={value} singleLine onChange={(val) => setValue(val)} />
          )}
        </label>
        {budgetResult ? (
          budgetResult.overflow > 0 ? (
            <div className="flex items-center justify-between gap-2 px-1">
              <div className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400">
                <AlertCircle size={14} className="shrink-0" aria-hidden="true" />
                <span className={cn(getTypographyClassName('caption'), 'text-rose-600 dark:text-rose-400')}>
                  Vượt quá giới hạn trang in PDF A4 (vượt {budgetResult.overflow} ký tự)
                </span>
              </div>
              <span className={cn(getTypographyClassName('caption'), 'text-rose-600 dark:text-rose-400')}>
                {budgetResult.current} / {budgetResult.max}
              </span>
            </div>
          ) : (
            <div className="flex justify-end px-1">
              <span className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)]')}>
                {budgetResult.current} / {budgetResult.max} ký tự
              </span>
            </div>
          )
        ) : null}
      </div>
      <button
        type="button"
        disabled={disabled || pending || (!allowEmpty && !value.trim())}
        onClick={() => onSave(value.trim())}
        className={cn(
          getTypographyClassName('buttonPrimary'),
          'w-fit rounded-[var(--radius-button)] bg-[var(--color-action-primary-surface)] px-4 py-2 text-[var(--color-action-primary-text)] disabled:opacity-50 cursor-pointer',
        )}
      >
        {pending ? 'Saving…' : 'Save'}
      </button>
    </>
  );
}
