'use client';

import { useState } from 'react';
import { getTypographyClassName } from '../../config/typography';
import { cn } from '../../utils/cn';
import { Copy, Check, Eye, EyeOff } from 'lucide-react';
import type { PromptPreview } from '../quotation-workspace/useQuotationWorkspace';

type Props = {
  promptPreview?: PromptPreview;
  systemPrompt?: string;
  userPrompt?: string;
  factsSnapshot?: Record<string, unknown>;
  onRequestPreview?: () => void;
};

export function RealtimePromptPreviewPanel({
  promptPreview,
  systemPrompt,
  userPrompt,
  factsSnapshot,
  onRequestPreview,
}: Props) {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'system' | 'user' | 'json'>('system');
  const [copied, setCopied] = useState(false);

  const activeSystem = promptPreview?.systemPrompt || systemPrompt || 'System prompt loading or unavailable.';
  const activeUser = promptPreview?.userPrompt || userPrompt || 'User prompt loading or unavailable.';
  const jsonFacts = promptPreview?.factsSnapshot
    ? JSON.stringify(promptPreview.factsSnapshot, null, 2)
    : factsSnapshot
    ? JSON.stringify(factsSnapshot, null, 2)
    : '{}';

  const handleToggle = () => {
    const next = !open;
    setOpen(next);
    if (next && onRequestPreview) {
      onRequestPreview();
    }
  };

  const handleCopy = () => {
    const fullText = `=== SYSTEM PROMPT ===\n${activeSystem}\n\n=== USER PROMPT ===\n${activeUser}`;
    void navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Approximate token estimator (4 chars per token)
  const estSystemTokens = Math.round(activeSystem.length / 4);
  const estUserTokens = Math.round(activeUser.length / 4);

  return (
    <div className="grid min-w-0 gap-2 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-3 shadow-2xs">
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={handleToggle}
          className={cn(
            getTypographyClassName('label'),
            'flex items-center gap-1.5 text-[var(--color-on-surface)] hover:text-[var(--color-accent)] cursor-pointer'
          )}
        >
          {open ? <EyeOff className="w-3.5 h-3.5 text-[var(--color-accent)]" /> : <Eye className="w-3.5 h-3.5 text-[var(--color-accent)]" />}
          <span>{open ? 'Hide Realtime Prompt Inspector' : '▶ Inspect Realtime Prompt & Rules (v1)'}</span>
        </button>

        {open ? (
          <div className="flex items-center gap-2">
            <span className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)] font-mono')}>
              ~{estSystemTokens + estUserTokens} tokens
            </span>
            <button
              type="button"
              onClick={handleCopy}
              className={cn(
                getTypographyClassName('caption'),
                'flex items-center gap-1 rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1 text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:border-[var(--color-accent)] cursor-pointer transition-all'
              )}
            >
              {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3 text-[var(--color-accent)]" />}
              <span>{copied ? 'Copied!' : 'Copy Prompt'}</span>
            </button>
          </div>
        ) : null}
      </div>

      {open ? (
        <div className="mt-2 grid gap-2">
          <div className="flex flex-wrap gap-1 border-b border-[var(--color-border)] pb-1">
            <button
              type="button"
              onClick={() => setActiveTab('system')}
              className={cn(
                getTypographyClassName('caption'),
                'rounded px-2.5 py-1 cursor-pointer transition-all',
                activeTab === 'system'
                  ? 'bg-[var(--color-accent)] text-white shadow-2xs'
                  : 'text-[var(--color-muted)] hover:text-[var(--color-on-surface)]'
              )}
            >
              System Prompt ({estSystemTokens} tokens)
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('user')}
              className={cn(
                getTypographyClassName('caption'),
                'rounded px-2.5 py-1 cursor-pointer transition-all',
                activeTab === 'user'
                  ? 'bg-[var(--color-accent)] text-white shadow-2xs'
                  : 'text-[var(--color-muted)] hover:text-[var(--color-on-surface)]'
              )}
            >
              User Prompt ({estUserTokens} tokens)
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('json')}
              className={cn(
                getTypographyClassName('caption'),
                'rounded px-2.5 py-1 cursor-pointer transition-all',
                activeTab === 'json'
                  ? 'bg-[var(--color-accent)] text-white shadow-2xs'
                  : 'text-[var(--color-muted)] hover:text-[var(--color-on-surface)]'
              )}
            >
              JSON Facts Injected
            </button>
          </div>

          <div
            className={cn(
              getTypographyClassName('caption'),
              'max-h-64 overflow-y-auto rounded-[var(--radius-button)] bg-[var(--color-surface)] p-3 font-mono text-[var(--color-on-surface)] whitespace-pre-wrap border border-[var(--color-border)]'
            )}
          >
            {activeTab === 'system' && activeSystem}
            {activeTab === 'user' && activeUser}
            {activeTab === 'json' && jsonFacts}
          </div>
        </div>
      ) : null}
    </div>
  );
}
