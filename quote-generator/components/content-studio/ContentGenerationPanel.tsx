'use client';

import { useMemo, useState } from 'react';
import { cn } from '../../utils/cn.ts';
import { getTypographyClassName } from '../../config/typography.ts';
import type { ContentFactInput, PromptPreview } from '../quotation-workspace/useQuotationWorkspace.ts';
import { RichTextEditor } from '../ui/RichTextEditor.tsx';
import { PromptOptionPillSelector, GROUND_RULE_OPTIONS, BRAND_OPTIONS } from './PromptOptionPillSelector.tsx';
import { RealtimePromptPreviewPanel } from './RealtimePromptPreviewPanel.tsx';

type Mode = 'storytelling' | 'detailed';

function readFact(value: Record<string, unknown> | undefined, path: Array<string | number>): unknown {
  let current: unknown = value;
  for (const part of path) {
    current = current && typeof current === 'object' ? (current as Record<string | number, unknown>)[part] : undefined;
  }
  return current;
}

function factKeyLabel(key: string): string {
  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/^./, (char) => char.toUpperCase());
}

function FactValue({ value, nested = false }: { value: unknown; nested?: boolean }) {
  if (value === undefined || value === null || value === '') {
    return <span className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>Not provided</span>;
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return <span className={cn(getTypographyClassName('bodySm'), 'break-words text-[var(--color-on-surface)]')}>{String(value)}</span>;
  }
  if (Array.isArray(value)) {
    if (!value.length) return <span className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>Not provided</span>;
    if (value.every((item) => typeof item === 'string' || typeof item === 'number')) {
      return (
        <ul className="grid min-w-0 gap-1.5">
          {value.map((item, index) => (
            <li key={`${String(item)}-${index}`} className={cn(getTypographyClassName('bodySm'), 'break-words text-[var(--color-on-surface)]')}>
              {String(item)}
            </li>
          ))}
        </ul>
      );
    }
    return (
      <div className="grid min-w-0 gap-2">
        {value.map((item, index) => (
          <div key={index} className="min-w-0 rounded-[var(--radius-button)] bg-[var(--color-surface-muted)] p-2">
            <FactValue value={item} nested />
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === 'object') {
    return (
      <dl className={cn('grid min-w-0 gap-1.5', nested && 'gap-2')}>
        {Object.entries(value as Record<string, unknown>).map(([key, item]) => (
          <div key={key} className="grid min-w-0 gap-0.5">
            <dt className={cn(getTypographyClassName('caption'), 'text-[var(--color-muted)]')}>{factKeyLabel(key)}</dt>
            <dd className="min-w-0">
              <FactValue value={item} nested />
            </dd>
          </div>
        ))}
      </dl>
    );
  }
  return <span className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>Not provided</span>;
}

export function ContentGenerationPanel({
  scope = '',
  mode,
  onModeChange,
  instruction,
  defaultInstruction,
  onInstructionChange,
  onRestoreDefault,
  factInputs,
  facts,
  onGenerate,
  pending,
  disabled,
  promptPreview,
  draftSystemPrompt,
  draftUserPrompt,
  onRequestPreview,
}: {
  scope?: string;
  mode: Mode;
  onModeChange: (mode: Mode) => void;
  instruction: string;
  defaultInstruction: string;
  onInstructionChange: (value: string) => void;
  onRestoreDefault: () => void;
  factInputs: ContentFactInput[];
  facts?: Record<string, unknown>;
  onGenerate: () => void;
  pending: boolean;
  disabled: boolean;
  promptPreview?: PromptPreview;
  draftSystemPrompt?: string;
  draftUserPrompt?: string;
  onRequestPreview?: () => void;
}) {
  const usingDefault = instruction === defaultInstruction;

  // Infer default brand from facts (quote.brand_id)
  const defaultBrandId = typeof facts?.brand_id === 'string' && facts.brand_id ? facts.brand_id : 'capella_travel';
  const [selectedBrandId, setSelectedBrandId] = useState<string>(defaultBrandId);

  // Initialize ground rules for current scope
  const initialRuleIds = useMemo(() => {
    return GROUND_RULE_OPTIONS.filter((r) => scope.startsWith('itinerary:day:') || r.id === 'GR-7030').map((r) => r.id);
  }, [scope]);

  const [selectedRuleIds, setSelectedRuleIds] = useState<string[]>(initialRuleIds);
  const [selectedConstraintIds, setSelectedConstraintIds] = useState<string[]>(['schema_validation', 'no_price_hallucination', 'brand_safety']);

  const [disabledFactIds, setDisabledFactIds] = useState<string[]>([]);

  const toggleRule = (ruleId: string) => {
    setSelectedRuleIds((prev) => (prev.includes(ruleId) ? prev.filter((id) => id !== ruleId) : [...prev, ruleId]));
  };

  const toggleConstraint = (constraintId: string) => {
    setSelectedConstraintIds((prev) => (prev.includes(constraintId) ? prev.filter((id) => id !== constraintId) : [...prev, constraintId]));
  };

  const toggleFact = (factId: string) => {
    setDisabledFactIds((prev) => (prev.includes(factId) ? prev.filter((id) => id !== factId) : [...prev, factId]));
  };

  // Filter facts payload based on active fact pills
  const activeFactsSnapshot = useMemo(() => {
    if (!facts) return {};
    const clone: Record<string, unknown> = { ...facts };
    if (disabledFactIds.length) {
      for (const disabledId of disabledFactIds) {
        const targetInput = factInputs.find((i) => i.id === disabledId);
        if (targetInput && targetInput.path.length > 0) {
          const topKey = targetInput.path[0];
          delete clone[topKey];
        }
      }
    }
    const sanitize = (val: unknown): unknown => {
      if (val === null || val === undefined || val === '') return undefined;
      if (Array.isArray(val)) {
        const cleaned = val.map(sanitize).filter((item) => item !== undefined);
        return cleaned.length ? cleaned : undefined;
      }
      if (typeof val === 'object') {
        const res: Record<string, unknown> = {};
        for (const [k, v] of Object.entries(val as Record<string, unknown>)) {
          const cleanedV = sanitize(v);
          if (cleanedV !== undefined) {
            res[k] = cleanedV;
          }
        }
        return Object.keys(res).length ? res : undefined;
      }
      return val;
    };

    return (sanitize(clone) as Record<string, unknown>) || {};
  }, [facts, disabledFactIds, factInputs]);

  // Compile real-time System Prompt preview based on selected pills
  const compiledSystemPrompt = useMemo(() => {
    if (promptPreview?.systemPrompt) return promptPreview.systemPrompt;
    if (draftSystemPrompt) return draftSystemPrompt;

    const brandObj = BRAND_OPTIONS.find((b) => b.id === selectedBrandId) || BRAND_OPTIONS[0];
    const activeRules = GROUND_RULE_OPTIONS.filter((r) => selectedRuleIds.includes(r.id));
    const activeConstraints = selectedConstraintIds;

    const parts = [
      'Role: senior luxury travel copywriter.',
      `Brand: ${brandObj.label}. Tone: luxury editorial`,
      'Preferred vocabulary: bespoke, luxury, sanctuary. Avoid: cheap, basic.',
      'Goal: return brochure-ready plain-text fields',
      `- Brand Voice Guidelines:\n  • ${brandObj.detailText}`,
      `- Writing Mode Rules:\n  • Mode: ${mode === 'storytelling' ? 'Storytelling (evocative, sensory cadence)' : 'Detailed (restrained, precise logistics)'}`,
    ];

    if (activeRules.length) {
      parts.push('- Ground Rules:\n  ' + activeRules.map((r) => `• [${r.id}] ${r.label}: ${r.detailText}`).join('\n  '));
    }

    if (activeConstraints.length) {
      parts.push(`Constraints: Schema validation required. No price hallucination. Brand safety active.`);
    }

    parts.push('Validation: satisfy the structured output schema exactly.');
    return parts.join('\n');
  }, [promptPreview, draftSystemPrompt, selectedBrandId, selectedRuleIds, selectedConstraintIds, mode]);

  // Compile real-time User Prompt preview
  const compiledUserPrompt = useMemo(() => {
    if (promptPreview?.userPrompt) return promptPreview.userPrompt;
    if (draftUserPrompt) return draftUserPrompt;
    return `Scope: ${scope}\nWriting instruction: ${instruction}\n\nInput Facts (JSON):\n${JSON.stringify(activeFactsSnapshot, null, 2)}`;
  }, [promptPreview, draftUserPrompt, scope, instruction, activeFactsSnapshot]);

  return (
    <aside className="grid h-fit min-w-0 max-w-full gap-4 overflow-hidden rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 xl:sticky xl:top-4">
      <div className="min-w-0">
        <h3 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>AI Assistant Studio</h3>
        <p className={cn(getTypographyClassName('bodySm'), 'mt-1 break-words text-[var(--color-muted)]')}>
          Configure prompt options using badge pills. Generate a validated draft into editable fields.
        </p>
      </div>

      {/* Modular Tag-Pill Option Selector */}
      <PromptOptionPillSelector
        defaultBrandId={defaultBrandId}
        selectedBrandId={selectedBrandId}
        onBrandChange={setSelectedBrandId}
        selectedMode={mode}
        onModeChange={(m) => onModeChange(m as Mode)}
        selectedRuleIds={selectedRuleIds}
        onToggleRule={toggleRule}
        selectedConstraintIds={selectedConstraintIds}
        onToggleConstraint={toggleConstraint}
        factInputs={factInputs}
        facts={facts}
        disabledFactIds={disabledFactIds}
        onToggleFact={toggleFact}
        disabled={disabled}
      />

      {/* Generation Brief Editor */}
      <label className="grid min-w-0 gap-1.5">
        <span className={cn(getTypographyClassName('label'), 'break-words text-[var(--color-muted)]')}>
          Generation Brief {usingDefault ? '· default' : '· custom'}
        </span>
        <RichTextEditor value={instruction} minHeight="6rem" onChange={onInstructionChange} />
      </label>

      <div className="flex items-center justify-between gap-2">
        <p className={cn(getTypographyClassName('caption'), 'break-words text-[var(--color-muted)]')}>
          Brief modifies tone & style. Verified facts & response schema remain fixed.
        </p>
        <button
          type="button"
          onClick={onRestoreDefault}
          disabled={usingDefault}
          className={cn(
            getTypographyClassName('buttonSecondary'),
            'min-h-9 w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-3 py-1.5 disabled:opacity-50 cursor-pointer'
          )}
        >
          Restore default
        </button>
      </div>

      {/* Real-time Prompt Inspector Panel */}
      <RealtimePromptPreviewPanel
        promptPreview={promptPreview}
        systemPrompt={compiledSystemPrompt}
        userPrompt={compiledUserPrompt}
        factsSnapshot={activeFactsSnapshot}
        onRequestPreview={onRequestPreview}
      />

      {/* Generate Action Button */}
      <button
        type="button"
        disabled={pending || disabled}
        onClick={onGenerate}
        className={cn(
          getTypographyClassName('buttonPrimary'),
          'min-h-11 w-full rounded-[var(--radius-button)] bg-[var(--color-action-primary-surface)] px-4 py-2.5 text-[var(--color-action-primary-text)] shadow-xs transition-all hover:opacity-90 disabled:opacity-50 cursor-pointer lg:min-h-10'
        )}
      >
        {pending ? 'Generating draft…' : 'Generate draft with selected options'}
      </button>
    </aside>
  );
}

export function FactsUsed({ factInputs, facts }: { factInputs: ContentFactInput[]; facts?: Record<string, unknown> }) {
  return (
    <div className="grid min-w-0 max-w-full gap-2">
      <p className={cn(getTypographyClassName('label'), 'text-[var(--color-muted)]')}>FACTS USED IN PROMPT</p>
      {factInputs.map((input) => {
        const value = readFact(facts, input.path);
        const nights = input.id === 'duration' ? readFact(facts, ['trip_facts', 'duration_nights']) : undefined;
        const formattedDuration = typeof value === 'number' && typeof nights === 'number' ? `${value} days / ${nights} nights` : value;
        return (
          <div key={input.id} className="min-w-0 overflow-hidden rounded-[var(--radius-button)] border border-[var(--color-border)] p-3 bg-[var(--color-surface-muted)]">
            <p className={cn(getTypographyClassName('label'), 'break-words text-[var(--color-muted)]')}>
              {input.label}
              {input.required ? ' · required' : ''}
            </p>
            <div className="mt-1 min-w-0">
              <FactValue value={formattedDuration} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
