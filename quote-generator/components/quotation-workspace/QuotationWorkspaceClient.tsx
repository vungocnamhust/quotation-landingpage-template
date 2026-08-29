"use client";

import dynamic from "next/dynamic";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
  type CSSProperties,
  type SetStateAction,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  ClipboardList,
  PenLine,
  Palette,
  Rocket,
  Lock,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Calculator,
} from "lucide-react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import FactsForm from "./FactsForm.tsx";
import useSWR from "swr";
import {
  hydrateDestinationRefs,
  type QuotationFacts,
  type QuoteRequestItem,
} from "./factsTypes.ts";
import { apiErrorMessage, quotationFetch, QuotationApiError } from "../../lib/apiError.ts";
import { publishQuotation } from "../../lib/publicationApi.ts";
import { usePublicationJob } from "./usePublicationJob.ts";
import { workflowAdapter } from "../../lib/rules/workflowAdapter.ts";
import { buildDisplayDocumentFromQuoteDocument } from "../../display/runtimePageBuilder.ts";
import type { ViewMode } from "../../display/contracts.ts";
import { updateDesignerPresentationFacts } from "../../lib/prefillEngine.ts";
import { useQuotationWorkspace } from "./useQuotationWorkspace.ts";
import { useQuotationWorkflowManager } from "./useQuotationWorkflowManager.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";
import { useWorkspaceNavigation } from "../staff-workspace/WorkspaceNavigation.tsx";
import {
  parseFactsDeepLink,
  serializeFactsFocus,
  type ResolvedHandoff,
} from "./editableHandoff.ts";
import { ReviewBlockersPanel } from "./ReviewBlockersPanel.tsx";
import DesignPreviewToolbar from "./DesignPreviewToolbar.tsx";
import BrochurePreviewModal from "./BrochurePreviewModal.tsx";
import RequestRecapModal from "./RequestRecapModal.tsx";
import EditQuotationConfirmModal from "./EditQuotationConfirmModal.tsx";
import ImpactCenter from "./ImpactCenter.tsx";
import { useContentActionPlan, type ContentAction } from "./useContentActionPlan.ts";
import { useContentActionExecution } from "./useContentActionExecution.ts";
import { isQuotationStageLoading } from "../../lib/stageLoading.ts";
import { CostingWorkbench } from "../quotation-costing/CostingWorkbench.tsx";
import { AttachRecoveryBanner } from "../quotation-costing/AttachRecoveryBanner.tsx";
import { clearAttachRecovery, readAttachRecovery } from "../../lib/attachRecovery.ts";

const ContentStudioClient = dynamic(
  () => import("../content-studio/ContentStudioClient"),
  {
    loading: () => (
      <div className="workspace-skeleton">
        <div className="workspace-skeleton__line workspace-skeleton__line--wide" />
        <div className="workspace-skeleton__line workspace-skeleton__line--mid" />
      </div>
    ),
  }
);
const DesignCanvas = dynamic(() => import("./DesignCanvas"), {
  loading: () => (
    <div className="workspace-skeleton">
      <div className="workspace-skeleton__line workspace-skeleton__line--mid" />
    </div>
  ),
});
const PublicationTargetManager = dynamic(
  () => import("./PublicationTargetManager")
);
const API_BASE = process.env.NEXT_PUBLIC_QUOTATION_API_URL ?? "";
const stages = ["facts", "costing", "content", "design", "review"] as const;
type Stage = (typeof stages)[number];

const stageIcons: Record<Stage, React.ComponentType<{ size?: number; className?: string }>> = {
  facts: ClipboardList,
  costing: Calculator,
  content: PenLine,
  design: Palette,
  review: Rocket,
};

function StagePanelSkeleton({ stage }: { stage: Stage }) {
  return (
    <div className="workspace-skeleton" role="status" aria-live="polite" aria-label={`Loading ${stage} workspace`}>
      <div className="workspace-skeleton__line workspace-skeleton__line--wide" />
      <div className="workspace-skeleton__line workspace-skeleton__line--mid" />
      <div className="workspace-skeleton__line" />
    </div>
  );
}

export default function QuotationWorkspaceClient({
  quotationId,
  lang,
}: {
  quotationId: string;
  lang: string;
}) {
  const router = useRouter();
  const { push } = useWorkspaceNavigation();
  const search = useSearchParams();
  const pathname = usePathname();
  const requestedStage = search.get("stage");
  const isImpactCenter = requestedStage === "impact";
  const stage: Stage = stages.includes(requestedStage as Stage)
    ? (requestedStage as Stage)
    : "facts";
  const attachRecovery = readAttachRecovery(new URLSearchParams(search.toString()));
  const [requestedStageIntent, setRequestedStageIntent] = useState<Stage | null>(null);
  const [isStageRoutePending, startStageTransition] = useTransition();
  const [isStageGuarding, setIsStageGuarding] = useState(false);
  const setStage = useCallback((next: Stage) => {
    const params = new URLSearchParams(search.toString());
    params.set("stage", next);
    startStageTransition(() => {
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    });
  }, [pathname, router, search, startStageTransition]);
  const handleAttachRecovered = useCallback(() => {
    const params = clearAttachRecovery(new URLSearchParams(search.toString()));
    params.set("stage", "costing");
    params.set("lang", lang);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [lang, pathname, router, search]);
  const { toast, notify, clearScope } = useToast();
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null);
  const [fallbackUrl, setFallbackUrl] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [publicationBrandId, setPublicationBrandId] = useState<string | null>(
    null
  );
  const [previewMode, setPreviewMode] = useState<ViewMode>("desktop");
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [editableFacts, setEditableFacts] = useState<QuotationFacts | null>(
    null
  );
  const [isEditingQuotation, setIsEditingQuotation] = useState(false);
  const [isEditQuotationModalOpen, setIsEditQuotationModalOpen] = useState(false);
  const [pendingEditQuotationTarget, setPendingEditQuotationTarget] = useState<ResolvedHandoff | undefined>();
  const [pending, startTransition] = useTransition();
  const workspace = useQuotationWorkspace(quotationId, lang);
  const refreshWorkspace = workspace.refresh;
  const { data: factsData } = workspace.facts;
  const { data: documentData } = workspace.document;
  const { data: reviewData } = workspace.review;
  const { data: workflowData } = workspace.workflow;
  const { data: options } = workspace.options;
  const { data: brandsResponse } = workspace.brands;
  const contentActionPlan = useContentActionPlan(quotationId, isImpactCenter);
  const contentActionExecution = useContentActionExecution(quotationId);

  const opportunityId =
    factsData?.source?.opportunityId ||
    ((factsData?.facts as Record<string, unknown> | undefined)?.opportunity_id as string | undefined) ||
    ((documentData?.document?.meta as Record<string, unknown> | undefined)?.opportunityId as string | undefined);

  const { data: quoteRequest } = useSWR<QuoteRequestItem>(
    opportunityId ? `${API_BASE}/api/v2/workspace/requests/${opportunityId}` : null,
    (url: string) => quotationFetch<QuoteRequestItem>(url, undefined, "Failed to load request.")
  );
  const [isRecapOpen, setIsRecapOpen] = useState(false);

  const {
    isFactsDirty,
    isSaving: isWorkflowSaving,
    guardedNavigateStage,
    saveFactsWithRefresh,
  } = useQuotationWorkflowManager({
    quotationId,
    lang,
    stage,
    setStage,
    editableFacts,
    setEditableFacts,
    workspace,
    toast,
    notify,
  });

  const factsDeepLink = useMemo(
    () =>
      parseFactsDeepLink(
        search.get("factsSection"),
        search.get("focus"),
        documentData?.document,
      ),
    [documentData?.document, search],
  );
  const [publicationJobId, setPublicationJobId] = useState<string | null>(null);
  // Plan 16.2 F-13/F-14: keyed strictly to the id of the job actually
  // requested — a stray response for a superseded job can never overwrite
  // this state, and switching brand/republishing mid-flight naturally
  // re-keys to the new job instead of leaking the old one's status.
  const publicationJob = usePublicationJob(publicationJobId);
  // Plan 16.2 F-15: one canonical computation feeds both the Publish gate
  // and the ReviewBlockersPanel badges — they can no longer disagree,
  // because they are now reading the same value instead of each deriving
  // it independently from /review-status and /workflow.
  const canonicalWorkflow = useMemo(
    () => workflowAdapter.fromServerWorkflow(workflowData, reviewData, publicationJob, lang),
    [workflowData, reviewData, publicationJob, lang]
  );
  const reviewReady = canonicalWorkflow.isReady;
  const loadError =
    workspace.facts.error ??
    workspace.document.error ??
    workspace.workflow.error ??
    workspace.options.error ??
    workspace.brands.error;

  useEffect(() => {
    if (!factsData?.baselineLang || factsData.baselineLang === lang) return;
    const params = new URLSearchParams(search.toString());
    params.set("lang", factsData.baselineLang);
    router.replace(`${pathname}?${params.toString()}`);
  }, [factsData?.baselineLang, lang, pathname, router, search]);

  const selectedBrandId =
    publicationBrandId ?? documentData?.brandProfile.id ?? "";
  const previewProfile =
    brandsResponse?.brands.find((brand) => brand.id === selectedBrandId)
      ?.renderProfile ?? documentData?.brandProfile;
  const liveDocumentModel = useMemo(
    () =>
      documentData && previewProfile
        ? buildDisplayDocumentFromQuoteDocument({
            document: documentData.document,
            brandProfile: previewProfile,
            lang: lang as "en" | "vi" | "ar",
            viewMode: previewMode,
          })
        : null,
    [documentData, lang, previewMode, previewProfile]
  );

  const blockersRef = useRef<HTMLDivElement>(null);

  const scrollToBlockers = useCallback(() => {
    setStage("review");
    window.setTimeout(() => {
      blockersRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 50);
  }, [setStage]);

  const goTo = useCallback(
    async (next: Stage) => {
      setRequestedStageIntent(next);
      setIsStageGuarding(true);
      const allowed = await guardedNavigateStage(next);
      setIsStageGuarding(false);
      if (!allowed) {
        setRequestedStageIntent(null);
        return;
      }

      if (next === "review" && !reviewReady) {
        notify({
          message: "Resolve the server-reported review blockers before publishing.",
          type: "error",
          persistent: true,
          scope: "review:blockers",
          action: {
            label: "Open blockers",
            onClick: scrollToBlockers,
          },
        });
      }
    },
    [guardedNavigateStage, notify, reviewReady, scrollToBlockers]
  );

  function saveFacts(facts: QuotationFacts) {
    void saveFactsWithRefresh(facts, { targetStageAfterSave: "content" });
  }

  function createBusinessVersion(facts: QuotationFacts) {
    if (!documentData) return;
    startTransition(async () => {
      try {
        const result = await workspace.request<{ redirectUrl: string }>(
          `/api/v2/quotations/${quotationId}/versions`,
          { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ facts, baseRevision: documentData.currentRevision }) },
          "Unable to create the quotation version."
        );
        toast("New quotation version created. Review its exact change plan in Impact Center.", "success");
        push(result.redirectUrl);
      } catch (error) {
        notify({ message: apiErrorMessage(error), type: "error", persistent: true, scope: "quotation:version", action: { label: "Retry", onClick: () => createBusinessVersion(facts) } });
      }
    });
  }

  function savePresentation() {
    startTransition(async () => {
      try {
        await workspace.savePresentation({
          themeId: "brochure",
          layoutVersion: 1,
        });
        toast("Presentation choices saved.", "success");
        setEditableFacts(null);
      } catch (error) {
        toast(apiErrorMessage(error), "error");
      }
    });
  }

  // Plan 16.2 F-01: `publish` is redefined every render, closing over that
  // render's `documentData.currentRevision`. Storing it directly as a toast
  // action's onClick freezes that closure — a later `document.mutate()`
  // never reaches the button the user clicks. Routing "Retry" through this
  // ref instead means the click always invokes whichever `publish` closure
  // is current at click time.
  const publishRef = useRef(() => {});

  function publish() {
    if (!documentData || !reviewReady) return;
    const baseRevision = documentData.currentRevision;
    startTransition(async () => {
      let payload: Awaited<ReturnType<typeof publishQuotation>>;
      try {
        payload = await publishQuotation(quotationId, lang, {
          baseRevision,
          brandId: selectedBrandId || undefined,
        });
      } catch (error) {
        const recovery = error instanceof QuotationApiError ? error.metadata.recovery : null;
        if (recovery === "reload") {
          // D1: never resend the stale baseRevision — refresh first, then
          // let the user re-trigger publish with the button's own (now
          // fresh) closure.
          await workspace.document.mutate();
          const currentRevision = error instanceof QuotationApiError ? error.metadata.currentRevision : undefined;
          notify({
            message: `This quotation changed in another session${currentRevision != null ? ` (now revision ${currentRevision})` : ""}. Review the latest version, then publish again.`,
            type: "error",
            persistent: true,
            scope: "publish:request",
            action: { label: "Publish latest revision", onClick: () => publishRef.current() },
          });
          return;
        }
        if (recovery === "open-blockers") {
          notify({ message: apiErrorMessage(error), type: "error", persistent: true, scope: "publish:request", action: { label: "Open blockers", onClick: scrollToBlockers } });
          return;
        }
        notify({ message: apiErrorMessage(error), type: "error", persistent: true, scope: "publish:request", action: { label: "Retry", onClick: () => publishRef.current() } });
        return;
      }
      setPublishedUrl(payload.published_url ?? null);
      setFallbackUrl(payload.fallback_url ?? null);
      setPdfUrl(payload.pdfUrl ?? null);
      setPublicationJobId(payload.jobId ?? null);
      try {
        await workspace.refresh();
      } catch (error) {
        const message = apiErrorMessage(error);
        notify({ message: `Publication was queued, but the workspace could not refresh: ${message}`, type: "error", persistent: true, scope: "publish:refresh", action: { label: "Retry refresh", onClick: () => void workspace.refresh() } });
      }
      clearScope("publish:request");
      toast(
        payload.status === "queued"
          ? "Publication queued while PDF renders."
          : `Published version ${payload.version ?? ""}.`,
        payload.status === "queued" ? "info" : "success"
      );
    });
  }

  useEffect(() => {
    publishRef.current = publish;
  });

  // Surface terminal job transitions exactly once per (job, status) pair —
  // usePublicationJob owns polling/correlation; this only reacts to it.
  const handledJobTransitionRef = useRef<string | null>(null);
  useEffect(() => {
    if (!publicationJob) return;
    const key = `${publicationJob.id}:${publicationJob.status}`;
    if (handledJobTransitionRef.current === key) return;
    handledJobTransitionRef.current = key;
    if (publicationJob.status === "succeeded") {
      void refreshWorkspace();
      clearScope("publish:job");
      toast("Publication is live.", "success");
    } else if (publicationJob.status === "failed") {
      notify({ message: publicationJob.lastError || "Publication failed before the PDF could be published.", type: "error", persistent: true, scope: "publish:job", action: { label: "Open review", onClick: () => setStage("review") } });
    }
  }, [publicationJob, refreshWorkspace, clearScope, toast, notify, setStage]);

  const labels: Record<Stage, string> = {
    facts: "Facts",
    costing: "Costing",
    content: "Content",
    design: "Design",
    review: "Review & Publish",
  };

  const isLocked = (item: Stage) => item === "review" ? !reviewReady : false;

  const isComplete = (item: Stage) => {
    if (item === "facts") return workflowData?.facts.ready ?? false;
    // Costing is a tool, not a gate (chốt #10) — it never blocks or shows as "complete".
    if (item === "costing") return false;
    if (item === "content") return workflowData?.content.ready ?? false;
    if (item === "design") return workflowData?.design.ready ?? false;
    if (item === "review") return canonicalWorkflow.isReady;
    return false;
  };

  const immutableFacts = factsData?.businessVersion?.immutable === true;
  const editable = factsData?.source?.kind === "manual" && (!immutableFacts || isEditingQuotation);

  const activeFacts =
    editableFacts ??
    (factsData?.facts
      ? hydrateDestinationRefs(factsData.facts, factsData.resolvedFacts)
      : undefined);
  const stageResourcesReady =
    stage === "facts"
      ? Boolean(factsData?.facts && activeFacts && options)
      : stage === "costing"
      ? true
      : stage === "content"
      ? Boolean(documentData && factsData)
      : stage === "design"
      ? Boolean(documentData && factsData && liveDocumentModel)
      : Boolean(reviewData && workflowData);
  const isStageLoading =
    isStageGuarding ||
    isStageRoutePending ||
    isQuotationStageLoading({
      committedStage: stage,
      requestedStage: requestedStageIntent,
      resourcesReady: stageResourcesReady,
      hasLoadError: Boolean(loadError),
    });

  const updateEditableFacts = useCallback(
    (next: SetStateAction<QuotationFacts>) => {
      setEditableFacts((previous) => {
        const current =
          previous ??
          (factsData?.facts
            ? hydrateDestinationRefs(factsData.facts, factsData.resolvedFacts)
            : undefined);
        if (!current) return previous;
        return typeof next === "function" ? next(current) : next;
      });
    },
    [factsData]
  );

  const navigateHandoff = useCallback(
    async (target: ResolvedHandoff) => {
      setRequestedStageIntent(target.stage as Stage);
      setIsStageGuarding(true);
      const allowed = await guardedNavigateStage(target.stage as Stage);
      setIsStageGuarding(false);
      if (!allowed) {
        setRequestedStageIntent(null);
        return;
      }

      const params = new URLSearchParams(search.toString());
      params.set("stage", target.stage);
      if (target.stage === "facts") {
        params.delete("section");
        params.set("factsSection", target.section);
        const focus = serializeFactsFocus(target.focus);
        if (focus) params.set("focus", focus);
        else params.delete("focus");
      } else if (target.stage === "design") {
        params.delete("factsSection");
        params.delete("section");
        const focus = serializeFactsFocus(target.focus);
        if (focus) {
          params.set("focus", focus);
        } else if (target.source && target.source !== "blocker") {
          params.set("focus", target.source);
        } else {
          params.delete("focus");
        }
      } else {
        params.delete("factsSection");
        params.delete("focus");
        let section = target.section;
        if (target.focus?.kind === "day") {
          const days = ((documentData?.document.itinerary as { days?: Array<{ dayNumber?: number; sourceFactId?: string }> } | undefined)?.days ?? []);
          const day = days[target.focus.index];
          const factId = day?.sourceFactId ?? day?.dayNumber;
          if (factId != null) section = `itinerary:day:${factId}`;
        }
        params.set("section", section);
      }
      startStageTransition(() => {
        router.replace(`${pathname}?${params.toString()}`, { scroll: false });
      });
    },
    [documentData?.document, guardedNavigateStage, pathname, router, search, startStageTransition],
  );

  // Plan 16 §B.3, Case 2: a locked field on the Design canvas never writes a
  // shadow value while Facts are immutable — it opens this confirmation,
  // which only flips edit mode + deep-links into Facts. The version itself
  // is created only when the user submits that form (createBusinessVersion).
  const requestEditQuotation = useCallback((target?: ResolvedHandoff) => {
    setPendingEditQuotationTarget(target);
    setIsEditQuotationModalOpen(true);
  }, []);

  const cancelEditQuotation = useCallback(() => {
    setIsEditQuotationModalOpen(false);
    setPendingEditQuotationTarget(undefined);
  }, []);

  const confirmEditQuotation = useCallback(() => {
    const target = pendingEditQuotationTarget;
    setIsEditQuotationModalOpen(false);
    setPendingEditQuotationTarget(undefined);
    setIsEditingQuotation(true);
    void navigateHandoff(target ?? { stage: "facts", section: "trip", source: "", wildcardIndices: [] });
  }, [pendingEditQuotationTarget, navigateHandoff]);

  const acceptImpactCenter = useCallback(async () => {
    try {
      await contentActionExecution.accept();
      await contentActionPlan.mutate();
      clearScope("quotation:impact-center");
      toast("Change plan accepted. Choose where to continue.", "success");
    } catch (error) {
      notify({ message: apiErrorMessage(error), type: "error", persistent: true, scope: "quotation:impact-center", action: { label: "Retry", onClick: () => void contentActionPlan.mutate() } });
      throw error;
    }
  }, [clearScope, contentActionExecution, contentActionPlan, notify, toast]);

  const openContentAction = useCallback((action?: ContentAction) => {
    setRequestedStageIntent("content");
    const params = new URLSearchParams(search.toString());
    params.set("stage", "content");
    if (action) {
      params.set("section", action.scope);
      params.set("impactAction", action.id);
      const focus = action.scope.startsWith("itinerary:day:") ? action.scope.split(":").at(-1) : "";
      if (focus) params.set("focus", focus); else params.delete("focus");
    } else {
      params.delete("impactAction");
    }
    startStageTransition(() => {
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    });
  }, [pathname, router, search, startStageTransition]);

  const executeContentActions = useCallback(async (mode: "auto" | "bypass", actions: ContentAction[]) => {
    const plan = contentActionPlan.data;
    if (!plan || !actions.length) return;
    try {
      const result = await contentActionExecution.execute(
        mode,
        plan.id,
        actions.map((action) => action.id),
        "storytelling",
        mode === "bypass" ? documentData?.currentRevision : undefined,
      );
      await Promise.all([workspace.refresh(), contentActionPlan.mutate()]);
      toast(mode === "auto" ? "Review drafts are ready in Content Studio." : "Selected generated content has been applied.", "success");
      openContentAction(actions[0]);
      return result;
    } catch (error) {
      notify({ message: apiErrorMessage(error), type: "error", persistent: true, scope: `quotation:content-action:${mode}`, action: { label: "Retry", onClick: () => void executeContentActions(mode, actions) } });
      throw error;
    }
  }, [contentActionExecution, contentActionPlan, documentData?.currentRevision, notify, openContentAction, toast, workspace]);

  if (isImpactCenter) {
    return <ImpactCenter plan={contentActionPlan.data} loading={!contentActionPlan.data && !contentActionPlan.error} error={contentActionPlan.error ? apiErrorMessage(contentActionPlan.error) : null} pendingMode={contentActionExecution.pendingMode} onAccept={acceptImpactCenter} onGenerateDrafts={async (actions) => { await executeContentActions("auto", actions); }} onGenerateAndApply={async (actions) => { await executeContentActions("bypass", actions); }} onRetry={() => void contentActionPlan.mutate()} onReviewFacts={() => void goTo("facts")} onOpenContent={openContentAction} />;
  }

  return (
    <div
      className="flex min-w-0 w-full flex-col gap-6"
      style={liveDocumentModel?.colors.appChrome.style as CSSProperties | undefined}
    >
      <header className="flex flex-col gap-5 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--elevation-card)]">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  getTypographyClassName("overline"),
                  "text-[var(--color-accent)]"
                )}
              >
                Quotation Studio
              </span>
              <span
                className={cn(
                  getTypographyClassName("caption"),
                  "rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2.5 py-0.5 text-[var(--color-muted)]"
                )}
              >
                {editable ? "Manual Snapshot" : "DMC Core Snapshot"}
              </span>
              {factsData?.baselineLang ? (
                <span
                  className={cn(
                    getTypographyClassName("caption"),
                    "rounded-full border border-[var(--color-border)] bg-[var(--color-accent-wash)] px-2.5 py-0.5 text-[var(--color-accent)]"
                  )}
                >
                  {lang.toUpperCase()}
                </span>
              ) : null}
            </div>
            <h1
              className={cn(
                getTypographyClassName("pageTitle"),
                "text-[var(--color-on-surface)]"
              )}
            >
              {quotationId}
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {quoteRequest ? (
              <button
                type="button"
                onClick={() => setIsRecapOpen(true)}
                className={cn(
                  getTypographyClassName("buttonSecondary"),
                  "flex items-center gap-2 min-h-11 rounded-[var(--radius-button)] border border-amber-300/80 bg-amber-50/80 text-amber-900 hover:bg-amber-100 px-4 transition-all shadow-xs cursor-pointer"
                )}
                title="View original customer request context & constraints"
              >
                <ClipboardList size={15} className="text-amber-700" aria-hidden="true" />
                <span>Request Recap</span>
              </button>
            ) : null}
            {immutableFacts && !isEditingQuotation ? (
              <button type="button" onClick={() => setIsEditingQuotation(true)} className={cn(getTypographyClassName("buttonSecondary"), "flex items-center gap-2 min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)]")}>Edit Quotation</button>
            ) : null}

            <button
              type="button"
              onClick={() => {
                void workspace
                  .refresh()
                  .then(() => toast("Latest quotation revision loaded.", "info"))
                  .catch((error) => toast(apiErrorMessage(error), "error"));
              }}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "flex items-center gap-2 min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-on-surface)] hover:bg-[var(--color-accent-wash)] hover:text-[var(--color-accent)] px-4 transition-all cursor-pointer"
              )}
            >
              <RefreshCw size={14} aria-hidden="true" />
              <span>Refresh latest revision</span>
            </button>
          </div>
        </div>

        {/* Stepper Navigation */}
        <nav
          className="workspace-stepper border-t border-[var(--color-border)] pt-4"
          aria-label="Workspace stages"
        >
          {stages.map((item, index) => {
            const Icon = stageIcons[item];
            const locked = isLocked(item);
            const complete = isComplete(item);
            const current = stage === item;
            const pendingTarget = isStageLoading && requestedStageIntent === item;

            return (
              <div
                key={item}
                className="contents"
              >
                {index > 0 ? (
                  <div
                    className={cn(
                      "workspace-stepper__connector",
                      isComplete(stages[index - 1]) && "workspace-stepper__connector--done"
                    )}
                    aria-hidden="true"
                  />
                ) : null}
                <button
                  type="button"
                  onClick={() => goTo(item)}
                  aria-current={current ? "step" : undefined}
                  aria-busy={pendingTarget || undefined}
                  aria-disabled={locked || pendingTarget || undefined}
                  disabled={pendingTarget}
                  className={cn(
                    "workspace-stepper__step",
                    current && "workspace-stepper__step--current",
                    complete && "workspace-stepper__step--complete",
                    locked && "workspace-stepper__step--locked"
                  )}
                  title={locked ? "Resolve previous stages first" : undefined}
                >
                  <span className="workspace-stepper__circle">
                    {pendingTarget ? (
                      <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                    ) : complete ? (
                      <CheckCircle2 size={16} aria-hidden="true" />
                    ) : locked ? (
                      <Lock size={14} aria-hidden="true" />
                    ) : (
                      <Icon size={16} aria-hidden="true" />
                    )}
                  </span>
                  <span className="workspace-stepper__label">
                    <span className={cn(getTypographyClassName("buttonSecondary"))}>
                      {labels[item]}
                    </span>
                  </span>
                </button>
              </div>
            );
          })}
        </nav>
      </header>

      <section className="flex flex-col gap-6 min-w-0 w-full">
        {stage === "facts" && !isStageLoading && factsData?.facts && activeFacts && options ? (
          <>
          <FactsForm
            facts={activeFacts}
            options={options}
            resolvedFacts={factsData.resolvedFacts}
            readOnly={!editable}
            allowSubmitWhenReadOnly={!editable && !immutableFacts}
            templateLocked={isEditingQuotation}
            isDirty={isFactsDirty}
            sourceNote={
              isEditingQuotation
                ? `Editing creates business version ${(factsData?.businessVersion?.number ?? 0) + 1}; the current version remains immutable.`
                : editable
                ? "Manual quotation · changes create a new fact revision and stale older candidates."
                : `DMC Core owns this snapshot${
                    factsData?.source?.opportunityId
                      ? ` · ${factsData.source.opportunityId}`
                      : ""
                  }${
                    factsData?.source?.snapshotAt
                      ? ` · ${factsData.source.snapshotAt}`
                      : ""
                  }.`
            }
            onChange={updateEditableFacts}
            onSubmit={() =>
              isEditingQuotation ? createBusinessVersion(activeFacts) : editable ? saveFacts(activeFacts) : savePresentation()
            }
            pending={pending || isWorkflowSaving}
            deepLink={factsDeepLink}
            mediaWorkspace={documentData ? { quotationId, lang, document: documentData.document, currentRevision: documentData.currentRevision, contract: documentData.editableContract, onSaved: workspace.refresh } : undefined}
            onDesignerSelected={documentData ? async (designerProfileId) => {
              try {
                await workspace.request(`/api/v2/quotations/${quotationId}/facts/designer?lang=${encodeURIComponent(lang)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ baseRevision: documentData.currentRevision, designerProfileId }) }, "Travel Designer could not be assigned.");
                await workspace.refresh();
                toast("Travel Designer assigned to quotation.", "success");
              } catch (err: unknown) {
                toast(apiErrorMessage(err) || "Travel Designer could not be assigned.", "error");
              }
            } : undefined}
            submitLabel={
              isEditingQuotation
                ? "Create new quotation version"
                : editable
                ? "Save facts & prepare content"
                : "Save presentation choices"
            }
          />
          </>
        ) : stage === "facts" && !loadError ? (
          <StagePanelSkeleton stage="facts" />
        ) : null}

        {stage === "costing" && !isStageLoading ? (
          <>
            {attachRecovery ? (
              <AttachRecoveryBanner
                quotationId={quotationId}
                recovery={attachRecovery}
                onRecovered={handleAttachRecovered}
              />
            ) : null}
            <CostingWorkbench
              anchor={{ quotationId }}
              baseRevision={documentData?.currentRevision ?? workflowData?.currentRevision ?? 1}
              existingOptions={
                ((factsData?.facts as Record<string, unknown> | undefined)?.pricing_facts as { options?: Array<Record<string, unknown>> } | undefined)?.options?.map((opt) => ({
                  id: String(opt.id || ""),
                  label: opt.label as string | undefined,
                  currency: opt.currency as string | undefined,
                  group_total_amount_minor: (opt.group_total_amount_minor as number | undefined) ?? (opt.groupTotalAmountMinor as number | undefined),
                  per_adult_amount_minor: (opt.per_adult_amount_minor as number | undefined) ?? (opt.perAdultAmountMinor as number | undefined),
                  per_traveler_amount_minor: (opt.per_traveler_amount_minor as number | undefined) ?? (opt.perTravelerAmountMinor as number | undefined),
                })) ||
                (documentData?.document?.pricingOptions as Array<Record<string, unknown>> | undefined)?.map((opt) => ({
                  id: String(opt.id || ""),
                  label: opt.label as string | undefined,
                  currency: opt.currency as string | undefined,
                  group_total_amount_minor: (opt.groupTotalAmountMinor as number | undefined) ?? (opt.group_total_amount_minor as number | undefined),
                  per_adult_amount_minor: (opt.perAdultAmountMinor as number | undefined) ?? (opt.per_adult_amount_minor as number | undefined),
                  per_traveler_amount_minor: (opt.perTravelerAmountMinor as number | undefined) ?? (opt.per_traveler_amount_minor as number | undefined),
                })) ||
                []
              }
              adultsCount={
                (factsData?.facts as Record<string, unknown> | undefined)?.customer_facts
                  ? Number(((factsData?.facts as Record<string, unknown>).customer_facts as Record<string, unknown>).adults || 2)
                  : 2
              }
              onApplyPricingSuccess={() => {
                refreshWorkspace();
                notify({
                  type: "success",
                  message: "Giá thương mại đã được đồng bộ từ bảng dự toán sang báo giá.",
                });
              }}
            />
          </>
        ) : stage === "costing" && !loadError ? (
          <StagePanelSkeleton stage="costing" />
        ) : null}

        {loadError ? (
          <div
            role="alert"
            className="flex flex-wrap items-center gap-3 rounded-[var(--radius-card)] border border-[var(--color-border-strong)] bg-[var(--color-surface-muted)] p-4"
          >
            <p
              className={cn(
                getTypographyClassName("bodyMd"),
                "text-[var(--color-on-surface)]"
              )}
            >
              {apiErrorMessage(loadError)}
            </p>
            <button
              type="button"
              onClick={() => {
                void workspace.refresh();
              }}
              className={cn(
                getTypographyClassName("buttonSecondary"),
                "min-h-11 rounded-[var(--radius-button)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 text-[var(--color-muted)] transition-all hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-on-surface)]"
              )}
            >
              Retry loading
            </button>
          </div>
        ) : null}

        {stage === "content" && !isStageLoading && documentData && factsData ? (
          <>
          <ContentStudioClient
            quotationId={quotationId}
            lang={lang}
            impactActionId={search.get("impactAction") ?? undefined}
            onEditFacts={(section) => {
              setRequestedStageIntent("facts");
              const params = new URLSearchParams(search.toString());
              params.set("stage", "facts");
              params.delete("section");
              params.delete("focus");
              params.set("factsSection", section === "booking_terms" ? "seller" : section === "inclusions_exclusions" ? "services" : "trip");
              startStageTransition(() => {
                router.replace(`${pathname}?${params.toString()}`, { scroll: false });
              });
            }}
            onProceedToDesign={() => void goTo("design")}
            resources={{
              documentData,
              draftsData: workspace.drafts.data,
              factsData,
              reviewData,
              refresh: workspace.refresh,
              request: workspace.request,
            }}
          />
          </>
        ) : stage === "content" && !loadError ? <StagePanelSkeleton stage="content" /> : null}

        {stage === "design" && !isStageLoading && documentData && factsData && liveDocumentModel ? (
          <div className="flex flex-col gap-5">
            <DesignPreviewToolbar
              viewMode={previewMode}
              onViewModeChange={setPreviewMode}
              onOpenPreview={() => setIsPreviewModalOpen(true)}
              themeName={previewProfile?.themeId ?? documentData.brandProfile.themeId ?? "Brochure"}
            />

            <div className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
              <p
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "text-[var(--color-muted)]"
                )}
              >
                This preview reads the canonical brochure document. Only applied
                content is visible. Click elements on the canvas to edit presentation copy.
              </p>
              <DesignCanvas
                  quotationId={quotationId}
                  lang={lang}
                  model={liveDocumentModel}
                  document={documentData.document}
                  currentRevision={documentData.currentRevision}
                  canEditDesignerFacts={editable && !immutableFacts}
                  immutableFacts={immutableFacts}
                  isEditingQuotation={isEditingQuotation}
                  factsSourceKind={factsData?.source?.kind}
                  businessVersionNumber={factsData?.businessVersion?.number}
                  onRequestEditQuotation={requestEditQuotation}
                  contract={documentData.editableContract}
                  facts={factsData?.facts}
                  onSaved={() => workspace.refresh()}
                  onSaveDesignerFacts={async (next) => {
                    try {
                      const updatedFacts = updateDesignerPresentationFacts(
                        factsData.facts,
                        next
                      );
                      if (immutableFacts) throw new Error("Designer Facts are immutable; use Design overrides.");
                      await workspace.saveFacts(updatedFacts);
                      toast("Presentation copy saved to Facts.", "success");
                    } catch (error) {
                      toast(apiErrorMessage(error), "error");
                      throw error;
                    }
                  }}
                  onHandoff={navigateHandoff}
                  focus={search.get("focus") ?? undefined}
                />
            </div>

            {liveDocumentModel ? (
              <BrochurePreviewModal
                isOpen={isPreviewModalOpen}
                onClose={() => setIsPreviewModalOpen(false)}
                documentModel={liveDocumentModel}
                initialViewMode={previewMode}
                publishedUrl={publishedUrl}
              />
            ) : null}
          </div>
        ) : stage === "design" && !loadError ? <StagePanelSkeleton stage="design" /> : null}

        {stage === "review" && !reviewReady ? (
          <div ref={blockersRef}>
            <ReviewBlockersPanel
              workflow={canonicalWorkflow}
              onSetStage={(stg) => setStage(stg)}
              onNavigateHandoff={navigateHandoff}
            />
          </div>
        ) : null}

        {stage === "review" && reviewReady ? (
          <div className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <p
              className={cn(
                getTypographyClassName("bodyMd"),
                "text-[var(--color-on-surface)]"
              )}
            >
              {reviewData?.ready
                ? "The canonical document is ready for review and publish."
                : "Resolve the remaining factual or content-review checks before publishing."}
            </p>
            {reviewData?.missingInputs.length ||
            reviewData?.blockingDrafts.length ? (
              <ul
                className={cn(
                  getTypographyClassName("bodySm"),
                  "text-[var(--color-muted)]"
                )}
              >
                <li>
                  Missing facts: {reviewData.missingInputs.join(", ") || "none"}
                </li>
                <li>
                  Content to review:{" "}
                  {reviewData.blockingDrafts.join(", ") || "none"}
                </li>
              </ul>
            ) : null}
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={publish}
                disabled={pending || !reviewReady || !selectedBrandId || publicationJob?.status === "queued" || publicationJob?.status === "running"}
                className={cn(
                  getTypographyClassName("buttonPrimary"),
                  "min-h-11 rounded-[var(--radius-button)] bg-[var(--color-accent)] !text-white hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] px-6 shadow-md border border-transparent transition-all disabled:opacity-50"
                )}
              >
                {pending ? "Publishing…" : "Publish quotation"}
              </button>
            </div>
            <PublicationTargetManager
              quotationId={quotationId}
              brandId={selectedBrandId}
              onBrandChange={setPublicationBrandId}
              brandsData={brandsResponse}
              publications={workspace.publications.data}
              refresh={workspace.refresh}
            />
            {publishedUrl ? publicationJob?.status === 'succeeded' ? <a href={publishedUrl} target="_blank" rel="noreferrer" className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-accent)]")}>Canonical URL</a> : <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>Canonical URL · Preparing</span> : null}
            {fallbackUrl ? publicationJob?.status === 'succeeded' ? <a href={fallbackUrl} target="_blank" rel="noreferrer" className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-accent)]")}>Customer fallback URL</a> : <span className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-muted)]")}>Customer fallback URL · Preparing</span> : null}
            {publicationJob ? (
              <p
                className={cn(
                  getTypographyClassName("bodySm"),
                  "text-[var(--color-muted)]"
                )}
              >
                Publication job: {publicationJob.status}
                {publicationJob.lastError
                  ? ` · ${publicationJob.lastError}`
                  : ""}
              </p>
            ) : null}
            {pdfUrl ? (
              <a
                href={pdfUrl}
                target="_blank"
                rel="noreferrer"
                className={cn(
                  getTypographyClassName("bodyMd"),
                  "text-[var(--color-accent)]"
                )}
              >
                Download PDF
              </a>
            ) : null}
          </div>
        ) : null}
      </section>

      <RequestRecapModal
        isOpen={isRecapOpen}
        onClose={() => setIsRecapOpen(false)}
        request={quoteRequest ?? null}
      />
      <EditQuotationConfirmModal
        isOpen={isEditQuotationModalOpen}
        businessVersionNumber={factsData?.businessVersion?.number}
        onConfirm={confirmEditQuotation}
        onCancel={cancelEditQuotation}
      />
    </div>
  );
}
