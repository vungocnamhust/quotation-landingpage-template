'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { DisplayDocument } from '../../display/runtimePageBuilder.ts';
import { apiErrorMessage } from '../../lib/apiError.ts';
import { buildContentMutation } from '../../lib/rules/designMutation.ts';
import type { EditableBrochureContract } from './useQuotationWorkspace.ts';
import BoundaryCanvas, { type InspectorDescriptor, type ResolvedInspectorSelection } from './BoundaryCanvas.tsx';
import ContextualInspector from './ContextualInspector.tsx';
import MediaDrawer from './MediaDrawer.tsx';
import { matchEditableSource, resolveInspectorDescriptor, resolveEditableHandoff, type ResolvedHandoff } from './editableHandoff.ts';
import type { QuotationFacts } from './factsTypes.ts';
import { useToast } from '../staff-workspace/ToastProvider.tsx';
import { useDesignCanvasSave } from './useDesignCanvasSave.ts';
import { useMediaSlotSave } from './useMediaSlotSave.ts';
import { withManualSource } from '../../lib/rules/mediaSlotReconciler.ts';

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
  immutableFacts,
  isEditingQuotation,
  factsSourceKind,
  businessVersionNumber,
  contract,
  facts,
  onSaved,
  onSaveDesignerFacts,
  onHandoff,
  onRequestEditQuotation,
  focus,
}: {
  quotationId: string;
  lang: string;
  model: DisplayDocument;
  document: Record<string, unknown>;
  currentRevision: number;
  canEditDesignerFacts: boolean;
  immutableFacts?: boolean;
  isEditingQuotation?: boolean;
  factsSourceKind?: string;
  businessVersionNumber?: number;
  contract?: EditableBrochureContract;
  facts?: QuotationFacts;
  onSaved: () => Promise<unknown> | void;
  onSaveDesignerFacts: (next: FactInspectorPatch) => Promise<void>;
  onHandoff: (target: ResolvedHandoff) => void;
  onRequestEditQuotation?: (target?: ResolvedHandoff) => void;
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
  const { patchContentValues, savePresentationOverride } = useDesignCanvasSave({
    quotationId,
    lang,
    currentRevision,
    onSaved,
    toast,
    notify,
    clearScope,
  });
  const { saveSlot } = useMediaSlotSave({ quotationId, lang, currentRevision, onSaved });

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

  /**
   * Write-Target Dispatcher:
   * Dispatches updates to Content, Facts, or Presentation Overrides safely.
   * A locked (owner === 'fact' | 'fact-derived') field with no direct-inspector
   * surface never reaches here — the Locked Panel offers only a handoff, no
   * save button — so there is deliberately no copyOverrides fallback for it
   * (Plan 16 §B5: that fallback created a silent, unreconciled shadow value).
   */
  const save = async (descriptor: InspectorDescriptor, value: string) => {
    // 1. Content-owned fields (e.g. Itinerary day summary, Overview letter, Route map description, Hero lede)
    if (descriptor.owner === 'content') {
      try {
        const mutation = buildContentMutation(descriptor.source, resolvedHandoff?.source, value);
        await patchContentValues([mutation]);
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

    // 2. Design-owned fields (presentation copyOverrides / identityOverrides)
    if (descriptor.owner === 'design') {
      const identityKey = descriptor.source?.match(/^\/presentation\/identityOverrides\/([^/]+)$/)?.[1];
      await savePresentationOverride(descriptor.fieldId, value, identityKey);
      return;
    }

    // 3. Designer-facts inspector surface (owner === 'fact', editorSurface === 'design-inspector')
    const factField = DESIGNER_FACT_FIELD_BY_DESCRIPTOR[descriptor.fieldId as keyof typeof DESIGNER_FACT_FIELD_BY_DESCRIPTOR];
    if (descriptor.owner === 'fact' && descriptor.editorSurface === 'design-inspector' && factField) {
      if (!canEditDesignerFacts) {
        throw new Error('Facts are immutable for this quotation version. Use Edit Quotation to make changes.');
      }
      await onSaveDesignerFacts({ [factField]: value });
      await onSaved();
      toast('Facts updated.', 'success');
      return;
    }

    throw new Error(`${descriptor.fieldId} is not editable from the Design canvas.`);
  };

  const saveMedia = async (fieldId: string, value: unknown) => {
    try {
      await saveSlot(fieldId, value);
      clearScope('design:media');
      toast('Media updated successfully.', 'success');
      setIsMediaDrawerOpen(false);
    } catch (error) {
      const message = apiErrorMessage(error);
      notify({
        message,
        type: 'error',
        persistent: true,
        scope: 'design:media',
        action: { label: 'Retry', onClick: () => void saveMedia(fieldId, value) },
      });
    }
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

  const activeInitialPrefix = useMemo(() => {
    if (!activeMediaMatch) return undefined;
    const fieldId = activeMediaMatch.fieldId;
    if (fieldId.startsWith('itinerary.days.')) {
      const dayIndex = Number(fieldId.split('.')[2]);
      const day = facts?.trip_facts?.itinerary?.[dayIndex];
      const destRef = day?.destination_ref;
      return (
        destRef?.mediaPrefix ||
        destRef?.defaultMediaPrefix ||
        (destRef?.slug ? `destination/${destRef.slug}` : undefined)
      );
    }
    if (fieldId.startsWith('stays.hotels.')) {
      const hotelIndex = Number(fieldId.split('.')[2]);
      const hotel = facts?.service_facts?.hotels?.[hotelIndex];
      const destRef = hotel?.destination_ref;
      return (
        destRef?.mediaPrefix ||
        destRef?.defaultMediaPrefix ||
        (destRef?.slug ? `destination/${destRef.slug}` : undefined)
      );
    }
    if (fieldId === 'assets.hero' || fieldId === 'assets.itineraryDivider' || fieldId === 'assets.staysDivider' || fieldId === 'assets.hotelDivider') {
      const firstDay = facts?.trip_facts?.itinerary?.[0];
      const destRef = firstDay?.destination_ref;
      return destRef?.mediaPrefix || destRef?.defaultMediaPrefix || undefined;
    }
    return undefined;
  }, [activeMediaMatch, facts]);

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
              immutableFacts={immutableFacts}
              isEditingQuotation={isEditingQuotation}
              factsSourceKind={factsSourceKind}
              businessVersionNumber={businessVersionNumber}
              onRequestEditQuotation={onRequestEditQuotation}
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
            void saveMedia(activeMediaMatch.fieldId, withManualSource(r2Key));
          }}
          onConfirm={(r2Keys) => {
            void saveMedia(activeMediaMatch.fieldId, r2Keys.map((k) => withManualSource(k)));
          }}
          initialPrefix={activeInitialPrefix}
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
