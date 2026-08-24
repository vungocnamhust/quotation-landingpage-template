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
  RefreshCw,
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
import { apiErrorMessage, quotationFetch } from "../../lib/apiError.ts";
import { buildDisplayDocumentFromQuoteDocument } from "../../display/runtimePageBuilder.ts";
import type { ViewMode } from "../../display/contracts.ts";
import { updateDesignerPresentationFacts } from "../../lib/prefillEngine.ts";
import { useQuotationWorkspace } from "./useQuotationWorkspace.ts";
import { useQuotationWorkflowManager } from "./useQuotationWorkflowManager.ts";
import { useToast } from "../staff-workspace/ToastProvider.tsx";
import {
  parseFactsDeepLink,
  serializeFactsFocus,
  type ResolvedHandoff,
} from "./editableHandoff.ts";
import { ReviewBlockersPanel } from "./ReviewBlockersPanel.tsx";
import DesignPreviewToolbar from "./DesignPreviewToolbar.tsx";
import BrochurePreviewModal from "./BrochurePreviewModal.tsx";
import RequestRecapModal from "./RequestRecapModal.tsx";
import ImpactCenter from "./ImpactCenter.tsx";

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
const stages = ["facts", "content", "design", "review"] as const;
type Stage = (typeof stages)[number];

const stageIcons: Record<Stage, React.ComponentType<{ size?: number; className?: string }>> = {
  facts: ClipboardList,
  content: PenLine,
  design: Palette,
  review: Rocket,
};

export default function QuotationWorkspaceClient({
  quotationId,
  lang,
}: {
  quotationId: string;
  lang: string;
}) {
  const router = useRouter();
  const search = useSearchParams();
  const pathname = usePathname();
  const initialStage = search.get("stage");
  const isImpactCenter = initialStage === "impact";
  const [stage, setStage] = useState<Stage>(
    stages.includes(initialStage as Stage) ? (initialStage as Stage) : "facts"
  );
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
  const [pending, startTransition] = useTransition();
  const workspace = useQuotationWorkspace(quotationId, lang, isImpactCenter);
  const refreshWorkspace = workspace.refresh;
  const { data: factsData } = workspace.facts;
  const { data: documentData } = workspace.document;
  const { data: reviewData } = workspace.review;
  const { data: workflowData } = workspace.workflow;
  const { data: options } = workspace.options;
  const { data: brandsResponse } = workspace.brands;
  const { data: impactsData } = workspace.impacts;

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
  const [publicationJob, setPublicationJob] = useState<{
    id: string;
    status: string;
    lastError: string | null;
  } | null>(null);
  const reviewReady = workflowData?.review.ready ?? false;
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
  }, []);

  const goTo = useCallback(
    async (next: Stage) => {
      const allowed = await guardedNavigateStage(next);
      if (!allowed) return;

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
        router.push(result.redirectUrl);
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

  function publish() {
    if (!documentData || !reviewReady) return;
    startTransition(async () => {
      let payload: {
        published_url?: string;
        fallback_url?: string;
        pdfUrl?: string;
        jobId?: string;
        status?: string;
        version?: number;
      };
      try {
        payload = await quotationFetch(
          `${API_BASE}/api/v2/quotations/${quotationId}/publish?lang=${encodeURIComponent(
            lang
          )}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              baseRevision: documentData.currentRevision,
              brandId: selectedBrandId || undefined,
            }),
          },
          "Publish failed."
        );
      } catch (error) {
        const message = apiErrorMessage(error);
        notify({ message, type: "error", persistent: true, scope: "publish:request", action: { label: "Retry", onClick: publish } });
        return;
      }
      setPublishedUrl(payload.published_url ?? null);
      setFallbackUrl(payload.fallback_url ?? null);
      setPdfUrl(payload.pdfUrl ?? null);
      setPublicationJob({
        id: payload.jobId ?? '',
        status: payload.status ?? "queued",
        lastError: null,
      });
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
    if (!publicationJob?.id || !['queued', 'running'].includes(publicationJob.status)) return;
    const timer = window.setTimeout(async () => {
      try {
        const job = await quotationFetch<{ id: string; status: string; lastError: string | null }>(
          `${API_BASE}/api/v2/publication-jobs/${publicationJob.id}`,
          undefined,
          'Unable to refresh publication status.',
        );
        setPublicationJob(job);
        if (job.status === 'succeeded') {
          await refreshWorkspace();
          clearScope('publish:job');
          toast('Publication is live.', 'success');
        }
        if (job.status === 'failed') {
          notify({ message: job.lastError || 'Publication failed before the PDF could be published.', type: 'error', persistent: true, scope: 'publish:job', action: { label: 'Open review', onClick: () => setStage('review') } });
        }
      } catch (error) {
        const message = apiErrorMessage(error);
        setPublicationJob((current) => current ? { ...current, status: 'failed', lastError: message } : current);
        notify({ message: `Publication status could not be refreshed: ${message}`, type: 'error', persistent: true, scope: 'publish:job', action: { label: 'Retry status', onClick: () => setPublicationJob((current) => current ? { ...current, status: 'queued' } : current) } });
      }
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [clearScope, notify, publicationJob, refreshWorkspace, toast]);

  const labels: Record<Stage, string> = {
    facts: "Facts",
    content: "Content",
    design: "Design",
    review: "Review & Publish",
  };

  const isLocked = (item: Stage) => item === "review" ? !reviewReady : false;

  const isComplete = (item: Stage) => {
    if (item === "facts") return workflowData?.facts.ready ?? false;
    if (item === "content") return workflowData?.content.ready ?? false;
    if (item === "design") return workflowData?.design.ready ?? false;
    if (item === "review") return workflowData?.review.ready ?? false;
    return false;
  };

  const immutableFacts = factsData?.businessVersion?.immutable === true;
  const editable = factsData?.source?.kind === "manual" && (!immutableFacts || isEditingQuotation);

  const activeFacts =
    editableFacts ??
    (factsData?.facts
      ? hydrateDestinationRefs(factsData.facts, factsData.resolvedFacts)
      : undefined);

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
      const allowed = await guardedNavigateStage(target.stage as Stage);
      if (!allowed) return;

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
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [documentData?.document, guardedNavigateStage, pathname, router, search],
  );

  const acceptImpactCenter = useCallback(async (selectedTargetIds: number[]) => {
    try {
      await workspace.request(
        `/api/v2/quotations/${quotationId}/impacts/accept`,
        { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ selectedTargetIds }) },
        "Impact Center could not be accepted."
      );
      await workspace.refresh();
      clearScope("quotation:impact-center");
      toast("Change plan accepted. Choose where to continue.", "success");
    } catch (error) {
      notify({ message: apiErrorMessage(error), type: "error", persistent: true, scope: "quotation:impact-center", action: { label: "Retry", onClick: () => void workspace.impacts.mutate() } });
      throw error;
    }
  }, [clearScope, notify, quotationId, toast, workspace]);

  if (isImpactCenter) {
    return <ImpactCenter impacts={impactsData?.items ?? []} loading={!impactsData && !workspace.impacts.error} error={workspace.impacts.error ? apiErrorMessage(workspace.impacts.error) : null} pending={pending} onAccept={acceptImpactCenter} onRetry={() => void workspace.impacts.mutate()} onReviewFacts={() => router.replace(`${pathname}?stage=facts&lang=${encodeURIComponent(lang)}`)} onOpenContent={(target) => router.replace(`${pathname}?stage=content&section=${encodeURIComponent(target.scope)}&focus=${encodeURIComponent(target.deepLink.focus ?? "")}&impactTarget=${target.id}&lang=${encodeURIComponent(lang)}`)} />;
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
                  aria-disabled={locked}
                  className={cn(
                    "workspace-stepper__step",
                    current && "workspace-stepper__step--current",
                    complete && "workspace-stepper__step--complete",
                    locked && "workspace-stepper__step--locked"
                  )}
                  title={locked ? "Resolve previous stages first" : undefined}
                >
                  <span className="workspace-stepper__circle">
                    {complete ? (
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
        {stage === "facts" && factsData?.facts && activeFacts && options ? (
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
        ) : stage === "facts" ? (
          <div className="workspace-skeleton">
            <div className="workspace-skeleton__line workspace-skeleton__line--wide" />
            <div className="workspace-skeleton__line workspace-skeleton__line--mid" />
          </div>
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

        {stage === "content" ? (
          <>
          <ContentStudioClient
            quotationId={quotationId}
            lang={lang}
            onEditFacts={(section) => {
              const params = new URLSearchParams(search.toString());
              params.set("stage", "facts");
              params.delete("section");
              params.delete("focus");
              params.set("factsSection", section === "booking_terms" ? "seller" : section === "inclusions_exclusions" ? "services" : "trip");
              router.replace(`${pathname}?${params.toString()}`, { scroll: false });
              setStage("facts");
            }}
            onProceedToDesign={() => setStage("design")}
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
        ) : null}

        {stage === "design" && documentData ? (
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
              {liveDocumentModel && factsData ? (
                <DesignCanvas
                  quotationId={quotationId}
                  lang={lang}
                  model={liveDocumentModel}
                  document={documentData.document}
                  currentRevision={documentData.currentRevision}
                  canEditDesignerFacts={editable && !immutableFacts}
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
              ) : null}
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
        ) : null}

        {stage === "review" && !reviewReady ? (
          <div ref={blockersRef}>
            <ReviewBlockersPanel
              reviewData={reviewData}
              workflowData={workflowData}
              publicationJob={publicationJob}
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
                disabled={pending || !reviewReady || !selectedBrandId}
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
    </div>
  );
}
