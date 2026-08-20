'use client';

import { useEffect, useRef, useState } from 'react';
import type { DisplayDocument } from '../../display/runtimePageBuilder.ts';
import { quotationFetch, apiErrorMessage } from '../../lib/apiError.ts';
import type { EditableBrochureContract } from './useQuotationWorkspace.ts';
import BoundaryCanvas, { type InspectorDescriptor, type ResolvedInspectorSelection } from './BoundaryCanvas.tsx';
import ContextualInspector from './ContextualInspector.tsx';
import MediaDrawer from './MediaDrawer.tsx';
import { matchEditableSource, resolveInspectorDescriptor, resolveEditableHandoff, type ResolvedHandoff } from './editableHandoff.ts';
import type { QuotationFacts } from './factsTypes.ts';
import { useToast } from '../staff-workspace/ToastProvider.tsx';

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';

export type FactInspectorPatch = Partial<
  Pick<QuotationFacts['designer_facts'], 'seller_subtitle' | 'designer_kicker' | 'designer_title' | 'designer_quote' | 'designer_signature' | 'designer_experience' | 'cta_body'>
> & {
  booking_title?: string | null;
  booking_description?: string | null;
  customer_market?: string | null;
  customer_greeting_name?: string | null;
  customer_party_label?: string | null;
};

export const DESIGNER_FACT_FIELD_BY_DESCRIPTOR = {
  'designer.kicker': 'designer_kicker',
  'designer.title': 'designer_title',
  'designer.subtitle': 'seller_subtitle',
  'designer.quote': 'designer_quote',
  'designer.signature': 'designer_signature',
  'designer.experience': 'designer_experience',
  'designer.ctaBody': 'cta_body',
  'bookingTerms.title': 'booking_title',
  'bookingTerms.body': 'booking_description',
  'customer.greetingName': 'customer_greeting_name',
  'customer.partyLabel': 'customer_party_label',
} as const;

function setDocumentPath(
  document: Record<string, unknown>,
  source: string,
  value: unknown
): Record<string, unknown> {
  const parts = source.startsWith('/') ? source.slice(1).split('/') : source.split('.');
  const clone = JSON.parse(JSON.stringify(document)) as Record<string, unknown>;
  let cursor: Record<string, unknown> | unknown[] = clone;

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    const isLast = i === parts.length - 1;
    const nextPart = parts[i + 1];
    const nextIsNumeric = nextPart !== undefined && /^\d+$/.test(nextPart);
    const key = /^\d+$/.test(part) ? Number(part) : part;

    if (isLast) {
      (cursor as Record<string | number, unknown>)[key] = value;
    } else {
      const currentVal = (cursor as Record<string | number, unknown>)[key];
      if (currentVal === undefined || currentVal === null || typeof currentVal !== 'object') {
        (cursor as Record<string | number, unknown>)[key] = nextIsNumeric ? [] : {};
      }
      cursor = (cursor as Record<string | number, unknown>)[key] as Record<string, unknown> | unknown[];
    }
  }

  return clone;
}

function readDocumentPath(document: Record<string, unknown>, source: string): unknown {
  const parts = source.startsWith('/') ? source.slice(1).split('/') : source.split('.');
  let cursor: unknown = document;

  for (const part of parts) {
    if (cursor === undefined || cursor === null || typeof cursor !== 'object') {
      return undefined;
    }
    const key = /^\d+$/.test(part) ? Number(part) : part;
    cursor = (cursor as Record<string | number, unknown>)[key];
  }

  return cursor;
}

function findMediaMatch(
  mediaSlots: NonNullable<EditableBrochureContract['mediaSlotRegistry']>,
  selected: InspectorDescriptor | null
) {
  if (!selected) return null;
  for (const slot of mediaSlots) {
    const template = slot.fieldTemplate;
    const source = slot.source;
    if (template === selected.fieldId) {
      return { slot, fieldId: template };
    }
    const wildcardIndices = matchEditableSource(source, selected.source);
    if (wildcardIndices && wildcardIndices.length > 0) {
      const sourceParts = selected.source.slice(1).split('/');
      const indexVal = sourceParts[wildcardIndices[0]];
      const concreteFieldId = template.includes('*') ? template.replace('*', indexVal) : template;
      return { slot, fieldId: concreteFieldId };
    }
  }
  if (selected.fieldId.startsWith('hero.bannerImage')) {
    return {
      slot: {
        fieldTemplate: 'hero.bannerImage',
        source: '/hero/bannerImage',
        editorRoute: 'hero',
        pickerContext: 'library' as const,
        minItems: 1,
        maxItems: 1,
        requiredForPublish: true,
      },
      fieldId: 'hero.bannerImage',
    };
  }
  return null;
}

export default function DesignCanvas({
  quotationId,
  lang,
  model,
  document,
  currentRevision,
  canEditDesignerFacts,
  contract,
  facts,
  onSaved,
  onSaveDesignerFacts,
  onHandoff,
  focus,
}: {
  quotationId: string;
  lang: string;
  model: DisplayDocument;
  document: Record<string, unknown>;
  currentRevision: number;
  canEditDesignerFacts: boolean;
  contract?: EditableBrochureContract;
  facts?: QuotationFacts;
  onSaved: () => Promise<unknown> | void;
  onSaveDesignerFacts: (next: FactInspectorPatch) => Promise<void>;
  onHandoff: (target: ResolvedHandoff) => void;
  focus?: string;
}) {
  const { toast, notify, clearScope } = useToast();
  const [selected, setSelected] = useState<InspectorDescriptor | null>(null);
  const [resolvedHandoff, setResolvedHandoff] = useState<ResolvedHandoff | undefined>();
  const [renderedValue, setRenderedValue] = useState('');
  const [selectedTop, setSelectedTop] = useState<number | null>(null);
  const [isMediaDrawerOpen, setIsMediaDrawerOpen] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);
  const inspectorRef = useRef<HTMLDivElement>(null);

  const mediaSlots = contract?.mediaSlotRegistry ?? [];
  const activeMediaMatch = findMediaMatch(mediaSlots, selected);
  const activeMediaValue = selected ? readDocumentPath(document, selected.source) : null;

  useEffect(() => {
    if (!focus) return;

    const timer = window.setTimeout(() => {
      const canvas = sectionRef.current;
      if (!canvas) return;

      let targetEl: HTMLElement | null = null;

      // 1. Try exact data-editable
      targetEl = canvas.querySelector<HTMLElement>(`[data-editable="${focus}"]`);

      // 2. Try prefix match on data-editable
      if (!targetEl && focus.startsWith('/')) {
        targetEl = canvas.querySelector<HTMLElement>(`[data-editable^="${focus}"]`);
      }

      // 3. Try day:index:N grammar
      if (!targetEl && focus.startsWith('day:')) {
        const parts = focus.split(':');
        const indexStr = parts[parts.length - 1];
        targetEl =
          canvas.querySelector<HTMLElement>(`[data-editable^="/itinerary/days/${indexStr}/description"]`) ||
          canvas.querySelector<HTMLElement>(`[data-editable^="/itinerary/days/${indexStr}/title"]`) ||
          canvas.querySelector<HTMLElement>(`[data-editable^="/itinerary/days/${indexStr}"]`);
      }

      // 4. Try hotel:index:N grammar
      if (!targetEl && focus.startsWith('hotel:')) {
        const parts = focus.split(':');
        const indexStr = parts[parts.length - 1];
        targetEl =
          canvas.querySelector<HTMLElement>(`[data-editable^="/stays/hotels/${indexStr}/hotelImage"]`) ||
          canvas.querySelector<HTMLElement>(`[data-editable^="/stays/hotels/${indexStr}"]`);
      }

      // 5. Try fieldId match via contract
      if (!targetEl && contract?.fields) {
        const matchedField = contract.fields.find((f) => f.fieldId === focus);
        if (matchedField) {
          const sourcePrefix = matchedField.source.replace(/\*.*$/, '');
          targetEl = canvas.querySelector<HTMLElement>(`[data-editable^="${sourcePrefix}"]`);
        }
      }

      if (targetEl) {
        // a) Smoothly scroll into center
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // b) Apply pulse highlight ring for 2 seconds
        targetEl.dataset.workspaceHighlighted = 'true';
        const clearHighlight = window.setTimeout(() => {
          targetEl?.removeAttribute('data-workspace-highlighted');
        }, 2000);

        // c) Trigger selection to open right inspector
        const source = targetEl.dataset.editable ?? '';
        const matched = resolveInspectorDescriptor(contract?.fields ?? [], source);
        if (matched) {
          const canvasTop = sectionRef.current?.getBoundingClientRect().top ?? 0;
          const elemTop = targetEl.getBoundingClientRect().top;
          const relativeTop = Math.max(0, elemTop - canvasTop);

          const editorValue = targetEl.getAttribute('data-workspace-editor-value');
          const val = editorValue !== null ? editorValue : (targetEl.getAttribute('aria-label') || targetEl.textContent || '').trim();

          setSelected(matched.descriptor);
          setResolvedHandoff(resolveEditableHandoff(matched.descriptor, source, document));
          setRenderedValue(val);
          if (inspectorRef.current) {
            const inspectorHeight = inspectorRef.current.offsetHeight;
            const top = Math.max(0, relativeTop - inspectorHeight / 2);
            setSelectedTop(Math.max(0, top));
          }
        }

        return () => window.clearTimeout(clearHighlight);
      }
    }, 150);

    return () => window.clearTimeout(timer);
  }, [focus, contract?.fields, document]);

  const saveCanonicalDocument = async (nextDoc: Record<string, unknown>, retryCount = 0): Promise<void> => {
    try {
      await quotationFetch(
        `${API_BASE}/api/v2/quotations/${quotationId}/document?lang=${encodeURIComponent(lang)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            document: nextDoc,
            baseRevision: currentRevision,
          }),
        },
        'Document content could not be saved.'
      );
      await onSaved();
    } catch (error) {
      if (retryCount < 1 && error instanceof Error && error.message.includes('conflict')) {
        await onSaved();
        return saveCanonicalDocument(nextDoc, retryCount + 1);
      }
      throw error;
    }
  };

  const savePresentationOverride = async (
    fieldId: string,
    value: string,
    identityKey?: string,
    retryCount = 0
  ): Promise<void> => {
    try {
      await quotationFetch(
        `${API_BASE}/api/v2/quotations/${quotationId}/presentation/overrides?lang=${encodeURIComponent(lang)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            baseRevision: currentRevision,
            copyOverrides: identityKey ? {} : { [fieldId]: value },
            identityOverrides: identityKey ? { [identityKey]: value } : {},
          }),
        },
        'Design override could not be saved.'
      );
      await onSaved();
      clearScope('design:override');
      toast('Design override saved.', 'success');
    } catch (error) {
      if (retryCount < 1 && error instanceof Error && error.message.includes('conflict')) {
        await onSaved();
        return savePresentationOverride(fieldId, value, identityKey, retryCount + 1);
      }
      const message = apiErrorMessage(error);
      notify({
        message,
        type: 'error',
        persistent: true,
        scope: 'design:override',
        action: { label: 'Reload', onClick: () => window.location.reload() },
      });
      throw new Error(message);
    }
  };

  const saveMediaSlot = async (
    fieldId: string,
    mediaValue: unknown,
    retryCount = 0
  ): Promise<void> => {
    try {
      await quotationFetch(
        `${API_BASE}/api/v2/quotations/${quotationId}/facts/media?lang=${encodeURIComponent(lang)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            baseRevision: currentRevision,
            slots: [{ fieldId, value: mediaValue }],
          }),
        },
        'Media could not be saved.'
      );
      await onSaved();
      clearScope('design:media');
      toast('Media updated successfully.', 'success');
      setIsMediaDrawerOpen(false);
    } catch (error) {
      if (retryCount < 1 && error instanceof Error && error.message.includes('conflict')) {
        await onSaved();
        return saveMediaSlot(fieldId, mediaValue, retryCount + 1);
      }
      const message = apiErrorMessage(error);
      notify({
        message,
        type: 'error',
        persistent: true,
        scope: 'design:media',
        action: { label: 'Retry', onClick: () => void saveMediaSlot(fieldId, mediaValue) },
      });
      throw new Error(message);
    }
  };

  /**
   * Write-Target Dispatcher:
   * Dispatches updates to Canonical Document, Facts, Presentation Overrides or Media Facts safely.
   */
  const save = async (descriptor: InspectorDescriptor, value: string) => {
    // 1. Fact-owned fields (e.g. Designer, Greeting Name, Party Label, Booking Terms)
    const factField = DESIGNER_FACT_FIELD_BY_DESCRIPTOR[descriptor.fieldId as keyof typeof DESIGNER_FACT_FIELD_BY_DESCRIPTOR];
    if (descriptor.owner === 'fact' && (descriptor.editorSurface === 'design-inspector' || factField)) {
      if (canEditDesignerFacts && factField) {
        await onSaveDesignerFacts({ [factField]: value });
        await onSaved();
        toast('Facts updated.', 'success');
        return;
      }
      // Smart Fallback for dmc_handoff or read-only facts: Save to copyOverrides to prevent HTTP 403
      await savePresentationOverride(descriptor.fieldId, value);
      return;
    }

    // 2. Content-owned fields (e.g. Itinerary day summary, Overview letter, Route map description, Hero lede)
    if (descriptor.owner === 'content') {
      try {
        const nextDoc = setDocumentPath(document, descriptor.source, value);
        await saveCanonicalDocument(nextDoc);
        clearScope('design:content');
        toast('Content saved to brochure.', 'success');
      } catch (error) {
        const message = apiErrorMessage(error);
        notify({
          message,
          type: 'error',
          persistent: true,
          scope: 'design:content',
          action: { label: 'Retry', onClick: () => void save(descriptor, value) },
        });
        throw new Error(message);
      }
      return;
    }

    // 3. Design-owned fields (presentation copyOverrides / identityOverrides)
    if (descriptor.owner === 'design') {
      const identityKey = descriptor.source?.match(/^\/presentation\/identityOverrides\/([^/]+)$/)?.[1];
      await savePresentationOverride(descriptor.fieldId, value, identityKey);
      return;
    }

    // Fallback: save as presentation copyOverride
    await savePresentationOverride(descriptor.fieldId, value);
  };

  const select = (selection: ResolvedInspectorSelection, value: string) => {
    setSelected(selection.descriptor);
    setResolvedHandoff(selection.handoff);
    setRenderedValue(value);
    const top = selection.elementTop ?? 0;
    const section = sectionRef.current;
    const inspector = inspectorRef.current;
    if (section && inspector) {
      const maxTop = Math.max(0, section.offsetHeight - inspector.offsetHeight);
      setSelectedTop(Math.max(0, Math.min(top, maxTop)));
    } else {
      setSelectedTop(Math.max(0, top));
    }
  };

  const offset = selectedTop ?? 0;

  return (
    <>
      <section ref={sectionRef} className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <BoundaryCanvas model={model} document={document} contract={contract} onResolve={select} onHover={() => undefined} />
        <div
          className="relative"
          style={{ '--inspector-offset': `${offset}px` } as React.CSSProperties}
        >
          <div
            ref={inspectorRef}
            className="transition-transform duration-200 ease-out xl:[transform:translateY(var(--inspector-offset,0px))]"
          >
            <ContextualInspector
              selected={selected}
              resolvedHandoff={resolvedHandoff}
              renderedValue={renderedValue}
              onSave={save}
              onHandoff={onHandoff}
              canEditFactInspector={canEditDesignerFacts}
              facts={facts}
              onSaveFactFields={onSaveDesignerFacts}
              onOpenMediaDrawer={() => setIsMediaDrawerOpen(true)}
              mediaValue={activeMediaValue}
            />
          </div>
        </div>
      </section>

      {isMediaDrawerOpen && activeMediaMatch ? (
        <MediaDrawer
          open={isMediaDrawerOpen}
          onClose={() => setIsMediaDrawerOpen(false)}
          onSelect={(r2Key) => {
            void saveMediaSlot(activeMediaMatch.fieldId, { r2Key, source: 'manual' });
          }}
          onConfirm={(r2Keys) => {
            void saveMediaSlot(
              activeMediaMatch.fieldId,
              r2Keys.map((k) => ({ r2Key: k, source: 'manual' }))
            );
          }}
          context={
            activeMediaMatch.slot.pickerContext === 'library'
              ? undefined
              : {
                  kind: activeMediaMatch.slot.pickerContext as 'destination' | 'accommodation' | 'team',
                }
          }
          selectionMode={activeMediaMatch.slot.maxItems > 1 ? 'multiple' : 'single'}
          maxSelection={activeMediaMatch.slot.maxItems}
        />
      ) : null}
    </>
  );
}
