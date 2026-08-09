'use client';

import { useState } from 'react';
import type { DisplayDocument } from '../../display/runtimePageBuilder';
import { quotationFetch, apiErrorMessage } from '../../lib/apiError';
import type { EditableBrochureContract } from './useQuotationWorkspace';
import BoundaryCanvas, { type InspectorDescriptor, type ResolvedInspectorSelection } from './BoundaryCanvas';
import ContextualInspector from './ContextualInspector';
import type { ResolvedHandoff } from './editableHandoff';

const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? '';

export default function DesignCanvas({ quotationId, lang, model, document, currentRevision, contract, onSaved, onHandoff }: {
  quotationId: string;
  lang: string;
  model: DisplayDocument;
  document: Record<string, unknown>;
  currentRevision: number;
  contract?: EditableBrochureContract;
  onSaved: () => Promise<unknown> | void;
  onHandoff: (target: ResolvedHandoff) => void;
}) {
  const [selected, setSelected] = useState<InspectorDescriptor | null>(null);
  const [resolvedHandoff, setResolvedHandoff] = useState<ResolvedHandoff | undefined>();
  const [renderedValue, setRenderedValue] = useState('');
  const save = async (descriptor: InspectorDescriptor, value: string) => {
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
    } catch (error) {
      throw new Error(apiErrorMessage(error));
    }
  };
  const select = (selection: ResolvedInspectorSelection, value: string) => {
    setSelected(selection.descriptor);
    setResolvedHandoff(selection.handoff);
    setRenderedValue(value);
  };
  return <section className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
    <BoundaryCanvas model={model} document={document} contract={contract} onResolve={select} onHover={() => undefined} />
    <ContextualInspector selected={selected} resolvedHandoff={resolvedHandoff} renderedValue={renderedValue} onSave={save} onHandoff={onHandoff} />
  </section>;
}
