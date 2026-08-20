'use client';

import { useEffect, useMemo, useRef } from 'react';
import DisplayPage from '../DisplayPage.tsx';
import type { DisplayDocument } from '../../display/runtimePageBuilder.ts';
import type { EditableBrochureContract } from './useQuotationWorkspace.ts';
import {
  resolveEditableHandoff,
  resolveInspectorDescriptor,
  type InspectorDescriptor,
  type ResolvedHandoff,
} from './editableHandoff.ts';

export type { InspectorDescriptor } from './editableHandoff.ts';
export type ResolvedInspectorSelection = {
  descriptor: InspectorDescriptor;
  source: string;
  handoff?: ResolvedHandoff;
  elementTop?: number;
};

function renderedValue(element: HTMLElement) {
  const editorValue = element.getAttribute('data-workspace-editor-value');
  if (editorValue !== null) return editorValue;
  const aria = element.getAttribute('aria-label');
  return (aria || element.textContent || '').trim();
}

export default function BoundaryCanvas({
  model,
  document,
  contract,
  onResolve,
  onHover,
}: {
  model: DisplayDocument;
  document: Record<string, unknown>;
  contract?: EditableBrochureContract;
  onResolve: (selection: ResolvedInspectorSelection, value: string) => void;
  onHover: (descriptor: InspectorDescriptor | null) => void;
}) {
  const root = useRef<HTMLDivElement>(null);
  const fields = useMemo(() => contract?.fields ?? [], [contract]);
  const resolve = (element: HTMLElement | null) => {
    const source = element?.dataset.editable;
    if (!element || !source) return null;
    const matched = resolveInspectorDescriptor(fields, source);
    if (!matched) return null;
    return {
      descriptor: matched.descriptor,
      source,
      handoff: resolveEditableHandoff(matched.descriptor, source, document),
    };
  };
  const clear = (attribute: 'data-workspace-hovered' | 'data-workspace-selected') =>
    root.current?.querySelectorAll(`[${attribute}="true"]`).forEach((node) => node.removeAttribute(attribute));
  const select = (element: HTMLElement | null) => {
    const selection = resolve(element);
    if (!selection || !element) return false;
    clear('data-workspace-selected');
    element.dataset.workspaceSelected = 'true';
    const canvasTop = root.current?.getBoundingClientRect().top ?? 0;
    const elemTop = element.getBoundingClientRect().top;
    const relativeTop = Math.max(0, elemTop - canvasTop);
    onResolve({ ...selection, elementTop: relativeTop }, renderedValue(element));
    return true;
  };

  useEffect(() => {
    const canvas = root.current;
    if (!canvas) return;
    const annotate = () => canvas.querySelectorAll<HTMLElement>('[data-editable]').forEach((element) => {
      if (resolve(element)) {
        element.dataset.workspaceTarget = 'true';
        if (element.tabIndex < 0) element.tabIndex = 0;
      }
    });
    annotate();
    const observer = new MutationObserver(annotate);
    observer.observe(canvas, { childList: true, subtree: true });
    return () => observer.disconnect();
  // Contract changes must re-annotate the canonical DisplayPage DOM.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fields, document]);

  const targetFor = (target: EventTarget | null) => target instanceof HTMLElement ? target.closest<HTMLElement>('[data-editable]') : null;
  return (
    <div
      ref={root}
      className="workspace-boundary-canvas overflow-hidden rounded-[var(--radius-card)] border border-[var(--color-border)] focus-within:ring-2 focus-within:ring-[var(--color-focus)] [&_[data-workspace-hovered=true]]:outline [&_[data-workspace-hovered=true]]:outline-1 [&_[data-workspace-hovered=true]]:outline-offset-2 [&_[data-workspace-hovered=true]]:outline-[var(--color-accent)] [&_[data-workspace-selected=true]]:outline [&_[data-workspace-selected=true]]:outline-2 [&_[data-workspace-selected=true]]:outline-offset-2 [&_[data-workspace-selected=true]]:outline-[var(--color-focus)]"
      onPointerMoveCapture={(event) => {
        const element = targetFor(event.target); const selection = resolve(element);
        clear('data-workspace-hovered');
        if (selection && element) element.dataset.workspaceHovered = 'true';
        onHover(selection?.descriptor ?? null);
      }}
      onPointerLeave={() => { clear('data-workspace-hovered'); onHover(null); }}
      onFocusCapture={(event) => { const element = targetFor(event.target); if (element) select(element); }}
      onClickCapture={(event) => { if (select(targetFor(event.target))) { event.preventDefault(); event.stopPropagation(); } }}
      onKeyDownCapture={(event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        if (select(targetFor(event.target))) { event.preventDefault(); event.stopPropagation(); }
      }}
    >
      <DisplayPage documentModel={model} workspaceCanvas />
    </div>
  );
}
