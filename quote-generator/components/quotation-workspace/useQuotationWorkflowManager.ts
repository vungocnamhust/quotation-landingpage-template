"use client";

import { useCallback, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { QuotationFacts } from "./factsTypes.ts";
import { ensureFactsDefaults } from "./factsTypes.ts";
import type { useQuotationWorkspace } from "./useQuotationWorkspace.ts";
import { apiErrorMessage } from "../../lib/apiError.ts";

import type { ToastItem } from "../staff-workspace/ToastProvider.tsx";

export type WorkspaceStage = "facts" | "costing" | "content" | "design" | "review";

export type UseQuotationWorkflowManagerOptions = {
  quotationId: string;
  lang: string;
  stage: WorkspaceStage;
  setStage: (stage: WorkspaceStage) => void;
  editableFacts: QuotationFacts | null;
  setEditableFacts: Dispatch<SetStateAction<QuotationFacts | null>>;
  workspace: ReturnType<typeof useQuotationWorkspace>;
  toast: (message: string, type?: "success" | "error" | "info") => void;
  notify: (opts: Omit<ToastItem, "id">) => void;
};

export function isFactsEquivalent(
  a: QuotationFacts | null | undefined,
  b: QuotationFacts | null | undefined
): boolean {
  if (a === b) return true;
  if (!a || !b) return false;

  try {
    const normA = JSON.stringify(ensureFactsDefaults(a));
    const normB = JSON.stringify(ensureFactsDefaults(b));
    return normA === normB;
  } catch {
    return false;
  }
}

export function useQuotationWorkflowManager({
  stage,
  setStage,
  editableFacts,
  setEditableFacts,
  workspace,
  toast,
  notify,
}: UseQuotationWorkflowManagerOptions) {
  const [isSaving, setIsSaving] = useState(false);

  const baselineFacts = workspace.facts.data?.facts;
  const currentRevision = workspace.document.data?.currentRevision ?? 0;

  // Dirty checking
  const isFactsDirty = useMemo(() => {
    if (!editableFacts) return false;
    if (!baselineFacts) return true;
    return !isFactsEquivalent(editableFacts, baselineFacts);
  }, [editableFacts, baselineFacts]);

  /**
   * Save facts to backend, clear dirty state, and refresh all SWR caches atomically.
   */
  const saveFactsWithRefresh = useCallback(
    async (
      factsToSave: QuotationFacts,
      options?: { targetStageAfterSave?: WorkspaceStage; silent?: boolean }
    ): Promise<boolean> => {
      setIsSaving(true);
      try {
        await workspace.saveFacts(factsToSave);
        setEditableFacts(null);
        await workspace.refresh();

        if (!options?.silent) {
          toast("Facts saved. Existing content candidates re-evaluated.", "success");
        }

        if (options?.targetStageAfterSave) {
          setStage(options.targetStageAfterSave);
        }

        return true;
      } catch (error) {
        const message = apiErrorMessage(error);
        notify({
          message: `Failed to save facts: ${message}`,
          type: "error",
          persistent: true,
          scope: "facts:save",
          action: {
            label: "Retry save",
            onClick: () => {
              void workspace
                .saveFacts(factsToSave)
                .then(() => {
                  setEditableFacts(null);
                  return workspace.refresh();
                })
                .then(() => {
                  if (options?.targetStageAfterSave) {
                    setStage(options.targetStageAfterSave);
                  }
                  toast("Facts saved.", "success");
                })
                .catch((retryErr) => {
                  toast(apiErrorMessage(retryErr), "error");
                });
            },
          },
        });
        toast(message, "error");
        return false;
      } finally {
        setIsSaving(false);
      }
    },
    [workspace, setEditableFacts, toast, notify, setStage]
  );

  /**
   * Guarded Stage Navigation (Dirty State Protection):
   * When navigating away from Facts with unsaved changes, automatically performs
   * a Staged Auto-Save and refreshes SWR caches before completing the transition.
   * If saving fails, the user is kept on Facts tab to prevent data loss.
   */
  const guardedNavigateStage = useCallback(
    async (
      targetStage: WorkspaceStage,
      onSaveSuccess?: () => void
    ): Promise<boolean> => {
      if (stage === targetStage) return true;

      // If on Facts tab with unsaved modifications, auto-save before leaving
      if (stage === "facts" && targetStage !== "facts" && isFactsDirty && editableFacts) {
        toast("Auto-saving facts before moving to " + targetStage + "…", "info");
        const success = await saveFactsWithRefresh(editableFacts, {
          targetStageAfterSave: targetStage,
          silent: false,
        });

        if (success) {
          onSaveSuccess?.();
          return true;
        }

        // Save failed -> prevent navigation and keep user on Facts tab
        return false;
      }

      // Safe navigation
      setStage(targetStage);
      return true;
    },
    [stage, isFactsDirty, editableFacts, toast, saveFactsWithRefresh, setStage]
  );

  /**
   * Manually re-sync SWR caches across all workspace queries.
   */
  const refreshWorkflow = useCallback(async () => {
    try {
      await workspace.refresh();
    } catch (error) {
      toast(apiErrorMessage(error), "error");
    }
  }, [workspace, toast]);

  return {
    isFactsDirty,
    isSaving,
    activeRevision: currentRevision,
    guardedNavigateStage,
    saveFactsWithRefresh,
    refreshWorkflow,
  };
}
