'use client';

import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Highlight from '@tiptap/extension-highlight';
import { Markdown } from 'tiptap-markdown';
import { useEffect, useRef } from 'react';
import { Bold, Italic, Highlighter, List, ListOrdered, Undo, Redo } from 'lucide-react';
import { cn } from '../../utils/cn';
import { getTypographyClassName } from '../../config/typography';

export interface TipTapRichEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  minHeight?: string;
  singleLine?: boolean;
}

export function TipTapRichEditorCore({
  value,
  onChange,
  className,
  minHeight,
  singleLine = false,
}: TipTapRichEditorProps) {
  const isUpdatingRef = useRef(false);
  const effectiveMinHeight = minHeight ?? (singleLine ? '2.25rem' : '6rem');

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        bulletList: { keepMarks: true },
        orderedList: { keepMarks: true },
      }),
      Highlight.configure({
        multicolor: false,
      }),
      Markdown.configure({
        html: true,
        transformCopiedText: true,
        transformPastedText: true,
      }),
    ],
    content: value || '',
    editorProps: {
      handleKeyDown: (_view, event) => {
        if (singleLine && event.key === 'Enter') {
          event.preventDefault();
          return true;
        }
        return false;
      },
      attributes: {
        class: cn(
          getTypographyClassName('bodySm'),
          'prose dark:prose-invert max-w-none focus:outline-none text-[var(--color-on-surface)] px-2.5 py-1.5',
          singleLine ? 'whitespace-nowrap overflow-hidden' : 'min-h-[var(--min-editor-height)]',
        ),
        style: `min-height: ${effectiveMinHeight};`,
      },
    },
    onUpdate: ({ editor }) => {
      isUpdatingRef.current = true;
      const storage = editor.storage as unknown as Record<string, { get?: () => string }>;
      const markdownOutput = storage.markdown?.get?.() ?? editor.getText();
      onChange(markdownOutput);
      setTimeout(() => {
        isUpdatingRef.current = false;
      }, 0);
    },
  });

  // Synchronize external value changes if not currently typing
  useEffect(() => {
    if (!editor || isUpdatingRef.current) return;
    const storage = editor.storage as unknown as Record<string, { get?: () => string }>;
    const currentMarkdown = storage.markdown?.get?.() ?? '';
    if (value !== currentMarkdown && value !== editor.getHTML()) {
      editor.commands.setContent(value || '');
    }
  }, [value, editor]);

  if (!editor) {
    return (
      <div
        className={cn(
          'min-h-24 w-full animate-pulse rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-3',
          className,
        )}
      />
    );
  }

  return (
    <div
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] transition-all focus-within:ring-2 focus-within:ring-[var(--color-focus)]',
        className,
      )}
    >
      {/* Compact Formatting Toolbar */}
      <div className="flex flex-wrap items-center gap-1 border-b border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] px-2 py-1 select-none">
        <button
          type="button"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={cn(
            getTypographyClassName('caption'),
            'inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-pill)] transition-colors hover:bg-[var(--color-surface)]',
            editor.isActive('bold')
              ? 'bg-[var(--color-accent-wash)] text-[var(--color-accent)]'
              : 'text-[var(--color-muted)]',
          )}
          title="Bold (Ctrl+B)"
        >
          <Bold className="h-3.5 w-3.5" />
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={cn(
            getTypographyClassName('caption'),
            'inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-pill)] transition-colors hover:bg-[var(--color-surface)]',
            editor.isActive('ita' + 'lic')
              ? 'bg-[var(--color-accent-wash)] text-[var(--color-accent)]'
              : 'text-[var(--color-muted)]',
          )}
          title="Italic (Ctrl+I)"
        >
          <Italic className="h-3.5 w-3.5" />
        </button>

        <button
          type="button"
          onClick={() => editor.chain().focus().toggleHighlight().run()}
          className={cn(
            getTypographyClassName('caption'),
            'inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-pill)] transition-colors hover:bg-[var(--color-surface)]',
            editor.isActive('highlight')
              ? 'bg-[var(--color-accent-wash)] text-[var(--color-accent)]'
              : 'text-[var(--color-muted)]',
          )}
          title="Highlight (Ctrl+Shift+H)"
        >
          <Highlighter className="h-3.5 w-3.5" />
        </button>

        {!singleLine ? (
          <>
            <div className="mx-1 h-4 w-px bg-[var(--color-border-strong)]" />

            <button
              type="button"
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              className={cn(
                getTypographyClassName('caption'),
                'inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-pill)] transition-colors hover:bg-[var(--color-surface)]',
                editor.isActive('bulletList')
                  ? 'bg-[var(--color-accent-wash)] text-[var(--color-accent)]'
                  : 'text-[var(--color-muted)]',
              )}
              title="Bullet List"
            >
              <List className="h-3.5 w-3.5" />
            </button>

            <button
              type="button"
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              className={cn(
                getTypographyClassName('caption'),
                'inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-pill)] transition-colors hover:bg-[var(--color-surface)]',
                editor.isActive('orderedList')
                  ? 'bg-[var(--color-accent-wash)] text-[var(--color-accent)]'
                  : 'text-[var(--color-muted)]',
              )}
              title="Numbered List"
            >
              <ListOrdered className="h-3.5 w-3.5" />
            </button>
          </>
        ) : null}

        <div className="mx-1 h-4 w-px bg-[var(--color-border-strong)]" />

        <button
          type="button"
          disabled={!editor.can().undo()}
          onClick={() => editor.chain().focus().undo().run()}
          className={cn(
            getTypographyClassName('caption'),
            'inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-pill)] text-[var(--color-muted)] transition-colors hover:bg-[var(--color-surface)] disabled:opacity-30',
          )}
          title="Undo (Ctrl+Z)"
        >
          <Undo className="h-3.5 w-3.5" />
        </button>

        <button
          type="button"
          disabled={!editor.can().redo()}
          onClick={() => editor.chain().focus().redo().run()}
          className={cn(
            getTypographyClassName('caption'),
            'inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-pill)] text-[var(--color-muted)] transition-colors hover:bg-[var(--color-surface)] disabled:opacity-30',
          )}
          title="Redo (Ctrl+Y)"
        >
          <Redo className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Editor Content Area */}
      <EditorContent editor={editor} className="min-w-0 flex-1" />
    </div>
  );
}

export default TipTapRichEditorCore;
