'use client';

import { useRef, useState } from 'react';
import type { DisplayDocument } from '../../display/runtimePageBuilder';
import { quotationFetch, apiErrorMessage } from '../../lib/apiError';
import type { EditableBrochureContract } from './useQuotationWorkspace';
import BoundaryCanvas, { type InspectorDescriptor, type ResolvedInspectorSelection } from './BoundaryCanvas';
import ContextualInspector from './ContextualInspector';
import type { ResolvedHandoff } from './editableHandoff';
import type { QuotationFacts } from './factsTypes';
import { useToast } from '../staff-workspace/ToastProvider';

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

const DESIGNER_FACT_FIELD_BY_DESCRIPTOR = {
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

export default function DesignCanvas({ quotationId, lang, model, document, currentRevision, canEditDesignerFacts, contract, facts, onSaved, onSaveDesignerFacts, onHandoff }: {
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
}) {
  const { toast, notify, clearScope } = useToast();
  const [selected, setSelected] = useState<InspectorDescriptor | null>(null);
  const [resolvedHandoff, setResolvedHandoff] = useState<ResolvedHandoff | undefined>();
  const [renderedValue, setRenderedValue] = useState('');
  const [selectedTop, setSelectedTop] = useState<number | null>(null);
  const sectionRef = useRef<HTMLElement>(null);
  const inspectorRef = useRef<HTMLDivElement>(null);

  const save = async (descriptor: InspectorDescriptor, value: string) => {
    const factField = DESIGNER_FACT_FIELD_BY_DESCRIPTOR[descriptor.fieldId as keyof typeof DESIGNER_FACT_FIELD_BY_DESCRIPTOR];
    if (descriptor.owner === 'fact' && descriptor.editorSurface === 'design-inspector' && factField) {
      if (!canEditDesignerFacts) throw new Error('Facts are read-only for this quotation source.');
      await onSaveDesignerFacts({ [factField]: value });
      return;
    }
    if (descriptor.owner !== 'design' || descriptor.inspectorControl === 'none') throw new Error('This field is not editable from Design.');
    const identityKey = descriptor.source?.match(/^\/presentation\/identityOverrides\/([^/]+)$/)?.[1];
    try {
      await quotationFetch(`${API_BASE}/api/v2/quotations/${quotationId}/presentation/overrides?lang=${encodeURIComponent(lang)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseRevision: currentRevision,
          copyOverrides: identityKey ? {} : { [descriptor.fieldId]: value },
          identityOverrides: identityKey ? { [identityKey]: value } : {},
        }),
      }, 'Design override could not be saved.');
      await onSaved();
      clearScope('design:override');
      toast('Design override saved.', 'success');
    } catch (error) {
      const message = apiErrorMessage(error);
      notify({ message, type: 'error', persistent: true, scope: 'design:override', action: { label: 'Reload', onClick: () => window.location.reload() } });
      throw new Error(message);
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

  return <section ref={sectionRef} className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
    <BoundaryCanvas model={model} document={document} contract={contract} onResolve={select} onHover={() => undefined} />
    <div
      className="relative"
      style={{ '--inspector-offset': `${offset}px` } as React.CSSProperties}
    >
      <div
        ref={inspectorRef}
        className="transition-transform duration-200 ease-out xl:[transform:translateY(var(--inspector-offset,0px))]"
      >
        <ContextualInspector selected={selected} resolvedHandoff={resolvedHandoff} renderedValue={renderedValue} onSave={save} onHandoff={onHandoff} canEditFactInspector={canEditDesignerFacts} facts={facts} onSaveFactFields={onSaveDesignerFacts} />
      </div>
    </div>
  </section>;
}
