'use client';

import dynamic from 'next/dynamic';
import type { TipTapRichEditorProps } from './TipTapRichEditorCore';

const TipTapRichEditorCore = dynamic(() => import('./TipTapRichEditorCore'), {
  ssr: false,
  loading: () => (
    <div className="min-h-24 w-full animate-pulse rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-3" />
  ),
});

export function RichTextEditor(props: TipTapRichEditorProps) {
  return <TipTapRichEditorCore {...props} />;
}

export default RichTextEditor;
