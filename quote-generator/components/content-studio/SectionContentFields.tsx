'use client';

import { AlertCircle } from 'lucide-react';
import { cn } from '../../utils/cn.ts';
import { getTypographyClassName } from '../../config/typography.ts';
import { contentReconciler } from '../../lib/rules/contentReconciler.ts';
import type { ContentCandidate, ContentEditorField } from '../quotation-workspace/useQuotationWorkspace.ts';
import { RichTextEditor } from '../ui/RichTextEditor.tsx';

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

function CharacterBudgetMeter({
  budgetType,
  text,
}: {
  budgetType: string;
  text: string | string[] | null | undefined;
}) {
  const result = contentReconciler.validatePdfTextBudget(budgetType, text);

  if (result.overflow > 0) {
    return (
      <div className="flex items-center justify-between gap-2 mt-1 px-1">
        <div className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400">
          <AlertCircle size={14} className="shrink-0" aria-hidden="true" />
          <span className={cn(getTypographyClassName('caption'), 'text-rose-600 dark:text-rose-400')}>
            Vượt quá giới hạn trang in PDF A4 (vượt {result.overflow} ký tự)
          </span>
        </div>
        <span className={cn(getTypographyClassName('caption'), 'text-rose-600 dark:text-rose-400')}>
          {result.current} / {result.max}
        </span>
      </div>
    );
  }

  return (
    <div className="flex justify-end mt-1 px-1">
      <span className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)]')}>
        {result.current} / {result.max} ký tự
      </span>
    </div>
  );
}

function FieldEditor({
  scope,
  field,
  candidate,
  onChange,
  document,
}: {
  scope?: string;
  field: ContentEditorField;
  candidate: ContentCandidate;
  onChange: (value: ContentCandidate) => void;
  document?: Record<string, unknown>;
}) {
  const budgetType = contentReconciler.deriveBudgetType(scope, field.id, field.path);

  if (field.control === 'string-list') {
    const items = Array.isArray(readValue(candidate, field.path)) ? (readValue(candidate, field.path) as unknown[]).map(String) : [];
    const segmentBound = field.id === 'route-stop-descriptions';
    const staySegments = (
      ((document?.route as Record<string, unknown>)?.staySegments ||
      (candidate?.route as Record<string, unknown>)?.staySegments) as Array<Record<string, unknown>>
    ) || [];

    return (
      <fieldset className="grid gap-3">
        <legend className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>{field.label}</legend>

        {items.map((item, index) => {
          if (!segmentBound) {
            return (
              <div key={`${field.id}-${index}`} className="grid gap-1.5">
                <span className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)]')}>Item {index + 1}</span>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
                  <div className="min-w-0 flex-1">
                    <RichTextEditor
                      value={item}
                      minHeight="4rem"
                      onChange={(nextVal) =>
                        onChange(writeValue(candidate, field.path, items.map((current, currentIndex) => currentIndex === index ? nextVal : current)))
                      }
                    />
                    <CharacterBudgetMeter budgetType={budgetType} text={item} />
                  </div>
                  <button
                    type="button"
                    onClick={() => onChange(writeValue(candidate, field.path, items.filter((_, currentIndex) => currentIndex !== index)))}
                    className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border)] px-3')}
                  >
                    Remove
                  </button>
                </div>
              </div>
            );
          }

          const segment = staySegments[index];
          const cityName = String(segment?.displayName ?? segment?.city ?? `Stop ${index + 1}`);
          const daysLabel = String(segment?.daysLabel ?? '');
          const nightsLabel = String(segment?.nightsLabel ?? '');
          const hotelName = String(segment?.hotelName ?? '');
          const activityPreviews = Array.isArray(segment?.activityPreviews) ? (segment.activityPreviews as Array<Record<string, unknown>>) : [];
          const fallbackDesc = activityPreviews
            .map((ap) => {
              const lbl = String(ap.label ?? '');
              const sum = String(ap.summary ?? '');
              return lbl && sum ? `${lbl}: ${sum}` : sum || lbl;
            })
            .filter(Boolean)
            .join(' ');

          return (
            <div key={`${field.id}-${index}`} className="grid gap-2.5 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border)] pb-2">
                <div className="flex items-center gap-2">
                  <span className={cn(getTypographyClassName('caption'), 'inline-flex items-center justify-center rounded-md bg-[var(--color-primary)] px-2 py-0.5 text-white')}>
                    Stop {String(index + 1).padStart(2, '0')}
                  </span>
                  <span className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>
                    {cityName}
                  </span>
                </div>
                {daysLabel ? (
                  <span className={cn(getTypographyClassName('caption'), 'inline-flex items-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-0.5 text-[var(--color-muted)]')}>
                    {daysLabel} {nightsLabel ? `• ${nightsLabel}` : ''}
                  </span>
                ) : null}
              </div>

              {hotelName ? (
                <p className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)]')}>
                  <strong className="text-[var(--color-on-surface)]">Hotel:</strong> {hotelName}
                </p>
              ) : null}

              <div className="grid gap-1">
                <label className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>
                  Description for brochure map & timeline
                </label>
                <RichTextEditor
                  value={item}
                  placeholder={fallbackDesc ? `Default preview: "${fallbackDesc}"` : 'Write custom description for this stop...'}
                  minHeight="5rem"
                  onChange={(nextVal) =>
                    onChange(writeValue(candidate, field.path, items.map((current, currentIndex) => currentIndex === index ? nextVal : current)))
                  }
                />
                <CharacterBudgetMeter budgetType="route_stop_description" text={item} />
                {!item && fallbackDesc ? (
                  <p className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)] opacity-80')}>
                    Left empty: Will display default activity summary on brochure map & timeline.
                  </p>
                ) : null}
              </div>
            </div>
          );
        })}

        {segmentBound ? (
          <div className={cn(getTypographyClassName('caption'), 'rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-[var(--color-muted)]')}>
            <strong className="text-[var(--color-on-surface)]">Fact-derived Destinations:</strong> Route stops are generated automatically from your approved itinerary stays. Update <strong>Itinerary Facts</strong> to change the number of destinations.
          </div>
        ) : (
          <button
            type="button"
            onClick={() => onChange(writeValue(candidate, field.path, [...items, '']))}
            className={cn(getTypographyClassName('buttonSecondary'), 'min-h-11 w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-2')}
          >
            Add item
          </button>
        )}
      </fieldset>
    );
  }

  const value = typeof readValue(candidate, field.path) === 'string' ? String(readValue(candidate, field.path)) : '';
  return (
    <div className="grid gap-1.5">
      <label className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>{field.label}</label>
      {field.control === 'textarea' ? (
        <RichTextEditor value={value} minHeight="6rem" onChange={(nextVal) => onChange(writeValue(candidate, field.path, nextVal))} />
      ) : (
        <RichTextEditor value={value} singleLine onChange={(nextVal) => onChange(writeValue(candidate, field.path, nextVal))} />
      )}
      <CharacterBudgetMeter budgetType={budgetType} text={value} />
    </div>
  );
}

export function SectionContentFields({
  scope,
  fields,
  candidate,
  onChange,
  document,
}: {
  scope?: string;
  fields: ContentEditorField[];
  candidate: ContentCandidate;
  onChange: (value: ContentCandidate) => void;
  document?: Record<string, unknown>;
}) {
  return (
    <section className="grid gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div>
        <h3 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>Brochure content</h3>
        <p className={cn(getTypographyClassName('bodySm'), 'mt-1 text-[var(--color-muted)]')}>Write directly, or generate into these fields. Nothing is published until Apply.</p>
      </div>
      {fields.map((field) => (
        <FieldEditor key={field.id} scope={scope} field={field} candidate={candidate} onChange={onChange} document={document} />
      ))}
    </section>
  );
}
