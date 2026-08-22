'use client';

import { useCallback, useState, useTransition } from 'react';
import { apiErrorMessage } from '../../lib/apiError.ts';
import { useToast } from '../staff-workspace/ToastProvider.tsx';
import { cloneCandidate } from './SectionContentFields.tsx';
import { contentReconciler } from '../../lib/rules/contentReconciler.ts';
import type {
  ContentCandidate,
  ContentDraft,
  DocumentResponse,
  PromptPreview,
} from '../quotation-workspace/useQuotationWorkspace.ts';
import { SCOPE_BY_SECTION_TYPE, type Mode } from './useContentStudioState.ts';

export type UseContentGenerationOptions = {
  quotationId: string;
  lang: string;
  scope: string | null;
  mode: Mode;
  activeCustomInstruction: string | null;
  editor?: {
    owner?: string;
    generation?: boolean;
    defaultInstructions?: Record<string, string> | null;
  };
  draft?: ContentDraft;
  workingCandidate?: ContentCandidate;
  readiness: Array<{
    sectionId: string;
    sectionType: string;
    generator?: boolean;
    status?: string | null;
  }>;
  resources: {
    documentData?: DocumentResponse;
    refresh: () => Promise<unknown>;
    request: <T>(
      path: string,
      init?: RequestInit,
      fallback?: string
    ) => Promise<T>;
  };
  setGeneratedDraft: (draft: ContentDraft | null) => void;
  setWorkingCandidate: (candidate: ContentCandidate) => void;
  setLocalCandidate: (
    val: { scope: string; candidate: ContentCandidate } | null
  ) => void;
  onProceedToDesign?: () => void;
};

export function useContentGeneration({
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
}: UseContentGenerationOptions) {
  const [pending, startTransition] = useTransition();
  const [message, setMessage] = useState(
    'Select a section to review its content.'
  );
  const [promptPreview, setPromptPreview] = useState<
    PromptPreview | undefined
  >(undefined);
  const [batchState, setBatchState] = useState<{
    isRunning: boolean;
    generatingScope: string | null;
    completedCount: number;
    totalCount: number;
  }>({
    isRunning: false,
    generatingScope: null,
    completedCount: 0,
    totalCount: 0,
  });

  const { toast, notify, clearScope } = useToast();

  const reportFailure = useCallback(
    (action: string, error: unknown) => {
      const msg = apiErrorMessage(error);
      setMessage(msg);
      notify({
        message: msg,
        type: 'error',
        persistent: true,
        scope: `content:${action}`,
        action: { label: 'Reload', onClick: () => window.location.reload() },
      });
    },
    [notify]
  );

  const handleRequestPromptPreview = useCallback(async () => {
    if (!scope) return;
    try {
      const res = await resources.request<{ promptPreview: PromptPreview }>(
        `/api/v2/quotations/${quotationId}/content-drafts/prompt-preview?lang=${encodeURIComponent(
          lang
        )}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scope,
            generationMode: mode,
            instruction: activeCustomInstruction ?? '',
          }),
        }
      );
      setPromptPreview(res.promptPreview);
    } catch (err) {
      console.error('Failed to preview prompt', err);
      toast(apiErrorMessage(err) || 'Failed to generate prompt preview.', 'error');
    }
  }, [activeCustomInstruction, lang, mode, quotationId, resources, scope, toast]);

  const generate = useCallback(() => {
    if (!scope || !editor?.generation) return;
    startTransition(async () => {
      try {
        const response = await resources.request<{ draft: ContentDraft }>(
          `/api/v2/quotations/${quotationId}/content-drafts?lang=${encodeURIComponent(
            lang
          )}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              scope,
              generationMode: mode,
              instruction: activeCustomInstruction ?? '',
            }),
          },
          'Content generation failed.'
        );
        setGeneratedDraft(response.draft);
        setWorkingCandidate(cloneCandidate(response.draft.candidate));
        await resources.refresh();
        clearScope('content:generate');
        setMessage(
          response.draft.missingInputs.length
            ? 'Complete the required Facts before generating this draft.'
            : 'AI draft filled into the content fields. Review it before Apply.'
        );
        toast('Content draft is ready for review.', 'success');
      } catch (error) {
        reportFailure('generate', error);
      }
    });
  }, [
    activeCustomInstruction,
    clearScope,
    editor?.generation,
    lang,
    mode,
    quotationId,
    reportFailure,
    resources,
    scope,
    setGeneratedDraft,
    setWorkingCandidate,
    toast,
  ]);

  const handleBatchGenerateAll = useCallback(() => {
    const eligibleItems = readiness.filter((item) => {
      const itemScope = item.sectionId.startsWith('itinerary:day:')
        ? item.sectionId
        : SCOPE_BY_SECTION_TYPE[item.sectionType] ?? item.sectionType;
      const itemEditor = resources.documentData?.contentRegistry?.[itemScope];
      return (
        item.generator !== false &&
        item.status !== 'can_thong_tin' &&
        itemEditor?.owner !== 'fact'
      );
    });

    const uniqueScopes = Array.from(
      new Set(
        eligibleItems.map((item) =>
          item.sectionId.startsWith('itinerary:day:')
            ? item.sectionId
            : SCOPE_BY_SECTION_TYPE[item.sectionType] ?? item.sectionType
        )
      )
    );

    if (!uniqueScopes.length) {
      toast(
        'No AI content sections are ready for generation. Check missing Facts.',
        'info'
      );
      return;
    }

    startTransition(async () => {
      setBatchState({
        isRunning: true,
        generatingScope: 'all',
        completedCount: 0,
        totalCount: uniqueScopes.length,
      });

      try {
        const res = await resources.request<{
          ok: boolean;
          drafts: ContentDraft[];
          count: number;
        }>(
          `/api/v2/quotations/${quotationId}/content-drafts/batch-generate?lang=${encodeURIComponent(
            lang
          )}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              generationMode: mode,
              instruction: activeCustomInstruction ?? '',
            }),
          },
          'Batch generation failed.'
        );

        await resources.refresh();
        clearScope('content:generate');
        const count = res.count ?? res.drafts?.length ?? uniqueScopes.length;
        const drafts = res.drafts ?? [];
        let hasAnyOverflow = false;
        for (const d of drafts) {
          if (d.candidate) {
            const check = contentReconciler.validateCandidatePdfBudget(d.scope, d.candidate as Record<string, unknown>);
            if (!check.isValid) {
              hasAnyOverflow = true;
              break;
            }
          }
        }
        if (hasAnyOverflow) {
          setMessage(`Batch generation completed (${count} sections ready), but some exceed PDF A4 budgets.`);
          toast(
            '⚠️ Batch generation completed, but some sections exceed PDF A4 budgets. Please review highlighted items.',
            'warning'
          );
        } else {
          setMessage(`Batch generation completed (${count} sections ready).`);
          toast(`All ${count} content sections generated successfully!`, 'success');
        }
      } catch (err) {
        reportFailure('generate', err);
      } finally {
        setBatchState({
          isRunning: false,
          generatingScope: null,
          completedCount: uniqueScopes.length,
          totalCount: uniqueScopes.length,
        });
      }
    });
  }, [
    activeCustomInstruction,
    clearScope,
    lang,
    mode,
    quotationId,
    readiness,
    reportFailure,
    resources,
    toast,
  ]);

  const saveDraft = useCallback(() => {
    if (!scope || !workingCandidate) return;
    startTransition(async () => {
      try {
        const response = draft
          ? await resources.request<{ draft: ContentDraft }>(
              `/api/v2/quotations/${quotationId}/content-drafts/${draft.id}`,
              {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate: workingCandidate }),
              }
            )
          : await resources.request<{ draft: ContentDraft }>(
              `/api/v2/quotations/${quotationId}/content-drafts/manual?lang=${encodeURIComponent(
                lang
              )}`,
              {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  scope,
                  candidate: workingCandidate,
                  baseRevision: resources.documentData?.currentRevision,
                }),
              }
            );
        setGeneratedDraft(response.draft);
        setWorkingCandidate(cloneCandidate(response.draft.candidate));
        await resources.refresh();
        clearScope('content:save');
        setMessage('Draft saved. Apply it when the content is ready.');
        toast('Content draft saved.', 'success');
      } catch (error) {
        reportFailure('save', error);
      }
    });
  }, [
    clearScope,
    draft,
    lang,
    quotationId,
    reportFailure,
    resources,
    scope,
    setGeneratedDraft,
    setWorkingCandidate,
    toast,
    workingCandidate,
  ]);

  const apply = useCallback(() => {
    if (!workingCandidate || !scope) return;
    startTransition(async () => {
      try {
        let activeDraft = draft;
        if (!activeDraft) {
          const created = await resources.request<{ draft: ContentDraft }>(
            `/api/v2/quotations/${quotationId}/content-drafts/manual?lang=${encodeURIComponent(
              lang
            )}`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                scope,
                candidate: workingCandidate,
                baseRevision: resources.documentData?.currentRevision,
              }),
            }
          );
          activeDraft = created.draft;
        } else {
          const patched = await resources.request<{ draft: ContentDraft }>(
            `/api/v2/quotations/${quotationId}/content-drafts/${activeDraft.id}`,
            {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ candidate: workingCandidate }),
            }
          );
          activeDraft = patched.draft;
        }
        await resources.request(
          `/api/v2/quotations/${quotationId}/content-drafts/${activeDraft.id}/apply`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              baseRevision:
                resources.documentData?.currentRevision ??
                activeDraft.sourceDocumentRevision,
            }),
          }
        );
        await resources.refresh();
        setGeneratedDraft(null);
        setLocalCandidate(null);
        clearScope('content:apply');
        setMessage('Content applied to the canonical brochure.');
        toast('Content applied to the canonical brochure.', 'success');
      } catch (error) {
        reportFailure('apply', error);
      }
    });
  }, [
    clearScope,
    draft,
    lang,
    quotationId,
    reportFailure,
    resources,
    scope,
    setGeneratedDraft,
    setLocalCandidate,
    toast,
    workingCandidate,
  ]);

  const discard = useCallback(() => {
    if (!draft) return;
    startTransition(async () => {
      try {
        await resources.request(
          `/api/v2/quotations/${quotationId}/content-drafts/${draft.id}/discard`,
          { method: 'POST' }
        );
        await resources.refresh();
        setGeneratedDraft(null);
        setLocalCandidate(null);
        clearScope('content:discard');
        setMessage('Draft discarded; canonical content remains unchanged.');
        toast('Content draft discarded.', 'info');
      } catch (error) {
        reportFailure('discard', error);
      }
    });
  }, [
    clearScope,
    draft,
    quotationId,
    reportFailure,
    resources,
    setGeneratedDraft,
    setLocalCandidate,
    toast,
  ]);

  const applyAll = useCallback(() => {
    startTransition(async () => {
      try {
        if (workingCandidate && scope) {
          const activeDraft = draft;
          if (!activeDraft) {
            await resources.request<{ draft: ContentDraft }>(
              `/api/v2/quotations/${quotationId}/content-drafts/manual?lang=${encodeURIComponent(
                lang
              )}`,
              {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  scope,
                  candidate: workingCandidate,
                  baseRevision: resources.documentData?.currentRevision,
                }),
              }
            );
          } else {
            await resources.request<{ draft: ContentDraft }>(
              `/api/v2/quotations/${quotationId}/content-drafts/${activeDraft.id}`,
              {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate: workingCandidate }),
              }
            );
          }
        }

        const res = await resources.request<{
          ok: boolean;
          currentRevision: number;
          appliedCount: number;
        }>(
          `/api/v2/quotations/${quotationId}/content-drafts/apply-all?lang=${encodeURIComponent(
            lang
          )}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              baseRevision: resources.documentData?.currentRevision ?? 1,
            }),
          },
          'Failed to apply all content drafts.'
        );

        await resources.refresh();
        setGeneratedDraft(null);
        setLocalCandidate(null);
        clearScope('content:apply');
        const countMsg = res.appliedCount ? `${res.appliedCount} ` : '';
        setMessage(`Applied ${countMsg}drafts to the canonical brochure.`);
        toast(`All ${countMsg}content drafts applied to brochure!`, 'success');
      } catch (error) {
        reportFailure('apply', error);
      }
    });
  }, [
    clearScope,
    draft,
    lang,
    quotationId,
    reportFailure,
    resources,
    scope,
    setGeneratedDraft,
    setLocalCandidate,
    toast,
    workingCandidate,
  ]);

  const handleProceedToDesign = useCallback(() => {
    startTransition(async () => {
      try {
        if (workingCandidate && scope) {
          const activeDraft = draft;
          if (!activeDraft) {
            await resources.request<{ draft: ContentDraft }>(
              `/api/v2/quotations/${quotationId}/content-drafts/manual?lang=${encodeURIComponent(
                lang
              )}`,
              {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  scope,
                  candidate: workingCandidate,
                  baseRevision: resources.documentData?.currentRevision,
                }),
              }
            );
          } else {
            await resources.request<{ draft: ContentDraft }>(
              `/api/v2/quotations/${quotationId}/content-drafts/${activeDraft.id}`,
              {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate: workingCandidate }),
              }
            );
          }
        }

        await resources.request(
          `/api/v2/quotations/${quotationId}/content-drafts/apply-all?lang=${encodeURIComponent(
            lang
          )}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              baseRevision: resources.documentData?.currentRevision ?? 1,
            }),
          }
        );
        await resources.refresh();
        setGeneratedDraft(null);
        setLocalCandidate(null);
        clearScope('content:apply');
      } catch (error) {
        reportFailure('apply', error);
        return;
      }
      onProceedToDesign?.();
    });
  }, [
    clearScope,
    draft,
    lang,
    onProceedToDesign,
    quotationId,
    reportFailure,
    resources,
    scope,
    setGeneratedDraft,
    setLocalCandidate,
    workingCandidate,
  ]);

  return {
    pending,
    message,
    setMessage,
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
  };
}
