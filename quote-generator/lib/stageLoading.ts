export type QuotationWorkspaceStage = "facts" | "content" | "design" | "review";

export function isQuotationStageLoading({
  committedStage,
  requestedStage,
  resourcesReady,
  hasLoadError,
}: {
  committedStage: QuotationWorkspaceStage;
  requestedStage: QuotationWorkspaceStage | null;
  resourcesReady: boolean;
  hasLoadError: boolean;
}): boolean {
  if (!requestedStage) return false;
  if (requestedStage !== committedStage) return false;
  return !resourcesReady && !hasLoadError;
}
