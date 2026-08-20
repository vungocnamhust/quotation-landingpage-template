'use client';

import { useState, useTransition } from 'react';
import { getTypographyClassName } from '../../config/typography.ts';
import { cn } from '../../utils/cn.ts';
import type { InspectorDescriptor } from './BoundaryCanvas.tsx';
import type { ResolvedHandoff } from './editableHandoff.ts';
import type { QuotationFacts } from './factsTypes.ts';
import type { FactInspectorPatch } from './DesignCanvas.tsx';
import { inferGreetingName, inferPartyLabel } from '../../lib/prefillRules.ts';
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
}: {
  selected: InspectorDescriptor | null;
  resolvedHandoff?: ResolvedHandoff;
  renderedValue: string;
  onSave: (descriptor: InspectorDescriptor, value: string) => Promise<void>;
  onHandoff: (target: ResolvedHandoff) => void;
  canEditFactInspector?: boolean;
  facts?: QuotationFacts;
  onSaveFactFields?: (patch: FactInspectorPatch) => Promise<void>;
}) {
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const owner = selected?.owner;
  const control = selected?.inspectorControl;
  const directFactInspector = owner === 'fact' && selected?.editorSurface === 'design-inspector';

  const defaultMessage = !selected
    ? 'Select an element on the brochure.'
    : selected.owner === 'design'
    ? 'Edit this presentation field in the inspector.'
    : directFactInspector
    ? 'Edit this field copy here; it will be saved to Facts.'
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

          {control !== 'none' && (owner === 'design' || directFactInspector) ? (
            <div className="grid gap-2">
              <DesignControl
                key={`${selected.fieldId}:${renderedValue}`}
                initialValue={renderedValue}
                control={control === 'textarea' || selected.fieldId === 'bookingTerms.body' ? 'textarea' : 'text'}
                pending={pending}
                disabled={directFactInspector && !canEditFactInspector}
                allowEmpty={directFactInspector}
                label={directFactInspector ? (selected?.fieldId.startsWith('designer.') ? 'Designer copy (saved to Facts)' : 'Copy / Setting (saved to Facts)') : 'Presentation copy'}
                onSave={(value) =>
                  startTransition(async () => {
                    try {
                      await onSave(selected, value);
                      setNotice('Copy saved.');
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
                  className={cn(getTypographyClassName('caption'), 'w-fit text-[var(--color-accent)] hover:underline mt-1')}
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
                  className={cn(getTypographyClassName('caption'), 'w-fit text-[var(--color-accent)] hover:underline mt-1')}
                >
                  Auto-generate party label
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
                  className={cn(getTypographyClassName('buttonSecondary'), 'w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2')}
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

function DesignControl({
  initialValue,
  control,
  pending,
  disabled,
  allowEmpty,
  label,
  onSave,
}: {
  initialValue: string;
  control: 'text' | 'textarea';
  pending: boolean;
  disabled: boolean;
  allowEmpty: boolean;
  label: string;
  onSave: (value: string) => void;
}) {
  const [value, setValue] = useState(initialValue);
  return (
    <>
      <label className="grid gap-2">
        <span className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>{label}</span>
        {control === 'textarea' ? (
          <RichTextEditor value={value} minHeight="6rem" onChange={(val) => setValue(val)} />
        ) : (
          <RichTextEditor value={value} singleLine onChange={(val) => setValue(val)} />
        )}
      </label>
      <button
        type="button"
        disabled={disabled || pending || (!allowEmpty && !value.trim())}
        onClick={() => onSave(value.trim())}
        className={cn(
          getTypographyClassName('buttonPrimary'),
          'w-fit rounded-[var(--radius-button)] bg-[var(--color-action-primary-surface)] px-4 py-2 text-[var(--color-action-primary-text)] disabled:opacity-50',
        )}
      >
        Save
      </button>
    </>
  );
}
