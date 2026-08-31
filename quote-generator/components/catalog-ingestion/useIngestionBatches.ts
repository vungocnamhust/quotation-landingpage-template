"use client";

import { useCallback, useState } from "react";
import useSWR from "swr";
import {
  answerIngestionBatchClarifications,
  commitIngestionBatch,
  createIngestionBatch,
  editIngestionBatch,
  getIngestionBatch,
  listIngestionBatches,
  rejectIngestionBatch,
  type IngestionBatch,
  type IngestionBatchStatus,
  type IngestionSourceChannel,
  type IngestionSourceDocumentType,
} from "../../lib/quotationApi.ts";
import { apiErrorMessage, QuotationApiError } from "../../lib/apiError.ts";

/**
 * Headless hook for the Interactive Ingestion Co-Pilot (15.8) — owns the batch list cache,
 * the currently-selected batch's cache, and every mutation. Every write's response IS the
 * new cache value (the server always returns the fresh batch), so mutations replace the
 * cache instead of triggering a revalidating refetch — same shape as useCostingWorkspace.
 */
export function useIngestionBatches(statusFilter?: IngestionBatchStatus) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);

  const {
    data: listData,
    error: listError,
    isLoading: isLoadingList,
    mutate: mutateList,
  } = useSWR(["ingestion-batches", statusFilter ?? "all"], () => listIngestionBatches(statusFilter), {
    revalidateOnFocus: false,
  });

  const {
    data: selectedBatch,
    isLoading: isLoadingBatch,
    mutate: mutateBatch,
  } = useSWR(selectedId ? ["ingestion-batch", selectedId] : null, ([, id]) => getIngestionBatch(id), {
    revalidateOnFocus: false,
  });

  const applyBatch = useCallback(
    (batch: IngestionBatch) => {
      mutateBatch(batch, { revalidate: false });
      mutateList();
      setActionError(null);
      return batch;
    },
    [mutateBatch, mutateList],
  );

  const runAction = useCallback(
    async <T,>(action: () => Promise<T>): Promise<T | null> => {
      try {
        return await action();
      } catch (error) {
        setActionError(apiErrorMessage(error));
        if (error instanceof QuotationApiError && error.kind === "conflict" && selectedId) {
          await mutateBatch();
        }
        return null;
      }
    },
    [mutateBatch, selectedId],
  );

  const extractBatch = useCallback(
    async (input: { rawText: string; sourceChannel: IngestionSourceChannel; sourceDocumentType: IngestionSourceDocumentType }) => {
      setIsExtracting(true);
      try {
        return await runAction(async () => {
          const batch = await createIngestionBatch(input);
          setSelectedId(batch.id);
          return applyBatch(batch);
        });
      } finally {
        setIsExtracting(false);
      }
    },
    [applyBatch, runAction],
  );

  const answerClarifications = useCallback(
    (answers: Record<string, unknown>) =>
      runAction(async () => {
        if (!selectedBatch) return null;
        const batch = await answerIngestionBatchClarifications(selectedBatch.id, answers, selectedBatch.batch_revision);
        return applyBatch(batch);
      }),
    [applyBatch, runAction, selectedBatch],
  );

  const editBatch = useCallback(
    (edits: Record<string, unknown>) =>
      runAction(async () => {
        if (!selectedBatch) return null;
        const batch = await editIngestionBatch(selectedBatch.id, edits, selectedBatch.batch_revision);
        return applyBatch(batch);
      }),
    [applyBatch, runAction, selectedBatch],
  );

  const commitBatch = useCallback(
    (acknowledgeUnresolved = false) =>
      runAction(async () => {
        if (!selectedBatch) return null;
        const batch = await commitIngestionBatch(selectedBatch.id, selectedBatch.batch_revision, acknowledgeUnresolved);
        return applyBatch(batch);
      }),
    [applyBatch, runAction, selectedBatch],
  );

  const rejectBatch = useCallback(
    (reason?: string) =>
      runAction(async () => {
        if (!selectedBatch) return null;
        const batch = await rejectIngestionBatch(selectedBatch.id, selectedBatch.batch_revision, reason);
        return applyBatch(batch);
      }),
    [applyBatch, runAction, selectedBatch],
  );

  return {
    batches: listData?.items ?? [],
    totalBatches: listData?.total ?? 0,
    isLoadingList,
    listErrorMessage: listError ? apiErrorMessage(listError) : null,
    selectedId,
    selectBatch: setSelectedId,
    selectedBatch: selectedBatch ?? null,
    isLoadingBatch,
    isExtracting,
    actionError,
    extractBatch,
    answerClarifications,
    editBatch,
    commitBatch,
    rejectBatch,
    refreshList: () => mutateList(),
  };
}
