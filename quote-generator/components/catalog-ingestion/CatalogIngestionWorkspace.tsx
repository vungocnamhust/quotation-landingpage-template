"use client";

import { useState } from "react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import { BatchList } from "./BatchList.tsx";
import { BatchStatusBadge } from "./BatchList.tsx";
import { ClarificationPanel } from "./ClarificationPanel.tsx";
import { CommitDialog } from "./CommitDialog.tsx";
import { DiffViewer } from "./DiffViewer.tsx";
import { PasteIntakeCard } from "./PasteIntakeCard.tsx";
import { UnresolvedPanel } from "./UnresolvedPanel.tsx";
import { useIngestionBatches } from "./useIngestionBatches.ts";

const MAX_QA_ROUNDS = 2;

export function CatalogIngestionWorkspace() {
  const {
    batches,
    isLoadingList,
    listErrorMessage,
    selectedId,
    selectBatch,
    selectedBatch,
    isLoadingBatch,
    isExtracting,
    actionError,
    extractBatch,
    answerClarifications,
    commitBatch,
    rejectBatch,
  } = useIngestionBatches();

  const [isAnswering, setIsAnswering] = useState(false);
  const [isCommitDialogOpen, setIsCommitDialogOpen] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [unresolvedAcknowledged, setUnresolvedAcknowledged] = useState(false);

  const unresolvedItems = selectedBatch?.payload.unresolved ?? [];
  const clarifications = selectedBatch?.resolution?.clarifications ?? [];
  const resolutionEntries = selectedBatch?.resolution?.entries ?? [];
  const roundsUsed = selectedBatch?.conversation.length ?? 0;

  const hasBlockingClarifications = clarifications.some((c) => c.blocking);
  const canCommit =
    !!selectedBatch &&
    (selectedBatch.status === "ready" || selectedBatch.status === "draft") &&
    !hasBlockingClarifications &&
    (unresolvedItems.length === 0 || unresolvedAcknowledged);

  const handleSubmitAnswers = async (answers: Record<string, string>) => {
    setIsAnswering(true);
    try {
      await answerClarifications(answers);
    } finally {
      setIsAnswering(false);
    }
  };

  const handleConfirmCommit = async () => {
    setIsCommitting(true);
    try {
      const result = await commitBatch(unresolvedAcknowledged);
      if (result) {
        setIsCommitDialogOpen(false);
        setUnresolvedAcknowledged(false);
      }
    } finally {
      setIsCommitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <header>
        <p className={cn(getTypographyClassName("overline"), "text-[var(--color-accent)]")}>Catalog operations</p>
        <h1 className={cn(getTypographyClassName("pageTitle"), "mt-1 text-[var(--color-on-surface)]")}>
          Import from text
        </h1>
        <p className={cn(getTypographyClassName("bodyLg"), "mt-1 text-[var(--color-muted)]")}>
          Paste a supplier tariff email — the Resolver Co-Pilot proposes matches, asks
          clarifying questions when unsure, and never commits without your review.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-6">
          <PasteIntakeCard isExtracting={isExtracting} errorMessage={actionError} onExtract={(input) => void extractBatch(input)} />

          {selectedBatch ? (
            <>
              <div className="flex items-center justify-between gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-4">
                <div>
                  <p className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Selected batch</p>
                  <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-on-surface)]")}>{selectedBatch.id}</p>
                </div>
                <BatchStatusBadge status={selectedBatch.status} />
              </div>

              {isLoadingBatch ? (
                <p className={cn(getTypographyClassName("bodySm"), "text-[var(--color-muted)]")}>Loading batch…</p>
              ) : (
                <>
                  <ClarificationPanel
                    clarifications={clarifications}
                    roundsUsed={roundsUsed}
                    maxRounds={MAX_QA_ROUNDS}
                    isSubmitting={isAnswering}
                    onSubmit={handleSubmitAnswers}
                  />

                  <UnresolvedPanel
                    items={unresolvedItems}
                    acknowledged={unresolvedAcknowledged}
                    onAcknowledgedChange={setUnresolvedAcknowledged}
                  />

                  <DiffViewer entries={resolutionEntries} payload={selectedBatch.payload} />

                  {selectedBatch.status !== "committed" && selectedBatch.status !== "rejected" ? (
                    <div className="flex gap-3">
                      <button
                        type="button"
                        disabled={!canCommit}
                        onClick={() => setIsCommitDialogOpen(true)}
                        className={cn(
                          getTypographyClassName("buttonPrimary"),
                          "rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] disabled:cursor-not-allowed disabled:opacity-50",
                        )}
                      >
                        Review &amp; commit
                      </button>
                      <button
                        type="button"
                        onClick={() => void rejectBatch()}
                        className={cn(
                          getTypographyClassName("buttonSecondary"),
                          "rounded-[var(--radius-button)] border border-[var(--color-border-strong)] px-4 py-2.5 text-[var(--color-on-surface)] transition-colors hover:bg-[var(--color-surface-hover)]",
                        )}
                      >
                        Reject
                      </button>
                    </div>
                  ) : null}
                </>
              )}
            </>
          ) : null}
        </div>

        <BatchList
          batches={batches}
          selectedId={selectedId}
          isLoading={isLoadingList}
          errorMessage={listErrorMessage}
          onSelect={selectBatch}
        />
      </div>

      {isCommitDialogOpen ? (
        <CommitDialog
          entries={resolutionEntries}
          isCommitting={isCommitting}
          onClose={() => setIsCommitDialogOpen(false)}
          onConfirm={() => void handleConfirmCommit()}
        />
      ) : null}
    </div>
  );
}
