'use client';

import { useMemo } from 'react';
import { CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import SectionOutlineNav from '../ui/SectionOutlineNav.tsx';
import { getTypographyClassName } from '../../config/typography.ts';
import { cn } from '../../utils/cn.ts';
import { ContentDraftActions } from './ContentDraftActions.tsx';
import { ContentGenerationPanel, FactsUsed } from './ContentGenerationPanel.tsx';
import { SectionContentFields } from './SectionContentFields.tsx';
import type {
  ContentFactInput,
  DocumentResponse,
  DraftsResponse,
  FactsResponse,
  ReviewResponse,
} from '../quotation-workspace/useQuotationWorkspace.ts';
import {
  useContentStudioState,
  labels,
  SCOPE_BY_SECTION_TYPE,
} from './useContentStudioState.ts';
import { useContentGeneration } from './useContentGeneration.ts';

type Props = {
  quotationId: string;
  lang: string;
  onEditFacts?: (section?: string) => void;
  onProceedToDesign?: () => void;
  resources: {
    documentData?: DocumentResponse;
    draftsData?: DraftsResponse;
    factsData?: FactsResponse;
    reviewData?: ReviewResponse;
    refresh: () => Promise<unknown>;
    request: <T>(path: string, init?: RequestInit, fallback?: string) => Promise<T>;
  };
};

function FactOwnedNotice() {
  return (
    <div className="rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4">
      <p className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}>
        This section is derived directly from approved Facts and cannot be edited manually.
      </p>
    </div>
  );
}

function FactsIncompleteBanner({ onEditFacts }: { onEditFacts: () => void }) {
  return (
    <div
      role="alert"
      className="mb-4 grid gap-2 rounded-[var(--radius-card)] border border-amber-500/30 bg-amber-500/10 p-4"
    >
      <p className={cn(getTypographyClassName('bodySm'), 'text-amber-800')}>
        Required Facts are missing for this section. Please update Facts to proceed.
      </p>
      <button
        type="button"
        onClick={onEditFacts}
        className={cn(
          getTypographyClassName('buttonSecondary'),
          'min-h-9 w-fit rounded-[var(--radius-button)] border border-amber-500/30 px-3 py-1 text-amber-900 cursor-pointer'
        )}
      >
        Edit Facts
      </button>
    </div>
  );
}

function ContentContractUnavailable({ onRetry }: { onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="grid gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4"
    >
      <div>
        <h3 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>
          Content workspace is unavailable
        </h3>
        <p className={cn(getTypographyClassName('bodySm'), 'mt-1 text-[var(--color-muted)]')}>
          The document response is missing the Content editor contract. Fields cannot be safely guessed because the registry is their source of truth.
        </p>
      </div>
      <button
        type="button"
        onClick={onRetry}
        className={cn(
          getTypographyClassName('buttonSecondary'),
          'min-h-11 w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2 cursor-pointer'
        )}
      >
        Retry loading workspace
      </button>
    </div>
  );
}

function DeterministicFactsPanel({
  factInputs,
  facts,
}: {
  factInputs: ContentFactInput[];
  facts?: Record<string, unknown>;
}) {
  return (
    <aside className="grid h-fit gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-4 xl:sticky xl:top-4">
      <div>
        <h3 className={cn(getTypographyClassName('cardTitle'), 'text-[var(--color-on-surface)]')}>
          Approved checklist
        </h3>
        <p className={cn(getTypographyClassName('bodySm'), 'mt-1 text-[var(--color-muted)]')}>
          This section is derived deterministically from approved Facts. It does not use AI generation.
        </p>
      </div>
      <FactsUsed factInputs={factInputs} facts={facts} />
    </aside>
  );
}

export default function ContentStudioClient({
  quotationId,
  lang,
  onEditFacts,
  onProceedToDesign,
  resources,
}: Props) {
  const {
    mode,
    setMode,
    readiness,
    selected,
    scope,
    editor,
    factOwned,
    draft,
    workingCandidate,
    setWorkingCandidate,
    setGeneratedDraft,
    setLocalCandidate,
    instruction,
    activeCustomInstruction,
    setCustomInstruction,
    select,
    complete,
    factsForPanel,
  } = useContentStudioState({
    quotationId,
    lang,
    resources,
  });

  const {
    pending,
    message,
    promptPreview,
    handleRequestPromptPreview,
    batchState,
    generate,
    handleBatchGenerateAll,
    saveDraft,
    apply,
    applyAll,
    discard,
    handleProceedToDesign,
  } = useContentGeneration({
    quotationId,
    lang,
    scope,
    mode,
    activeCustomInstruction,
    editor,
    draft,
    workingCandidate,
    readiness,
    resources,
    setGeneratedDraft,
    setWorkingCandidate,
    setLocalCandidate,
    onProceedToDesign,
  });

  const pendingDraftsCount = (resources.draftsData?.drafts ?? []).filter(
    (d) => d.status === 'draft' || d.status === 'stale'
  ).length;

  const outlineItems = useMemo(
    () =>
      readiness.map((item) => {
        const isSelected = selected?.sectionId === item.sectionId;
        const labelText = item.sectionId.startsWith('itinerary:day:')
          ? item.label
          : labels[item.sectionType] ?? item.label;
        const itemScope = item.sectionId.startsWith('itinerary:day:')
          ? item.sectionId
          : SCOPE_BY_SECTION_TYPE[item.sectionType] ?? item.sectionType;
        const hasUnreviewedDraft = Boolean(
          (resources.draftsData?.drafts ?? []).find(
            (d) => d.scope === itemScope && (d.status === 'draft' || d.status === 'stale')
          )
        );
        const isCurrentlyGenerating =
          batchState.isRunning &&
          (batchState.generatingScope === itemScope || batchState.generatingScope === 'all');

        return {
          id: item.sectionId,
          label: labelText,
          isSelected,
          isGenerating: isCurrentlyGenerating,
          status: item.status,
          badge: isCurrentlyGenerating
            ? { text: 'Generating…', variant: 'generating' as const }
            : hasUnreviewedDraft
            ? { text: 'Draft', variant: 'draft' as const }
            : undefined,
        };
      }),
    [
      readiness,
      selected?.sectionId,
      resources.draftsData?.drafts,
      batchState.isRunning,
      batchState.generatingScope,
    ]
  );

  const batchHeaderAction = (
    <div className="flex flex-col gap-2 w-full">
      <button
        type="button"
        onClick={handleBatchGenerateAll}
        disabled={batchState.isRunning || pending}
        className={cn(
          getTypographyClassName('buttonPrimary'),
          'min-h-10 w-full rounded-[var(--radius-button)] bg-[color-mix(in_srgb,var(--color-accent)_90%,black)] hover:bg-[var(--color-accent)] !text-white px-3 py-2 flex items-center justify-center gap-2 shadow-xs transition-all disabled:opacity-50 cursor-pointer'
        )}
      >
        {batchState.isRunning ? (
          <>
            <Loader2 size={15} className="animate-spin text-white shrink-0" />
            <span>Generating drafts…</span>
          </>
        ) : (
          <>
            <Sparkles size={15} className="text-amber-200 shrink-0" />
            <span>Generate all sections</span>
          </>
        )}
      </button>

      {pendingDraftsCount > 0 ? (
        <button
          type="button"
          onClick={applyAll}
          disabled={pending || batchState.isRunning}
          className={cn(
            getTypographyClassName('buttonSecondary'),
            'min-h-9 w-full rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] hover:bg-[var(--color-accent-wash)] text-[var(--color-on-surface)] px-3 py-1.5 flex items-center justify-center gap-1.5 shadow-2xs transition-all disabled:opacity-50 cursor-pointer'
          )}
        >
          <CheckCircle2 size={14} className="text-[var(--color-accent)] shrink-0" />
          <span>Apply all ({pendingDraftsCount}) to brochure</span>
        </button>
      ) : null}
    </div>
  );

  const outlineFooter = onProceedToDesign ? (
    <button
      type="button"
      onClick={handleProceedToDesign}
      disabled={pending || batchState.isRunning}
      className={cn(
        getTypographyClassName('buttonPrimary'),
        'min-h-11 w-full rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-4 shadow-md transition-all disabled:opacity-50 cursor-pointer'
      )}
    >
      {pending
        ? 'Applying content…'
        : pendingDraftsCount > 0 || workingCandidate
        ? `Apply (${pendingDraftsCount || 1}) & proceed to Design`
        : 'Proceed to Design'}
    </button>
  ) : undefined;

  const defaultInstruction = editor?.defaultInstructions?.[mode] ?? '';

  return (
    <section className="grid min-w-0 gap-5 lg:grid-cols-[17rem_minmax(0,1fr)]">
      <SectionOutlineNav
        title="CONTENT STUDIO"
        completedCount={complete}
        totalCount={readiness.length}
        counterLabel="ready"
        items={outlineItems}
        onSelect={select}
        ariaLabel="Content sections"
        headerAction={batchHeaderAction}
        batchProgress={
          batchState.isRunning
            ? {
                current: batchState.completedCount,
                total: batchState.totalCount,
                isRunning: true,
              }
            : undefined
        }
        footer={outlineFooter}
      />
      <main className="min-w-0 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <p
          aria-live="polite"
          className={cn(getTypographyClassName('bodySm'), 'text-[var(--color-muted)]')}
        >
          {message}
        </p>
        <div className="mt-4">
          {selected?.status === 'can_thong_tin' && factOwned ? (
            <FactsIncompleteBanner onEditFacts={() => onEditFacts?.(selected.sectionId)} />
          ) : null}
          {factOwned ? (
            <>
              <FactOwnedNotice />
              <div className="mt-5">
                <SectionContentFields
                  scope={scope ?? ''}
                  fields={editor?.fields ?? []}
                  candidate={workingCandidate ?? {}}
                  onChange={setWorkingCandidate}
                  document={resources.documentData?.document}
                />
              </div>
              <button
                type="button"
                onClick={() => onEditFacts?.(selected.sectionId)}
                className={cn(
                  getTypographyClassName('buttonSecondary'),
                  'min-h-11 w-fit rounded-[var(--radius-button)] border border-[var(--color-border)] px-4 py-2 cursor-pointer mt-4'
                )}
              >
                Open approved Facts
              </button>
            </>
          ) : workingCandidate && editor ? (
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(20rem,0.85fr)]">
              <div className="grid gap-4">
                <SectionContentFields
                  scope={scope ?? ''}
                  fields={editor.fields}
                  candidate={workingCandidate}
                  onChange={setWorkingCandidate}
                  document={resources.documentData?.document}
                />
                <ContentDraftActions
                  hasDraft={Boolean(draft)}
                  canApply={Boolean(workingCandidate)}
                  pending={pending}
                  onSave={saveDraft}
                  onApply={apply}
                  onDiscard={discard}
                />
              </div>
              {editor.generation ? (
                <ContentGenerationPanel
                  scope={scope ?? ''}
                  mode={mode}
                  onModeChange={setMode}
                  instruction={instruction}
                  defaultInstruction={defaultInstruction}
                  onInstructionChange={setCustomInstruction}
                  onRestoreDefault={() => setCustomInstruction(null)}
                  factInputs={editor.factInputs}
                  facts={factsForPanel}
                  onGenerate={generate}
                  pending={pending}
                  disabled={selected?.status === 'can_thong_tin'}
                  promptPreview={promptPreview}
                  draftSystemPrompt={draft?.generation?.systemPrompt}
                  draftUserPrompt={draft?.generation?.userPrompt}
                  onRequestPreview={handleRequestPromptPreview}
                />
              ) : (
                <DeterministicFactsPanel
                  factInputs={editor.factInputs}
                  facts={factsForPanel}
                />
              )}
            </div>
          ) : (
            <ContentContractUnavailable onRetry={() => { void resources.refresh(); }} />
          )}
        </div>
      </main>
    </section>
  );
}
